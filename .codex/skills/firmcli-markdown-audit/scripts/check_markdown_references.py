"""Check local file and run references from markdown audit targets."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

DEFAULT_EXCLUDE_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "tmp",
}

RUN_ID_RE = re.compile(r"\b20\d{6}T\d{6}Z-[0-9a-f]{8}\b")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
KNOWN_PREFIXES = (
    ".codex/",
    ".claude/",
    "boards/",
    "docs/",
    "firmware/",
    "markdowns/",
    "runs/",
    "scripts/",
    "src/",
    "superpowers/",
    "tests/",
)
KNOWN_SUFFIXES = (
    ".bat",
    ".cfg",
    ".cmd",
    ".h",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".rst",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
)
COMMAND_PREFIXES = (
    "--",
    "py ",
    "python ",
    "ruff ",
    "uv ",
    "pytest ",
    "mypy ",
)
TEMPLATE_MARKERS = ("<", ">", "*", "...")


@dataclass(frozen=True)
class ReferenceCheck:
    markdown: str
    reference: str
    kind: str
    target: str
    exists: bool


def repo_root() -> Path:
    return Path.cwd().resolve()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root()).as_posix()
    except ValueError:
        return str(path)


def is_excluded(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        relative = path
    return any(part in DEFAULT_EXCLUDE_PARTS for part in relative.parts)


def iter_markdowns(roots: list[Path]) -> list[Path]:
    root_dir = repo_root()
    files: set[Path] = set()
    for root in roots:
        search_root = (root_dir / root).resolve()
        if not search_root.exists():
            continue
        if search_root.is_file() and search_root.suffix.lower() == ".md":
            if not is_excluded(search_root, root_dir):
                files.add(search_root)
            continue
        for path in search_root.rglob("*.md"):
            if not is_excluded(path, root_dir):
                files.add(path.resolve())
    return sorted(files)


def normalize_reference(value: str) -> str | None:
    candidate = unquote(value.strip().strip("<>").strip())
    if not candidate or candidate.startswith("#"):
        return None
    parsed = urlparse(candidate)
    if parsed.scheme and parsed.scheme not in {"", "file"}:
        return None
    if parsed.scheme == "file":
        candidate = parsed.path
    candidate = candidate.split("#", 1)[0]
    candidate = re.sub(r":\d+(?::\d+)?$", "", candidate)
    candidate = candidate.strip().replace("\\", "/")
    if not candidate:
        return None
    return candidate


def looks_like_local_path(candidate: str) -> bool:
    lowered = candidate.lower()
    if lowered.startswith(KNOWN_PREFIXES):
        return True
    if lowered.endswith(KNOWN_SUFFIXES) and "/" in lowered:
        return True
    return False


def is_command(candidate: str) -> bool:
    lowered = candidate.lower()
    return any(lowered.startswith(prefix) for prefix in COMMAND_PREFIXES)


def is_template_reference(candidate: str) -> bool:
    return any(marker in candidate for marker in TEMPLATE_MARKERS)


def resolve_reference(markdown: Path, reference: str) -> Path:
    root = repo_root()
    candidate = Path(reference)
    if candidate.is_absolute():
        return candidate
    root_target = (root / candidate).resolve()
    if reference.startswith(KNOWN_PREFIXES):
        return root_target
    if root_target.exists():
        return root_target
    return (markdown.parent / candidate).resolve()


def extract_references(markdown: Path) -> list[tuple[str, str]]:
    text = markdown.read_text(encoding="utf-8", errors="replace")
    refs: list[tuple[str, str]] = []
    for run_id in RUN_ID_RE.findall(text):
        refs.append((run_id, f"runs/{run_id}"))
    for raw in BACKTICK_RE.findall(text):
        normalized = normalize_reference(raw)
        if normalized and not is_command(normalized) and looks_like_local_path(normalized):
            refs.append((raw, normalized))
    for raw in LINK_RE.findall(text):
        normalized = normalize_reference(raw)
        if normalized and not is_command(normalized) and looks_like_local_path(normalized):
            refs.append((raw, normalized))
    return refs


def check_markdown(markdown: Path) -> list[ReferenceCheck]:
    checks: list[ReferenceCheck] = []
    seen: set[tuple[str, str]] = set()
    for raw, normalized in extract_references(markdown):
        if (raw, normalized) in seen:
            continue
        seen.add((raw, normalized))
        target = resolve_reference(markdown, normalized)
        template = is_template_reference(normalized)
        kind = "template" if template else "run" if normalized.startswith("runs/") else "path"
        checks.append(
            ReferenceCheck(
                markdown=rel(markdown),
                reference=raw,
                kind=kind,
                target=rel(target),
                exists=True if template else target.exists(),
            )
        )
    return checks


def render_markdown(checks: list[ReferenceCheck], show_all: bool) -> str:
    visible = checks if show_all else [check for check in checks if not check.exists]
    heading = "Markdown Reference Checks" if show_all else "Missing Markdown References"
    output = [
        f"# {heading}",
        "",
        "| Markdown | Kind | Reference | Target | Exists |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in visible:
        output.append(
            f"| {check.markdown} | {check.kind} | `{check.reference}` | "
            f"`{check.target}` | {str(check.exists).lower()} |"
        )
    output.append("")
    output.append(
        f"Checked {len(checks)} references; {sum(not check.exists for check in checks)} missing."
    )
    output.append("")
    return "\n".join(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Markdown file or directory to scan. Defaults to markdowns.",
    )
    parser.add_argument("--all", action="store_true", help="Show existing and missing refs.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--output", type=Path, help="Write output to this path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = [Path(value) for value in args.root] or [Path("markdowns")]
    checks: list[ReferenceCheck] = []
    for markdown in iter_markdowns(roots):
        checks.extend(check_markdown(markdown))

    if args.json:
        rendered = json.dumps([asdict(check) for check in checks], indent=2) + "\n"
    else:
        rendered = render_markdown(checks, args.all)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if any(not check.exists for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
