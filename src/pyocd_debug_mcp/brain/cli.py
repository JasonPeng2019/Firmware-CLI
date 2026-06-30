"""CLI entrypoint for the R12 turnkey brain."""

from __future__ import annotations

import argparse

import anyio

from pyocd_debug_mcp import benchmark_support as benchmark_support
from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.app import run_benchmark_case, run_benchmark_suite, run_freeform_task
from pyocd_debug_mcp.brain.cli_parsing import (
    add_planning_hook_arguments as _add_planning_hook_arguments,
    parse_iteration_estimate_json as _parse_iteration_estimate_json,
    parse_timeout_config_json as _parse_timeout_config_json,
    parse_timeout_proposal_json as _parse_timeout_proposal_json,
)
from pyocd_debug_mcp.brain.config import BrainConfigError
from pyocd_debug_mcp.brain.loop import TurnkeyExecution
from pyocd_debug_mcp.brain.task_input import add_task_input_arguments, resolve_task_input


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one turnkey freeform task.")
    run_parser.add_argument("--board-id", required=True)
    add_task_input_arguments(run_parser)
    run_parser.add_argument("--provider")
    run_parser.add_argument("--model")
    run_parser.add_argument("--port")
    run_parser.add_argument("--flash-artifact")
    run_parser.add_argument("--elf")
    run_parser.add_argument("--max-iters", type=int, default=12)
    run_parser.add_argument("--serial-read-seconds", type=float, default=3.0)
    run_parser.add_argument("--memory-mode", choices=["deterministic", "model-summary"])
    run_parser.add_argument("--native-sync-every", type=int)
    run_parser.add_argument("--workspace-root")
    run_parser.add_argument("--build-command")
    run_parser.add_argument(
        "--client-action",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Register a session-scoped client action script. Repeatable.",
    )
    _add_planning_hook_arguments(run_parser)

    benchmark_parser = subparsers.add_parser("benchmark", help="Run turnkey benchmark cases.")
    benchmark_group = benchmark_parser.add_mutually_exclusive_group(required=True)
    benchmark_group.add_argument("--case-id")
    benchmark_group.add_argument("--suite")
    benchmark_parser.add_argument("--provider")
    benchmark_parser.add_argument("--model")
    benchmark_parser.add_argument("--max-iters", type=int, default=18)
    benchmark_parser.add_argument("--serial-read-seconds", type=float, default=3.0)
    benchmark_parser.add_argument("--memory-mode", choices=["deterministic", "model-summary"])
    benchmark_parser.add_argument("--native-sync-every", type=int)
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
    task = resolve_task_input(args)
    return await run_freeform_task(
        board_id=args.board_id,
        task=task,
        provider=args.provider,
        model=args.model,
        max_iters=args.max_iters,
        serial_read_seconds=args.serial_read_seconds,
        memory_mode=getattr(args, "memory_mode", None),
        native_sync_every=getattr(args, "native_sync_every", None),
        port=args.port,
        flash_artifact=args.flash_artifact,
        elf=args.elf,
        workspace_root=args.workspace_root,
        build_command=args.build_command,
        client_action_specs=tuple(args.client_action or ()),
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
            return (
                0
                if execution.result.final_status in {"fixed", "healthy_confirmed", "diagnosed_only"}
                else 1
            )

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
                memory_mode=args.memory_mode,
                native_sync_every=args.native_sync_every,
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
            memory_mode=args.memory_mode,
            native_sync_every=args.native_sync_every,
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
