import contextlib
import sys
from io import StringIO
from pathlib import Path

import pytest
from pydantic_settings import BaseSettings

from monkay import Monkay, load, load_any


@pytest.fixture(autouse=True, scope="function")
def cleanup():
    for p in (Path(__file__).parent / "targets").iterdir():
        sys.modules.pop(f"tests.targets.{p.stem}", None)
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

    # in extras
    assert mod.foo() == "foo"
    assert mod.bar() == "bar"
    assert mod.bar2() == "bar2"
    with pytest.raises(KeyError):
        mod.monkay.add_lazy_import("bar", "tests.targets.fn_module:bar")
    with pytest.raises(KeyError):
        mod.monkay.add_deprecated_lazy_import(
            "bar",
            {
                "path": "tests.targets.fn_module:deprecated",
                "reason": "old.",
                "new_attribute": "super_new",
            },
        )

    assert isinstance(mod.settings, BaseSettings)
    with pytest.warns(DeprecationWarning) as record:
        assert mod.deprecated() == "deprecated"
    assert (
        record[0].message.args[0]
        == 'Attribute: "deprecated" is deprecated.\nReason: old.\nUse "super_new" instead.'
    )


def test_load():
    assert load("tests.targets.fn_module.bar") is not None
    assert load("tests.targets.fn_module:bar") is not None
    with pytest.raises(ValueError):
        assert load("tests.targets.fn_module.bar", allow_splits=":") is not None
    with pytest.raises(AttributeError):
        assert load("tests.targets.fn_module:bar", allow_splits=".") is not None


def test_load_any():
    assert load_any("tests.targets.fn_module", ["not_existing", "bar"]) is not None
    with pytest.warns(DeprecationWarning) as records:
        assert (
            load_any(
                "tests.targets.fn_module",
                ["not_existing", "bar"],
                non_first_deprecated=True,
            )
            is not None
        )
    assert (
        load_any(
            "tests.targets.fn_module",
            ["bar", "not_existing"],
            non_first_deprecated=True,
        )
        is not None
    )
    assert str(records[0].message) == '"bar" is deprecated, use "not_existing" instead.'
    with pytest.raises(ImportError):
        assert load_any("tests.targets.fn_module", ["not-existing"]) is None
    with pytest.raises(ImportError):
        assert load_any("tests.targets.fn_module", []) is None
    with pytest.raises(ImportError):
        load_any("tests.targets.not_existing", ["bar"])


def test_extensions(capsys):
    import tests.targets.module_full as mod
    from tests.targets.extension import Extension, NonExtension

    captured = capsys.readouterr()
    assert captured.out == captured.err == ""

    app = mod.FakeApp()
    mod.monkay.set_instance(app)
    captured_out = capsys.readouterr().out
    assert captured_out == "settings_extension1 called\nsettings_extension2 called\n"
    with pytest.raises(ValueError):
        mod.monkay.add_extension(NonExtension(name="foo"))  # type: ignore
    with pytest.raises(KeyError):
        mod.monkay.add_extension(Extension(name="settings_extension1"))
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


def test_caches():
    import tests.targets.module_full as mod

    assert not mod.monkay._cached_imports

    assert mod.bar() == "bar"
    assert "bar" in mod.monkay._cached_imports
    assert isinstance(mod.settings, BaseSettings)
    assert "settings" not in mod.monkay._cached_imports
    # settings cache
    assert "_loaded_settings" in mod.monkay.__dict__
    mod.monkay.clear_caches()

    assert not mod.monkay._cached_imports
    assert "_loaded_settings" not in mod.monkay.__dict__


def test_sorted_exports():
    import tests.targets.module_full as mod

    eval(mod.stringify_all_plain(separate_by_category=True))
    eval(mod.stringify_all_plain(separate_by_category=False))
    assert (
        mod.stringify_all(separate_by_category=True)
        == '__all__ = [\n"deprecated"\n,"bar2"\n,"bar"\n,"dynamic"\n,"settings"\n,"foo"\n,"stringify_all"\n]'
    )
    assert (
        mod.stringify_all(separate_by_category=False)
        == '__all__ = [\n"bar2"\n,"bar"\n,"deprecated"\n,"dynamic"\n,"foo"\n,"settings"\n,"stringify_all"\n]'
    )


def test_dir_full():
    import tests.targets.module_full as mod

    assert "bar2" in dir(mod)


def test_dir_add_none_getattr_fixup():
    import tests.targets.module_none_getattr as mod

    assert "__dir__" in mod.__dict__
    assert list(filter(lambda x: not x.startswith("__"), dir(mod))) == [
        "Monkay",
        "extras",
        "foo",
        "monkay",
    ]
    mod.monkay.add_lazy_import("bar2", ".fn_module:bar2")
    assert mod.foo() == "foo"
    assert mod.bar2() == "bar2"
    assert list(filter(lambda x: not x.startswith("__"), dir(mod))) == [
        "Monkay",
        "bar2",
        "extras",
        "foo",
        "monkay",
    ]


def test_dir_add_none():
    import tests.targets.module_none as mod

    assert "__dir__" not in mod.__dict__
    assert "__getattr__" not in mod.__dict__
    assert list(filter(lambda x: not x.startswith("__"), dir(mod))) == [
        "Monkay",
        "monkay",
    ]
    mod.monkay.add_lazy_import("bar2", ".fn_module:bar2")
    assert mod.bar2() == "bar2"
    assert "__dir__" in mod.__dict__
    assert "__getattr__" in mod.__dict__
    assert list(filter(lambda x: not x.startswith("__"), dir(mod))) == [
        "Monkay",
        "bar2",
        "monkay",
    ]


def test_dir_add_none_extra():
    import tests.targets.module_none as mod

    assert "__dir__" not in mod.__dict__
    assert "__getattr__" not in mod.__dict__
    attrs = set(dir(mod))
    attrs.add("bar2")
    attrs.add("__dir__")
    attrs.add("__getattr__")
    mod.monkay.add_lazy_import("bar2", ".fn_module:bar2")
    assert set(dir(mod)) == attrs
