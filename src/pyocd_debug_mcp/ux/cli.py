"""Operator-facing turnkey CLI with a richer interactive terminal UX."""

from __future__ import annotations

import argparse

import anyio

from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.app import run_benchmark_case, run_benchmark_suite, run_freeform_task
from pyocd_debug_mcp.brain.config import BrainConfigError
from pyocd_debug_mcp.ux.history import UXHistoryError, load_session_bundle, list_history
from pyocd_debug_mcp.ux.renderer import UXRenderer
from pyocd_debug_mcp.ux.shell import OperatorShell


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run one turnkey task with live rendering.")
    run_parser.add_argument("--board-id", required=True)
    run_parser.add_argument("--task", required=True)
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
    run_parser.add_argument("--raw-output", choices=["off", "final", "all"], default="final")

    benchmark_parser = subparsers.add_parser("benchmark", help="Run turnkey benchmark cases with live rendering.")
    benchmark_group = benchmark_parser.add_mutually_exclusive_group(required=True)
    benchmark_group.add_argument("--case-id")
    benchmark_group.add_argument("--suite")
    benchmark_parser.add_argument("--provider")
    benchmark_parser.add_argument("--model")
    benchmark_parser.add_argument("--max-iters", type=int, default=18)
    benchmark_parser.add_argument("--serial-read-seconds", type=float, default=3.0)
    benchmark_parser.add_argument("--memory-mode", choices=["deterministic", "model-summary"])
    benchmark_parser.add_argument("--native-sync-every", type=int)
    benchmark_parser.add_argument("--raw-output", choices=["off", "final", "all"], default="final")

    history_parser = subparsers.add_parser("history", help="List recent turnkey sessions.")
    history_parser.add_argument("--limit", type=int, default=20)

    show_parser = subparsers.add_parser("show", help="Show a saved turnkey run summary.")
    show_parser.add_argument("session_id")

    rerun_parser = subparsers.add_parser("rerun", help="Rerun a saved turnkey request in a new session.")
    rerun_parser.add_argument("session_id")
    rerun_parser.add_argument("--raw-output", choices=["off", "final", "all"], default="final")

    return parser


def _render_run(args: argparse.Namespace) -> int:
    renderer = UXRenderer(raw_output=args.raw_output)
    try:
        execution = anyio.run(
            lambda: run_freeform_task(
                board_id=args.board_id,
                task=args.task,
                provider=args.provider,
                model=args.model,
                port=args.port,
                flash_artifact=args.flash_artifact,
                elf=args.elf,
                max_iters=args.max_iters,
                serial_read_seconds=args.serial_read_seconds,
                memory_mode=args.memory_mode,
                native_sync_every=args.native_sync_every,
                workspace_root=args.workspace_root,
                build_command=args.build_command,
                event_sink=renderer.emit,
            )
        )
    except BrainConfigError as exc:
        renderer.print_error(str(exc))
        return 2
    renderer.render_execution(execution)
    return 0 if execution.result.final_status in {"fixed", "healthy_confirmed", "diagnosed_only"} else 1


def _render_benchmark(args: argparse.Namespace) -> int:
    renderer = UXRenderer(raw_output=args.raw_output)
    try:
        if args.case_id:
            report = run_benchmark_case(
                case_id=args.case_id,
                provider=args.provider,
                model=args.model,
                max_iters=args.max_iters,
                serial_read_seconds=args.serial_read_seconds,
                memory_mode=args.memory_mode,
                native_sync_every=args.native_sync_every,
                event_sink=renderer.emit,
            )
            renderer.render_case_report(report)
            return 0 if report.score_report.outcome_label == "full_success" else 1
        reports = run_benchmark_suite(
            suite_name=args.suite,
            provider=args.provider,
            model=args.model,
            max_iters=args.max_iters,
            serial_read_seconds=args.serial_read_seconds,
            memory_mode=args.memory_mode,
            native_sync_every=args.native_sync_every,
            event_sink=renderer.emit,
        )
        for report in reports:
            renderer.render_case_report(report)
        renderer.render_suite_summary(args.suite, reports)
        return 0 if r12_benchmark._suite_acceptance(args.suite, reports) else 1
    except BrainConfigError as exc:
        renderer.print_error(str(exc))
        return 2


def _show_history(limit: int) -> int:
    renderer = UXRenderer(raw_output="off")
    renderer.render_history(list_history(limit=limit))
    return 0


def _show_session(session_id: str) -> int:
    renderer = UXRenderer(raw_output="off")
    try:
        bundle = load_session_bundle(session_id)
    except UXHistoryError as exc:
        renderer.print_error(str(exc))
        return 1
    renderer.render_session_bundle(bundle)
    return 0


def _rerun_session(args: argparse.Namespace) -> int:
    renderer = UXRenderer(raw_output=args.raw_output)
    shell = OperatorShell(renderer=renderer)
    if shell.rerun_session(args.session_id):
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        return OperatorShell().run()
    if args.command == "run":
        return _render_run(args)
    if args.command == "benchmark":
        return _render_benchmark(args)
    if args.command == "history":
        return _show_history(args.limit)
    if args.command == "show":
        return _show_session(args.session_id)
    if args.command == "rerun":
        return _rerun_session(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
