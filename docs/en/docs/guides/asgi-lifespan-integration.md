# ASGI Lifespan Integration

Use Monkay’s ASGI helpers when you need deterministic startup/shutdown control.

## Scenarios

- Integrating framework setup hooks into lifespan.
- Running startup/shutdown in tests with timeout protection.
- Wrapping applications that do not fully implement lifespan behavior.

## Components

- `Lifespan`: drives startup/shutdown like a minimal server harness.
- `LifespanHook`: injects setup/shutdown hooks around an ASGI app.

## Example Paths

- [Reference: ASGI](../reference/asgi.md)
- [Reference: testing](../reference/testing.md)
