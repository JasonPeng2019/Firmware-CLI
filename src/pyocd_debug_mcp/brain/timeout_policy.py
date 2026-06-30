"""Brain-owned timeout and iteration policy for Branch C."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.timeouts import (
    ServerTimeoutUpdate,
    TurnkeyTimeoutConfig,
    TurnkeyTimeoutUpdate,
    apply_turnkey_timeout_update,
    clamp_turnkey_timeout_value,
    derive_server_timeout_update,
    server_timeout_update_to_record,
)

ProposalSource = Literal["invocation", "turn"]

DEFAULT_ITERATION_SAFETY_BUFFER = 2
MAX_EFFECTIVE_ITERATIONS = 40

TURNKEY_TIMEOUT_FIELDS = (
    "default_tool_seconds",
    "connect_seconds",
    "flash_seconds",
    "recover_seconds",
    "uart_read_seconds",
    "uart_read_grace_seconds",
    "build_seconds",
    "batch_seconds",
    "external_command_seconds",
    "provider_seconds",
    "mcp_startup_seconds",
)


@dataclass(frozen=True)
class IterationBudgetSummary:
    source: ProposalSource
    operator_max_iters: int
    current_effective_max_iters: int
    requested_max_iterations: int | None
    derived_requested_total: int | None
    effective_max_iters: int
    default_safety_buffer_applied: bool = False
    ignored: bool = False

    def to_record(self) -> dict[str, object]:
        return {
            "source": self.source,
            "operator_max_iters": self.operator_max_iters,
            "current_effective_max_iters": self.current_effective_max_iters,
            "requested_max_iterations": self.requested_max_iterations,
            "derived_requested_total": self.derived_requested_total,
            "effective_max_iters": self.effective_max_iters,
            "default_safety_buffer_applied": self.default_safety_buffer_applied,
            "ignored": self.ignored,
        }


@dataclass(frozen=True)
class TimeoutPolicyResult:
    effective_timeout_config: TurnkeyTimeoutConfig
    effective_max_iters: int
    accepted_timeout_update: TurnkeyTimeoutUpdate | None
    clamped_timeout_fields: dict[str, dict[str, float]]
    rejected_timeout_fields: dict[str, str]
    server_sync_update: ServerTimeoutUpdate | None
    server_sync_apply_now: bool
    iteration_budget_summary: IterationBudgetSummary | None

    def to_record(self) -> dict[str, object]:
        return {
            "effective_timeout_config": self.effective_timeout_config.to_record(),
            "effective_max_iters": self.effective_max_iters,
            "accepted_timeout_update": _update_to_record(self.accepted_timeout_update),
            "clamped_timeout_fields": self.clamped_timeout_fields,
            "rejected_timeout_fields": self.rejected_timeout_fields,
            "server_sync_update": _server_update_to_record(self.server_sync_update),
            "server_sync_apply_now": self.server_sync_apply_now,
            "iteration_budget_summary": self.iteration_budget_summary.to_record()
            if self.iteration_budget_summary is not None
            else None,
        }


def apply_policy_proposals(
    *,
    current_timeout_config: TurnkeyTimeoutConfig,
    current_effective_max_iters: int,
    operator_max_iters: int,
    proposal_source: ProposalSource,
    timeout_proposal: TimeoutProposal | None,
    iteration_estimate: IterationEstimate | None,
    connected: bool,
) -> TimeoutPolicyResult:
    effective_timeout_config = current_timeout_config
    accepted_timeout_update: TurnkeyTimeoutUpdate | None = None
    clamped_timeout_fields: dict[str, dict[str, float]] = {}
    rejected_timeout_fields: dict[str, str] = {}
    server_sync_update: ServerTimeoutUpdate | None = None

    if timeout_proposal is not None:
        accepted_payload: dict[str, float] = {}
        changed_fields: set[str] = set()
        for field_name in TURNKEY_TIMEOUT_FIELDS:
            requested_value = getattr(timeout_proposal, field_name)
            if requested_value is None:
                continue
            applied_value = clamp_turnkey_timeout_value(field_name, requested_value)
            current_value = getattr(current_timeout_config, field_name)
            if applied_value != requested_value:
                clamped_timeout_fields[field_name] = {
                    "requested_seconds": requested_value,
                    "applied_seconds": applied_value,
                }
            if applied_value == current_value:
                continue
            accepted_payload[field_name] = applied_value
            changed_fields.add(field_name)
        if accepted_payload:
            accepted_timeout_update = TurnkeyTimeoutUpdate(**accepted_payload)
            effective_timeout_config = apply_turnkey_timeout_update(
                current_timeout_config,
                accepted_timeout_update,
            )
            server_sync_update = derive_server_timeout_update(
                effective_timeout_config,
                changed_turnkey_fields=changed_fields,
            )

    iteration_budget_summary = _evaluate_iteration_budget(
        current_effective_max_iters=current_effective_max_iters,
        operator_max_iters=operator_max_iters,
        proposal_source=proposal_source,
        iteration_estimate=iteration_estimate,
    )
    effective_max_iters = (
        iteration_budget_summary.effective_max_iters
        if iteration_budget_summary is not None
        else current_effective_max_iters
    )

    return TimeoutPolicyResult(
        effective_timeout_config=effective_timeout_config,
        effective_max_iters=effective_max_iters,
        accepted_timeout_update=accepted_timeout_update,
        clamped_timeout_fields=clamped_timeout_fields,
        rejected_timeout_fields=rejected_timeout_fields,
        server_sync_update=server_sync_update,
        server_sync_apply_now=server_sync_update is not None and not connected,
        iteration_budget_summary=iteration_budget_summary,
    )


def _evaluate_iteration_budget(
    *,
    current_effective_max_iters: int,
    operator_max_iters: int,
    proposal_source: ProposalSource,
    iteration_estimate: IterationEstimate | None,
) -> IterationBudgetSummary | None:
    if iteration_estimate is None:
        return None

    requested_total = iteration_estimate.requested_max_iterations
    default_safety_buffer_applied = False
    if requested_total is None:
        component_values = (
            iteration_estimate.board_tool_calls,
            iteration_estimate.debug_cycles,
            iteration_estimate.false_termination_retries,
        )
        if (
            any(value is not None for value in component_values)
            or iteration_estimate.safety_buffer is not None
        ):
            safety_buffer = iteration_estimate.safety_buffer
            if safety_buffer is None:
                safety_buffer = DEFAULT_ITERATION_SAFETY_BUFFER
                default_safety_buffer_applied = True
            requested_total = (
                (iteration_estimate.board_tool_calls or 0)
                + (iteration_estimate.debug_cycles or 0)
                + (iteration_estimate.false_termination_retries or 0)
                + safety_buffer
            )

    if requested_total is None:
        return IterationBudgetSummary(
            source=proposal_source,
            operator_max_iters=operator_max_iters,
            current_effective_max_iters=current_effective_max_iters,
            requested_max_iterations=iteration_estimate.requested_max_iterations,
            derived_requested_total=None,
            effective_max_iters=current_effective_max_iters,
            default_safety_buffer_applied=default_safety_buffer_applied,
            ignored=True,
        )

    clamped_requested_total = min(max(requested_total, 1), MAX_EFFECTIVE_ITERATIONS)
    effective_max_iters = min(operator_max_iters, clamped_requested_total)
    return IterationBudgetSummary(
        source=proposal_source,
        operator_max_iters=operator_max_iters,
        current_effective_max_iters=current_effective_max_iters,
        requested_max_iterations=iteration_estimate.requested_max_iterations,
        derived_requested_total=requested_total,
        effective_max_iters=effective_max_iters,
        default_safety_buffer_applied=default_safety_buffer_applied,
    )


def _update_to_record(update: TurnkeyTimeoutUpdate | None) -> dict[str, float] | None:
    if update is None:
        return None
    return {
        field_name: value
        for field_name in TURNKEY_TIMEOUT_FIELDS
        if (value := getattr(update, field_name)) is not None
    }


def _server_update_to_record(update: ServerTimeoutUpdate | None) -> dict[str, float] | None:
    return server_timeout_update_to_record(update)
