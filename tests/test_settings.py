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
