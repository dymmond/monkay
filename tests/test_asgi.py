from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack
from typing import Any

import pytest

from monkay.asgi import LifespanHook, LifespanProvider, lifespan

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
    async with lifespan(LifespanHook(probe, setup=helper_setup, do_forward=False)):
        assert setup_complete
        assert not shutdown_complete

    assert setup_complete
    assert shutdown_complete


@pytest.mark.parametrize("probe", [stub, stub_empty, stub_raise])
async def test_lifespan_sniff(probe):
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
    async with lifespan(
        # sniff detects the lifespan of the server and doesn't start another lifespan task
        LifespanProvider(LifespanHook(probe, setup=helper_setup, do_forward=False))
    ):
        assert setup_complete
        assert not shutdown_complete
    assert setup_complete
    assert shutdown_complete


async def test_lifespan_sniff_started():
    provider = LifespanProvider(LifespanHook(stub, do_forward=False))
    async with lifespan(provider):

        async def stub_receive():
            return {}

        async def stub_send(msg: Any):
            pass

        # try a spec violation
        with pytest.raises(RuntimeError):
            await provider({"type": "lifespan"}, stub_receive, stub_send)


async def test_LifespanProvider_forward():
    provider = LifespanProvider(stub)
    assert provider.test_attribute


async def test_LifespanHook_forward():
    provider = LifespanHook(stub)
    assert provider.test_attribute
