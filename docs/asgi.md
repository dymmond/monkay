# ASGI

Given that monkay is used from a bunc of libraries which hook into ASGI lifespans,
we have also some helpers.

## lifespan

Wraps an asgi application as AsyncContextManager and run the lifespan protocol.

## LifespanProvider

For use with asgi servers which does not implement the lifespan protocol. Here we just hook into the eventloop and bring lifespan to the ASGI app.

!!! Warning
    Do not use with ASGI servers which speak the lifespan protocol.

## LifespanHook

You have a library with setup/shutdown routines and want to integrate it with lifespan in an ASGI webserver?
Or you have django, ... which still doesn't support lifespan?

This middleware is your life-saver.
