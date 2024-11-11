from dataclasses import dataclass

from monkay import Monkay


@dataclass
class Extension:
    name: str = "default"

    def apply(self, app: Monkay) -> None:
        assert isinstance(app, Monkay)
        assert app.instance.is_fake_app
        print(f"{self.name} called")


@dataclass
class BrokenExtension1:
    name: str = "broken1"

    def apply(self, app: Monkay) -> None:
        app.ensure_extension("non-existent")


@dataclass
class BrokenExtension2:
    name: str = "broken2"

    def apply(self, app: Monkay) -> None:
        # not allowed here
        app.apply_extensions()


@dataclass
class NonExtension:
    name: str
