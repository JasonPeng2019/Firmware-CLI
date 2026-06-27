#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def parse_name_status(raw: str) -> dict[str, str]:
    items: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        items[path] = status
    return items


def to_commit_list(raw: str) -> list[str]:
    return [line for line in raw.splitlines() if line.strip()]


def render_markdown(payload: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append(f"# Ref Comparison: {payload['left']} vs {payload['right']}")
    lines.append("")
    lines.append(f"- repo_root: `{payload['repo_root']}`")
    lines.append(f"- merge_base: `{payload['merge_base']}`")
    lines.append("")
    lines.append("## Commits only in left")
    for item in payload["left_only_commits"]:
        lines.append(f"- `{item}`")
    if not payload["left_only_commits"]:
        lines.append("- none")
    lines.append("")
    lines.append("## Commits only in right")
    for item in payload["right_only_commits"]:
        lines.append(f"- `{item}`")
    if not payload["right_only_commits"]:
        lines.append("- none")
    lines.append("")
    lines.append("## Files changed on both sides")
    for row in payload["overlap"]:
        lines.append(
            f"- `{row['path']}`: left={row['left_status']} right={row['right_status']}"
        )
    if not payload["overlap"]:
        lines.append("- none")
    lines.append("")
    lines.append("## Files only in left")
    for path in payload["left_only_files"]:
        lines.append(f"- `{path}`")
    if not payload["left_only_files"]:
        lines.append("- none")
    lines.append("")
    lines.append("## Files only in right")
    for path in payload["right_only_files"]:
        lines.append(f"- `{path}`")
    if not payload["right_only_files"]:
        lines.append("- none")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory two git refs and report overlapping vs unique changes."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    parser.add_argument("--base", default=None)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    base = args.base or git(repo_root, "merge-base", args.left, args.right)

    left_commits = to_commit_list(git(repo_root, "log", "--oneline", f"{base}..{args.left}"))
    right_commits = to_commit_list(git(repo_root, "log", "--oneline", f"{base}..{args.right}"))

    left_changes = parse_name_status(
        git(repo_root, "diff", "--name-status", f"{base}..{args.left}")
    )
    right_changes = parse_name_status(
        git(repo_root, "diff", "--name-status", f"{base}..{args.right}")
    )

    overlap_paths = sorted(set(left_changes) & set(right_changes))
    left_only_files = sorted(set(left_changes) - set(right_changes))
    right_only_files = sorted(set(right_changes) - set(left_changes))

    payload: dict[str, object] = {
        "repo_root": str(repo_root),
        "left": args.left,
        "right": args.right,
        "merge_base": base,
        "left_only_commits": left_commits,
        "right_only_commits": right_commits,
        "left_only_files": left_only_files,
        "right_only_files": right_only_files,
        "overlap": [
            {
                "path": path,
                "left_status": left_changes[path],
                "right_status": right_changes[path],
            }
            for path in overlap_paths
        ],
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(render_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
