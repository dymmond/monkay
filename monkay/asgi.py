"""ASGI helpers."""

from asyncio import Queue, Task, create_task, wait_for
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack, suppress
from functools import partial, wraps
from types import TracebackType
from typing import Any, Generic, TypeVar, cast, overload

from .types import ASGIApp

BoundASGIApp = TypeVar("BoundASGIApp", bound=ASGIApp)


class Lifespan(Generic[BoundASGIApp]):
    """Implement the lifespan protocol like a server. Takes an ASGI app."""

    app: BoundASGIApp
    timeout: float | None
    task: Task | None = None
    state: MutableMapping[str, Any] | None = None

    def __init__(self, app: BoundASGIApp, *, timeout: None | int | float = None) -> None:
        self.app = app
        self.timeout = float(timeout) if timeout else None

    async def start_raw(self) -> BoundASGIApp:
        """Start routine without timeout."""
        if self.task is not None:
            return self.app
        # inverted, we have server view
        self.send_queue: Queue[MutableMapping[str, Any]] = Queue()
        self.receive_queue: Queue[MutableMapping[str, Any]] = Queue()
        self.state = {}
        self.send_queue.put_nowait({"type": "lifespan.startup"})
        self.task = create_task(
            self.app(  # type: ignore
                {
                    "type": "lifespan",
                    "asgi": {"version": "3.0", "spec_version": "2.0"},
                    "state": self.state,
                },
                # inverted send, receive because we are emulating the server
                self.send_queue.get,
                self.receive_queue.put,
            )
        )
        response = await self.receive_queue.get()
        match cast(Any, response.get("type")):
            case "lifespan.startup.complete":
                ...
            case "lifespan.startup.failed":
                raise RuntimeError("Lifespan startup failed:", response.get("msg") or "")
        return self.app

    async def __aenter__(self) -> BoundASGIApp:
        """Start routine with optional timeout."""
        if self.timeout:
            return await wait_for(self.start_raw(), self.timeout)
        return await self.start_raw()

    async def shutdown_raw(self) -> None:
        """Shutdown routine without timeout."""
        task = self.task
        if task is None:
            return
        self.task = None
        if task.done():
            raise RuntimeError("Lifespan task errored:", task.exception())

        self.send_queue.put_nowait({"type": "lifespan.shutdown"})
        response = await self.receive_queue.get()
        match response.get("type"):
            case "lifespan.shutdown.complete":
                ...
            case "lifespan.shutdown.failed":
                raise RuntimeError("Lifespan shutdown failed:", response.get("msg") or "")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        """Shutdown routine with optional timeout."""
        if self.timeout:
            await wait_for(self.shutdown_raw(), self.timeout)
        await self.shutdown_raw()


class MuteInteruptException(BaseException):
    """Silent exception which is handled by LifespanHook."""


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
    """Helper for creating a library lifespan integration."""
    if app is None:
        return partial(LifespanHook, setup=setup, do_forward=do_forward)

    shutdown_stack: AsyncExitStack | None = None

    @wraps(app)
    async def app_wrapper(
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        """Wraps the ASGI callable. Provides a forward."""
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
    "Lifespan",
    "LifespanHook",
    "ASGIApp",
]
