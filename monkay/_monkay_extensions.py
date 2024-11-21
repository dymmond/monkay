from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from inspect import isclass
from typing import TYPE_CHECKING, Any, Generic, Literal, cast

from .types import INSTANCE, SETTINGS, ExtensionProtocol

if TYPE_CHECKING:
    from .core import Monkay


class MonkayExtensions(Generic[INSTANCE, SETTINGS]):
    # extensions are pretended to always exist, we check the _extensions_var
    _extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]]
    _extensions_var: None | ContextVar[None | dict[str, ExtensionProtocol[INSTANCE, SETTINGS]]] = (
        None
    )
    # pretend it always exists
    _extensions_applied_var: ContextVar[set[str] | None]
    extension_order_key_fn: None | Callable[[ExtensionProtocol[INSTANCE, SETTINGS]], Any]
    # in truth a property
    instance: INSTANCE | None

    def apply_extensions(self, *, use_overwrite: bool = True) -> None:
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
                # despite slightly inaccurate (added before applying actually) this ensures that no loops appear
                extensions_applied.add(name)
                extension.apply(cast("Monkay[INSTANCE, SETTINGS]", self))
        finally:
            self._extensions_applied_var.reset(token)

    def ensure_extension(
        self, name_or_extension: str | ExtensionProtocol[INSTANCE, SETTINGS]
    ) -> None:
        assert self._extensions_var is not None, "Monkay not enabled for extensions."
        extensions_applied = self._extensions_applied_var.get()
        assert extensions_applied is not None, "Applying extensions not active."
        extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None = (
            self._extensions_var.get()
        )
        if extensions is None:
            extensions = self._extensions
        if isinstance(name_or_extension, str):
            name = name_or_extension
            extension = extensions.get(name)
        elif not isclass(name_or_extension) and isinstance(name_or_extension, ExtensionProtocol):
            name = name_or_extension.name
            extension = extensions.get(name, name_or_extension)
        else:
            raise RuntimeError(
                'Provided extension "{name_or_extension}" does not implement the ExtensionProtocol'
            )
        if name in extensions_applied:
            return

        if extension is None:
            raise RuntimeError(f'Extension: "{name}" does not exist.')
        # despite slightly inaccurate (added before applying actually) this ensures that no loops appear
        extensions_applied.add(name)
        extension.apply(cast("Monkay[INSTANCE, SETTINGS]", self))

    def add_extension(
        self,
        extension: ExtensionProtocol[INSTANCE, SETTINGS]
        | type[ExtensionProtocol[INSTANCE, SETTINGS]]
        | Callable[[], ExtensionProtocol[INSTANCE, SETTINGS]],
        *,
        use_overwrite: bool = True,
        on_conflict: Literal["error", "keep", "replace"] = "error",
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
        if extension.name in extensions:
            if on_conflict == "error":
                raise KeyError(f'Extension "{extension.name}" already exists.')
            elif on_conflict == "keep":
                return
        extensions[extension.name] = extension

    @contextmanager
    def with_extensions(
        self,
        extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None,
        *,
        apply_extensions: bool = False,
    ) -> Generator[dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None]:
        # why None, for temporary using the real extensions
        assert self._extensions_var is not None, "Monkay not enabled for extensions"
        token = self._extensions_var.set(extensions)
        try:
            if apply_extensions and self.instance is not None:
                self.apply_extensions()
            yield extensions
        finally:
            self._extensions_var.reset(token)
