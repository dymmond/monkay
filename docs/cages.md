---
hide:
  - navigation
---

# Cages

**Cages** are transparent proxies to context variables. They forward all function calls to the wrapped object, making it behave normally in most cases, just like the original. However, all operations are executed on a **ContextVar** clone of the original object. The original is copied via `copy.copy()` by default, or optionally via `copy.deepcopy()` for deep copies.

**Monkay** Cages allow for monkey-patching other libraries that are not async-safe. This is especially useful in scenarios where you need to wrap or proxy non-async-safe code for compatibility with an asynchronous application, ensuring safe operations even in multi-threaded contexts.

---

## Usage

There are two ways to register a Cage:

1. **Self-registering (Recommended)**
2. **Manual registration**

The **self-registering** method is recommended because it can automatically detect if another Cage object is
nested within it. In such cases, it skips re-initializing the Cage and keeps the existing one, ensuring that
multiple libraries can patch other libraries without fear of overwriting each other’s Cages.

### Example: Self-registering Cage

```python
from monkay import Cage

foo = []
foo2: list

# Move an existing variable into a cage
Cage(globals(), name="foo", update_fn=lambda overwrite, new_original: new_original + overwrite)

# Inject a new Cage
Cage(globals(), [], name="foo2")

# Manually assign
original: list = []
cage_for_original = Cage(globals(), name="original", skip_self_register=True)

foo.append("a")
foo.append("b")
assert foo == ["a", "b"]

with foo.monkay_with_override(["b", "c"]):
    assert foo == ["b", "c"]
assert foo == ["a", "b"]

with foo.monkay_with_original() as original:
    assert original == []
    original.append("updated")

# Thanks to the update function
assert foo == ["updated", "a", "b"]
```

### `monkay_with_override` Method

The `monkay_with_override` method allows you to override the current value in the **Cage** with new data for a
limited scope. It takes two arguments:

- **overwrite** (Mandatory): The new value you want to assign to the context variable.
- **allow_value_update** (Keyword-only, default: `True`): Allows updating the original value when the context
- variable is updated.

If `allow_value_update` is `True`, when the original value is updated, the local value in the context variable
is also updated.

---

## With Thread Lock

**Cages** are designed to be **async-safe**, meaning they can be safely used in asynchronous environments.
Additionally, they can protect updates to the original object using locks to ensure thread safety.

### Example: Using Thread Lock for Safety

```python
from threading import Lock
from monkay import Cage

foo: list
Cage(globals(), [], name="foo", original_wrapper=Lock(), update_fn=lambda overwrite, new_original: new_original + overwrite)

# Now threadsafe
with foo.monkay_with_original() as original:
    assert original == []
    original.append("updated")
```

In the above example, we use a `Lock()` to ensure that updates to the original object are done safely in a
multi-threaded environment.

---

## Preloads

Cages also support **preloads**, which are useful for setting initial values before any operation happens.
Preloads allow you to provide default values or configurations before any context variable manipulation occurs.

For a detailed explanation and syntax of preloading, please refer to the [Tutorial](./tutorial.md).

---

## Using Deep Copy

By default, when no context variable has been initialized, the original object is copied via `copy.copy()`
into the context variable. However, if you require a deep copy of the original object (to avoid shallow copying issues), you can provide the `deep_copy=True` parameter when initializing the Cage.

```python
Cage(globals(), name="foo", deep_copy=True)
```

This ensures that the original object is copied deeply, meaning all nested objects are also copied, rather
than simply referenced.

---

## TransparentCage

**TransparentCage** is a subclass of `Cage` that exposes a **ContextVar-like** interface. It behaves as a container
for the context variable while also allowing you to interact with it like a `ContextVar`.

In simpler terms, a `TransparentCage` is just a **Cage** that behaves exactly like a context variable but with
additional functionality.

### Public Methods:
- `monkay_name`
- `monkay_set`
- `monkay_reset`
- `monkay_get`

These methods are essentially prefixes to the corresponding **ContextVar** methods. The **TransparentCage** simply
redirects these methods to the underlying **ContextVar**, providing additional context handling.

---

## Advanced Features

### New Context Variable Name

By default, when a context variable is created, it is injected into the global scope with the name pattern: `"_{name}_ctx"`, where `name` is the provided name. You can define a custom name pattern for the context variable by providing the `context_var_name` parameter.

```python
Cage(globals(), name="foo", context_var_name="custom_pattern_{name}_ctx")
```

### Accessing the Proxied Object Directly

Proxying the context variable introduces slight overhead. If you need to access the proxied object directly (the copy of the original object stored in the context variable), you can use the `monkay_proxied()` method.

```python
foo_copy = foo.monkay_proxied()
```

This will give you direct access to the proxied object, bypassing the normal context variable proxying.

### Skipping the Wrapper

In some cases, you may want to skip the wrapper for a specific operation. You can do this using the `monkay_with_original()` method with the `use_wrapper=False` argument:

```python
with foo.monkay_with_original(use_wrapper=False):
    # Perform operations directly on the original without the wrapper
    pass
```

Alternatively, if you want to persist the context variable without the wrapper, you can use the `monkay_conditional_update_copy()` method:

```python
foo.monkay_conditional_update_copy(use_wrapper=False)
```

This allows you to control the application of the wrapper at runtime for more granular control.

---

### Managing Wrapper Usage

If you have specific needs regarding wrapper usage when accessing proxied objects, **Monkay** gives you
fine-grained control:

- **When reading the proxied object** (with no updates happening):
  You can control the wrapper usage with `use_wrapper=True` or `use_wrapper=False` based on your needs.

- **When updating**:
  You can toggle whether to use the wrapper with `monkay_proxied(use_wrapper=True)` or `monkay_proxied(use_wrapper=False)` based on the operation you're performing.

---

## Summary of Key Features

- **Transparent Proxying**: Cages act as transparent proxies to context variables, allowing you to work with non-async-safe libraries in an async environment.
- **Self-registration**: Automatically registers cages and prevents overwriting, ensuring compatibility with multiple libraries.
- **Thread-Safe Operations**: Cages can be used safely in multi-threaded applications with locks for protecting updates.
- **Preloads and Deep Copies**: Support for preloading values and deep copies for more complex structures.
- **Direct Access to Proxied Objects**: Access the original object in the context variable via `monkay_proxied()`.
- **Wrapper Control**: Flexibility to skip or control the wrapper around the proxied object when required.
