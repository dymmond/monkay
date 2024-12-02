# Release notes

## Version 0.1.1

### Changed

- Initialize the getter and dir functions lazily when adding lazy imports.
- Guess attributes from `__all__` when `__getattr__` definition without `__dir__` function is found.

### Fixed

- Missing `__dir__` injection so lazy imports didn't show up in `dir()`.
- Error when adding lazy imports later without pre-existing lazy imports.

## Version 0.1.0

### Changed

- Internals refactored. `base.py` is splitted now in multiple submodules.
- Allow different settings than pydantic_settings.
- Switch to semantic versioning.
- Add cages (thread-safe, proxying contextvars).

### Fixed

- `with_instance` without `with_extensions` was not working.

## Version 0.0.9

### Added

- `apply_settings` parameter.
- `evaluate_settings` for lazy settings or settings overwrites.

### Fixed

- Lazy setup.

## Version 0.0.8

### Added

- Settings forwards
- `settings_path` parameter has now more allowed value types.
- Assignments to the settings attribute.
- `with_` and `set_` operations returning set object.

### Changed

- `settings_path=""` behaves now different (enables settings). The default switched to `None` (disabled settings).

### Removed

- Remove deprecated alias for `settings_preloads_name`.

### Fixed

- Use the right instance for apply_settings in set_instance.

## Version 0.0.7

### Fixed

- Missing py.typed.
- Fix double dot in reason. This parameter alone should control the punctuation.

## Version 0.0.6

### Fixed

- Re-exports were not detected correctly.

## Version 0.0.5

### Added

- `sorted_exports` for sorted `__all__` exports.
- Hooks for add_lazy_import, add_deprecated_lazy_import.

### Changed

- `find_missing` test method has some different error names.
- `find_missing` doesn't require the all_var anymore.

## Version 0.0.4

### Added

- `find_missing` test method.
- `getter` attribute saving the injected getter.
- `absolutify_import` helper.
- Add pre-commit.

### Changed

- Rename typo `settings_preload_name` to `settings_preloads_name`.
- Fix relative imports.

## Version 0.0.3

### Added

- Cache control utilities are added.

### Changed

- It is now allowed to provide own loaders instead of the path.

## Version 0.0.1

Initial release
