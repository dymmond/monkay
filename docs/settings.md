# Settings

## Setting settings forward

Sometimes you have some packages which should work independently but
in case of a main package the packages should use the settings of the main package.

For this monkay settings have a forwarding mode, in which the cache is disabled.
It can be enabled by either setting the settings parameter to a function (most probably less common)
or simply assigning a callable to the monkay settings property.
It is expected that the assigned function returns a suitable settings object.


Child

``` python
import os
from monkay import Monkay

monkay = Monkay(
    globals(),
    settings_path=os.environ.get("MONKAY_CHILD_SETTINGS", "foo.test:example") or ""
)
```

Main

``` python
import os
import child

monkay = Monkay(
    globals(),
    settings_path=os.environ.get("MONKAY_MAIN_SETTINGS", "foo.test:example") or ""
)
child.monkay.settings = lambda: monkay.settings
```

## Lazy settings setup

Like when using a settings forward it is possible to activate the settings later by assigning a string, a class or an settings instance
to the settings attribute.
For this provide an empty string to the settings_path variable.
It ensures the initialization takes place.

``` python
import os
from monkay import Monkay

monkay = Monkay(
    globals(),
    # required for initializing settings
    settings_path=""
    evaluate_settings=False
)

# somewhere later

if not os.environ.get("DEBUG"):
    monkay.settings = os.environ.get("MONKAY_MAIN_SETTINGS", "foo.test:example") or ""
elif os.environ.get("PERFORMANCE"):
    # you can also provide a class
    monkay.settings = DebugSettings
else:
    monkay.settings = DebugSettings()

# now the settings are applied
monkay.evaluate_settings()
```

### `evaluate_settings` parameters

`evaluate_settings` has following keyword only parameter:

- on_conflict: matches the values of add_extension but defaults to `keep`

## Other settings types

All of the assignment examples are also possible as settings_path parameter.
When assigning a string or a class, the initialization happens on the first access to the settings
attribute and are cached.
Functions get evaluated on every access and should care for caching in case it is required (for forwards the caching
takes place in the main settings).

## Forwarder

Sometimes you have an old settings place and want to forward it to the monkay one.
Here does no helper exist but a forwarder is easy to write:

``` python
from typing import Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from .global_settings import EdgySettings


class SettingsForward:
    def __getattribute__(self, name: str) -> Any:
        import edgy

        return getattr(edgy.monkay.settings, name)

# we want to pretend the forward is the real object
settings = cast("EdgySettings", SettingsForward())

__all__ = ["settings"]

```
