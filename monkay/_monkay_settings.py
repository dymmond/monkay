from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cached_property
from inspect import isclass
from typing import Generic, cast

from .base import UnsetError, load
from .types import SETTINGS


class MonkaySettings(Generic[SETTINGS]):
    """
    Manages settings for a Monkay instance, providing functionality to load, evaluate, and access settings.
    """

    package: str | None
    """
    The package name associated with the Monkay instance.
    This attribute is used to resolve relative import paths within settings definitions.
    """

    _settings_evaluated: bool = False
    """
    A flag indicating whether the settings have been evaluated and loaded.
    This flag prevents redundant loading and evaluation of settings.
    """

    settings_preloads_name: str
    """
    The name used to identify preload settings within the settings definition.
    This attribute specifies the key used to access preload configurations.
    """

    settings_extensions_name: str
    """
    The name used to identify extension settings within the settings definition.
    This attribute specifies the key used to access extension configurations.
    """

    _settings_var: ContextVar[tuple[SETTINGS, list[bool]] | None] | None = None
    """
    A context variable that allows temporary overriding of the loaded settings.
    This variable enables context-specific settings manipulation, allowing for temporary
    replacement or modification of the underlying settings.
    """

    _settings_definition: SETTINGS | type[SETTINGS] | str | Callable[[], SETTINGS] | None = None
    """
    The definition of the settings, which can be a settings instance, a settings class,
    a string representing a settings path, or a callable that returns a settings instance.
    This attribute provides flexibility in how settings are defined and loaded.
    """

    @cached_property
    def _loaded_settings(self) -> SETTINGS | None:
        """
        Loads and returns the settings based on the settings definition.

        This cached property loads the settings object from the provided definition.
        It handles settings definitions that are classes, string paths, or None.

        Returns:
            The loaded settings object, or None if no settings definition is provided.
        Raises:
            AssertionError: if the _settings_definition is not a class or a string.
        """
        # only class and string pathes
        if isclass(self._settings_definition):
            return self._settings_definition()
        assert isinstance(
            self._settings_definition, str
        ), f"Not a settings object: {self._settings_definition}"
        if not self._settings_definition:
            return None
        settings: SETTINGS | type[SETTINGS] = load(self._settings_definition, package=self.package)
        if isclass(settings):
            settings = settings()
        return cast(SETTINGS, settings)

    @property
    def settings_evaluated(self) -> bool:
        """
        Checks if the settings have been evaluated and loaded.

        This property returns a boolean indicating whether the settings have been evaluated.
        It checks both the global settings evaluation flag and the context-specific flag.

        Returns:
            True if the settings have been evaluated, False otherwise.

        Raises:
            AssertionError: If Monkay is not enabled for settings.
        """
        assert self._settings_var is not None, "Monkay not enabled for settings"
        _settings_var = self._settings_var.get()
        if _settings_var is None:
            return self._settings_evaluated
        else:
            return _settings_var[1][0]

    @settings_evaluated.setter
    def settings_evaluated(self, value: bool) -> None:
        """
        Sets the settings evaluation flag.

        This setter method updates the settings evaluation flag, indicating whether the settings have been loaded.
        It updates both the global evaluation flag and the context-specific flag.

        Args:
            value: The boolean value to set.

        Raises:
            AssertionError: If Monkay is not enabled for settings.
        """
        assert self._settings_var is not None, "Monkay not enabled for settings"
        _settings_var = self._settings_var.get()
        if _settings_var is None:
            self._settings_evaluated = value
        else:
            _settings_var[1][0] = value

    @property
    def settings(self) -> SETTINGS:
        """
        Retrieves the settings object.

        This property returns the settings object associated with the Monkay instance.
        It handles settings definitions that are instances, callables, or loaded from paths.

        Returns:
            The settings object.

        Raises:
            AssertionError: If Monkay is not enabled for settings.
            UnsetError: If settings are not set or the settings function returned None.
        """
        assert self._settings_var is not None, "Monkay not enabled for settings"
        _settings_var = self._settings_var.get()
        if _settings_var is not None:
            settings: SETTINGS | Callable[[], SETTINGS] | None = _settings_var[0]
        else:
            settings = None
        if settings is None:
            # when settings_path is callable bypass the cache, for forwards
            settings = (
                self._loaded_settings
                if isinstance(self._settings_definition, str) or isclass(self._settings_definition)
                else self._settings_definition
            )
        if callable(settings):
            settings = settings()
        if settings is None:
            raise UnsetError("Settings are not set yet or the settings function returned None.")
        return settings

    @settings.setter
    def settings(
        self, value: str | Callable[[], SETTINGS] | SETTINGS | type[SETTINGS] | None
    ) -> None:
        """
        Sets the settings definition for the Monkay instance.

        This setter method allows setting the settings definition, which can be a string path,
        a callable, a settings instance, a settings class, or None. It also resets the settings
        evaluation flag and clears the cached settings.

        Args:
            value: The settings definition to set.

        Raises:
            AssertionError: If Monkay is not enabled for settings.
        """
        assert self._settings_var is not None, "Monkay not enabled for settings"
        self._settings_evaluated = False
        if value is False or value is None or value == "":
            self._settings_definition = ""
            del self.settings
            return
        if not isinstance(value, str) and not callable(value) and not isclass(value):
            self._settings_definition = lambda: value
        else:
            self._settings_definition = value
        del self.settings

    @settings.deleter
    def settings(self) -> None:
        """
        Deletes the cached settings, forcing them to be reloaded on next access.

        This deleter method clears the cached settings, ensuring that the settings are reloaded
        from the definition when accessed next.
        """
        # clear cache
        self.__dict__.pop("_loaded_settings", None)

    @contextmanager
    def with_settings(self, settings: SETTINGS | None) -> Generator[SETTINGS | None]:
        """
        Temporarily sets and yields new settings for the Monkay instance within a context.

        This context manager allows temporarily overriding the settings associated with the Monkay instance.
        It yields the provided settings and then restores the original settings after the context exits.

        Args:
            settings: The new settings to use within the context, or None to temporarily use the real settings.

        Yields:
            The provided settings.

        Raises:
            AssertionError: If Monkay is not enabled for settings.
        """
        assert self._settings_var is not None, "Monkay not enabled for settings"
        # why None, for temporary using the real settings
        token = self._settings_var.set((settings, [False]) if settings is not None else None)
        try:
            yield settings
        finally:
            self._settings_var.reset(token)
