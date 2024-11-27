# Cages

Cages are transparent proxies to context variables. It forwards all function calls to the wrapped object so it behaves
normal in most cases like the original despite all operations are executed on the contextvar clone of the original.
The original is copied via copy or optionally via deepcopy.

This allows monkey patching other libraries which are not async safe. Even from other libraries,

## Usage

There are two ways

1. registering via self registering (recommended)
2. registering manually

The first way is recommended because it can be detected if it would nest another Cage object.
In this case it would just skip the initialization and the old Cage is kept.

Advantage of this: multiple libraries can patch other libraries without fearing to overwrite another cage.

``` python
from monkay import Cage

foo = []
foo2: list

# we can move an existing variable in a cage
Cage(globals(), name="foo", update_fn=lambda overwrite, new_original: new_original+overwrite)
# we can inject
Cage(globals(), [], name="foo2")
# we can manually assign
original: list = []
cage_for_original = Cage(globals(), name="original", skip_self_register=True)

foo.add("a")
foo.add("b")
assert foo == ["a", "b"]

with foo.monkay_with_override(["b", "c"]):
    assert foo == ["b", "c"]
assert foo == ["a", "b"]

with foo.monkay_with_original() as original:
    assert original == []
    original.append("updated")

# thanks to the update function
assert foo == ["updated", "a", "b"]
```

### With thread Lock

Cages are async safe designed. They can even protect updates of the original via locks.
With `use_wrapper_for_reads=True` inconsistent states for non-async safe copyable structures are prevented.

``` python
from threading import Lock
from monkay import Cage

foo: list
Cage(globals(), [], name="foo", original_wrapper=Lock(),  update_fn=lambda overwrite, new_original: new_original+overwrite)

# now threadsafe
with foo.monkay_with_original() as original:
    assert original == []
    original.append("updated")
```

### Preloads

Of course cages support also preloads. See [Tutorial](./tutorial.md) for examples and the syntax.


### Using deep copy

By default when no contextvariable was initialized the original is copied via `copy.copy()` into the contextvariable.
By providing `deep_copy=True` `copy.deepcopy()` is used.


## Advanced

### New context variable name

By default a context-variable is created and injected to globals with the pattern:

`"_{name}_ctx"` where name is the provided name.

You can define a different by providing the parameter

`context_var_name="different_pattern"` optionally with the name placeholder.

### Access proxied object direct

Proxying the context variable has a slight overhead. You can access the proxied object (the copy of the original in the contextvar)
via `cage.monkay_proxied()`.

### Skip wrapper

Sometimes you want to skip the wrapper for this call

`cage.monkay_with_original(use_wrapper=False)`

And if you want to persist the contextvar without wrapper despite having `use_wrapper_for_reads=True` set, use:

`cage.monkay_conditional_update_copy(use_wrapper=False)`

You can also do the inverse by calling, when having `use_wrapper_for_reads=False` (default):
`cage.monkay_conditional_update_copy(use_wrapper=True)`

Or disable/enable the wrapper for reading when accessing the proxied object directly (only when an update is happening)
`cage.monkay_proxied(use_wrapper=True)`
