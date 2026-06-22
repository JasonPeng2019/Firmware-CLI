"""Typed models for the turnkey brain."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillStep:
    """One bounded MCP tool call in a static turnkey skill."""

    step_id: str
    tool: str
    arguments: dict[str, Any]
    timeout_seconds: float
    expected_substrings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillSpec:
    """Tracked turnkey skill description loaded from YAML."""

    skill_id: str
    title: str
    supported_kinds: tuple[str, ...]
    workflow_kind: str
    steps: tuple[SkillStep, ...]
    final_assertions: tuple[str, ...]
    requires_workspace: bool
    source_path: Path


@dataclass(frozen=True)
class TurnkeyRunRequest:
    """Inputs for one turnkey run."""

    board_id: str
    skill_id: str
    case_id: str | None = None
    workspace_root: str | None = None
    flash_artifact: str | None = None
    symbol_artifact: str | None = None
    expected_uart_substring: str | None = None
    stage1_symbol_name: str = "stage1_known_value"
    stage1_symbol_value_u32: str = "0x1234ABCD"
    build_command: str | None = None
    initial_post_flash_state: str = "running"


@dataclass(frozen=True)
class ToolCallResponse:
    """Flattened MCP tool result used by the runner."""

    text: str
    is_error: bool


@dataclass(frozen=True)
class StepResult:
    """Observed result for one executed skill step."""

    step_id: str
    tool: str
    arguments: dict[str, Any]
    timeout_seconds: float
    expected_substrings: tuple[str, ...]
    ok: bool
    duration_seconds: float
    output_text: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Observation:
    """Recorded evidence collected during a turnkey run."""

    observation_id: str
    source: str
    summary: str
    evidence_excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Hypothesis:
    """Tracked hypothesis derived from observations."""

    hypothesis_id: str
    summary: str
    status: str
    supporting_observation_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Experiment:
    """One deliberate experiment or intervention in a turnkey run."""

    experiment_id: str
    purpose: str
    action_summary: str
    result: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyEvaluation:
    """A high-level strategy judgment recorded by the turnkey brain."""

    strategy_id: str
    outcome: str
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TurnkeyRunResult:
    """Structured run summary for CLI output and saved artifacts."""

    run_id: str
    board_id: str
    skill_id: str
    case_id: str | None
    final_status: str
    classification: str | None
    root_cause: str | None
    session_id: str | None
    workspace_root: str | None
    reference_source_root: str | None
    flash_artifact: str
    symbol_artifact: str
    steps: tuple[StepResult, ...]
    observations: tuple[Observation, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    experiments: tuple[Experiment, ...] = ()
    strategy_evaluations: tuple[StrategyEvaluation, ...] = ()
    files_changed: tuple[str, ...] = ()
    verification: dict[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    result_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        data["observations"] = [item.to_dict() for item in self.observations]
        data["hypotheses"] = [item.to_dict() for item in self.hypotheses]
        data["experiments"] = [item.to_dict() for item in self.experiments]
        data["strategy_evaluations"] = [item.to_dict() for item in self.strategy_evaluations]
        return data


@dataclass(frozen=True)
class PreparedRunContext:
    """Board/artifact facts used to render skill templates."""

    board_id: str
    board_kind: str
    case_id: str | None
    workspace_root: Path | None
    reference_source_root: Path
    flash_artifact: Path
    symbol_artifact: Path
    expected_uart_substring: str
    build_command: str | None = None
    initial_post_flash_state: str = "running"
    stage1_symbol_name: str = "stage1_known_value"
    stage1_symbol_value_u32: str = "0x1234ABCD"


@dataclass
class MutableRunState:
    """Mutable state container while a turnkey run is in flight."""

    session_id: str | None = None
    final_status: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    experiments: list[Experiment] = field(default_factory=list)
    strategy_evaluations: list[StrategyEvaluation] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    verification: dict[str, bool] = field(default_factory=dict)
    classification: str | None = None
    root_cause: str | None = None
    warnings: list[str] = field(default_factory=list)
