"""Shared future-facing decision/planning types for the R12 brain."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EarlyExitVerdictCode = Literal["infeasible", "needs_intervention", "ambiguous"]
BoardDecisionKind = Literal["board_action", "return"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimeoutProposal(_StrictModel):
    default_tool_seconds: float | None = Field(default=None, gt=0)
    connect_seconds: float | None = Field(default=None, gt=0)
    flash_seconds: float | None = Field(default=None, gt=0)
    recover_seconds: float | None = Field(default=None, gt=0)
    uart_read_seconds: float | None = Field(default=None, gt=0)
    uart_read_grace_seconds: float | None = Field(default=None, gt=0)
    build_seconds: float | None = Field(default=None, gt=0)
    batch_seconds: float | None = Field(default=None, gt=0)
    external_command_seconds: float | None = Field(default=None, gt=0)
    provider_seconds: float | None = Field(default=None, gt=0)
    mcp_startup_seconds: float | None = Field(default=None, gt=0)


class IterationEstimate(_StrictModel):
    board_tool_calls: int | None = Field(default=None, ge=0)
    debug_cycles: int | None = Field(default=None, ge=0)
    false_termination_retries: int | None = Field(default=None, ge=0)
    safety_buffer: int | None = Field(default=None, ge=0)
    requested_max_iterations: int | None = Field(default=None, ge=1)


class EarlyExitVerdict(_StrictModel):
    verdict: EarlyExitVerdictCode
    reason: str = Field(min_length=1)


class ActionCall(_StrictModel):
    action_type: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ActionBatch(_StrictModel):
    calls: tuple[ActionCall, ...] = ()


class BoardDecision(_StrictModel):
    decision_kind: BoardDecisionKind
    action_batch: ActionBatch | None = None
    early_exit: EarlyExitVerdict | None = None
    timeout_proposal: TimeoutProposal | None = None
    iteration_estimate: IterationEstimate | None = None
    return_message: str | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> "BoardDecision":
        if self.decision_kind == "board_action":
            if self.action_batch is None or not self.action_batch.calls:
                raise ValueError("board_action decisions require at least one action call")
            if self.return_message is not None or self.early_exit is not None:
                raise ValueError("board_action decisions cannot carry return-only fields")
        else:
            if self.action_batch is not None:
                raise ValueError("return decisions cannot carry an action batch")
            if self.return_message is None and self.early_exit is None:
                raise ValueError("return decisions require a return_message or early_exit")
        return self
