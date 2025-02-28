from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generic

from ._monkay_extensions import MonkayExtensions
from .types import INSTANCE, SETTINGS


class MonkayInstance(MonkayExtensions[INSTANCE, SETTINGS], Generic[INSTANCE, SETTINGS]):
    """
    Manages the instance associated with a Monkay object, providing context-aware instance management.
    """

    _instance: None | INSTANCE = None
    """
    The actual instance being managed by Monkay.
    This attribute holds the object that Monkay is wrapping and enhancing.
    """

    _instance_var: ContextVar[INSTANCE | None] | None = None
    """
    A context variable that allows temporary overriding of the managed instance.
    This variable enables context-specific instance manipulation, allowing for temporary
    replacement or modification of the underlying instance.
    """

    @property
    def instance(self) -> INSTANCE | None:  # type: ignore
        """
        Retrieves the current instance managed by Monkay.

        This property returns the instance associated with the Monkay object. It first checks if a context-specific
        instance is set via `_instance_var`. If not, it returns the default instance `_instance`.

        Returns:
            The current instance, or None if no instance is set.

        Raises:
            AssertionError: If Monkay is not enabled for instances.
        """
        assert self._instance_var is not None, "Monkay not enabled for instances"
        instance: INSTANCE | None = self._instance_var.get()
        if instance is None:
            instance = self._instance
        return instance

    def set_instance(
        self,
        instance: INSTANCE | None,
        *,
        apply_extensions: bool = True,
        use_extensions_overwrite: bool = True,
    ) -> INSTANCE | None:
        """
        Sets the instance managed by Monkay and optionally applies extensions.

        This method updates the instance associated with the Monkay object. It also allows applying extensions
        immediately after setting the instance.

        Args:
            instance: The new instance to set, or None to unset the instance.
            apply_extensions: If True, applies the registered extensions after setting the instance.
            use_extensions_overwrite: If True, uses the extensions from the `_extensions_var` if available;
                                       otherwise, uses the default `_extensions`.

        Returns:
            The set instance.

        Raises:
            AssertionError: If Monkay is not enabled for instances.
            RuntimeError: If another extension application process is already active in the same context.
        """
        assert self._instance_var is not None, "Monkay not enabled for instances"
        # need to address before the instance is swapped
        if (
            apply_extensions
            and self._extensions_var is not None
            and self._extensions_applied_var.get() is not None
        ):
            raise RuntimeError("Other apply process in the same context is active.")
        self._instance = instance
        if apply_extensions and instance is not None and self._extensions_var is not None:
            # unapply a potential instance overwrite
            with self.with_instance(None):
                self.apply_extensions(use_overwrite=use_extensions_overwrite)
        return instance

    @contextmanager
    def with_instance(
        self,
        instance: INSTANCE | None,
        *,
        apply_extensions: bool = False,
        use_extensions_overwrite: bool = True,
    ) -> Generator[INSTANCE | None]:
        """
        Temporarily sets and yields a new instance for the Monkay object within a context.

        This context manager allows temporarily overriding the instance associated with the Monkay object.
        It yields the provided instance and then restores the original instance after the context exits.

        Args:
            instance: The new instance to use within the context, or None to temporarily unset the instance.
            apply_extensions: If True, applies the registered extensions after setting the instance.
            use_extensions_overwrite: If True, uses the extensions from the `_extensions_var` if available;
                                       otherwise, uses the default `_extensions`.

        Yields:
            The provided instance.

        Raises:
            AssertionError: If Monkay is not enabled for instances.
            RuntimeError: If another extension application process is already active in the same context.
        """
        assert self._instance_var is not None, "Monkay not enabled for instances"
        # need to address before the instance is swapped
        if (
            apply_extensions
            and self._extensions_var is not None
            and self._extensions_applied_var.get() is not None
        ):
            raise RuntimeError("Other apply process in the same context is active.")
        token = self._instance_var.set(instance)
        try:
            if apply_extensions and self._extensions_var is not None:
                self.apply_extensions(use_overwrite=use_extensions_overwrite)
            yield instance
        finally:
            self._instance_var.reset(token)
