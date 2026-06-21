from __future__ import annotations

import json
from collections import deque
from dataclasses import replace
from pathlib import Path

import anyio
import pytest

from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.actions import (
    FinalizeAction,
    ServerToolAction,
    TurnDecision,
    VerificationSnapshot,
)
from pyocd_debug_mcp.brain.config import BrainConfigError, build_turnkey_invocation, load_provider_config
from pyocd_debug_mcp.brain.loop import TurnkeyExecution, run_turnkey
from pyocd_debug_mcp.brain.mcp_client import ToolTextResult
from pyocd_debug_mcp.brain.skills import load_skills_for_context
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain.workspace import prepare_workspace_session
from tests.harness import r11_benchmark as r11


class FakeProvider:
    def __init__(self, decisions: list[TurnDecision]) -> None:
        self._decisions = deque(decisions)

    async def next_decision(self, *, instructions: str, turn_prompt: str) -> object:
        decision = self._decisions.popleft()
        return type(
            "ProviderTurn",
            (),
            {
                "decision": decision,
                "output_text": json.dumps(decision.model_dump(mode="json")),
                "response_id": "resp-test",
            },
        )()


class FakeClient:
    def __init__(self, results: dict[str, list[ToolTextResult]]) -> None:
        self._results = {name: deque(items) for name, items in results.items()}

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, object] | None = None) -> ToolTextResult:
        queue = self._results.get(tool_name)
        if not queue:
            raise RuntimeError(f"Unexpected tool call: {tool_name}")
        return queue.popleft()


def test_load_provider_config_requires_api_key_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PYOCD_TURNKEY_MODEL", raising=False)

    with pytest.raises(BrainConfigError):
        load_provider_config(None)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(BrainConfigError):
        load_provider_config(None)

    monkeypatch.setenv("PYOCD_TURNKEY_MODEL", "gpt-test")
    config = load_provider_config(None)
    assert config.api_key == "test-key"
    assert config.model == "gpt-test"


def test_skill_loader_selects_common_and_family_skills_deterministically() -> None:
    board = r11._load_board("nrf52833dk")

    skills = load_skills_for_context(
        board=board,
        task="Fix the missing boot ok UART output on the Nordic board and avoid unjustified recover.",
        case_kind="injected_bug",
    )

    skill_ids = [skill.skill_id for skill in skills]
    assert skill_ids == [
        "common.uart_mismatch_triage",
        "common.application_silent_uart",
        "nrf52833.recover_policy",
    ]
    assert "common.uart_mismatch_triage" in skill_ids
    assert "common.application_silent_uart" in skill_ids
    assert "nrf52833.recover_policy" in skill_ids


def test_prepare_workspace_session_tracks_diff_without_copy(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "src").mkdir(parents=True)
    source = workspace_root / "src" / "main.c"
    source.write_text("before\n", encoding="utf-8")

    session = prepare_workspace_session(
        workspace_root=workspace_root,
        allowed_edit_roots=("src",),
        build_command="./build.sh",
        code_edits_allowed=True,
        label="unit",
    )
    session.replace_file("src/main.c", "after\n")
    diff_path = tmp_path / "diff.patch"
    session.write_diff(diff_path)

    assert session.changed_files() == ("src/main.c",)
    assert "a/src/main.c" in diff_path.read_text(encoding="utf-8")
    assert "b/src/main.c" in diff_path.read_text(encoding="utf-8")


def test_run_turnkey_writes_run_artifacts_and_uses_structured_session_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    invocation = build_turnkey_invocation(
        mode="freeform",
        board_id="nrf52833dk",
        task="Verify this reference firmware is healthy and explain why.",
        model="gpt-test",
        max_iters=4,
        serial_read_seconds=1.0,
    )
    provider = FakeProvider(
        [
            TurnDecision(
                observation_summary="Need to connect first.",
                classification="healthy",
                action=ServerToolAction(tool_name="connect", arguments={}),
            ),
            TurnDecision(
                observation_summary="The board is connected and UART should be checked.",
                classification="healthy",
                action=ServerToolAction(tool_name="read_serial", arguments={"reset_on_open": True}),
            ),
            TurnDecision(
                observation_summary="The board looks healthy.",
                classification="healthy",
                action=FinalizeAction(
                    final_status="healthy_confirmed",
                    classification="healthy",
                    root_cause="The tracked reference firmware is behaving as expected.",
                    summary="Healthy baseline confirmed.",
                ),
            ),
        ]
    )
    client_factory = lambda: FakeClient(  # noqa: E731
        {
            "connect": [
                ToolTextResult(
                    tool_name="connect",
                    text="Connected to board 'nRF52833 DK' via probe 685400693 via pyocd-native. [board config: nrf52833dk] session_id=20260620T000000Z-deadbeef",
                )
            ],
            "read_serial": [
                ToolTextResult(
                    tool_name="read_serial",
                    text="UART matched on /dev/cu.usbmodem0006854006931 at 115200 baud via pyocd-native; expected='boot ok'; reopen_count=0; duration=1.00s; excerpt=boot ok",
                )
            ],
            "disconnect": [ToolTextResult(tool_name="disconnect", text="Disconnected.")],
        }
    )

    execution = anyio.run(
        lambda: run_turnkey(invocation, provider=provider, client_factory=client_factory)
    )

    assert execution.result.final_status == "healthy_confirmed"
    assert execution.result.session_id == "20260620T000000Z-deadbeef"
    assert execution.run_root == (tmp_path / "runs" / "20260620T000000Z-deadbeef")
    assert (execution.run_root / "run-metadata" / "turnkey_request.json").exists()
    assert (execution.run_root / "run-metadata" / "turnkey_result.json").exists()
    assert (execution.run_root / "run-metadata" / "turnkey_state.json").exists()
    assert (execution.run_root / "logs" / "brain_trace.jsonl").exists()
    assert (execution.run_root / "logs" / "model_turns.jsonl").exists()


