"""ASGI helpers."""

# Developer warning:
# please do no expose this module in monkay.__init__.
# this module depends on threading.locals and pulls them in.

import threading
from asyncio import AbstractEventLoop, Event, Queue, Task, create_task, get_running_loop, wait_for
from collections.abc import AsyncGenerator, Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from functools import partial, wraps
from typing import Any, TypedDict, TypeVar, cast, overload

from .types import ASGIApp

BoundASGIApp = TypeVar("BoundASGIApp", bound=ASGIApp)


class ManagementState(TypedDict):
    started: bool
    loop: AbstractEventLoop | None
    task: Task | None


@asynccontextmanager
async def lifespan(
    app: BoundASGIApp, *, timeout: None | float | int = None
) -> AsyncGenerator[BoundASGIApp, None]:
    """Transform the ASGI lifespan extension into an AsyncContextManager."""
    # inverted send, receive because we are emulating the server
    send_queue: Queue[MutableMapping[str, Any]] = Queue()
    receive_queue: Queue[MutableMapping[str, Any]] = Queue()
    state: MutableMapping[str, Any] = {}
    send_queue.put_nowait({"type": "lifespan.startup"})
    task: Task = create_task(
        app(  # type: ignore
            {
                "type": "lifespan",
                "asgi": {"version": "3.0", "spec_version": "2.0"},
                "state": state,
            },
            # inverted send, receive because we are emulating the server
            send_queue.get,
            receive_queue.put,
        )
    )
    if timeout:
        response = await wait_for(receive_queue.get(), timeout)
    else:
        response = await receive_queue.get()
    match cast(Any, response.get("type")):
        case "lifespan.startup.complete":
            ...
        case "lifespan.startup.failed":
            raise RuntimeError("Lifespan startup failed:", response.get("msg") or "")

    cleaned_up = False

    async def cleanup() -> None:
        nonlocal cleaned_up
        if cleaned_up:
            return
        cleaned_up = True
        send_queue.put_nowait({"type": "lifespan.shutdown"})
        if task.done():
            raise RuntimeError("Lifespan task errored", task.result())

        if timeout:
            response = await wait_for(receive_queue.get(), timeout)
        else:
            response = await receive_queue.get()
        match response.get("type"):
            case "lifespan.shutdown.complete":
                ...
            case "lifespan.shutdown.failed":
                raise RuntimeError("Lifespan shutdown failed:", response.get("msg") or "")

    try:
        yield app
    finally:
        await cleanup()


# why not contextvar? this is really thread local while contextvars can be copied.
lifespan_local = threading.local()


def get_management_state() -> ManagementState:
    if not hasattr(lifespan_local, "management_state"):
        lifespan_local.management_state = ManagementState(started=False, task=None, loop=None)
    return lifespan_local.management_state


async def _lifespan_task_helper(app: ASGIApp, startup_complete: Event) -> None:
    terminateevent = Event()
    state = get_management_state()
    try:
        async with lifespan(app):
            startup_complete.set()
            # wait until cancellation
            await terminateevent.wait()
    finally:
        state["started"] = False


@overload
def LifespanProvider(app: BoundASGIApp, *, sniff: bool = True) -> BoundASGIApp: ...


@overload
def LifespanProvider(
    app: None, *, sniff: bool = True
) -> Callable[[BoundASGIApp], BoundASGIApp]: ...


