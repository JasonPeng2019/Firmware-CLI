"""Tracked turnkey skill loading and template rendering."""

from __future__ import annotations

from pathlib import Path
from string import Formatter
from typing import Any

import yaml  # type: ignore[import-untyped]

from pyocd_debug_mcp.board_config import BoardConfig
from pyocd_debug_mcp.brain.models import SkillSpec, SkillStep

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SKILLS_ROOT = REPO_ROOT / "skills" / "turnkey"
SUPPORTED_BOARD_KINDS = frozenset({"all", "nordic_only"})
SUPPORTED_FINAL_ASSERTIONS = frozenset({"all_steps_succeeded"})
SUPPORTED_WORKFLOW_KINDS = frozenset(
    {
        "static_mcp_sequence",
        "reference_contract_diagnose",
        "reference_contract_repair",
    }
)


class SkillConfigError(Exception):
    """Raised when a tracked turnkey skill file is malformed."""


def _normalize_string_list(raw: object, *, field_name: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise SkillConfigError(f"Field '{field_name}' must be a YAML list")
    output: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            output.append(text)
    return tuple(output)


def _require_mapping(raw: object, *, field_name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SkillConfigError(f"Field '{field_name}' must be a YAML mapping/object")
    return dict(raw)


def _load_skill_step(raw: object, *, index: int) -> SkillStep:
    data = _require_mapping(raw, field_name=f"steps[{index}]")
    step_id = str(data.get("step_id", "")).strip()
    tool = str(data.get("tool", "")).strip()
    if not step_id:
        raise SkillConfigError(f"steps[{index}] is missing required field 'step_id'")
    if not tool:
        raise SkillConfigError(f"steps[{index}] is missing required field 'tool'")
    arguments = _require_mapping(data.get("arguments", {}), field_name=f"steps[{index}].arguments")
    timeout_value = data.get("timeout_seconds")
    if timeout_value is None:
        raise SkillConfigError(f"steps[{index}] is missing required field 'timeout_seconds'")
    timeout_seconds = float(timeout_value)
    if timeout_seconds <= 0:
        raise SkillConfigError(f"steps[{index}].timeout_seconds must be > 0")
    expected_substrings = _normalize_string_list(
        data.get("expected_substrings"),
        field_name=f"steps[{index}].expected_substrings",
    )
    return SkillStep(
        step_id=step_id,
        tool=tool,
        arguments=arguments,
        timeout_seconds=timeout_seconds,
        expected_substrings=expected_substrings,
    )


def _load_skill_spec(path: Path) -> SkillSpec:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SkillConfigError(f"Failed to parse {path}: {exc}") from exc
    data = _require_mapping(raw, field_name=path.name)
    skill_id = str(data.get("skill_id", "")).strip()
    title = str(data.get("title", "")).strip()
    if not skill_id:
        raise SkillConfigError(f"{path.name} is missing required field 'skill_id'")
    if not title:
        raise SkillConfigError(f"{path.name} is missing required field 'title'")

    supported_kinds = _normalize_string_list(data.get("supported_kinds"), field_name="supported_kinds")
    if not supported_kinds:
        raise SkillConfigError(f"{path.name} must define at least one supported_kinds entry")
    unsupported = sorted(set(supported_kinds) - SUPPORTED_BOARD_KINDS)
    if unsupported:
        raise SkillConfigError(
            f"{path.name} uses unsupported supported_kinds values: {', '.join(unsupported)}"
        )

    workflow_kind = str(data.get("workflow_kind") or "static_mcp_sequence").strip()
    if workflow_kind not in SUPPORTED_WORKFLOW_KINDS:
        raise SkillConfigError(
            f"{path.name} uses unsupported workflow_kind '{workflow_kind}'. "
            f"Supported values: {', '.join(sorted(SUPPORTED_WORKFLOW_KINDS))}"
        )

    raw_steps = data.get("steps")
    if raw_steps is None:
        raw_steps = []
    if not isinstance(raw_steps, list):
        raise SkillConfigError(f"{path.name} field 'steps' must be a YAML list")
    if workflow_kind == "static_mcp_sequence" and not raw_steps:
        raise SkillConfigError(f"{path.name} must define a non-empty 'steps' list")
    steps = tuple(_load_skill_step(step, index=index) for index, step in enumerate(raw_steps))

    final_assertions = _normalize_string_list(
        data.get("final_assertions"),
        field_name="final_assertions",
    )
    unsupported_assertions = sorted(set(final_assertions) - SUPPORTED_FINAL_ASSERTIONS)
    if unsupported_assertions:
        raise SkillConfigError(
            f"{path.name} uses unsupported final_assertions values: "
            f"{', '.join(unsupported_assertions)}"
        )

    return SkillSpec(
        skill_id=skill_id,
        title=title,
        supported_kinds=supported_kinds,
        workflow_kind=workflow_kind,
        steps=steps,
        final_assertions=final_assertions,
        requires_workspace=bool(data.get("requires_workspace", False)),
        source_path=path.resolve(),
    )


def load_skill_specs(skills_root: Path = DEFAULT_SKILLS_ROOT) -> tuple[SkillSpec, ...]:
    root = skills_root.expanduser().resolve()
    if not root.exists():
        raise SkillConfigError(f"Turnkey skills directory does not exist: {root}")
    if not root.is_dir():
        raise SkillConfigError(f"Turnkey skills path is not a directory: {root}")

    skills: list[SkillSpec] = []
    for path in sorted(root.glob("*.yaml")):
        skills.append(_load_skill_spec(path))
    if not skills:
        raise SkillConfigError(f"No turnkey skill files found in: {root}")
    return tuple(skills)


def board_kind(board: BoardConfig) -> str:
    if board.mcu_family.startswith("nrf"):
        return "nordic"
    return "generic"


def skill_supports_board(skill: SkillSpec, board: BoardConfig) -> bool:
    if "all" in skill.supported_kinds:
        return True
    if "nordic_only" in skill.supported_kinds and board_kind(board) == "nordic":
        return True
    return False


def select_skill(
    skill_id: str,
    board: BoardConfig,
    *,
    skills_root: Path = DEFAULT_SKILLS_ROOT,
) -> SkillSpec:
    for skill in load_skill_specs(skills_root):
        if skill.skill_id != skill_id:
            continue
        if not skill_supports_board(skill, board):
            raise SkillConfigError(
                f"Skill '{skill_id}' is not supported for board '{board.board_id}'"
            )
        return skill
    raise SkillConfigError(f"Unknown turnkey skill: {skill_id}")


class _StrictFormatMap(dict[str, Any]):
    def __missing__(self, key: str) -> Any:  # pragma: no cover - defensive, exercised through renderer
        raise SkillConfigError(f"Unknown template field '{key}' in skill arguments")


def _render_string(template: str, values: dict[str, Any]) -> str:
    formatter = Formatter()
    try:
        fields = [field_name for _, field_name, _, _ in formatter.parse(template) if field_name]
    except ValueError as exc:
        raise SkillConfigError(f"Invalid format string '{template}': {exc}") from exc

    if not fields:
        return template
    return template.format_map(_StrictFormatMap(values))


def render_template(value: Any, template_values: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _render_string(value, template_values)
    if isinstance(value, dict):
        return {
            str(key): render_template(inner, template_values)
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [render_template(item, template_values) for item in value]
    return value
