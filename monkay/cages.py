from __future__ import annotations

import copy
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from contextvars import ContextVar
from inspect import isclass
from threading import Lock
from typing import Any, Generic, TypeVar, cast


class Undefined: ...


T = TypeVar("T")


class Cage(Generic[T]):
    monkay_original_last_update: int

    def __init__(
        self,
        globals_dict: dict,
        obj: T | type[Undefined] = Undefined,
        *,
        name: str | None = None,
        context_var_name: str = "_{name}_ctx",
        deep_copy: bool = False,
        # for e.g. locks
        original_wrapper: AbstractContextManager = nullcontext(),
        update_fn: Callable[[T, T], T] | None = None,
    ):
        if name is None:
            assert obj is not Undefined
            name = obj.__name__ if isclass(obj) else type(obj).__name__
        elif obj is Undefined:
            obj = globals_dict[name]
        assert obj is not Undefined
        context_var_name = context_var_name.format(name=name)
        self.monkay_context_var = globals_dict[context_var_name] = ContextVar[
            tuple[int, T] | type[Undefined]
        ](context_var_name, default=Undefined)
        self.monkay_deep_copy = deep_copy
        self.monkay_update_fn = update_fn
        self.monkay_original = obj
        self.monkay_original_last_update = 0
        self.monkay_original_last_update_lock = None if update_fn is None else Lock()
        self.monkay_original_wrapper = original_wrapper

    def monkay_refresh_copy(
        self, *, obj: T | type[Undefined] = Undefined, _monkay_dict: dict | None = None
    ) -> T:
        if _monkay_dict is None:
            _monkay_dict = super().__getattribute__("__dict__")
        if obj is Undefined:
            obj = (
                copy.deepcopy(_monkay_dict["monkay_original"])
                if _monkay_dict["monkay_deep_copy"]
                else copy.copy(_monkay_dict["monkay_original"])
            )
        _monkay_dict["monkay_context_var"].set(_monkay_dict["monkay_original_last_update"], obj)
        return cast(T, obj)

    def monkay_conditional_update_copy(self, *, _monkay_dict: dict | None = None) -> T:
        if _monkay_dict is None:
            _monkay_dict = super().__getattribute__("__dict__")
        tup = _monkay_dict["monkay_context_var"].get()
        if tup is Undefined:
            obj = self.monkay_refresh_copy(_monkay_dict=_monkay_dict)
        elif (
            _monkay_dict["monkay_update_fn"] is not None
            and tup[0] != _monkay_dict["monkay_original_last_update"]
        ):
            obj = _monkay_dict["monkay_update_fn"](obj, _monkay_dict["monkay_original"])
            obj = self.monkay_refresh_copy(obj=obj, _monkay_dict=_monkay_dict)
        else:
            obj = tup[1]
        return obj

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("monkay_") or name == "__setattr__":
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

    @contextmanager
    def monkay_with_override(self, value: T) -> Generator[T]:
        monkay_dict = super().__getattribute__("__dict__")
        token = monkay_dict["monkay_context_var"].set(value)
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
