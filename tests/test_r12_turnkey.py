from __future__ import annotations

import json
from collections import deque
from dataclasses import replace
from pathlib import Path
import subprocess
from types import SimpleNamespace
from typing import Any, cast

import anyio
import pytest

from pyocd_debug_mcp import benchmark_support as r11
from pyocd_debug_mcp import reference_smoke
from pyocd_debug_mcp.brain import app as brain_app
from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain import loop as loop_mod
from pyocd_debug_mcp.brain.actions import (
    FinalizeAction,
    ServerToolAction,
    TurnDecision,
    TurnkeyRunResult,
    VerificationSnapshot,
)
from pyocd_debug_mcp.brain.cli import build_parser as build_turnkey_cli_parser
from pyocd_debug_mcp.brain.config import (
    BrainProviderConfig,
    BrainConfigError,
    build_turnkey_invocation,
    load_provider_config,
    resolve_memory_mode,
    resolve_native_sync_every,
)
from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.brain.loop import TurnkeyExecution, run_turnkey, run_turnkey_with_provider
from pyocd_debug_mcp.brain.mcp_client import MCPClientError, ToolDescriptor, ToolTextResult
from pyocd_debug_mcp.brain.provider_claude_cli import (
    _build_claude_command,
    _extract_claude_output_text,
)
from pyocd_debug_mcp.brain.provider_codex_cli import _build_codex_command
from pyocd_debug_mcp.brain.provider_types import (
    apply_deterministic_compaction,
    append_memory_entry,
    plan_memory_compaction,
    ProviderCapabilities,
    ProviderMemoryEntry,
    ProviderMemorySummaryResult,
    ProviderPromptBundle,
    ProviderProgressUpdate,
    ProviderSessionState,
    ProviderTurn,
    make_provider_session_state,
)
from pyocd_debug_mcp.brain.skills import load_skills_for_context
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain.tool_schemas import build_tool_schema_bundle
from pyocd_debug_mcp.brain.workspace import WorkspaceError, prepare_workspace_session
from pyocd_debug_mcp.timeouts import (
    TurnkeyTimeoutConfig,
    TURNKEY_CONNECT_TIMEOUT_SECONDS,
    TURNKEY_DEFAULT_TOOL_TIMEOUT_SECONDS,
    TURNKEY_FLASH_TIMEOUT_SECONDS,
    TURNKEY_RECOVER_TIMEOUT_SECONDS,
)


class FakeProvider:
    def __init__(self, decisions: list[TurnDecision]) -> None:
        self._decisions = deque(decisions)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_native_session=False,
            supports_transcript_continuation=True,
            supports_response_id_continuation=False,
            supports_tool_schema_prompt=True,
            continuation_mode="transcript-only",
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
            response_id="resp-test",
            session_state=session_state.with_last_continuation_path(
                "transcript-memory",
                metadata={"continuation_kind": "test-transcript-memory"},
            ),
            provider_metadata={
                "continuation_kind": "test-transcript-memory",
                "continuation_path": "transcript-memory",
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
        turns = ",".join(str(entry.turn_index) for entry in evicted_entries) or "none"
        return ProviderMemorySummaryResult(
            summary_text=f"{prior_summary_text}\n- summarized turns: {turns}".strip(),
            provider_metadata={"provider": "fake-provider"},
        )


class FakeClient:
    def __init__(self, results: dict[str, list[ToolTextResult]]) -> None:
        self._results = {name: deque(items) for name, items in results.items()}
        self.calls: list[tuple[str, dict[str, object] | None]] = []
        self._tool_descriptors = (
            ToolDescriptor(
                name="connect",
                description="Connect to one board.",
                input_schema={"type": "object", "properties": {"board_id": {"type": "string"}}},
            ),
            ToolDescriptor(
                name="read_serial",
                description="Read serial text until a match or timeout.",
                input_schema={"type": "object", "properties": {"expected_text": {"type": "string"}}},
            ),
            ToolDescriptor(
                name="disconnect",
                description="Disconnect the active session.",
                input_schema={"type": "object", "properties": {}},
            ),
            ToolDescriptor(
                name="get_state",
                description="Read target state.",
                input_schema={"type": "object", "properties": {}},
            ),
            ToolDescriptor(
                name="flash_firmware",
                description="Flash one firmware artifact.",
                input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            ),
            ToolDescriptor(
                name="unlock_recover",
                description="Recover a protected device.",
                input_schema={"type": "object", "properties": {"confirm": {"type": "boolean"}}},
            ),
        )

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, object] | None = None) -> ToolTextResult:
        self.calls.append((tool_name, arguments))
        queue = self._results.get(tool_name)
        if not queue:
            raise RuntimeError(f"Unexpected tool call: {tool_name}")
        return queue.popleft()

    async def list_tools(self) -> tuple[ToolDescriptor, ...]:
        return self._tool_descriptors


def test_load_provider_config_requires_api_key_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PYOCD_TURNKEY_MODEL", raising=False)
    monkeypatch.delenv("PYOCD_TURNKEY_PROVIDER", raising=False)

    with pytest.raises(BrainConfigError):
        load_provider_config(None)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(BrainConfigError):
        load_provider_config(None)

    monkeypatch.setenv("PYOCD_TURNKEY_MODEL", "gpt-test")
    config = load_provider_config(None)
    assert config.provider == "openai-api"
    assert config.api_key == "test-key"
    assert config.model == "gpt-test"


def test_load_provider_config_supports_anthropic_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PYOCD_TURNKEY_PROVIDER", "anthropic-api")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anth-key")
    monkeypatch.setenv("PYOCD_TURNKEY_MODEL", "claude-sonnet-test")

    config = load_provider_config(None)
    assert config.provider == "anthropic-api"
    assert config.api_key == "anth-key"
    assert config.model == "claude-sonnet-test"


def test_load_provider_config_supports_cli_providers_without_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PYOCD_TURNKEY_MODEL", raising=False)
    monkeypatch.setenv("PYOCD_TURNKEY_PROVIDER", "codex-cli")
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/local/bin/{name}")

    codex = load_provider_config(None)
    assert codex.provider == "codex-cli"
    assert codex.api_key is None
    assert codex.model is None

    monkeypatch.setenv("PYOCD_TURNKEY_PROVIDER", "claude-cli")
    claude = load_provider_config(None)
    assert claude.provider == "claude-cli"
    assert claude.api_key is None
    assert claude.model is None


