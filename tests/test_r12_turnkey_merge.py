from __future__ import annotations

import json
import subprocess
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import anyio
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData
import pytest

from pyocd_debug_mcp import benchmark_support as r11
from pyocd_debug_mcp.brain.actions import FinalizeAction, ServerToolAction, TurnDecision
from pyocd_debug_mcp.brain import mcp_client as mcp_client_mod
from pyocd_debug_mcp.brain.config import BrainConfigError, build_turnkey_invocation
from pyocd_debug_mcp.brain.evidence import Experiment, Hypothesis, Observation, StrategyEvaluation
from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.loop import run_turnkey
from pyocd_debug_mcp.brain.mcp_client import (
    LocalMCPClient,
    MCPClientError,
    StdioToolClient,
    ToolTextResult,
    default_server_command,
)
from pyocd_debug_mcp.brain.provider_claude_cli import (
    ClaudeCLIDecisionProvider,
    ProviderResponseError as ClaudeProviderResponseError,
)
from pyocd_debug_mcp.brain.provider_codex_cli import (
    CodexCLIDecisionProvider,
    ProviderResponseError as CodexProviderResponseError,
)
from pyocd_debug_mcp.brain.provider_openai import OpenAIDecisionProvider
from pyocd_debug_mcp.brain.provider_anthropic import AnthropicDecisionProvider
from pyocd_debug_mcp.brain.provider_types import (
    ProviderCapabilities,
    ProviderMemoryEntry,
    ProviderMemorySummaryResult,
    ProviderPromptBundle,
    ProviderResumeFailure,
    ProviderResumeFailureRecord,
    ProviderRuntimeContext,
    ProviderSessionState,
    ProviderTurn,
    make_provider_session_state,
    with_provider_resume_recovery_request,
)
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain import loop as loop_mod
from pyocd_debug_mcp.brain import workspace as workspace_mod


def require_run_root(run_root: Path | None) -> Path:
    assert run_root is not None
    return run_root


class _FakeProvider:
    def __init__(self, decisions: list[TurnDecision]) -> None:
        self._decisions = deque(decisions)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_native_session=False,
            supports_transcript_continuation=True,
            supports_response_id_continuation=False,
            supports_tool_schema_prompt=True,
            continuation_mode="local-primary",
        )

    async def next_decision(
        self,
        *,
        prompt_bundle: ProviderPromptBundle,
        session_state: ProviderSessionState,
    ) -> ProviderTurn:
        decision = self._decisions.popleft()
        return ProviderTurn(
            decision=decision,
            output_text=json.dumps(decision.model_dump(mode="json")),
            response_id="resp-merge-test",
            session_state=session_state.with_last_continuation_path(
                "local-memory-only",
                metadata={"continuation_kind": "merge-test-local-memory-only"},
            ),
            provider_metadata={
                "continuation_kind": "merge-test-local-memory-only",
                "continuation_path": "local-memory-only",
                "memory_injected": True,
            },
        )

    async def summarize_memory(
        self,
        *,
        session_state: ProviderSessionState,
        prior_summary_text: str,
        evicted_entries: tuple[ProviderMemoryEntry, ...],
    ) -> ProviderMemorySummaryResult:
        return ProviderMemorySummaryResult(
            summary_text=prior_summary_text or "- merge summary",
            provider_metadata={"provider": "merge-fake"},
        )


class _FakeClient:
    def __init__(self, results: dict[str, list[ToolTextResult]]) -> None:
        self._results = {name: deque(items) for name, items in results.items()}
        self._tool_descriptors = (
            mcp_client_mod.ToolDescriptor(
                name="connect",
                description="Connect to one board.",
                input_schema={"type": "object", "properties": {"board_id": {"type": "string"}}},
            ),
            mcp_client_mod.ToolDescriptor(
                name="disconnect",
                description="Disconnect the active session.",
                input_schema={"type": "object", "properties": {}},
            ),
        )

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def call_tool(
        self, tool_name: str, arguments: dict[str, object] | None = None
    ) -> ToolTextResult:
        queue = self._results.get(tool_name)
        if not queue:
            raise RuntimeError(f"Unexpected tool call: {tool_name}")
        return queue.popleft()

    async def list_tools(self) -> tuple[mcp_client_mod.ToolDescriptor, ...]:
        return self._tool_descriptors


