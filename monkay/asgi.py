import sys
import threading
from asyncio import Event, Queue, create_task
from collections.abc import AsyncGenerator, Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from functools import partial, wraps
from typing import Any, TypeVar, cast, overload

from .types import ASGIApp

if sys.version_info >= (3, 11):
    from typing import assert_never
else:
    from typing_extensions import assert_never

BoundASGIApp = TypeVar("BoundASGIApp", bound=ASGIApp)


@asynccontextmanager
async def lifespan(app: BoundASGIApp) -> AsyncGenerator[BoundASGIApp, None]:
    """Transform the ASGI lifespan extension into an AsyncContextManager."""
    # inverted send, receive because we are emulating the server
    send_queue: Queue[MutableMapping[str, Any]] = Queue()
    receive_queue: Queue[MutableMapping[str, Any]] = Queue()
    state: MutableMapping[str, Any] = {}
    await send_queue.put({"type": "lifespan.startup"})
    await app(
        {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.0"}, "state": state},
        # inverted send, receive because we are emulating the server
        send_queue.get,
        receive_queue.put,
    )
    response = await receive_queue.get()
    match cast(Any, response.get("type")):
        case "lifespan.startup.complete":
            ...
        case "lifespan.startup.failed":
            raise RuntimeError("Lifespan startup failed:", response.get("msg") or "")
        case _ as invalid:
            assert_never(invalid)

    cleaned_up = False

    async def cleanup() -> None:
        nonlocal cleaned_up
        if cleaned_up:
            return
        cleaned_up = True
        await send_queue.put({"type": "lifespan.shutdown"})
        response = await receive_queue.get()
        match cast(Any, response.get("type")):
            case "lifespan.shutdown.complete":
                ...
            case "lifespan.shutdown.failed":
                raise RuntimeError("Lifespan shutdown failed:", response.get("msg") or "")
            case _ as invalid:
                assert_never(invalid)

    try:
        yield app
    finally:
        await cleanup()


async def _lifespan_task_helper(app: ASGIApp, startup_complete: Event) -> None:
    bogoevent = Event()
    async with lifespan(app):
        startup_complete.set()
        # wait until cancellation
        await bogoevent.wait()


# why not contextvar? this is really thread local while contextvars can be copied.
lifespan_local = threading.local()


@overload
def LifespanProvider(app: ASGIApp, *, sniff: bool = True) -> ASGIApp: ...


@overload
def LifespanProvider(app: None, *, sniff: bool = True) -> Callable[[ASGIApp], ASGIApp]: ...


def LifespanProvider(
    app: ASGIApp | None = None, *, sniff: bool = True
) -> ASGIApp | Callable[[ASGIApp], ASGIApp]:
    """Make lifespan usage possible in servers which doesn't support the extension e.g. daphne."""
    if app is None:
        return partial(LifespanProvider, sniff=sniff)

    @wraps(app)
    async def app_wrapper(
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        started = getattr(lifespan_local, "started", False)
        if sniff and scope.get("type") == "lifespan":
            # is already started in the same thread
            if started:
                raise RuntimeError("We should not execute lifespan twice in the same thread.")
            lifespan_local.started = True
        if not started:
            lifespan_local.started = True
            startup_complete = Event()
            lifespan_local._task_ref = create_task(_lifespan_task_helper(app, startup_complete))
            await startup_complete.wait()

        await app(scope, receive, send)

    return app_wrapper


class MuteInteruptException(BaseException): ...


@overload
def LifespanHook(
    app: ASGIApp,
    *,
    setup: Callable[[], Awaitable[AsyncExitStack]] | None = None,
    do_forward: bool = True,
) -> ASGIApp: ...


@overload
def LifespanHook(
    app: None,
    *,
    setup: Callable[[], Awaitable[AsyncExitStack]] | None = None,
    do_forward: bool = True,
) -> Callable[[ASGIApp], ASGIApp]: ...


def LifespanHook(
    app: ASGIApp | None = None,
    *,
    setup: Callable[[], Awaitable[AsyncExitStack]] | None = None,
    do_forward: bool = True,
) -> ASGIApp | Callable[[ASGIApp], ASGIApp]:
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
                # Await the message from the original receive callable.
                message = await original_receive()
                # Check if the message type is for lifespan startup.
                if message["type"] == "lifespan.startup":
                    if setup is not None:
                        try:
                            # Attempt to enter the registry's asynchronous context,
                            # typically establishing database connections.
                            shutdown_stack = await setup()
                        except Exception as exc:
                            # If an exception occurs during startup, send a failed
                            # message to the ASGI server.
                            await send({"type": "lifespan.startup.failed", "msg": str(exc)})
                            # Raise a custom exception to stop further lifespan
                            # processing for this event.
                            raise MuteInteruptException from None
                # Check if the message type is for lifespan shutdown.
                elif message["type"] == "lifespan.shutdown":  # noqa: SIM102
                    if shutdown_stack is not None:  # type: ignore
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

    return app_wrapper
