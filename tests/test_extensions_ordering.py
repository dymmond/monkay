from __future__ import annotations

from types import SimpleNamespace

from monkay import Monkay


def test_apply_extensions_uses_extension_order_key_function() -> None:
    calls: list[str] = []

    class DemoExtension:
        def __init__(self, name: str) -> None:
            self.name = name

        def apply(self, monkay: Monkay) -> None:  # noqa: ARG002
            calls.append(self.name)

    monkay = Monkay(
        {"__spec__": SimpleNamespace(parent="", name="tests.extensions_ordering")},
        with_extensions=True,
        extension_order_key_fn=lambda extension: extension.name,
    )

    monkay.add_extension(DemoExtension("b"))
    monkay.add_extension(DemoExtension("a"))
    monkay.add_extension(DemoExtension("c"))

    monkay.apply_extensions()

    assert calls == ["a", "b", "c"]
