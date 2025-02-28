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
    """
    Manages extensions for a Monkay instance, providing functionality to add, apply, and manipulate extensions.
    """

    _extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]]
    """
    A dictionary storing the registered extensions, mapping extension names to extension instances.
    This dictionary holds the base set of extensions associated with the Monkay instance.
    """

    _extensions_var: None | ContextVar[None | dict[str, ExtensionProtocol[INSTANCE, SETTINGS]]] = (
        None
    )
    """
    A context variable that allows temporary overriding of the registered extensions.
    When set, this variable holds a dictionary of extensions that take precedence over `_extensions`.
    It is used to manage extension contexts and allow for temporary extension configurations.
    """

    _extensions_applied_var: ContextVar[set[str] | None]
    """
    A context variable that tracks the set of applied extensions during the application process.
    This variable is used to prevent recursive application of extensions and ensure that each extension
    is applied only once within a given application context.
    """

    extension_order_key_fn: None | Callable[[ExtensionProtocol[INSTANCE, SETTINGS]], Any]
    """
    An optional function that defines the order in which extensions should be applied.
    If provided, this function is used to sort the extensions before application, allowing for custom
    application order based on extension properties.
    """

    instance: INSTANCE | None
    """
    A reference to the Monkay instance that these extensions are associated with.
    This attribute allows extensions to access the Monkay instance and its properties.
    """

    def apply_extensions(self, *, use_overwrite: bool = True) -> None:
        """
        Applies registered extensions to the Monkay instance.

        This method iterates through the registered extensions, applies them in the specified order,
        and manages the application process to prevent recursive or concurrent application issues.

        Args:
            use_overwrite: If True, uses the extensions from the `_extensions_var` if available;
                           otherwise, uses the default `_extensions`.
        Raises:
            AssertionError: If Monkay is not enabled for extensions.
            RuntimeError: If another extension application process is already active in the same context.
        """
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
        """
        Ensures that a specific extension is applied to the Monkay instance.

        This method checks if the given extension (either by name or instance) is already applied.
        If not, it applies the extension, preventing recursive application issues.

        Args:
            name_or_extension: The name of the extension or an instance of the extension.

        Raises:
            AssertionError: If Monkay is not enabled for extensions or if applying extensions is not active.
            RuntimeError: If the provided extension does not implement the ExtensionProtocol,
                          or if the extension does not exist.
        """
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
        """
        Adds a new extension to the Monkay instance.

        This method allows adding an extension, either as an instance, a class, or a callable that returns an instance.
        It handles conflicts based on the `on_conflict` parameter.

        Args:
            extension: The extension to add, which can be an instance, a class, or a callable.
            use_overwrite: If True, uses the extensions from the `_extensions_var` if available; otherwise, uses the default `_extensions`.
            on_conflict: Specifies how to handle conflicts when an extension with the same name already exists.
                         - "error": Raises a KeyError if a conflict occurs.
                         - "keep": Keeps the existing extension and ignores the new one.
                         - "replace": Replaces the existing extension with the new one.

        Raises:
            AssertionError: If Monkay is not enabled for extensions.
            ValueError: If the provided extension is not compatible (does not implement ExtensionProtocol).
            KeyError: If an extension with the same name already exists and `on_conflict` is set to "error".
        """
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
        """
        Temporarily sets and yields a new set of extensions for the Monkay instance.

        This method allows temporarily overriding the registered extensions within a context.
        It yields the provided extensions (or None to temporarily use the real extensions),
        and then restores the original extensions after the context exits.

        Args:
            extensions: The new set of extensions to use within the context, or None to temporarily use the real extensions.
            apply_extensions: If True, applies the temporary extensions immediately after setting them.

        Yields:
            The provided extensions (or None).

        Raises:
            AssertionError: If Monkay is not enabled for extensions.
        """
        # why None, for temporary using the real extensions
        assert self._extensions_var is not None, "Monkay not enabled for extensions"
        token = self._extensions_var.set(extensions)
        try:
            if apply_extensions and self.instance is not None:
                self.apply_extensions()
            yield extensions
        finally:
            self._extensions_var.reset(token)
