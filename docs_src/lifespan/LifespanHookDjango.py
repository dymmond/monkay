from monkay.asgi import ASGIApp, LifespanHook

django_app: ASGIApp = ...  # type: ignore

# for django
app = LifespanHook(django_app, do_forward=False)
