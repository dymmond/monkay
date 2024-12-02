# Tutorial

## How to use

### Installation

``` shell
pip install monkay
```

### Usage

Probably in the main `__init__.py` you define something like this:

``` python
from monkay import Monkay

monkay = Monkay(
    # required for autohooking
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path="settings_path:Settings",
    preloads=["tests.targets.module_full_preloaded1:load"],
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
    uncached_imports=["settings"],
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
        "settings": lambda: monkay.settings,
    },
    deprecated_lazy_imports={
        "deprecated": {
            "path": "tests.targets.fn_module:deprecated",
            "reason": "old.",
            "new_attribute": "super_new",
        }
    },
)
```


When providing your own `__all__` variable **after** providing Monkay or you want more controll, you can provide

`skip_all_update=True`

and update the `__all__` value via `Monkay.update_all_var` if wanted.


#### Lazy imports

When using lazy imports the globals get an `__getattr__` and `__dir__` injected. A potential old `__getattr__` and/or `__dir__` is used when specified **before**
initializing the Monkay instance.

The lookup hierarchy is:

`module attr > monkay __getattr__ > former __getattr__ or Error`.

Lazy imports of the `lazy_imports` parameter/attribute are defined in a dict with the key as the pseudo attribute and the value the forward string or a function
which return result is used.

There are also `deprecated_lazy_imports` which have as value a dictionary with the key-values

- `path`: Path to object or function returning object.
- `reason` (Optional): Deprecation reason.
- `new_attribute` (Optional): Upgrade path. New attribute.

##### Listing all attributes with `dir()`

Monkay also injects a `__dir__` module function for listing via dir. It contains all lazy imports as well as `__all__` variable contents.
The `__dir__` function is also injected without lazy imports when an existing `__getattr__` without a `__dir__` function was detected and
an `__all__` variable is available.
It is tried to guess the attributes provided by using the `__all__` variable.

In short the sources for the Monkay `__dir__` are:

- Old `__dir__()` function if provided before the Monkay initialization.
- `__all__` variable.
- Lazy imports.

##### Caching

By default all lazy import results are cached. This is sometimes not desirable
Sometimes it is desirable to not cache. E.g. for dynamic results like settings.
The caching can be disabled via the `uncached_imports` parameter which generates from an iterable
a set of imports which aren't cached.

There is also a method:

`clear_caches(settings_cache=True, import_cache=True)`

Which can be used to clear the caches.


#### Using settings

Settings pointed at via the string can be an initialized settings variable or a class.
When pointing to a class the class is automatically called without arguments.

Let's do the configuration like Django via environment variable:

``` python title="__init__.py"
import os
monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=os.environ.get("MONKAY_SETTINGS", "example.default.path.settings:Settings"),
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
    uncached_imports=["settings"],
    lazy_imports={"settings": lambda: monkay.settings}
)
```

``` python title="settings.py"
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    preloads: list[str] = []
    extensions: list[Any] = []
```

And voila settings are now available from monkay.settings as well as settings. This works only when all settings arguments are
set via environment or defaults.
Note the `uncached_imports`. Because temporary overwrites should be possible, we should not cache this import. The settings
are cached anyway.

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
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
)
```

##### Other settings libraries

Here we just use pydantic_settings. But settings can be everything from a dictionary, to a dataclass.
Only requirement is that names are resolvable as attributes or as keys.`


``` python title="explicit_settings.py"
from typing import TypedDict

class Settings(TypedDict):
    preloads: list[str]
    extensions: list[Any]
    foo: str

settings = Settings(preloads=[], extensions=[], foo="hello")
# or just a dictionary
# settings = {"preloads": [], "extensions": [], "foo": "hello"}
```

and

``` python title="__init__.py"
import os
from monkay import Monkay, get_value_from_settings
monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=os.environ.get("MONKAY_SETTINGS", "example.default.path.settings:settings"),
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
)

# attribute grabber with fallback to items
get_value_from_settings(monkay.settings, "foo")
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
    settings_preloads_name="preloads",
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
class ExtensionProtocol(Protocol[INSTANCE, SETTINGS]):
    name: str

    def apply(self, monkay_instance: Monkay[INSTANCE, SETTINGS]) -> None: ...
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


## Tricks

### Type-checker friendly lazy imports

Additionally to the lazy imports you can define in the `TYPE_CHECKING` scope the imports of the types.

They are not loaded except when type checking.

``` python

from typing import TYPE_CHECKING

from monkay import Monkay

if TYPE_CHECKING:
    from tests.targets.fn_module import bar

monkay = Monkay(
    # required for autohooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
)
```


### Static `__all__`

For autocompletions it is helpful to have a static `__all__` variable because many tools parse the sourcecode.
Handling the `__all__` manually is for small imports easy but for bigger projects problematic.

Let's extend the former example:


``` python

import os
from typing import TYPE_CHECKING

from monkay import Monkay

if TYPE_CHECKING:
    from tests.targets.fn_module import bar

__all__ =["bar", "monkay", "stringify_all", "check"]

monkay = Monkay(
    # required for autohooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
    skip_all_update=not os.environ.get("DEBUG")
    # when printing all, lazy imports automatically add to __all__
    post_add_lazy_import_hook=__all__.append if  __name__ == "__main__" else None
)


def print_stringify_all(separate_by_category: bool=True) -> None:
    print("__all__ = [\n{}\n]".format(
        "\n,".join(
            f'"{t[1]}"'
            for t in monkay.sorted_exports(separate_by_category=separate_by_category)
        )
    ))

def check() -> None:
    if monkay.find_missing(search_pathes=["tests.targets.fn_module"]):
        raise Exception()

if __name__ == "__main__":
    # refresh __all__ to contain all lazy imports
    __all__ = monkay.update_all_var(__all__)
    print_stringify_all()
elif os.environ.get("DEBUG"):
    check()
```

This way in a debug environment the imports are automatically checked.
And via `python -m mod` the new `__all__` can be exported.