def test_turnkey_loop_uses_shared_timeout_constants() -> None:
    from pyocd_debug_mcp.brain.loop import _tool_timeout_seconds

    ordinary = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nucleo_l476rg",
        task="Verify the board.",
        model=None,
        max_iters=2,
        serial_read_seconds=3.0,
    )
    long_serial = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nucleo_l476rg",
        task="Verify the board.",
        model=None,
        max_iters=2,
        serial_read_seconds=45.0,
    )

    assert _tool_timeout_seconds("connect", ordinary) == TURNKEY_CONNECT_TIMEOUT_SECONDS
    assert _tool_timeout_seconds("flash_firmware", ordinary) == TURNKEY_FLASH_TIMEOUT_SECONDS
    assert _tool_timeout_seconds("unlock_recover", ordinary) == TURNKEY_RECOVER_TIMEOUT_SECONDS
    assert _tool_timeout_seconds("get_state", ordinary) == TURNKEY_DEFAULT_TOOL_TIMEOUT_SECONDS
    assert _tool_timeout_seconds("read_serial", ordinary) == TURNKEY_DEFAULT_TOOL_TIMEOUT_SECONDS
    assert _tool_timeout_seconds("read_serial", long_serial) == 57.0


def test_provider_session_state_serialization_and_deterministic_compaction() -> None:
    state = make_provider_session_state(
        provider="codex-cli",
        model=None,
        continuation_mode="transcript-only",
    )
    for index in range(1, 7):
        state = append_memory_entry(
            state,
            ProviderMemoryEntry(
                turn_index=index,
                classification="healthy",
                observation_summary=f"obs {index}",
                hypothesis=None,
                action_kind="server_tool",
                action_summary=f"connect {index}",
                result_summary=f"result {index}",
                verification_snapshot="flash=True uart=True symbol=True green=True",
            ),
        )
    plan = plan_memory_compaction(state)
    assert plan is not None

    state = apply_deterministic_compaction(state, plan)
    record = state.to_record()

    assert record["provider"] == "codex-cli"
    assert record["memory_mode"] == "deterministic"
    assert len(record["recent_memory_entries"]) == 4
    assert record["recent_memory_entries"][0]["turn_index"] == 3
    assert record["memory_summary"]["covered_through_turn"] == 2
    assert record["memory_summary"]["source"] == "deterministic"


def test_provider_prompt_bundle_exposes_static_and_dynamic_render_modes() -> None:
    bundle = ProviderPromptBundle(
        system_instructions="sys",
        tool_schema_text="tool schema",
        provider_memory_text="memory block",
        turn_context_text="turn context",
        turn_decision_schema_text="decision schema",
    )

    assert bundle.render_bootstrap_text(include_memory=True) == (
        "tool schema\n\nmemory block\n\nturn context\n\ndecision schema"
    )
    assert bundle.render_native_delta_text() == "turn context"
    assert bundle.render_native_sync_text(include_memory=True) == (
        "tool schema\n\nmemory block\n\nturn context\n\ndecision schema"
    )
    assert bundle.render_retry_text("retry now") == "turn context\n\ndecision schema\n\nretry now"


def test_tool_schema_bundle_filters_and_orders_curated_tools() -> None:
    bundle = build_tool_schema_bundle(
        (
            ToolDescriptor(
                name="read_serial",
                description="Read UART.",
                input_schema={"type": "object", "properties": {"expected_text": {"type": "string"}}},
            ),
            ToolDescriptor(
                name="connect",
                description="Connect to a board.",
                input_schema={"type": "object", "properties": {"board_id": {"type": "string"}}},
            ),
            ToolDescriptor(
                name="debug_internal_only",
                description="Ignore me.",
                input_schema={"type": "object"},
            ),
        )
    )

    assert [entry.name for entry in bundle.entries] == ["connect", "read_serial"]
    assert "debug_internal_only" not in bundle.rendered_text
    assert "Refused [<code>]: <message> session_id=<id>" in bundle.rendered_text
    assert "Blocked [<code>]: <message> session_id=<id>" in bundle.rendered_text
    assert "Success text includes `session_id=...`" in bundle.rendered_text
    assert bundle.schema_hash


def test_memory_config_defaults_and_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYOCD_TURNKEY_MEMORY_MODE", raising=False)
    monkeypatch.delenv("PYOCD_TURNKEY_NATIVE_SYNC_EVERY", raising=False)

    assert resolve_memory_mode() == "deterministic"
    assert resolve_native_sync_every() == 4

    monkeypatch.setenv("PYOCD_TURNKEY_MEMORY_MODE", "model-summary")
    monkeypatch.setenv("PYOCD_TURNKEY_NATIVE_SYNC_EVERY", "7")

    assert resolve_memory_mode() == "model-summary"
    assert resolve_native_sync_every() == 7


def test_memory_compaction_triggers_on_recent_memory_char_limit() -> None:
    state = ProviderSessionState(
        provider="codex-cli",
        model=None,
        memory_mode="deterministic",
        continuation_mode="transcript-only",
        recent_render_char_limit=200,
    )
    for index in range(1, 4):
        state = append_memory_entry(
            state,
            ProviderMemoryEntry(
                turn_index=index,
                classification="healthy",
                observation_summary="x" * 180,
                hypothesis=None,
                action_kind="server_tool",
                action_summary="y" * 180,
                result_summary="z" * 180,
                verification_snapshot="flash=True uart=False symbol=True green=False",
            ),
        )
    plan = plan_memory_compaction(state)
    assert plan is not None
    assert plan.evicted_entries
    assert plan.rendered_recent_char_count <= state.recent_render_char_limit


def test_product_runtime_modules_do_not_import_tests_or_mutate_sys_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    product_files = (
        repo_root / "src" / "pyocd_debug_mcp" / "brain" / "app.py",
        repo_root / "src" / "pyocd_debug_mcp" / "brain" / "benchmark.py",
        repo_root / "src" / "pyocd_debug_mcp" / "brain" / "cli.py",
        repo_root / "src" / "pyocd_debug_mcp" / "benchmark_support.py",
        repo_root / "src" / "pyocd_debug_mcp" / "reference_smoke.py",
    )

    for path in product_files:
        text = path.read_text(encoding="utf-8")
        assert "tests.harness" not in text, path
        assert "tests." not in text, path
        assert "sys.path.insert" not in text, path


def test_stage1_harness_wrapper_reexports_shared_smoke_module() -> None:
    from tests.harness import stage1_smoke as harness_smoke

    assert harness_smoke.run_stage1_smoke is reference_smoke.run_stage1_smoke
    assert harness_smoke.main is reference_smoke.main


def test_r11_harness_wrapper_reexports_shared_benchmark_module() -> None:
    from tests.harness import r11_benchmark as harness_benchmark

    assert harness_benchmark.run_case is r11.run_case
    assert harness_benchmark.run_suite is r11.run_suite
    assert harness_benchmark.main is r11.main


def test_run_freeform_task_does_not_refuse_fix_wording_without_repair_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_run_turnkey_with_provider(
        invocation: object,
        *,
        provider_config: object,
        event_sink: object = None,
    ) -> SimpleNamespace:
        captured["invocation"] = invocation
        captured["provider_config"] = provider_config
        captured["event_sink"] = event_sink
        return SimpleNamespace(result=SimpleNamespace(final_status="diagnosed_only"))

    monkeypatch.setattr(
        brain_app,
        "load_provider_config",
        lambda model, provider=None: BrainProviderConfig(provider="codex-cli", model=model),
    )
    monkeypatch.setattr(brain_app, "run_turnkey_with_provider", _fake_run_turnkey_with_provider)

    execution = anyio.run(
        lambda: brain_app.run_freeform_task(
            board_id="nucleo_l476rg",
            task="Fix the wrong UART boot signature, but start by diagnosing it carefully.",
            provider="codex-cli",
            model=None,
        )
    )

    assert execution.result.final_status == "diagnosed_only"
    invocation = captured["invocation"]
    assert getattr(invocation, "task").startswith("Fix the wrong UART boot signature")
    assert getattr(invocation, "workspace_root") is None
    assert getattr(invocation, "allowed_edit_roots") == ()


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


