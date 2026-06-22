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

from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.actions import (
    FinalizeAction,
    ServerToolAction,
    TurnDecision,
    TurnkeyRunResult,
    VerificationSnapshot,
)
from pyocd_debug_mcp.brain.config import BrainConfigError, build_turnkey_invocation, load_provider_config
from pyocd_debug_mcp.brain.loop import TurnkeyExecution, run_turnkey
from pyocd_debug_mcp.brain.provider_claude_cli import (
    _build_claude_command,
    _extract_claude_output_text,
)
from pyocd_debug_mcp.brain.provider_codex_cli import _build_codex_command
from pyocd_debug_mcp.brain.mcp_client import ToolTextResult
from pyocd_debug_mcp.brain.provider_types import ProviderTurn
from pyocd_debug_mcp.brain.skills import load_skills_for_context
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain.workspace import prepare_workspace_session
from tests.harness import r11_benchmark as r11


class FakeProvider:
    def __init__(self, decisions: list[TurnDecision]) -> None:
        self._decisions = deque(decisions)

    async def next_decision(self, *, instructions: str, turn_prompt: str) -> ProviderTurn:
        decision = self._decisions.popleft()
        return ProviderTurn(
            decision=decision,
            output_text=json.dumps(decision.model_dump(mode="json")),
            response_id="resp-test",
        )


class FakeClient:
    def __init__(self, results: dict[str, list[ToolTextResult]]) -> None:
        self._results = {name: deque(items) for name, items in results.items()}
        self.calls: list[tuple[str, dict[str, object] | None]] = []

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
                )
            ],
            "disconnect": [
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
            ],
        }
    )
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop._verify_green",
        lambda *_args, **_kwargs: SimpleNamespace(
            pc=0x20000000,
            resolved_symbol=SimpleNamespace(name="stage1_known_value", value_u32=0x1234ABCD),
            capture_excerpt="boot ok",
        ),
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
            ],
            "read_serial": [
                ToolTextResult(
                    tool_name="read_serial",
                    text="UART did not match on /dev/cu.usbmodem143103 at 115200 baud via pyocd-native; expected='boot ok'; reopen_count=1; duration=2.00s; excerpt=boot nope",
                )
            ],
            "disconnect": [
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
            ],
        }
    )
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop._verify_green",
        lambda *_args, **_kwargs: SimpleNamespace(
            pc=0x08000B28,
            resolved_symbol=SimpleNamespace(name="stage1_known_value", value_u32=0x1234ABCD),
            capture_excerpt="boot ok",
        ),
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
            "disconnect": [
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
                ToolTextResult(tool_name="disconnect", text="Disconnected."),
            ],
        }
    )
    monkeypatch.setattr(
        "pyocd_debug_mcp.brain.loop._verify_green",
        lambda *_args, **_kwargs: SimpleNamespace(
            pc=0x20000000,
            resolved_symbol=SimpleNamespace(name="stage1_known_value", value_u32=0x1234ABCD),
            capture_excerpt="boot ok",
        ),
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
        _invocation: object, *, provider_config: object
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
        _invocation: object, *, provider_config: object
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


def test_r12_benchmark_task_guides_minimal_b001_repair() -> None:
    case = r11.load_case("nucleo_l476rg__b001_wrong_boot_text")

    task = r12_benchmark._render_case_task(case)

    assert "expected changed files: src/src/main.c" in task
    assert "smallest source change" in task
    assert "preserve `stage1_known_value = 0x1234ABCD`" in task
    assert "fix the UART print path only" in task


def test_codex_cli_command_uses_output_schema_and_temp_workspace(tmp_path: Path) -> None:
    command = _build_codex_command(
        model="gpt-5.5",
        working_dir=tmp_path,
        output_path=tmp_path / "out.json",
        prompt="turn prompt",
    )
    assert command[:6] == ["codex", "-a", "never", "-s", "danger-full-access", "exec"]
    assert "-o" in command
    assert "--model" in command
    assert "gpt-5.5" in command
    assert "-C" in command
    assert str(tmp_path) in command
    assert command[-1] == "turn prompt"


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
