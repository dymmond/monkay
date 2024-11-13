from __future__ import annotations

import warnings
from collections.abc import Callable, Collection, Generator, Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cached_property, partial
from importlib import import_module
from inspect import isclass, ismodule
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NamedTuple,
    Protocol,
    TypedDict,
    TypeVar,
    cast,
    overload,
    runtime_checkable,
)

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings

INSTANCE = TypeVar("INSTANCE")
SETTINGS = TypeVar("SETTINGS", bound="BaseSettings")


class SortedExportsEntry(NamedTuple):
    category: Literal["other", "lazy_import", "deprecated_lazy_import"]
    export_name: str
    path: str


class DeprecatedImport(TypedDict, total=False):
    path: str | Callable[[], Any]
    reason: str
    new_attribute: str


DeprecatedImport.__required_keys__ = frozenset({"deprecated"})


class PRE_ADD_LAZY_IMPORT_HOOK(Protocol):
    @overload
    @staticmethod
    def __call__(
        key: str,
        value: str | Callable[[], Any],
        type_: Literal["lazy_import"],
        /,
    ) -> tuple[str, str | Callable[[], Any]]: ...

    @overload
    @staticmethod
    def __call__(
        key: str,
        value: DeprecatedImport,
        type_: Literal["deprecated_lazy_import"],
        /,
    ) -> tuple[str, DeprecatedImport]: ...

    @staticmethod
    def __call__(
        key: str,
        value: str | Callable[[], Any] | DeprecatedImport,
        type_: Literal["lazy_import", "deprecated_lazy_import"],
        /,
    ) -> tuple[str, str | Callable[[], Any] | DeprecatedImport]: ...


def load(path: str, *, allow_splits: str = ":.", package: None | str = None) -> Any:
    splitted = path.rsplit(":", 1) if ":" in allow_splits else []
    if len(splitted) < 2 and "." in allow_splits:
        splitted = path.rsplit(".", 1)
    if len(splitted) != 2:
        raise ValueError(f"invalid path: {path}")
    module = import_module(splitted[0], package)
    return getattr(module, splitted[1])


def load_any(
    path: str,
    attrs: Collection[str],
    *,
    non_first_deprecated: bool = False,
    package: None | str = None,
) -> Any | None:
    module = import_module(path, package)
    first_name: None | str = None

    for attr in attrs:
        if hasattr(module, attr):
            if non_first_deprecated and first_name is not None:
                warnings.warn(
                    f'"{attr}" is deprecated, use "{first_name}" instead.',
                    DeprecationWarning,
                    stacklevel=2,
                )
            return getattr(module, attr)
        if first_name is None:
            first_name = attr
    raise ImportError(f"Could not import any of the attributes:.{', '.join(attrs)}")


def absolutify_import(import_path: str, package: str | None) -> str:
    if not package or not import_path:
        return import_path
    dot_count: int = 0
    try:
        while import_path[dot_count] == ".":
            dot_count += 1
    except IndexError:
        raise ValueError("not an import path") from None
    if dot_count == 0:
        return import_path
    if dot_count - 2 > package.count("."):
        raise ValueError("Out of bound, tried to cross parent.")
    if dot_count > 1:
        package = package.rsplit(".", dot_count - 1)[0]

    return f"{package}.{import_path.lstrip('.')}"


@runtime_checkable
class ExtensionProtocol(Protocol[INSTANCE, SETTINGS]):
    name: str

    def apply(self, monkay_instance: Monkay[INSTANCE, SETTINGS]) -> None: ...


class InGlobalsDict(Exception):
    pass


def _stub_previous_getattr(name: str) -> Any:
    raise AttributeError(f'Module has no attribute: "{name}" (Monkay).')


def _obj_to_full_name(obj: Any) -> str:
    if ismodule(obj):
        return obj.__spec__.name  # type: ignore
    if not isclass(obj):
        obj = type(obj)
    return f"{obj.__module__}.{obj.__qualname__}"


