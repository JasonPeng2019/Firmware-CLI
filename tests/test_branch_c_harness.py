from __future__ import annotations

import asyncio

from pyocd_debug_mcp.brain.mcp_client import ToolTextResult
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


def test_fail_on_skip_turns_skipped_selected_checks_into_failure() -> None:
    assert (
        branch_c_tests.main(
            [
                "--board-id",
                "nrf52833dk",
                "--skip-hardware",
                "--skip-codex",
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
