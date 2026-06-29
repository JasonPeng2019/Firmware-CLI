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
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, get_args

from pyocd_debug_mcp.brain.actions import AllowedServerToolName, decision_schema_text
from pyocd_debug_mcp.brain.app import run_freeform_task
from pyocd_debug_mcp.brain.config import TurnkeyInvocation
from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.brain.events import EVENT_KINDS
from pyocd_debug_mcp.brain.loop import _build_instructions, _build_turn_prompt, load_board
from pyocd_debug_mcp.brain.mcp_client import LocalMCPClient
from pyocd_debug_mcp.brain.provider_codex_cli import (
    ProviderResponseError,
    _build_codex_command,
    _compose_prompt,
)
from pyocd_debug_mcp.brain.provider_parsing import parse_turn_decision_json
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
    return CheckResult("stage0_bringup", PASS, f"host_bootstrap + stage0_check green for {args.board_id}")


def _live_codex_task() -> str:
    return (
        "Connect to the board with connect(board_id=...), call get_board_info, "
        "then finalize with final_status=unresolved, classification=tooling_failure, "
        "root_cause='dry run', summary='Branch C validation run.' "
        "Do not flash, edit files, or run a build."
    )


# ---------------------------------------------------------------------------
# 2 - timeouts.py is the single source of truth for defaults/clamp ranges
# ---------------------------------------------------------------------------


def check_timeout_defaults_and_clamp_ranges(args: argparse.Namespace) -> CheckResult:
    config = default_turnkey_timeout_config()
    if config.connect_seconds <= 0 or config.flash_seconds <= 0:
        return CheckResult("timeout_defaults_and_clamp_ranges", FAIL, "non-positive default timeout")

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
        return CheckResult("no_overreach_into_other_branches", FAIL, f"found out-of-scope symbols: {hits}")
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
        return CheckResult("policy_clamps_and_partial_update", FAIL, "raw 99999s connect_seconds passed through unclamped")
    if not_connected.effective_timeout_config.flash_seconds == 1.0:
        return CheckResult("policy_clamps_and_partial_update", FAIL, "raw 1s flash_seconds passed through unclamped")
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
# 8 - codex dry run of the real rendered prompt
# ---------------------------------------------------------------------------