def test_skill_loader_selects_baseline_skill_for_freeform_verify_task() -> None:
    board = r11._load_board("nucleo_l476rg")

    skills = load_skills_for_context(
        board=board,
        task="Verify this reference firmware is healthy and explain why.",
        case_kind=None,
    )

    skill_ids = [skill.skill_id for skill in skills]
    assert "common.baseline_verification" in skill_ids


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


def test_prepare_workspace_session_refuses_binary_read(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "src").mkdir(parents=True)
    (workspace_root / "src" / "firmware.bin").write_bytes(b"\x90\x00\xFF\x10")

    session = prepare_workspace_session(
        workspace_root=workspace_root,
        allowed_edit_roots=("src",),
        build_command="./build.sh",
        code_edits_allowed=True,
        label="unit-binary",
    )

    with pytest.raises(WorkspaceError, match="not UTF-8 text"):
        session.read_file("src/firmware.bin")


def test_run_turnkey_writes_run_artifacts_and_uses_structured_session_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="openai-api",
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
            TurnDecision.model_validate(
                {
                    "observation_summary": "The board now has enough evidence for a full green check.",
                    "classification": "healthy",
                    "action": {"kind": "run_green_check"},
                }
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
                ),
                ToolTextResult(
                    tool_name="read_serial",
                    text="UART matched on /dev/cu.usbmodem0006854006931 at 115200 baud via pyocd-native; expected='boot ok'; reopen_count=0; duration=1.00s; excerpt=boot ok",
                )
            ],
            "flash_firmware": [
                ToolTextResult(
                    tool_name="flash_firmware",
                    text="Flashed /tmp/reference.hex via pyocd-native; target left halted.",
                )
            ],
            "read_core_register": [
                ToolTextResult(tool_name="read_core_register", text="0x20000000")
            ],
            "disconnect": [
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
            ],
        }
    )
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop.resolve_symbol",
        lambda *_args, **_kwargs: SimpleNamespace(name="stage1_known_value", address=0x20000010),
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, client_factory),
        )
    )

    assert execution.result.final_status == "healthy_confirmed"
    assert execution.result.session_id == "20260620T000000Z-deadbeef"
    assert execution.state.session_id is None
    assert execution.state.session_ids_seen == ["20260620T000000Z-deadbeef"]
    assert execution.run_root == (tmp_path / "runs" / "20260620T000000Z-deadbeef")
    assert (execution.run_root / "run-metadata" / "turnkey_request.json").exists()
    assert (execution.run_root / "run-metadata" / "turnkey_result.json").exists()
    assert (execution.run_root / "run-metadata" / "turnkey_state.json").exists()
    assert (execution.run_root / "logs" / "brain_trace.jsonl").exists()
    assert (execution.run_root / "logs" / "model_turns.jsonl").exists()
    assert (execution.run_root / "logs" / "brain_events.jsonl").exists()
    event_kinds = [
        json.loads(line)["event_kind"]
        for line in (execution.run_root / "logs" / "brain_events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert "provider_turn_start" in event_kinds
    assert "provider_turn_complete" in event_kinds
    assert "tool_complete" in event_kinds
    assert "final_result" in event_kinds


def test_run_turnkey_returns_structured_tooling_failure_for_provider_turn_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FailingProvider:
        @property
        def capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(
                supports_native_session=False,
                supports_transcript_continuation=True,
                supports_response_id_continuation=False,
                supports_tool_schema_prompt=True,
                continuation_mode="transcript-only",
            )

        async def next_decision(
            self,
            *,
            prompt_bundle: ProviderPromptBundle,
            session_state: ProviderSessionState,
        ) -> ProviderTurn:
            raise RuntimeError("provider exploded")

        async def summarize_memory(
            self,
            *,
            session_state: ProviderSessionState,
            prior_summary_text: str,
            evicted_entries: tuple[ProviderMemoryEntry, ...],
        ) -> ProviderMemorySummaryResult:
            raise RuntimeError("summarizer exploded")

    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nrf52833dk",
        task="Verify this reference firmware is healthy and explain why.",
        model=None,
        max_iters=2,
        serial_read_seconds=1.0,
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=cast(Any, FailingProvider()),
            client_factory=cast(Any, lambda: FakeClient({})),
        )
    )

    assert execution.result.final_status == "blocked"
    assert execution.result.classification == "tooling_failure"
    assert execution.result.session_id is None
    assert execution.run_root is not None
    assert execution.run_root.name.startswith("turnkey-")
    assert (execution.run_root / "run-metadata" / "turnkey_request.json").exists()
    assert (execution.run_root / "run-metadata" / "turnkey_result.json").exists()
    assert (execution.run_root / "run-metadata" / "turnkey_state.json").exists()
    assert (execution.run_root / "logs" / "brain_events.jsonl").exists()
    assert "provider exploded" in execution.result.summary


def test_run_turnkey_forwards_provider_progress_updates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class ProgressProvider:
        @property
        def capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(
                supports_native_session=False,
                supports_transcript_continuation=True,
                supports_response_id_continuation=False,
                supports_tool_schema_prompt=True,
                continuation_mode="transcript-only",
            )

        async def next_decision(
            self,
            *,
            prompt_bundle: ProviderPromptBundle,
            session_state: ProviderSessionState,
        ) -> ProviderTurn:
            return ProviderTurn(
                decision=TurnDecision(
                    observation_summary="Healthy baseline confirmed.",
                    classification="healthy",
                    action=FinalizeAction(
                        final_status="diagnosed_only",
                        classification="healthy",
                        root_cause="No fault found.",
                        summary="Healthy baseline confirmed.",
                    ),
                ),
                output_text="{}",
                response_id="resp-progress",
                session_state=session_state.with_last_continuation_path("transcript-memory"),
                provider_metadata={"continuation_path": "transcript-memory"},
                progress_updates=(
                    ProviderProgressUpdate(
                        stage="provider_request",
                        message="Dispatching fake provider request.",
                    ),
                ),
            )

        async def summarize_memory(
            self,
            *,
            session_state: ProviderSessionState,
            prior_summary_text: str,
            evicted_entries: tuple[ProviderMemoryEntry, ...],
        ) -> ProviderMemorySummaryResult:
            return ProviderMemorySummaryResult(summary_text=prior_summary_text or "- summary")

    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nucleo_l476rg",
        task="Verify this reference firmware is healthy.",
        model=None,
        max_iters=1,
        serial_read_seconds=1.0,
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=cast(Any, ProgressProvider()),
            client_factory=cast(Any, lambda: FakeClient({})),
        )
    )

    event_kinds = [record["event_kind"] for record in execution.brain_events]
    assert "provider_progress" in event_kinds


