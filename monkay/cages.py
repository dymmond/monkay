from __future__ import annotations

import copy
from collections.abc import Callable, Generator, Iterable
from contextlib import AbstractContextManager, contextmanager, nullcontext
from contextvars import ContextVar, Token
from functools import wraps
from importlib import import_module
from inspect import ismethoddescriptor
from threading import Lock
from typing import Any, Generic, TypeVar, cast


class Undefined: ...


T = TypeVar("T")
DEFAULT = TypeVar("DEFAULT")

forbidden_names: set[str] = {
    "__getattribute__",
    "__setattr__",
    "__delattr__",
    "__new__",
    "__init__",
}
context_var_attributes: set[str] = {"name", "get", "set", "reset"}


class Cage(Generic[T]):
    """
    A container class that manages a value with context-aware modifications and synchronization.
    """

    monkay_context_var: ContextVar[tuple[int | None, T] | type[Undefined]]
    """
    A context variable that stores the current value and update timestamp within a specific context.
    This allows for context-specific modifications and retrieval of the value.
    """

    monkay_deep_copy: bool
    """
    A boolean indicating whether deep copies should be used when modifying the value.
    If True, modifications will create deep copies of the original value to avoid unintended side effects.
    """

    monkay_use_wrapper_for_reads: bool
    """
    A boolean indicating whether a wrapper should be used for read operations.
    If True, read operations will be wrapped in a context manager to ensure consistency.
    """

    monkay_update_fn: Callable[[T, T], T] | None
    """
    An optional function that defines how to update the value when modifications are made.
    This function takes the current value and the new value as input and returns the updated value.
    """

    monkay_name: str
    """
    A name associated with the Cage instance, used for identification and debugging purposes.
    """

    monkay_original: T
    """
    The original value stored in the Cage instance.
    This attribute holds the initial value that is managed by the Cage.
    """

    monkay_original_last_update: int
    """
    A timestamp indicating the last time the original value was updated.
    This timestamp is used to track changes and ensure consistency.
    """

    monkay_original_last_update_lock: None | Lock
    """
    An optional lock used to synchronize updates to the original value.
    This lock prevents race conditions when multiple threads or processes try to update the value concurrently.
    """

    monkay_original_wrapper: AbstractContextManager
    """
    A context manager used to wrap access to the original value, ensuring consistency and synchronization.
    This wrapper provides a controlled environment for read and write operations on the original value.
    """

    def __new__(
        cls,
        globals_dict: dict,
        obj: T | type[Undefined] = Undefined,
        *,
        name: str,
        preloads: Iterable[str] = (),
        context_var_name: str = "_{name}_ctx",
        deep_copy: bool = False,
        # for e.g. locks
        original_wrapper: AbstractContextManager = nullcontext(),
        update_fn: Callable[[T, T], T] | None = None,
        use_wrapper_for_reads: bool = False,
        skip_self_register: bool = False,
        package: str | None = "",
    ) -> Cage:
        """
        Creates a new Cage instance, wrapping an object and managing its context.

        This method initializes a Cage instance, wrapping the provided object and setting up
        context management. It handles preloads, context variable creation, and attribute forwarding.

        Args:
            globals_dict: The globals dictionary of the module where the Cage is created.
            obj: The object to wrap, or Undefined to retrieve it from globals_dict.
            name: The name of the object.
            preloads: An iterable of preload paths to execute before creating the Cage.
            context_var_name: The name of the context variable to create.
            deep_copy: If True, uses deep copies for modifications.
            original_wrapper: A context manager to wrap access to the original object.
            update_fn: An optional function to define how to update the object.
            use_wrapper_for_reads: If True, uses the wrapper for read operations.
            skip_self_register: If True, skips registering the Cage instance in globals_dict.
            package: The package name to use for relative imports.

        Returns:
            A new Cage instance.

        Raises:
            AssertionError: If the object is Undefined and not found in globals_dict.
            ImportError: If a preload module cannot be imported.
            AttributeError: If a preload function cannot be found.
        """
        if package == "" and globals_dict.get("__spec__"):
            package = globals_dict["__spec__"].parent
        package = package or None
        for preload in preloads:
            splitted = preload.rsplit(":", 1)
            try:
                module = import_module(splitted[0], package)
            except ImportError:
                module = None
            if module is not None and len(splitted) == 2:
                getattr(module, splitted[1])()
        if obj is Undefined:
            obj = globals_dict[name]
        assert obj is not Undefined
        if not skip_self_register and isinstance(obj, Cage):
            return obj
        context_var_name = context_var_name.format(name=name)
        obj_type = type(obj)
        attrs: dict = {}
        for attr in dir(obj_type):
            if not attr.startswith("__") or not attr.endswith("__") or attr in forbidden_names:
                continue
            val = getattr(obj_type, attr)
            if ismethoddescriptor(val):
                # we need to add the wrapper to the dict
                attrs[attr] = cls.monkay_forward(obj_type, attr)
        attrs["__new__"] = object.__new__
        monkay_cage_cls = type(cls.__name__, (cls,), attrs)
        monkay_cage_instance = monkay_cage_cls()
        monkay_cage_instance.monkay_name = name
        monkay_cage_instance.monkay_context_var = globals_dict[context_var_name] = ContextVar(
            context_var_name, default=Undefined
        )
        monkay_cage_instance.monkay_deep_copy = deep_copy
        monkay_cage_instance.monkay_use_wrapper_for_reads = use_wrapper_for_reads
        monkay_cage_instance.monkay_update_fn = update_fn
        monkay_cage_instance.monkay_original = obj
        monkay_cage_instance.monkay_original_last_update = 0
        monkay_cage_instance.monkay_original_last_update_lock = (
            None if update_fn is None else Lock()
        )
        monkay_cage_instance.monkay_original_wrapper = original_wrapper

        if not skip_self_register:
            globals_dict[name] = monkay_cage_instance
        return monkay_cage_instance

    @classmethod
    def monkay_forward(cls, obj_type: type, name: str) -> Any:
        """
        Creates a wrapper function that forwards method calls to the wrapped object.

        This class method generates a wrapper function that intercepts method calls to the Cage instance
        and forwards them to the wrapped object, ensuring that the object is updated or copied as needed.

        Args:
            obj_type: The type of the wrapped object.
            name: The name of the method to forward.

        Returns:
            A wrapper function that forwards method calls.
        """

        @wraps(getattr(obj_type, name))
        def _(self, *args: Any, **kwargs: Any):
            obj = self.monkay_conditional_update_copy()
            return getattr(obj, name)(*args, **kwargs)

        return _

    def monkay_refresh_copy(
        self,
        *,
        obj: T | type[Undefined] = Undefined,
        use_wrapper: bool | None = None,
        _monkay_dict: dict | None = None,
    ) -> T:
        """
        Refreshes the context variable with a copy of the original object.

        This method updates the context variable with a fresh copy of the original object,
        optionally using a wrapper and handling deep or shallow copies.

        Args:
            obj: An optional object to use instead of creating a copy.
            use_wrapper: If True, uses the original wrapper when accessing the original object.
                         If None, uses the Cage's default `monkay_use_wrapper_for_reads` value.
            _monkay_dict: An optional dictionary to use instead of the Cage's `__dict__`.

        Returns:
            The refreshed object.
        """
        if _monkay_dict is None:
            _monkay_dict = super().__getattribute__("__dict__")
        if use_wrapper is None:
            use_wrapper = _monkay_dict["monkay_use_wrapper_for_reads"]
        if obj is Undefined:
            with _monkay_dict["monkay_original_wrapper"] if use_wrapper else nullcontext():
                obj = (
                    copy.deepcopy(_monkay_dict["monkay_original"])
                    if _monkay_dict["monkay_deep_copy"]
                    else copy.copy(_monkay_dict["monkay_original"])
                )
        _monkay_dict["monkay_context_var"].set((_monkay_dict["monkay_original_last_update"], obj))
        return cast(T, obj)

    def monkay_conditional_update_copy(
        self, *, use_wrapper: bool | None = None, _monkay_dict: dict | None = None
    ) -> T:
        """
        Retrieves a context-aware copy of the original object, updating it if necessary.

        This method retrieves a copy of the original object, updating it based on context and update functions.
        It checks if the context variable is set and if the original object has been updated, and applies
        the update function if necessary.

        Args:
            use_wrapper: If True, uses the original wrapper when accessing the original object.
                         If None, uses the Cage's default `monkay_use_wrapper_for_reads` value.
            _monkay_dict: An optional dictionary to use instead of the Cage's `__dict__`.

        Returns:
            The context-aware copy of the object.
        """
        if _monkay_dict is None:
            _monkay_dict = super().__getattribute__("__dict__")
        if use_wrapper is None:
            use_wrapper = _monkay_dict["monkay_use_wrapper_for_reads"]
        tup = _monkay_dict["monkay_context_var"].get()
        if tup is Undefined:
            obj = self.monkay_refresh_copy(_monkay_dict=_monkay_dict)
        elif (
            _monkay_dict["monkay_update_fn"] is not None
            and tup[0] is not None
            and tup[0] != _monkay_dict["monkay_original_last_update"]
        ):
            with _monkay_dict["monkay_original_wrapper"] if use_wrapper else nullcontext():
                obj = _monkay_dict["monkay_update_fn"](tup[1], _monkay_dict["monkay_original"])
            obj = self.monkay_refresh_copy(
                obj=obj, _monkay_dict=_monkay_dict, use_wrapper=use_wrapper
            )
        else:
            obj = tup[1]
        return obj

    def __getattribute__(self, name: str) -> Any:
        """
        Overrides attribute access to retrieve attributes from the context-aware copy.

        This method intercepts attribute access and retrieves the attribute from the context-aware copy
        of the object, ensuring that the object is updated as needed.

        Args:
            name: The name of the attribute to retrieve.

        Returns:
            The retrieved attribute value.
        """
        if name in forbidden_names or name.startswith("monkay_"):
            return super().__getattribute__(name)
        obj = self.monkay_conditional_update_copy()

        return getattr(obj, name)

    def __delattr__(
        self,
        name: str,
    ) -> None:
        """
        Overrides attribute deletion to delete attributes from the context-aware copy.

        This method intercepts attribute deletion and deletes the attribute from the context-aware copy
        of the object, ensuring that the object is updated as needed.

        Args:
            name: The name of the attribute to delete.
        """
        if name.startswith("monkay_"):
            super().__delattr__(name)
            return
        obj = self.monkay_conditional_update_copy()
        delattr(obj, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Overrides attribute setting to set attributes in the context-aware copy.

        This method intercepts attribute setting and sets the attribute in the context-aware copy
        of the object, ensuring that the object is updated as needed.

        Args:
            name: The name of the attribute to set.
            value: The value to set the attribute to.
        """
        if name.startswith("monkay_"):
            super().__setattr__(name, value)
            return
        obj = self.monkay_conditional_update_copy()
        setattr(obj, name, value)

    def monkay_proxied(
        self,
        use_wrapper: bool | None = None,
    ) -> T:
        """
        Returns a proxied version of the object, ensuring context-aware updates.

        This method returns a context-aware copy of the object, optionally using a wrapper.

        Args:
            use_wrapper: If True, uses the original wrapper when accessing the original object.
                         If None, uses the Cage's default `monkay_use_wrapper_for_reads` value.

        Returns:
            The proxied object.
        """
        return self.monkay_conditional_update_copy(use_wrapper=use_wrapper)

    @contextmanager
    def monkay_with_override(self, value: T, *, allow_value_update: bool = True) -> Generator[T]:
        """
        Temporarily overrides the context variable with a new value within a context.

        This context manager temporarily sets the context variable to a new value and yields it.
        After the context exits, the original context variable is restored.

        Args:
            value: The new value to set the context variable to.
            allow_value_update: If True, allows the value to be updated by the update function.
                                If False, the value will not be updated.

        Yields:
            The new value.
        """
        monkay_dict = super().__getattribute__("__dict__")
        token = monkay_dict["monkay_context_var"].set(
            (monkay_dict["monkay_original_last_update"] if allow_value_update else None, value)
        )
        try:
            yield value
        finally:
            monkay_dict["monkay_context_var"].reset(token)

    @contextmanager
    def monkay_with_original(
        self, use_wrapper: bool = True, update_after: bool = True
    ) -> Generator[T]:
        """
        Temporarily accesses the original value within a context, optionally updating it.

        This context manager yields the original value, optionally using a wrapper and updating
        the last update timestamp after the context exits.

        Args:
            use_wrapper: If True, uses the original wrapper when accessing the original value.
            update_after: If True, updates the last update timestamp after the context exits.

        Yields:
            The original value.
        """
        monkay_dict = super().__getattribute__("__dict__")
        wrapper = monkay_dict["monkay_original_wrapper"] if use_wrapper else nullcontext()
        with wrapper:
            yield monkay_dict["monkay_original"]
            if update_after and monkay_dict["monkay_original_last_update_lock"] is not None:
                with monkay_dict["monkay_original_last_update_lock"]:
                    monkay_dict["monkay_original_last_update"] += 1

    def monkay_set(self, value: T) -> Token:
        """
        Sets the context variable to a new value and returns a token.

        This method sets the context variable to a new value and returns a token that can be used
        to reset the context variable to its previous value.

        Args:
            value: The new value to set the context variable to.

        Returns:
            A token that can be used to reset the context variable.
        """
        monkay_dict = super().__getattribute__("__dict__")
        return monkay_dict["monkay_context_var"].set(
            (monkay_dict["monkay_original_last_update"], value)
        )

    def monkay_get(self, default: T | DEFAULT | None = None) -> T | DEFAULT | None:
        """
        Retrieves the current value of the context variable, or a default value if it's not set.

        This method retrieves the current value of the context variable. If the context variable is not set,
        it returns the original value or a default value if provided.

        Args:
            default: The default value to return if the context variable is not set.

        Returns:
            The current value of the context variable, the original value, or the default value.
        """
        monkay_dict = super().__getattribute__("__dict__")
        tup: type[Undefined] | tuple[int | None, T] = monkay_dict["monkay_context_var"].get()
        if tup is Undefined:
            original: T | type[Undefined] = monkay_dict["monkay_original"]
            if original is not Undefined:
                return cast("DEFAULT | None", original)
            else:
                return default
        else:
            return cast("tuple[int | None, T]", tup)[1]

    def monkay_reset(self, token: Token):
        """
        Resets the context variable to its previous value using a token.

        This method resets the context variable to its previous value using a token returned by `monkay_set`.

        Args:
            token: The token returned by `monkay_set`.
        """
        self.monkay_context_var.reset(token)


class TransparentCage(Cage):
    """
    A transparent Cage subclass that exposes context variable attributes directly.

    This subclass of Cage allows direct access to context variable attributes (e.g., 'get', 'set', 'reset')
    without requiring the 'monkay_' prefix. It provides a more transparent interface for interacting
    with context-aware values.
    """

    def __getattribute__(self, name: str) -> Any:
        """
        Overrides attribute access to expose context variable attributes directly.

        This method intercepts attribute access and exposes context variable attributes without
        the 'monkay_' prefix.

        Args:
            name: The name of the attribute to retrieve.

        Returns:
            The retrieved attribute value.
        """
        if name in context_var_attributes:
            name = f"monkay_{name}"
        return super().__getattribute__(name)
