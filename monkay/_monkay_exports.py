from __future__ import annotations

import warnings
from collections.abc import Callable, Collection
from functools import partial
from importlib import import_module
from inspect import isclass, ismodule
from itertools import chain
from typing import (
    Any,
    Literal,
    cast,
)

from .base import InGlobalsDict, absolutify_import, load
from .types import PRE_ADD_LAZY_IMPORT_HOOK, DeprecatedImport, SortedExportsEntry


def _stub_previous_getattr(name: str) -> Any:
    raise AttributeError(f'Module has no attribute: "{name}" (Monkay).')


def _obj_to_full_name(obj: Any) -> str:
    if ismodule(obj):
        return obj.__spec__.name  # type: ignore
    if not isclass(obj):
        obj = type(obj)
    return f"{obj.__module__}.{obj.__qualname__}"


_empty: tuple[Any, ...] = ()


class MonkayExports:
    package: str | None
    getter: Callable[..., Any] | None = None
    dir_fn: Callable[[], list[str]] | None = None
    globals_dict: dict
    _cached_imports: dict[str, Any]
    pre_add_lazy_import_hook: None | PRE_ADD_LAZY_IMPORT_HOOK
    post_add_lazy_import_hook: None | Callable[[str], None]
    lazy_imports: dict[str, str | Callable[[], Any]]
    deprecated_lazy_imports: dict[str, DeprecatedImport]
    uncached_imports: set[str]

    def _init_global_dir_hook(self) -> None:
        if self.dir_fn is not None:
            return
        dir_fn = self.module_dir_fn
        if "__dir__" in self.globals_dict:
            dir_fn = partial(dir_fn, chained_dir_fn=self.globals_dict["__dir__"])
        self.globals_dict["__dir__"] = self.dir_fn = dir_fn

    def _init_global_getter_hook(self) -> None:
        if self.getter is not None:
            return
        getter = self.module_getter
        if "__getattr__" in self.globals_dict:
            getter = partial(getter, chained_getter=self.globals_dict["__getattr__"])
        self.globals_dict["__getattr__"] = self.getter = getter

    def find_missing(
        self,
        *,
        all_var: bool | Collection[str] = True,
        search_pathes: None | Collection[str] = None,
        ignore_deprecated_import_errors: bool = False,
        require_search_path_all_var: bool = True,
    ) -> dict[
        str,
        set[
            Literal[
                "not_in_all_var",
                "missing_attr",
                "missing_all_var",
                "import",
                "shadowed",
                "search_path_extra",
                "search_path_import",
            ]
        ],
    ]:
        """Debug method to check missing imports"""
        self._init_global_getter_hook()

        assert self.getter is not None
        missing: dict[
            str,
            set[
                Literal[
                    "not_in_all_var",
                    "missing_attr",
                    "missing_all_var",
                    "import",
                    "shadowed",
                    "search_path_extra",
                    "search_path_import",
                ]
            ],
        ] = {}
        if all_var is True:
            try:
                all_var = self.getter("__all__", check_globals_dict=True)
            except AttributeError:
                missing.setdefault(self.globals_dict["__spec__"].name, set()).add(
                    "missing_all_var"
                )
                all_var = []
        key_set = set(chain(self.lazy_imports.keys(), self.deprecated_lazy_imports.keys()))
        value_pathes_set: set[str] = set()
        for name in key_set:
            found_path: str = ""
            if name in self.lazy_imports and isinstance(self.lazy_imports[name], str):
                found_path = cast(str, self.lazy_imports[name]).replace(":", ".")
            elif name in self.deprecated_lazy_imports and isinstance(
                self.deprecated_lazy_imports[name]["path"], str
            ):
                found_path = cast(str, self.deprecated_lazy_imports[name]["path"]).replace(
                    ":", "."
                )
            if found_path:
                value_pathes_set.add(absolutify_import(found_path, self.package))
            try:
                obj = self.getter(name, no_warn_deprecated=True, check_globals_dict="fail")
                # also add maybe rexported path
                value_pathes_set.add(_obj_to_full_name(obj))
            except InGlobalsDict:
                missing.setdefault(name, set()).add("shadowed")
            except ImportError:
                if not ignore_deprecated_import_errors or name not in self.deprecated_lazy_imports:
                    missing.setdefault(name, set()).add("import")
        if all_var is not False:
            for export_name in cast(Collection[str], all_var):
                try:
                    obj = self.getter(
                        export_name, no_warn_deprecated=True, check_globals_dict=True
                    )
                except AttributeError:
                    missing.setdefault(export_name, set()).add("missing_attr")
                    continue
                if export_name not in key_set:
                    value_pathes_set.add(_obj_to_full_name(obj))

        if search_pathes:
            for search_path in search_pathes:
                try:
                    mod = import_module(search_path, self.package)
                except ImportError:
                    missing.setdefault(search_path, set()).add("search_path_import")
                    continue
                try:
                    all_var_search = mod.__all__
                except AttributeError:
                    if require_search_path_all_var:
                        missing.setdefault(search_path, set()).add("missing_all_var")

                    continue
                for export_name in all_var_search:
                    export_path = absolutify_import(f"{search_path}.{export_name}", self.package)
                    try:
                        # for re-exports
                        obj = getattr(mod, export_name)
                    except AttributeError:
                        missing.setdefault(export_path, set()).add("missing_attr")
                        # still check check the export path
                        if export_path not in value_pathes_set:
                            missing.setdefault(export_path, set()).add("search_path_extra")
                        continue
                    if (
                        export_path not in value_pathes_set
                        and _obj_to_full_name(obj) not in value_pathes_set
                    ):
                        missing.setdefault(export_path, set()).add("search_path_extra")

        if all_var is not False:
            for name in key_set.difference(cast(Collection[str], all_var)):
                missing.setdefault(name, set()).add("not_in_all_var")

        return missing

    def add_lazy_import(
        self, name: str, value: str | Callable[[], Any], *, no_hooks: bool = False
    ) -> None:
        if not no_hooks and self.pre_add_lazy_import_hook is not None:
            name, value = self.pre_add_lazy_import_hook(name, value, "lazy_import")
        if name in self.lazy_imports:
            raise KeyError(f'"{name}" is already a lazy import')
        if name in self.deprecated_lazy_imports:
            raise KeyError(f'"{name}" is already a deprecated lazy import')
        self._init_global_getter_hook()
        self._init_global_dir_hook()
        self.lazy_imports[name] = value
        if not no_hooks and self.post_add_lazy_import_hook is not None:
            self.post_add_lazy_import_hook(name)

    def add_deprecated_lazy_import(
        self, name: str, value: DeprecatedImport, *, no_hooks: bool = False
    ) -> None:
        if not no_hooks and self.pre_add_lazy_import_hook is not None:
            name, value = self.pre_add_lazy_import_hook(name, value, "deprecated_lazy_import")
        if name in self.lazy_imports:
            raise KeyError(f'"{name}" is already a lazy import')
        if name in self.deprecated_lazy_imports:
            raise KeyError(f'"{name}" is already a deprecated lazy import')
        self._init_global_getter_hook()
        self._init_global_dir_hook()
        self.deprecated_lazy_imports[name] = value
        if not no_hooks and self.post_add_lazy_import_hook is not None:
            self.post_add_lazy_import_hook(name)

    def sorted_exports(
        self,
        all_var: Collection[str] | None = None,
        *,
        separate_by_category: bool = True,
        sort_by: Literal["export_name", "path"] = "path",
    ) -> list[SortedExportsEntry]:
        if all_var is None:
            all_var = self.globals_dict.get("__all__", _empty)
        sorted_exports: list[SortedExportsEntry] = []
        # ensure all entries are only returned once
        for name in set(all_var):
            if name in self.lazy_imports:
                sorted_exports.append(
                    SortedExportsEntry(
                        "lazy_import",
                        name,
                        cast(
                            str,
                            self.lazy_imports[name]
                            if isinstance(self.lazy_imports[name], str)
                            else f"{self.globals_dict['__spec__'].name}.{name}",
                        ),
                    )
                )
            elif name in self.deprecated_lazy_imports:
                sorted_exports.append(
                    SortedExportsEntry(
                        "deprecated_lazy_import",
                        name,
                        cast(
                            str,
                            self.deprecated_lazy_imports[name]["path"]
                            if isinstance(self.deprecated_lazy_imports[name]["path"], str)
                            else f"{self.globals_dict['__spec__'].name}.{name}",
                        ),
                    )
                )
            else:
                sorted_exports.append(
                    SortedExportsEntry(
                        "other",
                        name,
                        f"{self.globals_dict['__spec__'].name}.{name}",
                    )
                )
        if separate_by_category:

            def key_fn(ordertuple: SortedExportsEntry) -> tuple:
                return ordertuple.category, getattr(ordertuple, sort_by)
        else:

            def key_fn(ordertuple: SortedExportsEntry) -> tuple:
                return (getattr(ordertuple, sort_by),)

        sorted_exports.sort(key=key_fn)
        return sorted_exports

    def module_dir_fn(
        self,
        *,
        chained_dir_fn: Callable[[], list[str]] | None = None,
    ) -> list[str]:
        baseset = set(self.globals_dict.get("__all__", None) or _empty)
        baseset.update(self.lazy_imports.keys())
        baseset.update(self.deprecated_lazy_imports.keys())
        if chained_dir_fn is None:
            baseset.update(self.globals_dict.keys())
        else:
            baseset.update(chained_dir_fn())
        return list(baseset)

    def module_getter(
        self,
        key: str,
        *,
        chained_getter: Callable[[str], Any] = _stub_previous_getattr,
        no_warn_deprecated: bool = False,
        check_globals_dict: bool | Literal["fail"] = False,
    ) -> Any:
        """
        Module Getter which handles lazy imports.
        The injected version containing a potential found __getattr__ handler as chained_getter
        is availabe as getter attribute.
        """
        if check_globals_dict and key in self.globals_dict:
            if check_globals_dict == "fail":
                raise InGlobalsDict(f'"{key}" is defined as real variable.')
            return self.globals_dict[key]
        lazy_import = self.lazy_imports.get(key)
        if lazy_import is None:
            deprecated = self.deprecated_lazy_imports.get(key)
            if deprecated is not None:
                lazy_import = deprecated["path"]
                if not no_warn_deprecated:
                    warn_strs = [f'Attribute: "{key}" is deprecated.']
                    if deprecated.get("reason"):
                        # Note: no dot is added, this is the responsibility of the reason author.
                        warn_strs.append(f"Reason: {deprecated['reason']}")
                    if deprecated.get("new_attribute"):
                        warn_strs.append(f'Use "{deprecated["new_attribute"]}" instead.')
                    warnings.warn("\n".join(warn_strs), DeprecationWarning, stacklevel=2)

        if lazy_import is None:
            return chained_getter(key)
        if key not in self._cached_imports or key in self.uncached_imports:
            if callable(lazy_import):
                value: Any = lazy_import()
            else:
                value = load(lazy_import, package=self.package)
            if key in self.uncached_imports:
                return value
            else:
                self._cached_imports[key] = value
        return self._cached_imports[key]

    def update_all_var(self, all_var: Collection[str]) -> list[str] | set[str]:
        if isinstance(all_var, set):
            all_var_set = all_var
        else:
            if not isinstance(all_var, list):
                all_var = list(all_var)
            all_var_set = set(all_var)

        if self.lazy_imports or self.deprecated_lazy_imports:
            for var in chain(
                self.lazy_imports,
                self.deprecated_lazy_imports,
            ):
                if var not in all_var_set:
                    if isinstance(all_var, list):
                        all_var.append(var)
                    else:
                        cast(set[str], all_var).add(var)

        return cast("list[str] | set[str]", all_var)
