# Release notes


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
