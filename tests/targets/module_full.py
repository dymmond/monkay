from monkay import Monkay

extras = {"foo": lambda: "foo"}


def __getattr__(name: str):
    try:
        return extras[name]
    except KeyError as exc:
        raise AttributeError from exc


class FakeApp:
    is_fake_app: bool = True


__all__ = ["foo", "stringify_all"]  # noqa
monkay = Monkay(
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path="tests.targets.settings:Settings",
    preloads=["tests.targets.module_full_preloaded1:load"],
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
    uncached_imports=["settings"],
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


def stringify_all_plain(separate_by_category: bool):
    return "[\n{}\n]".format(
        "\n,".join(
            f'"{t[1]}"' for t in monkay.sorted_exports(separate_by_category=separate_by_category)
        )
    )


def stringify_all(separate_by_category: bool):
    return f"__all__ = {stringify_all_plain(separate_by_category)}"
