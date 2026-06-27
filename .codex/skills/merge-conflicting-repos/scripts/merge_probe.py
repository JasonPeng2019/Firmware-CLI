#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def conflicted_paths_from_status(raw: str) -> list[str]:
    conflicted_prefixes = {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
    paths: list[str] = []
    for line in raw.splitlines():
        if not line:
            continue
        prefix = line[:2]
        path = line[3:]
        if prefix in conflicted_prefixes:
            paths.append(path)
    return paths


def touched_paths_from_status(raw: str) -> list[str]:
    paths: list[str] = []
    for line in raw.splitlines():
        if not line:
            continue
        paths.append(line[3:])
    return paths


def render_markdown(payload: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append(f"# Merge Probe: {payload['target']} <- {payload['other']}")
    lines.append("")
    lines.append(f"- repo_root: `{payload['repo_root']}`")
    lines.append(f"- clean_merge: `{payload['clean_merge']}`")
    lines.append(f"- merge_exit_code: `{payload['merge_exit_code']}`")
    lines.append("")
    lines.append("## Conflicted files")
    for item in payload["conflicted_files"]:
        lines.append(f"- `{item}`")
    if not payload["conflicted_files"]:
        lines.append("- none")
    lines.append("")
    lines.append("## All touched files")
    for item in payload["touched_files"]:
        lines.append(f"- `{item}`")
    if not payload["touched_files"]:
        lines.append("- none")
    lines.append("")
    lines.append("## Merge stderr")
    lines.append("```text")
    lines.append(str(payload["merge_stderr"]).strip())
    lines.append("```")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely probe a merge in a temporary detached worktree."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--other", required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    tempdir = Path(tempfile.mkdtemp(prefix="merge-probe-"))
    worktree_path = tempdir / "worktree"

    payload: dict[str, object] = {
        "repo_root": str(repo_root),
        "target": args.target,
        "other": args.other,
        "clean_merge": False,
        "merge_exit_code": None,
        "merge_stdout": "",
        "merge_stderr": "",
        "conflicted_files": [],
        "touched_files": [],
        "status_lines": [],
    }

    try:
        run_git(repo_root, "worktree", "add", "--detach", str(worktree_path), args.target)
        merge_result = run_git(
            worktree_path,
            "merge",
            "--no-commit",
            "--no-ff",
            args.other,
            check=False,
        )
        status_result = run_git(worktree_path, "status", "--porcelain", check=False)

        payload["merge_exit_code"] = merge_result.returncode
        payload["merge_stdout"] = merge_result.stdout.strip()
        payload["merge_stderr"] = merge_result.stderr.strip()
        payload["status_lines"] = [line for line in status_result.stdout.splitlines() if line.strip()]
        payload["conflicted_files"] = conflicted_paths_from_status(status_result.stdout)
        payload["touched_files"] = touched_paths_from_status(status_result.stdout)
        payload["clean_merge"] = merge_result.returncode == 0 and not payload["conflicted_files"]

        run_git(worktree_path, "merge", "--abort", check=False)
        run_git(worktree_path, "reset", "--hard", "HEAD", check=False)
    finally:
        run_git(repo_root, "worktree", "remove", "--force", str(worktree_path), check=False)
        shutil.rmtree(tempdir, ignore_errors=True)

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(render_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