def test_default_server_command_uses_uv_run_repo_entrypoint() -> None:
    command = default_server_command()
    assert command.command == "uv"
    assert command.args == ("run", "pyocd-debug-mcp")
    assert command.cwd is not None


def test_local_mcp_client_start_times_out(monkeypatch) -> None:
    class SlowStartupTransport:
        async def __aenter__(self) -> "SlowStartupTransport":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        async def list_tool_descriptors(self) -> tuple[mcp_client_mod.ToolDescriptor, ...]:
            await anyio.sleep(1.0)
            return (
                mcp_client_mod.ToolDescriptor(
                    name="connect",
                    description="Connect to one board.",
                    input_schema={"type": "object", "properties": {"board_id": {"type": "string"}}},
                ),
            )

        async def call_tool_text(
            self,
            name: str,
            arguments: dict[str, object] | None,
            *,
            timeout_seconds: float | None = None,
        ) -> ToolTextResult:
            return ToolTextResult(tool_name=name, text="ok")

    monkeypatch.setattr(mcp_client_mod, "MCP_STARTUP_TIMEOUT_SECONDS", 0.01)
    client = LocalMCPClient()
    client._transport = SlowStartupTransport()  # type: ignore[assignment]

    with pytest.raises(MCPClientError, match="startup timed out after 0s"):
        anyio.run(client.start)


def test_local_mcp_client_cleans_up_on_non_timeout_start_failure() -> None:
    class FailingStartupTransport:
        def __init__(self) -> None:
            self.exit_calls: list[tuple[object, object, object]] = []

        async def __aenter__(self) -> "FailingStartupTransport":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            self.exit_calls.append((exc_type, exc, tb))
            return None

        async def list_tool_names(self) -> set[str]:
            raise RuntimeError("tool listing failed")

        async def call_tool_text(
            self,
            name: str,
            arguments: dict[str, object] | None,
            *,
            timeout_seconds: float | None = None,
        ) -> ToolTextResult:
            return ToolTextResult(tool_name=name, text="ok")

    transport = FailingStartupTransport()
    client = LocalMCPClient()
    client._transport = transport  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="tool listing failed"):
        anyio.run(client.start)

    assert len(transport.exit_calls) == 1
    assert transport.exit_calls[0][0] is RuntimeError
    assert client.available_tools == ()


def test_stdio_tool_client_cleans_up_when_initialize_fails(monkeypatch) -> None:
    events: list[str] = []

    class FakeStdioManager:
        async def __aenter__(self) -> tuple[object, object]:
            events.append("manager-enter")
            return object(), object()

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            events.append(f"manager-exit:{getattr(exc_type, '__name__', exc_type)}")
            return None

    class FakeSession:
        def __init__(self, read_stream: object, write_stream: object) -> None:
            del read_stream, write_stream

        async def __aenter__(self) -> None:
            events.append("session-enter")
            return None

        async def initialize(self) -> None:
            events.append("session-initialize")
            raise RuntimeError("initialize failed")

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            events.append(f"session-exit:{getattr(exc_type, '__name__', exc_type)}")
            return None

    monkeypatch.setattr(mcp_client_mod, "stdio_client", lambda params: FakeStdioManager())
    monkeypatch.setattr(mcp_client_mod, "ClientSession", FakeSession)

    client = StdioToolClient(default_server_command())

    with pytest.raises(RuntimeError, match="initialize failed"):
        anyio.run(client.__aenter__)

    assert events == [
        "manager-enter",
        "session-enter",
        "session-initialize",
        "session-exit:RuntimeError",
        "manager-exit:RuntimeError",
    ]


def test_stdio_tool_client_suppresses_expected_cleanup_errors() -> None:
    class NoisyCloser:
        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            raise anyio.BrokenResourceError

    client = StdioToolClient(default_server_command())
    client._session = NoisyCloser()  # type: ignore[assignment]
    client._stdio_manager = NoisyCloser()

    anyio.run(lambda: client.__aexit__(None, None, None))

    assert client._session is None
    assert client._stdio_manager is None


