# FAQ and Troubleshooting

## Why are my lazy imports not in `__all__`?

By default, Monkay updates `__all__` when lazy imports are registered.
If you pass `skip_all_update=True`, update manually with `update_all_var(...)`.

## Why does `monkay.settings` raise `UnsetError`?

Settings are disabled (`settings_path=None/False/""`) or the active settings
callable returned `None`.

## Why did `evaluate_settings()` return `False`?

You likely used `ignore_import_errors=True` and settings resolution failed.
Run again with `ignore_import_errors=False` to expose the underlying exception.

## Why does extension registration fail with `ValueError`?

- The object does not satisfy `ExtensionProtocol`, or
- `on_conflict` is not one of `error`, `keep`, `replace`.

## How do I debug export mismatches?

Use `find_missing(...)` from a configured module:

```python
missing = monkay.find_missing(all_var=True, search_pathes=["your.module"])
print(missing)
```

## How do I avoid state leakage in tests?

- Prefer `with_settings`, `with_extensions`, `with_instance`, and `with_full_overwrite`.
- Clean dynamically imported modules from `sys.modules` in test fixtures.
- Keep global mutable state inside cages or explicit fixtures.
