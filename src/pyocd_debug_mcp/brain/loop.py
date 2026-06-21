"""Deterministic turnkey orchestration loop for the R12 brain."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from pyocd_debug_mcp.board_config import (
    DEFAULT_BOARD_CONFIG_DIR,
    BoardConfig,
    load_selected_board_configs,
)
from pyocd_debug_mcp.brain.actions import (
    Classification,
    ReadFileAction,
    FinalizeAction,
    ReplaceFileAction,
    RunBuildAction,
    RunGreenCheckAction,
    ServerToolAction,
    TurnDecision,
    TurnkeyRunResult,
    VerificationSnapshot,
)
from pyocd_debug_mcp.brain.config import BrainProviderConfig, TurnkeyInvocation
from pyocd_debug_mcp.brain.mcp_client import LocalMCPClient, MCPClientError, ToolTextResult
from pyocd_debug_mcp.brain.provider_factory import create_decision_provider
from pyocd_debug_mcp.brain.provider_types import DecisionProvider, ProviderTurn
from pyocd_debug_mcp.brain.skills import SkillManifest, load_skills_for_context, render_skills
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain.workspace import WorkspaceError, WorkspaceSession, prepare_workspace_session
from pyocd_debug_mcp.reference_artifacts import resolve_reference_artifacts
from pyocd_debug_mcp.services.session_runtime import RUNS_ROOT

if TYPE_CHECKING:
    from tests.harness.stage1_smoke import Stage1SmokeResult

REPO_ROOT = Path(__file__).resolve().parents[3]

MAX_NO_PROGRESS_STREAK = 3
MAX_IDENTICAL_BUILD_FAILURES = 2
MAX_STAGNANT_FIX_CYCLES = 2


class TurnkeyLoopError(RuntimeError):
    """Raised when the turnkey loop cannot complete a run."""


class TurnkeyRefusal(TurnkeyLoopError):
    """Raised for deterministic local-policy refusals in the turnkey client."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class TurnkeyExecution:
    invocation: TurnkeyInvocation
    board: BoardConfig
    result: TurnkeyRunResult
    state: BrainState
    run_root: Path | None
    prompt_text: str
    request_payload: dict[str, object]
    selected_skills: tuple[SkillManifest, ...]
    model_turns: tuple[dict[str, object], ...]
    brain_trace: tuple[dict[str, object], ...]


def load_board(board_id: str) -> BoardConfig:
    boards = load_selected_board_configs(DEFAULT_BOARD_CONFIG_DIR, requested_ids=[board_id])
    if not boards:
        raise TurnkeyLoopError(f"Board not found: {board_id}")
    return boards[0]


def _default_artifacts(invocation: TurnkeyInvocation, board: BoardConfig) -> tuple[Path, Path]:
    artifacts = resolve_reference_artifacts(
        board,
        flash_artifact=invocation.flash_artifact,
        elf_path=invocation.elf,
    )
    return artifacts.flash_artifact, artifacts.symbol_artifact


def _build_request_payload(
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    selected_skills: tuple[SkillManifest, ...],
) -> dict[str, object]:
    flash_artifact, symbol_artifact = _default_artifacts(invocation, board)
    return {
        "mode": invocation.mode,
        "board_id": board.board_id,
        "display_name": board.display_name,
        "task": invocation.task,
        "case_id": invocation.case_id,
        "case_kind": invocation.case_kind,
        "provider": invocation.provider,
        "model": invocation.model,
        "max_iters": invocation.max_iters,
        "serial_read_seconds": invocation.serial_read_seconds,
        "port_override": invocation.port,
        "flash_artifact": str(flash_artifact),
        "symbol_artifact": str(symbol_artifact),
        "workspace_root": str(invocation.workspace_root) if invocation.workspace_root else None,
        "build_command": invocation.build_command,
        "code_edits_allowed": invocation.code_edits_allowed,
        "allowed_edit_roots": list(invocation.allowed_edit_roots),
        "recover_allowed": invocation.recover_allowed,
        "expected_uart_substring": invocation.expected_uart_substring,
        "expected_symbol_name": invocation.expected_symbol_name,
        "expected_symbol_value_u32": invocation.expected_symbol_value_u32,
        "selected_skill_ids": [skill.skill_id for skill in selected_skills],
    }


