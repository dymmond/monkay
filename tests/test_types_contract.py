from __future__ import annotations

from monkay.types import DeprecatedImport


def test_deprecated_import_requires_path_key() -> None:
    """Keep TypedDict runtime metadata aligned with documented schema."""
    assert DeprecatedImport.__required_keys__ == frozenset({"path"})
