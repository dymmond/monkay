from foo import monkay as foo_monkay


def get_application():
    # sys.path updates
    important_preloads = [...]
    foo_monkay.evaluate_preloads(important_preloads, ignore_import_errors=False)
    extra_preloads = [...]
    foo_monkay.evaluate_preloads(extra_preloads)
    foo_monkay.evaluate_settings()
    return ...


app = get_application()
