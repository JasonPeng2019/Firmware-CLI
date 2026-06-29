from __future__ import annotations

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

