from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

INCLUDE_PATTERN = re.compile(r"\{!>\s*(?P<path>[^}]+?)\s*!?\}")
FENCED_INCLUDE_PATTERN = re.compile(
    r"```(?P<lang>[^\n`]*)\n[ \t]*\{!>\s*(?P<path>[^}]+?)\s*!?\}[ \t]*\n```",
    re.MULTILINE,
)

LANGUAGE_BY_SUFFIX = {
    ".bash": "bash",
    ".dockerfile": "dockerfile",
    ".js": "javascript",
    ".json": "json",
    ".md": "markdown",
    ".py": "python",
    ".sh": "bash",
    ".toml": "toml",
    ".txt": "text",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}

MARKDOWN_SUFFIXES = {".md", ".markdown"}


class DocsPipelineError(RuntimeError):
    """Raised when docs generation or build fails."""


def _normalize_newlines(content: str) -> str:
    """Normalize newline representation for deterministic output.

    Args:
        content: Input text from markdown/include files.

    Returns:
        Text with CRLF/CR normalized to LF.
    """
    return content.replace("\r\n", "\n").replace("\r", "\n")


def infer_language(path: Path) -> str:
    """Infer syntax highlighting language for an included file.

    Args:
        path: Include target path.

    Returns:
        Language identifier for fenced code blocks.
    """
    suffix = path.suffix.lower()
    if path.name.lower() == "dockerfile":
        return "dockerfile"
    return LANGUAGE_BY_SUFFIX.get(suffix, "text")


def _resolve_include_path(include_expr: str, source_file: Path, include_base_dir: Path) -> Path:
    """Resolve include target path using base-path semantics first.

    Resolution order:
    1. ``include_base_dir / include_expr`` (MkDocs-like base behavior)
    2. ``source_file.parent / include_expr`` (source-relative fallback)

    Args:
        include_expr: Path expression found in include directive.
        source_file: Markdown file currently being rendered.
        include_base_dir: Base include directory.

    Returns:
        Resolved include file path.

    Raises:
        DocsPipelineError: If no file exists for the include expression.
    """
    candidates = [
        (include_base_dir / include_expr).resolve(),
        (source_file.parent / include_expr).resolve(),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise DocsPipelineError(
        f"Include path does not exist for {source_file}: {include_expr} -> "
        f"{candidates[0]} (base), {candidates[1]} (source-relative)"
    )


def _render_markdown_file(
    source_file: Path,
    include_base_dir: Path,
    stack: tuple[Path, ...],
) -> str:
    """Render one markdown file with recursive include expansion.

    Args:
        source_file: Markdown file to render.
        include_base_dir: Base include directory.
        stack: Include traversal stack for cycle detection.

    Returns:
        Fully rendered markdown with includes expanded.

    Raises:
        DocsPipelineError: If include cycles are detected.
    """
    resolved_source = source_file.resolve()
    if resolved_source in stack:
        cycle = " -> ".join(str(path) for path in (*stack, resolved_source))
        raise DocsPipelineError(f"Include cycle detected: {cycle}")

    content = _normalize_newlines(source_file.read_text(encoding="utf-8"))
    next_stack = (*stack, resolved_source)

    def render_file(path: Path) -> str:
        if path.suffix.lower() in MARKDOWN_SUFFIXES:
            return _render_markdown_file(path, include_base_dir, next_stack).rstrip("\n")
        return _normalize_newlines(path.read_text(encoding="utf-8")).rstrip("\n")

    def replace_fenced(match: re.Match[str]) -> str:
        include_expr = match.group("path").strip()
        include_path = _resolve_include_path(include_expr, source_file, include_base_dir)
        body = render_file(include_path)
        language = match.group("lang").strip() or infer_language(include_path)
        if body:
            return f"```{language}\n{body}\n```"
        return f"```{language}\n```"

    def replace(match: re.Match[str]) -> str:
        include_expr = match.group("path").strip()
        include_path = _resolve_include_path(include_expr, source_file, include_base_dir)
        body = render_file(include_path)
        suffix = include_path.suffix.lower()
        if suffix in MARKDOWN_SUFFIXES:
            return body
        language = infer_language(include_path)
        if body:
            return f"```{language}\n{body}\n```"
        return f"```{language}\n```"

    rendered = FENCED_INCLUDE_PATTERN.sub(replace_fenced, content)
    rendered = INCLUDE_PATTERN.sub(replace, rendered)
    if not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def prepare_docs_tree(source_dir: Path, output_dir: Path) -> list[Path]:
    """Generate build-ready docs by expanding include directives.

    Args:
        source_dir: Source markdown root (unexpanded docs).
        output_dir: Build-ready destination directory.

    Returns:
        List of generated output file paths.

    Raises:
        DocsPipelineError: If source directory is missing.
    """
    if not source_dir.is_dir():
        raise DocsPipelineError(f"Source docs directory not found: {source_dir}")
    include_base_dir = source_dir

    tmp_output_dir = output_dir.parent / f".{output_dir.name}.tmp"
    if tmp_output_dir.exists():
        shutil.rmtree(tmp_output_dir)
    tmp_output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for source_file in sorted(source_dir.rglob("*")):
        if source_file.is_dir():
            continue
        relative = source_file.relative_to(source_dir)
        target = tmp_output_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        if source_file.suffix.lower() in MARKDOWN_SUFFIXES:
            rendered = _render_markdown_file(source_file, include_base_dir, stack=())
            target.write_text(rendered, encoding="utf-8")
        else:
            shutil.copy2(source_file, target)

        generated.append(target)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    tmp_output_dir.replace(output_dir)
    return [output_dir / path.relative_to(tmp_output_dir) for path in generated]


def run_zensical(
    *,
    project_root: Path,
    config_file: Path,
    command: str,
    clean: bool = False,
    dev_addr: str | None = None,
    open_browser: bool = False,
) -> None:
    """Run a Zensical command with a fixed configuration path.

    Args:
        project_root: Repository root used as command working directory.
        config_file: Zensical config file path.
        command: Zensical command, e.g. ``build`` or ``serve``.
        clean: Whether to pass ``--clean`` for build command.
        dev_addr: Optional serve address in ``host:port`` form.
        open_browser: Whether to pass ``--open`` in serve mode.

    Raises:
        DocsPipelineError: If the zensical process exits with a non-zero code.
    """
    cli = ["zensical", command, "--config-file", str(config_file)]
    if command == "build" and clean:
        cli.append("--clean")
    if command == "serve":
        if dev_addr:
            cli.extend(["--dev-addr", dev_addr])
        if open_browser:
            cli.append("--open")
    try:
        subprocess.run(cli, check=True, cwd=project_root)
    except subprocess.CalledProcessError as exc:
        raise DocsPipelineError(
            f"Zensical command failed with exit code {exc.returncode}: {' '.join(cli)}"
        ) from exc
