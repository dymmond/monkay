# Testing


## Temporary overwrites

For tests, but not limited to, Monkay provides three methods returning a contextmanager which provides threadsafe a temporary overwrite:

- `with_settings(settings)`
- `with_extensions(extensions_dict, *, apply_extensions=False)`
- `with_instance(instance, * apply_extensions=False,use_extensions_overwrite=True)`


## Check lazy imports

Monkay provides the debug method `find_missing(*, all_var=None, search_pathes=None, ignore_deprecated_import_errors=False, require_search_path_all_var=True)`.
It is quite expensive so it should be only called for debugging, testing and in error cases.
It returns a dictionary containing items which had issues, e.g. imports failed or not in `__all__` variable.

When providing `search_pathes` (module pathes as string), all exports are checked if they are in the value set of Monkey.

When providing `__all__` as `all_var`, it is checked for all imports.

Returned is a dictionary in the format:

- key: import name or import path
- value: set with errors

Errors:

- `all_var`: key is not in the provided `__all__` variable
- `import`: key had an ImportError
- `search_path_extra`: key (here a path) is not included in lazy imports.
- `search_path_import`: import of key (here the search path) failed
- `search_path_all_var`: module imported as search path had no `__all__`. This error can be disabled with `require_search_path_all_var=False`

### Ignore import errors when lazy import is deprecated

The parameter `ignore_deprecated_import_errors=True` silences errors happening when an lazy import which was marked as deprecated failed.

### Example

Using Monkay for tests is confortable and easy:

``` python

import edgy

def test_edgy_lazy_imports():
    assert not edgy.monkay.find_missing(all_var=edgy.__all__, search_pathes=["edgy.core.files", "edgy.core.db.fields", "edgy.core.connection"])

```

That was the test. Now we know that no lazy import is broken.
