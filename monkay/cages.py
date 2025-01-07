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
    monkay_context_var: ContextVar[tuple[int | None, T] | type[Undefined]]
    monkay_deep_copy: bool
    monkay_use_wrapper_for_reads: bool
    monkay_update_fn: Callable[[T, T], T] | None
    monkay_name: str
    monkay_original: T
    monkay_original_last_update: int
    monkay_original_last_update_lock: None | Lock
    monkay_original_wrapper: AbstractContextManager

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
        """Sets the contextvar."""
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
        if name in forbidden_names or name.startswith("monkay_"):
            return super().__getattribute__(name)
        obj = self.monkay_conditional_update_copy()

        return getattr(obj, name)

    def __delattr__(
        self,
        name: str,
    ) -> None:
        if name.startswith("monkay_"):
            super().__delattr__(name)
            return
        obj = self.monkay_conditional_update_copy()
        delattr(obj, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("monkay_"):
            super().__setattr__(name, value)
            return
        obj = self.monkay_conditional_update_copy()
        setattr(obj, name, value)

    def monkay_proxied(
        self,
        use_wrapper: bool | None = None,
    ) -> T:
        return self.monkay_conditional_update_copy(use_wrapper=use_wrapper)

    @contextmanager
    def monkay_with_override(self, value: T, *, allow_value_update: bool = True) -> Generator[T]:
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
        monkay_dict = super().__getattribute__("__dict__")
        wrapper = monkay_dict["monkay_original_wrapper"] if use_wrapper else nullcontext()
        with wrapper:
            yield monkay_dict["monkay_original"]
            if update_after and monkay_dict["monkay_original_last_update_lock"] is not None:
                with monkay_dict["monkay_original_last_update_lock"]:
                    monkay_dict["monkay_original_last_update"] += 1

    def monkay_set(self, value: T) -> Token:
        monkay_dict = super().__getattribute__("__dict__")
        return monkay_dict["monkay_context_var"].set(
            (monkay_dict["monkay_original_last_update"], value)
        )

    def monkay_get(self, default: T | DEFAULT | None = None) -> T | DEFAULT | None:
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
        self.monkay_context_var.reset(token)


class TransparentCage(Cage):
    def __getattribute__(self, name: str) -> Any:
        if name in context_var_attributes:
            name = f"monkay_{name}"
        return super().__getattribute__(name)
