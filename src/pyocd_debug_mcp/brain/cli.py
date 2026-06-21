"""CLI entrypoint for the R12 turnkey brain."""

from __future__ import annotations

import argparse

import anyio

from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.config import (
    BrainConfigError,
    build_turnkey_invocation,
    load_provider_config,
    task_requires_code_fix,
)
from pyocd_debug_mcp.brain.loop import TurnkeyExecution, run_turnkey_with_provider


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

    benchmark_parser = subparsers.add_parser("benchmark", help="Run turnkey benchmark cases.")
    benchmark_group = benchmark_parser.add_mutually_exclusive_group(required=True)
    benchmark_group.add_argument("--case-id")
    benchmark_group.add_argument("--suite")
    benchmark_parser.add_argument("--provider")
    benchmark_parser.add_argument("--model")
    benchmark_parser.add_argument("--max-iters", type=int, default=12)
    benchmark_parser.add_argument("--serial-read-seconds", type=float, default=3.0)
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
    provider = load_provider_config(args.model, args.provider)
    if task_requires_code_fix(args.task) and not (args.workspace_root and args.build_command):
        raise BrainConfigError(
            "Refused [turnkey/missing-workspace-context]: this task appears to require a code fix, "
            "but no --workspace-root and --build-command were supplied."
        )
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider=provider.provider,
        board_id=args.board_id,
        task=args.task,
        model=provider.model,
        max_iters=args.max_iters,
        serial_read_seconds=args.serial_read_seconds,
        port=args.port,
        flash_artifact=args.flash_artifact,
        elf=args.elf,
        workspace_root=args.workspace_root,
        build_command=args.build_command,
        code_edits_allowed=bool(args.workspace_root and args.build_command),
        allowed_edit_roots=("src",) if args.workspace_root and args.build_command else (),
        recover_allowed=True,
    )
    return await run_turnkey_with_provider(invocation, provider_config=provider)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            execution = anyio.run(_run_freeform, args)
            _print_execution(execution)
            return 0 if execution.result.final_status in {"fixed", "healthy_confirmed", "diagnosed_only"} else 1

        provider = load_provider_config(args.model, args.provider)
        if args.case_id:
            report = r12_benchmark.run_case(
                args.case_id,
                provider=provider.provider,
                model=provider.model,
                max_iters=args.max_iters,
                serial_read_seconds=args.serial_read_seconds,
            )
            from tests.harness import r11_benchmark as r11  # local import to keep product path light

            r11.print_case_summary(report)
            return 0 if report.score_report.outcome_label == "full_success" else 1

        reports = r12_benchmark.run_suite(
            args.suite,
            provider=provider.provider,
            model=provider.model,
            max_iters=args.max_iters,
            serial_read_seconds=args.serial_read_seconds,
        )
        from tests.harness import r11_benchmark as r11  # local import to keep product path light

        for report in reports:
            r11.print_case_summary(report)
        r11.print_suite_summary(args.suite, reports)
        return 0 if r12_benchmark._suite_acceptance(args.suite, reports) else 1
    except BrainConfigError as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
