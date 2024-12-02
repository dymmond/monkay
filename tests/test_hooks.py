import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="function")
def cleanup():
    for p in (Path(__file__).parent / "targets").iterdir():
        sys.modules.pop(f"tests.targets.{p.stem}", None)
    yield


def test_hooks():
    import tests.targets.module_prefixed as mod

    assert "bar" in mod.__all__
    assert "deprecated" in mod.__all__


@pytest.mark.parametrize(
    "monkay_fn",
    [
        lambda m: m.add_lazy_import("bar", ".fn_module:bar", no_hooks=True),
        lambda m: m.add_deprecated_lazy_import(
            "deprecated",
            {
                "path": "tests.targets.fn_module:deprecated",
                "reason": "old.",
                "new_attribute": "super_new",
            },
            no_hooks=True,
        ),
    ],
)
def test_no_hooks_collisions(monkay_fn):
    import tests.targets.module_prefixed as mod

    with pytest.raises(KeyError):
        monkay_fn(mod.monkay)


@pytest.mark.parametrize(
    "monkay_fn,export,in_all",
    [
        (lambda m: m.add_lazy_import("bar", ".fn_module:bar"), "lazy_import_bar", True),
        (
            lambda m: m.add_deprecated_lazy_import(
                "deprecated",
                {
                    "path": "tests.targets.fn_module:deprecated",
                    "reason": "old.",
                    "new_attribute": "super_new",
                },
            ),
            "deprecated_lazy_import_deprecated",
            True,
        ),
        (
            lambda m: m.add_lazy_import(
                "bar2",
                ".fn_module:bar",
                no_hooks=True,
            ),
            "bar2",
            False,
        ),
        (
            lambda m: m.add_deprecated_lazy_import(
                "deprecated2",
                {
                    "path": "tests.targets.fn_module:deprecated",
                    "reason": "old.",
                    "new_attribute": "super_new",
                },
                no_hooks=True,
            ),
            "deprecated2",
            False,
        ),
    ],
)
def test_add(monkay_fn, export, in_all):
    import tests.targets.module_prefixed as mod

    monkay_fn(mod.monkay)
    if in_all:
        assert export in mod.__all__
    assert mod.monkay.getter(export, no_warn_deprecated=True, check_globals_dict=True) is not None


@pytest.mark.parametrize(
    "monkay_fn,export",
    [
        (lambda m: m.add_lazy_import("bar", ".fn_module:bar"), "bar"),
        (
            lambda m: m.add_deprecated_lazy_import(
                "deprecated",
                {
                    "path": "tests.targets.fn_module:deprecated",
                    "reason": "old.",
                    "new_attribute": "super_new",
                },
            ),
            "deprecated",
        ),
        (
            lambda m: m.add_lazy_import(
                "bar2",
                ".fn_module:bar",
                no_hooks=True,
            ),
            "bar2",
        ),
        (
            lambda m: m.add_deprecated_lazy_import(
                "deprecated2",
                {
                    "path": "tests.targets.fn_module:deprecated",
                    "reason": "old.",
                    "new_attribute": "super_new",
                },
                no_hooks=True,
            ),
            "deprecated2",
        ),
    ],
)
def test_none_add(monkay_fn, export):
    import tests.targets.module_none as mod

    monkay_fn(mod.monkay)
    mod.__all__ = mod.monkay.update_all_var([])
    assert export in mod.__all__
    assert (
        mod.monkay.getter(export, no_warn_deprecated=True, check_globals_dict="fail") is not None
    )
