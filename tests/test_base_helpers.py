from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from monkay.base import absolutify_import, evaluate_preloads, load


@pytest.fixture(autouse=True)
def cleanup_dynamic_modules():
    module_names = {"tests.targets.dynamic_preload_mod", "tests.targets.dynamic_loader_mod"}
    for module_name in module_names:
        sys.modules.pop(module_name, None)
    yield
    for module_name in module_names:
        sys.modules.pop(module_name, None)


def test_evaluate_preloads_calls_named_preload_function() -> None:
    calls: list[str] = []
    module = ModuleType("tests.targets.dynamic_preload_mod")

    def initialize() -> None:
        calls.append("initialized")

    module.initialize = initialize
    sys.modules[module.__name__] = module

    assert evaluate_preloads([f"{module.__name__}:initialize"], ignore_import_errors=False)
    assert calls == ["initialized"]


def test_evaluate_preloads_reports_missing_module_without_raising_when_ignored() -> None:
    assert not evaluate_preloads(
        ["tests.targets.does_not_exist_module"], ignore_import_errors=True
    )


def test_evaluate_preloads_raises_for_missing_module_when_not_ignored() -> None:
    with pytest.raises(ImportError):
        evaluate_preloads(["tests.targets.does_not_exist_module"], ignore_import_errors=False)


def test_load_errors_include_circular_import_hint_when_module_initializing() -> None:
    module = ModuleType("tests.targets.dynamic_loader_mod")
    module.__spec__ = SimpleNamespace(_initializing=True)  # type: ignore[assignment]
    sys.modules[module.__name__] = module

    with pytest.raises(ImportError, match="circular import"):
        load(f"{module.__name__}:missing")


@pytest.mark.parametrize(
    "import_path, package, expected",
    [
        ("module.path", "tests.targets", "module.path"),
        (".module", "tests.targets", "tests.targets.module"),
        ("..module", "tests.targets.child", "tests.targets.module"),
    ],
)
def test_absolutify_import_success(import_path: str, package: str, expected: str) -> None:
    assert absolutify_import(import_path, package) == expected


@pytest.mark.parametrize(
    "import_path, package",
    [
        ("....module", "tests.targets"),
    ],
)
def test_absolutify_import_invalid_paths(import_path: str, package: str) -> None:
    with pytest.raises(ValueError):
        absolutify_import(import_path, package)


def test_absolutify_import_returns_empty_path_when_import_path_is_empty() -> None:
    assert absolutify_import("", "tests.targets") == ""
