import os

from monkay import Monkay

monkay = Monkay(
    # Required for auto-hooking
    globals(),
    with_extensions=True,
    with_instance=True,
    settings_path=lambda: os.environ.get("SETTINGS_MODULE_IMPORT", "settings_path:Settings") or "",
    preloads=["tests.targets.module_full_preloaded1:load"],
    # Warning: settings names have a catch
    settings_preloads_name="preloads",
    settings_extensions_name="extensions",
    uncached_imports=["settings"],
    lazy_imports={
        "bar": "tests.targets.fn_module:bar",
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
