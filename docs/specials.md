# Specials

## Overwriting the used package for relative imports

Provide the `package` parameter to Monkay. By default it is set to the `__spec__.parent` of the module.
For a toplevel module it is the same name like the module.

## Adding dynamically lazy imports

For adding lazy imports there are two methods:

- `add_lazy_import(export_name, path_or_fn, *, no_hooks=False)`: Adding new lazy import or fail if already exist.
- `add_deprecated_lazy_import(export_name, DeprecatedImport, *, no_hoosk=False)`: Adding new deprecated lazy import or fail if already exist.

By default the `__all__` variable is not modified but sometimes this is desirable.

For this cases hooks exist:

- `pre_add_lazy_import_hook(key, value, type_: Literal["lazy_import" | "deprecated_lazy_import"])`: Wrap around key and value and takes as third parameter the type.
- `post_add_lazy_import_hook(key)`: The way to go to update the `__all__` variable dynamically.

The hooks are only executed when manually adding a lazy import and not during the setup of Monkay.

### Example: Automatically update `__all__`

``` python

from monkay import Monkay

# we use a set
__all__ = {"bar"}

monkay = Monkay(
    # required for autohooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
    settings_path="settings_path:Settings",
    post_add_lazy_import_hook=__all__.add
)

if monkay.settings.with_deprecated:
    monkay.add_deprecated_lazy_import(
        "deprecated",
        {
            "path": "tests.targets.fn_module:deprecated",
            "reason": "old",
            "new_attribute": "super_new",
        }
    )
    # __all__ has now also deprecated when with_deprecated is true
```

### Example: prefix lazy imports

``` python

from monkay import Monkay

# we use a set
__all__ = {"bar"}

def prefix_fn(name: str, value: Any, type_: str) -> tuple[str, Any]:
    return f"{type_}_prefix_{name}", value

monkay = Monkay(
    # required for autohooking
    globals(),
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
    },
    pre_add_lazy_import_hook=prefix_fn,
    post_add_lazy_import_hook=__all__.add
)
monkay.add_deprecated_lazy_import(
    "deprecated",
    {
        "path": "tests.targets.fn_module:deprecated",
        "reason": "old",
        "new_attribute": "super_new",
    }
)
# __all__, lazy_imports has now also deprecated under a type prefix name
# but we can skip the hooks with no_hooks=True

monkay.add_deprecated_lazy_import(
    "deprecated",
    {
        "path": "tests.targets.fn_module:deprecated",
        "reason": "old",
        "new_attribute": "super_new",
    },
    no_hooks=True
)
```
