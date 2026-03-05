# First Production Run

Use this checklist before shipping a Monkay-enabled package.

## Runtime Checklist

1. Ensure all startup preloads are deterministic and idempotent.
2. Ensure settings import path is valid in deployment environment.
3. Confirm extension ordering is explicit if order matters.
4. Confirm deprecated lazy imports include `reason` and `new_attribute`.

## Quality Gates

Run all local gates:

```shell
task check
```

Equivalent direct commands:

```shell
hatch run lint
hatch run check_types
hatch test
```

## Documentation Gates

```shell
hatch run docs:prepare
hatch run docs:build
```
