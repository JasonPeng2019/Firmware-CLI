"""Find likely redundant markdown pairs for consolidation review."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from itertools import combinations
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

HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}")
STOP_WORDS = {
    "and",
    "are",
    "but",
    "can",
    "for",
    "from",
    "have",
    "into",
    "not",
    "that",
    "the",
    "this",
    "with",
    "you",
}


@dataclass(frozen=True)
class DocumentProfile:
    path: str
    tokens: set[str]
    headings: set[str]


@dataclass(frozen=True)
class Overlap:
    left: str
    right: str
    token_jaccard: float
    shared_headings: list[str]


def repo_root() -> Path:
    return Path.cwd().resolve()


def rel(path: Path) -> str:
    return path.resolve().relative_to(repo_root()).as_posix()


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


def profile(path: Path) -> DocumentProfile:
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    tokens = {token for token in TOKEN_RE.findall(text) if token not in STOP_WORDS}
    headings = {heading.strip().lower() for heading in HEADING_RE.findall(text)}
    return DocumentProfile(path=rel(path), tokens=tokens, headings=headings)


def score(left: DocumentProfile, right: DocumentProfile) -> Overlap:
    union = left.tokens | right.tokens
    token_jaccard = len(left.tokens & right.tokens) / len(union) if union else 0.0
    shared_headings = sorted(left.headings & right.headings)
    return Overlap(
        left=left.path,
        right=right.path,
        token_jaccard=round(token_jaccard, 3),
        shared_headings=shared_headings[:10],
    )


def render_markdown(overlaps: list[Overlap]) -> str:
    output = [
        "# Markdown Overlap Candidates",
        "",
        "| Score | Left | Right | Shared headings |",
        "| ---: | --- | --- | --- |",
    ]
    for item in overlaps:
        output.append(
            f"| {item.token_jaccard:.3f} | {item.left} | {item.right} | "
            f"{'<br>'.join(item.shared_headings)} |"
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
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.25,
        help="Minimum token Jaccard score to report.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum pairs to report.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--output", type=Path, help="Write output to this path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = [Path(value) for value in args.root] or [Path("markdowns")]
    profiles = [profile(path) for path in iter_markdowns(roots)]
    overlaps = [
        item
        for item in (score(left, right) for left, right in combinations(profiles, 2))
        if item.token_jaccard >= args.threshold or item.shared_headings
    ]
    overlaps.sort(key=lambda item: (item.token_jaccard, len(item.shared_headings)), reverse=True)
    overlaps = overlaps[: args.limit]

    if args.json:
        rendered = json.dumps([asdict(item) for item in overlaps], indent=2) + "\n"
    else:
        rendered = render_markdown(overlaps)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
