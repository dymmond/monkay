---
hide:
  - navigation
---

# Specials

**Monkay** provides several special features that enhance flexibility, handle lazy imports, manage extensions, and ensure thread-safety and asynchronous safety. These features can be critical when building dynamic applications that need fine-grained control over imports, settings, and extensions.

---

## Overwriting the Used Package for Relative Imports

By default, **Monkay** sets the `package` parameter to the `__spec__.parent` of the module, which is typically the directory containing the module. This is helpful for resolving relative imports.

If you need to specify a different package for resolving relative imports, you can override this default behavior by providing the `package` parameter when initializing **Monkay**.

### Example:

```python
from monkay import Monkay

monkay = Monkay(
    globals(),
    package="my_custom_package"  # Override the default package for resolving relative imports
)
```

In this case, **Monkay** will use `"my_custom_package"` to resolve relative imports instead of using the module's `__spec__.parent`.

---

## Adding Dynamically Lazy Imports

**Monkay** allows you to add **lazy imports** dynamically, either for regular imports or deprecated imports. There are two methods for this:

- **`add_lazy_import(export_name, path_or_fn, *, no_hooks=False)`**: Adds a new lazy import or fails if the import already exists.
- **`add_deprecated_lazy_import(export_name, DeprecatedImport, *, no_hooks=False)`**: Adds a new deprecated lazy import or fails if it already exists.

Additionally, **Monkay** allows you to dynamically modify the `__all__` variable, which is useful for managing the module's exports.

### Hook Functions:
- **`pre_add_lazy_import_hook(key, value, type_: Literal["lazy_import", "deprecated_lazy_import"])`**: This hook is called before adding a lazy import or a deprecated lazy import.
- **`post_add_lazy_import_hook(key)`**: This hook is called after a lazy import is added and is the proper place to update the `__all__` variable.

The hooks only apply when manually adding a lazy import (not during the initial setup of **Monkay**).

---

### Example: Automatically Update `__all__`

```python
from monkay import Monkay

# we use a set for __all__
__all__ = {"bar"}

monkay = Monkay(
    # required for auto-hooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
    settings_path="settings_path:Settings",
    post_add_lazy_import_hook=__all__.add  # Automatically update __all__ when a lazy import is added
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

In this example, we dynamically add the `bar` import, and when the deprecated import is added, the `__all__` variable is automatically updated to include `deprecated`.

---

### Example: Prefix Lazy Imports

You can modify the name of lazy imports dynamically by using the `pre_add_lazy_import_hook`. This hook allows you to change the name of the imported module before it's added.

```python
from monkay import Monkay

# we use a set for __all__
__all__ = {"bar"}

def prefix_fn(name: str, value: Any, type_: str) -> tuple[str, Any]:
    return f"{type_}_prefix_{name}", value  # Prefix the lazy import name

monkay = Monkay(
    # required for auto-hooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
    pre_add_lazy_import_hook=prefix_fn,  # Apply prefix to the import name
    post_add_lazy_import_hook=__all__.add  # Update __all__ after adding the import
)

monkay.add_deprecated_lazy_import(
    "deprecated",
    {
        "path": "tests.targets.fn_module:deprecated",
        "reason": "old.",
        "new_attribute": "super_new",
    }
)
# Now __all__ and lazy_imports will include "lazy_import_prefix_bar" and "deprecated_prefix_deprecated"
```

This will prefix the lazy imports with `lazy_import_prefix_` and `deprecated_prefix_`, allowing for more organized import naming.

---

## Manual Extension Setup

You can add extensions to **Monkay** manually via the `add_extension` method. The `add_extension` method allows you to specify additional behavior for handling extensions within your application.

### Parameters:
- **`use_overwrite`** (default: `True`): Specifies whether to use the temporary overwrite provided by `with_extensions`. Setting this to `False` prevents overwriting.
- **`on_conflict`** (default: `"error"`): Defines the behavior when an extension name conflicts with an existing one. Options include:
  - `"error"`: Raise an error.
  - `"keep"`: Keep the old extension.
  - `"replace"`: Replace with the new extension.

### Example:

```python
monkay.add_extension(
    MyExtension(),
    use_overwrite=False,
    on_conflict="replace"
)
```

This will add the `MyExtension()` to **Monkay**, replacing any existing extension with the same name.

---

## Temporary Disable Overwrite

You can disable overwriting for a specific scope by using the `with_...` functions with `None`. This is useful for preventing temporary changes to global state, such as when applying extensions or settings.

### Example:

```python
with monkay.with_settings(None) as new_settings:
    # Here new_settings will be None and the old settings will be restored
    assert new_settings is None
    assert monkay.settings is old_settings
```

This temporarily disables the settings overwrite and restores the original settings.

---

## Echoed Values

The `with_` and `set_` methods in **Monkay** return the passed variable as a context manager value. This allows you to modify the value temporarily within a specific scope.

### Example:

```python
with monkay.with_settings(Settings()) as new_settings:
    # Perform actions with the settings overwrite
    with monkay.with_settings(None) as new_settings2:
        # Echoed value is None, meaning the overwrite is disabled
        assert new_settings2 is None
        # The settings revert to the original state
        assert monkay.settings is old_settings
```

---

## `evaluate_preloads`

The `evaluate_preloads` function allows you to load preloads across your application. It ensures that all preloads are evaluated, returning `True` if all succeeded.

### Parameters:
- **`preloads`**: A list of import paths to evaluate. See the [Preloads section](./tutorial.md#preloads) for special syntax.
- **`ignore_import_errors`**: When `True` (default), not all import paths need to be available. When `False`, all imports must succeed.
- **`package`** (Optional): Specify a different package for the preload imports. By default, **Monkay** uses the package of the **Monkay** instance.

### Example:

```python
monkay.evaluate_preloads(
    preloads=["module1", "module2"],
    ignore_import_errors=True
)
```

This will attempt to load the preloads `module1` and `module2`, ignoring any import errors that occur.

---

## Typings

**Monkay** is fully typed, supporting **Generic** types for both the instance and settings. This allows you to define stricter types for instances and settings within your application.

### Example:

```python
from dataclasses import dataclass
from pydantic_settings import BaseSettings
from monkay import Monkay, ExtensionProtocol

class Instance: ...


@dataclass
class Extension(ExtensionProtocol["Instance", "Settings"]):
    name: str = "hello"

    def apply(self, monkay_instance: Monkay) -> None:
        """Do something here"""


class Settings(BaseSettings):
    extensions: list[ExtensionProtocol["Instance", "Settings"]] = [Extension()]


monkay = Monkay[Instance, Settings](
    globals(),
    settings_path=Settings,
    with_extensions=True,
    settings_extensions_name="extensions"
)
```

In this example, we define the types for `Instance` and `Settings` and apply extensions with stricter typing.

---

## Cages

**[Cages](./cages.md)** are a special feature of **Monkay** that handle global mutable structures in an async-safe manner. Cages ensure thread-safety and allow you to work with structures that are not natively async-safe (e.g., userland threads, asyncio).

Because Cages are essential to handling mutable structures in an async-safe way, they have their own documentation. Please refer to the [Cages documentation](cages.md) for more details.
