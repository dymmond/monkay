# Specials

## Overwriting the used package for relative imports

Provide the `package` parameter to Monkay. By default it is set to the `__spec__.parent` of the module.
For a toplevel module it is the same name like the module.

## Adding dynamically lazy imports

For adding lazy imports there are two methods:

- `add_lazy_import(export_name, path_or_fn, *, no_hooks=False)`: Adding new lazy import or fail if already exist.
- `add_deprecated_lazy_import(export_name, DeprecatedImport, *, no_hoosk=False)`: Adding new deprecated lazy import or fail if already exist.

By default the `__all__` variable is not modified but sometimes this is desirable.

For this cases hooks exist:

- `pre_add_lazy_import_hook(key, value, type_: Literal["lazy_import" | "deprecated_lazy_import"])`: Wrap around key and value and takes as third parameter the type.
- `post_add_lazy_import_hook(key)`: The way to go to update the `__all__` variable dynamically.

The hooks are only executed when manually adding a lazy import and not during the setup of Monkay.

### Example: Automatically update `__all__`

``` python

from monkay import Monkay

# we use a set
__all__ = {"bar"}

monkay = Monkay(
    # required for autohooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
    settings_path="settings_path:Settings",
    post_add_lazy_import_hook=__all__.add
)

if monkay.settings.with_deprecated:
    monkay.add_deprecated_lazy_import(
        "deprecated",
        {
            "path": "tests.targets.fn_module:deprecated",
            "reason": "old.",
            "new_attribute": "super_new",
        }
    )
    # __all__ has now also deprecated when with_deprecated is true
```

### Example: prefix lazy imports

``` python

from monkay import Monkay

# we use a set
__all__ = {"bar"}

def prefix_fn(name: str, value: Any, type_: str) -> tuple[str, Any]:
    return f"{type_}_prefix_{name}", value

monkay = Monkay(
    # required for autohooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
    pre_add_lazy_import_hook=prefix_fn,
    post_add_lazy_import_hook=__all__.add
)
monkay.add_deprecated_lazy_import(
    "deprecated",
    {
        "path": "tests.targets.fn_module:deprecated",
        "reason": "old.",
        "new_attribute": "super_new",
    }
)
# __all__, lazy_imports has now also deprecated under a type prefix name
# but we can skip the hooks with no_hooks=True

monkay.add_deprecated_lazy_import(
    "deprecated",
    {
        "path": "tests.targets.fn_module:deprecated",
        "reason": "old.",
        "new_attribute": "super_new",
    },
    no_hooks=True
)
```

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

## Manual extension setup

Extensions can be added via the add_extension method.
It has 2 keyword parameters:

- use_overwrite (by default True): Use the temporary overwrite provided by with_extensions. Setting this to False is a shortcut to unapply via with_extensions.
- on_conflict (by default "error"): Define what happens on a name conflict: error, keep (old extension), replace (with provided extension)


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

if not os.environg.get("DEBUG"):
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


## Temporary disable overwrite

You can also use the `with_...` functions with None. This disables the overwrite for the scope.
It is used in set_instance when applying extensions.

## Echoed values

The `with_` and `set_` methods return the passed variable as contextmanager value.

e.g.

``` python

with monkay.with_settings(Settings()) as new_settings:
    # do things with the settings overwrite

    # disable the overwrite
    with monkay.with_settings(None) as new_settings2:
        # echoed is None
        assert new_settings2 is None
        # settings are the old settings again
        assert monkay.settings is old_settings

```


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

## Typings

Monkay is fully typed and its main class Monkay is a Generic supporting 2 type parameters:

`INSTANCE` and `SETTINGS`.

Monkay features also a protocol type for extensions: `ExtensionProtocol`.
This is protocol is runtime checkable and has also support for both paramers.

Here a combined example:


```python
from dataclasses import dataclass

from pydantic_settings import BaseSettings
from monkay import Monkay, ExtensionProtocol

class Instance: ...


# providing Instance and Settings as generic types is entirely optional here
@dataclass
class Extension(ExtensionProtocol["Instance", "Settings"]):
    name: str = "hello"

    def apply(self, monkay_instance: Monkay) -> None:
        """Do something here"""


class Settings(BaseSettings):
    extensions: list[ExtensionProtocol["Instance", "Settings"]] =[Extension()]


# type Monkay more strict
monkay = Monkay[Instance, Settings](
    globals(),
    # provide settings object via class
    settings_path=Settings,
    with_extensions=True,
    settings_extensions_name="extensions"
)
```
