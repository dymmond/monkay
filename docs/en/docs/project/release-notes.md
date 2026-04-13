# Release Notes


## 0.5.3

### Added

- `CMToASGIMiddleware` to transform contextmanager into ASGI middleware.

### Fixed

- Export of `MuteInterruptException`.
- Fix spelling of `MuteInterruptException` the old name is still available.

## 0.5.2

### Added

- Runtime validation for extension/settings conflict policy values.
- Public API contract tests that lock exported symbols and call signatures.
- Regression tests for TypedDict schema metadata and concurrent ASGI lifespan isolation.
- Expanded documentation set: installation/compatibility, tutorials, error handling,
  performance best practices, configuration reference, and FAQ.
- `Taskfile.yml` alongside `Taskfile.yaml`, with standardized tasks:
  `lint`, `format`, `typecheck`, `test`, `coverage`, `docs`, `docs:serve`, `clean`, `check`.

### Changed

- `LifespanHook` now scopes shutdown setup state per lifespan invocation.
- README and documentation landing pages were reworked for clearer onboarding and navigation.

### Fixed

- `DeprecatedImport` TypedDict required-key metadata now correctly requires `path`.
- Documentation now reflects valid `on_conflict` values (`error`, `keep`, `replace`).

## 0.5.1

### Changed

- Feature assertions include now more documentation.
- Importloops cause better error messages.
- Deprecate the undocumented and defunct `ignore_settings_import_errors` parameter.
- Consistently raise ImportErrors instead of also raising AttributeErrors in load.

## 0.5.0

### Added

- ASGI lifespan support.

## 0.4.3

### Changed

- Removed support for Python 3.9.

### Fixed

- Broken internal import.
- License.

## 0.4.2

### Changed

- Parameter `apply_extensions` of `with_full_overwrite` defaults now to `False`.

### Fixed

- `with_full_overwrite` overwrote wrong settings/extensions due to a too early invocation.
- `with_full_overwrite` was not composable, the `apply_extensions` parameter worked only with an instance.

## 0.4.1

### Fixed

- Update settings_path typing. This was overlooked when updating the types.

## 0.4.0

### Added

- Add `with_full_overwrite` helper method which sets multiple contexts.
- Add `evaluate_settings_with` parameter to `with_settings`.

### Changed

- When string or class is provided by a callable for settings it is parsed and cached.
  This allows lazy parsing of environment variables, so they can be changed programmatically.
- Allow unsetting settings via `with_settings` by using `False` or `""`.

## 0.3.0

### Changed

- Emergency release removing implicit settings evaluation during `__init__`.
- `evaluate_settings` behaves like the previous `evaluate_settings_once`.
- Setting the `evaluate_settings` parameter in `__init__` is now an error.
- For `evaluate_settings(ignore_import_errors=...)`, the default changed to `False`.

### Added

- `evaluate_settings` has two extra keyword parameters: `onetime` and `ignore_preload_import_errors`.

### Deprecated

- `evaluate_settings_once` is deprecated.

## 0.2.2

### Added

- `UnsetError` for simpler checking if the settings are unset.

### Fixed

- Handle edge-cases better when settings are unset or disabled.
- Don't touch settings in `evaluate_settings` when not required.

## 0.2.1

### Fixed

- Add AttributeError to the ignored import errors.
- Wrong return value for `evaluate_settings_once` when already evaluated.

## 0.2.0

### Added

- Add `evaluate_settings_once`.
- Add `TransparentCage`, which also exposes the `ContextVar` interface.
- Add `monkay_` prefixed ContextVar-like attributes and methods.
- Add optional `allow_value_update` to `monkay_with_override` method on cage.

### Changed

- Monkay `__init__` uses `evaluate_settings_once` instead of `evaluate_settings`.
- Deleting the settings via assignment now also invalidates the cache.

### Fixed

- Assigning an empty dictionary to settings deleted settings; now limited to supported falsy values.
- Cage `with_overwrite` did not escape the last update component properly.

## 0.1.1

### Changed

- Initialize the getter and dir functions lazily when adding lazy imports.
- Guess attributes from `__all__` when `__getattr__` definition without `__dir__` function is found.

### Fixed

- Missing `__dir__` injection so lazy imports didn't show up in `dir()`.
- Error when adding lazy imports later without pre-existing lazy imports.

## 0.1.0

### Changed

- Internals refactored. `base.py` is split now into multiple submodules.
- Allow different settings than `pydantic_settings`.
- Switch to semantic versioning.
- Add cages (thread-safe, proxying contextvars).

### Fixed

- `with_instance` without `with_extensions` was not working.

## 0.0.9

### Added

- `apply_settings` parameter.
- `evaluate_settings` for lazy settings or settings overwrites.

### Fixed

- Lazy setup.

## 0.0.8

### Added

- Settings forwards.
- `settings_path` parameter has now more allowed value types.
- Assignments to the settings attribute.
- `with_` and `set_` operations returning set object.

### Changed

- `settings_path=""` behaves now different (enables settings).
  The default switched to `None` (disabled settings).

### Removed

- Remove deprecated alias for `settings_preloads_name`.

### Fixed

- Use the right instance for `apply_settings` in `set_instance`.

## 0.0.7

### Fixed

- Missing `py.typed`.
- Fix double dot in reason. This parameter alone should control punctuation.

## 0.0.6

### Fixed

- Re-exports were not detected correctly.

## 0.0.5

### Added

- `sorted_exports` for sorted `__all__` exports.
- Hooks for `add_lazy_import`, `add_deprecated_lazy_import`.

### Changed

- `find_missing` test method has some different error names.
- `find_missing` doesn't require `all_var` anymore.

## 0.0.4

### Added

- `find_missing` test method.
- `getter` attribute saving the injected getter.
- `absolutify_import` helper.
- Add pre-commit.

### Changed

- Rename typo `settings_preload_name` to `settings_preloads_name`.
- Fix relative imports.

## 0.0.3

### Added

- Cache control utilities are added.

### Changed

- It is now allowed to provide own loaders instead of the path.

## 0.0.1

### Added

- Initial release.
