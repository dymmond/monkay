import asyncio
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack
from typing import Any

import pytest

from monkay.asgi import Lifespan, LifespanHook

pytestmark = pytest.mark.anyio


async def stub(
    scope: MutableMapping[str, Any],
    receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
    send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
) -> None:
    await send(await receive())


stub.test_attribute = True


async def stub_raise(
    scope: MutableMapping[str, Any],
    receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
    send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
) -> None:
    raise Exception()


async def stub_empty(
    scope: MutableMapping[str, Any],
    receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
    send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
) -> None: ...


@pytest.mark.parametrize("probe", [stub, stub_empty, stub_raise])
async def test_lifespan(probe):
    setup_complete = False
    shutdown_complete = False

    async def helper_cleanup():
        nonlocal shutdown_complete
        shutdown_complete = True

    async def helper_setup():
        nonlocal setup_complete
        setup_complete = True
        cm = AsyncExitStack()
        cm.push_async_callback(helper_cleanup)
        return cm

    assert not setup_complete
    assert not shutdown_complete
    async with Lifespan(LifespanHook(probe, setup=helper_setup, do_forward=False)):
        assert setup_complete
        assert not shutdown_complete

    assert setup_complete
    assert shutdown_complete


@pytest.mark.parametrize("probe", [stub, stub_empty, stub_raise])
async def test_lifespan_server(probe):
    setup_complete = False
    shutdown_complete = False

    async def helper_cleanup():
        nonlocal shutdown_complete
        shutdown_complete = True

    async def helper_setup():
        nonlocal setup_complete
        setup_complete = True
        cm = AsyncExitStack()
        cm.push_async_callback(helper_cleanup)
        return cm

    assert not setup_complete
    assert not shutdown_complete
    app = LifespanHook(probe, setup=helper_setup, do_forward=False)
    wrapped = Lifespan(app)
    await wrapped.__aenter__()
    try:
        assert setup_complete
        assert not shutdown_complete
    finally:
        await wrapped.__aexit__()

    assert setup_complete
    assert shutdown_complete


async def test_LifespanHook_forward():
    provider = LifespanHook(stub)
    assert provider.test_attribute


@pytest.mark.parametrize("phase", ["startup", "shutdown"])
async def test_lifespan_timeout(phase):
    async def helper_cleanup():
        if phase == "shutdown":
            await asyncio.sleep(100)

    async def helper_setup():
        if phase == "startup":
            await asyncio.sleep(100)
        cm = AsyncExitStack()
        cm.push_async_callback(helper_cleanup)
        return cm

    with pytest.raises(asyncio.TimeoutError):
        async with Lifespan(LifespanHook(stub, setup=helper_setup, do_forward=False), timeout=0.4):
            pass


async def test_lifespan_startup_failure_cleans_task():
    async def helper_setup():
        raise RuntimeError("boom")

    wrapped = Lifespan(LifespanHook(stub, setup=helper_setup, do_forward=False))

    with pytest.raises(RuntimeError, match="Lifespan startup failed"):
        await wrapped.start_raw()

    # Startup errors must not leave task state behind, otherwise later starts are skipped.
    assert wrapped.task is None

    with pytest.raises(RuntimeError, match="Lifespan startup failed"):
        await wrapped.start_raw()

    assert wrapped.task is None


async def test_lifespan_startup_timeout_cleans_task():
    async def helper_setup():
        await asyncio.sleep(100)
        return AsyncExitStack()

    wrapped = Lifespan(LifespanHook(stub, setup=helper_setup, do_forward=False), timeout=0.05)

    with pytest.raises(asyncio.TimeoutError):
        await wrapped.__aenter__()

    assert wrapped.task is None


async def test_lifespan_startup_unexpected_message_cleans_task():
    async def app(
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        await receive()
        await send({"type": "lifespan.startup.unexpected"})
        await asyncio.sleep(100)

    wrapped = Lifespan(app)

    with pytest.raises(RuntimeError, match="Unexpected startup response"):
        await wrapped.start_raw()

    assert wrapped.task is None


async def test_lifespan_shutdown_waits_for_app_completion():
    complete = asyncio.Event()

    async def app(
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        message = await receive()
        assert message["type"] == "lifespan.startup"
        await send({"type": "lifespan.startup.complete"})
        message = await receive()
        assert message["type"] == "lifespan.shutdown"
        await send({"type": "lifespan.shutdown.complete"})
        complete.set()

    wrapped = Lifespan(app)
    async with wrapped:
        pass

    assert complete.is_set()
    assert wrapped.task is None


async def test_lifespan_shutdown_propagates_task_errors():
    async def app(
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        message = await receive()
        assert message["type"] == "lifespan.startup"
        await send({"type": "lifespan.startup.complete"})
        message = await receive()
        assert message["type"] == "lifespan.shutdown"
        await send({"type": "lifespan.shutdown.complete"})
        raise RuntimeError("shutdown crash")

    wrapped = Lifespan(app)
    await wrapped.__aenter__()

    with pytest.raises(RuntimeError, match="Lifespan task errored during shutdown"):
        await wrapped.__aexit__()
