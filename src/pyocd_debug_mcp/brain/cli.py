"""CLI entrypoint for the R12 turnkey brain."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
from typing import Any, cast

import anyio

from pyocd_debug_mcp import benchmark_support as benchmark_support
from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.app import run_benchmark_case, run_benchmark_suite, run_freeform_task
from pyocd_debug_mcp.brain.config import BrainConfigError
from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.brain.loop import TurnkeyExecution
from pyocd_debug_mcp.timeouts import (
    TurnkeyTimeoutConfig,
    TurnkeyTimeoutUpdate,
    apply_turnkey_timeout_update,
    default_turnkey_timeout_config,
)


def _parse_json_object(raw: str, *, flag_name: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BrainConfigError(f"{flag_name} must be valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise BrainConfigError(f"{flag_name} must decode to a JSON object.")
    return payload


def _parse_timeout_config_json(raw: str | None) -> TurnkeyTimeoutConfig | None:
    if raw is None:
        return None
    payload = _parse_json_object(raw, flag_name="--timeout-config-json")
    allowed_fields = {field.name for field in fields(TurnkeyTimeoutUpdate)}
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise BrainConfigError(
            "--timeout-config-json contains unsupported keys: " + ", ".join(unknown_fields)
        )
    try:
        update = TurnkeyTimeoutUpdate(**cast(dict[str, Any], payload))
        return apply_turnkey_timeout_update(default_turnkey_timeout_config(), update)
    except (TypeError, ValueError) as exc:
        raise BrainConfigError(f"--timeout-config-json is invalid: {exc}") from exc


def _parse_timeout_proposal_json(raw: str | None) -> TimeoutProposal | None:
    if raw is None:
        return None
    payload = _parse_json_object(raw, flag_name="--timeout-proposal-json")
    try:
        return TimeoutProposal.model_validate(payload)
    except Exception as exc:
        raise BrainConfigError(f"--timeout-proposal-json is invalid: {exc}") from exc


def _parse_iteration_estimate_json(raw: str | None) -> IterationEstimate | None:
    if raw is None:
        return None
    payload = _parse_json_object(raw, flag_name="--iteration-estimate-json")
    try:
        return IterationEstimate.model_validate(payload)
    except Exception as exc:
        raise BrainConfigError(f"--iteration-estimate-json is invalid: {exc}") from exc


def _add_planning_hook_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--timeout-config-json",
        help="Optional JSON object of turnkey timeout overrides applied over repo defaults.",
    )
    parser.add_argument(
        "--timeout-proposal-json",
        help="Optional JSON object carrying the future model timeout proposal shape.",
    )
    parser.add_argument(
        "--iteration-estimate-json",
        help="Optional JSON object carrying the future model iteration-estimate shape.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one turnkey freeform task.")
    run_parser.add_argument("--board-id", required=True)
    run_parser.add_argument("--task", required=True)
    run_parser.add_argument("--provider")
    run_parser.add_argument("--model")
    run_parser.add_argument("--port")
    run_parser.add_argument("--flash-artifact")
    run_parser.add_argument("--elf")
    run_parser.add_argument("--max-iters", type=int, default=12)
    run_parser.add_argument("--serial-read-seconds", type=float, default=3.0)
    run_parser.add_argument("--workspace-root")
    run_parser.add_argument("--build-command")
    _add_planning_hook_arguments(run_parser)

    benchmark_parser = subparsers.add_parser("benchmark", help="Run turnkey benchmark cases.")
    benchmark_group = benchmark_parser.add_mutually_exclusive_group(required=True)
    benchmark_group.add_argument("--case-id")
    benchmark_group.add_argument("--suite")
    benchmark_parser.add_argument("--provider")
    benchmark_parser.add_argument("--model")
    benchmark_parser.add_argument("--max-iters", type=int, default=18)
    benchmark_parser.add_argument("--serial-read-seconds", type=float, default=3.0)
    _add_planning_hook_arguments(benchmark_parser)
    return parser


def _print_execution(execution: TurnkeyExecution) -> None:
    result = execution.result
    verification = result.verification
    print(
        f"[{result.final_status.upper()}] board={result.board_id} "
        f"session_id={result.session_id or '(none)'}"
    )
    print(f"classification: {result.classification}")
    print(f"summary: {result.summary}")
    print(f"root_cause: {result.root_cause}")
    print(
        "verification: "
        f"flash_ok={verification.flash_ok} "
        f"uart_ok={verification.uart_ok} "
        f"symbol_ok={verification.symbol_ok} "
        f"green_check_ok={verification.green_check_ok}"
    )
    if execution.run_root is not None:
        print(f"run_root: {execution.run_root}")


async def _run_freeform(args: argparse.Namespace) -> TurnkeyExecution:
    timeout_config = _parse_timeout_config_json(args.timeout_config_json)
    timeout_proposal = _parse_timeout_proposal_json(args.timeout_proposal_json)
    iteration_estimate = _parse_iteration_estimate_json(args.iteration_estimate_json)
    return await run_freeform_task(
        board_id=args.board_id,
        task=args.task,
        provider=args.provider,
        model=args.model,
        max_iters=args.max_iters,
        serial_read_seconds=args.serial_read_seconds,
        port=args.port,
        flash_artifact=args.flash_artifact,
        elf=args.elf,
        workspace_root=args.workspace_root,
        build_command=args.build_command,
        timeout_config=timeout_config,
        timeout_proposal=timeout_proposal,
        iteration_estimate=iteration_estimate,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            execution = anyio.run(_run_freeform, args)
            _print_execution(execution)
            return 0 if execution.result.final_status in {"fixed", "healthy_confirmed", "diagnosed_only"} else 1

        timeout_config = _parse_timeout_config_json(args.timeout_config_json)
        timeout_proposal = _parse_timeout_proposal_json(args.timeout_proposal_json)
        iteration_estimate = _parse_iteration_estimate_json(args.iteration_estimate_json)
        if args.case_id:
            report = run_benchmark_case(
                case_id=args.case_id,
                provider=args.provider,
                model=args.model,
                max_iters=args.max_iters,
                serial_read_seconds=args.serial_read_seconds,
                timeout_config=timeout_config,
                timeout_proposal=timeout_proposal,
                iteration_estimate=iteration_estimate,
            )
            benchmark_support.print_case_summary(report)
            return 0 if report.score_report.outcome_label == "full_success" else 1

        reports = run_benchmark_suite(
            suite_name=args.suite,
            provider=args.provider,
            model=args.model,
            max_iters=args.max_iters,
            serial_read_seconds=args.serial_read_seconds,
            timeout_config=timeout_config,
            timeout_proposal=timeout_proposal,
            iteration_estimate=iteration_estimate,
        )
        for report in reports:
            benchmark_support.print_case_summary(report)
        benchmark_support.print_suite_summary(args.suite, reports)
        return 0 if r12_benchmark._suite_acceptance(args.suite, reports) else 1
    except BrainConfigError as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