def _format_board_facts(board: BoardConfig, invocation: TurnkeyInvocation) -> str:
    lines = [
        f"board_id={board.board_id}",
        f"display_name={board.display_name}",
        f"mcu_family={board.mcu_family}",
        f"probe_family={board.probe_family}",
        f"pyocd_target={board.pyocd_target}",
        f"default_baudrate={board.default_baudrate}",
        f"test_read_address=0x{board.test_addr:08X}",
        f"recover_mode={board.recover_mode or '(none)'}",
        f"requires_recover_validation={board.requires_recover_validation}",
        f"provider={invocation.provider}",
        f"model={invocation.model or '(provider default)'}",
    ]
    if board.expected_uart_substring:
        lines.append(f"default_uart_substring={board.expected_uart_substring}")
    if board.silicon_id_addr is not None and board.silicon_id_expected is not None:
        lines.append(
            f"silicon_identity=0x{board.silicon_id_addr:08X}->0x{board.silicon_id_expected:08X}"
        )
    if invocation.expected_uart_substring:
        lines.append(f"benchmark_uart_substring={invocation.expected_uart_substring}")
    if invocation.expected_symbol_name and invocation.expected_symbol_value_u32 is not None:
        lines.append(
            f"benchmark_symbol={invocation.expected_symbol_name}=0x{invocation.expected_symbol_value_u32:08X}"
        )
    return "\n".join(lines)


def _workspace_summary(workspace: WorkspaceSession | None) -> str:
    if workspace is None:
        return "workspace: (none)"
    return (
        f"workspace_root={workspace.root}\n"
        f"code_edits_allowed={workspace.code_edits_allowed}\n"
        f"allowed_edit_roots={list(workspace.allowed_edit_roots)}\n"
        f"build_command={workspace.build_command or '(none)'}"
    )


def _build_instructions(invocation: TurnkeyInvocation) -> str:
    benchmark_note = (
        "The benchmark prompt may mention a final structured result. In this turnkey client, do not "
        "emit a raw benchmark-result object. Emit one TurnDecision JSON object per turn and use the "
        "`finalize` action when you are ready for the runner to assemble the final benchmark result."
        if invocation.mode == "benchmark"
        else "Emit one TurnDecision JSON object per turn and use the `finalize` action when you are ready to stop."
    )
    return (
        "You are the turnkey firmware-debugging brain for a local pyOCD-based repair system.\n\n"
        "Rules:\n"
        "- Return exactly one JSON object that matches the TurnDecision schema.\n"
        "- Prefer connecting with connect(board_id=...) and do not guess probe UIDs.\n"
        "- Do not pass a generic target override such as cortex_m.\n"
        "- Gather evidence before editing code.\n"
        "- Use unlock_recover only when the symptoms justify it and the task policy allows it.\n"
        "- When code edits are allowed, replace whole files only; do not describe patches in prose.\n"
        "- Use run_green_check when you believe the target is healthy again.\n"
        f"- {benchmark_note}\n"
    )


