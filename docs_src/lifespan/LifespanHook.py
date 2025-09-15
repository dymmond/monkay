from contextlib import AsyncExitStack

from monkay.asgi import LifespanHook

esmerald_app = ...
django_app = ...


async def setup() -> AsyncExitStack:
    stack = AsyncExitStack()

    # do something
    async def cleanup_async(): ...

    stack.push_async_callback(cleanup_async)

    # do something else
    def cleanup_sync(): ...

    stack.callback(cleanup_sync)

    return stack


# for frameworks supporting lifespan
app = LifespanHook(esmerald_app, setup=setup)
# for django or for testing
# asgi_app = LifespanHook(esmerald_app, setup=setup, do_forward=False)