def test_stdio_tool_client_maps_mcp_timeout_to_mcp_client_error() -> None:
    class FakeSession:
        async def call_tool(
            self,
            name: str,
            *,
            arguments: dict[str, object] | None,
            read_timeout_seconds: object = None,
        ) -> object:
            del name, arguments, read_timeout_seconds
            raise McpError(
                ErrorData(
                    code=408,
                    message="Timed out while waiting for response to CallToolRequest. Waited 0.01 seconds.",
                )
            )

    client = StdioToolClient(default_server_command())
    client._session = FakeSession()  # type: ignore[assignment]

    with pytest.raises(MCPClientError, match="Tool 'read_serial' timed out after 0s"):
        anyio.run(
            lambda: client.call_tool_text(
                "read_serial", {"read_seconds": 1.0}, timeout_seconds=0.01
            )
        )


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


def test_build_turnkey_invocation_rejects_nonpositive_max_iters() -> None:
    with pytest.raises(BrainConfigError, match="max_iters must be > 0"):
        build_turnkey_invocation(
            mode="freeform",
            provider="codex-cli",
            board_id="nrf52840dk",
            task="verify",
            model=None,
            max_iters=0,
            serial_read_seconds=3.0,
        )


def test_build_turnkey_invocation_rejects_nonpositive_serial_read_seconds() -> None:
    with pytest.raises(BrainConfigError, match="serial_read_seconds must be > 0"):
        build_turnkey_invocation(
            mode="freeform",
            provider="codex-cli",
            board_id="nrf52840dk",
            task="verify",
            model=None,
            max_iters=4,
            serial_read_seconds=0.0,
        )


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

    observations = cast(list[dict[str, object]], record["observations"])
    hypotheses = cast(list[dict[str, object]], record["hypotheses"])
    experiments = cast(list[dict[str, object]], record["experiments"])
    strategy_evaluations = cast(list[dict[str, object]], record["strategy_evaluations"])
    assert record["observations"] == [
        {
            "observation_id": "obs-001",
            "source": "turn",
            "summary": "saw healthy UART",
            "evidence_excerpt": "UART matched",
        }
    ]
    assert observations[0]["summary"] == "saw healthy UART"
    assert hypotheses[0]["summary"] == "firmware is healthy"
    assert experiments[0]["purpose"] == "run green check"
    assert strategy_evaluations[0]["next_action"] == "finalize"


def test_execute_read_file_returns_file_contents(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "src").mkdir(parents=True)
    (workspace_root / "src" / "main.c").write_text(
        "int main(void) { return 0; }\n", encoding="utf-8"
    )
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
                action=ServerToolAction(
                    tool_name="connect",
                    arguments={"board_id": "nrf52840dk"},
                ),
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
            client_factory=cast(Any, client_factory),
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
    assert (require_run_root(execution.run_root) / "run-metadata" / "turnkey_state.json").exists()


def _case_report(
    case_id: str, *, score: int = 100, outcome: str = "full_success"
) -> r11.CaseRunReport:
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
        captured["input"] = kwargs.get("input")
        captured["timeout"] = kwargs.get("timeout")
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

    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.provider_codex_cli.tempfile.TemporaryDirectory",
        lambda prefix: _TempDir(),
    )
    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_codex_cli.subprocess.run", fake_run)

    provider = CodexCLIDecisionProvider(model=None)
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="",
        provider_memory_text="memory block",
        turn_context_text="prompt",
        turn_decision_schema_text="",
    )
    turn = provider._next_decision_sync(
        bundle,
        make_provider_session_state(
            provider="codex-cli",
            model=None,
            continuation_mode="remote-primary",
            runtime_context=ProviderRuntimeContext(
                runtime_root=str(output_dir),
                working_directory=str(output_dir),
            ),
        ),
    )

    assert turn.decision.classification == "healthy"
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["input"] == "sys\n\nmemory block\n\nprompt"
    assert captured["timeout"] == 300.0


