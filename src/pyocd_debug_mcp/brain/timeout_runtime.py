"""Branch C runtime timeout orchestration helpers for the turnkey loop."""

from __future__ import annotations

from collections.abc import Mapping

from pyocd_debug_mcp.brain.actions import IterationEstimate, TimeoutProposal, TurnDecision
from pyocd_debug_mcp.brain.config import TurnkeyInvocation
from pyocd_debug_mcp.brain.events import EventKind, EventKinds, EventSink, emit_brain_event
from pyocd_debug_mcp.brain.mcp_client import LocalMCPClient, MCPClientError
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain.timeout_policy import (
    ProposalSource,
    TimeoutPolicyResult,
    apply_policy_proposals,
)
from pyocd_debug_mcp.timeouts import (
    merge_server_timeout_updates,
    server_timeout_update_to_record,
)


def _result_session_id(state: BrainState) -> str | None:
    if state.session_id is not None:
        return state.session_id
    if state.session_ids_seen:
        return state.session_ids_seen[-1]
    return None


async def _record_timeout_event(
    *,
    sink: EventSink | None,
    records: list[dict[str, object]],
    invocation: TurnkeyInvocation,
    state: BrainState,
    event_kind: EventKind,
    message: str,
    details: Mapping[str, object] | None = None,
) -> None:
    event = await emit_brain_event(
        sink,
        event_kind=event_kind,
        board_id=state.board_id,
        iteration=state.iteration,
        session_id=_result_session_id(state),
        provider=invocation.provider,
        model=invocation.model,
        message=message,
        details=dict(details or {}),
    )
    records.append(event.to_record())


async def _record_timeout_policy_events(
    *,
    sink: EventSink | None,
    records: list[dict[str, object]],
    invocation: TurnkeyInvocation,
    state: BrainState,
    proposal_source: ProposalSource,
    timeout_proposal: TimeoutProposal | None,
    iteration_estimate: IterationEstimate | None,
    policy_result: TimeoutPolicyResult,
) -> None:
    if timeout_proposal is not None:
        await _record_timeout_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind=EventKinds.TIMEOUT_PROPOSAL_RECEIVED,
            message=f"Accepted {proposal_source} timeout proposal for evaluation.",
            details=timeout_proposal.model_dump(mode="json"),
        )
    if iteration_estimate is not None:
        await _record_timeout_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind=EventKinds.ITERATION_ESTIMATE_RECEIVED,
            message=f"Accepted {proposal_source} iteration estimate for evaluation.",
            details=iteration_estimate.model_dump(mode="json"),
        )
    if policy_result.accepted_timeout_update is not None:
        await _record_timeout_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind=EventKinds.TIMEOUT_POLICY_APPLIED,
            message=f"Applied {proposal_source} timeout proposal.",
            details=policy_result.to_record(),
        )
        if policy_result.accepted_timeout_update.provider_seconds is not None:
            await _record_timeout_event(
                sink=sink,
                records=records,
                invocation=invocation,
                state=state,
                event_kind=EventKinds.PROVIDER_TIMEOUT_UPDATED,
                message="Updated provider timeout budget for subsequent turns.",
                details={
                    "provider_seconds": policy_result.effective_timeout_config.provider_seconds,
                    "source": proposal_source,
                },
            )
    if policy_result.clamped_timeout_fields:
        await _record_timeout_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind=EventKinds.TIMEOUT_POLICY_CLAMPED,
            message=f"Clamped {proposal_source} timeout proposal inside hard caps.",
            details=policy_result.clamped_timeout_fields,
        )
    if policy_result.rejected_timeout_fields:
        await _record_timeout_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind=EventKinds.TIMEOUT_POLICY_REJECTED,
            message=f"Rejected fields from the {proposal_source} timeout proposal.",
            details=policy_result.rejected_timeout_fields,
        )
    if policy_result.iteration_budget_summary is not None:
        await _record_timeout_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind=EventKinds.ITERATION_BUDGET_APPLIED,
            message=f"Updated effective iteration budget from the {proposal_source} estimate.",
            details=policy_result.iteration_budget_summary.to_record(),
        )


