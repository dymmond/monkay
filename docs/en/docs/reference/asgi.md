# ASGI

Given that monkay is used from a bunch of libraries which hook into ASGI lifespans,
we have also some ASGI helpers.

## `CMToASGIMiddleware`

Transforms a `ContextManager` (async/sync) to an ASGI-Middleware. This is quite handy if you want to manipulate the `ContextVar`s
and inject e.g. a database but only for a part of the ASGI monolith.
You can also provide an async/sync `Callable`, which receives the scope and is expected to return a `ContextManager` (async/sync).

!!! Note
    When a `ContextManager` is also callable, it is still treated as `ContextManager` (neccessary for compatibility). If you want it to be called,
    use `lambda scope: callable_cm(scope)`.

**Edgy Example**

Here we wrap an app with edgy.
```python
{!> ../../../../docs_src/asgi/cm/basic.py !}
```

Why is `asgi(...)` not enough?
We only manipulate the lifespan protocol with asgi, but don't set the instance.

!!! Note
    `return_cm` is a callable which returns a contextmanager. This is a way to generate a contextmanager every request.


This is only one example. We can do much more by injecting ContextManager as middleware or generating them. No need to program boilerplate code anymore for this.


## `Lifespan`

Wraps an asgi application as `AsyncContextManager` and run the lifespan protocol. You can optionally provide an `timeout` parameter.
This can be handy for spurious hangups when used for testing. You can also use `__aenter__()` and `__aexit__()` manually for e.g. server implementations
of lifespan.

**Simple cli usage**

```python
{!> ../../../../docs_src/asgi/lifespan/Lifespan.py !}
```

**Testing**

```python
{!> ../../../../docs_src/asgi/lifespan/LifespanHookTesting.py !}
```

**ASGI Server**

If you want to add asgi lifespan support to an ASGI server you can do as well:

```python
{!> ../../../../docs_src/asgi/lifespan/Lifespan_server.py !}
```

## `LifespanHook`

This is the reverse part to Lifespan.

You have a library with setup/shutdown routines and want to integrate it with lifespan in an ASGI webserver?
Or you have django, ... which still doesn't support lifespan?

This middleware is your life-saver.

For hooking simply provide a setup async callable which returns an `AsyncExitStack` (contextlib) for cleaning up.
LifespanHook has an endpoint mode, so that lifespan events are not forwarded.
This is required for e.g. django, which still doesn't support lifespans.

**Example library integration**

```python
{!> ../../../../docs_src/asgi/lifespan/LifespanHook.py !}
```

**Example django**

Django hasn't lifespan support yet. To use it with lifespan servers (and middleware) we can do something like this:
```python
{!> ../../../../docs_src/asgi/lifespan/LifespanHookDjango.py !}
```

**Example testing**

You need a quick endpoint for lifespan? Here it is.

```python
{!> ../../../../docs_src/asgi/lifespan/LifespanHookTesting.py !}
```

## Forwarded attributes feature of `LifespanHook`

Access on attributes which doesn't exist on `LifespanHook` are forwarded to the wrapped app (callable which can also be something like an Lilya or Esmerald instance). This allows users to access methods on it without unwrapping. Setting and deleting however doesn't work this way.
To unwrap to the native instance use the `__wrapped__` attribute.


The yielded app of `Lifespan` is not wrapped and can be natively used.
