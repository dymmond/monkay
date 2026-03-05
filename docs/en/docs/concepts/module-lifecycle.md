# Module Lifecycle

Monkay sits between module import-time and runtime access.

## Flow

```mermaid
flowchart TD
    A["Import module"] --> B["Monkay(...) initializes hooks"]
    B --> C["Lazy import requested"]
    C --> D{"Cached?"}
    D -- "Yes" --> E["Return cached object"]
    D -- "No" --> F["Load path or call factory"]
    F --> G{"Uncached import?"}
    G -- "Yes" --> H["Return object without caching"]
    G -- "No" --> I["Store in cache and return"]
```

## Key Implications

- Lazy imports are resolved by module-level `__getattr__`.
- Optional uncached imports keep values dynamic per access.
- Deprecated lazy imports issue warnings while preserving compatibility.

## Related

- [Reference: tutorial](../reference/tutorial.md)
- [Guide: lazy imports and deprecations](../guides/lazy-imports-and-deprecations.md)
