from monkay.asgi import ASGIApp, Lifespan


class Server:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.lifespan = Lifespan(app)

    async def startup(self) -> None:
        ...
        await self.lifespan.__aenter__()

    async def shutdown(self) -> None:
        ...
        await self.lifespan.__aexit__()
