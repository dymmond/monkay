import asyncio
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any

import pytest

from monkay.asgi import CMToASGIMiddleware, Lifespan, LifespanHook

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


cv = ContextVar("cv")


async def stub_check_context_var(
    scope: MutableMapping[str, Any],
    receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
    send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
) -> None:
    cv.set(cv.get() + 1)
    d = await receive()
    await send({"cv": cv.get(), **d})


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


async def test_lifespan_hook_setup_stack_is_isolated_per_concurrent_scope():
    started = asyncio.Event()
    release = asyncio.Event()
    startup_count = 0
    cleanup_calls: list[int] = []

    async def helper_cleanup(token: int) -> None:
        cleanup_calls.append(token)

    async def helper_setup() -> AsyncExitStack:
        nonlocal startup_count
        startup_count += 1
        token = startup_count
        stack = AsyncExitStack()
        stack.push_async_callback(helper_cleanup, token)
        return stack

    wrapped = LifespanHook(stub, setup=helper_setup, do_forward=False)

    async def worker() -> None:
        async with Lifespan(wrapped):
            if startup_count == 2:
                started.set()
            await started.wait()
            await release.wait()

    task_a = asyncio.create_task(worker())
    task_b = asyncio.create_task(worker())
    await started.wait()
    release.set()
    await asyncio.gather(task_a, task_b)

    assert sorted(cleanup_calls) == [1, 2]


async def execute_app(app: Any, scope: Any = None, message: Any = None):
    send_queue: asyncio.Queue[MutableMapping[str, Any]] = asyncio.Queue()
    receive_queue: asyncio.Queue[MutableMapping[str, Any]] = asyncio.Queue()
    await receive_queue.put(message or {})
    await app(scope or {}, receive_queue.get, send_queue.put)
    return send_queue.get_nowait()


async def test_cm_to_middleware_direct_sync():
    retrieved = None

    @contextmanager
    def cm():
        nonlocal retrieved
        token = cv.set(0)
        try:
            yield
        finally:
            retrieved = cv.get()
            cv.reset(token)

    app = CMToASGIMiddleware(stub_check_context_var, cm=cm())
    assert await execute_app(app) == {"cv": 1}

    assert retrieved == 1


async def test_cm_to_middleware_direct_async():
    retrieved = None

    @asynccontextmanager
    async def cm():
        nonlocal retrieved
        token = cv.set(0)
        try:
            yield
        finally:
            retrieved = cv.get()
            cv.reset(token)

    app = CMToASGIMiddleware(stub_check_context_var, cm=cm())
    assert await execute_app(app) == {"cv": 1}

    assert retrieved == 1


async def test_cm_to_middleware_fn_sync():
    retrieved = None

    def func(scope):
        assert scope == {"foo": 1}

        @contextmanager
        def cm():
            nonlocal retrieved
            token = cv.set(0)
            try:
                yield
            finally:
                retrieved = cv.get()
                cv.reset(token)

        return cm()

    app = CMToASGIMiddleware(stub_check_context_var, cm=func)
    assert await execute_app(app, {"foo": 1}, {"foo2": 2}) == {"cv": 1, "foo2": 2}
    assert retrieved == 1


async def test_cm_to_middleware_fn_async():
    retrieved = None

    async def cm_caller(scope):
        assert scope == {"foo": 1}

        @asynccontextmanager
        async def cm():
            nonlocal retrieved
            token = cv.set(0)
            try:
                yield
            finally:
                retrieved = cv.get()
                cv.reset(token)

        return cm()

    app = CMToASGIMiddleware(stub_check_context_var, cm=cm_caller)
    assert await execute_app(app, {"foo": 1}, {"foo2": 2}) == {"cv": 1, "foo2": 2}
    assert retrieved == 1
