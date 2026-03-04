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

## Quality Commands

### Using Taskfile

```shell
task lint
task format
task typecheck
task test
task coverage
task release_checks
```

### Using Hatch Directly

```shell
hatch run lint
hatch run format
hatch run check_types
hatch test
hatch test --cover
```

## Docs Workflow (Zensical)

Prepare docs (expands include directives and examples):

```shell
hatch run docs:prepare
```

Build docs:

```shell
hatch run docs:build
```

Serve docs with live source refresh:

```shell
hatch run docs:serve
```

Verify `docs_src` snippets:

```shell
hatch run docs:verify
```

## Pull Request Expectations

1. Keep changes small and reviewable.
2. Add tests for bug fixes and behavior changes.
3. Keep public API backward-compatible unless a break is explicitly planned.
4. Run `task release_checks` before opening or updating a PR.