def test_run_turnkey_uses_invocation_default_timeout_for_disconnect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    captured_disconnect_timeouts: list[float] = []
    original_call_tool = loop_mod._call_tool_with_timeout

    async def _wrapped_call_tool(client: Any, tool_name: str, arguments: dict[str, object], *, timeout_seconds: float) -> ToolTextResult:
        if tool_name == "disconnect":
            captured_disconnect_timeouts.append(timeout_seconds)
        return await original_call_tool(client, tool_name, arguments, timeout_seconds=timeout_seconds)

    monkeypatch.setattr("pyocd_debug_mcp.brain.loop._call_tool_with_timeout", _wrapped_call_tool)
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nucleo_l476rg",
        task="Verify this reference firmware is healthy.",
        model=None,
        max_iters=2,
        serial_read_seconds=1.0,
        timeout_config=replace(TurnkeyTimeoutConfig(), default_tool_seconds=17.0),
    )
    provider = FakeProvider(
        [
            TurnDecision(
                observation_summary="Need to connect first.",
                classification="healthy",
                action=ServerToolAction(tool_name="connect", arguments={}),
            ),
            TurnDecision(
                observation_summary="Connected and healthy.",
                classification="healthy",
                action=FinalizeAction(
                    final_status="diagnosed_only",
                    classification="healthy",
                    root_cause="No fault found.",
                    summary="Healthy baseline confirmed.",
                ),
            ),
        ]
    )

    anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(
                Any,
                lambda: FakeClient(
                    {
                        "connect": [
                            ToolTextResult(
                                tool_name="connect",
                                text=(
                                    "Connected to board 'NUCLEO-L476RG' via probe "
                                    "0668FF514988525067213913 via pyocd-native. "
                                    "[board config: nucleo_l476rg] session_id=20260625T000000Z-timeout"
                                ),
                            )
                        ],
                        "disconnect": [ToolTextResult(tool_name="disconnect", text="Disconnected.")],
                    }
                ),
            ),
        )
    )

    assert captured_disconnect_timeouts == [17.0]


def test_run_turnkey_returns_structured_tooling_failure_for_mcp_startup_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class StartupFailureClient:
        async def __aenter__(self) -> "StartupFailureClient":
            raise MCPClientError("startup failed")

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    provider = FakeProvider(
        [
            TurnDecision(
                observation_summary="Need to connect first.",
                classification="healthy",
                action=ServerToolAction(tool_name="connect", arguments={}),
            )
        ]
    )
    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nrf52833dk",
        task="Verify this reference firmware is healthy and explain why.",
        model=None,
        max_iters=2,
        serial_read_seconds=1.0,
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, lambda: StartupFailureClient()),
        )
    )

    assert execution.result.final_status == "blocked"
    assert execution.result.classification == "tooling_failure"
    assert execution.result.session_id is None
    assert execution.run_root is not None
    assert execution.run_root.name.startswith("turnkey-")
    assert (execution.run_root / "run-metadata" / "turnkey_result.json").exists()
    assert "mcp-startup-failed" in execution.result.summary


def test_run_turnkey_with_provider_normalizes_provider_setup_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop.create_decision_provider",
        lambda _config: (_ for _ in ()).throw(RuntimeError("provider setup failed")),
    )
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nucleo_l476rg",
        task="Verify this reference firmware is healthy and explain why.",
        model=None,
        max_iters=2,
        serial_read_seconds=1.0,
    )

    execution = anyio.run(
        lambda: run_turnkey_with_provider(
            invocation,
            provider_config=BrainProviderConfig(provider="codex-cli", model=None),
        )
    )

    assert execution.result.final_status == "blocked"
    assert execution.result.classification == "tooling_failure"
    assert execution.result.session_id is None
    assert execution.run_root is not None
    assert (execution.run_root / "run-metadata" / "turnkey_result.json").exists()
    assert "provider-setup-failed" in execution.result.summary


def test_run_turnkey_treats_binary_read_as_workspace_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    workspace_root = tmp_path / "workspace"
    (workspace_root / "src").mkdir(parents=True)
    (workspace_root / "src" / "firmware.bin").write_bytes(b"\x90\x00\xFF\x10")

    invocation = build_turnkey_invocation(
        mode="benchmark",
        provider="openai-api",
        board_id="nucleo_l476rg",
        task="Inspect the workspace and diagnose the fault.",
        model="gpt-test",
        max_iters=2,
        serial_read_seconds=1.0,
        workspace_root=workspace_root,
        build_command="./build.sh",
        case_id="nucleo_l476rg__b_test_binary_read",
        case_kind="injected_bug",
        expected_uart_substring="boot ok",
        expected_symbol_name="stage1_known_value",
        expected_symbol_value_u32=0x1234ABCD,
        code_edits_allowed=True,
        allowed_edit_roots=("src",),
        recover_allowed=False,
    )
    provider = FakeProvider(
        [
            TurnDecision.model_validate(
                {
                    "observation_summary": "Inspect the workspace file first.",
                    "classification": "code_bug",
                    "action": {"kind": "read_file", "path": "src/firmware.bin"},
                }
            ),
            TurnDecision(
                observation_summary="The binary read was refused cleanly, so summarize that limitation.",
                classification="code_bug",
                action=FinalizeAction(
                    final_status="diagnosed_only",
                    classification="code_bug",
                    root_cause="The requested workspace path is a binary artifact, not a UTF-8 source file.",
                    summary="Binary workspace reads are rejected cleanly.",
                ),
            ),
        ]
    )
    client_factory = lambda: FakeClient({})  # noqa: E731

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, client_factory),
        )
    )

    assert execution.result.final_status == "diagnosed_only"
    assert "WorkspaceError" in execution.state.last_result_text
    assert "not UTF-8 text" in execution.state.last_result_text


