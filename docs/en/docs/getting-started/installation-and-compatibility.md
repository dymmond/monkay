# Installation and Compatibility

## Runtime Requirements

- Python 3.10 or newer
- No required runtime dependencies

## Install Monkay

```shell
pip install monkay
```

## Optional Dependency Groups

Monkay exposes optional dependency groups for local development workflows:

```shell
pip install -e .[testing]
pip install -e .[docs]
```

## Verify Environment

```shell
python --version
python -c "import monkay; print(monkay.__all__)"
```

## Development Toolchain

Project tooling is centered around:

- Ruff (`task lint`, `task format`)
- Ty (`task typecheck`)
- Pytest (`task test`)
- MkDocs/Zensical (`task docs`, `task docs:serve`)

## Related

- [Install and first module](install-and-first-module.md)
- [Contributing](../project/contributing.md)
