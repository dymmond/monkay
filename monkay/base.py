from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cached_property, partial
from importlib import import_module
from inspect import isclass
from itertools import chain
from threading import Lock
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypedDict,
    TypeVar,
    runtime_checkable,
)

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings

L = TypeVar("L")


class DeprecatedImport(TypedDict):
    path: str
    reason: str = "-"
    new_attribute: str = ""


def load(path: str, allow_splits: str = ":.") -> tuple[Any, Any]:
    splitted = path.rsplit(":", 1) if ":" in allow_splits else []
    if len(splitted) < 2 and "." in allow_splits:
        splitted = path.rsplit(".", 1)
    if len(splitted) != 2:
        raise ValueError(f"invalid path: {path}")
    module = import_module(splitted[0])
    return module, getattr(module, splitted[1])


def multi_load(path: str, attrs: Iterable[str]) -> tuple[Any, Any] | None:
    module = import_module(path)
    for attr in attrs:
        if hasattr(module, attr):
            return module, getattr(module, attr)
    return None


@runtime_checkable
class ExtensionProtocol(Protocol, Generic[L]):
    name: str

    def apply(self, app: L) -> None: ...


def _stub_previous_getattr(name: str) -> Any:
    raise AttributeError(f'Module has no attribute: "{name}" (Monkay).')