def test_run_turnkey_allows_green_check_after_first_failed_fix_verification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("pyocd_debug_mcp.brain.loop.RUNS_ROOT", tmp_path / "runs")
    workspace_root = tmp_path / "workspace"
    source = workspace_root / "src" / "src" / "main.c"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("boot nope\n", encoding="utf-8")

    invocation = build_turnkey_invocation(
        mode="benchmark",
        provider="openai-api",
        board_id="nucleo_l476rg",
        task="Fix the wrong UART boot text and verify the board is healthy again.",
        model="gpt-test",
        max_iters=8,
        serial_read_seconds=1.0,
        workspace_root=workspace_root,
        build_command="true",
        case_id="nucleo_l476rg__b001_wrong_boot_text",
        case_kind="injected_bug",
        expected_uart_substring="boot ok",
        expected_symbol_name="stage1_known_value",
        expected_symbol_value_u32=0x1234ABCD,
        code_edits_allowed=True,
        allowed_edit_roots=("src",),
        recover_allowed=False,
    )
    provider = FakeProvider(
        [
            TurnDecision(
                observation_summary="Connect to the scoped board first.",
                classification=None,
                action=ServerToolAction(tool_name="connect", arguments={"board_id": "nucleo_l476rg"}),
            ),
            TurnDecision(
                observation_summary="Flash the current workspace image before checking UART.",
                classification=None,
                action=ServerToolAction(tool_name="flash_firmware", arguments={}),
            ),
            TurnDecision(
                observation_summary="Capture UART from the flashed image to confirm the bug.",
                classification=None,
                action=ServerToolAction(tool_name="read_serial", arguments={}),
            ),
            TurnDecision.model_validate(
                {
                    "observation_summary": "The board prints the wrong boot text, so patch the workspace source.",
                    "classification": "code_bug",
                    "action": {
                        "kind": "replace_file",
                        "path": "src/src/main.c",
                        "content": "boot ok\n",
                    },
                }
            ),
            TurnDecision.model_validate(
                {
                    "observation_summary": "The source fix is applied; rebuild the workspace.",
                    "classification": "code_bug",
                    "action": {
                        "kind": "run_build",
                        "build_command": "true",
                    },
                }
            ),
            TurnDecision(
                observation_summary="Reflash the rebuilt image before the final verifier.",
                classification="code_bug",
                action=ServerToolAction(tool_name="flash_firmware", arguments={}),
            ),
            TurnDecision.model_validate(
                {
                    "observation_summary": "The repaired build is flashed; run the canonical green check now.",
                    "classification": "code_bug",
                    "action": {"kind": "run_green_check"},
                }
            ),
            TurnDecision(
                observation_summary="The repaired image is now healthy.",
                classification="code_bug",
                action=FinalizeAction(
                    final_status="fixed",
                    classification="code_bug",
                    root_cause="The workspace firmware printed the wrong boot text and now matches the tracked healthy baseline.",
                    summary="Repaired the UART boot text and verified the board is healthy again.",
                ),
            ),
        ]
    )
    client_factory = lambda: FakeClient(  # noqa: E731
        {
            "connect": [
                ToolTextResult(
                    tool_name="connect",
                    text="Connected to board 'NUCLEO-L476RG' via probe 0668FF514988525067213913 via pyocd-native. [board config: nucleo_l476rg] session_id=20260620T000000Z-fixcheck",
                )
            ],
            "flash_firmware": [
                ToolTextResult(
                    tool_name="flash_firmware",
                    text="Flashed /tmp/firmware.hex via pyocd-native; target left running.",
                ),
                ToolTextResult(
                    tool_name="flash_firmware",
                    text="Flashed /tmp/firmware.hex via pyocd-native; target left running.",
                ),
                ToolTextResult(
                    tool_name="flash_firmware",
                    text="Flashed /tmp/firmware.hex via pyocd-native; target left halted.",
                ),
            ],
            "read_serial": [
                ToolTextResult(
                    tool_name="read_serial",
                    text="UART did not match on /dev/cu.usbmodem143103 at 115200 baud via pyocd-native; expected='boot ok'; reopen_count=1; duration=2.00s; excerpt=boot nope",
                ),
                ToolTextResult(
                    tool_name="read_serial",
                    text="UART matched on /dev/cu.usbmodem143103 at 115200 baud via pyocd-native; expected='boot ok'; reopen_count=0; duration=1.00s; excerpt=boot ok",
                )
            ],
            "read_core_register": [
                ToolTextResult(tool_name="read_core_register", text="0x08000B28")
            ],
            "read_memory": [
                ToolTextResult(tool_name="read_memory", text="0x1234ABCD")
            ],
            "disconnect": [
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
            ],
        }
    )
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop.resolve_symbol",
        lambda *_args, **_kwargs: SimpleNamespace(name="stage1_known_value", address=0x08001000),
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, client_factory),
        )
    )

    assert execution.result.final_status == "fixed"
    assert execution.result.verification.green_check_ok is True
    assert execution.state.stagnant_fix_cycle_count == 0
    assert execution.state.pending_fix_evaluation is False
    assert "run_green_check" in execution.result.actions_taken


def test_run_turnkey_refuses_healthy_finalize_before_green_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="openai-api",
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
                observation_summary="UART looks good already, so finalize healthy.",
                classification="healthy",
                action=FinalizeAction(
                    final_status="healthy_confirmed",
                    classification="healthy",
                    root_cause="Premature healthy conclusion.",
                    summary="Should be refused until green check passes.",
                ),
            ),
            TurnDecision.model_validate(
                {
                    "observation_summary": "Run the canonical green check now.",
                    "classification": "healthy",
                    "action": {"kind": "run_green_check"},
                }
            ),
            TurnDecision(
                observation_summary="Green check passed; finalize healthy.",
                classification="healthy",
                action=FinalizeAction(
                    final_status="healthy_confirmed",
                    classification="healthy",
                    root_cause="Tracked reference behavior matches the healthy contract.",
                    summary="Healthy baseline confirmed after green check.",
                ),
            ),
        ]
    )
    fake_client = FakeClient(
        {
            "connect": [
                ToolTextResult(
                    tool_name="connect",
                    text="Connected to board 'nRF52833 DK' via probe 685400693 via pyocd-native. [board config: nrf52833dk] session_id=20260620T000000Z-deadbeef",
                )
            ],
            "flash_firmware": [
                ToolTextResult(
                    tool_name="flash_firmware",
                    text="Flashed /tmp/reference.hex via pyocd-native; target left halted.",
                )
            ],
            "read_core_register": [
                ToolTextResult(tool_name="read_core_register", text="0x20000000")
            ],
            "read_serial": [
                ToolTextResult(
                    tool_name="read_serial",
                    text="UART matched on /dev/cu.usbmodem0006854006931 at 115200 baud via pyocd-native; expected='boot ok'; reopen_count=0; duration=1.00s; excerpt=boot ok",
                )
            ],
            "disconnect": [
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
            ],
        }
    )
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop.resolve_symbol",
        lambda *_args, **_kwargs: SimpleNamespace(name="stage1_known_value", address=0x20000010),
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, lambda: fake_client),
        )
    )

    assert execution.result.final_status == "healthy_confirmed"
    assert execution.result.verification.green_check_ok is True
    assert execution.brain_trace[1]["result_text"].startswith(
        "Refused [brain/finalize-without-green-check]"
    )


