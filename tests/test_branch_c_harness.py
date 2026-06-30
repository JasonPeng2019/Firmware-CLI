from __future__ import annotations

import asyncio

from pyocd_debug_mcp.brain.actions import FinalizeAction, TurnDecision
from pyocd_debug_mcp.brain.mcp_client import ToolTextResult
from pyocd_debug_mcp.brain.provider_types import ProviderTurn
from pyocd_debug_mcp.probe_inventory import ProbeInfo
from tests.harness import branch_c_tests


def test_probe_visible_uses_shared_probe_inventory(monkeypatch) -> None:
    calls: list[object] = []

    def fake_list_connected_probes(run_cmd):
        calls.append(run_cmd)
        return [
            ProbeInfo(
                uid="ABC123",
                description="CMSIS-DAP Debug Probe",
                raw="CMSIS-DAP Debug Probe ABC123",
            )
        ]

    monkeypatch.setattr(branch_c_tests, "list_connected_probes", fake_list_connected_probes)

    result = branch_c_tests.check_probe_visible(branch_c_tests.build_parser().parse_args([]))

    assert calls
    assert result.status == branch_c_tests.PASS
    assert "ABC123::CMSIS-DAP Debug Probe" in result.detail


def test_live_codex_task_uses_schema_valid_classification() -> None:
    task = branch_c_tests._live_codex_task()

    assert "classification=tooling_failure" in task
    assert "classification=other" not in task


def test_selected_providers_default_to_codex_cli() -> None:
    args = branch_c_tests.build_parser().parse_args([])

    assert branch_c_tests._selected_providers(args) == ("codex-cli",)


def test_selected_providers_support_cli_matrix_and_skip_codex() -> None:
    args = branch_c_tests.build_parser().parse_args(
        ["--provider", "codex-cli", "--provider", "claude-cli", "--skip-codex"]
    )

    assert branch_c_tests._selected_providers(args) == ("claude-cli",)


def test_fail_on_skip_turns_skipped_selected_checks_into_failure() -> None:
    assert (
        branch_c_tests.main(
            [
                "--board-id",
                "nrf52833dk",
                "--skip-hardware",
                "--skip-providers",
                "--fail-on-skip",
            ]
        )
        == 0
    )


def test_live_sync_check_halts_before_reading_core_register(monkeypatch) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self.halted = False

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def connect(self, *, board_id: str) -> ToolTextResult:
            self.calls.append(f"connect:{board_id}")
            return ToolTextResult("connect", "session_id=fake")

        async def halt(self) -> ToolTextResult:
            self.calls.append("halt")
            self.halted = True
            return ToolTextResult("halt", "halted")

        async def read_core_register(self, *, name: str) -> ToolTextResult:
            self.calls.append(f"read:{name}")
            if not self.halted:
                return ToolTextResult("read_core_register", "core is running", is_error=True)
            return ToolTextResult("read_core_register", "pc=0x08000000")

        async def sync_timeouts(self, update: object) -> ToolTextResult:
            self.calls.append("sync")
            return ToolTextResult(
                "_brain_sync_timeouts",
                '{"applied": true, "effective_server_timeouts": {"flash_program_seconds": 12.0}}',
            )

        async def disconnect(self) -> ToolTextResult:
            self.calls.append("disconnect")
            return ToolTextResult("disconnect", "disconnected")

    fake_client = FakeClient()
    monkeypatch.setattr(branch_c_tests, "LocalMCPClient", lambda: fake_client)

    result = asyncio.run(branch_c_tests._live_sync_check("nucleo_l476rg"))

    assert result.status == branch_c_tests.PASS
    assert fake_client.calls == [
        "connect:nucleo_l476rg",
        "halt",
        "read:pc",
        "sync",
        "read:pc",
        "disconnect",
    ]


def test_provider_dry_run_uses_selected_provider_factory(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        async def next_decision(
            self,
            *,
            instructions: str,
            turn_prompt: str,
            timeout_seconds: float | None = None,
        ) -> ProviderTurn:
            captured["instructions"] = instructions
            captured["turn_prompt"] = turn_prompt
            captured["timeout_seconds"] = timeout_seconds
            return ProviderTurn(
                decision=TurnDecision(
                    observation_summary="dry run",
                    classification="healthy",
                    action=FinalizeAction(
                        final_status="healthy_confirmed",
                        classification="healthy",
                        root_cause="dry run",
                        summary="dry run",
                    ),
                ),
                output_text="{}",
                response_id=None,
            )

    def fake_create_decision_provider(config):
        captured["provider"] = config.provider
        captured["model"] = config.model
        captured["config_timeout"] = config.timeout_seconds
        return FakeProvider()

    monkeypatch.setattr(branch_c_tests.shutil, "which", lambda name: f"C:/fake/{name}.exe")
    monkeypatch.setattr(branch_c_tests, "create_decision_provider", fake_create_decision_provider)
    args = branch_c_tests.build_parser().parse_args(
        [
            "--board-id",
            "nucleo_l476rg",
            "--provider",
            "claude-cli",
            "--provider-model",
            "claude-cli=sonnet",
            "--provider-timeout-seconds",
            "7",
        ]
    )

    result = branch_c_tests.check_provider_dry_run_prompt_render(args, "claude-cli")

    assert result.status == branch_c_tests.PASS
    assert result.name == "provider_dry_run_prompt_render[claude-cli]"
    assert captured["provider"] == "claude-cli"
    assert captured["model"] == "sonnet"
    assert captured["config_timeout"] == 7
    assert captured["timeout_seconds"] == 7
    assert "effective_timeouts=" in str(captured["turn_prompt"])
