from __future__ import annotations

from pathlib import Path

from pyocd_debug_mcp.brain.models import (
    Experiment,
    Hypothesis,
    Observation,
    StepResult,
    StrategyEvaluation,
    TurnkeyRunResult,
)
from tests.harness import r11_benchmark as r11
from tests.harness import r12_turnkey_benchmark as r12


def _result(
    *,
    case_id: str,
    board_id: str,
    final_status: str,
    classification: str,
    files_changed: tuple[str, ...],
) -> TurnkeyRunResult:
    return TurnkeyRunResult(
        run_id="turnkey-test",
        board_id=board_id,
        skill_id="reference-contract-repair",
        case_id=case_id,
        final_status=final_status,
        classification=classification,
        root_cause="test root cause",
        session_id="sess-123",
        workspace_root="C:/tmp/workspace",
        reference_source_root="C:/tmp/reference",
        flash_artifact="C:/tmp/fw.hex",
        symbol_artifact="C:/tmp/fw.elf",
        steps=(
            StepResult(
                step_id="connect",
                tool="connect",
                arguments={"board_id": board_id},
                timeout_seconds=45.0,
                expected_substrings=(),
                ok=True,
                duration_seconds=0.1,
                output_text="Connected",
                error=None,
            ),
        ),
        observations=(
            Observation("obs-001", "read_serial", "uart observed", "boot ok"),
        ),
        hypotheses=(
            Hypothesis("hyp-001", "reference contract healthy", "supported", ("obs-001",)),
        ),
        experiments=(
            Experiment("exp-001", "verify contract", "flash + inspect", "success"),
        ),
        strategy_evaluations=(
            StrategyEvaluation("strat-001", "chose repair", "rebuild"),
        ),
        files_changed=files_changed,
        verification={
            "flash_ok": True,
            "uart_ok": True,
            "symbol_ok": True,
            "green_check_ok": True,
        },
        warnings=(),
        result_path="C:/tmp/result.json",
    )


def test_turnkey_scoped_pair_suite_loads_in_frozen_order() -> None:
    cases = r12.load_suite(r12.TURNKEY_SCOPED_PAIR_SUITE)

    assert [case.case_id for case in cases] == [
        "nucleo_l476rg__k001_reference_green",
        "nrf52833dk__k001_reference_green",
        "nucleo_l476rg__f001_halted_target_silent_uart",
        "nrf52833dk__f001_halted_target_silent_uart",
        "nucleo_l476rg__b001_wrong_boot_text",
        "nrf52833dk__b001_wrong_boot_text",
        "nucleo_l476rg__b002_wrong_known_value",
        "nrf52833dk__b002_wrong_known_value",
        "nucleo_l476rg__b003_silent_uart",
        "nrf52833dk__b003_silent_uart",
        "nucleo_l476rg__b004_dual_signal_regression",
        "nrf52833dk__b004_dual_signal_regression",
    ]


def test_turnkey_alt_suite_loads_in_frozen_order() -> None:
    cases = r12.load_suite(r12.TURNKEY_ALT_SUITE)

    assert [case.case_id for case in cases] == [
        "nrf52840dk__k001_reference_green",
        "nrf52840dk__f001_halted_target_silent_uart",
        "nrf52840dk__b001_wrong_boot_text",
        "nrf52840dk__b002_wrong_known_value",
        "nrf52840dk__b003_silent_uart",
        "nrf52840dk__b004_dual_signal_regression",
    ]


def test_select_skill_id_routes_each_case_kind() -> None:
    assert (
        r12.select_skill_id(r11.load_case("nrf52840dk__k001_reference_green"))
        == "reference-health-check"
    )
    assert (
        r12.select_skill_id(r11.load_case("nrf52840dk__f001_halted_target_silent_uart"))
        == "reference-contract-diagnose"
    )
    assert (
        r12.select_skill_id(r11.load_case("nrf52840dk__b001_wrong_boot_text"))
        == "reference-contract-repair"
    )


def test_build_request_threads_workspace_and_build_command_for_bug_case(tmp_path: Path) -> None:
    case = r11.load_case("nrf52840dk__b001_wrong_boot_text")
    prepared = r11.PreparedCase(
        case=case,
        board=r11._load_board(case.board_id),
        workspace=r11.PreparedWorkspace(
            source_root=tmp_path / "source",
            workspace_root=tmp_path / "workspace",
            snapshot_root=tmp_path / "snapshot",
        ),
        probe_uid="probe-123",
        flash_artifact=tmp_path / "workspace" / "build" / "firmware.hex",
        symbol_artifact=tmp_path / "workspace" / "build" / "firmware.elf",
    )

    request = r12.build_request(prepared)

    assert request.skill_id == "reference-contract-repair"
    assert request.workspace_root == str(prepared.workspace.workspace_root)
    assert request.flash_artifact == str(prepared.flash_artifact)
    assert request.symbol_artifact == str(prepared.symbol_artifact)
    assert request.build_command == case.allowed_actions.build_command
    assert request.initial_post_flash_state == "running"


def test_score_case_full_success_for_repair_case() -> None:
    case = r11.load_case("nrf52840dk__b001_wrong_boot_text")
    result = _result(
        case_id=case.case_id,
        board_id=case.board_id,
        final_status="fixed",
        classification="code_bug",
        files_changed=("src/src/main.c",),
    )
    verification = r11.VerificationSummary(
        flash_ok=True,
        uart_ok=True,
        symbol_ok=True,
        green_check_ok=True,
        excerpt="boot ok",
        error_text=None,
    )

    score = r12.score_case(case, "reference-contract-repair", result, verification)

    assert score.score == 100
    assert score.outcome_label == "full_success"
