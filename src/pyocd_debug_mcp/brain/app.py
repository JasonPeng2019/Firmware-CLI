"""Shared invocation helpers for the headless brain CLI and the operator shell."""

from __future__ import annotations

from collections.abc import Sequence

from tests.harness import r11_benchmark as r11

from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.config import (
    BrainConfigError,
    TurnkeyProviderKind,
    build_turnkey_invocation,
    load_provider_config,
    task_requires_code_fix,
)
from pyocd_debug_mcp.brain.events import EventSink
from pyocd_debug_mcp.brain.loop import TurnkeyExecution, run_turnkey_with_provider


async def run_freeform_task(
    *,
    board_id: str,
    task: str,
    provider: TurnkeyProviderKind | None = None,
    model: str | None = None,
    port: str | None = None,
    flash_artifact: str | None = None,
    elf: str | None = None,
    max_iters: int = 12,
    serial_read_seconds: float = 3.0,
    workspace_root: str | None = None,
    build_command: str | None = None,
    event_sink: EventSink | None = None,
) -> TurnkeyExecution:
    provider_config = load_provider_config(model, provider)
    if task_requires_code_fix(task) and not (workspace_root and build_command):
        raise BrainConfigError(
            "Refused [turnkey/missing-workspace-context]: this task appears to require a code fix, "
            "but no --workspace-root and --build-command were supplied."
        )
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider=provider_config.provider,
        board_id=board_id,
        task=task,
        model=provider_config.model,
        max_iters=max_iters,
        serial_read_seconds=serial_read_seconds,
        port=port,
        flash_artifact=flash_artifact,
        elf=elf,
        workspace_root=workspace_root,
        build_command=build_command,
        code_edits_allowed=bool(workspace_root and build_command),
        allowed_edit_roots=("src",) if workspace_root and build_command else (),
        recover_allowed=True,
    )
    return await run_turnkey_with_provider(
        invocation,
        provider_config=provider_config,
        event_sink=event_sink,
    )


def run_benchmark_case(
    *,
    case_id: str,
    provider: TurnkeyProviderKind | None = None,
    model: str | None = None,
    max_iters: int = r12_benchmark.DEFAULT_MAX_ITERS,
    serial_read_seconds: float = r11.DEFAULT_SERIAL_READ_SECONDS,
    event_sink: EventSink | None = None,
) -> r11.CaseRunReport:
    provider_config = load_provider_config(model, provider)
    return r12_benchmark.run_case(
        case_id,
        provider=provider_config.provider,
        model=provider_config.model,
        max_iters=max_iters,
        serial_read_seconds=serial_read_seconds,
        event_sink=event_sink,
    )


def run_benchmark_suite(
    *,
    suite_name: str,
    provider: TurnkeyProviderKind | None = None,
    model: str | None = None,
    max_iters: int = r12_benchmark.DEFAULT_MAX_ITERS,
    serial_read_seconds: float = r11.DEFAULT_SERIAL_READ_SECONDS,
    event_sink: EventSink | None = None,
) -> list[r11.CaseRunReport]:
    provider_config = load_provider_config(model, provider)
    reports: list[r11.CaseRunReport] = []
    for case in r11.load_suite(suite_name):
        reports.append(
            r12_benchmark.run_case(
                case.case_id,
                provider=provider_config.provider,
                model=provider_config.model,
                max_iters=max_iters,
                serial_read_seconds=serial_read_seconds,
                event_sink=event_sink,
            )
        )
    return reports


def benchmark_case_ids(suite_name: str) -> Sequence[str]:
    return tuple(case.case_id for case in r11.load_suite(suite_name))
