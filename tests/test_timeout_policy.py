from __future__ import annotations

import json
from pathlib import Path

import anyio

from pyocd_debug_mcp.brain.events import (
    BrainEvent,
    EventKinds,
    fanout_event_sink,
    jsonl_event_sink,
)
from pyocd_debug_mcp.brain.timeout_policy import apply_policy_proposals
from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.timeouts import TurnkeyTimeoutConfig


def test_timeout_policy_clamps_flash_timeout_and_derives_server_sync() -> None:
    result = apply_policy_proposals(
        current_timeout_config=TurnkeyTimeoutConfig(),
        current_effective_max_iters=12,
        operator_max_iters=12,
        proposal_source="invocation",
        timeout_proposal=TimeoutProposal(flash_seconds=1000.0),
        iteration_estimate=None,
        connected=False,
    )

    assert result.effective_timeout_config.flash_seconds == 600.0
    assert result.accepted_timeout_update is not None
    assert result.accepted_timeout_update.flash_seconds == 600.0
    assert result.clamped_timeout_fields["flash_seconds"]["requested_seconds"] == 1000.0
    assert result.server_sync_apply_now is True
    assert result.server_sync_update is not None
    assert result.server_sync_update.flash_erase_all_seconds == 600.0


def test_timeout_policy_derives_iteration_budget_with_default_safety_buffer() -> None:
    result = apply_policy_proposals(
        current_timeout_config=TurnkeyTimeoutConfig(),
        current_effective_max_iters=18,
        operator_max_iters=18,
        proposal_source="turn",
        timeout_proposal=None,
        iteration_estimate=IterationEstimate(
            board_tool_calls=3,
            debug_cycles=2,
            false_termination_retries=1,
        ),
        connected=True,
    )

    assert result.iteration_budget_summary is not None
    assert result.iteration_budget_summary.derived_requested_total == 8
    assert result.iteration_budget_summary.default_safety_buffer_applied is True
    assert result.effective_max_iters == 8


def test_timeout_policy_never_raises_iteration_budget_above_operator_limit() -> None:
    result = apply_policy_proposals(
        current_timeout_config=TurnkeyTimeoutConfig(),
        current_effective_max_iters=6,
        operator_max_iters=6,
        proposal_source="turn",
        timeout_proposal=None,
        iteration_estimate=IterationEstimate(requested_max_iterations=25),
        connected=False,
    )

    assert result.effective_max_iters == 6


def test_timeout_policy_defers_server_sync_when_connected() -> None:
    result = apply_policy_proposals(
        current_timeout_config=TurnkeyTimeoutConfig(),
        current_effective_max_iters=12,
        operator_max_iters=12,
        proposal_source="turn",
        timeout_proposal=TimeoutProposal(connect_seconds=75.0),
        iteration_estimate=None,
        connected=True,
    )

    assert result.server_sync_update is not None
    assert result.server_sync_apply_now is False
    assert result.server_sync_update.reset_halt_seconds == 2.5


def test_jsonl_event_sink_writes_json_safe_records(tmp_path: Path) -> None:
    sink = jsonl_event_sink(tmp_path / "events.jsonl")
    event = BrainEvent(
        event_kind=EventKinds.TOOL_COMPLETE,
        timestamp="2026-06-26T00:00:00Z",
        board_id="nrf52833dk",
        iteration=2,
        session_id="sess-1",
        provider="codex-cli",
        model=None,
        message="done",
        details={"path": tmp_path / "artifact.elf", "values": {1, 2}},
    )

    sink(event)

    record = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").strip())
    assert record["details"]["path"].endswith("artifact.elf")
    assert sorted(record["details"]["values"]) == ["1", "2"] or sorted(record["details"]["values"]) == [1, 2]


def test_fanout_event_sink_calls_all_sinks() -> None:
    received_a: list[str] = []
    received_b: list[str] = []

    def sink_a(event: BrainEvent) -> None:
        received_a.append(event.event_kind)

    async def sink_b(event: BrainEvent) -> None:
        received_b.append(event.message)

    sink = fanout_event_sink(sink_a, sink_b)
    assert sink is not None

    anyio.run(
        lambda: sink(
            BrainEvent(
                event_kind=EventKinds.RUN_START,
                timestamp="2026-06-26T00:00:00Z",
                board_id="nucleo_l476rg",
                iteration=0,
                session_id=None,
                provider="openai-api",
                model="gpt-test",
                message="started",
            )
        )
    )

    assert received_a == [EventKinds.RUN_START]
    assert received_b == ["started"]
