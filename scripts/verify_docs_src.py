#!/usr/bin/env python
from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for docs_src verification."""
    parser = argparse.ArgumentParser(description="Verify Python snippets under docs_src.")
    parser.add_argument(
        "--check-file",
        type=Path,
        default=None,
        help="Verify one file instead of scanning the full docs_src tree.",
    )
    parser.add_argument(
        "--import-check",
        action="store_true",
        help="Try importing files after syntax verification.",
    )
    return parser.parse_args()


def verify_syntax(path: Path) -> tuple[bool, str | None]:
    """Validate Python syntax via ``ast.parse``.

    Args:
        path: File path to inspect.

    Returns:
        Tuple of success flag and optional error detail.
    """
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return False, f"{path}: {exc}"
    return True, None


def verify_import(path: Path) -> tuple[bool, str | None]:
    """Best-effort module import verification for a snippet file.

    Args:
        path: File path to import.

    Returns:
        Tuple of success flag and optional error detail.
    """
    module_name = f"_verify_docs_src_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return False, f"{path}: unable to load module spec"
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, f"{path}: {exc}"
    finally:
        sys.modules.pop(module_name, None)


def iter_targets(root: Path, explicit_file: Path | None) -> list[Path]:
    """Resolve verification targets.

    Args:
        root: docs_src root path.
        explicit_file: Optional single file path.

    Returns:
        Sorted list of files to verify.
    """
    if explicit_file is not None:
        return [explicit_file]
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def main() -> int:
    """Run snippet verification checks."""
    args = parse_args()
    root = Path(__file__).resolve().parent.parent / "docs_src"
    targets = iter_targets(root, args.check_file)
    if not targets:
        print("No docs_src Python files found.")
        return 0

    failures: list[str] = []
    for target in targets:
        ok, error = verify_syntax(target)
        if not ok and error is not None:
            failures.append(error)
            continue
        if args.import_check:
            ok, error = verify_import(target)
            if not ok and error is not None:
                failures.append(error)

    if failures:
        print("docs_src verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"docs_src verification passed ({len(targets)} file(s)).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
