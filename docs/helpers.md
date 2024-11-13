# Helpers


Monkay comes with some helpers

- `load(path, *, allow_splits=":.", package=None)`: Load a path like Monkay. `allow_splits` allows to configure if attributes are separated via . or :.
  When both are specified, both split ways are possible (Default).
- `load_any(module_path, potential_attrs, *, non_first_deprecated=False, package=None)`: Checks for a module if any attribute name matches. Return attribute value or raises ImportError when non matches.
  When `non_first_deprecated` is `True`, a DeprecationMessage is issued for the non-first attribute which matches. This can be handy for deprecating module interfaces.
- `absolutify_import(import_path, package)`. Converts a relative import_path (absolute import pathes are returned unchanged) to an absolute import path.

Example:

``` python

import os

from monkay import Monkay, load, load_any

monkay = Monkay(
    # required for autohooking
    globals(),
    lazy_imports={
        "bar": lambda: load_any("tests.targets.fn_module", ["bar", "bar_deprecated", "bar_deprecated2"], non_first_deprecated=True),
        # we can also pass environment variables. This one is evaluated when Monkay is created. It is quite limited.
        "dynamic": os.environ["DYNAMIC"],
        # this one is evaluated when calling dynamic2 and can be reevaulated by clearing the cache
        "dynamic2": lambda: load(os.environ["DYNAMIC"]),
    },
    deprecated_lazy_imports={
        "deprecated": {
            # manual load
            "path": lambda: load("tests.targets.fn_module:deprecated"),
            "reason": "old.",
            "new_attribute": "super_new",
        }
    },
)


```
