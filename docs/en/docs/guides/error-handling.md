# Error Handling

This guide explains common Monkay failures and how to diagnose them quickly.

## Import Resolution Errors

### Invalid import path (`load`)

`load()` raises `ValueError` for invalid path syntax and `ImportError` when
module/attribute resolution fails.

```python
from monkay import load

load("mypkg.module:missing")
```

### Circular import hints

When import resolution happens while a module is initializing, Monkay raises
an `ImportError` with a circular import hint.

## Settings Errors

### Settings disabled or unset

Accessing `monkay.settings` without an active settings definition raises
`UnsetError`.

### Unknown conflict policy

`evaluate_settings(on_conflict=...)` and `add_extension(on_conflict=...)`
accept only `"error"`, `"keep"`, and `"replace"`. Any other value raises `ValueError`.

## Extension Errors

- Duplicate extension name with `on_conflict="error"` -> `KeyError`
- Invalid extension object -> `ValueError`
- Recursive/concurrent apply process in same context -> `RuntimeError`

## ASGI Lifespan Errors

`Lifespan` raises `RuntimeError` for startup/shutdown protocol failures and
propagates task-level errors with explicit messages.

## Debugging Checklist

1. Verify import paths are absolute/relative as expected for your package.
2. Confirm startup sequence calls `evaluate_settings()` at the correct stage.
3. Run `task test` and isolate failing behavior in a regression test.
4. Use `find_missing(...)` to inspect module export inconsistencies.
