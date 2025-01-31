import sys
from pathlib import Path

import pytest

from monkay import UnsetError


@pytest.fixture(autouse=True, scope="function")
def cleanup():
    for p in (Path(__file__).parent / "targets").iterdir():
        sys.modules.pop(f"tests.targets.{p.stem}", None)
    yield


def test_settings_basic():
    import tests.targets.module_full as mod
    from tests.targets.settings import Settings, hurray

    new_settings = Settings(preloads=[], extensions=[])

    old_settings = mod.monkay.settings
    settings_path = mod.monkay._settings_definition
    assert isinstance(settings_path, str)
    assert mod.monkay.settings is old_settings
    mod.monkay.settings = new_settings
    assert mod.monkay.settings is new_settings

    mod.monkay.settings = lambda: old_settings
    assert mod.monkay.settings is old_settings
    # auto generated settings
    mod.monkay.settings = Settings
    mod.monkay.settings = "tests.targets.settings:hurray"
    assert mod.monkay.settings is hurray


def test_disabled_settings():
    import tests.targets.module_disabled_settings as mod

    with pytest.raises(AssertionError):
        mod.monkay.evaluate_settings()

    with pytest.raises(AssertionError):
        mod.monkay.settings  # noqa


def test_notfound_settings():
    import tests.targets.module_notfound_settings as mod

    assert not mod.monkay.settings_evaluated

    mod.monkay.evaluate_settings(ignore_import_errors=True)
    assert not mod.monkay.settings_evaluated

    with pytest.raises(ImportError):
        mod.monkay.evaluate_settings()


def test_notevaluated_settings():
    import tests.targets.module_notevaluated_settings as mod

    assert mod.monkay.settings_evaluated

    mod.monkay.evaluate_settings()
    mod.monkay.evaluate_settings(ignore_import_errors=False)

    # now evaluate settings
    with pytest.raises(ImportError):
        mod.monkay.settings  # noqa


@pytest.mark.parametrize("value", [False, None, ""])
def test_unset_settings(value):
    import tests.targets.module_full as mod

    mod.monkay.settings = value

    mod.monkay.evaluate_settings(ignore_import_errors=True)
    with pytest.raises(UnsetError):
        mod.monkay.evaluate_settings()

    with pytest.raises(UnsetError):
        mod.monkay.settings  # noqa


def test_settings_overwrite():
    import tests.targets.module_full as mod

    assert mod.monkay.settings_evaluated

    old_settings = mod.monkay.settings
    settings_path = mod.monkay._settings_definition
    assert isinstance(settings_path, str)

    assert "tests.targets.module_settings_preloaded" not in sys.modules
    new_settings = old_settings.model_copy(
        update={"preloads": ["tests.targets.module_settings_preloaded"]}
    )
    with mod.monkay.with_settings(new_settings) as yielded:
        assert not mod.monkay.settings_evaluated
        assert mod.monkay.settings is new_settings
        assert mod.monkay.settings is yielded
        assert mod.monkay.settings is not old_settings
        assert "tests.targets.module_settings_preloaded" not in sys.modules
        mod.monkay.evaluate_settings(onetime=False, on_conflict="keep")
        assert mod.monkay.settings_evaluated
        # assert no evaluation anymore
        old_evaluate_settings = mod.monkay._evaluate_settings

        def fake_evaluate():
            raise

        mod.monkay._evaluate_settings = fake_evaluate
        assert mod.monkay.evaluate_settings()
        mod.monkay._evaluate_settings = old_evaluate_settings
        assert "tests.targets.module_settings_preloaded" in sys.modules

        # overwriting settings doesn't affect temporary scope
        mod.monkay.settings = mod.monkay._settings_definition
        assert mod.monkay.settings is new_settings

        # now access the non-temporary settings
        with mod.monkay.with_settings(None):
            assert mod.monkay.settings is not new_settings
            assert mod.monkay.settings is not old_settings


@pytest.mark.parametrize("transform", [lambda x: x, lambda x: x.model_dump()])
@pytest.mark.parametrize("mode", ["error", "replace", "keep"])
def test_settings_overwrite_evaluate_modes(mode, transform):
    import tests.targets.module_full as mod

    with mod.monkay.with_settings(
        transform(
            mod.monkay.settings.model_copy(
                update={"preloads": ["tests.targets.module_settings_preloaded"]}
            )
        )
    ) as new_settings:
        assert new_settings is not None
        if mode == "error":
            with pytest.raises(KeyError):
                mod.monkay.evaluate_settings(on_conflict=mode, onetime=False)
        else:
            mod.monkay.evaluate_settings(on_conflict=mode, onetime=False)


@pytest.mark.parametrize("transform", [lambda x: x, lambda x: x.model_dump()])
def test_settings_overwrite_evaluate_no_conflict(transform):
    import tests.targets.module_full as mod

    with mod.monkay.with_settings(
        transform(
            mod.monkay.settings.model_copy(
                update={
                    "preloads": ["tests.targets.module_settings_preloaded"],
                    "extensions": [],
                }
            )
        )
    ) as new_settings:
        assert new_settings is not None
        mod.monkay.evaluate_settings(on_conflict="error", onetime=False)
