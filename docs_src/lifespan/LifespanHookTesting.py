from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack
from typing import Any

from monkay.asgi import Lifespan, LifespanHook


async def stub_raise(
    scope: MutableMapping[str, Any],
    receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
    send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
) -> None:
    raise Exception("Should not be reached")


async def setup() -> AsyncExitStack:
    stack = AsyncExitStack()

    # do something
    async def cleanup_async(): ...

    stack.push_async_callback(cleanup_async)

    # do something else
    def cleanup_sync(): ...

    stack.callback(cleanup_sync)

    return stack


async def test_asgi_hook():
    hook_to_test = LifespanHook(LifespanHook(stub_raise, do_forward=False), setup=setup)
    async with Lifespan(hook_to_test, timeout=30):
        pass
