# Testing with Overrides

Monkay’s context managers make tests isolated and deterministic.

## Common Patterns

- `with_instance(...)` for per-test runtime injection.
- `with_settings(...)` for temporary settings.
- `with_extensions(...)` for controlled extension sets.
- `with_full_overwrite(...)` for end-to-end environment overrides.

## Recommended Test Sequence

1. Arrange with a temporary override context.
2. Trigger `evaluate_settings()` / `apply_extensions()` explicitly.
3. Assert behavior.
4. Exit context and assert original state is restored.

## Reference

- [Reference: testing](../reference/testing.md)
- [Reference: settings](../reference/settings.md)
