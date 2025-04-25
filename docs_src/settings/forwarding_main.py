import os

import child

from monkay import Monkay

monkay = Monkay(
    globals(),
    settings_path=lambda: os.environ.get("MONKAY_MAIN_SETTINGS", "foo.test:example") or "",
)
# because monkay.settings is an instance it uses not a cache for the settings
child.monkay.settings = lambda: monkay.settings