def _build_turn_prompt(
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
    skills_text: str,
    workspace: WorkspaceSession | None,
) -> str:
    verification = state.verification
    return (
        "Task:\n"
        f"{invocation.task.strip()}\n\n"
        "Board facts:\n"
        f"{_format_board_facts(board, invocation)}\n\n"
        "Workspace/build context:\n"
        f"{_workspace_summary(workspace)}\n\n"
        "Current state:\n"
        f"iteration={state.iteration}\n"
        f"session_id={state.session_id or '(none)'}\n"
        f"session_ids_seen={state.session_ids_seen}\n"
        f"flash_count={state.flash_count}\n"
        f"build_count={state.build_count}\n"
        f"recover_count={state.recover_count}\n"
        f"last_classification={state.last_classification or '(none)'}\n"
        f"last_action_summary={state.last_action_summary or '(none)'}\n"
        f"last_observation={state.last_observation_text or '(none)'}\n"
        f"last_result={state.last_result_text or '(none)'}\n"
        f"blocked_action_families={sorted(state.blocked_action_families)}\n"
        f"refused_action_families={sorted(state.refused_action_families)}\n"
        f"verification.flash_ok={verification.flash_ok}\n"
        f"verification.uart_ok={verification.uart_ok}\n"
        f"verification.symbol_ok={verification.symbol_ok}\n"
        f"verification.green_check_ok={verification.green_check_ok}\n\n"
        "Selected skills:\n"
        f"{skills_text}\n\n"
        "Available action kinds:\n"
        "- server_tool: connect, disconnect, get_board_info, get_state, halt, resume, reset, read_core_register, read_memory, flash_firmware, read_serial, unlock_recover\n"
        "- read_file(path)\n"
        "- replace_file(path, content)\n"
        "- run_build(build_command?)\n"
        "- run_green_check\n"
        "- finalize(final_status, classification, root_cause, summary)\n\n"
        "TurnDecision JSON schema:\n"
        f"{TurnDecision.model_json_schema()}\n"
    )


def _model_turn_record(iteration: int, provider_turn: ProviderTurn) -> dict[str, object]:
    return {
        "iteration": iteration,
        "response_id": provider_turn.response_id,
        "output_text": provider_turn.output_text,
        "decision": provider_turn.decision.model_dump(mode="json"),
    }


def _brain_trace_record(
    *,
    iteration: int,
    action_kind: str,
    payload: dict[str, object],
    result_text: str,
) -> dict[str, object]:
    return {
        "iteration": iteration,
        "action_kind": action_kind,
        "payload": payload,
        "result_text": result_text,
    }


def _flash_target_path(invocation: TurnkeyInvocation, board: BoardConfig) -> str:
    flash_artifact, _ = _default_artifacts(invocation, board)
    return str(flash_artifact)


def _green_check_artifacts(invocation: TurnkeyInvocation, board: BoardConfig) -> tuple[Path, Path]:
    if invocation.flash_artifact is not None and invocation.elf is not None:
        return invocation.flash_artifact, invocation.elf
    flash_artifact, elf = _default_artifacts(invocation, board)
    return flash_artifact, elf


def _update_observation_state(state: BrainState, decision: TurnDecision, result_text: str) -> None:
    current_signature = f"{decision.classification}:{decision.observation_summary}:{result_text}"
    if current_signature == state.last_no_progress_signature:
        state.no_progress_streak += 1
    else:
        state.no_progress_streak = 0
        state.last_no_progress_signature = current_signature
    state.last_observation_text = decision.observation_summary
    if decision.classification is not None:
        state.last_classification = decision.classification


def _update_build_failure_state(
    state: BrainState,
    build_result_text: str,
    changed_files: tuple[str, ...],
) -> None:
    signature = f"{build_result_text}|{changed_files}"
    if signature == state.last_build_failure_signature:
        state.repeated_build_failure_count += 1
    else:
        state.repeated_build_failure_count = 1
        state.last_build_failure_signature = signature


def _update_verification_state(
    state: BrainState,
    *,
    flash_ok: bool,
    uart_ok: bool,
    symbol_ok: bool,
    green_check_ok: bool,
) -> None:
    state.verification = VerificationSnapshot(
        flash_ok=flash_ok,
        uart_ok=uart_ok,
        symbol_ok=symbol_ok,
        green_check_ok=green_check_ok,
    )
    signature = state.verification_signature()
    if signature == state.last_verification_signature:
        state.stagnant_fix_cycle_count += 1
    else:
        state.stagnant_fix_cycle_count = 0
        state.last_verification_signature = signature


def _render_refusal(code: str, message: str) -> str:
    return f"Refused [{code}]: {message}"


