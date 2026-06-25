"""Deterministic internal turnkey playbook loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from pyocd_debug_mcp.board_config import BoardConfig
from pyocd_debug_mcp.runtime_resources import resolve_turnkey_playbooks_root

PLAYBOOKS_ROOT = resolve_turnkey_playbooks_root()
SUPPORTED_BOARD_KINDS = frozenset({"all", "nordic_only"})
SUPPORTED_WORKFLOW_KINDS = frozenset(
    {
        "static_mcp_sequence",
        "reference_contract_diagnose",
        "reference_contract_repair",
    }
)


class PlaybookConfigError(RuntimeError):
    """Raised when an internal turnkey playbook is malformed."""


@dataclass(frozen=True)
class PlaybookStep:
    """One deterministic step in an internal playbook."""

    step_id: str
    tool: str
    arguments: dict[str, Any]
    timeout_seconds: float
    expected_substrings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlaybookSpec:
    """Loaded deterministic helper playbook."""

    playbook_id: str
    title: str
    supported_kinds: tuple[str, ...]
    workflow_kind: str
    steps: tuple[PlaybookStep, ...]
    final_assertions: tuple[str, ...]
    requires_workspace: bool
    source_path: Path


def _normalize_string_list(raw: object, *, field_name: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise PlaybookConfigError(f"Field '{field_name}' must be a YAML list")
    output: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            output.append(text)
    return tuple(output)


def _require_mapping(raw: object, *, field_name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PlaybookConfigError(f"Field '{field_name}' must be a YAML mapping/object")
    return dict(raw)


def _load_playbook_step(raw: object, *, index: int) -> PlaybookStep:
    data = _require_mapping(raw, field_name=f"steps[{index}]")
    step_id = str(data.get("step_id", "")).strip()
    tool = str(data.get("tool", "")).strip()
    if not step_id:
        raise PlaybookConfigError(f"steps[{index}] is missing required field 'step_id'")
    if not tool:
        raise PlaybookConfigError(f"steps[{index}] is missing required field 'tool'")
    arguments = _require_mapping(data.get("arguments", {}), field_name=f"steps[{index}].arguments")
    timeout_value = data.get("timeout_seconds")
    if timeout_value is None:
        raise PlaybookConfigError(f"steps[{index}] is missing required field 'timeout_seconds'")
    timeout_seconds = float(timeout_value)
    if timeout_seconds <= 0:
        raise PlaybookConfigError(f"steps[{index}].timeout_seconds must be > 0")
    expected_substrings = _normalize_string_list(
        data.get("expected_substrings"),
        field_name=f"steps[{index}].expected_substrings",
    )
    return PlaybookStep(
        step_id=step_id,
        tool=tool,
        arguments=arguments,
        timeout_seconds=timeout_seconds,
        expected_substrings=expected_substrings,
    )


def load_playbook_manifest(path: Path) -> PlaybookSpec:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PlaybookConfigError(f"Failed to parse {path}: {exc}") from exc
    data = _require_mapping(raw, field_name=path.name)
    playbook_id = str(data.get("skill_id") or data.get("playbook_id") or "").strip()
    title = str(data.get("title", "")).strip()
    if not playbook_id:
        raise PlaybookConfigError(f"{path.name} is missing required field 'skill_id' or 'playbook_id'")
    if not title:
        raise PlaybookConfigError(f"{path.name} is missing required field 'title'")

    supported_kinds = _normalize_string_list(data.get("supported_kinds"), field_name="supported_kinds")
    if not supported_kinds:
        raise PlaybookConfigError(f"{path.name} must define at least one supported_kinds entry")
    unsupported = sorted(set(supported_kinds) - SUPPORTED_BOARD_KINDS)
    if unsupported:
        raise PlaybookConfigError(
            f"{path.name} uses unsupported supported_kinds values: {', '.join(unsupported)}"
        )

    workflow_kind = str(data.get("workflow_kind") or "static_mcp_sequence").strip()
    if workflow_kind not in SUPPORTED_WORKFLOW_KINDS:
        raise PlaybookConfigError(
            f"{path.name} uses unsupported workflow_kind '{workflow_kind}'. "
            f"Supported values: {', '.join(sorted(SUPPORTED_WORKFLOW_KINDS))}"
        )

    raw_steps = data.get("steps")
    if raw_steps is None:
        raw_steps = []
    if not isinstance(raw_steps, list):
        raise PlaybookConfigError(f"{path.name} field 'steps' must be a YAML list")
    steps = tuple(_load_playbook_step(step, index=index) for index, step in enumerate(raw_steps))

    return PlaybookSpec(
        playbook_id=playbook_id,
        title=title,
        supported_kinds=supported_kinds,
        workflow_kind=workflow_kind,
        steps=steps,
        final_assertions=_normalize_string_list(data.get("final_assertions"), field_name="final_assertions"),
        requires_workspace=bool(data.get("requires_workspace", False)),
        source_path=path.resolve(),
    )


def load_playbook_specs(playbooks_root: Path = PLAYBOOKS_ROOT) -> tuple[PlaybookSpec, ...]:
    root = playbooks_root.expanduser().resolve()
    if not root.exists():
        raise PlaybookConfigError(f"Turnkey playbooks directory does not exist: {root}")
    if not root.is_dir():
        raise PlaybookConfigError(f"Turnkey playbooks path is not a directory: {root}")
    playbooks = tuple(load_playbook_manifest(path) for path in sorted(root.glob("*.yaml")))
    if not playbooks:
        raise PlaybookConfigError(f"No turnkey playbook files found in: {root}")
    return playbooks


def playbook_supports_board(playbook: PlaybookSpec, board: BoardConfig) -> bool:
    if "all" in playbook.supported_kinds:
        return True
    if "nordic_only" in playbook.supported_kinds and board.mcu_family.startswith("nrf"):
        return True
    return False


def select_playbook(
    playbook_id: str,
    board: BoardConfig,
    *,
    playbooks_root: Path = PLAYBOOKS_ROOT,
) -> PlaybookSpec:
    for playbook in load_playbook_specs(playbooks_root):
        if playbook.playbook_id != playbook_id:
            continue
        if not playbook_supports_board(playbook, board):
            raise PlaybookConfigError(
                f"Playbook '{playbook_id}' is not supported for board '{board.board_id}'"
            )
        return playbook
    raise PlaybookConfigError(f"Unknown turnkey playbook: {playbook_id}")
