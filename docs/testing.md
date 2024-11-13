# Testing


## Temporary overwrites

For tests, but not limited to, Monkay provides three methods returning a contextmanager which provides threadsafe a temporary overwrite:

- `with_settings(settings)`
- `with_extensions(extensions_dict, *, apply_extensions=False)`
- `with_instance(instance, * apply_extensions=False,use_extensions_overwrite=True)`


## Check imports and exports

Monkay provides the debug method `find_missing(*, all_var=True, search_pathes=None, ignore_deprecated_import_errors=False, require_search_path_all_var=True)`.
It is quite expensive so it should be only called for debugging, testing and in error cases.
It returns a dictionary containing items which had issues, e.g. imports failed or not in `__all__` variable.

When providing `search_pathes` (module pathes as string), all exports are checked if they are in the value set of Monkey.

When providing `__all__` or `True` as `all_var`, the variable or in case of `True` the module `__all__` is checked for missing exports/imports.

Returned is a dictionary in the format:

- key: import name or import path
- value: set with errors

Errors:

- `not_in_all_var`: Key is not in the provided `__all__` variable.
- `missing_attr`: Key (path) which was defined in an `__all__` variable does not exist or raises an AttributeError.
- `missing_all_var`: Key (search path or main module) had no `__all__`. For search pathes this error can be disabled via `require_search_path_all_var=False`.
- `import`: Key (module or function) raised an ImportError.
- `shadowed`: Key is defined as lazy_import  but defined in the main module so the lazy import is not used.
- `search_path_extra`: Key (path) is not included in lazy imports.
- `search_path_import`: Import of key (here the search path) failed.

### Ignore import errors when lazy import is deprecated

The parameter `ignore_deprecated_import_errors=True` silences errors happening when an lazy import which was marked as deprecated failed.

### Example

Using Monkay for tests is confortable and easy:

``` python

import edgy

def test_edgy_lazy_imports():
    missing = edgy.monkay.find_missing(all_var=edgy.__all__, search_pathes=["edgy.core.files", "edgy.core.db.fields", "edgy.core.connection"])
    # remove false positives
    if missing["AutoNowMixin"] == {"AutoNowMixin"}:
        del missing["AutoNowMixin"]
    assert not missing

```

That was the test. Now we know that no lazy import is broken.
