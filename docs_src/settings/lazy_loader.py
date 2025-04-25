import os
from dataclasses import dataclass

from monkay import Monkay


@dataclass
class Settings:
    env: str


@dataclass
class ProductionSettings(Settings):
    env: str = "production"


@dataclass
class DebugSettings(Settings):
    env: str = "debug"


def lazy_loader():
    # Lazy setup based on environment variables
    if not os.environ.get("DEBUG"):
        return os.environ.get("MONKAY_MAIN_SETTINGS", "foo.test:example") or ""
    elif os.environ.get("PERFORMANCE"):
        # must be class to be cached
        return ProductionSettings
    else:
        # not a class, will evaluated always on access
        return DebugSettings()


monkay = Monkay(
    globals(),
    # Required for initializing settings feature
    settings_path=lazy_loader,
)

# Now the settings are applied
monkay.evaluate_settings()
