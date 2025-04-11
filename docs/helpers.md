---
hide:
  - navigation
---

# Helpers

**Monkay** comes with several useful helper functions to assist in managing imports, handling attributes, and working with modules. These helpers streamline the process of loading and managing dependencies in a flexible and robust way.

## Helper Functions

### `load(path, *, allow_splits=":.", package=None)`

The `load()` function is used to load a module or attribute from a given path. The `path` can refer to a module or an attribute within a module. The `allow_splits` parameter determines how the path is split into parts (typically for modules and attributes). By default, both `.` and `:` are allowed as separators.

- **`allow_splits`**: Configures whether attributes are separated by `.` or `:`. You can specify both (default behavior) or restrict it to one.
- **`package`**: Optionally specify the package to search in (useful for relative imports).

#### Example:

```python
from monkay import load

module = load("foo.bar:attribute")
```

In this example, the path `"foo.bar:attribute"` will be resolved, with `.` and `:` both supported as path separators.

---

### `load_any(module_path, potential_attrs, *, non_first_deprecated=False, package=None)`

The `load_any()` function attempts to load a module and check for any attribute name that matches one of the potential attributes. If a matching attribute is found, it will be returned. If no match is found, it raises an `ImportError`. Additionally, this function allows for deprecating certain attributes.

- **`module_path`**: The path to the module (like `"foo.bar"`).
- **`potential_attrs`**: A list of attribute names to check within the module.
- **`non_first_deprecated`**: When set to `True`, a **DeprecationWarning** is issued for any non-first attribute match, useful for deprecating old attributes.
- **`package`**: Optionally specify the package to search in.

This function is helpful when you want to allow multiple attribute names for a module, with support for deprecation warnings for older attributes.

#### Example:

```python
from monkay import load_any

# Attempts to load any of the attributes bar, bar_deprecated, or bar_deprecated2 from the module tests.targets.fn_module.
# Issues a deprecation warning for the non-first match if non_first_deprecated=True
result = load_any("tests.targets.fn_module", ["bar", "bar_deprecated", "bar_deprecated2"], non_first_deprecated=True)
```

If `"bar"` is found, it will be returned. If `"bar_deprecated"` or `"bar_deprecated2"` are found next, they will trigger a **DeprecationWarning**.

---

### `absolutify_import(import_path, package)`

The `absolutify_import()` function converts a relative import path to an absolute import path. If the path is already absolute, it is returned unchanged.

- **`import_path`**: The relative or absolute import path to convert.
- **`package`**: The base package to resolve relative paths.

This function is useful for ensuring that all imports are absolute, making it easier to handle imports in different contexts (e.g., in packages or scripts).

#### Example:

```python
from monkay import absolutify_import

# Converts a relative import path to an absolute import path
absolute_path = absolutify_import("foo.bar", "my_package")
```

This will convert a relative import like `"foo.bar"` to the absolute import path `"my_package.foo.bar"`.

---

## Using Helpers with Lazy Imports

Monkay allows you to use these helper functions as part of the **lazy import** mechanism, where module loading is deferred until needed. This is useful for improving startup performance and reducing the initial load time.

### Example: Lazy Imports with `load_any` and `load`

```python
import os
from monkay import Monkay, load, load_any

monkay = Monkay(
    # Required for auto-hooking
    globals(),
    lazy_imports={
        # Dynamically load the 'bar' attribute or fallback to deprecated attributes
        "bar": lambda: load_any("tests.targets.fn_module", ["bar", "bar_deprecated", "bar_deprecated2"], non_first_deprecated=True),
        # Environment variable evaluation on initialization
        "dynamic": os.environ["DYNAMIC"],
        # Lazy load with a lambda, evaluated when dynamic2 is accessed
        "dynamic2": lambda: load(os.environ["DYNAMIC"]),
    },
    deprecated_lazy_imports={
        "deprecated": {
            # Manually load a deprecated attribute
            "path": lambda: load("tests.targets.fn_module:deprecated"),
            "reason": "old.",
            "new_attribute": "super_new",
        }
    },
)
```

In this example, Monkay is configured with **lazy imports**:
- The `bar` import is deferred until accessed, using `load_any` to check for several potential attribute names, with a deprecation warning for non-first matches.
- The `dynamic` import is directly fetched from an environment variable.
- The `dynamic2` import uses `load()` to load the path dynamically based on an environment variable, and can be re-evaluated by clearing the cache.
- The `deprecated_lazy_imports` section handles deprecated imports, specifying the reason for deprecation and a new attribute name to use.

---

## Summary of Helper Functions

- **`load()`**: Loads a module or attribute from a specified path with configurable path separators.
- **`load_any()`**: Attempts to load any matching attribute from a module, with support for deprecation warnings for non-first matches.
- **`absolutify_import()`**: Converts a relative import path to an absolute import path.

These helpers provide powerful ways to handle dynamic and lazy imports, as well as manage deprecated attributes, making it easier to maintain and extend your applications.
