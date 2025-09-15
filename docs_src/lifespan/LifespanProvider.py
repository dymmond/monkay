from monkay.asgi import LifespanProvider

asgi_app = ...

asgi_app = LifespanProvider(asgi_app)
