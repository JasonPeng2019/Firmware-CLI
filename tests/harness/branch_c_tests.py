#!/usr/bin/env python3
"""Branch C (event spine + timeout policy) validation harness.

See markdowns/curr/branch_c_test_plan.md for what each check proves and why.
Run with: uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, get_args

from pyocd_debug_mcp.brain.actions import AllowedServerToolName, decision_schema_text
from pyocd_debug_mcp.brain.app import run_freeform_task
from pyocd_debug_mcp.brain.config import (
    BrainProviderConfig,
    TurnkeyInvocation,
    TurnkeyProviderKind,
    resolve_provider_native_skill_root,
)
from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.brain.events import EVENT_KINDS
from pyocd_debug_mcp.brain.loop import _build_full_turn_prompt, _build_instructions, load_board
from pyocd_debug_mcp.brain.mcp_client import LocalMCPClient
from pyocd_debug_mcp.brain.provider_factory import create_decision_provider
from pyocd_debug_mcp.brain.provider_types import ProviderPromptBundle, make_provider_session_state
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain.timeout_policy import apply_policy_proposals
from pyocd_debug_mcp.probe_inventory import list_connected_probes
from pyocd_debug_mcp.timeouts import (
    ServerTimeoutUpdate,
    clamp_turnkey_timeout_value,
    default_turnkey_timeout_config,
    subprocess_timeout_stream_text,
    server_timeout_update_to_record,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
DEFAULT_PROVIDER_CHECKS: tuple[TurnkeyProviderKind, ...] = ("codex-cli",)
CLI_PROVIDER_EXECUTABLES: dict[TurnkeyProviderKind, str] = {
    "codex-cli": "codex",
    "claude-cli": "claude",
}


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def header(text: str) -> None:
    print(f"\n{'=' * 70}\n  {text}\n{'=' * 70}")


def log(result: CheckResult) -> None:
    print(f"  [{result.status}] {result.name}: {result.detail}")


# ---------------------------------------------------------------------------
# 1 / 6 - hardware preconditions
# ---------------------------------------------------------------------------


def _run_pyocd_inventory_command(cmd: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["uv", "run", *cmd],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        return 127, "", "uv command not found"
    except subprocess.TimeoutExpired as exc:
        return (
            124,
            subprocess_timeout_stream_text(exc.stdout),
            f"command timed out after 30s: {' '.join(cmd)}",
        )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def check_probe_visible(args: argparse.Namespace) -> CheckResult:
    probes = list_connected_probes(_run_pyocd_inventory_command)
    if not probes:
        return CheckResult(
            "probe_visible",
            SKIP,
            "no debug probe detected by shared probe inventory; plug in the board and rerun",
        )
    probe_summary = ", ".join(f"{probe.uid or '(no uid)'}::{probe.description}" for probe in probes)
    return CheckResult("probe_visible", PASS, f"detected {len(probes)} probe(s): {probe_summary}")


def check_stage0_bringup(args: argparse.Namespace) -> CheckResult:
    port_arg = f"{args.board_id}={args.port}" if args.port else None
    bootstrap_cmd = ["uv", "run", "python", "host_bootstrap.py", "--board-id", args.board_id]
    stage0_cmd = ["uv", "run", "python", "stage0_check.py", "--board-id", args.board_id]
    if port_arg:
        bootstrap_cmd.extend(["--port", port_arg])
        stage0_cmd.extend(["--port", port_arg])

    bootstrap = subprocess.run(
        bootstrap_cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if bootstrap.returncode != 0:
        return CheckResult(
            "stage0_bringup",
            FAIL,
            f"host_bootstrap.py failed: {bootstrap.stdout[-500:]}",
        )
    stage0 = subprocess.run(
        stage0_cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if stage0.returncode != 0:
        return CheckResult(
            "stage0_bringup", FAIL, f"stage0_check.py failed: {stage0.stdout[-500:]}"
        )
    return CheckResult(
        "stage0_bringup", PASS, f"host_bootstrap + stage0_check green for {args.board_id}"
    )


def _live_provider_task() -> str:
    return (
        "First load governed tool details for connect and get_board_info. "
        "On a later provider turn, connect to the board with connect(board_id=...), "
        "call get_board_info, then finalize with final_status=unresolved, "
        "classification=tooling_failure, "
        "root_cause='dry run', summary='Branch C validation run.' "
        "Do not flash, edit files, or run a build."
    )


def _live_codex_task() -> str:
    """Compatibility helper for older tests; provider-neutral checks use `_live_provider_task`."""

    return _live_provider_task()


def _provider_check_name(provider: TurnkeyProviderKind, check_name: str) -> str:
    return f"{check_name}[{provider}]"


def _selected_providers(args: argparse.Namespace) -> tuple[TurnkeyProviderKind, ...]:
    if args.skip_providers:
        return ()
    raw_providers: tuple[TurnkeyProviderKind, ...] = tuple(args.provider or DEFAULT_PROVIDER_CHECKS)
    if args.skip_codex:
        raw_providers = tuple(provider for provider in raw_providers if provider != "codex-cli")
    return raw_providers


def _provider_executable(provider: TurnkeyProviderKind) -> str:
    return CLI_PROVIDER_EXECUTABLES[provider]


def _provider_model(args: argparse.Namespace, provider: TurnkeyProviderKind) -> str | None:
    if not args.provider_model:
        return args.model
    selected: dict[str, str] = {}
    for item in args.provider_model:
        if "=" not in item:
            raise SystemExit(f"--provider-model expects PROVIDER=MODEL, got: {item}")
        raw_provider, model = item.split("=", 1)
        normalized_provider = raw_provider.strip().lower()
        if normalized_provider not in CLI_PROVIDER_EXECUTABLES or not model.strip():
            raise SystemExit(f"--provider-model expects PROVIDER=MODEL, got: {item}")
        selected[normalized_provider] = model.strip()
    return selected.get(provider, args.model)


# ---------------------------------------------------------------------------
# 2 - timeouts.py is the single source of truth for defaults/clamp ranges
# ---------------------------------------------------------------------------


def check_timeout_defaults_and_clamp_ranges(args: argparse.Namespace) -> CheckResult:
    config = default_turnkey_timeout_config()
    if config.connect_seconds <= 0 or config.flash_seconds <= 0:
        return CheckResult(
            "timeout_defaults_and_clamp_ranges", FAIL, "non-positive default timeout"
        )

    too_high = clamp_turnkey_timeout_value("connect_seconds", 99999.0)
    too_low = clamp_turnkey_timeout_value("flash_seconds", 1.0)
    if too_high >= 99999.0 or too_low <= 1.0:
        return CheckResult(
            "timeout_defaults_and_clamp_ranges",
            FAIL,
            f"clamp did not clip out-of-range input (connect={too_high}, flash={too_low})",
        )
    return CheckResult(
        "timeout_defaults_and_clamp_ranges",
        PASS,
        f"defaults positive; clamp clipped 99999s connect -> {too_high}s, 1s flash -> {too_low}s",
    )


# ---------------------------------------------------------------------------
# 3 - timeout-admin tool must stay off the model-facing schema
# ---------------------------------------------------------------------------


def check_timeout_admin_not_model_facing(args: argparse.Namespace) -> CheckResult:
    allowed_tools = get_args(AllowedServerToolName)
    schema_text = decision_schema_text()
    leaks = [
        name
        for name in ("_brain_sync_timeouts", "sync_timeouts", "set_timeouts")
        if name in allowed_tools or name in schema_text
    ]
    if leaks:
        return CheckResult(
            "timeout_admin_not_model_facing",
            FAIL,
            f"timeout-admin surface leaked into the model-facing schema: {leaks}",
        )
    return CheckResult(
        "timeout_admin_not_model_facing",
        PASS,
        "_brain_sync_timeouts absent from AllowedServerToolName and decision_schema_text()",
    )


# ---------------------------------------------------------------------------
# 4 - Branch C must not own batch/client-action/checkpoint/inspector logic
# ---------------------------------------------------------------------------


FORBIDDEN_PATTERNS = (
    re.compile(r"\bActionBatch\b"),
    re.compile(r"\bclient_action"),
    re.compile(r"\bcheckpoint\b", re.IGNORECASE),
    re.compile(r"\binspector\b", re.IGNORECASE),
)

BRANCH_C_FILES = (
    REPO_ROOT / "src/pyocd_debug_mcp/brain/events.py",
    REPO_ROOT / "src/pyocd_debug_mcp/brain/timeout_policy.py",
    REPO_ROOT / "src/pyocd_debug_mcp/timeouts.py",
)


def check_no_overreach_into_other_branches(args: argparse.Namespace) -> CheckResult:
    hits: list[str] = []
    for path in BRANCH_C_FILES:
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                hits.append(f"{path.name}: {match.group(0)!r}")
    if hits:
        return CheckResult(
            "no_overreach_into_other_branches", FAIL, f"found out-of-scope symbols: {hits}"
        )
    return CheckResult(
        "no_overreach_into_other_branches",
        PASS,
        f"no batch/client-action/checkpoint/inspector symbols in {[p.name for p in BRANCH_C_FILES]}",
    )


# ---------------------------------------------------------------------------
# 5 - timeout_policy clamps proposals and derives a partial server update
# ---------------------------------------------------------------------------


def check_policy_clamps_and_partial_update(args: argparse.Namespace) -> CheckResult:
    base_config = default_turnkey_timeout_config()
    proposal = TimeoutProposal(connect_seconds=99999.0, flash_seconds=1.0)
    iteration_estimate = IterationEstimate(requested_max_iterations=999)

    not_connected = apply_policy_proposals(
        current_timeout_config=base_config,
        current_effective_max_iters=12,
        operator_max_iters=12,
        proposal_source="invocation",
        timeout_proposal=proposal,
        iteration_estimate=iteration_estimate,
        connected=False,
    )

    if not_connected.effective_timeout_config.connect_seconds == 99999.0:
        return CheckResult(
            "policy_clamps_and_partial_update",
            FAIL,
            "raw 99999s connect_seconds passed through unclamped",
        )
    if not_connected.effective_timeout_config.flash_seconds == 1.0:
        return CheckResult(
            "policy_clamps_and_partial_update",
            FAIL,
            "raw 1s flash_seconds passed through unclamped",
        )
    if not_connected.effective_max_iters != 12:
        return CheckResult(
            "policy_clamps_and_partial_update",
            FAIL,
            f"model's requested_max_iterations=999 overrode operator_max_iters=12 "
            f"(got effective_max_iters={not_connected.effective_max_iters})",
        )

    server_record = server_timeout_update_to_record(not_connected.server_sync_update) or {}
    if "step_instruction_seconds" in server_record:
        return CheckResult(
            "policy_clamps_and_partial_update",
            FAIL,
            "server_sync_update touched step_instruction_seconds, "
            "which is only tied to default_tool_seconds (not changed in this proposal) "
            "-- update is not partial",
        )
    if "flash_program_seconds" not in server_record:
        return CheckResult(
            "policy_clamps_and_partial_update",
            FAIL,
            "server_sync_update missing flash_program_seconds even though flash_seconds changed",
        )

    connected = apply_policy_proposals(
        current_timeout_config=base_config,
        current_effective_max_iters=12,
        operator_max_iters=12,
        proposal_source="invocation",
        timeout_proposal=proposal,
        iteration_estimate=None,
        connected=True,
    )
    if connected.server_sync_apply_now:
        return CheckResult(
            "policy_clamps_and_partial_update",
            FAIL,
            "server_sync_apply_now=True while a session is connected "
            "-- spec requires deferring sync against an open session",
        )

    return CheckResult(
        "policy_clamps_and_partial_update",
        PASS,
        f"connect_seconds clamped to {not_connected.effective_timeout_config.connect_seconds}s, "
        f"flash_seconds clamped to {not_connected.effective_timeout_config.flash_seconds}s, "
        f"effective_max_iters capped at operator's 12, server update partial "
        f"({sorted(server_record)}), sync deferred while connected",
    )


# ---------------------------------------------------------------------------
# 7 - live partial timeout sync must not mutate the open session
# ---------------------------------------------------------------------------


async def _live_sync_check(board_id: str) -> CheckResult:
    async with LocalMCPClient() as client:
        connect_result = await client.connect(board_id=board_id)
        if "session_id=" not in connect_result.text:
            return CheckResult(
                "live_sync_does_not_mutate_open_session",
                FAIL,
                f"connect did not report a session_id: {connect_result.text}",
            )

        halt_result = await client.halt()
        if halt_result.is_error:
            return CheckResult(
                "live_sync_does_not_mutate_open_session",
                FAIL,
                f"halt before baseline read failed: {halt_result.text}",
            )

        baseline = await client.read_core_register(name="pc")
        if baseline.is_error:
            return CheckResult(
                "live_sync_does_not_mutate_open_session",
                FAIL,
                f"baseline read_core_register failed: {baseline.text}",
            )

        sync_result = await client.sync_timeouts(ServerTimeoutUpdate(flash_program_seconds=12.0))
        try:
            sync_payload = json.loads(sync_result.text)
        except json.JSONDecodeError:
            return CheckResult(
                "live_sync_does_not_mutate_open_session",
                FAIL,
                f"_brain_sync_timeouts did not return JSON: {sync_result.text}",
            )
        if not sync_payload.get("applied"):
            return CheckResult(
                "live_sync_does_not_mutate_open_session",
                FAIL,
                f"_brain_sync_timeouts reported applied=False: {sync_payload}",
            )
        if sync_payload.get("effective_server_timeouts", {}).get("flash_program_seconds") != 12.0:
            return CheckResult(
                "live_sync_does_not_mutate_open_session",
                FAIL,
                f"effective_server_timeouts did not reflect the new value: {sync_payload}",
            )

        after = await client.read_core_register(name="pc")
        if after.is_error:
            return CheckResult(
                "live_sync_does_not_mutate_open_session",
                FAIL,
                f"read_core_register after sync failed -- the live session was disrupted: {after.text}",
            )

        await client.disconnect()
        return CheckResult(
            "live_sync_does_not_mutate_open_session",
            PASS,
            "session stayed alive (pc read before/after) while _brain_sync_timeouts "
            "applied a partial update for future connects",
        )


def check_live_sync_does_not_mutate_open_session(args: argparse.Namespace) -> CheckResult:
    try:
        return asyncio.run(_live_sync_check(args.board_id))
    except Exception as exc:  # noqa: BLE001 - report hardware/transport errors as a check result
        return CheckResult(
            "live_sync_does_not_mutate_open_session",
            FAIL,
            f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# 8 - provider dry run of the real rendered prompt
# ---------------------------------------------------------------------------


def check_provider_dry_run_prompt_render(
    args: argparse.Namespace, provider: TurnkeyProviderKind
) -> CheckResult:
    check_name = _provider_check_name(provider, "provider_dry_run_prompt_render")
    executable = _provider_executable(provider)
    if shutil.which(executable) is None:
        return CheckResult(check_name, SKIP, f"{executable} CLI not found on PATH")

    board = load_board(args.board_id)
    invocation = TurnkeyInvocation(
        mode="freeform",
        provider=provider,
        board_id=args.board_id,
        task="Without touching the board, state in one sentence what your first action would be.",
        model=_provider_model(args, provider),
        max_iters=2,
        serial_read_seconds=3.0,
        memory_mode="deterministic",
        native_sync_every=10,
        recent_turn_detail_limit=2,
        mid_history_turn_limit=6,
        mid_history_render_chars=4_000,
        memory_summary_max_chars=2_000,
        preload_common_details=True,
        provider_native_skills="auto",
        provider_native_skill_root=resolve_provider_native_skill_root(),
        port=args.port,
    )
    state = BrainState(
        run_mode=invocation.mode,
        board_id=args.board_id,
        task=invocation.task,
        case_id=None,
        case_kind=None,
        selected_skill_ids=(),
        effective_timeout_config=invocation.timeout_config,
        effective_max_iters=invocation.max_iters,
    )
    instructions = _build_instructions(invocation)
    turn_prompt = _build_full_turn_prompt(
        invocation, board, state, skills_text="(none)", workspace=None
    )
    if "effective_timeouts=" not in turn_prompt:
        return CheckResult(
            check_name, FAIL, "rendered prompt is missing the Branch C effective_timeouts line"
        )
    provider_config = BrainProviderConfig(
        provider=provider,
        model=invocation.model,
        timeout_seconds=args.provider_timeout_seconds,
    )
    decision_provider = create_decision_provider(provider_config)
    session_state = make_provider_session_state(
        provider=provider,
        model=invocation.model,
        memory_mode=invocation.memory_mode,
        continuation_mode=decision_provider.capabilities.continuation_mode,
        native_sync_every=invocation.native_sync_every,
    )
    prompt_bundle = ProviderPromptBundle(
        system_instructions=instructions,
        tool_schema_text="Curated MCP tool index (compact):\n(dry-run prompt render)",
        provider_memory_text="",
        turn_context_text=turn_prompt,
        turn_decision_schema_text=f"TurnDecision JSON schema:\n{decision_schema_text()}",
    )
    try:
        turn = asyncio.run(
            decision_provider.next_decision(
                prompt_bundle=prompt_bundle,
                session_state=session_state,
            )
        )
    except Exception as exc:  # noqa: BLE001 - provider errors are acceptance evidence
        detail = str(exc)[-500:]
        lowered = detail.lower()
        if any(
            token in lowered for token in ("401", "unauthorized", "auth", "login", "refresh token")
        ):
            return CheckResult(
                check_name,
                SKIP,
                f"{provider} auth/runtime issue -- authenticate the provider CLI and retry: {detail}",
            )
        return CheckResult(
            check_name, FAIL, f"{provider} provider dry run failed: {type(exc).__name__}: {detail}"
        )

    action = turn.decision.action
    action_batch = turn.decision.action_batch
    if action is None and (action_batch is None or not action_batch.calls):
        return CheckResult(
            check_name, FAIL, f"{provider} returned a TurnDecision without action or action_batch"
        )
    if action is not None:
        decision_shape = f"action.kind={action.kind}"
    else:
        assert action_batch is not None
        decision_shape = f"action_batch.calls={len(action_batch.calls)}"
    return CheckResult(
        check_name,
        PASS,
        f"real prompt rendered with effective_timeouts and {provider} returned a valid "
        f"TurnDecision ({decision_shape})",
    )


# ---------------------------------------------------------------------------
# 9 - full provider-driven live run against real hardware
# ---------------------------------------------------------------------------


async def _live_provider_run_check(
    args: argparse.Namespace, provider: TurnkeyProviderKind
) -> CheckResult:
    check_name = _provider_check_name(provider, "provider_live_run_events_and_clamp")
    execution = await run_freeform_task(
        board_id=args.board_id,
        task=_live_provider_task(),
        provider=provider,
        model=_provider_model(args, provider),
        port=args.port,
        max_iters=6,
        timeout_proposal=TimeoutProposal(connect_seconds=99999.0, flash_seconds=1.0),
        iteration_estimate=IterationEstimate(requested_max_iterations=999),
    )

    bad_events = [
        record for record in execution.brain_events if record.get("event_kind") not in EVENT_KINDS
    ]
    if bad_events:
        return CheckResult(check_name, FAIL, f"malformed event_kind(s) recorded: {bad_events[:3]}")

    result_tools = set(execution.result.mcp_tools_used)
    touched_hardware = bool({"connect", "get_board_info"} & result_tools)
    for record in execution.brain_events:
        details = record.get("details")
        tool_name = details.get("tool_name") if isinstance(details, dict) else None
        if record.get("event_kind") == "tool_complete" and tool_name in {
            "connect",
            "get_board_info",
        }:
            touched_hardware = True
            break
    if not touched_hardware:
        return CheckResult(
            check_name,
            FAIL,
            "no connect/get_board_info evidence found in tool_complete events or "
            f"final result tools -- {provider} never reached real hardware",
        )

    effective = execution.state.effective_timeout_config
    if effective.connect_seconds == 99999.0 or effective.flash_seconds == 1.0:
        return CheckResult(
            check_name,
            FAIL,
            f"invocation timeout_proposal was not clamped: {effective.to_record()}",
        )

    run_root_note = f", run_root={execution.run_root}" if execution.run_root else ""
    return CheckResult(
        check_name,
        PASS,
        f"{provider}: {len(execution.brain_events)} well-formed events, hardware touched, "
        f"connect_seconds clamped to {effective.connect_seconds}s, "
        f"flash_seconds clamped to {effective.flash_seconds}s{run_root_note}",
    )


def check_provider_live_run_events_and_clamp(
    args: argparse.Namespace, provider: TurnkeyProviderKind
) -> CheckResult:
    check_name = _provider_check_name(provider, "provider_live_run_events_and_clamp")
    executable = _provider_executable(provider)
    if shutil.which(executable) is None:
        return CheckResult(check_name, SKIP, f"{executable} CLI not found on PATH")
    try:
        return asyncio.run(_live_provider_run_check(args, provider))
    except Exception as exc:  # noqa: BLE001 - report hardware/provider/runtime errors as a check result
        detail = str(exc)[-500:]
        lowered = detail.lower()
        if any(
            token in lowered for token in ("401", "unauthorized", "auth", "login", "refresh token")
        ):
            return CheckResult(
                check_name,
                SKIP,
                f"{provider} auth/runtime issue -- authenticate the provider CLI and retry: {detail}",
            )
        return CheckResult(
            check_name,
            FAIL,
            f"{provider} live run failed: {type(exc).__name__}: {detail}",
        )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CheckFn = Callable[[argparse.Namespace], CheckResult]

NO_HARDWARE_CHECKS: tuple[CheckFn, ...] = (
    check_timeout_defaults_and_clamp_ranges,
    check_timeout_admin_not_model_facing,
    check_no_overreach_into_other_branches,
    check_policy_clamps_and_partial_update,
)

HARDWARE_PRECONDITION_CHECKS: tuple[CheckFn, ...] = (
    check_probe_visible,
    check_stage0_bringup,
)

HARDWARE_ONLY_CHECKS: tuple[CheckFn, ...] = (check_live_sync_does_not_mutate_open_session,)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board-id", default="nrf52840dk")
    parser.add_argument(
        "--port",
        help=(
            "Optional serial port override for the selected board, e.g. "
            "/dev/cu.usbmodem0010502864801. Passed to host_bootstrap.py, "
            "stage0_check.py, and the turnkey brain as BOARD_ID=PORT where needed."
        ),
    )
    parser.add_argument("--model", default=None, help="Optional codex model override.")
    parser.add_argument(
        "--provider",
        action="append",
        choices=tuple(CLI_PROVIDER_EXECUTABLES),
        help=(
            "Provider CLI to exercise for Branch C provider checks. Repeat for a matrix. "
            "Defaults to codex-cli for backward compatibility."
        ),
    )
    parser.add_argument(
        "--provider-model",
        action="append",
        default=[],
        metavar="PROVIDER=MODEL",
        help=(
            "Optional provider-specific model override, e.g. claude-cli=sonnet. "
            "Falls back to --model when omitted."
        ),
    )
    parser.add_argument(
        "--provider-timeout-seconds",
        type=float,
        default=120.0,
        help="Timeout for each provider dry-run decision call.",
    )
    parser.add_argument(
        "--skip-hardware",
        action="store_true",
        help="Skip every check that needs the attached board.",
    )
    parser.add_argument(
        "--skip-providers",
        action="store_true",
        help="Skip every check that shells out to a provider CLI.",
    )
    parser.add_argument(
        "--skip-codex",
        action="store_true",
        help="Deprecated compatibility alias: remove codex-cli from provider checks.",
    )
    parser.add_argument(
        "--fail-on-skip",
        action="store_true",
        help=(
            "Treat any selected SKIP result as a failing acceptance condition. "
            "Use for Branch C acceptance; omit during local development when hardware or providers are unavailable."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results: list[CheckResult] = []

    header("Pure-Python spec checks (no hardware, no providers)")
    for fn in NO_HARDWARE_CHECKS:
        result = fn(args)
        log(result)
        results.append(result)

    hardware_ok = False
    if args.skip_hardware:
        header("Hardware checks skipped (--skip-hardware)")
    else:
        header(f"Hardware preconditions ({args.board_id})")
        for fn in HARDWARE_PRECONDITION_CHECKS:
            result = fn(args)
            log(result)
            results.append(result)
        hardware_ok = all(
            r.status == PASS for r in results if r.name in {"probe_visible", "stage0_bringup"}
        )

        header("Hardware-only Branch C checks")
        if hardware_ok:
            for fn in HARDWARE_ONLY_CHECKS:
                result = fn(args)
                log(result)
                results.append(result)
        else:
            for fn in HARDWARE_ONLY_CHECKS:
                result = CheckResult(
                    "live_sync_does_not_mutate_open_session",
                    SKIP,
                    "hardware preconditions did not pass",
                )
                log(result)
                results.append(result)

    selected_providers = _selected_providers(args)
    if not selected_providers:
        header("provider checks skipped")
    else:
        header("provider dry-run checks (no hardware required)")
        for provider in selected_providers:
            result = check_provider_dry_run_prompt_render(args, provider)
            log(result)
            results.append(result)

        if args.skip_hardware:
            header("provider + live hardware checks not selected (--skip-hardware)")
        else:
            header("provider + live hardware checks")
        if args.skip_hardware:
            pass
        elif not hardware_ok:
            for provider in selected_providers:
                result = CheckResult(
                    _provider_check_name(provider, "provider_live_run_events_and_clamp"),
                    SKIP,
                    "hardware preconditions did not pass",
                )
                log(result)
                results.append(result)
        else:
            for provider in selected_providers:
                result = check_provider_live_run_events_and_clamp(args, provider)
                log(result)
                results.append(result)

    header("Summary")
    passed = sum(1 for r in results if r.status == PASS)
    failed = sum(1 for r in results if r.status == FAIL)
    skipped = sum(1 for r in results if r.status == SKIP)
    print(f"  {passed} passed, {failed} failed, {skipped} skipped (of {len(results)})")
    for result in results:
        log(result)
    if args.fail_on_skip and skipped:
        print("  fail-on-skip enabled: skipped selected checks make this run incomplete")
        return 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
