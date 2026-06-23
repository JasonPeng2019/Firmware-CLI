from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import anyio

from pyocd_debug_mcp.brain.actions import FinalizeAction, TurnDecision
from pyocd_debug_mcp.brain.config import build_turnkey_invocation
from pyocd_debug_mcp.brain.evidence import Experiment, Hypothesis, Observation, StrategyEvaluation
from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.loop import run_turnkey
from pyocd_debug_mcp.brain.mcp_client import ToolTextResult, default_server_command
from pyocd_debug_mcp.brain.provider_claude_cli import ClaudeCLIDecisionProvider
from pyocd_debug_mcp.brain.provider_codex_cli import CodexCLIDecisionProvider
from pyocd_debug_mcp.brain.provider_types import ProviderTurn
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain import loop as loop_mod
from pyocd_debug_mcp.brain import workspace as workspace_mod
from tests.harness import r11_benchmark as r11


class _FakeProvider:
    def __init__(self, decisions: list[TurnDecision]) -> None:
        self._decisions = deque(decisions)

    async def next_decision(self, *, instructions: str, turn_prompt: str) -> ProviderTurn:
        decision = self._decisions.popleft()
        return ProviderTurn(
            decision=decision,
            output_text=json.dumps(decision.model_dump(mode="json")),
            response_id="resp-merge-test",
        )


class _FakeClient:
    def __init__(self, results: dict[str, list[ToolTextResult]]) -> None:
        self._results = {name: deque(items) for name, items in results.items()}

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, object] | None = None) -> ToolTextResult:
        queue = self._results.get(tool_name)
        if not queue:
            raise RuntimeError(f"Unexpected tool call: {tool_name}")
        return queue.popleft()


def test_default_server_command_uses_uv_run_repo_entrypoint() -> None:
    command = default_server_command()
    assert command.command == "uv"
    assert command.args == ("run", "pyocd-debug-mcp")
    assert command.cwd is not None


def test_run_local_command_uses_windows_shell_on_windows(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        captured["args"] = args
        captured["cwd"] = kwargs.get("cwd")
        captured["encoding"] = kwargs.get("encoding")
        captured["errors"] = kwargs.get("errors")
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(workspace_mod.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(workspace_mod.subprocess, "run", fake_run)

    result = workspace_mod._run_local_command("echo hello", cwd=tmp_path, timeout_seconds=5.0)

    assert captured["args"] == ["cmd.exe", "/d", "/s", "/c", "echo hello"]
    assert captured["cwd"] == tmp_path
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert result.exit_code == 0
    assert result.stdout == "ok\n"


def test_brain_state_to_record_includes_typed_evidence() -> None:
    state = BrainState(
        run_mode="freeform",
        board_id="nrf52840dk",
        task="verify",
        case_id=None,
        case_kind=None,
        selected_skill_ids=("common.baseline_verification",),
        observations=[Observation("obs-001", "turn", "saw healthy UART", "UART matched")],
        hypotheses=[Hypothesis("hyp-001", "firmware is healthy", "open", ("obs-001",))],
        experiments=[Experiment("exp-001", "run green check", "run_green_check()", "passed")],
        strategy_evaluations=[StrategyEvaluation("strat-001", "keep verifying", "finalize")],
    )

    record = state.to_record()

    assert record["observations"] == [
        {
            "observation_id": "obs-001",
            "source": "turn",
            "summary": "saw healthy UART",
            "evidence_excerpt": "UART matched",
        }
    ]
    assert record["hypotheses"][0]["summary"] == "firmware is healthy"
    assert record["experiments"][0]["purpose"] == "run green check"
    assert record["strategy_evaluations"][0]["next_action"] == "finalize"


def test_execute_read_file_returns_file_contents(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "src").mkdir(parents=True)
    (workspace_root / "src" / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    session = workspace_mod.prepare_workspace_session(
        workspace_root=workspace_root,
        allowed_edit_roots=("src",),
        build_command=None,
        code_edits_allowed=False,
        label="read-file",
    )
    state = BrainState(
        run_mode="freeform",
        board_id="nrf52840dk",
        task="inspect",
        case_id=None,
        case_kind=None,
        selected_skill_ids=(),
    )

    result = loop_mod._execute_read_file(session, "src/main.c", state)

    assert "Contents of src/main.c:" in result
    assert "int main(void) { return 0; }" in result


def test_run_turnkey_records_decision_evidence_and_timeout_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(loop_mod, "RUNS_ROOT", tmp_path / "runs")

    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nrf52840dk",
        task="Verify this reference firmware is healthy and explain why.",
        model=None,
        max_iters=2,
        serial_read_seconds=3.0,
        code_edits_allowed=False,
        allowed_edit_roots=(),
        recover_allowed=True,
    )
    provider = _FakeProvider(
        [
            TurnDecision(
                observation_summary="Need to connect and inspect the board state first.",
                classification="healthy",
                hypothesis="The board is probably already healthy.",
                strategy_evaluation="Connect first so the next decision uses real board evidence.",
                action={"kind": "server_tool", "tool_name": "connect", "arguments": {"board_id": "nrf52840dk"}},
            ),
            TurnDecision(
                observation_summary="The board connected cleanly, so the run can stop after diagnosis.",
                classification="healthy",
                hypothesis="No repair is needed.",
                strategy_evaluation="Stop now because the task was verify-only and the session is healthy.",
                action=FinalizeAction(
                    final_status="diagnosed_only",
                    classification="healthy",
                    root_cause="the board connected cleanly during the verify-only smoke test",
                    summary="diagnosis complete",
                ),
            ),
        ]
    )

    def client_factory() -> _FakeClient:
        return _FakeClient(
            {
                "connect": [
                    ToolTextResult(
                        tool_name="connect",
                        text="Connected to board [board config: nrf52840dk] via pyocd-native via probe 123 session_id=20260622T000000",
                    )
                ],
                "disconnect": [ToolTextResult(tool_name="disconnect", text="Disconnected.")],
            }
        )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=client_factory,
        )
    )

    assert execution.result.final_status == "diagnosed_only"
    assert [item.summary for item in execution.state.observations] == [
        "Need to connect and inspect the board state first.",
        "The board connected cleanly, so the run can stop after diagnosis.",
    ]
    assert [item.summary for item in execution.state.hypotheses] == [
        "The board is probably already healthy.",
        "No repair is needed.",
    ]
    assert execution.state.strategy_evaluations[0].next_action == "server_tool"
    assert (execution.run_root / "run-metadata" / "turnkey_state.json").exists()


