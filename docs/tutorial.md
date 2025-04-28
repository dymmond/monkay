---
hide:
  - navigation
---

# Tutorial

**Monkay** simplifies dynamic imports, extension management, settings handling, and much more. This tutorial walks you through the essential steps for using **Monkay** in your projects.

---

## How to Use **Monkay**

### Installation

To get started with **Monkay**, install it via `pip`:

```shell
pip install monkay
```

---

### Usage

Below is an example of how to set up **Monkay** in your project. You can use **Monkay** to manage dynamic imports, lazy loading, settings, extensions, and more.

```python title="foo/__init__.py"
{!>../docs_src/tutorial/full_example_init.py}
```

This configuration sets up **Monkay** with several features:
- **Lazy imports** for `bar` and `settings`.
- **Lazy evaluated settings_path** for being able to update the environment variable in code.
- **Deprecated lazy imports** for `deprecated`.
- **Preloads** and **extensions** for dynamic configuration.
- **Uncached imports** to prevent caching specific imports like settings.

```python title="foo/main.py"
{!>../docs_src/tutorial/full_example_main.py}
```

In `main.py`, the application is initialized by evaluating preloads and settings, ensuring that all required dependencies are loaded before use.

---

### **Managing `__all__` for Control**

After providing **Monkay**, if you need more control over the `__all__` variable, you can disable the automatic update of `__all__` by setting `skip_all_update=True`. You can later update it manually using `Monkay.update_all_var`.

**Warning**: Using `settings_preloads_name` or `settings_extensions_name` can sometimes cause circular dependency issues. To avoid such issues, ensure that you call `evaluate_settings()` later in the setup process. For more information, refer to [Settings Preloads and Extensions](#settings-extensions-and-preloads).

---

## Lazy Imports

**Monkay** enhances the import process by allowing lazy imports. When using lazy imports, **Monkay** injects `__getattr__` and `__dir__` into the globals.

The lookup hierarchy for lazy imports is as follows:
1. **Module attribute**
2. **Monkay `__getattr__`**
3. **Previous `__getattr__` or error**

Lazy imports are defined in the `lazy_imports` dictionary, where the key is the pseudo attribute name and the value is the module path or a function returning the result.

#### Deprecated Lazy Imports

In addition to lazy imports, **Monkay** also supports deprecated lazy imports. These are defined as a dictionary with the following keys:
- **`path`**: The path to the object.
- **`reason`** (Optional): Reason for deprecation.
- **`new_attribute`** (Optional): The new attribute to use.

#### Listing All Attributes with `dir()`

**Monkay** injects a `__dir__()` function that provides a list of all attributes, including lazy imports and the contents of `__all__`. This is useful when working with autocompletion and introspection.

- **Sources for `__dir__`**:
  - The old `__dir__()` function (if provided before **Monkay** initialization).
  - `__all__` variable.
  - Lazy imports.

---

## Caching

By default, **Monkay** caches all lazy imports. However, caching may not always be desirable, especially for dynamic results like settings. You can disable caching for specific imports using the `uncached_imports` parameter, which takes an iterable of imports that shouldn't be cached.

You can also clear the caches using the `clear_caches()` method:

```python
monkay.clear_caches(settings_cache=True, import_cache=True)
```

This will clear the caches for both settings and imports, ensuring that fresh data is loaded.

---

### Using Settings

You can configure **Monkay** to use settings from various sources, including environment variables, classes, or explicitly defined settings objects. Here's an example of configuring **Monkay** using environment variables (similar to Django's settings pattern):

```python title="__init__.py"
import os
monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=lambda: os.environ.get("MONKAY_SETTINGS", "example.default.path.settings:Settings"),
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
    uncached_imports=["settings"],
    lazy_imports={"settings": lambda: monkay.settings}
)
```

Here, the `settings_path` is determined by an environment variable when accessed, and **Monkay** will use `settings` as the main settings object.
The object will be cached.

```python title="settings.py"
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    preloads: list[str] = []
    extensions: list[Any] = []
```

In this setup, **Monkay** will dynamically load the `Settings` class from the specified path, and settings will be available via `monkay.settings`.

---

### Other Settings Libraries

While **Monkay** uses `pydantic_settings` in this example, the settings can come from any source that is resolvable as attributes or keys, such as dictionaries or `TypedDict`.

