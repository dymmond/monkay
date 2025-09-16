from monkay.asgi import LifespanHook

django_app = ...

# for django
app = LifespanHook(django_app, do_forward=False)
