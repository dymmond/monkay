from monkay import Monkay

extras = {"foo": lambda: "foo"}


def __getattr__(name: str):
    try:
        return extras[name]
    except KeyError as exc:
        raise AttributeError from exc


class FakeApp:
    is_fake_app: bool = True


monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path="tests.targets.settings:Settings",
    preloads=["tests.targets.module_full_preloaded1:load"],
    settings_preload_name="preloads",
    settings_extensions_name="extensions",
    uncached_imports=["settings"],
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
        "dynamic": lambda: "dynamic",
        "settings": lambda: monkay.settings,
    },
    deprecated_lazy_imports={
        "deprecated": {
            "path": "tests.targets.fn_module:deprecated",
            "reason": "old",
            "new_attribute": "super_new",
        }
    },
)
