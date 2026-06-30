from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def is_project_root(path: Path) -> bool:
    return (path / ".codex" / "skills").is_dir() and (path / "superpowers").is_dir()


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if is_project_root(parent):
            return parent
        candidate = parent / "Firmware-CLI"
        if is_project_root(candidate):
            return candidate
    raise RuntimeError("Could not locate the Firmware-CLI project root")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("slug cannot be empty after normalization")
    return slug


def spec_template(slug: str, task: str, roadmap: str | None) -> str:
    roadmap_line = roadmap or "[add roadmap anchor if known]"
    return f"""> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# {slug.replace("-", " ")}

## Goal in plain English

Task: {task}
Roadmap anchor: {roadmap_line}

## Scope and non-scope

In scope:

Out of scope:

## Reconciliation summary

- Build plan:
- Current code:
- Other docs or notes:
- Disagreements:

## Design

## Board-facts-as-data and origin tags

## Documentation plan

## Portability

## Verification plan

## Acceptance criteria

## Verified

## Pending verification
"""


def review_template(slug: str, task: str) -> str:
    return f"""# Review for {slug}

Task: {task}

## Verdict

CHANGES REQUESTED

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |

## Hardware hand-off status

## What's genuinely good
"""


def process_template(slug: str, task: str, roadmap: str | None) -> str:
    roadmap_line = roadmap or "[add roadmap anchor if known]"
    return f"""# Process ledger for {slug}

## Goal and roadmap anchor

Task: {task}
Roadmap anchor: {roadmap_line}

## Done

## In progress

## TODO

## Limitations and known gaps

## Hardware hand-off

## Open decisions and surfaced issues

## Verified

## Pending verification
"""


def render(kind: str, slug: str, task: str, roadmap: str | None) -> str:
    if kind == "spec":
        return spec_template(slug, task, roadmap)
    if kind == "review":
        return review_template(slug, task)
    if kind == "process":
        return process_template(slug, task, roadmap)
    raise ValueError(f"unsupported kind: {kind}")


def output_path(base: Path, kind: str, slug: str) -> Path:
    suffix = {
        "spec": "_spec.md",
        "review": "_review.md",
        "process": "_process.md",
    }[kind]
    return base / f"{slug}{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a spec, review, or process markdown shell in markdowns/curr."
    )
    parser.add_argument("kind", choices=("spec", "review", "process"))
    parser.add_argument("slug", help="Kebab-case slug or free text to normalize.")
    parser.add_argument("--task", required=True, help="Plain-English task summary.")
    parser.add_argument("--roadmap", help="Optional roadmap anchor like R12 or G3.")
    parser.add_argument(
        "--path",
        default=str(repo_root() / "markdowns" / "curr"),
        help="Output directory. Defaults to markdowns/curr under the repo root.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing file instead of leaving it untouched.",
    )
    args = parser.parse_args()

    slug = slugify(args.slug)
    base = Path(args.path).resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = output_path(base, args.kind, slug)

    if target.exists() and not args.force:
        print(target)
        return 0

    target.write_text(render(args.kind, slug, args.task, args.roadmap), encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
