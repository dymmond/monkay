# Performance and Best Practices

## Lazy Import Strategy

- Prefer string lazy imports for static references.
- Use callable lazy imports only when values must be computed dynamically.
- Keep `uncached_imports` small and explicit.

## Settings Lifecycle

- Evaluate settings once at startup when possible.
- Use `with_settings(...)` for tests/sub-scopes rather than mutating global state.
- Call `clear_caches(settings_cache=True)` only when runtime config changed.

## Extension Lifecycle

- Keep `apply()` methods idempotent and side-effect conscious.
- Use `extension_order_key_fn` when ordering matters.
- Prefer explicit conflict policies (`error`, `keep`, `replace`).

## Cages

- Use shallow copy (`deep_copy=False`) unless deep isolation is required.
- Provide `update_fn` only when synchronizing background mutations is necessary.
- Keep wrapped objects reasonably small; copied state scales with object size.

## ASGI Lifespan

- Scope setup resources via `AsyncExitStack` and always release on shutdown.
- Keep startup/shutdown operations bounded and predictable.
- Use `Lifespan(timeout=...)` in tests to catch hangs early.

## Quality Gates

Run these in local/CI loops:

```shell
task check
task coverage
task docs
```