def test_openai_provider_uses_previous_response_id_and_updates_session_state(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeResponses:
        def create(self, **kwargs: object) -> object:
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                id="resp-next",
                output_text=json.dumps(
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
            )

    class _FakeOpenAI:
        def __init__(self, *, api_key: str, timeout: float) -> None:
            self.responses = _FakeResponses()

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_openai.OpenAI", _FakeOpenAI)

    provider = OpenAIDecisionProvider(api_key="test-key", model="gpt-test")
    session_state = make_provider_session_state(
        provider="openai-api",
        model="gpt-test",
        continuation_mode="remote-primary",
    ).with_native_handle_update(response_id="resp-prev")
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="prompt",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(bundle, session_state)

    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["previous_response_id"] == "resp-prev"
    assert kwargs["input"] == "prompt"
    assert turn.response_id == "resp-next"
    assert turn.session_state.native_handle is not None
    assert turn.session_state.native_handle.response_id == "resp-next"
    assert turn.provider_metadata["continuation_path"] == "remote-resume"
    assert turn.provider_metadata["prompt_render_mode"] == "remote-delta"
    assert turn.provider_metadata["static_tool_schema_injected"] is False
    assert turn.provider_metadata["decision_schema_injected"] is False
    assert [update.stage for update in turn.progress_updates] == [
        "provider_request",
        "continuation",
    ]
    assert provider.capabilities.supports_native_session is True


def test_openai_provider_previous_response_failure_is_typed_resume_failure(
    monkeypatch,
) -> None:
    class _FakeResponses:
        def create(self, **kwargs: object) -> object:
            del kwargs
            raise RuntimeError("response chain expired")

    class _FakeOpenAI:
        def __init__(self, *, api_key: str, timeout: float) -> None:
            self.responses = _FakeResponses()

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_openai.OpenAI", _FakeOpenAI)

    provider = OpenAIDecisionProvider(api_key="test-key", model="gpt-test")
    session_state = make_provider_session_state(
        provider="openai-api",
        model="gpt-test",
        continuation_mode="remote-primary",
    ).with_native_handle_update(response_id="resp-prev")
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="prompt",
        turn_decision_schema_text="decision schema",
    )

    with pytest.raises(ProviderResumeFailure) as exc_info:
        provider._next_decision_sync(bundle, session_state)

    record = exc_info.value.to_record()
    assert record["provider"] == "openai-api"
    assert record["remote_handle_kind"] == "response_id"
    assert record["expected_handle_id"] == "resp-prev"
    assert record["replacement_provider_session_started"] is False
    assert "response chain expired" in str(record["failure_text"])


def test_openai_provider_retry_updates_prompt_metadata(
    monkeypatch,
) -> None:
    call_inputs: list[dict[str, object]] = []

    class _FakeResponses:
        def __init__(self) -> None:
            self._outputs = iter(
                (
                    "not json",
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
                )
            )

        def create(self, **kwargs: object) -> object:
            call_inputs.append(dict(kwargs))
            return SimpleNamespace(id="resp-retry", output_text=next(self._outputs))

    class _FakeOpenAI:
        def __init__(self, *, api_key: str, timeout: float) -> None:
            self.responses = _FakeResponses()

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_openai.OpenAI", _FakeOpenAI)

    provider = OpenAIDecisionProvider(api_key="test-key", model="gpt-test")
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(
        bundle,
        make_provider_session_state(
            provider="openai-api",
            model="gpt-test",
            continuation_mode="remote-primary",
        ),
    )

    assert len(call_inputs) == 2
    assert (
        call_inputs[0]["input"] == "tool schema\n\nmemory block\n\nturn context\n\ndecision schema"
    )
    assert (
        call_inputs[1]["input"]
        == "turn context\n\ndecision schema\n\nYour previous reply was invalid. Return only one JSON object that matches the schema exactly."
    )
    assert turn.provider_metadata["prompt_render_mode"] == "retry"
    assert turn.provider_metadata["memory_injected"] is False
    assert turn.provider_metadata["static_tool_schema_injected"] is False
    assert turn.provider_metadata["decision_schema_injected"] is True
    assert turn.provider_metadata["retry_count"] == 1


def test_codex_cli_provider_surfaces_subprocess_timeout(
    monkeypatch,
) -> None:
    class _TempDir:
        def __enter__(self) -> str:
            return "."

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    def fake_run(command: list[str], **kwargs: object) -> object:
        timeout = kwargs.get("timeout")
        assert isinstance(timeout, (int, float))
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.provider_codex_cli.tempfile.TemporaryDirectory",
        lambda prefix: _TempDir(),
    )
    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_codex_cli.subprocess.run", fake_run)

    provider = CodexCLIDecisionProvider(model=None, timeout_seconds=1.0)
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="",
        provider_memory_text="",
        turn_context_text="prompt",
        turn_decision_schema_text="",
    )

    with pytest.raises(CodexProviderResponseError, match="Codex CLI timed out after 1s"):
        provider._next_decision_sync(
            bundle,
            make_provider_session_state(
                provider="codex-cli", model=None, continuation_mode="local-primary"
            ),
        )


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
        captured["timeout"] = kwargs.get("timeout")
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

    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.provider_claude_cli.tempfile.TemporaryDirectory",
        lambda prefix: _TempDir(),
    )
    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_claude_cli.subprocess.run", fake_run)

    provider = ClaudeCLIDecisionProvider(model=None)
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="",
        provider_memory_text="memory block",
        turn_context_text="prompt",
        turn_decision_schema_text="",
    )
    turn = provider._next_decision_sync(
        bundle,
        make_provider_session_state(
            provider="claude-cli", model=None, continuation_mode="remote-primary"
        ),
    )

    assert turn.decision.classification == "healthy"
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["timeout"] == 300.0


