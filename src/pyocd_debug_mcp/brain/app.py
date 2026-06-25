"""Shared invocation helpers for the headless brain CLI and the operator shell."""

from __future__ import annotations

from collections.abc import Sequence

from pyocd_debug_mcp import benchmark_support as benchmark_support
from pyocd_debug_mcp.brain import benchmark as r12_benchmark
from pyocd_debug_mcp.brain.config import (
    TurnkeyMemoryMode,
    TurnkeyProviderKind,
    build_turnkey_invocation,
    load_provider_config,
)
from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.brain.events import EventSink
from pyocd_debug_mcp.brain.loop import TurnkeyExecution, run_turnkey_with_provider
from pyocd_debug_mcp.timeouts import TurnkeyTimeoutConfig


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
    memory_mode: TurnkeyMemoryMode | None = None,
    native_sync_every: int | None = None,
    workspace_root: str | None = None,
    build_command: str | None = None,
    event_sink: EventSink | None = None,
    timeout_config: TurnkeyTimeoutConfig | None = None,
    timeout_proposal: TimeoutProposal | None = None,
    iteration_estimate: IterationEstimate | None = None,
) -> TurnkeyExecution:
    if timeout_config is None:
        provider_config = load_provider_config(model, provider)
    else:
        provider_config = load_provider_config(
            model,
            provider,
            provider_timeout_seconds=timeout_config.provider_seconds,
        )
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider=provider_config.provider,
        board_id=board_id,
        task=task,
        model=provider_config.model,
        max_iters=max_iters,
        serial_read_seconds=serial_read_seconds,
        memory_mode=memory_mode,
        native_sync_every=native_sync_every,
        port=port,
        flash_artifact=flash_artifact,
        elf=elf,
        workspace_root=workspace_root,
        build_command=build_command,
        code_edits_allowed=bool(workspace_root and build_command),
        allowed_edit_roots=(),
        recover_allowed=True,
        timeout_config=timeout_config,
        timeout_proposal=timeout_proposal,
        iteration_estimate=iteration_estimate,
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
    serial_read_seconds: float = benchmark_support.DEFAULT_SERIAL_READ_SECONDS,
    memory_mode: TurnkeyMemoryMode | None = None,
    native_sync_every: int | None = None,
    event_sink: EventSink | None = None,
    timeout_config: TurnkeyTimeoutConfig | None = None,
    timeout_proposal: TimeoutProposal | None = None,
    iteration_estimate: IterationEstimate | None = None,
) -> benchmark_support.CaseRunReport:
    if timeout_config is None:
        provider_config = load_provider_config(model, provider)
    else:
        provider_config = load_provider_config(
            model,
            provider,
            provider_timeout_seconds=timeout_config.provider_seconds,
        )
    return r12_benchmark.run_case(
        case_id,
        provider=provider_config.provider,
        model=provider_config.model,
        max_iters=max_iters,
        serial_read_seconds=serial_read_seconds,
        memory_mode=memory_mode,
        native_sync_every=native_sync_every,
        event_sink=event_sink,
        timeout_config=timeout_config,
        timeout_proposal=timeout_proposal,
        iteration_estimate=iteration_estimate,
    )


def run_benchmark_suite(
    *,
    suite_name: str,
    provider: TurnkeyProviderKind | None = None,
    model: str | None = None,
    max_iters: int = r12_benchmark.DEFAULT_MAX_ITERS,
    serial_read_seconds: float = benchmark_support.DEFAULT_SERIAL_READ_SECONDS,
    memory_mode: TurnkeyMemoryMode | None = None,
    native_sync_every: int | None = None,
    event_sink: EventSink | None = None,
    timeout_config: TurnkeyTimeoutConfig | None = None,
    timeout_proposal: TimeoutProposal | None = None,
    iteration_estimate: IterationEstimate | None = None,
) -> list[benchmark_support.CaseRunReport]:
    if timeout_config is None:
        provider_config = load_provider_config(model, provider)
    else:
        provider_config = load_provider_config(
            model,
            provider,
            provider_timeout_seconds=timeout_config.provider_seconds,
        )
    reports: list[benchmark_support.CaseRunReport] = []
    for case in benchmark_support.load_suite(suite_name):
        reports.append(
            r12_benchmark.run_case(
                case.case_id,
                provider=provider_config.provider,
                model=provider_config.model,
                max_iters=max_iters,
                serial_read_seconds=serial_read_seconds,
                memory_mode=memory_mode,
                native_sync_every=native_sync_every,
                event_sink=event_sink,
                timeout_config=timeout_config,
                timeout_proposal=timeout_proposal,
                iteration_estimate=iteration_estimate,
            )
        )
    return reports


def benchmark_case_ids(suite_name: str) -> Sequence[str]:
    return tuple(case.case_id for case in benchmark_support.load_suite(suite_name))