def _normalize_session_id(session_id: str | None) -> Path | None:
    if not session_id:
        return None
    return RUNS_ROOT / session_id


def _verify_green(
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
) -> Stage1SmokeResult:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from tests.harness.stage1_smoke import run_stage1_smoke

    flash_artifact, elf = _green_check_artifacts(invocation, board)
    return run_stage1_smoke(
        board_id=board.board_id,
        probe_uid=state.probe_uid,
        port=invocation.port,
        flash_artifact=flash_artifact,
        elf=elf,
        serial_read_seconds=invocation.serial_read_seconds,
    )


async def _execute_server_tool(
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
    client: LocalMCPClient,
    action: ServerToolAction,
) -> ToolTextResult:
    arguments = dict(action.arguments)
    if action.tool_name == "connect":
        arguments.setdefault("board_id", board.board_id)
        if invocation.mode == "benchmark":
            if arguments.get("unique_id") is not None:
                raise TurnkeyRefusal(
                    "brain/connect-unique-id-forbidden",
                    "Benchmark cases must connect by board_id only.",
                )
            if arguments.get("target") is not None:
                raise TurnkeyRefusal(
                    "brain/connect-target-override-forbidden",
                    "Benchmark cases must not pass an explicit target override.",
                )
    elif action.tool_name == "flash_firmware":
        if "path" not in arguments and invocation.flash_artifact is not None:
            arguments["path"] = str(invocation.flash_artifact)
    elif action.tool_name == "read_serial":
        if invocation.port is not None:
            arguments.setdefault("port", invocation.port)
        arguments.setdefault("read_seconds", invocation.serial_read_seconds)
    elif action.tool_name == "unlock_recover" and not invocation.recover_allowed:
        raise TurnkeyRefusal(
            "brain/recover-forbidden",
            "This task does not allow unlock_recover as a valid intervention.",
        )

    result = await client.call_tool(action.tool_name, arguments=arguments)
    state.register_tool_use(action.tool_name)
    state.actions_taken.append(action.tool_name)
    state.mcp_tools_used.append(action.tool_name)
    state.last_action_summary = f"{action.tool_name}({arguments})"
    state.last_result_text = result.text

    if result.refusal_code is not None:
        state.refused_action_families.add(action.tool_name)
    if result.blocked_code is not None:
        state.blocked_action_families.add(action.tool_name)
    if action.tool_name == "connect":
        state.register_connect(
            session_id=result.session_id,
            probe_uid=result.probe_uid,
            route_used=result.route_used,
        )
    if action.tool_name == "flash_firmware" and result.text.startswith("Flashed "):
        _update_verification_state(
            state,
            flash_ok=True,
            uart_ok=state.verification.uart_ok,
            symbol_ok=state.verification.symbol_ok,
            green_check_ok=state.verification.green_check_ok,
        )
    if action.tool_name == "read_serial":
        matched = result.text.startswith("UART matched")
        _update_verification_state(
            state,
            flash_ok=state.verification.flash_ok,
            uart_ok=matched,
            symbol_ok=state.verification.symbol_ok,
            green_check_ok=state.verification.green_check_ok if not matched else state.verification.green_check_ok,
        )
    if action.tool_name == "unlock_recover" and "Recover completed" in result.text:
        state.recover_used = True
    return result


def _execute_read_file(workspace: WorkspaceSession | None, path: str, state: BrainState) -> str:
    if workspace is None:
        raise TurnkeyRefusal(
            "brain/no-workspace",
            "This run has no workspace attached, so local file reads are unavailable.",
        )
    text = workspace.read_file(path)
    state.actions_taken.append(f"read_file:{path}")
    state.last_action_summary = f"read_file({path})"
    state.last_result_text = f"Read {path} ({len(text)} chars)."
    return text