def test_anthropic_provider_uses_local_primary_memory_and_updates_state(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeMessages:
        def create(self, **kwargs: object) -> object:
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                id="anthropic-next",
                content=[
                    SimpleNamespace(
                        type="text",
                        text=json.dumps(
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
                    )
                ],
            )

    class _FakeAnthropic:
        def __init__(self, *, api_key: str, timeout: float) -> None:
            self.messages = _FakeMessages()

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_anthropic.Anthropic", _FakeAnthropic)

    provider = AnthropicDecisionProvider(api_key="anth-key", model="claude-test")
    session_state = make_provider_session_state(
        provider="anthropic-api",
        model="claude-test",
        continuation_mode="local-primary",
    )
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="prompt",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(bundle, session_state)

    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    message_text = kwargs["messages"][0]["content"]  # type: ignore[index]
    assert "memory block" in message_text
    assert turn.response_id == "anthropic-next"
    assert turn.session_state.native_handle is None
    assert turn.provider_metadata["continuation_path"] == "local-memory-only"
    assert turn.provider_metadata["memory_injected"] is True
    assert provider.capabilities.continuation_mode == "local-primary"
    assert provider.capabilities.remote_strategy == "none"


def test_anthropic_provider_retry_updates_prompt_metadata(
    monkeypatch,
) -> None:
    captured_messages: list[str] = []

    class _FakeMessages:
        def __init__(self) -> None:
            self._outputs = iter(
                (
                    "not json",
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
                )
            )

        def create(self, **kwargs: object) -> object:
            captured_messages.append(kwargs["messages"][0]["content"])  # type: ignore[index]
            return SimpleNamespace(
                id="anthropic-retry",
                content=[SimpleNamespace(type="text", text=next(self._outputs))],
            )

    class _FakeAnthropic:
        def __init__(self, *, api_key: str, timeout: float) -> None:
            self.messages = _FakeMessages()

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_anthropic.Anthropic", _FakeAnthropic)

    provider = AnthropicDecisionProvider(api_key="anth-key", model="claude-test")
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(
        bundle,
        make_provider_session_state(
            provider="anthropic-api",
            model="claude-test",
            continuation_mode="local-primary",
        ),
    )

    assert len(captured_messages) == 2
    assert captured_messages[0] == "tool schema\n\nmemory block\n\nturn context\n\ndecision schema"
    assert (
        captured_messages[1]
        == "turn context\n\ndecision schema\n\nYour previous reply was invalid. Return only one JSON object that matches the schema exactly."
    )
    assert turn.provider_metadata["prompt_render_mode"] == "retry"
    assert turn.provider_metadata["memory_injected"] is False
    assert turn.provider_metadata["static_tool_schema_injected"] is False
    assert turn.provider_metadata["decision_schema_injected"] is True
    assert turn.provider_metadata["retry_count"] == 1


def test_claude_cli_provider_surfaces_subprocess_timeout(
    monkeypatch,
) -> None:
    class _TempDir:
        def __enter__(self) -> str:
            return "."

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    def fake_run(command: list[str], **kwargs: object) -> object:
        timeout = kwargs.get("timeout")
        assert isinstance(timeout, (int, float))
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.provider_claude_cli.tempfile.TemporaryDirectory",
        lambda prefix: _TempDir(),
    )
    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_claude_cli.subprocess.run", fake_run)

    provider = ClaudeCLIDecisionProvider(model=None, timeout_seconds=1.0)
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="",
        provider_memory_text="",
        turn_context_text="prompt",
        turn_decision_schema_text="",
    )

    with pytest.raises(ClaudeProviderResponseError, match="Claude CLI timed out after 1s"):
        provider._next_decision_sync(
            bundle,
            make_provider_session_state(
                provider="claude-cli", model=None, continuation_mode="remote-primary"
            ),
        )


