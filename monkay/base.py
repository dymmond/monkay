from __future__ import annotations

import warnings
from collections.abc import Collection
from importlib import import_module
from typing import Any


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


class InGlobalsDict(Exception):
    pass


def get_value_from_settings(settings: Any, name: str) -> Any:
    try:
        return getattr(settings, name)
    except AttributeError:
        return settings[name]