def test_run_turnkey_refuses_redundant_connect() -> None:
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="openai-api",
        board_id="nrf52833dk",
        task="Verify this reference firmware is healthy and explain why.",
        model="gpt-test",
        max_iters=3,
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
                observation_summary="Reconnect to the same board again.",
                classification="healthy",
                action=ServerToolAction(tool_name="connect", arguments={"board_id": "nrf52833dk"}),
            ),
            TurnDecision(
                observation_summary="Stop after the redundant connect refusal.",
                classification="observability_fault",
                action=FinalizeAction(
                    final_status="diagnosed_only",
                    classification="observability_fault",
                    root_cause="Redundant reconnect was unnecessary.",
                    summary="Stopped after reconnect refusal.",
                ),
            ),
        ]
    )
    fake_client = FakeClient(
        {
            "connect": [
                ToolTextResult(
                    tool_name="connect",
                    text="Connected to board 'nRF52833 DK' via probe 685400693 via pyocd-native. [board config: nrf52833dk] session_id=20260620T000000Z-deadbeef",
                )
            ],
            "disconnect": [ToolTextResult(tool_name="disconnect", text="Disconnected.")],
        }
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, lambda: fake_client),
        )
    )

    assert execution.result.final_status == "diagnosed_only"
    assert execution.brain_trace[1]["result_text"].startswith("Refused [brain/redundant-connect]")


def test_run_turnkey_keeps_same_session_after_failed_green_check_in_benchmark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocation = build_turnkey_invocation(
        mode="benchmark",
        provider="openai-api",
        board_id="nucleo_l476rg",
        task="Repair the missing application UART output and verify the board is healthy again.",
        model="gpt-test",
        max_iters=4,
        serial_read_seconds=1.0,
        case_id="nucleo_l476rg__b003_silent_uart",
        case_kind="injected_bug",
        expected_uart_substring="boot ok",
        expected_symbol_name="stage1_known_value",
        expected_symbol_value_u32=0x1234ABCD,
        code_edits_allowed=True,
        allowed_edit_roots=("src",),
        recover_allowed=False,
    )
    provider = FakeProvider(
        [
            TurnDecision(
                observation_summary="Need to connect first.",
                classification="code_bug",
                action=ServerToolAction(tool_name="connect", arguments={}),
            ),
            TurnDecision.model_validate(
                {
                    "observation_summary": "Run the canonical verifier now that the board is connected.",
                    "classification": "code_bug",
                    "action": {"kind": "run_green_check"},
                }
            ),
            TurnDecision(
                observation_summary="Reconnect after the failed verifier.",
                classification="code_bug",
                action=ServerToolAction(tool_name="connect", arguments={"board_id": "nucleo_l476rg"}),
            ),
            TurnDecision(
                observation_summary="Stop after the reconnect refusal.",
                classification="code_bug",
                action=FinalizeAction(
                    final_status="diagnosed_only",
                    classification="code_bug",
                    root_cause="The verifier failed, but the original session remained active.",
                    summary="Stopped after redundant reconnect refusal.",
                ),
            ),
        ]
    )
    fake_client = FakeClient(
        {
            "connect": [
                ToolTextResult(
                    tool_name="connect",
                    text="Connected to board 'NUCLEO-L476RG' via probe 0668FF514988525067213913 via pyocd-native. [board config: nucleo_l476rg] session_id=20260620T000000Z-greenfail",
                )
            ],
            "flash_firmware": [
                ToolTextResult(
                    tool_name="flash_firmware",
                    text="Flashed /tmp/firmware.hex via pyocd-native; target left halted.",
                )
            ],
            "read_core_register": [
                ToolTextResult(tool_name="read_core_register", text="0x08000B28")
            ],
            "read_memory": [ToolTextResult(tool_name="read_memory", text="0x1234ABCD")],
            "disconnect": [ToolTextResult(tool_name="disconnect", text="Disconnected.")],
        }
    )
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop.resolve_symbol",
        lambda *_args, **_kwargs: SimpleNamespace(name="stage1_known_value", address=0x08001000),
    )
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop._parse_hex_text",
        lambda text, *, label: (_ for _ in ()).throw(RuntimeError("forced symbol read failure"))
        if label == "symbol stage1_known_value"
        else int(text, 0),
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, lambda: fake_client),
        )
    )

    assert execution.result.final_status == "diagnosed_only"
    assert execution.state.session_ids_seen == ["20260620T000000Z-greenfail"]
    assert execution.brain_trace[2]["result_text"].startswith("Refused [brain/redundant-connect]")


def test_run_turnkey_normalizes_integer_read_memory_address() -> None:
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="openai-api",
        board_id="nucleo_l476rg",
        task="Inspect runtime state without modifying code.",
        model="gpt-test",
        max_iters=3,
        serial_read_seconds=1.0,
    )
    provider = FakeProvider(
        [
            TurnDecision(
                observation_summary="Need to connect first.",
                classification="observability_fault",
                action=ServerToolAction(tool_name="connect", arguments={}),
            ),
            TurnDecision(
                observation_summary="Read memory from the board test address.",
                classification="observability_fault",
                action=ServerToolAction(tool_name="read_memory", arguments={"address": 0x08000000}),
            ),
            TurnDecision(
                observation_summary="Enough evidence collected.",
                classification="observability_fault",
                action=FinalizeAction(
                    final_status="diagnosed_only",
                    classification="observability_fault",
                    root_cause="Read-only inspection completed.",
                    summary="Finished without mutation.",
                ),
            ),
        ]
    )
    fake_client = FakeClient(
        {
            "connect": [
                ToolTextResult(
                    tool_name="connect",
                    text="Connected to board 'NUCLEO-L476RG' via probe 0668FF514988525067213913 via pyocd-native. [board config: nucleo_l476rg] session_id=20260620T000000Z-feedface",
                )
            ],
            "read_memory": [ToolTextResult(tool_name="read_memory", text="0x08000000")],
            "disconnect": [ToolTextResult(tool_name="disconnect", text="Disconnected.")],
        }
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, lambda: fake_client),
        )
    )

    assert execution.result.final_status == "diagnosed_only"
    assert fake_client.calls[1] == ("read_memory", {"address": "0x08000000"})


def test_run_turnkey_normalizes_relative_flash_path_against_workspace_root(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "build").mkdir(parents=True, exist_ok=True)

    invocation = build_turnkey_invocation(
        mode="benchmark",
        provider="openai-api",
        board_id="nrf52833dk",
        task="Flash the prepared benchmark artifact.",
        model="gpt-test",
        max_iters=3,
        serial_read_seconds=1.0,
        workspace_root=workspace_root,
        build_command="true",
        case_id="nrf52833dk__k001_reference_green",
        case_kind="known_good",
    )
    provider = FakeProvider(
        [
            TurnDecision(
                observation_summary="Need to connect first.",
                classification="healthy",
                action=ServerToolAction(tool_name="connect", arguments={}),
            ),
            TurnDecision(
                observation_summary="Flash the prepared workspace artifact.",
                classification="healthy",
                action=ServerToolAction(
                    tool_name="flash_firmware",
                    arguments={"path": "build/firmware.hex"},
                ),
            ),
            TurnDecision(
                observation_summary="Stop after the flash path normalization check.",
                classification="healthy",
                action=FinalizeAction(
                    final_status="diagnosed_only",
                    classification="healthy",
                    root_cause="Relative flash path normalization was exercised.",
                    summary="Finished flash path normalization coverage.",
                ),
            ),
        ]
    )
    fake_client = FakeClient(
        {
            "connect": [
                ToolTextResult(
                    tool_name="connect",
                    text="Connected to board 'nRF52833 DK' via probe 685400693 via pyocd-native. [board config: nrf52833dk] session_id=20260620T000000Z-flashpath",
                )
            ],
            "flash_firmware": [
                ToolTextResult(
                    tool_name="flash_firmware",
                    text="Flashed /tmp/workspace/build/firmware.hex via pyocd-native; target left running.",
                )
            ],
            "disconnect": [ToolTextResult(tool_name="disconnect", text="Disconnected.")],
        }
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, lambda: fake_client),
        )
    )

    assert execution.result.final_status == "diagnosed_only"
    assert fake_client.calls[1] == (
        "flash_firmware",
        {
            "path": str((workspace_root / "build" / "firmware.hex").resolve()),
        },
    )


