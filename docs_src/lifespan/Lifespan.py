from monkay.asgi import Lifespan

asgi_app = ...


async def cli_code():
    async with Lifespan(asgi_app) as app:  # noqa: F841
        # do something
        # e.g. app.list_routes()
        ...
