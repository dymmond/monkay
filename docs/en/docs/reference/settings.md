# Settings

This reference documents how Monkay loads, caches, overrides, and evaluates
settings objects.

## Settings Sources

`Monkay.settings` can be configured from:

- a dotted path (`"module:attribute"`),
- a settings class,
- a callable returning a settings source,
- an already-instantiated settings object.

When settings resolve to a class/path, Monkay caches the parsed object.
Callable sources can be used for dynamic forwarding patterns.

## Evaluate Settings

`evaluate_settings(...)` processes optional preload and extension lists from the
current settings object.

### Parameters

- `on_conflict`: extension conflict policy (`"error"`, `"keep"`, `"replace"`)
- `ignore_import_errors`: return `False` instead of raising on settings import/unset errors
- `ignore_preload_import_errors`: continue when preload imports fail
- `onetime`: skip re-evaluation when settings already evaluated in current context

### Example

```python
monkay.evaluate_settings(on_conflict="replace", onetime=False)
```

## Forwarding Settings

Forwarding allows a package to delegate settings to another package.

### Child package

```python
{!> ../../../../docs_src/settings/forwarding_child.py !}
```

### Main package

```python
{!> ../../../../docs_src/settings/forwarding_main.py !}
```

## Lazy Settings Setup

```python
{!> ../../../../docs_src/settings/lazy_loader.py !}
```

## Multi-Stage Resolution

```python
{!> ../../../../docs_src/settings/multi_stage.py !}
```

## Temporary Settings Overrides

Use `with_settings(...)` for context-local overrides:

```python
with monkay.with_settings(custom_settings):
    monkay.evaluate_settings(onetime=False)
```

Use `with_settings(None)` to temporarily disable override and access the base
settings definition.

## Clearing Settings Cache

```python
monkay.clear_caches(settings_cache=True, import_cache=False)
```

## Settings Preloads and Extensions

- `settings_preloads_name` points to a list of preload strings
- `settings_extensions_name` points to extension objects/factories/classes

These are only evaluated when `evaluate_settings(...)` is called.

## Error Behavior

- Disabled/unset settings access raises `UnsetError`.
- Unknown `on_conflict` values raise `ValueError`.
- Import failures raise `ImportError` unless suppressed with
  `ignore_import_errors=True`.

## Related

- [Configuration reference](configuration.md)
- [Testing reference](testing.md)
- [Error handling guide](../guides/error-handling.md)
