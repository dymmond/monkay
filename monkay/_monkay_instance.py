from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generic

from ._monkay_extensions import MonkayExtensions
from .types import INSTANCE, SETTINGS


class MonkayInstance(MonkayExtensions[INSTANCE, SETTINGS], Generic[INSTANCE, SETTINGS]):
    _instance: None | INSTANCE = None
    _instance_var: ContextVar[INSTANCE | None] | None = None

    @property
    def instance(self) -> INSTANCE | None:  # type: ignore
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
