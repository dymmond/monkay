# Helpers


Monkay comes with two helpers

- `load(path, allow_splits=":.")`: Load a path like Monkay. `allow_splits` allows to configure if attributes are seperated via . or :.
  When both are specified, both split ways are possible (Default).
- `load_any(module_path, potential_attrs, *, non_first_deprecated=False)`: Checks for a module if any attribute name matches. Return attribute value or raises ImportError when non matches.
  When `non_first_deprecated` is `True`, a DeprecationMessage is issued for the non-first attribute which matches. This can be handy for deprecating module interfaces.
