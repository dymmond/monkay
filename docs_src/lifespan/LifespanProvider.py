from monkay import LifespanProvider

asgi_app = ...

asgi_app = LifespanProvider(asgi_app)
