from monkay import lifespan

asgi_app = ...


async def cli_code():
    async with lifespan(asgi_app) as app:  # noqa: F841
        # do something
        # e.g. app.list_routes()
        ...
