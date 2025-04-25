---
hide:
  - navigation
---

# Testing

**Monkay** provides several utilities to facilitate testing, especially when dealing with temporary overwrites, lazy imports, and checking imports and exports.

---

## Temporary Overwrites

For testing purposes, **Monkay** provides three context manager methods that allow you to temporarily overwrite settings, extensions, or instances in a thread-safe manner. These methods help you control the environment during tests without affecting the global state.

### Available Context Managers:

1. **`with_settings(settings, *, evaluate_settings_with=None)`**: Temporarily overwrites the settings for the scope of the context. Optionally evaluate settings with provided parameters as dict. Enable evaluation by providing a dict.
2. **`with_extensions(extensions_dict, *, apply_extensions=False)`**: Temporarily overwrites the extensions for the scope. The `apply_extensions` flag controls whether extensions are applied during the overwrite.
3. **`with_instance(instance, *, apply_extensions=False, use_extensions_overwrite=True)`**: Temporarily overwrites the instance for the scope. You can also apply extensions and control the overwrite behavior using the respective flags.

These context managers provide a flexible way to test different configurations of settings, extensions, and instances without permanently modifying them.

### Example:

```python
from monkay import Monkay

monkay = Monkay(globals(), settings_path="", with_extensions=True, with_instance=True)

# Overwrite settings temporarily and evaluate it
with monkay.with_settings({"setting_name": "new_value"}, evaluate_settings_with={}):
    assert monkay.settings.setting_name == "new_value"

# Overwrite extensions temporarily
with monkay.with_extensions({"extension_name": "new_extension"}, apply_extensions=True):
    assert "extension_name" in monkay.extensions

# Overwrite instance temporarily
with monkay.with_instance(new_instance, apply_extensions=False):
    assert monkay.instance is new_instance
```

These context managers are especially useful for writing isolated and repeatable tests, where you may want to modify the environment without affecting the global state.

### Full overwrite

If multiple attributes should be simulated, e.g. for a virtual monkay environment, you can use
`with_full_overwrite`. The advantage: you have already the right order set.
Note: when not enabling a feature in monkay it will cause an error to provide a parameter for it.

#### Parameters

Parameters which need a feature enabled when creating the monkay instance:

**extensions** - Set an extra extensions set like with `with_extensions`. You might want to set it to {} for a clean extensions set.
**settings** - Overwrite the settings if specified. It types matches the `with_settings` contextmanager.
**instance** - Overwrite the instance if specified. It types matches the `with_instance` contextmanager.

Extra parameters:

- **apply_extensions** - Apply extensions. Only used when `extensions` parameter is used.
- **evaluate_settings_with** - Pass options to `with_settings` parameter `evaluate_settings_with`. Only used when `settings` parameter is used.
  To enable evaluation pass `{}`

#### Example:

```python
from monkay import Monkay

monkay = Monkay(globals(), settings_path="", with_extensions=True, with_instance=True)

# Overwrite everything temporarily and use a clean extensions set
with monkay.with_full_overwrite(extensions={}, settings=..., instance=..., evaluate_settings_with={}):
    assert monkay.instance is new_instance
```

---

## Check Imports and Exports

**Monkay** provides a debugging method called `find_missing()` to help you verify that all imports and exports are correctly defined and available. This method can be particularly useful for testing and debugging, but it is **expensive** and should only be used in error cases or for debugging purposes.

### `find_missing` Method

The `find_missing()` method checks if all exports are correctly defined in the `__all__` variable of a module and whether all required imports are available.

#### Parameters:
- **`all_var`**: If provided, the method checks that all keys are in the given `__all__` variable. If set to `True`, it checks the `__all__` variable of the module.
- **`search_pathes`**: A list of module paths to search for imports. The method will check if each import path is available and correctly imported.
- **`ignore_deprecated_import_errors`**: If set to `True`, it suppresses errors for deprecated imports that fail.
- **`require_search_path_all_var`**: If `True` (default), it ensures that the search path modules have an `__all__` variable. If `False`, missing `__all__` errors for search paths are ignored.

The method returns a dictionary with the following structure:

- **Key**: Import name or import path
- **Value**: Set of errors related to the import

#### Possible Errors:
- **`not_in_all_var`**: The import is not listed in the provided `__all__` variable.
- **`missing_attr`**: The attribute defined in `__all__` does not exist or raises an `AttributeError`.
- **`missing_all_var`**: The search path or main module does not have an `__all__` variable. This error can be suppressed by setting `require_search_path_all_var=False`.
- **`import`**: The import of the module or function raised an `ImportError`.
- **`shadowed`**: The key is defined as a lazy import but is also defined in the main module, meaning the lazy import is not used.
- **`search_path_extra`**: The search path is not included in the lazy imports.
- **`search_path_import`**: The import of the search path failed.

### Example:

Using **Monkay** for tests is straightforward and convenient, as shown in the example below:

```python
import edgy

def test_edgy_lazy_imports():
    # Check for missing imports in the specified modules
    missing = edgy.monkay.find_missing(
        all_var=edgy.__all__,
        search_pathes=["edgy.core.files", "edgy.core.db.fields", "edgy.core.connection"]
    )

    # Remove false positives if any
    if missing.get("AutoNowMixin") == {"AutoNowMixin"}:
        del missing["AutoNowMixin"]

    # Assert that no imports are missing
    assert not missing
```

In this example:
- The `find_missing()` method is used to check for any missing imports in the `edgy` module and its submodules.
- If there are any false positives (e.g., an import was marked as missing but is actually valid), they are removed from the result.
- The test asserts that there are no missing imports.

This ensures that no lazy imports are broken and that all expected imports are available.

---

### Ignore Import Errors for Deprecated Lazy Imports

When you have deprecated lazy imports, you can suppress import errors for these deprecated attributes by setting `ignore_deprecated_import_errors=True`. This is particularly useful when migrating from an old import path to a new one, while still allowing the application to run without breaking.

### Example:

```python
missing = edgy.monkay.find_missing(
    all_var=edgy.__all__,
    search_pathes=["edgy.core.files", "edgy.core.db.fields", "edgy.core.connection"],
    ignore_deprecated_import_errors=True
)
```

This will suppress errors for deprecated imports, allowing the system to continue functioning even if some of the lazy imports have been deprecated or removed.

---

## Summary of Key Features for Testing

- **Temporary Overwrites**: Use context managers (`with_settings`, `with_extensions`, `with_instance`) to temporarily modify settings, extensions, or instances in a thread-safe manner during tests.
- **Check Imports and Exports**: Use `find_missing()` to verify that all imports and exports are correctly defined and available, helping to identify issues with missing attributes or failed imports.
- **Ignore Deprecated Import Errors**: Optionally suppress errors for deprecated lazy imports to allow smoother transitions between old and new import paths.

These testing utilities provide an effective way to validate your application's environment and ensure that all components are correctly loaded and available during testing. Let me know if you need further refinements or if you'd like to move on to another section!
