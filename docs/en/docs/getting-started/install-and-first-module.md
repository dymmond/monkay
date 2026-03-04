# Install and First Module

## Install

```shell
pip install monkay
```

## Minimal Setup

Create a package module that wires Monkay once and exports your lazy API:

```python title="yourpkg/__init__.py"
{!> ../../../../docs_src/tutorial/full_example_init.py}
```

Then use it from a runtime entrypoint:

```python title="yourpkg/main.py"
{!> ../../../../docs_src/tutorial/full_example_main.py}
```

## Verify Runtime Behavior

1. Access a lazy import and confirm it resolves on first use.
2. Call `evaluate_settings()` once startup configuration is ready.
3. If needed, call `evaluate_preloads()` explicitly in startup.

## Related Guides

- [Lazy imports and deprecations](../guides/lazy-imports-and-deprecations.md)
- [Testing with overrides](../guides/testing-with-overrides.md)