def test_run_turnkey_defaults_benchmark_read_serial_to_expected_text_and_reset() -> None:
    invocation = build_turnkey_invocation(
        mode="benchmark",
        provider="openai-api",
        board_id="nucleo_l476rg",
        task="Validate the healthy benchmark baseline.",
        model="gpt-test",
        max_iters=3,
        serial_read_seconds=1.0,
        case_id="nucleo_l476rg__k001_reference_green",
        case_kind="known_good",
        expected_uart_substring="boot ok",
    )
    provider = FakeProvider(
        [
            TurnDecision(
                observation_summary="Need to connect first.",
                classification="healthy",
                action=ServerToolAction(tool_name="connect", arguments={}),
            ),
            TurnDecision(
                observation_summary="Check UART on the connected board.",
                classification="healthy",
                action=ServerToolAction(tool_name="read_serial", arguments={}),
            ),
            TurnDecision(
                observation_summary="Stop after UART verification.",
                classification="healthy",
                action=FinalizeAction(
                    final_status="diagnosed_only",
                    classification="healthy",
                    root_cause="Used for argument normalization coverage.",
                    summary="Finished benchmark UART defaulting test.",
                ),
            ),
        ]
    )
    fake_client = FakeClient(
        {
            "connect": [
                ToolTextResult(
                    tool_name="connect",
                    text="Connected to board 'NUCLEO-L476RG' via probe 0668FF514988525067213913 via pyocd-native. [board config: nucleo_l476rg] session_id=20260620T000000Z-feedface",
                )
            ],
            "read_serial": [
                ToolTextResult(
                    tool_name="read_serial",
                    text="UART matched on /dev/cu.usbmodem143103 at 115200 baud via pyocd-native; expected='boot ok'; reopen_count=0; duration=0.50s; excerpt=boot ok",
                )
            ],
            "disconnect": [ToolTextResult(tool_name="disconnect", text="Disconnected.")],
        }
    )

    execution = anyio.run(
        lambda: run_turnkey(
            invocation,
            provider=provider,
            client_factory=cast(Any, lambda: fake_client),
        )
    )

    assert execution.result.final_status == "diagnosed_only"
    assert fake_client.calls[1] == (
        "read_serial",
        {"read_seconds": 1.0, "expected_text": "boot ok", "reset_on_open": True},
    )


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

    monkeypatch.setattr(r11, "_prepare_case", lambda _case: prepared)
    monkeypatch.setattr(r11, "_prepare_target_state", lambda _prepared: None)
    monkeypatch.setattr(
        r11,
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
        r11,
        "_changed_files",
        lambda _before, _after: (),
    )
    monkeypatch.setattr(
        r12_benchmark,
        "load_provider_config",
        lambda *_args: type(
            "Cfg",
            (),
            {"api_key": "key", "model": "gpt-test", "provider": "openai-api"},
        )(),
    )
    async def fake_run_turnkey_with_provider(
        _invocation: object, *, provider_config: object, event_sink: object | None = None
    ) -> TurnkeyExecution:
        return TurnkeyExecution(
            invocation=replace(
                build_turnkey_invocation(
                    mode="benchmark",
                    provider="openai-api",
                    board_id=case.board_id,
                    task="task",
                    model="gpt-test",
                    max_iters=4,
                    serial_read_seconds=1.0,
                ),
                case_id=case.case_id,
            ),
            board=board,
            result=TurnkeyRunResult(
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
            brain_events=(),
        )

    monkeypatch.setattr(r12_benchmark, "run_turnkey_with_provider", fake_run_turnkey_with_provider)

    report = anyio.run(
        lambda: r12_benchmark.run_case_async(
            case.case_id,
            provider="openai-api",
            model="gpt-test",
        )
    )

    assert report.score_report.score == 100
    assert (run_root / "run-metadata" / "benchmark_case.json").exists()
    assert (run_root / "run-metadata" / "benchmark_result.json").exists()
    assert (run_root / "run-metadata" / "score.json").exists()
    assert (run_root / "run-metadata" / "firmware_identity.json").exists()


def test_r12_benchmark_falls_back_to_single_new_session_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = r11.load_case("nucleo_l476rg__k001_reference_green")
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
    (run_root / "run-metadata" / "session.json").write_text(
        json.dumps({"session_id": run_root.name, "board_id": case.board_id}),
        encoding="utf-8",
    )

    monkeypatch.setattr(r11, "_prepare_case", lambda _case: prepared)
    monkeypatch.setattr(r11, "_prepare_target_state", lambda _prepared: None)
    monkeypatch.setattr(
        r11,
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
    monkeypatch.setattr(r11, "_changed_files", lambda _before, _after: ())
    session_dir_snapshots = iter(({}, {run_root.name: run_root}))
    monkeypatch.setattr(r11, "_session_dirs", lambda: next(session_dir_snapshots))
    monkeypatch.setattr(
        r12_benchmark,
        "load_provider_config",
        lambda *_args: type(
            "Cfg",
            (),
            {"api_key": "key", "model": "gpt-test", "provider": "openai-api"},
        )(),
    )

    async def fake_run_turnkey_with_provider(
        _invocation: object, *, provider_config: object, event_sink: object | None = None
    ) -> TurnkeyExecution:
        return TurnkeyExecution(
            invocation=replace(
                build_turnkey_invocation(
                    mode="benchmark",
                    provider="openai-api",
                    board_id=case.board_id,
                    task="task",
                    model="gpt-test",
                    max_iters=4,
                    serial_read_seconds=1.0,
                ),
                case_id=case.case_id,
            ),
            board=board,
            result=TurnkeyRunResult(
                case_id=case.case_id,
                board_id=case.board_id,
                session_id=None,
                final_status="healthy_confirmed",
                classification="healthy",
                root_cause="No issue found.",
                actions_taken=["connect", "run_green_check"],
                mcp_tools_used=["connect", "run_green_check"],
                files_changed=[],
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
                session_id=None,
                session_ids_seen=[],
            ),
            run_root=None,
            prompt_text="prompt",
            request_payload={"board_id": case.board_id},
            selected_skills=(),
            model_turns=(),
            brain_trace=(),
            brain_events=(),
        )

    monkeypatch.setattr(r12_benchmark, "run_turnkey_with_provider", fake_run_turnkey_with_provider)

    report = anyio.run(
        lambda: r12_benchmark.run_case_async(
            case.case_id,
            provider="openai-api",
            model="gpt-test",
        )
    )

    assert report.session_id == run_root.name
    assert report.score_report.score == 100
    assert report.run_root == run_root


def test_r12_benchmark_task_uses_turnkey_contract() -> None:
    case = r11.load_case("nucleo_l476rg__k001_reference_green")

    task = r12_benchmark._render_case_task(case)

    assert "Case title:" in task
    assert "run_green_check" in task
    assert "read_symbol_u32" in task
    assert "do not expect `read_symbol_u32` to exist as a direct tool" in task
    assert "connect with `connect(board_id=...)`" in task
    assert "do not pass a generic target override such as `cortex_m`" in task
    assert "prefer `flash_firmware()` with no explicit path" in task
    assert "use relative workspace paths such as `src/src/main.c`" in task
    assert "if `run_green_check` fails, stay on the current session instead of reconnecting" in task


def test_r12_benchmark_task_guides_minimal_b001_repair() -> None:
    case = r11.load_case("nucleo_l476rg__b001_wrong_boot_text")

    task = r12_benchmark._render_case_task(case)

    assert "expected changed files: src/src/main.c" in task
    assert "smallest source change" in task
    assert "prefer surgical edits to the existing source over whole-file rewrites" in task
    assert "preserve `stage1_known_value = 0x1234ABCD`" in task
    assert "keep `stage1_known_value` as the flash-backed `const uint32_t ...` declaration" in task
    assert "do not convert `stage1_known_value` into a RAM-backed mutable/volatile variable" in task
    assert "fix the UART print path only" in task
    assert "keep the existing loop and the live `*(const volatile uint32_t *)&stage1_known_value` read intact" in task
    assert "keep the exact `const uint32_t stage1_known_value = 0x1234ABCD;` declaration form" in task
    assert "restore the application success text from `boot nope` to `boot ok`" in task


def test_prepare_workspace_session_allows_absolute_edit_path_within_allowed_root(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    source = workspace_root / "src" / "src" / "main.c"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("boot nope\n", encoding="utf-8")

    session = prepare_workspace_session(
        workspace_root=workspace_root,
        allowed_edit_roots=("src",),
        build_command="true",
        code_edits_allowed=True,
        label="absolute-edit",
        copy_workspace=False,
    )

    session.replace_file(str(source.resolve()), "boot ok\n")

    assert source.read_text(encoding="utf-8") == "boot ok\n"


def test_r12_benchmark_task_guides_b003_to_preserve_live_symbol_path() -> None:
    case = r11.load_case("nrf52833dk__b003_silent_uart")

    task = r12_benchmark._render_case_task(case)

    assert "missing application success UART" in task
    assert "flash-backed `const uint32_t ...` declaration" in task
    assert "keep the existing loop and live `stage1_known_value` read intact" in task
    assert "keep the exact `const uint32_t stage1_known_value = 0x1234ABCD;` declaration form" in task


def test_turnkey_cli_uses_higher_default_iteration_budget_for_benchmarks() -> None:
    args = build_turnkey_cli_parser().parse_args(["benchmark", "--case-id", "nrf52833dk__b003_silent_uart"])

    assert args.max_iters == 18


def test_module_benchmark_cli_accepts_planning_hook_arguments() -> None:
    args = r12_benchmark.build_parser().parse_args(
        [
            "case",
            "--case-id",
            "nrf52833dk__k001_reference_green",
            "--timeout-config-json",
            "{\"default_tool_seconds\": 19.0}",
            "--timeout-proposal-json",
            "{\"provider_seconds\": 120.0}",
            "--iteration-estimate-json",
            "{\"requested_max_iterations\": 6}",
        ]
    )

    assert args.timeout_config_json == "{\"default_tool_seconds\": 19.0}"
    assert args.timeout_proposal_json == "{\"provider_seconds\": 120.0}"
    assert args.iteration_estimate_json == "{\"requested_max_iterations\": 6}"


def test_module_benchmark_cli_threads_planning_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        r12_benchmark,
        "load_provider_config",
        lambda model, provider: BrainProviderConfig(provider="codex-cli", model=model),
    )

    def _fake_run_case(case_id: str, **kwargs: object) -> SimpleNamespace:
        captured["case_id"] = case_id
        captured.update(kwargs)
        return SimpleNamespace(
            score_report=SimpleNamespace(outcome_label="full_success", score=100),
            case_id=case_id,
            session_id="sess-1",
        )

    monkeypatch.setattr(r12_benchmark, "run_case", _fake_run_case)
    monkeypatch.setattr(r11, "print_case_summary", lambda _report: None)

    exit_code = r12_benchmark.main(
        [
            "case",
            "--case-id",
            "nrf52833dk__k001_reference_green",
            "--timeout-config-json",
            "{\"default_tool_seconds\": 19.0}",
            "--timeout-proposal-json",
            "{\"provider_seconds\": 120.0}",
            "--iteration-estimate-json",
            "{\"requested_max_iterations\": 6}",
        ]
    )

    assert exit_code == 0
    assert captured["case_id"] == "nrf52833dk__k001_reference_green"
    timeout_config = captured["timeout_config"]
    assert isinstance(timeout_config, TurnkeyTimeoutConfig)
    assert timeout_config.default_tool_seconds == 19.0
    assert captured["timeout_proposal"] == TimeoutProposal(provider_seconds=120.0)
    assert captured["iteration_estimate"] == IterationEstimate(requested_max_iterations=6)


def test_codex_cli_command_uses_output_schema_and_temp_workspace(tmp_path: Path) -> None:
    command = _build_codex_command(
        model="gpt-5.5",
        working_dir=tmp_path,
        output_path=tmp_path / "out.json",
    )
    assert command[:6] == ["codex", "-a", "never", "-s", "danger-full-access", "exec"]
    assert "-o" in command
    assert "--model" in command
    assert "gpt-5.5" in command
    assert "-C" in command
    assert str(tmp_path) in command
    assert command[-1] == "-"


def test_claude_cli_command_supports_optional_model() -> None:
    command = _build_claude_command(
        model="claude-sonnet-4-20250514",
        instructions="system",
        prompt="prompt",
    )
    assert command[:4] == ["claude", "--print", "--output-format", "json"]
    assert "--append-system-prompt" in command
    assert "--model" in command
    assert "claude-sonnet-4-20250514" in command


def test_claude_output_extractor_surfaces_provider_error() -> None:
    result = subprocess.CompletedProcess(
        args=["claude"],
        returncode=1,
        stdout=json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": True,
                "result": "API Error: 404 {\"type\":\"error\",\"error\":{\"type\":\"not_found_error\",\"message\":\"model: claude-sonnet-4-20250514\"}}",
            }
        ),
        stderr="",
    )

    output_text, error = _extract_claude_output_text(result)

    assert output_text == ""
    assert error is not None
    assert "not_found_error" in str(error)