def _execute_replace_file(
    workspace: WorkspaceSession | None,
    action: ReplaceFileAction,
    state: BrainState,
) -> str:
    if workspace is None:
        raise TurnkeyRefusal(
            "brain/no-workspace",
            "This run has no editable workspace attached.",
        )
    workspace.replace_file(action.path, action.content)
    state.actions_taken.append(f"replace_file:{action.path}")
    state.last_action_summary = f"replace_file({action.path})"
    state.last_result_text = f"Replaced {action.path}."
    return f"Replaced {action.path}."


def _execute_build(
    workspace: WorkspaceSession | None,
    action: RunBuildAction,
    state: BrainState,
) -> str:
    if workspace is None:
        raise TurnkeyRefusal(
            "brain/no-workspace",
            "This run has no workspace/build context.",
        )
    state.register_build()
    build = workspace.run_build(action.build_command)
    state.actions_taken.append("run_build")
    state.last_action_summary = f"run_build({action.build_command or workspace.build_command})"
    if build.exit_code == 0:
        state.last_result_text = "Build succeeded."
        state.repeated_build_failure_count = 0
        state.last_build_failure_signature = None
        return "Build succeeded."
    changed_files = workspace.changed_files()
    failure_text = (
        f"Build failed with exit_code={build.exit_code}.\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )
    _update_build_failure_state(state, failure_text, changed_files)
    state.last_result_text = failure_text
    return failure_text


def _execute_green_check(
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
) -> str:
    smoke = _verify_green(invocation, board, state)
    symbol_ok = True
    if (
        invocation.expected_symbol_name is not None
        and smoke.resolved_symbol.name != invocation.expected_symbol_name
    ):
        symbol_ok = False
    if (
        invocation.expected_symbol_value_u32 is not None
        and smoke.resolved_symbol.value_u32 != invocation.expected_symbol_value_u32
    ):
        symbol_ok = False
    _update_verification_state(
        state,
        flash_ok=True,
        uart_ok=True,
        symbol_ok=symbol_ok,
        green_check_ok=symbol_ok,
    )
    state.actions_taken.append("run_green_check")
    state.last_action_summary = "run_green_check()"
    state.last_result_text = (
        f"Green check passed on {board.board_id}: pc=0x{smoke.pc:08X}, "
        f"symbol={smoke.resolved_symbol.name}=0x{smoke.resolved_symbol.value_u32:08X}, "
        f"uart_excerpt={smoke.capture_excerpt}"
    )
    return state.last_result_text


def _check_local_convergence(state: BrainState) -> TurnkeyRunResult | None:
    if state.repeated_build_failure_count >= MAX_IDENTICAL_BUILD_FAILURES:
        return _blocked_result(
            state,
            classification=state.last_classification or "code_bug",
            code="brain/repeated-build-failure",
            message="Repeated identical build failures occurred without meaningful change.",
        )
    if state.no_progress_streak >= MAX_NO_PROGRESS_STREAK:
        return _blocked_result(
            state,
            classification=state.last_classification or "observability_fault",
            code="brain/no-progress",
            message="Repeated identical diagnosis turns occurred without new evidence.",
        )
    if state.stagnant_fix_cycle_count >= MAX_STAGNANT_FIX_CYCLES:
        return _blocked_result(
            state,
            classification=state.last_classification or "code_bug",
            code="brain/no-verification-improvement",
            message="Repeated edit/build cycles did not improve verification state.",
        )
    return None


def _blocked_result(
    state: BrainState,
    *,
    classification: Classification,
    code: str,
    message: str,
) -> TurnkeyRunResult:
    return TurnkeyRunResult(
        board_id=state.board_id,
        case_id=state.case_id,
        session_id=state.session_id,
        final_status="blocked",
        classification=classification,
        root_cause=message,
        actions_taken=list(state.actions_taken),
        mcp_tools_used=list(state.mcp_tools_used),
        files_changed=[],
        recover_used=state.recover_used,
        verification=state.verification,
        summary=f"Blocked [{code}]: {message}",
    )


def _final_result_from_action(
    state: BrainState,
    action: FinalizeAction,
    workspace: WorkspaceSession | None,
) -> TurnkeyRunResult:
    changed_files = list(workspace.changed_files()) if workspace is not None else []
    return TurnkeyRunResult(
        board_id=state.board_id,
        case_id=state.case_id,
        session_id=state.session_id,
        final_status=action.final_status,
        classification=action.classification,
        root_cause=action.root_cause,
        actions_taken=list(state.actions_taken),
        mcp_tools_used=list(state.mcp_tools_used),
        files_changed=changed_files,
        recover_used=state.recover_used,
        verification=state.verification,
        summary=action.summary,
    )


def _persist_turnkey_artifacts(
    execution: TurnkeyExecution,
    workspace: WorkspaceSession | None,
) -> None:
    if execution.run_root is None:
        return
    run_root = execution.run_root
    (run_root / "run-metadata").mkdir(parents=True, exist_ok=True)
    (run_root / "logs").mkdir(parents=True, exist_ok=True)
    (run_root / "applied-patches").mkdir(parents=True, exist_ok=True)
    (run_root / "run-metadata" / "turnkey_request.json").write_text(
        json.dumps(execution.request_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (run_root / "run-metadata" / "turnkey_result.json").write_text(
        execution.result.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (run_root / "run-metadata" / "turnkey_state.json").write_text(
        json.dumps(execution.state.to_record(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (run_root / "logs" / "prompt.txt").write_text(execution.prompt_text, encoding="utf-8")
    with (run_root / "logs" / "brain_trace.jsonl").open("w", encoding="utf-8") as handle:
        for record in execution.brain_trace:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")
    with (run_root / "logs" / "model_turns.jsonl").open("w", encoding="utf-8") as handle:
        for record in execution.model_turns:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")
    if workspace is not None:
        workspace.write_diff(run_root / "applied-patches" / "turnkey.diff")


async def run_turnkey(
    invocation: TurnkeyInvocation,
    *,
    provider: DecisionProvider,
    client_factory: Callable[[], LocalMCPClient] = LocalMCPClient,
) -> TurnkeyExecution:
    board = load_board(invocation.board_id)
    selected_skills = load_skills_for_context(
        board=board,
        task=invocation.task,
        case_kind=invocation.case_kind,
    )
    skills_text = render_skills(selected_skills)
    workspace = (
        prepare_workspace_session(
            workspace_root=invocation.workspace_root,
            code_edits_allowed=invocation.code_edits_allowed,
            allowed_edit_roots=invocation.allowed_edit_roots,
            build_command=invocation.build_command,
            label=invocation.case_id or board.board_id,
        )
        if invocation.workspace_root is not None
        else None
    )
    request_payload = _build_request_payload(invocation, board, selected_skills)
    prompt_text = _build_turn_prompt(
        invocation,
        board,
        BrainState(
            run_mode=invocation.mode,
            board_id=board.board_id,
            task=invocation.task,
            case_id=invocation.case_id,
            case_kind=invocation.case_kind,
            selected_skill_ids=tuple(skill.skill_id for skill in selected_skills),
        ),
        skills_text,
        workspace,
    )
    instructions = _build_instructions(invocation)
    state = BrainState(
        run_mode=invocation.mode,
        board_id=board.board_id,
        task=invocation.task,
        case_id=invocation.case_id,
        case_kind=invocation.case_kind,
        selected_skill_ids=tuple(skill.skill_id for skill in selected_skills),
    )
    result: TurnkeyRunResult | None = None
    model_turns: list[dict[str, object]] = []
    brain_trace: list[dict[str, object]] = []
    run_root: Path | None = None

    async with client_factory() as client:
        for iteration in range(1, invocation.max_iters + 1):
            state.iteration = iteration
            turn_prompt = _build_turn_prompt(invocation, board, state, skills_text, workspace)
            provider_turn = await provider.next_decision(
                instructions=instructions,
                turn_prompt=turn_prompt,
            )
            model_turns.append(_model_turn_record(iteration, provider_turn))
            decision = provider_turn.decision

            try:
                action = decision.action
                if isinstance(action, ServerToolAction):
                    action_result = await _execute_server_tool(invocation, board, state, client, action)
                    result_text = action_result.text
                    if state.session_id is not None and run_root is None:
                        run_root = _normalize_session_id(state.session_id)
                    if invocation.mode == "benchmark" and len(state.session_ids_seen) > 1:
                        result = _blocked_result(
                            state,
                            classification=decision.classification or "observability_fault",
                            code="benchmark/reconnect-not-allowed",
                            message="The turnkey client opened more than one MCP session during a benchmark case.",
                        )
                        brain_trace.append(
                            _brain_trace_record(
                                iteration=iteration,
                                action_kind=action.kind,
                                payload=action.model_dump(mode="json"),
                                result_text=result.summary,
                            )
                        )
                        break
                elif isinstance(action, ReplaceFileAction):
                    result_text = _execute_replace_file(workspace, action, state)
                elif isinstance(action, RunBuildAction):
                    result_text = _execute_build(workspace, action, state)
                elif isinstance(action, RunGreenCheckAction):
                    result_text = _execute_green_check(invocation, board, state)
                elif isinstance(action, ReadFileAction):
                    result_text = _execute_read_file(workspace, action.path, state)
                elif isinstance(action, FinalizeAction):
                    result = _final_result_from_action(state, action, workspace)
                    brain_trace.append(
                        _brain_trace_record(
                            iteration=iteration,
                            action_kind=action.kind,
                            payload=action.model_dump(mode="json"),
                            result_text=result.summary,
                        )
                    )
                    break
                else:
                    raise TurnkeyLoopError(f"Unhandled action kind: {action.kind}")
            except TurnkeyRefusal as exc:
                result_text = _render_refusal(exc.code, exc.message)
                state.refused_action_families.add(decision.action.kind)
                state.last_action_summary = decision.action.kind
                state.last_result_text = result_text
            except (WorkspaceError, MCPClientError, RuntimeError) as exc:
                result_text = f"{type(exc).__name__}: {exc}"
                state.last_action_summary = decision.action.kind
                state.last_result_text = result_text

            brain_trace.append(
                _brain_trace_record(
                    iteration=iteration,
                    action_kind=decision.action.kind,
                    payload=decision.action.model_dump(mode="json"),
                    result_text=result_text,
                )
            )
            _update_observation_state(state, decision, result_text)
            blocked = _check_local_convergence(state)
            if blocked is not None:
                result = blocked
                break

        if result is None:
            result = _blocked_result(
                state,
                classification=state.last_classification or "observability_fault",
                code="brain/max-iters",
                message=f"Reached max_iters={invocation.max_iters} without a final answer.",
            )

        if state.session_id is not None and run_root is None:
            run_root = _normalize_session_id(state.session_id)
        if state.session_id is not None:
            try:
                await client.call_tool("disconnect", {})
            except MCPClientError:
                pass

    execution = TurnkeyExecution(
        invocation=invocation,
        board=board,
        result=result,
        state=state,
        run_root=run_root,
        prompt_text=f"{instructions}\n\n{prompt_text}",
        request_payload=request_payload,
        selected_skills=selected_skills,
        model_turns=tuple(model_turns),
        brain_trace=tuple(brain_trace),
    )
    _persist_turnkey_artifacts(execution, workspace)
    return execution


async def run_turnkey_with_openai(invocation: TurnkeyInvocation, *, api_key: str) -> TurnkeyExecution:
    config = BrainProviderConfig(provider="openai-api", api_key=api_key, model=invocation.model)
    return await run_turnkey_with_provider(invocation, provider_config=config)


async def run_turnkey_with_provider(
    invocation: TurnkeyInvocation,
    *,
    provider_config: BrainProviderConfig,
) -> TurnkeyExecution:
    provider = create_decision_provider(provider_config)
    return await run_turnkey(invocation, provider=provider)
