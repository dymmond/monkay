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
    """
    Represents an entry in a sorted list of module exports.

    This class encapsulates information about a module export, including its category,
    name, and path.
    """

    category: Literal["other", "lazy_import", "deprecated_lazy_import"]
    """The category of the export."""
    export_name: str
    """The name of the export."""
    path: str
    """The path to the export."""


class DeprecatedImport(TypedDict, total=False):
    """
    Represents a deprecated import with optional deprecation details.

    This class defines the structure for deprecated imports, including the import path,
    reason for deprecation, and a replacement attribute.
    """

    path: str | Callable[[], Any]
    """The import path of the deprecated object, or a callable that returns the object."""
    reason: str
    """The reason for deprecation."""
    new_attribute: str
    """The replacement attribute to use."""


DeprecatedImport.__required_keys__ = frozenset({"deprecated"})


class PRE_ADD_LAZY_IMPORT_HOOK(Protocol):
    """
    A protocol defining the signature for a hook that modifies lazy import definitions before they are added.

    This protocol specifies the expected signature for a hook function that can be used to modify
    lazy import definitions before they are added to the module. It supports both regular lazy imports
    and deprecated lazy imports.
    """

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
