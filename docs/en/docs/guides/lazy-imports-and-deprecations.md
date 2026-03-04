# Lazy Imports and Deprecations

## Goal

Expose a stable module API while deferring heavyweight imports.

## Steps

1. Add lazy import entries in `Monkay(..., lazy_imports=...)`.
2. Add deprecated lazy imports for renamed attributes.
3. Keep `__all__` synchronized via automatic update or `update_all_var`.
4. Use `uncached_imports` for values that must refresh on each access.

## Example

See [Reference: tutorial](../reference/tutorial.md) and [Reference: specials](../reference/specials.md).

## Regression Checks

- Access each lazy attribute at least once in tests.
- Assert warning text for deprecated lazy imports.
- Validate exports using `find_missing()` in test helpers.
