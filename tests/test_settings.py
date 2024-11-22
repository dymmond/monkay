import sys
from pathlib import Path

import pytest


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


def test_settings_overwrite():
    import tests.targets.module_full as mod

    old_settings = mod.monkay.settings
    settings_path = mod.monkay._settings_definition
    assert isinstance(settings_path, str)

    assert "tests.targets.module_settings_preloaded" not in sys.modules
    new_settings = old_settings.model_copy(
        update={"preloads": ["tests.targets.module_settings_preloaded"]}
    )
    with mod.monkay.with_settings(new_settings) as yielded:
        assert mod.monkay.settings is new_settings
        assert mod.monkay.settings is yielded
        assert mod.monkay.settings is not old_settings
        assert "tests.targets.module_settings_preloaded" not in sys.modules
        mod.monkay.evaluate_settings()
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
                mod.monkay.evaluate_settings(on_conflict=mode)
        else:
            mod.monkay.evaluate_settings(on_conflict=mode)


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
        mod.monkay.evaluate_settings(on_conflict="error")