def test_r12_benchmark_records_case_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = r11.load_case("nrf52833dk__k001_reference_green")
    board = r11._load_board(case.board_id)
    prepared = r11.PreparedCase(
        case=case,
        board=board,
        workspace=r11.PreparedWorkspace(
            source_root=tmp_path / "source",
            workspace_root=tmp_path / "workspace",
            snapshot_root=tmp_path / "snapshot",
        ),
        probe_uid="probe-123",
        flash_artifact=tmp_path / "workspace" / "firmware.hex",
        symbol_artifact=tmp_path / "workspace" / "firmware.elf",
    )
    prepared.workspace.source_root.mkdir(parents=True)
    prepared.workspace.workspace_root.mkdir(parents=True)
    prepared.workspace.snapshot_root.mkdir(parents=True)
    prepared.flash_artifact.write_text("hex", encoding="utf-8")
    prepared.symbol_artifact.write_text("elf", encoding="utf-8")
    run_root = tmp_path / "runs" / "20260620T000000Z-test"
    (run_root / "logs").mkdir(parents=True)
    (run_root / "run-metadata").mkdir(parents=True)

    monkeypatch.setattr(r12_benchmark.r11, "_prepare_case", lambda _case: prepared)
    monkeypatch.setattr(r12_benchmark.r11, "_prepare_target_state", lambda _prepared: None)
    monkeypatch.setattr(
        r12_benchmark.r11,
        "_run_final_verification",
        lambda _prepared: r11.VerificationSummary(
            flash_ok=True,
            uart_ok=True,
            symbol_ok=True,
            green_check_ok=True,
            excerpt="boot ok",
            error_text=None,
        ),
    )
    monkeypatch.setattr(
        r12_benchmark.r11,
        "_changed_files",
        lambda _before, _after: (),
    )
    monkeypatch.setattr(
        r12_benchmark,
        "load_provider_config",
        lambda _model: type("Cfg", (), {"api_key": "key", "model": "gpt-test"})(),
    )
    async def fake_run_turnkey_with_openai(_invocation: object, *, api_key: str) -> TurnkeyExecution:
        return TurnkeyExecution(
            invocation=replace(
                build_turnkey_invocation(
                    mode="benchmark",
                    board_id=case.board_id,
                    task="task",
                    model="gpt-test",
                    max_iters=4,
                    serial_read_seconds=1.0,
                ),
                case_id=case.case_id,
            ),
            board=board,
            result=r12_benchmark.TurnkeyRunResult(
                case_id=case.case_id,
                board_id=case.board_id,
                session_id=run_root.name,
                final_status="healthy_confirmed",
                classification="healthy",
                root_cause="No issue found.",
                actions_taken=["connect", "flash_firmware", "read_serial"],
                mcp_tools_used=["connect", "flash_firmware", "read_serial"],
                files_changed=["src/src/main.c"],
                recover_used=False,
                verification=VerificationSnapshot(
                    flash_ok=True,
                    uart_ok=True,
                    symbol_ok=True,
                    green_check_ok=True,
                ),
                summary="Healthy baseline confirmed.",
            ),
            state=BrainState(
                run_mode="benchmark",
                board_id=case.board_id,
                task="task",
                case_id=case.case_id,
                case_kind=case.kind,
                selected_skill_ids=(),
                session_id=run_root.name,
                session_ids_seen=[run_root.name],
            ),
            run_root=run_root,
            prompt_text="prompt",
            request_payload={"board_id": case.board_id},
            selected_skills=(),
            model_turns=(),
            brain_trace=(),
        )

    monkeypatch.setattr(r12_benchmark, "run_turnkey_with_openai", fake_run_turnkey_with_openai)

    report = anyio.run(lambda: r12_benchmark.run_case_async(case.case_id, model="gpt-test"))

    assert report.score_report.score == 100
    assert (run_root / "run-metadata" / "benchmark_case.json").exists()
    assert (run_root / "run-metadata" / "benchmark_result.json").exists()
    assert (run_root / "run-metadata" / "score.json").exists()
    assert (run_root / "run-metadata" / "firmware_identity.json").exists()
