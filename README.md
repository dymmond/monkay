# Monkay

Monkay is a production-focused module lifecycle toolkit for Python packages.
It helps you ship lazy imports, settings loading, extension orchestration, and
context-isolated state without fragile import-time side effects.

## Why Monkay

Monkay is designed for libraries and applications that need to:

- expose stable public imports while deferring expensive imports,
- run controlled startup preloads and settings evaluation,
- apply pluggable extensions with deterministic conflict behavior,
- isolate mutable state per thread/task for safe tests and request scopes,
- validate module export consistency during development.

## Installation

```shell
pip install monkay
```

Runtime requirement: **Python 3.10+**.

## 60-Second Example

```python
# yourpkg/__init__.py
from monkay import Monkay

monkay = Monkay(
    globals(),
    lazy_imports={
        "json_dumps": "json:dumps",
    },
)

__all__ = ["json_dumps", "monkay"]
```

```python
# yourpkg/main.py
from yourpkg import json_dumps

payload = {"status": "ok"}
print(json_dumps(payload))
```

`json_dumps` is resolved lazily on first access and cached by default.

## Core Capabilities

- `Monkay`: lifecycle coordinator for imports, settings, instances, and extensions
- `load`, `load_any`, `absolutify_import`: import/path helpers
- `Cage`, `TransparentCage`: context-isolated mutable proxies
- `Lifespan`, `LifespanHook`: ASGI lifespan utilities
- `find_missing`, `sorted_exports`: export inspection and debugging helpers

## Public API Stability

Monkay keeps top-level public imports stable via `monkay.__all__`:

- `Monkay`
- `DeprecatedImport`
- `PRE_ADD_LAZY_IMPORT_HOOK`
- `ExtensionProtocol`
- `load`, `load_any`, `absolutify_import`
- `InGlobalsDict`, `UnsetError`, `get_value_from_settings`
- `Cage`, `TransparentCage`

## Documentation

Full docs: [monkay.dymmond.com](https://monkay.dymmond.com)

Recommended order:

1. [Getting Started](https://monkay.dymmond.com/getting-started/)
2. [Tutorials](https://monkay.dymmond.com/tutorials/)
3. [Concepts](https://monkay.dymmond.com/concepts/)
4. [How-to Guides](https://monkay.dymmond.com/guides/)
5. [Reference](https://monkay.dymmond.com/reference/)

## Development Quickstart

Monkay uses **hatch**, **ruff**, **ty**, **pytest**, and **mkdocs/zensical**.

```shell
pip install hatch
hatch run lint
hatch run check_types
hatch test
hatch run docs:build
```

If you use [Task](https://taskfile.dev), Monkay ships both `Taskfile.yml` and `Taskfile.yaml`:

```shell
task check
task coverage
task docs
task docs:serve
```

## Contributing

See [Contributing](https://monkay.dymmond.com/project/contributing/) for setup,
quality gates, docs workflow, and pull request expectations.
