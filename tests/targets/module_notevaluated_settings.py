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
    settings_path="tests.targets.not_existing_settings_path:Settings",
)
monkay.evaluate_settings()
