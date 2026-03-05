from __future__ import annotations

from typing import Literal, cast

ConflictMode = Literal["error", "keep", "replace"]
_VALID_CONFLICT_MODES = frozenset({"error", "keep", "replace"})


def validate_conflict_mode(value: str, *, parameter_name: str = "on_conflict") -> ConflictMode:
    """Validate an extension conflict mode value.

    This helper provides a single runtime validation point for conflict policies
    accepted by public APIs such as ``Monkay.evaluate_settings`` and
    ``Monkay.add_extension``.

    Args:
        value: Raw mode value provided by the caller.
        parameter_name: Name of the parameter used in error messages.

    Returns:
        The validated conflict mode.

    Raises:
        ValueError: If ``value`` is not one of ``"error"``, ``"keep"``, or
            ``"replace"``.
    """
    if value not in _VALID_CONFLICT_MODES:
        expected = ", ".join(sorted(f'"{mode}"' for mode in _VALID_CONFLICT_MODES))
        raise ValueError(f'Invalid {parameter_name}: "{value}". Expected one of: {expected}.')
    return cast(ConflictMode, value)