def LifespanProvider(
    app: BoundASGIApp | None = None, *, sniff: bool = True
) -> BoundASGIApp | Callable[[BoundASGIApp], BoundASGIApp]:
    """Make lifespan usage possible in servers which doesn't support the extension e.g. daphne."""
    if app is None:
        return partial(LifespanProvider, sniff=sniff)

    @wraps(app)
    async def app_wrapper(
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        state = get_management_state()
        started = state["started"]
        rloop = get_running_loop()
        loop = state["loop"]
        if loop and loop is not rloop:
            # trigger start
            started = state["started"] = False
            # cancel old loop task
            if task_ref := state.get("task"):
                task_ref.cancel()
        if sniff and scope.get("type") == "lifespan":
            # is already started in the same thread
            if started:
                raise RuntimeError("We should not execute lifespan twice in the same thread.")
            # prevent start
            started = state["started"] = True
        loop = state["loop"] = rloop
        if not started:
            # init
            started = state["started"] = True
            startup_complete = Event()
            state["task"] = create_task(_lifespan_task_helper(app, startup_complete))
            await startup_complete.wait()

        await app(scope, receive, send)

    # forward attributes
    app_wrapper.__getattr__ = lambda name: getattr(app, name)  # type: ignore

    return cast(BoundASGIApp, app_wrapper)


class MuteInteruptException(BaseException): ...


@overload
def LifespanHook(
    app: BoundASGIApp,
    *,
    setup: Callable[[], Awaitable[AsyncExitStack]] | None = None,
    do_forward: bool = True,
) -> BoundASGIApp: ...


@overload
def LifespanHook(
    app: None,
    *,
    setup: Callable[[], Awaitable[AsyncExitStack]] | None = None,
    do_forward: bool = True,
) -> Callable[[BoundASGIApp], BoundASGIApp]: ...


def LifespanHook(
    app: BoundASGIApp | None = None,
    *,
    setup: Callable[[], Awaitable[AsyncExitStack]] | None = None,
    do_forward: bool = True,
) -> BoundASGIApp | Callable[[BoundASGIApp], BoundASGIApp]:
    """Helper for creating a lifespan integration which forwards."""
    if app is None:
        return partial(LifespanHook, setup=setup, do_forward=do_forward)

    shutdown_stack: AsyncExitStack | None = None

    @wraps(app)
    async def app_wrapper(
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        nonlocal shutdown_stack
        # Check if the current scope is of type 'lifespan'.
        if scope["type"] == "lifespan":
            # Store the original receive callable to be used inside the wrapper.
            original_receive = receive

            async def receive() -> MutableMapping[str, Any]:
                """
                A wrapped `receive` callable that intercepts 'lifespan.startup'
                and 'lifespan.shutdown' messages to execute the setup.
                """
                nonlocal shutdown_stack
                # Await the message from the original receive callable.
                message = await original_receive()
                # Check if the message type is for lifespan startup.
                match message.get("type"):
                    case "lifespan.startup":
                        if setup is not None:
                            try:
                                # Setup an AsyncExitStack for cleanup.
                                shutdown_stack = await setup()
                            except Exception as exc:
                                # If an exception occurs during startup, send a failed
                                # message to the ASGI server.
                                await send({"type": "lifespan.startup.failed", "msg": str(exc)})
                                # Raise a custom exception to stop further lifespan
                                # processing for this event.
                                raise MuteInteruptException from None
                    case "lifespan.shutdown":  # noqa: SIM102
                        # Check if the message type is for lifespan shutdown.
                        if shutdown_stack is not None:
                            try:
                                # Attempt to exit asynchronous context.
                                await shutdown_stack.aclose()
                            except Exception as exc:
                                # If an exception occurs during shutdown, send a failed
                                # message to the ASGI server.
                                await send({"type": "lifespan.shutdown.failed", "msg": str(exc)})
                                # Raise a custom exception to stop further lifespan
                                # processing for this event.
                                raise MuteInteruptException from None
                # Return the original message after processing.
                return message

            # If `handle_lifespan` is True, this helper will fully manage
            # the lifespan protocol, including sending 'complete' messages.
            if not do_forward:
                # Suppress the MuteInteruptException to gracefully stop
                # the lifespan loop without uncaught exceptions.
                with suppress(MuteInteruptException):
                    # Continuously receive and process lifespan messages.
                    while True:
                        # Await the next lifespan message.
                        message = await receive()
                        # If it's a startup message, send a complete message.
                        if message["type"] == "lifespan.startup":
                            await send({"type": "lifespan.startup.complete"})
                        # If it's a shutdown message, send a complete message
                        # and break the loop.
                        elif message["type"] == "lifespan.shutdown":
                            await send({"type": "lifespan.shutdown.complete"})
                            break
                # Once lifespan handling is complete, return from the callable.
                return

        # For any scope type other than 'lifespan', or if handle_lifespan
        # is False (meaning the original app will handle 'complete' messages),
        # or after the lifespan handling is complete, call the original ASGI app.
        # Suppress MuteInteruptException in case it was raised by the
        # modified receive callable and propagated here.
        with suppress(MuteInteruptException):
            await app(scope, receive, send)

    # forward attributes
    app_wrapper.__getattr__ = lambda name: getattr(app, name)  # type: ignore

    return cast(BoundASGIApp, app_wrapper)


__all__ = [
    "lifespan",
    "LifespanHook",
    "LifespanProvider",
    "ASGIApp",
]
