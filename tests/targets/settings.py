from typing import Any

from pydantic_settings import BaseSettings

from monkay import load


class SettingsExtension:
    name: str = "settings_extension2"

    def apply(self, app: Any) -> None:
        print(f"{self.name} called")


class Settings(BaseSettings):
    preloads: list[str] = ["tests.targets.module_preloaded1"]
    extensions: list[Any] = [
        lambda: load("tests.targets.extension:Extension")(name="settings_extension1"),
        SettingsExtension,
    ]


hurray = Settings()
