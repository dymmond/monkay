from monkay import Monkay

extras = {"foo": lambda: "foo"}


__all__ = ["foo"]  # noqa


def __getattr__(name: str):
    try:
        return extras[name]
    except KeyError as exc:
        raise AttributeError from exc


## __dir__ is missing

monkay = Monkay(
    globals(),
)
