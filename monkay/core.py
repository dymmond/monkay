from __future__ import annotations

import warnings
from collections.abc import Callable, Generator, Iterable
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from typing import (
    Any,
    Generic,
    Literal,
    cast,
)

from ._monkay_exports import MonkayExports
from ._monkay_instance import MonkayInstance
from ._monkay_settings import MonkaySettings
from .base import Undefined, UnsetError, evaluate_preloads, get_value_from_settings
from .types import (
    INSTANCE,
    PRE_ADD_LAZY_IMPORT_HOOK,
    SETTINGS,
    SETTINGS_DEFINITION_TYPE,
    DeprecatedImport,
    EvaluateSettingsParameters,
    ExtensionProtocol,
)


class Monkay(
    MonkayInstance[INSTANCE, SETTINGS],
    MonkaySettings[SETTINGS],
    MonkayExports,
    Generic[INSTANCE, SETTINGS],
):
    """
    A comprehensive class that combines instance, settings, and export management for a module.

    This class provides a unified interface for managing module instances, settings, and exports.
    It integrates lazy imports, deprecated imports, settings loading, and instance management.
    """

    def __init__(
        self,
        globals_dict: dict,
        *,
        with_instance: str | bool = False,
        with_extensions: str | bool = False,
        extension_order_key_fn: None
        | Callable[[ExtensionProtocol[INSTANCE, SETTINGS]], Any] = None,
        settings_path: SETTINGS_DEFINITION_TYPE | Literal[False] = None,
        preloads: Iterable[str] = (),
        settings_preloads_name: str = "",
        settings_extensions_name: str = "",
        uncached_imports: Iterable[str] = (),
        lazy_imports: dict[str, str | Callable[[], Any]] | None = None,
        deprecated_lazy_imports: dict[str, DeprecatedImport] | None = None,
        settings_ctx_name: str = "monkay_settings_ctx",
        extensions_applied_ctx_name: str = "monkay_extensions_applied_ctx",
        skip_all_update: bool = False,
        skip_getattr_fixup: bool = False,
        evaluate_settings: None = None,
        ignore_settings_import_errors: bool = True,
        pre_add_lazy_import_hook: None | PRE_ADD_LAZY_IMPORT_HOOK = None,
        post_add_lazy_import_hook: None | Callable[[str], None] = None,
        ignore_preload_import_errors: bool = True,
        package: str | None = "",
    ) -> None:
        """
        Initializes a Monkay instance.

        This method sets up the Monkay instance with the provided configurations, including
        instance management, settings loading, lazy imports, and extension handling.

        Args:
            globals_dict: The module's globals dictionary.
            with_instance: If True, enables instance management with a default context variable name.
                           If a string, uses the provided name for the context variable.
            with_extensions: If True, enables extension management with a default context variable name.
                             If a string, uses the provided name for the context variable.
            extension_order_key_fn: An optional function to define the order in which extensions are applied.
            settings_path: The path to the settings object, a callable, a settings instance, or a settings class.
                           If False or None, settings are disabled.
            preloads: An iterable of preload paths to execute before initialization.
            settings_preloads_name: The name used to identify preload settings.
            settings_extensions_name: The name used to identify extension settings.
            uncached_imports: An iterable of import names that should not be cached.
            lazy_imports: A dictionary of lazy imports.
            deprecated_lazy_imports: A dictionary of deprecated lazy imports.
            settings_ctx_name: The name of the settings context variable.
            extensions_applied_ctx_name: The name of the extensions applied context variable.
            skip_all_update: If True, skips updating the `__all__` variable.
            skip_getattr_fixup: If True, skips fixing the missing `__dir__` function.
            evaluate_settings: Deprecated parameter.
            ignore_settings_import_errors: If True, ignores settings import errors.
            pre_add_lazy_import_hook: A hook to modify lazy import definitions before they are added.
            post_add_lazy_import_hook: A hook to execute after a lazy import is added.
            ignore_preload_import_errors: If True, ignores preload import errors.
            package: The package name to use for relative imports.
        """
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
        self.pre_add_lazy_import_hook = pre_add_lazy_import_hook
        self.post_add_lazy_import_hook = post_add_lazy_import_hook
        self.uncached_imports = set(uncached_imports)
        self.lazy_imports = {}
        self.deprecated_lazy_imports = {}
        if lazy_imports:
            for name, lazy_import in lazy_imports.items():
                self.add_lazy_import(name, lazy_import, no_hooks=True)
        if deprecated_lazy_imports:
            for name, deprecated_import in deprecated_lazy_imports.items():
                self.add_deprecated_lazy_import(name, deprecated_import, no_hooks=True)
        if settings_path is not None and settings_path is not False:
            self._settings_var = globals_dict[settings_ctx_name] = ContextVar(
                settings_ctx_name, default=None
            )
            self.settings = settings_path  # type: ignore
        self.settings_preloads_name = settings_preloads_name
        self.settings_extensions_name = settings_extensions_name

        if with_instance:
            self._instance_var = globals_dict[with_instance] = ContextVar(
                with_instance, default=None
            )
        if with_extensions:
            self.extension_order_key_fn = extension_order_key_fn
            self._extensions = {}
            self._extensions_var = globals_dict[with_extensions] = ContextVar(
                with_extensions, default=None
            )
            self._extensions_applied_var = globals_dict[extensions_applied_ctx_name] = ContextVar(
                extensions_applied_ctx_name, default=None
            )
        if not skip_all_update and (self.lazy_imports or self.deprecated_lazy_imports):
            all_var = globals_dict.setdefault("__all__", [])
            globals_dict["__all__"] = self.update_all_var(all_var)
        # fix missing __dir__ in case only __getattr__ was specified and __dir__ not
        # it assumes the __all__ var is correct
        if (
            not skip_getattr_fixup
            and "__all__" in globals_dict
            and "__getattr__" in globals_dict
            and "__dir__" not in globals_dict
        ):
            self._init_global_dir_hook()
        self.evaluate_preloads(preloads, ignore_import_errors=ignore_preload_import_errors)
        if evaluate_settings is not None:
            raise Exception(
                "This feature and the evaluate_settings parameter are removed in monkay 0.3"
            )

    def clear_caches(self, settings_cache: bool = True, import_cache: bool = True) -> None:
        """
        Clears the settings and import caches.

        This method clears the cached settings and/or import objects, forcing them to be reloaded
        on next access.

        Args:
            settings_cache: If True, clears the settings cache.
            import_cache: If True, clears the import cache.
        """
        if settings_cache:
            del self.settings
        if import_cache:
            self._cached_imports.clear()

    def evaluate_preloads(
        self,
        preloads: Iterable[str],
        *,
        ignore_import_errors: bool = True,
        package: str | None = None,
    ) -> bool:
        """
        Evaluates preload modules or functions specified in settings.

        This method delegates to the `evaluate_preloads` function, using the Monkay instance's
        package if no package is provided.

        Args:
            preloads: An iterable of preload paths, in the format "module" or "module:function".
            ignore_import_errors: If True, ignores import errors and continues processing.
            package: The package name to use as a context for relative imports.

        Returns:
            True if all preloads were successfully evaluated, False otherwise.
        """
        return evaluate_preloads(
            preloads, ignore_import_errors=ignore_import_errors, package=package or self.package
        )

    def _evaluate_settings(
        self,
        *,
        settings: SETTINGS,
        on_conflict: Literal["error", "keep", "replace"],
        ignore_preload_import_errors: bool,
        initial_settings_evaluated: bool,
    ) -> None:
        """
        Internal method to evaluate settings preloads and extensions.

        This method evaluates the preloads and extensions specified in the settings object.

        Args:
            settings: The settings object to evaluate.
            on_conflict: Specifies how to handle conflicts when adding extensions.
            ignore_preload_import_errors: If True, ignores preload import errors.
            initial_settings_evaluated: The initial state of the settings evaluation flag.

        Raises:
            Exception: If an error occurs during evaluation and initial settings evaluation was False.
        """
        self.settings_evaluated = True

        try:
            if self.settings_preloads_name:
                settings_preloads = get_value_from_settings(settings, self.settings_preloads_name)
                self.evaluate_preloads(
                    settings_preloads, ignore_import_errors=ignore_preload_import_errors
                )
            if self.settings_extensions_name:
                for extension in get_value_from_settings(settings, self.settings_extensions_name):
                    self.add_extension(extension, use_overwrite=True, on_conflict=on_conflict)
        except Exception as exc:
            if not initial_settings_evaluated:
                self.settings_evaluated = False
            raise exc

    def evaluate_settings(
        self,
        *,
        on_conflict: Literal["error", "keep", "replace"] = "error",
        ignore_import_errors: bool = False,
        ignore_preload_import_errors: bool = True,
        onetime: bool = True,
    ) -> bool:
        """
        Evaluates settings preloads and extensions.

        This method evaluates the preloads and extensions specified in the settings object.

        Args:
            on_conflict: Specifies how to handle conflicts when adding extensions.
            ignore_import_errors: If True, ignores settings import errors.
            ignore_preload_import_errors: If True, ignores preload import errors.
            onetime: If True, evaluates settings only once.

        Returns:
            True if settings were successfully evaluated, False otherwise.
        """
        initial_settings_evaluated = self.settings_evaluated
        if onetime and initial_settings_evaluated:
            return True
        # don't access settings when there is nothing to evaluate
        if not self.settings_preloads_name and not self.settings_extensions_name:
            self.settings_evaluated = True
            return True

        try:
            # load settings one time and before setting settings_evaluated to True
            settings = self.settings
        except Exception as exc:
            if ignore_import_errors and isinstance(exc, (UnsetError, ImportError, AttributeError)):
                return False
            raise exc
        self._evaluate_settings(
            on_conflict=on_conflict,
            settings=settings,
            ignore_preload_import_errors=ignore_preload_import_errors,
            initial_settings_evaluated=initial_settings_evaluated,
        )
        return True

    def evaluate_settings_once(
        self,
        *,
        on_conflict: Literal["error", "keep", "replace"] = "error",
        ignore_import_errors: bool = True,
    ) -> bool:
        """
        Evaluates settings preloads and extensions once. (Deprecated)

        This method is deprecated and now equivalent to `evaluate_settings(onetime=True)`.

        Args:
            on_conflict: Specifies how to handle conflicts when adding extensions.
            ignore_import_errors: If True, ignores settings import errors.

        Returns:
            True if settings were successfully evaluated, False otherwise.
        """
        warnings.warn(
            "`evaluate_settings_once` is deprecated. Use `evaluate_settings` instead. It has now the same functionality.",
            stacklevel=2,
        )
        return self.evaluate_settings(
            on_conflict=on_conflict, ignore_import_errors=ignore_import_errors, onetime=True
        )

    @contextmanager
    def with_full_overwrite(
        self,
        *,
        extensions: dict[str, ExtensionProtocol[INSTANCE, SETTINGS]]
        | None
        | type[Undefined] = Undefined,
        settings: SETTINGS_DEFINITION_TYPE | Literal[False] | type[Undefined] = Undefined,
        instance: INSTANCE | None | type[Undefined] = Undefined,
        apply_extensions: bool = False,
        evaluate_settings_with: EvaluateSettingsParameters | None = None,
    ) -> Generator[None]:
        """
        Apply all overwrites in the correct order. Useful for testing or sub-environments
        """
        ctx_extensions = (
            nullcontext()
            if extensions is Undefined
            else self.with_extensions(
                cast("dict[str, ExtensionProtocol[INSTANCE, SETTINGS]] | None", extensions),
                apply_extensions=False,
            )
        )
        ctx_settings = (
            nullcontext()
            if settings is Undefined
            else self.with_settings(
                cast("SETTINGS_DEFINITION_TYPE | Literal[False]", settings),
                evaluate_settings_with=None,
            )
        )
        ctx_instance = (
            nullcontext()
            if instance is Undefined
            else self.with_instance(
                cast("INSTANCE | None", instance),
                apply_extensions=False,
            )
        )

        with (
            ctx_extensions,
            ctx_settings,
            ctx_instance,
        ):
            # evaluate here because the ctxmanagers have not the information from the contextvars
            # evaluate settings also without settings instance
            if evaluate_settings_with is not None and evaluate_settings_with is not False:
                if evaluate_settings_with is True:
                    evaluate_settings_with = {}
                self.evaluate_settings(**evaluate_settings_with)
            # apply extensions also without extra instance
            if apply_extensions and self._extensions_var is not None:
                self.apply_extensions()
            yield