def check_codex_dry_run_prompt_render(args: argparse.Namespace) -> CheckResult:
    if shutil.which("codex") is None:
        return CheckResult("codex_dry_run_prompt_render", SKIP, "codex CLI not found on PATH")

    board = load_board(args.board_id)
    invocation = TurnkeyInvocation(
        mode="freeform",
        provider="codex-cli",
        board_id=args.board_id,
        task="Without touching the board, state in one sentence what your first action would be.",
        model=args.model,
        max_iters=2,
        serial_read_seconds=3.0,
        port=args.port,
    )
    state = BrainState(
        run_mode=invocation.mode,
        board_id=args.board_id,
        task=invocation.task,
        case_id=None,
        case_kind=None,
        selected_skill_ids=(),
    )
    instructions = _build_instructions(invocation)
    turn_prompt = _build_turn_prompt(invocation, board, state, skills_text="(none)", workspace=None)
    if "effective_timeouts=" not in turn_prompt:
        return CheckResult(
            "codex_dry_run_prompt_render", FAIL, "rendered prompt is missing the Branch C effective_timeouts line"
        )
    full_prompt = _compose_prompt(instructions, turn_prompt)

    with tempfile.TemporaryDirectory(prefix="branch-c-codex-dry-run-") as tmpdir:
        tmp_path = Path(tmpdir)
        output_path = tmp_path / "turn_decision.json"
        try:
            proc = subprocess.run(
                _build_codex_command(model=args.model, working_dir=tmp_path, output_path=output_path),
                input=full_prompt,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return CheckResult("codex_dry_run_prompt_render", FAIL, "codex exec timed out after 120s")

        output_text = output_path.read_text(encoding="utf-8") if output_path.exists() else proc.stdout.strip()
        if proc.returncode != 0 and not output_text:
            stderr_tail = proc.stderr.strip()[-300:]
            if "401" in stderr_tail or "Unauthorized" in stderr_tail or "refresh token" in stderr_tail:
                return CheckResult(
                    "codex_dry_run_prompt_render",
                    SKIP,
                    f"codex CLI is not authenticated -- run `codex login` and retry: {stderr_tail}",
                )
            return CheckResult("codex_dry_run_prompt_render", FAIL, f"codex exec failed: {stderr_tail}")

        try:
            decision = parse_turn_decision_json(output_text)
        except Exception as exc:  # noqa: BLE001 - report the real parse failure
            return CheckResult(
                "codex_dry_run_prompt_render",
                FAIL,
                f"codex output did not parse as a TurnDecision: {exc} -- raw: {output_text[-300:]}",
            )

    return CheckResult(
        "codex_dry_run_prompt_render",
        PASS,
        f"real prompt rendered with effective_timeouts and codex returned a valid "
        f"TurnDecision (action.kind={decision.action.kind})",
    )


# ---------------------------------------------------------------------------
# 9 - full codex-driven live run against real hardware
# ---------------------------------------------------------------------------


async def _live_codex_run_check(args: argparse.Namespace) -> CheckResult:
    execution = await run_freeform_task(
        board_id=args.board_id,
        task=_live_codex_task(),
        provider="codex-cli",
        model=args.model,
        port=args.port,
        max_iters=4,
        timeout_proposal=TimeoutProposal(connect_seconds=99999.0, flash_seconds=1.0),
        iteration_estimate=IterationEstimate(requested_max_iterations=999),
    )

    bad_events = [
        record for record in execution.brain_events if record.get("event_kind") not in EVENT_KINDS
    ]
    if bad_events:
        return CheckResult(
            "codex_live_run_events_and_clamp", FAIL, f"malformed event_kind(s) recorded: {bad_events[:3]}"
        )

    touched_hardware = any(
        record.get("event_kind") == "tool_complete" and record.get("details", {}).get("tool_name") in (
            "connect",
            "get_board_info",
        )
        for record in execution.brain_events
    )
    if not touched_hardware:
        return CheckResult(
            "codex_live_run_events_and_clamp",
            FAIL,
            "no connect/get_board_info tool_complete event found -- codex never reached real hardware",
        )

    effective = execution.state.effective_timeout_config
    if effective.connect_seconds == 99999.0 or effective.flash_seconds == 1.0:
        return CheckResult(
            "codex_live_run_events_and_clamp",
            FAIL,
            f"invocation timeout_proposal was not clamped: {effective.to_record()}",
        )

    run_root_note = f", run_root={execution.run_root}" if execution.run_root else ""
    return CheckResult(
        "codex_live_run_events_and_clamp",
        PASS,
        f"{len(execution.brain_events)} well-formed events, hardware touched, "
        f"connect_seconds clamped to {effective.connect_seconds}s, "
        f"flash_seconds clamped to {effective.flash_seconds}s{run_root_note}",
    )


def check_codex_live_run_events_and_clamp(args: argparse.Namespace) -> CheckResult:
    if shutil.which("codex") is None:
        return CheckResult("codex_live_run_events_and_clamp", SKIP, "codex CLI not found on PATH")
    try:
        return asyncio.run(_live_codex_run_check(args))
    except ProviderResponseError as exc:
        return CheckResult(
            "codex_live_run_events_and_clamp",
            SKIP,
            f"codex CLI auth/runtime issue -- run `codex login` and retry: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 - report hardware/runtime errors as a check result
        return CheckResult("codex_live_run_events_and_clamp", FAIL, f"{type(exc).__name__}: {exc}")


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

CODEX_CHECKS: tuple[CheckFn, ...] = (check_codex_dry_run_prompt_render,)

CODEX_PLUS_HARDWARE_CHECKS: tuple[CheckFn, ...] = (check_codex_live_run_events_and_clamp,)


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
        "--skip-hardware", action="store_true", help="Skip every check that needs the attached board."
    )
    parser.add_argument(
        "--skip-codex", action="store_true", help="Skip every check that shells out to the codex CLI."
    )
    parser.add_argument(
        "--fail-on-skip",
        action="store_true",
        help=(
            "Treat any selected SKIP result as a failing acceptance condition. "
            "Use for Branch C acceptance; omit during local development when hardware or codex is unavailable."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results: list[CheckResult] = []

    header("Pure-Python spec checks (no hardware, no codex)")
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
        hardware_ok = all(r.status == PASS for r in results if r.name in {"probe_visible", "stage0_bringup"})

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

    if args.skip_codex:
        header("codex checks skipped (--skip-codex)")
    else:
        header("codex dry-run checks (no hardware required)")
        for fn in CODEX_CHECKS:
            result = fn(args)
            log(result)
            results.append(result)

        header("codex + live hardware checks")
        if args.skip_hardware or not hardware_ok:
            for fn in CODEX_PLUS_HARDWARE_CHECKS:
                result = CheckResult(
                    "codex_live_run_events_and_clamp",
                    SKIP,
                    "hardware preconditions did not pass or were skipped",
                )
                log(result)
                results.append(result)
        else:
            for fn in CODEX_PLUS_HARDWARE_CHECKS:
                result = fn(args)
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
