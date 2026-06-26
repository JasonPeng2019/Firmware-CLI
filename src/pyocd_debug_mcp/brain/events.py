"""Structured event contracts for the turnkey brain and operator UX layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import inspect
from pathlib import Path
from typing import Any, Literal, TypeAlias


EventKind = Literal[
    "run_start",
    "provider_turn_start",
    "provider_turn_complete",
    "tool_start",
    "tool_complete",
    "file_read",
    "file_replace",
    "build_start",
    "build_complete",
    "green_check_start",
    "green_check_complete",
    "verification_state_update",
    "session_state",
    "refusal",
    "block",
    "unexpected_failure",
    "final_result",
    "timeout_proposal_received",
    "timeout_policy_applied",
    "timeout_policy_clamped",
    "timeout_policy_rejected",
    "iteration_estimate_received",
    "iteration_budget_applied",
    "timeout_sync_requested",
    "timeout_sync_applied",
    "timeout_sync_deferred",
    "timeout_sync_rejected",
    "provider_timeout_updated",
]


class EventKinds:
    RUN_START: EventKind = "run_start"
    PROVIDER_TURN_START: EventKind = "provider_turn_start"
    PROVIDER_TURN_COMPLETE: EventKind = "provider_turn_complete"
    TOOL_START: EventKind = "tool_start"
    TOOL_COMPLETE: EventKind = "tool_complete"
    FILE_READ: EventKind = "file_read"
    FILE_REPLACE: EventKind = "file_replace"
    BUILD_START: EventKind = "build_start"
    BUILD_COMPLETE: EventKind = "build_complete"
    GREEN_CHECK_START: EventKind = "green_check_start"
    GREEN_CHECK_COMPLETE: EventKind = "green_check_complete"
    VERIFICATION_STATE_UPDATE: EventKind = "verification_state_update"
    SESSION_STATE: EventKind = "session_state"
    REFUSAL: EventKind = "refusal"
    BLOCK: EventKind = "block"
    UNEXPECTED_FAILURE: EventKind = "unexpected_failure"
    FINAL_RESULT: EventKind = "final_result"
    TIMEOUT_PROPOSAL_RECEIVED: EventKind = "timeout_proposal_received"
    TIMEOUT_POLICY_APPLIED: EventKind = "timeout_policy_applied"
    TIMEOUT_POLICY_CLAMPED: EventKind = "timeout_policy_clamped"
    TIMEOUT_POLICY_REJECTED: EventKind = "timeout_policy_rejected"
    ITERATION_ESTIMATE_RECEIVED: EventKind = "iteration_estimate_received"
    ITERATION_BUDGET_APPLIED: EventKind = "iteration_budget_applied"
    TIMEOUT_SYNC_REQUESTED: EventKind = "timeout_sync_requested"
    TIMEOUT_SYNC_APPLIED: EventKind = "timeout_sync_applied"
    TIMEOUT_SYNC_DEFERRED: EventKind = "timeout_sync_deferred"
    TIMEOUT_SYNC_REJECTED: EventKind = "timeout_sync_rejected"
    PROVIDER_TIMEOUT_UPDATED: EventKind = "provider_timeout_updated"

EVENT_KINDS: tuple[EventKind, ...] = (
    EventKinds.RUN_START,
    EventKinds.PROVIDER_TURN_START,
    EventKinds.PROVIDER_TURN_COMPLETE,
    EventKinds.TOOL_START,
    EventKinds.TOOL_COMPLETE,
    EventKinds.FILE_READ,
    EventKinds.FILE_REPLACE,
    EventKinds.BUILD_START,
    EventKinds.BUILD_COMPLETE,
    EventKinds.GREEN_CHECK_START,
    EventKinds.GREEN_CHECK_COMPLETE,
    EventKinds.VERIFICATION_STATE_UPDATE,
    EventKinds.SESSION_STATE,
    EventKinds.REFUSAL,
    EventKinds.BLOCK,
    EventKinds.UNEXPECTED_FAILURE,
    EventKinds.FINAL_RESULT,
    EventKinds.TIMEOUT_PROPOSAL_RECEIVED,
    EventKinds.TIMEOUT_POLICY_APPLIED,
    EventKinds.TIMEOUT_POLICY_CLAMPED,
    EventKinds.TIMEOUT_POLICY_REJECTED,
    EventKinds.ITERATION_ESTIMATE_RECEIVED,
    EventKinds.ITERATION_BUDGET_APPLIED,
    EventKinds.TIMEOUT_SYNC_REQUESTED,
    EventKinds.TIMEOUT_SYNC_APPLIED,
    EventKinds.TIMEOUT_SYNC_DEFERRED,
    EventKinds.TIMEOUT_SYNC_REJECTED,
    EventKinds.PROVIDER_TIMEOUT_UPDATED,
)

STATUS_START_EVENT_KINDS: tuple[EventKind, ...] = (
    EventKinds.PROVIDER_TURN_START,
    EventKinds.TOOL_START,
    EventKinds.BUILD_START,
    EventKinds.GREEN_CHECK_START,
)

STATUS_COMPLETE_EVENT_KINDS: tuple[EventKind, ...] = (
    EventKinds.PROVIDER_TURN_COMPLETE,
    EventKinds.TOOL_COMPLETE,
    EventKinds.BUILD_COMPLETE,
    EventKinds.GREEN_CHECK_COMPLETE,
)


def event_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return str(value)


def jsonable_event_details(details: dict[str, Any] | None) -> dict[str, Any]:
    return cast_event_details(details or {})


def cast_event_details(details: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _jsonable(value) for key, value in details.items()}


@dataclass(frozen=True)
class BrainEvent:
    event_kind: EventKind
    timestamp: str
    board_id: str
    iteration: int | None
    session_id: str | None
    provider: str
    model: str | None
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "event_kind": self.event_kind,
            "timestamp": self.timestamp,
            "board_id": self.board_id,
            "iteration": self.iteration,
            "session_id": self.session_id,
            "provider": self.provider,
            "model": self.model,
            "message": self.message,
            "details": cast_event_details(self.details),
        }


EventSink: TypeAlias = Callable[[BrainEvent], object | Awaitable[object]]


async def emit_event(sink: EventSink | None, event: BrainEvent) -> None:
    if sink is None:
        return
    result = sink(event)
    if inspect.isawaitable(result):
        await result


async def emit_brain_event(
    sink: EventSink | None,
    *,
    event_kind: EventKind,
    board_id: str,
    iteration: int | None,
    session_id: str | None,
    provider: str,
    model: str | None,
    message: str,
    details: dict[str, Any] | None = None,
) -> BrainEvent:
    event = BrainEvent(
        event_kind=event_kind,
        timestamp=event_timestamp(),
        board_id=board_id,
        iteration=iteration,
        session_id=session_id,
        provider=provider,
        model=model,
        message=message,
        details=details or {},
    )
    await emit_event(sink, event)
    return event


def fanout_event_sink(*sinks: EventSink | None) -> EventSink | None:
    active_sinks = tuple(sink for sink in sinks if sink is not None)
    if not active_sinks:
        return None

    async def _fanout(event: BrainEvent) -> None:
        for sink in active_sinks:
            result = sink(event)
            if inspect.isawaitable(result):
                await result

    return _fanout


def jsonl_event_sink(path: Path) -> EventSink:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _sink(event: BrainEvent) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_record(), sort_keys=True))
            handle.write("\n")

    return _sink
