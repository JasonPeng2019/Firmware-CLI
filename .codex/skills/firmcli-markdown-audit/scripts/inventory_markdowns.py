"""Inventory markdown files for a Firmware-CLI documentation audit."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

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

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
RUN_ID_RE = re.compile(r"\b20\d{6}T\d{6}Z-[0-9a-f]{8}\b")
CODE_REF_RE = re.compile(
    r"`([^`\n]*(?:\.py|\.md|\.toml|\.ya?ml|\.json|\.ps1|\.sh|\.bat|\.txt)[^`\n]*)`"
)
STATUS_RE = re.compile(
    r"\b(todo|blocked|deferred|gap|risk|pass|fail|green|red|obsolete|superseded)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MarkdownInventory:
    path: str
    lines: int
    headings: list[str]
    code_refs: list[str]
    run_ids: list[str]
    status_terms: list[str]


def repo_root() -> Path:
    return Path.cwd().resolve()


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


def rel(path: Path) -> str:
    return path.relative_to(repo_root()).as_posix()


def unique(values: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if limit is not None and len(result) >= limit:
            break
    return result


def inventory_file(path: Path) -> MarkdownInventory:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    headings = [
        f"{match.group(1)} {match.group(2)}" for line in lines if (match := HEADING_RE.match(line))
    ]
    return MarkdownInventory(
        path=rel(path),
        lines=len(lines),
        headings=unique(headings, limit=12),
        code_refs=unique(CODE_REF_RE.findall(text), limit=20),
        run_ids=unique(RUN_ID_RE.findall(text), limit=20),
        status_terms=unique([match.group(1).lower() for match in STATUS_RE.finditer(text)]),
    )


def render_markdown(items: list[MarkdownInventory]) -> str:
    output = [
        "# Markdown Audit Inventory",
        "",
        "| File | Lines | Headings | Code refs | Run IDs | Status terms |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for item in items:
        output.append(
            "| {path} | {lines} | {headings} | {code_refs} | {run_ids} | {status_terms} |".format(
                path=item.path,
                lines=item.lines,
                headings="<br>".join(item.headings),
                code_refs="<br>".join(item.code_refs),
                run_ids="<br>".join(item.run_ids),
                status_terms=", ".join(item.status_terms),
            )
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
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--output", type=Path, help="Write output to this path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = [Path(value) for value in args.root] or [Path("markdowns")]
    items = [inventory_file(path) for path in iter_markdowns(roots)]
    if args.json:
        rendered = json.dumps([asdict(item) for item in items], indent=2) + "\n"
    else:
        rendered = render_markdown(items)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
