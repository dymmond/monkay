from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from .global_settings import EdgySettings


class SettingsForward:
    def __getattribute__(self, name: str) -> Any:
        import edgy

        return getattr(edgy.monkay.settings, name)


# Pretend the forward is the real object
settings = cast("EdgySettings", SettingsForward())

__all__ = ["settings"]
