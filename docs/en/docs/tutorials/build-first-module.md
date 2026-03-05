# Build Your First Module

This walkthrough builds a minimal package that exports a lazy API surface.

## Step 1: Create package entrypoint

```python
{!> ../../../../docs_src/tutorial/full_example_init.py}
```

## Step 2: Use your package from runtime code

```python title="yourpkg/main.py"
{!> ../../../../docs_src/tutorial/full_example_main.py}
```

## Step 3: Validate behavior

1. Access a lazy export and confirm it resolves on first use.
2. Call `evaluate_settings()` during startup.
3. Ensure repeated calls are safe (`onetime=True` by default).

## Step 4: Run checks

```shell
task check
task docs
```

## Next

Continue with [Wire settings and extensions](settings-and-extensions.md).
