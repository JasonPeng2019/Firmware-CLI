"""R12 turnkey benchmark runner over the native Python brain."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import anyio

from pyocd_debug_mcp.brain.actions import TurnkeyRunResult
from pyocd_debug_mcp.brain.config import (
    TurnkeyProviderKind,
    build_turnkey_invocation,
    load_provider_config,
)
from pyocd_debug_mcp.brain.loop import TurnkeyExecution, run_turnkey_with_provider

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.harness import r11_benchmark as r11  # noqa: E402

DEFAULT_MAX_ITERS = 12


def _render_case_task(case: r11.BenchmarkCase) -> str:
    return case.prompt_template.format(
        board_id=case.board_id,
        case_id=case.case_id,
        build_command=case.allowed_actions.build_command or "(no local rebuild expected)",
        uart_substring=case.expected_observables.uart_substring,
        symbol_name=case.expected_observables.symbol_name,
        symbol_value_u32_hex=f"0x{case.expected_observables.symbol_value_u32:08X}",
    )


def _execution_to_agent_result(result: TurnkeyRunResult) -> r11.ParsedAgentResult:
    return r11.ParsedAgentResult(
        case_id=result.case_id or "",
        board_id=result.board_id,
        session_id=result.session_id or "",
        final_status=result.final_status,
        classification=result.classification,
        root_cause=result.root_cause,
        actions_taken=tuple(result.actions_taken),
        mcp_tools_used=tuple(result.mcp_tools_used),
        files_changed=tuple(result.files_changed),
        recover_used=result.recover_used,
        verification=result.verification.model_dump(mode="json"),
        summary=result.summary,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record_turnkey_case_artifacts(
    prepared: r11.PreparedCase,
    execution: TurnkeyExecution,
    verification: r11.VerificationSummary,
    score_report: r11.ScoreReport,
    run_root: Path,
) -> None:
    benchmark_case = {
        "case_id": prepared.case.case_id,
        "title": prepared.case.title,
        "board_id": prepared.case.board_id,
        "kind": prepared.case.kind,
        "workspace_mode": prepared.case.workspace_mode,
        "source_root": str(prepared.workspace.source_root),
        "workspace_root": str(prepared.workspace.workspace_root),
        "flash_artifact": str(prepared.flash_artifact),
        "symbol_artifact": str(prepared.symbol_artifact),
        "probe_uid": prepared.probe_uid,
    }
    firmware_identity = {
        "case_id": prepared.case.case_id,
        "board_id": prepared.case.board_id,
        "flash_artifact": str(prepared.flash_artifact),
        "symbol_artifact": str(prepared.symbol_artifact),
        "flash_artifact_sha256": r11._sha256(prepared.flash_artifact),
        "symbol_artifact_sha256": r11._sha256(prepared.symbol_artifact),
        "artifact_kind": "bug_variant" if prepared.case.kind == "injected_bug" else "reference",
        "workspace_source_root": str(prepared.workspace.source_root),
    }
    score_payload = {
        "score": score_report.score,
        "outcome_label": score_report.outcome_label,
        "diagnosis_points": score_report.diagnosis_points,
        "intervention_points": score_report.intervention_points,
        "verification_points": score_report.verification_points,
        "safety_points": score_report.safety_points,
        "penalties": list(score_report.penalties),
        "reasons": list(score_report.reasons),
        "classification_correct": score_report.classification_correct,
        "intervention_correct": score_report.intervention_correct,
        "actual_changed_files": list(score_report.actual_changed_files),
        "runner_verification": asdict(verification),
        "runner_mode": "r12_turnkey",
        "session_ids_seen": list(execution.state.session_ids_seen),
    }

    _write_json(run_root / "run-metadata" / "benchmark_case.json", benchmark_case)
    _write_json(
        run_root / "run-metadata" / "benchmark_result.json",
        execution.result.model_dump(mode="json"),
    )
    _write_json(run_root / "run-metadata" / "score.json", score_payload)
    _write_json(run_root / "run-metadata" / "firmware_identity.json", firmware_identity)


def _suite_acceptance(suite_name: str, reports: list[r11.CaseRunReport]) -> bool:
    if not reports:
        return False
    if any(report.score_report.score < 50 for report in reports):
        return False
    average = sum(report.score_report.score for report in reports) / len(reports)
    if average < 85:
        return False

    by_case = {report.case_id: report for report in reports}
    known_good_ids = {
        "nucleo_l476rg__k001_reference_green",
        "nrf52833dk__k001_reference_green",
    }
    if not all(
        by_case.get(case_id) is not None and by_case[case_id].score_report.outcome_label == "full_success"
        for case_id in known_good_ids
    ):
        return False

    observability_ids = {
        "nucleo_l476rg__f001_halted_target_silent_uart",
        "nrf52833dk__f001_halted_target_silent_uart",
    }
    if not all(
        by_case.get(case_id) is not None
        and by_case[case_id].score_report.outcome_label == "full_success"
        and by_case[case_id].score_report.classification_correct
        for case_id in observability_ids
    ):
        return False

    full_success_bugs = sum(
        report.score_report.outcome_label == "full_success"
        and "__b" in report.case_id
        for report in reports
    )
    if full_success_bugs < 6:
        return False

    return True


async def run_case_async(
    case_id: str,
    *,
    provider: TurnkeyProviderKind | None = None,
    model: str | None,
    max_iters: int = DEFAULT_MAX_ITERS,
    serial_read_seconds: float = r11.DEFAULT_SERIAL_READ_SECONDS,
) -> r11.CaseRunReport:
    case = r11.load_case(case_id)
    if case.scoring_profile != r11.DEFAULT_SCORING_PROFILE:
        raise RuntimeError(f"Unsupported scoring profile: {case.scoring_profile}")

    prepared = r11._prepare_case(case)
    r11._prepare_target_state(prepared)
    provider_config = load_provider_config(model, provider)
    invocation = build_turnkey_invocation(
        mode="benchmark",
        provider=provider_config.provider,
        board_id=case.board_id,
        task=_render_case_task(case),
        model=provider_config.model,
        max_iters=max_iters,
        serial_read_seconds=serial_read_seconds,
        flash_artifact=prepared.flash_artifact,
        elf=prepared.symbol_artifact,
        workspace_root=prepared.workspace.workspace_root,
        build_command=case.allowed_actions.build_command,
        case_id=case.case_id,
        case_kind=case.kind,
        expected_uart_substring=case.expected_observables.uart_substring,
        expected_symbol_name=case.expected_observables.symbol_name,
        expected_symbol_value_u32=case.expected_observables.symbol_value_u32,
        code_edits_allowed=case.allowed_actions.code_edits_allowed,
        allowed_edit_roots=case.allowed_actions.allowed_edit_roots,
        recover_allowed=case.allowed_actions.recover_allowed,
    )
    execution = await run_turnkey_with_provider(invocation, provider_config=provider_config)

    run_root = execution.run_root
    if execution.result.session_id is None or run_root is None:
        verification = r11.VerificationSummary(
            flash_ok=False,
            uart_ok=False,
            symbol_ok=False,
            green_check_ok=False,
            excerpt="",
            error_text="The turnkey client did not create a canonical MCP session.",
        )
        score_report = r11.ScoreReport(
            score=0,
            outcome_label="fail",
            diagnosis_points=0,
            intervention_points=0,
            verification_points=0,
            safety_points=0,
            penalties=("session-root-missing",),
            reasons=((verification.error_text,) if verification.error_text is not None else ()),
            actual_changed_files=r11._changed_files(
                prepared.workspace.snapshot_root,
                prepared.workspace.workspace_root,
            ),
            classification_correct=False,
            intervention_correct=False,
        )
        return r11.CaseRunReport(
            case_id=case.case_id,
            board_id=case.board_id,
            session_id=None,
            final_status="unresolved",
            score_report=score_report,
            verification=verification,
            run_root=None,
        )

    if len(execution.state.session_ids_seen) != 1:
        verification = r11.VerificationSummary(
            flash_ok=False,
            uart_ok=False,
            symbol_ok=False,
            green_check_ok=False,
            excerpt="",
            error_text="The turnkey client opened more than one MCP session during a benchmark case.",
        )
        score_report = r11.ScoreReport(
            score=0,
            outcome_label="fail",
            diagnosis_points=0,
            intervention_points=0,
            verification_points=0,
            safety_points=0,
            penalties=("multiple-sessions",),
            reasons=((verification.error_text,) if verification.error_text is not None else ()),
            actual_changed_files=r11._changed_files(
                prepared.workspace.snapshot_root,
                prepared.workspace.workspace_root,
            ),
            classification_correct=False,
            intervention_correct=False,
        )
        return r11.CaseRunReport(
            case_id=case.case_id,
            board_id=case.board_id,
            session_id=execution.result.session_id,
            final_status="blocked",
            score_report=score_report,
            verification=verification,
            run_root=run_root,
        )

    verification = r11._run_final_verification(prepared)
    actual_changed_files = r11._changed_files(
        prepared.workspace.snapshot_root,
        prepared.workspace.workspace_root,
    )
    agent_result = _execution_to_agent_result(execution.result)
    score_report = r11._score_case(case, agent_result, verification, actual_changed_files)
    _record_turnkey_case_artifacts(prepared, execution, verification, score_report, run_root)
    return r11.CaseRunReport(
        case_id=case.case_id,
        board_id=case.board_id,
        session_id=execution.result.session_id,
        final_status=execution.result.final_status,
        score_report=score_report,
        verification=verification,
        run_root=run_root,
    )


def run_case(
    case_id: str,
    *,
    provider: TurnkeyProviderKind | None = None,
    model: str | None,
    max_iters: int = DEFAULT_MAX_ITERS,
    serial_read_seconds: float = r11.DEFAULT_SERIAL_READ_SECONDS,
) -> r11.CaseRunReport:
    return anyio.run(
        lambda: run_case_async(
            case_id,
            provider=provider,
            model=model,
            max_iters=max_iters,
            serial_read_seconds=serial_read_seconds,
        )
    )


def run_suite(
    suite_name: str,
    *,
    provider: TurnkeyProviderKind | None = None,
    model: str | None,
    max_iters: int = DEFAULT_MAX_ITERS,
    serial_read_seconds: float = r11.DEFAULT_SERIAL_READ_SECONDS,
) -> list[r11.CaseRunReport]:
    return [
        run_case(
            case.case_id,
            provider=provider,
            model=model,
            max_iters=max_iters,
            serial_read_seconds=serial_read_seconds,
        )
        for case in r11.load_suite(suite_name)
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    case_parser = subparsers.add_parser("case", help="Run exactly one turnkey benchmark case.")
    case_parser.add_argument("--case-id", required=True)
    case_parser.add_argument("--provider", required=False)
    case_parser.add_argument("--model", required=False)
    case_parser.add_argument("--max-iters", type=int, default=DEFAULT_MAX_ITERS)
    case_parser.add_argument(
        "--serial-read-seconds",
        type=float,
        default=r11.DEFAULT_SERIAL_READ_SECONDS,
    )

    suite_parser = subparsers.add_parser("suite", help="Run a named turnkey benchmark suite.")
    suite_parser.add_argument("--suite", required=True)
    suite_parser.add_argument("--provider", required=False)
    suite_parser.add_argument("--model", required=False)
    suite_parser.add_argument("--max-iters", type=int, default=DEFAULT_MAX_ITERS)
    suite_parser.add_argument(
        "--serial-read-seconds",
        type=float,
        default=r11.DEFAULT_SERIAL_READ_SECONDS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    provider_config = load_provider_config(args.model, getattr(args, "provider", None))
    model = provider_config.model
    provider = provider_config.provider
    if args.mode == "case":
        report = run_case(
            args.case_id,
            provider=provider,
            model=model,
            max_iters=args.max_iters,
            serial_read_seconds=args.serial_read_seconds,
        )
        r11.print_case_summary(report)
        return 0 if report.score_report.outcome_label == "full_success" else 1

    reports = run_suite(
        args.suite,
        provider=provider,
        model=model,
        max_iters=args.max_iters,
        serial_read_seconds=args.serial_read_seconds,
    )
    for report in reports:
        r11.print_case_summary(report)
    r11.print_suite_summary(args.suite, reports)
    return 0 if _suite_acceptance(args.suite, reports) else 1
