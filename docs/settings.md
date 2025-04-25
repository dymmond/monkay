---
hide:
  - navigation
---

# Settings

## Forwarding Settings

In some cases, you may have separate packages that need to operate independently but still need to use the
settings of a main package. **Monkay** allows for a forwarding mode where settings are forwarded from a child
package to the main package.

In this mode, the cache is disabled, and settings are assigned either by setting a function or by simply
assigning a callable to the `settings` property of the `Monkay` instance. The callable should return a suitable
settings object.

### Example: Child Package

```python
{!> ../docs_src/settings/forwarding_child.py !}
```

### Example: Main Package

```python
{!> ../docs_src/settings/forwarding_main.py !}
```

With this setup, the child package will use the settings from the main package, ensuring that all configurations
are aligned.

---

## Lazy Settings Setup

With **Monkay**, settings are only evaluated when needed. This allows for lazy setup, meaning you can defer the
evaluation of settings until later in the application lifecycle.

### Example:

```python
{!> ../docs_src/settings/lazy_loader.py !}
```

This approach allows for flexible configuration of the application, based on the environment, while deferring the
actual evaluation of settings and os.environ.

---

## Multi-Stage Settings Setup

For situations where you need to load settings from multiple sources or paths, **Monkay** supports multi-stage
settings evaluation. By passing `ignore_import_errors=True`, you can attempt to load settings from multiple paths
and handle errors more gracefully.

### Example:

```python
{!> ../docs_src/settings/multi_stage.py !}
```

In this example, **Monkay** tries to evaluate settings from both `a.settings` and `b.settings.develop`, ignoring
import errors if they occur.

---

## `evaluate_settings` Method

The `evaluate_settings` method is used to explicitly evaluate the settings, regardless of whether they have been
evaluated already. It also allows you to control how conflicts and import errors are handled.

### Parameters:
- `on_conflict`: Controls the behavior when settings conflict. Defaults to `error`.
- `onetime`: If `True` (default), the settings are evaluated only on the first call. Subsequent calls are no-ops.
- `ignore_import_errors`: If `True`, suppresses import-related errors when loading settings. Defaults to `False`.
- `ignore_preload_import_errors`: If `True`, suppresses errors related to preloads in settings. Defaults to `True`.

### Example:

```python
monkay.evaluate_settings(on_conflict="warn", ignore_import_errors=True)
```

This method will return `True` if the settings were successfully evaluated, or `False` if there was an error.

> **Note**: `evaluate_settings` does not touch the settings if no `settings_preloads_name` or `settings_extensions_name` is set, but it will still set the `settings_evaluated` flag to `True`.

> **Note**: The `ignore_import_errors` flag also suppresses the `UnsetError` that occurs when settings are unset.

---

## `settings_evaluated` Flag

The `settings_evaluated` flag is an internal property that tracks whether the settings have been evaluated.
This flag can be set on the `ContextVar` or on the instance, depending on the context.

It is reset when new settings are assigned and is initially set to `False` for instances without settings.

---

## Other Settings Types

**Monkay** supports various ways of assigning settings:

- **String or Class**: Initialization happens the first time the settings are accessed and are cached afterward.
- **Function**: The function gets evaluated each time the settings are accessed when returning an instance (useful for forwarding).
  Otherwise for types like str and class, the result is cached and used instead until the settings cache is cleared.

You can also use the `settings_path` parameter to assign a settings location directly, using either a string or
class reference. The caching behavior is the same.

---

## Forwarder

Sometimes, you may need to forward old settings to the **Monkay** settings. While there isn’t a built-in helper,
creating a forwarder is easy. Here's an example:

```python
{!> ../docs_src/settings/forwarder.py !}
```

### Note:
If you want to enable setting modifications, you may also need to define `__setattr__` and `__delattr__`.
However, this is not recommended unless absolutely necessary.

---

## Deleting Settings

You can delete settings by assigning one of the following values: `""`, `None`, or `False`. Afterward, any access
to settings will raise an error until new settings are assigned.

Example:

```python
monkay.settings = None  # This will delete the current settings
```

Trying to access `monkay.settings` afterward will raise an error until settings are set again.

---

## Settings Preloads and Extensions

**Monkay** allows you to handle settings preloads and extensions. Preloads are used to initialize settings before
other components of the application, and extensions can be used to add extra functionality.

### Example: Preloading Settings

```python
monkay.settings_preloads_name = "preload_settings"
monkay.evaluate_settings()
```

This ensures that `preload_settings` are loaded before the application starts, providing a mechanism to set up
necessary configurations upfront.

### Example: Adding Extensions

```python
monkay.settings_extensions_name = "additional_settings_extension"
monkay.evaluate_settings()
```

Extensions allow you to modify or extend the configuration system, adding custom behavior as needed.

---

## Handling Settings Conflicts

If multiple sources of settings are evaluated, conflicts may arise. By setting the `on_conflict` parameter, you can control how conflicts are handled.

### Conflict Options:
- `error`: Raise an error when a conflict occurs (default).
- `warn`: Log a warning but continue processing.
- `merge`: Merge the conflicting settings.
