import contextlib
import sys
from io import StringIO

import pytest

from monkay import Monkay


@pytest.fixture(autouse=True, scope="function")
def cleanup():
    for name in [
        "module_full_preloaded1_fn",
        "module_full_preloaded1",
        "module_preloaded1",
        "module_full",
        "fn_module",
    ]:
        sys.modules.pop(f"tests.targets.{name}", None)
    yield


def test_preloaded():
    assert "tests.targets.module_full" not in sys.modules
    import tests.targets.module_full as mod

    assert "tests.targets.fn_module" not in sys.modules

    assert "tests.targets.module_full" in sys.modules
    assert "tests.targets.module_full_preloaded1" in sys.modules
    assert "tests.targets.module_full_preloaded1_fn" in sys.modules
    assert "tests.targets.module_preloaded1" in sys.modules
    assert "tests.targets.extension" in sys.modules

    with contextlib.redirect_stdout(StringIO()):
        mod.bar  # noqa

    assert "tests.targets.fn_module" in sys.modules


def test_attrs():
    import tests.targets.module_full as mod

    assert isinstance(mod.monkay, Monkay)

    assert mod.foo() == "foo"
    assert mod.bar() == "bar"
    with pytest.warns(DeprecationWarning) as record:
        assert mod.deprecated() == "deprecated"
    assert (
        record[0].message.args[0]
        == 'Attribute: "deprecated" is deprecated.\nReason: old.\nUse "super_new" instead.'
    )


def test_extensions(capsys):
    import tests.targets.module_full as mod
    from tests.targets.extension import NonExtension

    captured = capsys.readouterr()
    assert captured.out == captured.err == ""

    app = mod.FakeApp()
    mod.monkay.set_instance(app)
    captured_out = capsys.readouterr().out
    assert captured_out == "settings_extension1 called\nsettings_extension2 called\n"
    with pytest.raises(ValueError):
        mod.monkay.add_extension(NonExtension(name="foo"))
    assert capsys.readouterr().out == ""

    # order

    class ExtensionA:
        name: str = "A"

        def apply(self, monkay: Monkay) -> None:
            monkay.ensure_extension("B")
            with pytest.raises(RuntimeError):
                monkay.ensure_extension("D")
            print("A")

    class ExtensionB:
        name: str = "B"

        def apply(self, monkay: Monkay) -> None:
            monkay.ensure_extension("A")
            monkay.ensure_extension(ExtensionC())
            print("B")

    class ExtensionC:
        name: str = "C"

        def apply(self, monkay: Monkay) -> None:
            monkay.ensure_extension(ExtensionA())
            print("C")

    with mod.monkay.with_extensions({"B": ExtensionB(), "A": ExtensionA()}):
        mod.monkay.apply_extensions()

    assert capsys.readouterr().out == "A\nC\nB\n"
    with mod.monkay.with_extensions(
        {
            "C": ExtensionC(),
            "B": ExtensionB(),
        }
    ):
        mod.monkay.apply_extensions()

    assert capsys.readouterr().out == "B\nA\nC\n"


def test_app(capsys):
    import tests.targets.module_full as mod

    app = mod.FakeApp()
    mod.monkay.set_instance(app)
    assert mod.monkay.instance is app
    captured_out = capsys.readouterr().out
    assert captured_out == "settings_extension1 called\nsettings_extension2 called\n"
    app2 = mod.FakeApp()
    with mod.monkay.with_instance(app2):
        assert mod.monkay.instance is app2
        assert capsys.readouterr().out == ""
    assert capsys.readouterr().out == ""