```python title="explicit_settings.py"
from typing import TypedDict

class Settings(TypedDict):
    preloads: list[str]
    extensions: list[Any]
    foo: str

settings = Settings(preloads=[], extensions=[], foo="hello")
```

You can use this structure within **Monkay** by pointing `settings_path` to the settings class or object.

---

## Settings Extensions and Preloads

When using `settings_preloads_name` or `settings_extensions_name`, it’s important to call `evaluate_settings()` later in the setup process to avoid circular dependencies and ensure that preloads and extensions are applied correctly. Failing to do so could result in missing imports or incorrect library versions.

Here’s an example of using **Monkay** with preloads and extensions:

```python title="edgy/settings/conf.py"
from functools import lru_cache

@lru_cache
def get_edgy():
    import edgy
    edgy.monkay.evaluate_settings(ignore_import_errors=False)
    return edgy

class SettingsForward:
    def __getattribute__(self, name: str) -> Any:
        return getattr(get_edgy().monkay.settings, name)

settings = SettingsForward()
```

This example demonstrates how to load settings dynamically and handle dependencies via preloads and extensions.

---

### Preloads

Preloads can be either module imports or function calls. When specifying preloads, you can use module paths or function names to ensure that the necessary components are loaded before the application starts.

```python title="preloader.py"
from importlib import import_module

def preloader():
    for i in ["foo.bar", "foo.err"]:
        import_module(i)
```

```python title="settings.py"
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    preloads: list[str] = ["preloader:preloader"]
```

**Warning**: Settings preloads are only executed after calling `evaluate_settings()`. Preloads provided in the `__init__` are evaluated immediately. To evaluate preloads later, you can call `evaluate_preloads()` directly.

---

### Using the Instance Feature

The instance feature is activated by providing `with_instance=True` when initializing **Monkay**. Once activated, you can set the instance via `set_instance`, allowing for dynamic configuration of your application.

```python title="__init__.py"
import os
from monkay import Monkay, load

monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=lambda: os.environ.get("MONKAY_SETTINGS", "example.default.path.settings:settings"),
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
)

monkay.evaluate_settings()
monkay.set_instance(settings.APP_PATH)
```

---

## Using the Extensions Feature

Extensions are a powerful feature of **Monkay** that allow you to extend the functionality of your application dynamically. Extensions must implement the `ExtensionProtocol`:

```python title="Extension Protocol"
from typing import Protocol

@runtime_checkable
class ExtensionProtocol(Protocol[INSTANCE, SETTINGS]):
    name: str

    def apply(self, monkay_instance: Monkay[INSTANCE, SETTINGS]) -> None: ...
```

Extensions can be applied to **Monkay** dynamically and can modify the instance or settings as needed.

```python title="settings.py"
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

### Apply extensions

Applying extensions is automatically done when setting the instance and extensions are enabled.
If this behaviour is unwanted, you can pass `apply_extensions=False` to `set_instance`

---

## Tricks

### Type-Checker Friendly Lazy Imports

You can define imports for type-checking within the `TYPE_CHECKING` scope. These imports are only used during type-checking and are not executed during runtime.

```python
from typing import TYPE_CHECKING

from monkay import Monkay

if TYPE_CHECKING:
    from tests.targets.fn_module import bar

monkay = Monkay(
    # Required for autohooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
)
```

### Static `__all__`

For autocompletion, it’s useful to define a static `__all__` variable. This ensures that IDEs and tools can parse the source code properly and provide accurate autocompletion.

```python
import os
from typing import TYPE_CHECKING

from monkay import Monkay

if TYPE_CHECKING:
    from tests.targets.fn_module import bar

__all__ = ["bar", "monkay", "stringify_all", "check"]

monkay = Monkay(
    # Required for autohooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
    skip_all_update=not os.environ.get("DEBUG"),
    post_add_lazy_import_hook=__all__.append if __name__ == "__main__" else None
)
```

This example updates `__all__` dynamically in the debug environment and ensures that lazy imports are added to `__all__`.


### Sub monkay environment

Sometimes you want to provide temporily a different environment for a code path. You can do this with:

[`with_full_overwrite`](testing.md#full-overwrite)
