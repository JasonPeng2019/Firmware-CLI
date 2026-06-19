from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.harness import r11_benchmark as r11


def load_fixture_result(name: str) -> r11.ParsedAgentResult:
    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "r11_results" / f"{name}.json"
    )
    return r11._parse_agent_result(fixture_path)


def test_all_r11_case_manifests_load() -> None:
    cases = []
    for case_dir in sorted(path for path in r11.CASES_ROOT.iterdir() if path.is_dir()):
        if (case_dir / "case.yaml").exists():
            cases.append(r11.load_case(case_dir.name))

    assert len(cases) == 8
    assert {case.scoring_profile for case in cases} == {r11.DEFAULT_SCORING_PROFILE}


def test_pilot_suite_loads_in_frozen_order() -> None:
    cases = r11.load_suite("pilot_v1")

    assert [case.case_id for case in cases] == [
        "nucleo_l476rg__k001_reference_green",
        "nrf52833dk__k001_reference_green",
        "nucleo_l476rg__b001_wrong_boot_text",
        "nrf52833dk__b001_wrong_boot_text",
        "nucleo_l476rg__b002_wrong_known_value",
        "nrf52833dk__b002_wrong_known_value",
        "nucleo_l476rg__f001_halted_target_silent_uart",
        "nrf52833dk__f001_halted_target_silent_uart",
    ]


def test_r11_result_schema_golden_samples_parse() -> None:
    fixed = load_fixture_result("fixed_success")
    partial = load_fixture_result("diagnosed_only_partial")
    blocked = load_fixture_result("blocked_failure")

    assert fixed.final_status == "fixed"
    assert partial.final_status == "diagnosed_only"
    assert blocked.final_status == "blocked"


def test_score_full_success_for_code_bug_case() -> None:
    case = r11.load_case("nrf52833dk__b001_wrong_boot_text")
    result = load_fixture_result("fixed_success")
    verification = r11.VerificationSummary(
        flash_ok=True,
        uart_ok=True,
        symbol_ok=True,
        green_check_ok=True,
        excerpt="boot ok",
        error_text=None,
    )

    score = r11._score_case(case, result, verification, ("src/src/main.c",))

    assert score.score == 100
    assert score.outcome_label == "full_success"


def test_score_diagnosed_only_partial_case() -> None:
    case = r11.load_case("nucleo_l476rg__b001_wrong_boot_text")
    result = load_fixture_result("diagnosed_only_partial")
    verification = r11.VerificationSummary(
        flash_ok=False,
        uart_ok=False,
        symbol_ok=False,
        green_check_ok=False,
        excerpt="",
        error_text="stage1 smoke failed",
    )

    score = r11._score_case(case, result, verification, ())

    assert score.score == 70
    assert score.outcome_label == "partial_success"


def test_score_unnecessary_recover_penalty() -> None:
    case = r11.load_case("nrf52833dk__k001_reference_green")
    result = load_fixture_result("fixed_success")
    result = r11.ParsedAgentResult(
        case_id=case.case_id,
        board_id=case.board_id,
        session_id=result.session_id,
        final_status="healthy_confirmed",
        classification="healthy",
        root_cause="No issue found.",
        actions_taken=result.actions_taken,
        mcp_tools_used=result.mcp_tools_used,
        files_changed=(),
        recover_used=True,
        verification=result.verification,
        summary="Used recover unnecessarily.",
    )
    verification = r11.VerificationSummary(
        flash_ok=True,
        uart_ok=True,
        symbol_ok=True,
        green_check_ok=True,
        excerpt="boot ok",
        error_text=None,
    )

    score = r11._score_case(case, result, verification, ())

    assert score.score == 75
    assert "unnecessary-recover:-25" in score.penalties


def test_score_wrong_diagnosis_cap() -> None:
    case = r11.load_case("nrf52833dk__b001_wrong_boot_text")
    result = load_fixture_result("fixed_success")
    result = r11.ParsedAgentResult(
        case_id=result.case_id,
        board_id=result.board_id,
        session_id=result.session_id,
        final_status=result.final_status,
        classification="physical_fault",
        root_cause=result.root_cause,
        actions_taken=result.actions_taken,
        mcp_tools_used=result.mcp_tools_used,
        files_changed=result.files_changed,
        recover_used=result.recover_used,
        verification=result.verification,
        summary=result.summary,
    )
    verification = r11.VerificationSummary(
        flash_ok=True,
        uart_ok=True,
        symbol_ok=True,
        green_check_ok=True,
        excerpt="boot ok",
        error_text=None,
    )

    score = r11._score_case(case, result, verification, ("src/src/main.c",))

    assert score.score == 60
    assert "wrong-diagnosis-cap:60" in score.penalties


def test_score_blocked_case_caps_at_40() -> None:
    case = r11.load_case("nrf52833dk__f001_halted_target_silent_uart")
    result = load_fixture_result("blocked_failure")
    verification = r11.VerificationSummary(
        flash_ok=False,
        uart_ok=False,
        symbol_ok=False,
        green_check_ok=False,
        excerpt="",
        error_text="watcher blocked the run",
    )

    score = r11._score_case(case, result, verification, ())

    assert score.score == 40
    assert score.outcome_label == "fail"


