#!/usr/bin/env python3
"""R12 turnkey acceptance benchmark over the product-owned turnkey runner."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyocd_debug_mcp.brain.models import TurnkeyRunRequest, TurnkeyRunResult
from pyocd_debug_mcp.brain.runner import TurnkeyRunner
from tests.harness import r11_benchmark as r11

TURNKEY_BENCHMARK_ROOT = r11.RUNS_ROOT / "_turnkey_benchmark"
TURNKEY_SCOPED_PAIR_SUITE = "turnkey_scoped_pair_v1"
TURNKEY_ALT_SUITE = "turnkey_alt_nrf52840_v1"


@dataclass(frozen=True)
class TurnkeyScoreReport:
    score: int
    outcome_label: str
    diagnosis_points: int
    intervention_points: int
    verification_points: int
    premium_points: int
    reasons: tuple[str, ...]
    classification_correct: bool
    intervention_correct: bool
    premium_advantage_ok: bool


@dataclass(frozen=True)
class TurnkeyCaseReport:
    case_id: str
    board_id: str
    skill_id: str
    final_status: str
    classification: str | None
    verification: r11.VerificationSummary
    score_report: TurnkeyScoreReport
    result_path: str | None


def load_suite(suite_name: str) -> list[r11.BenchmarkCase]:
    if suite_name not in {TURNKEY_SCOPED_PAIR_SUITE, TURNKEY_ALT_SUITE}:
        raise ValueError(f"Unsupported turnkey suite: {suite_name}")
    return r11.load_suite(suite_name)


def select_skill_id(case: r11.BenchmarkCase) -> str:
    if case.kind == "known_good":
        return "reference-health-check"
    if case.kind == "observability_fault":
        return "reference-contract-diagnose"
    if case.kind == "injected_bug":
        return "reference-contract-repair"
    raise ValueError(f"Unsupported turnkey benchmark case kind: {case.kind}")


def build_request(prepared: r11.PreparedCase) -> TurnkeyRunRequest:
    case = prepared.case
    return TurnkeyRunRequest(
        board_id=case.board_id,
        skill_id=select_skill_id(case),
        case_id=case.case_id,
        workspace_root=(
            str(prepared.workspace.workspace_root)
            if case.allowed_actions.code_edits_allowed
            else None
        ),
        flash_artifact=str(prepared.flash_artifact),
        symbol_artifact=str(prepared.symbol_artifact),
        expected_uart_substring=case.expected_observables.uart_substring,
        stage1_symbol_name=case.expected_observables.symbol_name,
        stage1_symbol_value_u32=f"0x{case.expected_observables.symbol_value_u32:08X}",
        build_command=case.allowed_actions.build_command,
        initial_post_flash_state=case.initial_prep.post_flash_state,
    )


def _premium_advantage_ok(skill_id: str, result: TurnkeyRunResult) -> bool:
    if skill_id == "reference-health-check":
        return bool(result.steps)
    return bool(
        result.observations
        and result.hypotheses
        and result.experiments
        and result.strategy_evaluations
    )


def score_case(
    case: r11.BenchmarkCase,
    skill_id: str,
    result: TurnkeyRunResult,
    verification: r11.VerificationSummary,
) -> TurnkeyScoreReport:
    classification_correct = result.classification == case.success_criteria.expected_classification
    diagnosis_points = 40 if classification_correct else 0

    expected_changed = case.success_criteria.expected_changed_files
    actual_changed = result.files_changed
    if case.success_criteria.requires_code_fix:
        intervention_correct = (
            result.final_status == "fixed"
            and actual_changed == expected_changed
            and r11._allowed_edit_paths(case, actual_changed)
        )
        intervention_points = 25 if intervention_correct else 0
    else:
        intervention_correct = actual_changed == ()
        intervention_points = 25 if intervention_correct else 0

    verification_ok = verification.green_check_ok
    if verification_ok:
        verification_points = 25
    elif any((verification.flash_ok, verification.uart_ok, verification.symbol_ok)):
        verification_points = 10
    else:
        verification_points = 0

    premium_advantage_ok = _premium_advantage_ok(skill_id, result)
    premium_points = 10 if premium_advantage_ok else 0

    reasons: list[str] = []
    if not classification_correct:
        reasons.append(
            f"expected classification '{case.success_criteria.expected_classification}', "
            f"got '{result.classification}'"
        )
    if case.success_criteria.requires_code_fix and not intervention_correct:
        reasons.append(
            f"expected changed files {list(expected_changed)}, got {list(actual_changed)}"
        )
    if not case.success_criteria.requires_code_fix and actual_changed:
        reasons.append(f"unexpected code edits: {list(actual_changed)}")
    if not verification_ok and verification.error_text:
        reasons.append(f"final verification failed: {verification.error_text}")
    if not premium_advantage_ok:
        reasons.append("premium advantage record was incomplete for this skill run")

    score = diagnosis_points + intervention_points + verification_points + premium_points
    score = max(0, min(100, score))
    outcome_label = (
        "full_success"
        if classification_correct and intervention_correct and verification_ok and premium_advantage_ok
        else ("partial_success" if score >= 50 else "fail")
    )
    return TurnkeyScoreReport(
        score=score,
        outcome_label=outcome_label,
        diagnosis_points=diagnosis_points,
        intervention_points=intervention_points,
        verification_points=verification_points,
        premium_points=premium_points,
        reasons=tuple(reasons),
        classification_correct=classification_correct,
        intervention_correct=intervention_correct,
        premium_advantage_ok=premium_advantage_ok,
    )


def run_case(case_id: str) -> TurnkeyCaseReport:
    case = r11.load_case(case_id)
    prepared = r11._prepare_case(case)
    r11._ensure_stage1_preflight(prepared.case.board_id, prepared.probe_uid)
    request = build_request(prepared)
    result = asyncio.run(TurnkeyRunner().run(request))
    verification = r11._run_final_verification(prepared)
    score_report = score_case(case, request.skill_id, result, verification)
    return TurnkeyCaseReport(
        case_id=case.case_id,
        board_id=case.board_id,
        skill_id=request.skill_id,
        final_status=result.final_status,
        classification=result.classification,
        verification=verification,
        score_report=score_report,
        result_path=result.result_path,
    )


def run_suite(suite_name: str) -> tuple[list[TurnkeyCaseReport], Path]:
    reports = [run_case(case.case_id) for case in load_suite(suite_name)]
    summary_path = _write_suite_summary(suite_name, reports)
    return reports, summary_path


def _write_suite_summary(suite_name: str, reports: list[TurnkeyCaseReport]) -> Path:
    TURNKEY_BENCHMARK_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = TURNKEY_BENCHMARK_ROOT / f"{suite_name}__{timestamp}.json"
    payload = {
        "suite_name": suite_name,
        "generated_at": timestamp,
        "reports": [
            {
                **asdict(report),
                "verification": asdict(report.verification),
                "score_report": asdict(report.score_report),
            }
            for report in reports
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def suite_acceptance(reports: list[TurnkeyCaseReport]) -> bool:
    return all(report.score_report.outcome_label == "full_success" for report in reports)


def print_case_summary(report: TurnkeyCaseReport) -> None:
    print(
        f"[{report.score_report.outcome_label.upper()}] {report.case_id} "
        f"skill={report.skill_id} score={report.score_report.score} "
        f"status={report.final_status}"
    )
    for reason in report.score_report.reasons:
        print(f"    - {reason}")


def print_suite_summary(
    suite_name: str,
    reports: list[TurnkeyCaseReport],
    summary_path: Path,
) -> None:
    average = sum(report.score_report.score for report in reports) / len(reports)
    full = sum(report.score_report.outcome_label == "full_success" for report in reports)
    partial = sum(report.score_report.outcome_label == "partial_success" for report in reports)
    failed = sum(report.score_report.outcome_label == "fail" for report in reports)
    print(
        f"\nSuite {suite_name}: full_success={full} partial_success={partial} "
        f"fail={failed} average_score={average:.1f}"
    )
    print(f"summary={summary_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case-id", help="Run exactly one turnkey benchmark case.")
    group.add_argument("--suite", help="Run a named turnkey benchmark suite.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.case_id:
        report = run_case(args.case_id)
        print_case_summary(report)
        return 0 if report.score_report.outcome_label == "full_success" else 1

    reports, summary_path = run_suite(args.suite)
    for report in reports:
        print_case_summary(report)
    print_suite_summary(args.suite, reports, summary_path)
    return 0 if suite_acceptance(reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
