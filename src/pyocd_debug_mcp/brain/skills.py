"""Skill loading and deterministic selection for the turnkey brain."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyocd_debug_mcp.board_config import BoardConfig
from pyocd_debug_mcp.runtime_resources import resolve_skills_root

SKILLS_ROOT = resolve_skills_root()  # PROJECT-DEFINED (repo checkout preferred, bundled fallback)


class SkillConfigError(RuntimeError):
    """Raised when a skill manifest is malformed."""


@dataclass(frozen=True)
class SkillApplicability:
    board_ids: tuple[str, ...]
    mcu_families: tuple[str, ...]
    case_kinds: tuple[str, ...]
    task_terms: tuple[str, ...]


@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    title: str
    applies_to: SkillApplicability
    priority: int
    facts: tuple[str, ...]
    diagnostic_hints: tuple[str, ...]
    verification_checks: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    source_path: Path


def _load_yaml(path: Path) -> dict[str, object]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - guaranteed by repo deps
        raise SkillConfigError(
            f"PyYAML is required to load skill manifests. Missing while reading {path}."
        ) from exc

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SkillConfigError(f"{path} must contain a YAML object.")
    return raw


def _normalize_str_list(value: object | None, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise SkillConfigError(f"{field_name} must be a YAML list.")
    output: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            output.append(text)
    return tuple(output)


def load_skill_manifest(path: Path) -> SkillManifest:
    raw = _load_yaml(path)
    skill_id = str(raw.get("skill_id") or "").strip()
    title = str(raw.get("title") or "").strip()
    priority = raw.get("priority")
    applies_to = raw.get("applies_to")
    if not skill_id or not title:
        raise SkillConfigError(f"{path} must define non-empty skill_id and title.")
    if not isinstance(priority, int):
        raise SkillConfigError(f"{path} must define integer priority.")
    if not isinstance(applies_to, dict):
        raise SkillConfigError(f"{path} must define applies_to as a YAML mapping.")

    return SkillManifest(
        skill_id=skill_id,
        title=title,
        applies_to=SkillApplicability(
            board_ids=_normalize_str_list(
                applies_to.get("board_ids"), field_name="applies_to.board_ids"
            ),
            mcu_families=_normalize_str_list(
                applies_to.get("mcu_families"),
                field_name="applies_to.mcu_families",
            ),
            case_kinds=_normalize_str_list(
                applies_to.get("case_kinds"), field_name="applies_to.case_kinds"
            ),
            task_terms=_normalize_str_list(
                applies_to.get("task_terms"), field_name="applies_to.task_terms"
            ),
        ),
        priority=priority,
        facts=_normalize_str_list(raw.get("facts"), field_name="facts"),
        diagnostic_hints=_normalize_str_list(
            raw.get("diagnostic_hints"),
            field_name="diagnostic_hints",
        ),
        verification_checks=_normalize_str_list(
            raw.get("verification_checks"),
            field_name="verification_checks",
        ),
        forbidden_actions=_normalize_str_list(
            raw.get("forbidden_actions"),
            field_name="forbidden_actions",
        ),
        source_path=path,
    )


def _iter_skill_paths(root: Path) -> tuple[Path, ...]:
    if not root.exists():
        return ()
    return tuple(sorted(path for path in root.rglob("*.yaml") if path.is_file()))


def _matches(skill: SkillManifest, *, board: BoardConfig, task: str, case_kind: str | None) -> bool:
    board_match = not skill.applies_to.board_ids or board.board_id in skill.applies_to.board_ids
    family_match = (
        not skill.applies_to.mcu_families or board.mcu_family in skill.applies_to.mcu_families
    )
    case_match = not skill.applies_to.case_kinds or (
        case_kind is not None and case_kind in skill.applies_to.case_kinds
    )
    lowered_task = task.lower()
    task_match = not skill.applies_to.task_terms or any(
        term.lower() in lowered_task for term in skill.applies_to.task_terms
    )
    return board_match and family_match and case_match and task_match


def load_skills_for_context(
    *,
    board: BoardConfig,
    task: str,
    case_kind: str | None,
    skills_root: Path = SKILLS_ROOT,
) -> tuple[SkillManifest, ...]:
    manifests: dict[str, SkillManifest] = {}
    common_root = skills_root / "common"
    family_root = skills_root / "mcu_families" / board.mcu_family

    for path in (*_iter_skill_paths(common_root), *_iter_skill_paths(family_root)):
        manifest = load_skill_manifest(path)
        if _matches(manifest, board=board, task=task, case_kind=case_kind):
            manifests[manifest.skill_id] = manifest

    return tuple(
        sorted(
            manifests.values(),
            key=lambda item: (item.priority, item.skill_id),
        )
    )


def render_skills(skills: tuple[SkillManifest, ...]) -> str:
    if not skills:
        return "(no matching turnkey skills loaded)"
    chunks: list[str] = []
    for skill in skills:
        lines = [f"- {skill.skill_id}: {skill.title}"]
        for item in skill.facts:
            lines.append(f"  fact: {item}")
        for item in skill.diagnostic_hints:
            lines.append(f"  hint: {item}")
        for item in skill.verification_checks:
            lines.append(f"  verify: {item}")
        for item in skill.forbidden_actions:
            lines.append(f"  avoid: {item}")
        chunks.append("\n".join(lines))
    return "\n".join(chunks)
