from typing import Any

from monkay import Monkay


def prefix_fn(name: str, value: Any, type_: str) -> tuple[str, Any]:
    return f"{type_}_{name}", value


__all__ = {"foo", "monkay"}  # noqa
monkay = Monkay(
    globals(),
    lazy_imports={
        "bar": ".fn_module:bar",
    },
    deprecated_lazy_imports={
        "deprecated": {
            "path": "tests.targets.fn_module:deprecated",
            "reason": "old.",
            "new_attribute": "super_new",
        }
    },
    pre_add_lazy_import_hook=prefix_fn,
    post_add_lazy_import_hook=__all__.add,
)
