# Contributing

Thanks for contributing to Monkay.

## Development Setup

```shell
git clone https://github.com/YOUR-USERNAME/monkay.git
cd monkay
pip install hatch
```

Optional explicit environment bootstrap:

```shell
hatch env create
hatch env create docs
```

## Taskfile Workflow

Monkay ships both `Taskfile.yml` and `Taskfile.yaml` for compatibility.

```shell
task lint
task format
task typecheck
task test
task coverage
task docs
task docs:serve
task clean
task check
```

## Hatch Equivalents

```shell
hatch run lint
hatch run format
hatch run check_types
hatch test
hatch test --cover
hatch run docs:build
hatch run docs:serve
```

## Docs Workflow

Prepare docs source expansion:

```shell
hatch run docs:prepare
```

Build docs:

```shell
hatch run docs:build
```

Serve docs:

```shell
hatch run docs:serve
```

Verify Python snippets under `docs_src`:

```shell
hatch run docs:verify
```

## Pull Request Expectations

1. Keep changes small and reviewable.
2. Add tests for behavior changes and bug fixes.
3. Preserve public API compatibility.
4. Run `task check` and `task docs` before opening/updating a PR.