class Monkay(Generic[INSTANCE, SETTINGS]):
    getter: Callable[..., Any]
    _instance: None | INSTANCE = None
    _instance_var: ContextVar[INSTANCE | None] | None = None
    # extensions are pretended to always exist, we check the _extensions_var
    _extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]]
    _extensions_var: None | ContextVar[None | dict[str, ExtensionProtocol[INSTANCE, SETTINGS]]] = None
    _extensions_applied: None | ContextVar[dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None] = None
    _settings_var: ContextVar[SETTINGS | None] | None = None

    def __init__(
        self,
        globals_dict: dict,
        *,
        with_instance: str | bool = False,
        with_extensions: str | bool = False,
        extension_order_key_fn: None | Callable[[ExtensionProtocol[INSTANCE, SETTINGS]], Any] = None,
        settings_path: str = "",
        preloads: Iterable[str] = (),
        settings_preload_name: str = "",
        settings_preloads_name: str = "",
        settings_extensions_name: str = "",
        uncached_imports: Iterable[str] = (),
        lazy_imports: dict[str, str | Callable[[], Any]] | None = None,
        deprecated_lazy_imports: dict[str, DeprecatedImport] | None = None,
        settings_ctx_name: str = "monkay_settings_ctx",
        extensions_applied_ctx_name: str = "monkay_extensions_applied_ctx",
        skip_all_update: bool = False,
        pre_add_lazy_import_hook: None | PRE_ADD_LAZY_IMPORT_HOOK = None,
        post_add_lazy_import_hook: None | Callable[[str], None] = None,
        package: str | None = "",
    ) -> None:
        self.globals_dict = globals_dict
        if with_instance is True:
            with_instance = "monkay_instance_ctx"
        with_instance = with_instance
        if with_extensions is True:
            with_extensions = "monkay_extensions_ctx"
        with_extensions = with_extensions
        if package == "" and globals_dict.get("__spec__"):
            package = globals_dict["__spec__"].parent
        self.package = package or None

        self._cached_imports: dict[str, Any] = {}
        self.pre_add_lazy_import_hook: None | PRE_ADD_LAZY_IMPORT_HOOK = pre_add_lazy_import_hook
        self.post_add_lazy_import_hook = post_add_lazy_import_hook
        self.uncached_imports: set[str] = set(uncached_imports)
        self.lazy_imports: dict[str, str | Callable[[], Any]] = {}
        self.deprecated_lazy_imports: dict[str, DeprecatedImport] = {}
        if lazy_imports:
            for name, lazy_import in lazy_imports.items():
                self.add_lazy_import(name, lazy_import, no_hooks=True)
        if deprecated_lazy_imports:
            for name, deprecated_import in deprecated_lazy_imports.items():
                self.add_deprecated_lazy_import(name, deprecated_import, no_hooks=True)
        self.settings_path = settings_path
        if self.settings_path:
            self._settings_var = globals_dict[settings_ctx_name] = ContextVar(settings_ctx_name, default=None)

        if settings_preload_name:
            warnings.warn(
                'The "settings_preload_name" parameter is deprecated use "settings_preloads_name" instead.',
                DeprecationWarning,
                stacklevel=2,
            )
        if not settings_preloads_name and settings_preload_name:
            settings_preloads_name = settings_preload_name
        self.settings_preloads_name = settings_preloads_name
        self.settings_extensions_name = settings_extensions_name

        self._handle_preloads(preloads)
        if with_instance:
            self._instance_var = globals_dict[with_instance] = ContextVar(with_instance, default=None)
        if with_extensions:
            self.extension_order_key_fn = extension_order_key_fn
            self._extensions = {}
            self._extensions_var = globals_dict[with_extensions] = ContextVar(with_extensions, default=None)
            self._extensions_applied_var = globals_dict[extensions_applied_ctx_name] = ContextVar(
                extensions_applied_ctx_name, default=None
            )
            self._handle_extensions()
        if self.lazy_imports or self.deprecated_lazy_imports:
            getter: Callable[..., Any] = self.module_getter
            if "__getattr__" in globals_dict:
                getter = partial(getter, chained_getter=globals_dict["__getattr__"])
            globals_dict["__getattr__"] = self.getter = getter
            if not skip_all_update:
                all_var = globals_dict.setdefault("__all__", [])
                globals_dict["__all__"] = self.update_all_var(all_var)

    def clear_caches(self, settings_cache: bool = True, import_cache: bool = True) -> None:
        if settings_cache:
            self.__dict__.pop("_settings", None)
        if import_cache:
            self._cached_imports.clear()

    @property
    def instance(self) -> INSTANCE | None:
        assert self._instance_var is not None, "Monkay not enabled for instances"
        instance: INSTANCE | None = self._instance_var.get()
        if instance is None:
            instance = self._instance
        return instance

    def set_instance(
        self,
        instance: INSTANCE,
        *,
        apply_extensions: bool = True,
        use_extensions_overwrite: bool = True,
    ) -> None:
        assert self._instance_var is not None, "Monkay not enabled for instances"
        # need to address before the instance is swapped
        if apply_extensions and self._extensions_applied_var.get() is not None:
            raise RuntimeError("Other apply process in the same context is active.")
        self._instance = instance
        if apply_extensions and self._extensions_var is not None:
            self.apply_extensions(use_overwrite=use_extensions_overwrite)

    @contextmanager
    def with_instance(
        self,
        instance: INSTANCE | None,
        *,
        apply_extensions: bool = False,
        use_extensions_overwrite: bool = True,
    ) -> Generator:
        assert self._instance_var is not None, "Monkay not enabled for instances"
        # need to address before the instance is swapped
        if apply_extensions and self._extensions_var is not None and self._extensions_applied_var.get() is not None:
            raise RuntimeError("Other apply process in the same context is active.")
        token = self._instance_var.set(instance)
        try:
            if apply_extensions and self._extensions_var is not None:
                self.apply_extensions(use_overwrite=use_extensions_overwrite)
            yield
        finally:
            self._instance_var.reset(token)

    def apply_extensions(self, use_overwrite: bool = True) -> None:
        assert self._extensions_var is not None, "Monkay not enabled for extensions"
        extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None = (
            self._extensions_var.get() if use_overwrite else None
        )
        if extensions is None:
            extensions = self._extensions
        extensions_applied = self._extensions_applied_var.get()
        if extensions_applied is not None:
            raise RuntimeError("Other apply process in the same context is active.")
        extensions_ordered: Iterable[tuple[str, ExtensionProtocol[INSTANCE, SETTINGS]]] = cast(
            dict[str, ExtensionProtocol[INSTANCE, SETTINGS]], extensions
        ).items()

        if self.extension_order_key_fn is not None:
            extensions_ordered = sorted(
                extensions_ordered,
                key=self.extension_order_key_fn,  # type:  ignore
            )
        extensions_applied = set()
        token = self._extensions_applied_var.set(extensions_applied)
        try:
            for name, extension in extensions_ordered:
                if name in extensions_applied:
                    continue
                extensions_applied.add(name)
                extension.apply(self)
        finally:
            self._extensions_applied_var.reset(token)

    def ensure_extension(self, name_or_extension: str | ExtensionProtocol[INSTANCE, SETTINGS]) -> None:
        assert self._extensions_var is not None, "Monkay not enabled for extensions"
        extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None = self._extensions_var.get()
        if extensions is None:
            extensions = self._extensions
        if isinstance(name_or_extension, str):
            name = name_or_extension
            extension = extensions.get(name)
        elif not isclass(name_or_extension) and isinstance(name_or_extension, ExtensionProtocol):
            name = name_or_extension.name
            extension = extensions.get(name, name_or_extension)
        else:
            raise RuntimeError('Provided extension "{name_or_extension}" does not implement the ExtensionProtocol')
        if name in self._extensions_applied_var.get():
            return

        if extension is None:
            raise RuntimeError(f'Extension: "{name}" does not exist.')
        self._extensions_applied_var.get().add(name)
        extension.apply(self)

    def add_extension(
        self,
        extension: ExtensionProtocol[INSTANCE, SETTINGS]
        | type[ExtensionProtocol[INSTANCE, SETTINGS]]
        | Callable[[], ExtensionProtocol[INSTANCE, SETTINGS]],
        use_overwrite: bool = True,
        replace: bool = False,
    ) -> None:
        assert self._extensions_var is not None, "Monkay not enabled for extensions"
        extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None = (
            self._extensions_var.get() if use_overwrite else None
        )
        if extensions is None:
            extensions = self._extensions
        if callable(extension) or isclass(extension):
            extension = extension()
        if not isinstance(extension, ExtensionProtocol):
            raise ValueError(f"Extension {extension} is not compatible")
        if not replace and extension.name in extensions:
            raise KeyError(f'Extension "{extension.name}" already exists.')
        extensions[extension.name] = extension

    @contextmanager
    def with_extensions(
        self,
        extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None,
        *,
        apply_extensions: bool = False,
    ) -> Generator:
        # why None, for temporary using the real extensions
        assert self._extensions_var is not None, "Monkay not enabled for extensions"
        token = self._extensions_var.set(extensions)
        try:
            if apply_extensions and self.instance is not None:
                self.apply_extensions()
            yield
        finally:
            self._extensions_var.reset(token)

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
        """Debug method to check"""

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
                missing.setdefault(self.globals_dict["__spec__"].name, set()).add("missing_all_var")
                all_var = []
        key_set = set(chain(self.lazy_imports.keys(), self.deprecated_lazy_imports.keys()))
        value_pathes_set: set[str] = set()
        for name in key_set:
            found_path: str = ""
            if name in self.lazy_imports and isinstance(self.lazy_imports[name], str):
                found_path = cast(str, self.lazy_imports[name]).replace(":", ".")
            elif name in self.deprecated_lazy_imports and isinstance(self.deprecated_lazy_imports[name]["path"], str):
                found_path = cast(str, self.deprecated_lazy_imports[name]["path"]).replace(":", ".")
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
                    obj = self.getter(export_name, no_warn_deprecated=True, check_globals_dict=True)
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
                    if export_path not in value_pathes_set and _obj_to_full_name(obj) not in value_pathes_set:
                        missing.setdefault(export_path, set()).add("search_path_extra")

        if all_var is not False:
            for name in key_set.difference(cast(Collection[str], all_var)):
                missing.setdefault(name, set()).add("not_in_all_var")

        return missing

    @cached_property
    def _settings(self) -> SETTINGS:
        settings: Any = load(self.settings_path, package=self.package)
        if isclass(settings):
            settings = settings()
        return settings

    @property
    def settings(self) -> SETTINGS:
        assert self._settings_var is not None, "Monkay not enabled for settings"
        settings = self._settings_var.get()
        if settings is None:
            settings = self._settings
        return settings

    @contextmanager
    def with_settings(self, settings: SETTINGS | None) -> Generator:
        assert self._settings_var is not None, "Monkay not enabled for settings"
        # why None, for temporary using the real settings
        token = self._settings_var.set(settings)
        try:
            yield
        finally:
            self._settings_var.reset(token)

    def add_lazy_import(self, name: str, value: str | Callable[[], Any], *, no_hooks: bool = False) -> None:
        if not no_hooks and self.pre_add_lazy_import_hook is not None:
            name, value = self.pre_add_lazy_import_hook(name, value, "lazy_import")
        if name in self.lazy_imports:
            raise KeyError(f'"{name}" is already a lazy import')
        if name in self.deprecated_lazy_imports:
            raise KeyError(f'"{name}" is already a deprecated lazy import')
        self.lazy_imports[name] = value
        if not no_hooks and self.post_add_lazy_import_hook is not None:
            self.post_add_lazy_import_hook(name)

    def add_deprecated_lazy_import(self, name: str, value: DeprecatedImport, *, no_hooks: bool = False) -> None:
        if not no_hooks and self.pre_add_lazy_import_hook is not None:
            name, value = self.pre_add_lazy_import_hook(name, value, "deprecated_lazy_import")
        if name in self.lazy_imports:
            raise KeyError(f'"{name}" is already a lazy import')
        if name in self.deprecated_lazy_imports:
            raise KeyError(f'"{name}" is already a deprecated lazy import')
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
            all_var = self.globals_dict["__all__"]
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
                        warn_strs.append(f"Reason: {deprecated['reason']}.")
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

    def _handle_preloads(self, preloads: Iterable[str]) -> None:
        if self.settings_preloads_name:
            preloads = chain(preloads, getattr(self.settings, self.settings_preloads_name))
        for preload in preloads:
            splitted = preload.rsplit(":", 1)
            try:
                module = import_module(splitted[0], self.package)
            except ImportError:
                module = None
            if module is not None and len(splitted) == 2:
                getattr(module, splitted[1])()

    def _handle_extensions(self) -> None:
        if self.settings_extensions_name:
            for extension in getattr(self.settings, self.settings_extensions_name):
                self.add_extension(extension, use_overwrite=False)