def _apply_timeout_policy_to_state(state: BrainState, policy_result: TimeoutPolicyResult) -> None:
    state.effective_timeout_config = policy_result.effective_timeout_config
    state.effective_max_iters = policy_result.effective_max_iters
    state.last_timeout_policy = policy_result.to_record()
    state.pending_server_timeout_sync = merge_server_timeout_updates(
        state.pending_server_timeout_sync,
        policy_result.server_sync_update,
    )


async def sync_pending_server_timeouts(
    *,
    sink: EventSink | None,
    records: list[dict[str, object]],
    invocation: TurnkeyInvocation,
    state: BrainState,
    client: LocalMCPClient,
    reason: str,
) -> None:
    pending_update = state.pending_server_timeout_sync
    if pending_update is None:
        return
    pending_update_record = server_timeout_update_to_record(pending_update)
    await _record_timeout_event(
        sink=sink,
        records=records,
        invocation=invocation,
        state=state,
        event_kind=EventKinds.TIMEOUT_SYNC_REQUESTED,
        message=f"Syncing staged server timeout defaults ({reason}).",
        details={"pending_update": pending_update_record, "reason": reason},
    )
    result = await client.sync_timeouts(
        pending_update,
        timeout_seconds=state.effective_timeout_config.default_tool_seconds,
    )
    if result.refusal_code or result.blocked_code:
        await _record_timeout_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind=EventKinds.TIMEOUT_SYNC_REJECTED,
            message=result.text,
            details={"pending_update": pending_update_record, "reason": reason},
        )
        raise MCPClientError(result.text)
    state.pending_server_timeout_sync = None
    await _record_timeout_event(
        sink=sink,
        records=records,
        invocation=invocation,
        state=state,
        event_kind=EventKinds.TIMEOUT_SYNC_APPLIED,
        message="Applied staged server timeout defaults for future connects.",
        details={"result_text": result.text, "reason": reason},
    )


async def apply_invocation_timeout_policy(
    *,
    sink: EventSink | None,
    records: list[dict[str, object]],
    invocation: TurnkeyInvocation,
    state: BrainState,
) -> None:
    if invocation.timeout_proposal is None and invocation.iteration_estimate is None:
        return
    policy_result = apply_policy_proposals(
        current_timeout_config=state.effective_timeout_config,
        current_effective_max_iters=state.effective_max_iters,
        operator_max_iters=invocation.max_iters,
        proposal_source="invocation",
        timeout_proposal=invocation.timeout_proposal,
        iteration_estimate=invocation.iteration_estimate,
        connected=False,
    )
    _apply_timeout_policy_to_state(state, policy_result)
    await _record_timeout_policy_events(
        sink=sink,
        records=records,
        invocation=invocation,
        state=state,
        proposal_source="invocation",
        timeout_proposal=invocation.timeout_proposal,
        iteration_estimate=invocation.iteration_estimate,
        policy_result=policy_result,
    )


async def apply_turn_timeout_policy(
    *,
    sink: EventSink | None,
    records: list[dict[str, object]],
    invocation: TurnkeyInvocation,
    state: BrainState,
    client: LocalMCPClient,
    decision: TurnDecision,
) -> None:
    if decision.timeout_proposal is None and decision.iteration_estimate is None:
        return
    connected = state.session_id is not None
    policy_result = apply_policy_proposals(
        current_timeout_config=state.effective_timeout_config,
        current_effective_max_iters=state.effective_max_iters,
        operator_max_iters=invocation.max_iters,
        proposal_source="turn",
        timeout_proposal=decision.timeout_proposal,
        iteration_estimate=decision.iteration_estimate,
        connected=connected,
    )
    _apply_timeout_policy_to_state(state, policy_result)
    await _record_timeout_policy_events(
        sink=sink,
        records=records,
        invocation=invocation,
        state=state,
        proposal_source="turn",
        timeout_proposal=decision.timeout_proposal,
        iteration_estimate=decision.iteration_estimate,
        policy_result=policy_result,
    )
    if policy_result.server_sync_update is None:
        return
    if policy_result.server_sync_apply_now and state.session_id is None:
        await sync_pending_server_timeouts(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            client=client,
            reason="turn-before-connect",
        )
        return
    if state.session_id is not None:
        await _record_timeout_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind=EventKinds.TIMEOUT_SYNC_DEFERRED,
            message="Deferred server timeout sync until the next disconnected state.",
            details={
                "pending_update": server_timeout_update_to_record(
                    state.pending_server_timeout_sync
                ),
            },
        )
