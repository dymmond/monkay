# Tutorial

## How to use

### Installation

``` shell
pip install monkay
# or
# pip install monkay[settings]
```

### Usage

Probably in the main `__init__.py` you define something like this:

``` python
monkay = Monkay(
    # required for autohooking
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path="settings_path:Settings",
    preloads=["tests.targets.module_full_preloaded1:load"],
    settings_preload_name="preloads",
    settings_extensions_name="extensions",
    lazy_imports={"bar": "tests.targets.fn_module:bar"},
    deprecated_lazy_imports={
        "deprecated": {
            "path": "tests.targets.fn_module:deprecated",
            "reason": "old",
            "new_attribute": "super_new",
        }
    },
)
```


When providing your own `__all__` variable **after** providing Monkay or you want more controll, you can provide

`skip_all_update=True`

and update the `__all__` value via `Monkay.update_all_var` if wanted.

#### Using settings

Settings can be an initialized pydantic settings variable or a class.
When pointing to a class the class is automatically called without arguments.

Let's do the configuration like Django via environment variable:

``` python title="__init__.py"
import os
monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=os.environ.get("MONKAY_SETTINGS", "example.default.path.settings:Settings"),
    settings_preload_name="preloads",
    settings_extensions_name="extensions",
)
```

``` python title="settings.py"
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    preloads: list[str] = []
    extensions: list[Any] = []

```

And voila settings are now available from monkay.settings. This works only when all settings arguments are
set via environment or defaults.

When having explicit variables this is also possible:

``` python title="explicit_settings.py"
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    preloads: list[str]
    extensions: list[Any]

settings = Settings(preloads=[], extensions=[])
```
Note here the lowercase settings

``` python title="__init__.py"
import os
from monkay import Monkay
monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=os.environ.get("MONKAY_SETTINGS", "example.default.path.settings:settings"),
    settings_preload_name="preloads",
    settings_extensions_name="extensions",
)
```

#### Pathes

Like shown in the examples pathes end with a `:` for an attribute. But sometimes a dot is nicer.
This is why you can also use a dot in most cases. A notable exception are preloads where `:` are marking loading functions.

#### Preloads

Preloads are required in case some parts of the application are self-registering but no extensions.

There are two kinds of preloads

1. Module preloads. Simply a module is imported via `import_module`. Self-registrations are executed
2. Functional preloads. With a `:`. The function name behind the `:` is executed and it is
   expected that the function does the preloading. The module however is still preloaded.


``` python title="preloader.py"
from importlib import import_module

def preloader():
    for i in ["foo.bar", "foo.err"]:
        import_module(i)

```

``` python title="settings.py"
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    preloads: list[str] = ["preloader:preloader"]
```

##### Lazy imports

When using lazy imports the globals get an `__getattr__` injected. A potential old `__getattr__` is used as fallback when provided **before**
initializing the Monkay instance:

`module attr > monkay __getattr__ > former __getattr__ or Error`.


Lazy imports of the `lazy_imports` parameter/attribute are defined in a dict with the key as the pseudo attribute and the value the forward.

There are also `deprecated_lazy_imports` which have as value a dictionary with the key-values

- `path`: Forward path.
- `reason` (Optional): Deprecation reason.
- `new_attribute` (Optional): Upgrade path.

#### Using the instance feature

The instance feature is activated by providing a boolean (or a string for an explicit name) to the `with_instance`
parameter.

For entrypoints you can set now the instance via `set_instance`. A good entrypoint is the init and using the settings:


``` python title="__init__.py"
import os
from monkay import Monkay, load

monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=os.environ.get("MONKAY_SETTINGS", "example.default.path.settings:settings"),
    settings_preload_name="preloads",
    settings_extensions_name="extensions",
)

monkay.set_instance(load(settings.APP_PATH))
```

#### Using the extensions feature

Extensions work well together with the instances features.

An extension is a class implementing the ExtensionProtocol:

``` python title="Extension protocol"
from typing import Protocol

@runtime_checkable
class ExtensionProtocol(Protocol[L]):
    name: str

    def apply(self, monkay_instance: Monkay[L]) -> None: ...

```


A name (can be dynamic) and the apply method are required. The instance itself is easily retrieved from
the monkay instance.

``` python title="settings.py"
from dataclasses import dataclass
import copy
from pydantic_settings import BaseSettings

class App:
    extensions: list[Any]

@dataclass
class Extension:
    name: str = "hello"

    def apply(self, monkay_instance: Monkay) -> None:
        monkay_instance.instance.extensions.append(copy.copy(self))

class Settings(BaseSettings):
    preloads: list[str] = ["preloader:preloader"]
    extensions: list[Any] = [Extension]
    APP_PATH: str = "settings.App"

```

##### Reordering extension order dynamically

During apply it is possible to call `monkay.ensure_extension(name | Extension)`. When providing an extension
it is automatically initialized though not added to extensions.
Every name is called once and extensions in `monkay.extensions` have priority. They will applied instead when providing
a same named extension via ensure_extension.

##### Reordering extension order dynamically2

There is a second more complicated way to reorder:

via the parameter `extension_order_key_fn`. It takes a key function which is expected to return a lexicographic key capable for ordering.

You can however intermix both.
