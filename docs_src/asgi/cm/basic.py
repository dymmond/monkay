from contextlib import contextmanager
from monkay.asgi import CMToASGIMiddleware

import edgy


def wrap_app(app):
    registry = edgy.Registry(...)
    instance = edgy.Instance(registry=registry)

    @contextmanager
    def returns_cm(scope):
        with edgy.monkay.with_instance(instance):
            yield

    app = registry.asgi(CMToASGIMiddleware(app, cm=returns_cm))
    instance = edgy.Instance(registry=registry, app=app)
