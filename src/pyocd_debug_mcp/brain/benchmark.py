"""R12 turnkey benchmark runner over the native Python brain."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, replace
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

DEFAULT_MAX_ITERS = 18


def _render_case_task(case: r11.BenchmarkCase) -> str:
    lines = [
        f"You are validating benchmark case `{case.case_id}` on `{case.board_id}`.",
        f"Case title: {case.title}",
        "",
        "Use only the turnkey client's action surface. In particular:",
        "- connect with `connect(board_id=...)`",
        "- do not pass a hard-coded probe UID",
        "- do not pass a generic target override such as `cortex_m`",
        "- prefer `flash_firmware()` with no explicit path so the client uses the prepared case artifact",
        "- use relative workspace paths such as `src/src/main.c`, not absolute workspace paths",
        "- if `run_green_check` fails, stay on the current session instead of reconnecting",
        "- use `run_green_check` for the canonical final healthy verification",
        "- do not expect `read_symbol_u32` to exist as a direct tool in this client",
        "",
        "Tracked observables:",
        f"- expected UART substring: `{case.expected_observables.uart_substring}`",
        f"- expected symbol: `{case.expected_observables.symbol_name}` = 0x{case.expected_observables.symbol_value_u32:08X}",
        f"- expected classification: `{case.success_criteria.expected_classification}`",
    ]

    if case.kind == "known_good":
        lines.extend(
            [
                "",
                "This case is intended to already be healthy.",
                "- treat the workspace as read-only",
                "- gather enough evidence to confirm the healthy baseline",
                "- once healthy evidence is complete, run `run_green_check` and finalize",
                "- do not edit source files or rebuild",
            ]
        )
    elif case.kind == "injected_bug":
        lines.extend(
            [
                "",
                "This case contains an injected code bug.",
                "- diagnose the fault from board evidence plus the provided workspace",
                "- only edit files under the allowed roots",
                f"- allowed edit roots: {', '.join(case.allowed_actions.allowed_edit_roots) or '(none)'}",
                f"- expected changed files: {', '.join(case.success_criteria.expected_changed_files) or '(none)'}",
                f"- build command: {case.allowed_actions.build_command or '(none)'}",
                "- make the smallest source change that fixes the failing observable",
                "- prefer surgical edits to the existing source over whole-file rewrites when the symptom maps to one line or one local path",
                "- preserve any healthy tracked observable that is not implicated by the current symptom",
                "- keep the existing include set, loop structure, and live `stage1_known_value` read unless the case explicitly requires changing them",
                "- keep `stage1_known_value` as the flash-backed `const uint32_t ...` declaration unless the case explicitly requires changing only its literal value",
                "- do not convert `stage1_known_value` into a RAM-backed mutable/volatile variable; the green check reads it immediately after reset-and-halt",
                "- the green check requires `stage1_known_value` to remain resolvable from the ELF and readable back at `0x1234ABCD`, not just present as a source literal",
                "- after any repair, rebuild and then run `run_green_check` before finalizing",
            ]
        )
        if case.case_id.endswith("__b001_wrong_boot_text"):
            lines.extend(
                [
                    "- this case's intended fault is the application UART success text, not the known symbol contract",
                    "- preserve `stage1_known_value = 0x1234ABCD` and fix the UART print path only",
                    "- do not replace the file with a new minimal `main`; keep the existing loop and the live `*(const volatile uint32_t *)&stage1_known_value` read intact",
                    "- keep the exact `const uint32_t stage1_known_value = 0x1234ABCD;` declaration form",
                    "- the intended repair is to restore the application success text from `boot nope` to `boot ok`",
                ]
            )
        elif case.case_id.endswith("__b002_wrong_known_value"):
            lines.extend(
                [
                    "- this case's intended fault is the known symbol value, not the UART success text",
                    "- preserve the `boot ok` UART behavior and repair the symbol/value path only",
                    "- keep the declaration flash-backed and change only the literal value needed to restore `0x1234ABCD`",
                    "- keep the live `stage1_known_value` read and loop structure intact while restoring the tracked symbol value",
                ]
            )
        elif case.case_id.endswith("__b003_silent_uart"):
            lines.extend(
                [
                    "- this case's intended fault is missing application success UART, while the known symbol contract stays healthy",
                    "- restore the application UART success output without rewriting unrelated symbol logic",
                    "- keep the exact `const uint32_t stage1_known_value = 0x1234ABCD;` declaration form",
                    "- keep the existing loop and live `stage1_known_value` read intact while restoring the missing application success output",
                ]
            )
        elif case.case_id.endswith("__b004_dual_signal_regression"):
            lines.extend(
                [
                    "- this case intentionally breaks both the UART success text and the known symbol value",
                    "- restore both tracked contracts, but still prefer a minimal repair inside the expected changed file",
                    "- keep the declaration flash-backed while restoring the `stage1_known_value` literal to `0x1234ABCD`",
                    "- keep the symbol resolvable in the ELF by preserving a live `stage1_known_value` read while restoring both tracked signals",
                ]
            )
    elif case.kind == "observability_fault":
        lines.extend(
            [
                "",
                "This case is an observability/runtime-state fault, not a code bug.",
                "- do not edit source files",
                "- prefer runtime-state tools such as get_state, reset, resume, and read_serial",
                "- once the runtime state is restored, run `run_green_check` and finalize",
            ]
        )

    if not case.allowed_actions.recover_allowed:
        lines.extend(
            [
                "",
                "Policy:",
                "- `unlock_recover` is not a valid action for this case",
            ]
        )

    lines.extend(
        [
            "",
            "Final answer requirements:",
            "- return the result through the turnkey client's `finalize` action",
            "- the final classification and summary must match the observed board behavior",
        ]
    )
    return "\n".join(lines)


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

    suite_cases = {case.case_id: case for case in r11.load_suite(suite_name)}
    by_case = {report.case_id: report for report in reports}
    known_good_ids = {
        case_id
        for case_id, case in suite_cases.items()
        if case.kind == "known_good"
    }
    if not all(
        by_case.get(case_id) is not None and by_case[case_id].score_report.outcome_label == "full_success"
        for case_id in known_good_ids
    ):
        return False

    observability_ids = {
        case_id
        for case_id, case in suite_cases.items()
        if case.kind == "observability_fault"
    }
    if not all(
        by_case.get(case_id) is not None
        and by_case[case_id].score_report.outcome_label == "full_success"
        and by_case[case_id].score_report.classification_correct
        for case_id in observability_ids
    ):
        return False

    injected_bug_ids = {
        case_id
        for case_id, case in suite_cases.items()
        if case.kind == "injected_bug"
    }
    full_success_bugs = sum(
        report.score_report.outcome_label == "full_success"
        and report.case_id in injected_bug_ids
        for report in reports
    )
    required_bug_successes = max(1, math.ceil(len(injected_bug_ids) * 0.75))
    if full_success_bugs < required_bug_successes:
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
    before_session_dirs = r11._session_dirs()
    execution = await run_turnkey_with_provider(invocation, provider_config=provider_config)
    after_session_dirs = r11._session_dirs()
    new_session_roots = tuple(
        after_session_dirs[name]
        for name in sorted(set(after_session_dirs) - set(before_session_dirs))
    )

    resolved_session_id = execution.result.session_id
    run_root = execution.run_root
    if resolved_session_id is None and len(new_session_roots) == 1:
        resolved_session_id = new_session_roots[0].name
    if run_root is None and resolved_session_id is not None:
        run_root = after_session_dirs.get(resolved_session_id)
    if resolved_session_id is not None and execution.result.session_id != resolved_session_id:
        execution = replace(
            execution,
            result=execution.result.model_copy(update={"session_id": resolved_session_id}),
            run_root=run_root,
        )
    if resolved_session_id is None or run_root is None:
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

    session_ids_seen = execution.state.session_ids_seen or (
        [resolved_session_id] if resolved_session_id is not None else []
    )
    if len(session_ids_seen) != 1:
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
            session_id=resolved_session_id,
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
        session_id=resolved_session_id,
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
