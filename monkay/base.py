from __future__ import annotations

import warnings
from collections.abc import Collection, Iterable
from importlib import import_module
from typing import Any


class Undefined: ...


def load(path: str, *, allow_splits: str = ":.", package: None | str = None) -> Any:
    """
    Dynamically loads an object from a module given its path.

    This function takes a string representing the path to an object within a module
    and dynamically imports the module and retrieves the object.

    Args:
        path: The path to the object, in the format "module:object" or "module.object".
        allow_splits: A string specifying the allowed separators for module and object names.
                      Defaults to ":." allowing both ":" and "." as separators.
        package: The package name to use as a context for relative imports.

    Returns:
        The loaded object.

    Raises:
        ValueError: If the path is invalid or cannot be parsed.
        ImportError: If the module cannot be imported.
        AttributeError: If the object cannot be found in the module.
    """
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
    """
    Dynamically loads any of the specified attributes from a module.

    This function takes a module path and a collection of attribute names. It attempts
    to import the module and retrieve each attribute in the given order. If any of the
    attributes are found, it returns the first one found.

    Args:
        path: The path to the module.
        attrs: A collection of attribute names to search for.
        non_first_deprecated: If True, issues deprecation warnings for all found attributes
                               except the first one.
        package: The package name to use as a context for relative imports.

    Returns:
        The first found attribute, or None if none of the attributes are found.

    Raises:
        ImportError: If the module cannot be imported or none of the attributes are found.
        DeprecationWarning: If `non_first_deprecated` is True and a non-first attribute is found.
    """
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
    """
    Converts a relative import path to an absolute import path.

    This function takes an import path and a package name and converts the relative
    import path to an absolute path by prepending the package name and adjusting
    for relative levels (e.g., "..module").

    Args:
        import_path: The import path to absolutify.
        package: The package name to use as a base for relative imports.

    Returns:
        The absolute import path.

    Raises:
        ValueError: If the import path is invalid or tries to cross parent boundaries.
    """
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


class InGlobalsDict(Exception): ...


class UnsetError(RuntimeError): ...


def get_value_from_settings(settings: Any, name: str) -> Any:
    """
    Retrieves a value from a settings object, supporting both attribute and dictionary access.

    This function attempts to retrieve a value from a settings object. It first tries to access
    the value as an attribute. If that fails, it tries to access the value as a dictionary key.

    Args:
        settings: The settings object to retrieve the value from.
        name: The name of the attribute or key to retrieve.

    Returns:
        The retrieved value.

    Raises:
        AttributeError: If the name is not found as an attribute and the settings object does not support dictionary access.
        KeyError: If the name is not found as a key in the settings object and attribute access also fails.
    """
    try:
        return getattr(settings, name)
    except AttributeError:
        return settings[name]


def evaluate_preloads(
    preloads: Iterable[str], *, ignore_import_errors: bool = True, package: str | None = None
) -> bool:
    """
    Evaluates preload modules or functions specified in settings.

    This function iterates through a collection of preload paths, imports the modules,
    and optionally calls specified functions within those modules.

    Args:
        preloads: An iterable of preload paths, in the format "module" or "module:function".
        ignore_import_errors: If True, ignores import errors and continues processing.
        package: The package name to use as a context for relative imports.

    Returns:
        True if all preloads were successfully evaluated, False otherwise.

    Raises:
        ImportError: If a module cannot be imported and `ignore_import_errors` is False.
        AttributeError: If a specified function cannot be found in a module and `ignore_import_errors` is False.
    """
    no_errors: bool = True
    for preload in preloads:
        splitted = preload.rsplit(":", 1)
        try:
            module = import_module(splitted[0], package)
        except (ImportError, AttributeError) as exc:
            if not ignore_import_errors:
                raise exc
            no_errors = False
            continue
        if len(splitted) == 2:
            getattr(module, splitted[1])()
    return no_errors
