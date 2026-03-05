# Wire Settings and Extensions

This tutorial demonstrates controlled settings resolution and extension application.

## Step 1: Configure Monkay with settings hooks

```python title="package/__init__.py"
from monkay import Monkay

monkay = Monkay(
    globals(),
    with_instance=True,
    with_extensions=True,
    settings_path="myproject.settings:Settings",
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
)
```

## Step 2: Evaluate settings at startup

```python
monkay.evaluate_settings(on_conflict="error")
```

`on_conflict` accepts only:

- `"error"`
- `"keep"`
- `"replace"`

## Step 3: Attach runtime instance

```python
app = object()
monkay.set_instance(app)
```

## Step 4: Test overrides safely

```python
with monkay.with_settings(False):
    ...

with monkay.with_extensions({}):
    ...

with monkay.with_instance(None):
    ...
```

## Related

- [Settings reference](../reference/settings.md)
- [Testing with overrides](../guides/testing-with-overrides.md)
- [Error handling](../guides/error-handling.md)
