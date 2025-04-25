from monkay import Monkay

monkay = Monkay(
    globals(),
    # Required for initializing settings feature
    settings_path="",
)


def find_settings():
    for path in ["a.settings", "b.settings.develop"]:
        monkay.settings = path
        if monkay.evaluate_settings(ignore_import_errors=True):
            break
