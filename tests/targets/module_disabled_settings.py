from monkay import Monkay

extras = {"foo": lambda: "foo"}


def __getattr__(name: str):
    try:
        return extras[name]
    except KeyError as exc:
        raise AttributeError from exc


class FakeApp:
    is_fake_app: bool = True


__all__ = ["foo"]  # noqa
monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=False,
    lazy_imports={
        "bar": ".fn_module:bar",
        "bar2": "..targets.fn_module:bar2",
        "dynamic": lambda: "dynamic",
        "settings": lambda: monkay.settings,
    },
    deprecated_lazy_imports={
        "deprecated": {
            "path": "tests.targets.fn_module:deprecated",
            "reason": "old.",
            "new_attribute": "super_new",
        }
    },
)
