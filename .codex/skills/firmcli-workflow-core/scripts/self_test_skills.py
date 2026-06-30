from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_SKILLS = (
    "firmcli-workflow-core",
    "firmcli-specs",
    "firmcli-build",
    "firmcli-review",
    "firmcli-spec-loop",
    "firmcli-fix-bug",
    "firmcli-test-suite",
    "firmcli-write-process",
    "firmcli-markdown-audit",
    "python-change",
)

EXPECTED_SOURCE_FILES = (
    ".claude/commands/build.md",
    ".claude/commands/fix-bug.md",
    ".claude/commands/review.md",
    ".claude/commands/spec-loop.md",
    ".claude/commands/specs.md",
    ".claude/commands/test-suite.md",
    ".claude/commands/write-process.md",
    "superpowers/agent_index_START_HERE.md",
    "superpowers/agent_consistency_playbook.md",
    "superpowers/agent_doc_sync_playbook.md",
    "superpowers/agent_coding_playbook.md",
    "superpowers/agent_portability_playbook.md",
    "superpowers/agent_script_doc_playbook.md",
    "superpowers/spec_build_review_loop_playbook.md",
)

EXPECTED_CORE_SCRIPTS = (
    "scaffold_workflow_doc.py",
    "run_check_ladder.py",
    "self_test_skills.py",
)


def is_project_root(path: Path) -> bool:
    return (path / ".claude" / "commands").is_dir() and (path / "superpowers").is_dir()


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if is_project_root(parent):
            return parent
        candidate = parent / "Firmware-CLI"
        if is_project_root(candidate):
            return candidate
    raise RuntimeError("Could not locate the Firmware-CLI project root")


def parse_frontmatter(skill_md: Path) -> tuple[str | None, str | None]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None, None
    name_match = re.search(r"^name:\s*(.+)$", match.group(1), re.MULTILINE)
    desc_match = re.search(r"^description:\s*(.+)$", match.group(1), re.MULTILINE)
    name = name_match.group(1).strip().strip('"') if name_match else None
    description = desc_match.group(1).strip().strip('"') if desc_match else None
    return name, description


def check_skill(skill_dir: Path, errors: list[str]) -> None:
    skill_md = skill_dir / "SKILL.md"
    openai_yaml = skill_dir / "agents" / "openai.yaml"

    if not skill_md.exists():
        errors.append(f"missing {skill_md}")
        return
    if not openai_yaml.exists():
        errors.append(f"missing {openai_yaml}")

    name, description = parse_frontmatter(skill_md)
    if name != skill_dir.name:
        errors.append(f"{skill_md} frontmatter name mismatch: {name!r}")
    if not description or "[TODO" in description:
        errors.append(f"{skill_md} has an incomplete description")

    text = skill_md.read_text(encoding="utf-8")
    if "[TODO" in text:
        errors.append(f"{skill_md} still contains template TODO text")


def maybe_run_quick_validate(skill_dir: Path, notices: list[str], errors: list[str]) -> None:
    validator = (
        Path.home()
        / ".codex"
        / "skills"
        / ".system"
        / "skill-creator"
        / "scripts"
        / "quick_validate.py"
    )
    if not validator.exists():
        notices.append(
            "quick_validate.py not found in the user skill-creator bundle; skipped external validation"
        )
        return
    completed = subprocess.run(
        [sys.executable, str(validator), str(skill_dir)],
        capture_output=True,
        text=True,
        cwd=str(repo_root()),
    )
    if completed.returncode != 0:
        output = (completed.stdout or "") + (completed.stderr or "")
        errors.append(f"quick_validate failed for {skill_dir.name}: {output.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the local Firmware-CLI Codex skill suite."
    )
    parser.add_argument(
        "--skip-quick-validate",
        action="store_true",
        help="Skip calling the global quick_validate helper even if it is available.",
    )
    args = parser.parse_args()

    root = repo_root()
    skills_root = root / ".codex" / "skills"
    core_scripts = skills_root / "firmcli-workflow-core" / "scripts"

    errors: list[str] = []
    notices: list[str] = []

    for rel_path in EXPECTED_SOURCE_FILES:
        if not (root / rel_path).exists():
            errors.append(f"missing source file: {rel_path}")

    for script_name in EXPECTED_CORE_SCRIPTS:
        if not (core_scripts / script_name).exists():
            errors.append(f"missing core script: {script_name}")

    for skill_name in EXPECTED_SKILLS:
        skill_dir = skills_root / skill_name
        if not skill_dir.exists():
            errors.append(f"missing skill directory: {skill_name}")
            continue
        check_skill(skill_dir, errors)
        if not args.skip_quick_validate:
            maybe_run_quick_validate(skill_dir, notices, errors)

    if notices:
        for notice in notices:
            print(f"NOTICE: {notice}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Skill suite validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