class Monkay(Generic[L]):
    monkays: dict[str, Monkay] = {}
    monkays_global_lock: Lock = Lock()
    instance: None | L = None
    instance_var: ContextVar[L | None] | None = None
    extensions: None | dict[str, ExtensionProtocol[L]] = None
    extensions_var: None | ContextVar[None | dict[str, ExtensionProtocol[L]]] = None

    def __init__(
        self,
        global_dict: dict,
        *,
        name: str = "",
        license: str = "",
        with_instance: str | bool = False,
        with_extensions: str | bool = False,
        register: bool | None = None,
        settings_path: str = "",
        preloads: Sequence[str] = (),
        settings_preload_name: str = "",
        settings_extensions_name: str = "",
        lazy_imports: dict[str, str] | None = None,
        deprecated_lazy_imports: dict[str, DeprecatedImport] | None = None,
    ) -> None:
        self.name = name or global_dict["__spec__"].name.split(".", 1)[0]
        if with_instance is True:
            with_instance = "monkay_instance_ctx"
        self.with_instance = with_instance
        if with_extensions is True:
            with_extensions = "monkay_extensions_ctx"
        self.with_extensions = with_extensions
        if register is None:
            register = self.name == global_dict["__name__"]

        self._cache_imports = {}
        self.module = global_dict["__spec__"].name
        self.license = license
        self.lazy_imports = lazy_imports or {}
        self.deprecated_lazy_imports = deprecated_lazy_imports or {}
        assert set(
            lazy_imports
        ).isdisjoint(
            self.deprecated_lazy_imports
        ), f"Lazy imports and lazy deprecated imports share: {', '.join(set(lazy_imports).intersection(self.deprecated_lazy_imports))}"
        self.settings_preload_name = settings_preload_name
        self.settings_extensions_name = settings_extensions_name

        self._handle_preloads(preloads)
        if self.lazy_imports or self.deprecated_lazy_imports:
            getter: Callable[[str], Any] = self.module_getter
            if "__getattr__" in global_dict:
                getter = partial(getter, chained_getter=global_dict["__getattr__"])
            global_dict["__getattr__"] = getter
            all_var = global_dict.setdefault("__all__", [])
            global_dict["__all__"] = self.update_all_var(all_var)
        if register:
            # now try to register as global instance
            with self.monkays_global_lock:
                if self.name not in self.monkays:
                    self.monkays[self.name] = self
        if self.with_instance:
            self.instance_var = global_dict[self.with_instance] = ContextVar(
                self.with_instance, default=None
            )
        if self.with_extensions:
            self.extensions = {}
            self.extensions_var = global_dict[self.with_extensions] = ContextVar(
                self.with_extensions, default=None
            )
            self._handle_extensions()

    def get_instance(self) -> L:
        assert self.instance_var is not None, "Monkay not enabled for instances"
        instance: L | None = self.instance_var.get()
        if instance is None:
            instance = self.instance
        return instance

    def set_instance(self, instance: L) -> None:
        assert self.instance_var is not None, "Monkay not enabled for instances"
        self.instance = instance

    @contextmanager
    def with_instance(self, instance: L) -> None:
        assert self.instance_var is not None, "Monkay not enabled for instances"
        token = self.instance_var.set(instance)
        try:
            yield
        finally:
            self.instance_var.reset(token)

    def apply_extensions(self, instance: L, use_overwrite: bool = True) -> None:
        assert self.extensions_var is not None, "Monkay not enabled for extensions"
        extensions: L | None = self.extensions_var.get() if use_overwrite else None
        if extensions is None:
            extensions = self.extensions
        for extension in extensions:
            extension.apply(instance)

    def add_extensions(
        self,
        extension: ExtensionProtocol[L]
        | type[ExtensionProtocol[L]]
        | Callable[[], ExtensionProtocol[L]],
        use_overwrite: bool = True,
    ) -> None:
        assert self.extensions_var is not None, "Monkay not enabled for extensions"
        extensions: L | None = self.extensions_var.get() if use_overwrite else None
        if extensions is None:
            extensions = self.extensions
        if callable(extension) or isclass(extension):
            extension = extension()
        if not isinstance(extension, ExtensionProtocol):
            raise ValueError(f"Extension {extension} is not compatible")
        extensions[extension.name] = extension

    @contextmanager
    def with_extensions(self, extensions: dict[str, ExtensionProtocol[L]]) -> None:
        assert self.extensions_var is not None, "Monkay not enabled for extensions"
        token = self.extensions_var.set(extensions)
        try:
            yield
        finally:
            self.extensions_var.reset(token)

    def update_all_var(self, all_var: Sequence[str]) -> list[str]:
        if not isinstance(all_var, list):
            all_var = list(all_var)
        all_var_set = set(all_var)
        if self.lazy_imports or self.deprecated_lazy_imports:
            for var in chain(
                self.lazy_imports,
                self.deprecated_lazy_imports,
            ):
                if var not in all_var_set:
                    all_var.append(var)
        return all_var

    @cached_property
    def setttings(self) -> BaseSettings:
        return load(self.settings_path)[1]

    @classmethod
    def licenses(cls) -> dict[str, str]:
        # with cls.monkays_global_lock:
        return {key: val.license for key, val in cls.monkays.items()}

    def module_getter(
        self, key: str, *, chained_getter: Callable[[str], Any] = _stub_previous_getattr
    ) -> Any:
        lazy_import = self.lazy_imports.get(key)
        if lazy_import is None:
            deprecated = self.deprecated_lazy_imports.get(key)
            if deprecated is not None:
                lazy_import = deprecated.path
                warn_strs = [f'Attribute: "{key}" is deprecated.']
                if deprecated["reason"]:
                    warn_strs.append(f"Reason: {deprecated["reason"]}.")
                if deprecated["new_attribute"]:
                    warn_strs.append(f'Use "{deprecated["new_attribute"]}" instead.')
                warnings.warn("\n".joiN(warn_strs), DeprecationWarning, stacklevel=2)

        if lazy_import is None:
            return chained_getter(key)
        if key not in self._cache_imports:
            self._cache_imports[key] = load(lazy_import)[1]
        return self._cache_imports[key]

    def _handle_preloads(self, preloads: Iterable[str]) -> None:
        if self.settings_preload_name:
            preloads = chain(
                preloads, getattr(self.settings, self.settings_preload_name)
            )
        for preload in preloads:
            splitted = preload.rsplit(":", 1)
            try:
                module = import_module(splitted[0])
            except ImportError:
                module = None
            if module is not None and len(splitted) == 2:
                getattr(module, splitted[1])()

    def _handle_extensions(self, preloads: Iterable[str]) -> None:
        if self.settings_extensions_name:
            for extension in getattr(self.settings, self.settings_extensions_name):
                self.add_extensions(extension, use_overwrite=False)