def _case_report(case_id: str, *, score: int = 100, outcome: str = "full_success") -> r11.CaseRunReport:
    return r11.CaseRunReport(
        case_id=case_id,
        board_id=case_id.split("__", 1)[0],
        session_id="session-1",
        final_status="fixed",
        score_report=r11.ScoreReport(
            score=score,
            outcome_label=outcome,
            diagnosis_points=25,
            intervention_points=25,
            verification_points=25,
            safety_points=25,
            penalties=(),
            reasons=(),
            actual_changed_files=(),
            classification_correct=True,
            intervention_correct=True,
        ),
        verification=r11.VerificationSummary(
            flash_ok=True,
            uart_ok=True,
            symbol_ok=True,
            green_check_ok=True,
            excerpt="ok",
            error_text=None,
        ),
        run_root=None,
    )


def test_suite_acceptance_supports_alternate_nrf52840_suite() -> None:
    reports = [
        _case_report("nrf52840dk__k001_reference_green"),
        _case_report("nrf52840dk__b001_wrong_boot_text"),
        _case_report("nrf52840dk__b002_wrong_known_value"),
        _case_report("nrf52840dk__f001_halted_target_silent_uart"),
        _case_report("nrf52840dk__b003_silent_uart"),
        _case_report("nrf52840dk__b004_dual_signal_regression"),
    ]

    assert r12_benchmark._suite_acceptance("nrf52840dk_v1_plus_b003_b004", reports) is True


def test_codex_cli_provider_uses_utf8_subprocess_capture(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    output_dir = tmp_path / "codex-provider"
    output_dir.mkdir(parents=True, exist_ok=True)

    class _TempDir:
        def __enter__(self) -> str:
            return str(output_dir)

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    def fake_run(command: list[str], **kwargs: object) -> object:
        captured["encoding"] = kwargs.get("encoding")
        captured["errors"] = kwargs.get("errors")
        (output_dir / "turn_decision.json").write_text(
            json.dumps(
                {
                    "observation_summary": "connected",
                    "classification": "healthy",
                    "action": {
                        "kind": "finalize",
                        "final_status": "diagnosed_only",
                        "classification": "healthy",
                        "root_cause": "none",
                        "summary": "ok",
                    },
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_codex_cli.tempfile.TemporaryDirectory", lambda prefix: _TempDir())
    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_codex_cli.subprocess.run", fake_run)

    provider = CodexCLIDecisionProvider(model=None)
    turn = provider._next_decision_sync("sys", "prompt")

    assert turn.decision.classification == "healthy"
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"


def test_claude_cli_provider_uses_utf8_subprocess_capture(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class _TempDir:
        def __enter__(self) -> str:
            return "."

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    def fake_run(command: list[str], **kwargs: object) -> object:
        captured["encoding"] = kwargs.get("encoding")
        captured["errors"] = kwargs.get("errors")
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "result": json.dumps(
                        {
                            "observation_summary": "connected",
                            "classification": "healthy",
                            "action": {
                                "kind": "finalize",
                                "final_status": "diagnosed_only",
                                "classification": "healthy",
                                "root_cause": "none",
                                "summary": "ok",
                            },
                        }
                    ),
                    "is_error": False,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_claude_cli.tempfile.TemporaryDirectory", lambda prefix: _TempDir())
    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_claude_cli.subprocess.run", fake_run)

    provider = ClaudeCLIDecisionProvider(model=None)
    turn = provider._next_decision_sync("sys", "prompt")

    assert turn.decision.classification == "healthy"
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