def test_prepare_workspace_keeps_tracked_bug_fixture_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(r11, "WORKSPACES_ROOT", tmp_path / "workspaces")
    case = r11.load_case("nrf52833dk__b001_wrong_boot_text")
    workspace = r11._prepare_workspace(case)
    original_source = workspace.source_root / "src" / "src" / "main.c"
    copied_source = workspace.workspace_root / "src" / "src" / "main.c"
    copied_source.write_text("changed\n", encoding="utf-8")

    assert "boot nope" in original_source.read_text(encoding="utf-8")
    assert copied_source.read_text(encoding="utf-8") == "changed\n"


def test_record_case_artifacts_writes_expected_files(tmp_path: Path) -> None:
    case = r11.load_case("nrf52833dk__b001_wrong_boot_text")
    board = r11._load_board(case.board_id)
    workspace_root = tmp_path / "workspace"
    snapshot_root = tmp_path / "snapshot"
    workspace_root.mkdir()
    snapshot_root.mkdir()
    (workspace_root / "src").mkdir()
    (snapshot_root / "src").mkdir()
    (workspace_root / "src" / "file.txt").write_text("after\n", encoding="utf-8")
    (snapshot_root / "src" / "file.txt").write_text("before\n", encoding="utf-8")
    flash_artifact = workspace_root / "firmware.hex"
    symbol_artifact = workspace_root / "firmware.elf"
    flash_artifact.write_text("hex", encoding="utf-8")
    symbol_artifact.write_text("elf", encoding="utf-8")
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("prompt", encoding="utf-8")
    result_path = tmp_path / "result.json"
    result = load_fixture_result("fixed_success")
    result_path.write_text(json.dumps(result.__dict__), encoding="utf-8")

    prepared = r11.PreparedCase(
        case=case,
        board=board,
        workspace=r11.PreparedWorkspace(
            source_root=workspace_root,
            workspace_root=workspace_root,
            snapshot_root=snapshot_root,
        ),
        probe_uid="probe-123",
        flash_artifact=flash_artifact,
        symbol_artifact=symbol_artifact,
    )
    codex_run = r11.CodexRunArtifacts(
        exit_code=0,
        stdout_text='{"event":"done"}\n',
        stderr_text="",
        result_path=result_path,
        prompt_path=prompt_path,
        new_session_dirs=(tmp_path / "20260618T000000Z-deadbeef",),
    )
    run_root = codex_run.new_session_dirs[0]
    (run_root / "logs").mkdir(parents=True)
    (run_root / "run-metadata").mkdir(parents=True)
    verification = r11.VerificationSummary(
        flash_ok=True,
        uart_ok=True,
        symbol_ok=True,
        green_check_ok=True,
        excerpt="boot ok",
        error_text=None,
    )
    score = r11.ScoreReport(
        score=100,
        outcome_label="full_success",
        diagnosis_points=40,
        intervention_points=25,
        verification_points=25,
        safety_points=10,
        penalties=(),
        reasons=(),
        actual_changed_files=("src/file.txt",),
        classification_correct=True,
        intervention_correct=True,
    )

    r11._record_case_artifacts(prepared, result, codex_run, verification, score, run_root)

    assert (run_root / "run-metadata" / "benchmark_case.json").exists()
    assert (run_root / "run-metadata" / "benchmark_result.json").exists()
    assert (run_root / "run-metadata" / "score.json").exists()
    assert (run_root / "run-metadata" / "firmware_identity.json").exists()
    assert (run_root / "logs" / "codex_exec.jsonl").read_text(encoding="utf-8") == '{"event":"done"}\n'
    assert (run_root / "logs" / "prompt.txt").read_text(encoding="utf-8") == "prompt"
    assert (run_root / "captured-serial" / "final_excerpt.txt").read_text(encoding="utf-8") == "boot ok\n"
    assert (run_root / "applied-patches" / "agent.diff").exists()


def test_run_case_fails_when_no_session_directory_is_created(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = r11.load_case("nucleo_l476rg__k001_reference_green")
    board = r11._load_board(case.board_id)
    workspace_root = tmp_path / "workspace"
    snapshot_root = tmp_path / "snapshot"
    workspace_root.mkdir()
    snapshot_root.mkdir()
    prepared = r11.PreparedCase(
        case=case,
        board=board,
        workspace=r11.PreparedWorkspace(
            source_root=workspace_root,
            workspace_root=workspace_root,
            snapshot_root=snapshot_root,
        ),
        probe_uid="probe-123",
        flash_artifact=tmp_path / "firmware.hex",
        symbol_artifact=tmp_path / "firmware.elf",
    )
    prepared.flash_artifact.write_text("hex", encoding="utf-8")
    prepared.symbol_artifact.write_text("elf", encoding="utf-8")
    prompt_path = workspace_root / ".r11_prompt.txt"
    result_path = workspace_root / ".r11_codex_result.json"
    prompt_path.write_text("prompt", encoding="utf-8")
    result_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(r11, "_ensure_codex_registration", lambda: None)
    monkeypatch.setattr(r11, "_prepare_case", lambda _case: prepared)
    monkeypatch.setattr(r11, "_prepare_target_state", lambda _prepared: None)
    monkeypatch.setattr(
        r11,
        "_run_codex",
        lambda _case, _workspace, _prompt: r11.CodexRunArtifacts(
            exit_code=1,
            stdout_text="",
            stderr_text="failed",
            result_path=result_path,
            prompt_path=prompt_path,
            new_session_dirs=(),
        ),
    )

    report = r11.run_case(case.case_id)

    assert report.final_status == "unresolved"
    assert report.score_report.score == 0
    assert report.run_root is None
