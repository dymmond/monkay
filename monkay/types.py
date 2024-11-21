from __future__ import annotations

from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NamedTuple,
    Protocol,
    TypedDict,
    TypeVar,
    overload,
    runtime_checkable,
)

if TYPE_CHECKING:
    from .core import Monkay


INSTANCE = TypeVar("INSTANCE")
SETTINGS = TypeVar("SETTINGS")


@runtime_checkable
class ExtensionProtocol(Protocol[INSTANCE, SETTINGS]):
    name: str

    def apply(self, monkay_instance: Monkay[INSTANCE, SETTINGS]) -> None: ...


class SortedExportsEntry(NamedTuple):
    category: Literal["other", "lazy_import", "deprecated_lazy_import"]
    export_name: str
    path: str


class DeprecatedImport(TypedDict, total=False):
    path: str | Callable[[], Any]
    reason: str
    new_attribute: str


DeprecatedImport.__required_keys__ = frozenset({"deprecated"})


class PRE_ADD_LAZY_IMPORT_HOOK(Protocol):
    @overload
    @staticmethod
    def __call__(
        key: str,
        value: str | Callable[[], Any],
        type_: Literal["lazy_import"],
        /,
    ) -> tuple[str, str | Callable[[], Any]]: ...

    @overload
    @staticmethod
    def __call__(
        key: str,
        value: DeprecatedImport,
        type_: Literal["deprecated_lazy_import"],
        /,
    ) -> tuple[str, DeprecatedImport]: ...

    @staticmethod
    def __call__(
        key: str,
        value: str | Callable[[], Any] | DeprecatedImport,
        type_: Literal["lazy_import", "deprecated_lazy_import"],
        /,
    ) -> tuple[str, str | Callable[[], Any] | DeprecatedImport]: ...
