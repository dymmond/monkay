#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
import threading
from pathlib import Path

try:
    from scripts.docs_pipeline import DocsPipelineError, prepare_docs_tree, run_zensical
except ModuleNotFoundError:  # pragma: no cover
    from docs_pipeline import DocsPipelineError, prepare_docs_tree, run_zensical


ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCE_DOCS_DIR = ROOT_DIR / "docs" / "en" / "docs"
GENERATED_DOCS_DIR = ROOT_DIR / "docs" / "generated"
DEFAULT_CONFIG_FILE = ROOT_DIR / "mkdocs.yaml"
DEFAULT_SITE_DIR = ROOT_DIR / "site"
DEFAULT_CACHE_DIR = ROOT_DIR / ".cache"
SOURCE_DOCS_SNIPPETS_DIR = ROOT_DIR / "docs_src"


def _snapshot(paths: list[Path]) -> dict[str, int]:
    """Build a filesystem timestamp snapshot for watch mode.

    Args:
        paths: Files/directories to snapshot recursively.

    Returns:
        Mapping of absolute file path to nanosecond mtime.
    """
    state: dict[str, int] = {}
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            state[str(path.resolve())] = path.stat().st_mtime_ns
            continue
        for candidate in sorted(path.rglob("*")):
            if candidate.is_file():
                state[str(candidate.resolve())] = candidate.stat().st_mtime_ns
    return state


def _resolve_config(config_file: str) -> Path:
    """Resolve and validate docs config file path.

    Args:
        config_file: Path to config file relative to repository root.

    Returns:
        Absolute config file path.

    Raises:
        DocsPipelineError: If the config file does not exist.
    """
    config_path = (ROOT_DIR / config_file).resolve()
    if not config_path.is_file():
        raise DocsPipelineError(f"Config file not found: {config_path}")
    return config_path


def _prepare() -> list[Path]:
    """Prepare generated documentation tree.

    Returns:
        List of generated files.
    """
    generated = prepare_docs_tree(SOURCE_DOCS_DIR, GENERATED_DOCS_DIR)
    print(f"Prepared {len(generated)} docs file(s) in {GENERATED_DOCS_DIR}")
    return generated


def _watch_sources(stop_event: threading.Event, interval: float = 0.5) -> None:
    """Watch source docs/snippets and regenerate docs on changes.

    Args:
        stop_event: Event used to stop watcher loop.
        interval: Poll interval in seconds.
    """
    watch_paths = [SOURCE_DOCS_DIR, SOURCE_DOCS_SNIPPETS_DIR]
    previous = _snapshot(watch_paths)
    while not stop_event.wait(interval):
        current = _snapshot(watch_paths)
        if current == previous:
            continue
        previous = current
        try:
            _prepare()
            print("Docs refreshed.")
        except DocsPipelineError as exc:
            print(f"Docs refresh failed: {exc}")


def cmd_prepare(_: argparse.Namespace) -> None:
    """Command handler for docs preparation."""
    _prepare()
    print("Docs prepared.")


def cmd_clean(_: argparse.Namespace) -> None:
    """Command handler for docs cleanup."""
    for path in [GENERATED_DOCS_DIR, DEFAULT_SITE_DIR, DEFAULT_CACHE_DIR]:
        shutil.rmtree(path, ignore_errors=True)
    print("Docs artifacts removed.")


def cmd_build(args: argparse.Namespace) -> None:
    """Command handler for docs build."""
    config_path = _resolve_config(args.config_file)
    _prepare()
    run_zensical(
        project_root=ROOT_DIR,
        config_file=config_path,
        command="build",
        clean=args.clean,
    )
    print("Docs built with Zensical.")


def cmd_serve(args: argparse.Namespace) -> None:
    """Command handler for docs serve."""
    config_path = _resolve_config(args.config_file)
    _prepare()

    stop_event = threading.Event()
    watch_thread: threading.Thread | None = None
    if args.watch_sources:
        watch_thread = threading.Thread(
            target=_watch_sources,
            args=(stop_event,),
            daemon=True,
        )
        watch_thread.start()
        print(f"Watching docs sources: {SOURCE_DOCS_DIR} and {SOURCE_DOCS_SNIPPETS_DIR}")

    try:
        run_zensical(
            project_root=ROOT_DIR,
            config_file=config_path,
            command="serve",
            dev_addr=f"{args.host}:{args.port}",
            open_browser=args.open,
        )
    finally:
        stop_event.set()
        if watch_thread is not None:
            watch_thread.join(timeout=1.0)


def _build_parser() -> argparse.ArgumentParser:
    """Create CLI parser for docs automation commands."""
    parser = argparse.ArgumentParser(
        prog="docs.py",
        description="Monkay docs utility commands for Zensical.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Generate build-ready Markdown by expanding include directives.",
    )
    prepare_parser.set_defaults(func=cmd_prepare)

    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove generated docs artifacts and build output.",
    )
    clean_parser.set_defaults(func=cmd_clean)

    build_parser = subparsers.add_parser("build", help="Prepare docs and run `zensical build`.")
    build_parser.add_argument(
        "-f",
        "--config-file",
        default=str(DEFAULT_CONFIG_FILE.relative_to(ROOT_DIR)),
        help="Config file path relative to repository root.",
    )
    build_parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean zensical cache before build.",
    )
    build_parser.set_defaults(func=cmd_build)

    serve_parser = subparsers.add_parser("serve", help="Prepare docs and run `zensical serve`.")
    serve_parser.add_argument(
        "-f",
        "--config-file",
        default=str(DEFAULT_CONFIG_FILE.relative_to(ROOT_DIR)),
        help="Config file path relative to repository root.",
    )
    serve_parser.add_argument(
        "--host", default="127.0.0.1", help="Host interface for docs server."
    )
    serve_parser.add_argument("--port", type=int, default=8000, help="Port for docs server.")
    serve_parser.add_argument("--open", action="store_true", help="Open docs in the browser.")
    serve_parser.add_argument(
        "--watch-sources",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Watch docs/en/docs and docs_src for changes.",
    )
    serve_parser.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute docs CLI.

    Args:
        argv: Optional argument vector for programmatic usage.

    Returns:
        Process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        handler = args.func
        handler(args)
    except DocsPipelineError as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
