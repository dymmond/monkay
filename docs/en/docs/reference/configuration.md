# Configuration Reference

This page documents the primary `Monkay(...)` configuration parameters.

## Core Constructor Parameters

- `globals_dict`: module globals where Monkay installs hooks.
- `package`: package used to resolve relative import paths.
- `preloads`: preload modules/functions evaluated during initialization.
- `ignore_preload_import_errors`: continue on preload import errors.

## Lazy Import Configuration

- `lazy_imports`: mapping of export name -> import path or callable.
- `deprecated_lazy_imports`: mapping of export name -> deprecated import metadata.
- `uncached_imports`: names that must bypass lazy-import cache.
- `skip_all_update`: disable automatic `__all__` updates.
- `skip_getattr_fixup`: disable automatic `__dir__` fixup when `__getattr__` exists.
- `pre_add_lazy_import_hook`: mutate lazy import registration before insert.
- `post_add_lazy_import_hook`: callback invoked after successful insert.

## Settings Configuration

- `settings_path`: settings source (`str`, class, callable, or instance-like object).
- `settings_ctx_name`: context variable name used for temporary settings overrides.
- `settings_preloads_name`: attribute/key used to read settings preloads.
- `settings_extensions_name`: attribute/key used to read extension definitions.

## Instance and Extensions Configuration

- `with_instance`: enable instance management (bool or context var name).
- `with_extensions`: enable extension registry (bool or context var name).
- `extensions_applied_ctx_name`: context variable used while applying extensions.
- `extension_order_key_fn`: sort key used when applying extension set.

## Deprecated Constructor Parameters

- `evaluate_settings`: removed and must stay `None`.
- `ignore_settings_import_errors`: deprecated legacy compatibility parameter.

## Related

- [Settings reference](settings.md)
- [Specials](specials.md)
- [Tutorials](../tutorials/index.md)