def test_codex_cli_provider_reports_memory_injected_only_when_memory_block_exists(
    monkeypatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "codex-provider-empty-memory"
    output_dir.mkdir(parents=True, exist_ok=True)

    class _TempDir:
        def __enter__(self) -> str:
            return str(output_dir)

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    def fake_run(command: list[str], **kwargs: object) -> object:
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

    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.provider_codex_cli.tempfile.TemporaryDirectory",
        lambda prefix: _TempDir(),
    )
    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_codex_cli.subprocess.run", fake_run)

    provider = CodexCLIDecisionProvider(model=None)
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="tool schema",
        provider_memory_text="",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(
        bundle,
        make_provider_session_state(
            provider="codex-cli",
            model=None,
            continuation_mode="remote-primary",
            runtime_context=ProviderRuntimeContext(
                runtime_root=str(output_dir),
                working_directory=str(output_dir),
            ),
        ),
    )

    assert turn.provider_metadata["memory_injected"] is False


def test_claude_cli_provider_resumes_remote_session_and_records_unified_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    working_dir = tmp_path / "claude-resume"
    working_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command: list[str], **kwargs: object) -> object:
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "session_id": "sess-parent",
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

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_claude_cli.subprocess.run", fake_run)

    provider = ClaudeCLIDecisionProvider(model="sonnet")
    session_state = make_provider_session_state(
        provider="claude-cli",
        model="sonnet",
        continuation_mode="remote-primary",
        runtime_context=ProviderRuntimeContext(
            runtime_root=str(working_dir),
            working_directory=str(working_dir),
        ),
    ).with_native_handle_update(native_session_id="sess-parent")
    bundle = ProviderPromptBundle(
        system_instructions="system",
        tool_schema_text="tool schema",
        provider_memory_text="",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(bundle, session_state)

    assert calls
    assert "--resume" in calls[0]
    assert "sess-parent" in calls[0]
    assert "--fork-session" not in calls[0]
    assert turn.provider_metadata["remote_strategy"] == "claude-session-resume"
    assert turn.provider_metadata["remote_handle_kind"] == "session_id"
    assert turn.provider_metadata["remote_handle_id"] == "sess-parent"
    assert turn.provider_metadata["remote_handle_present"] is True
    assert turn.provider_metadata["resumed_remote"] is True
    assert turn.provider_metadata["fresh_remote_turn"] is False
    assert turn.provider_metadata["local_memory_fallback_used"] is False
    assert turn.provider_metadata["prompt_render_mode"] == "remote-delta"
    assert turn.provider_metadata["memory_injected"] is False


def test_claude_cli_provider_fork_retry_commits_child_session_only_on_success(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    outputs = iter(
        (
            json.dumps({"session_id": "sess-parent", "result": "not json", "is_error": False}),
            json.dumps(
                {
                    "session_id": "sess-child",
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
        )
    )
    working_dir = tmp_path / "claude-fork"
    working_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command: list[str], **kwargs: object) -> object:
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=next(outputs), stderr="")

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_claude_cli.subprocess.run", fake_run)

    provider = ClaudeCLIDecisionProvider(model="sonnet")
    session_state = make_provider_session_state(
        provider="claude-cli",
        model="sonnet",
        continuation_mode="remote-primary",
        runtime_context=ProviderRuntimeContext(
            runtime_root=str(working_dir),
            working_directory=str(working_dir),
        ),
    ).with_native_handle_update(native_session_id="sess-parent")
    bundle = ProviderPromptBundle(
        system_instructions="system",
        tool_schema_text="tool schema",
        provider_memory_text="",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(bundle, session_state)

    assert len(calls) == 2
    assert "--resume" in calls[0] and "sess-parent" in calls[0]
    assert "--fork-session" not in calls[0]
    assert "--resume" in calls[1] and "sess-parent" in calls[1]
    assert "--fork-session" in calls[1]
    assert turn.session_state.native_handle is not None
    assert turn.session_state.native_handle.native_session_id == "sess-child"
    assert turn.provider_metadata["continuation_path"] == "remote-fork"
    assert turn.provider_metadata["fork_retry_used"] is True
    assert turn.provider_metadata["remote_handle_id"] == "sess-child"
    assert turn.provider_metadata["resumed_remote"] is True
    assert turn.provider_metadata["fresh_remote_turn"] is False


def test_claude_cli_provider_resume_failure_fails_closed_by_default(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    working_dir = tmp_path / "claude-strict"
    working_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command: list[str], **kwargs: object) -> object:
        del kwargs
        calls.append(command)
        return SimpleNamespace(returncode=1, stdout="", stderr="resume failed")

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_claude_cli.subprocess.run", fake_run)

    provider = ClaudeCLIDecisionProvider(model="sonnet")
    session_state = make_provider_session_state(
        provider="claude-cli",
        model="sonnet",
        continuation_mode="remote-primary",
        runtime_context=ProviderRuntimeContext(
            runtime_root=str(working_dir),
            working_directory=str(working_dir),
        ),
    ).with_native_handle_update(native_session_id="sess-parent")
    bundle = ProviderPromptBundle(
        system_instructions="system",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    with pytest.raises(ProviderResumeFailure) as exc_info:
        provider._next_decision_sync(bundle, session_state)

    assert len(calls) == 1
    assert "--resume" in calls[0] and "sess-parent" in calls[0]
    record = exc_info.value.to_record()
    assert record["provider"] == "claude-cli"
    assert record["remote_handle_kind"] == "session_id"
    assert record["expected_handle_id"] == "sess-parent"
    assert record["replacement_provider_session_started"] is False
    assert "resume failed" in str(record["failure_text"])


def test_claude_cli_provider_explicit_recovery_starts_labeled_fresh_memory_session(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    working_dir = tmp_path / "claude-recovery"
    working_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command: list[str], **kwargs: object) -> object:
        del kwargs
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "session_id": "sess-fresh",
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

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_claude_cli.subprocess.run", fake_run)

    provider = ClaudeCLIDecisionProvider(model="sonnet")
    base_session_state = make_provider_session_state(
        provider="claude-cli",
        model="sonnet",
        continuation_mode="remote-primary",
        runtime_context=ProviderRuntimeContext(
            runtime_root=str(working_dir),
            working_directory=str(working_dir),
        ),
    ).with_native_handle_update(native_session_id="sess-parent")
    session_state = with_provider_resume_recovery_request(
        base_session_state,
        action="new-session-from-memory",
        failure=ProviderResumeFailureRecord(
            provider="claude-cli",
            remote_strategy="claude-session-resume",
            continuation_mode="remote-primary",
            continuation_path="remote-resume",
            remote_handle_kind="session_id",
            expected_handle_id="sess-parent",
            turn_index=2,
            failure_text="resume failed",
            local_memory_available=True,
        ),
    )
    bundle = ProviderPromptBundle(
        system_instructions="system",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(bundle, session_state)

    assert len(calls) == 1
    assert "--resume" not in calls[0]
    assert turn.provider_metadata["continuation_path"] == "local-memory-fallback"
    assert turn.provider_metadata["local_memory_fallback_used"] is True
    assert turn.provider_metadata["memory_injected"] is True
    assert turn.provider_metadata["fresh_remote_turn"] is True
    assert turn.provider_metadata["resumed_remote"] is False
    assert turn.provider_metadata["remote_handle_id"] == "sess-fresh"
    assert turn.provider_metadata["recovery_created_new_session"] is True
    assert turn.provider_metadata["replaced_remote_handle_id"] == "sess-parent"
    assert turn.session_state.metadata["resume_recovery_action"] is None


def test_codex_cli_provider_resumes_remote_thread_and_records_unified_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    working_dir = tmp_path / "codex-resume"
    working_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command: list[str], **kwargs: object) -> object:
        calls.append(command)
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
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

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_codex_cli.subprocess.run", fake_run)

    provider = CodexCLIDecisionProvider(model="gpt-5")
    session_state = make_provider_session_state(
        provider="codex-cli",
        model="gpt-5",
        continuation_mode="remote-primary",
        runtime_context=ProviderRuntimeContext(
            runtime_root=str(working_dir),
            working_directory=str(working_dir),
        ),
    ).with_native_handle_update(
        native_session_id="thread-parent",
        provider_fields={"codex_thread_id": "thread-parent"},
    )
    bundle = ProviderPromptBundle(
        system_instructions="system",
        tool_schema_text="tool schema",
        provider_memory_text="",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(bundle, session_state)

    assert calls
    assert "resume" in calls[0]
    assert "thread-parent" in calls[0]
    assert turn.provider_metadata["remote_strategy"] == "codex-thread-resume"
    assert turn.provider_metadata["remote_handle_kind"] == "thread_id"
    assert turn.provider_metadata["remote_handle_id"] == "thread-parent"
    assert turn.provider_metadata["remote_handle_present"] is True
    assert turn.provider_metadata["resumed_remote"] is True
    assert turn.provider_metadata["fresh_remote_turn"] is False
    assert turn.provider_metadata["local_memory_fallback_used"] is False
    assert turn.provider_metadata["prompt_render_mode"] == "remote-delta"
    assert turn.provider_metadata["memory_injected"] is False


def test_codex_cli_provider_resume_failure_fails_closed_by_default(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    working_dir = tmp_path / "codex-strict"
    working_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command: list[str], **kwargs: object) -> object:
        del kwargs
        calls.append(command)
        return SimpleNamespace(returncode=1, stdout="", stderr="resume failed")

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_codex_cli.subprocess.run", fake_run)

    provider = CodexCLIDecisionProvider(model="gpt-5")
    session_state = make_provider_session_state(
        provider="codex-cli",
        model="gpt-5",
        continuation_mode="remote-primary",
        runtime_context=ProviderRuntimeContext(
            runtime_root=str(working_dir),
            working_directory=str(working_dir),
        ),
    ).with_native_handle_update(
        native_session_id="thread-parent",
        provider_fields={"codex_thread_id": "thread-parent"},
    )
    bundle = ProviderPromptBundle(
        system_instructions="system",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    with pytest.raises(ProviderResumeFailure) as exc_info:
        provider._next_decision_sync(bundle, session_state)

    assert len(calls) == 1
    assert "resume" in calls[0] and "thread-parent" in calls[0]
    record = exc_info.value.to_record()
    assert record["provider"] == "codex-cli"
    assert record["remote_handle_kind"] == "thread_id"
    assert record["expected_handle_id"] == "thread-parent"
    assert record["replacement_provider_session_started"] is False
    assert "resume failed" in str(record["failure_text"])


def test_codex_cli_provider_explicit_recovery_starts_labeled_fresh_memory_thread(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    working_dir = tmp_path / "codex-recovery"
    working_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command: list[str], **kwargs: object) -> object:
        del kwargs
        calls.append(command)
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
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
        return SimpleNamespace(
            returncode=0,
            stdout='{"type":"thread.started","thread_id":"thread-fresh"}\n',
            stderr="",
        )

    monkeypatch.setattr("pyocd_debug_mcp.brain.provider_codex_cli.subprocess.run", fake_run)

    provider = CodexCLIDecisionProvider(model="gpt-5")
    base_session_state = make_provider_session_state(
        provider="codex-cli",
        model="gpt-5",
        continuation_mode="remote-primary",
        runtime_context=ProviderRuntimeContext(
            runtime_root=str(working_dir),
            working_directory=str(working_dir),
        ),
    ).with_native_handle_update(
        native_session_id="thread-parent",
        provider_fields={"codex_thread_id": "thread-parent"},
    )
    session_state = with_provider_resume_recovery_request(
        base_session_state,
        action="new-session-from-memory",
        failure=ProviderResumeFailureRecord(
            provider="codex-cli",
            remote_strategy="codex-thread-resume",
            continuation_mode="remote-primary",
            continuation_path="remote-resume",
            remote_handle_kind="thread_id",
            expected_handle_id="thread-parent",
            turn_index=2,
            failure_text="resume failed",
            local_memory_available=True,
        ),
    )
    bundle = ProviderPromptBundle(
        system_instructions="system",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    turn = provider._next_decision_sync(bundle, session_state)

    assert len(calls) == 1
    assert "resume" not in calls[0]
    assert "--ephemeral" not in calls[0]
    assert turn.provider_metadata["continuation_path"] == "local-memory-fallback"
    assert turn.provider_metadata["local_memory_fallback_used"] is True
    assert turn.provider_metadata["memory_injected"] is True
    assert turn.provider_metadata["fresh_remote_turn"] is True
    assert turn.provider_metadata["resumed_remote"] is False
    assert turn.provider_metadata["remote_handle_id"] == "thread-fresh"
    assert turn.provider_metadata["recovery_created_new_session"] is True
    assert turn.provider_metadata["replaced_remote_handle_id"] == "thread-parent"
    assert turn.session_state.metadata["resume_recovery_action"] is None
