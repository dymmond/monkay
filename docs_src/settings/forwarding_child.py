import os

from monkay import Monkay

monkay = Monkay(
    globals(),
    settings_path=lambda: os.environ.get("MONKAY_CHILD_SETTINGS", "foo.test:example") or "",
)
