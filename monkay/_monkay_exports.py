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
    """
    Manages lazy imports and exports for a module, providing enhanced attribute access and introspection.
    """

    package: str | None
    """The package name associated with the module."""

    getter: Callable[..., Any] | None = None
    """
    The getter function used for attribute access, initialized with lazy import logic.
    This function handles both regular attribute access and the resolution of lazy imports.
    """

    dir_fn: Callable[[], list[str]] | None = None
    """
    The directory listing function, enhanced to include lazy imports.
    This function is used to generate the list of attributes available in the module.
    """

    globals_dict: dict
    """The module's globals dictionary, used to access and modify module-level variables."""

    _cached_imports: dict[str, Any]
    """
    A cache of resolved lazy imports.
    This dictionary stores the results of lazy imports to avoid redundant loading.
    """

    pre_add_lazy_import_hook: None | PRE_ADD_LAZY_IMPORT_HOOK
    """
    A hook to modify lazy import definitions before they are added.
    This hook allows for custom logic to be applied before a lazy import is registered.
    """

    post_add_lazy_import_hook: None | Callable[[str], None]
    """
    A hook to execute after a lazy import is added.
    This hook allows for custom logic to be applied after a lazy import is successfully registered.
    """

    lazy_imports: dict[str, str | Callable[[], Any]]
    """
    A dictionary of lazy imports, mapping names to import paths or callables.
    This dictionary stores the definitions of lazy imports, which are resolved on demand.
    """

    deprecated_lazy_imports: dict[str, DeprecatedImport]
    """
    A dictionary of deprecated lazy imports, including deprecation details.
    This dictionary stores the definitions of deprecated lazy imports, which issue warnings on access.
    """

    uncached_imports: set[str]
    """
    A set of imports that should not be cached.
    This set contains the names of lazy imports that should be resolved every time they are accessed.
    """

    def _init_global_dir_hook(self) -> None:
        """
        Initializes the global directory listing hook if it's not already set.

        This method sets up the `__dir__` function in the module's globals dictionary.
        It enhances the directory listing to include lazy and deprecated imports,
        and optionally chains with an existing `__dir__` function.
        """
        if self.dir_fn is not None:
            return
        dir_fn = self.module_dir_fn
        if "__dir__" in self.globals_dict:
            dir_fn = partial(dir_fn, chained_dir_fn=self.globals_dict["__dir__"])
        self.globals_dict["__dir__"] = self.dir_fn = dir_fn

    def _init_global_getter_hook(self) -> None:
        """
        Initializes the global attribute getter hook if it's not already set.

        This method sets up the `__getattr__` function in the module's globals dictionary.
        It enhances attribute access to handle lazy and deprecated imports,
        and optionally chains with an existing `__getattr__` function.
        """
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
        """
        Debug method to check for missing imports and inconsistencies in exports.

        This method performs a comprehensive check for missing attributes, imports,
        and inconsistencies in the module's exports, including lazy and deprecated imports.
        It compares the defined exports with the module's `__all__` variable and optional
        search paths to identify potential issues.

        Args:
            all_var: If True, checks against the module's `__all__` variable.
                     If a collection, checks against the provided names.
                     If False, skips checking against `__all__`.
            search_pathes: Optional list of module paths to search for additional exports.
            ignore_deprecated_import_errors: If True, ignores import errors for deprecated lazy imports.
            require_search_path_all_var: If True, requires `__all__` to be defined in searched modules.

        Returns:
            A dictionary where keys are names of missing or inconsistent items,
            and values are sets of strings indicating the types of issues.

        Issue types:
            - "not_in_all_var": Export is defined but not in `__all__`.
            - "missing_attr": Attribute is missing from the module or a searched module.
            - "missing_all_var": `__all__` is missing from the module or a searched module.
            - "import": Import error occurred while resolving a lazy or deprecated import.
            - "shadowed": Attribute is shadowed by a real variable in the module's globals.
            - "search_path_extra": Export from a search path is not found in the module's exports.
            - "search_path_import": Import error occurred while importing a search path.
        """
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
        """
        Adds a lazy import to the module.

        This method adds a lazy import, which is resolved only when the attribute is accessed.
        This can improve module loading performance by deferring imports.

        Args:
            name: The name of the lazy import.
            value: The import path as a string or a callable that returns the imported object.
            no_hooks: If True, skips the pre and post add hooks.

        Raises:
            KeyError: If the name is already a lazy or deprecated lazy import.
        """
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
        """
        Adds a deprecated lazy import to the module.

        This method adds a lazy import that is marked as deprecated. When accessed, it will
        issue a deprecation warning.

        Args:
            name: The name of the deprecated import.
            value: A dictionary containing details about the deprecation, including the import path.
            no_hooks: If True, skips the pre and post add hooks.

        Raises:
            KeyError: If the name is already a lazy or deprecated lazy import.
        """
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
        """
        Returns a sorted list of module exports, categorized and sorted as specified.

        This method generates a list of `SortedExportsEntry` objects, which represent the module's exports.
        It categorizes exports as "lazy_import", "deprecated_lazy_import", or "other", and sorts them
        based on the specified criteria.

        Args:
            all_var: An optional collection of export names. If None, uses the module's `__all__` variable.
            separate_by_category: If True, sorts exports by category first, then by the specified `sort_by` attribute.
            sort_by: The attribute to sort by, either "export_name" or "path".

        Returns:
            A list of `SortedExportsEntry` objects.
        """
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
        """
        Generates a directory listing for the module, including lazy and deprecated imports.

        This method combines the module's `__all__` variable, lazy imports, deprecated lazy imports,
        and optionally the results of a chained directory listing function to create a comprehensive
        list of attributes.

        Args:
            chained_dir_fn: An optional function that returns a list of attribute names,
                              used to extend the directory listing.

        Returns:
            A list of attribute names representing the module's directory.
        """
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

        This method acts as a custom attribute getter for the module, handling lazy imports and deprecated attributes.
        It first checks if the attribute exists in the module's globals dictionary. If not, it checks for lazy or
        deprecated lazy imports. If found, it resolves and returns the imported object.

        Args:
            key: The name of the attribute to retrieve.
            chained_getter: A fallback getter function to call if the attribute is not found in lazy imports.
            no_warn_deprecated: If True, suppresses deprecation warnings for deprecated attributes.
            check_globals_dict: If True, checks the module's globals dictionary first. If "fail", raises InGlobalsDict if found.

        Returns:
            The retrieved attribute value.

        Raises:
            InglobalsDict: If `check_globals_dict` is "fail" and the attribute is found in globals.
            DeprecationWarning: If a deprecated attribute is accessed and `no_warn_deprecated` is False.
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
        """
        Updates the `__all__` variable to include lazy and deprecated lazy imports.

        This method ensures that all names defined as lazy or deprecated lazy imports
        are included in the module's `__all__` variable.

        Args:
            all_var: The current `__all__` variable as a collection of strings.

        Returns:
            The updated `__all__` variable, either as a list or a set, depending on the input type.
        """
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
