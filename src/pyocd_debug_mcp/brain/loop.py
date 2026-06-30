"""Deterministic turnkey orchestration loop for the R12 brain."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
import inspect
from pathlib import Path
import shutil
import time
from typing import cast

import anyio

from pyocd_debug_mcp.board_config import (
    DEFAULT_BOARD_CONFIG_DIR,
    BoardConfig,
    load_selected_board_configs,
)
from pyocd_debug_mcp.brain.action_policy import SERVER_NATIVE_ACTIONS, namespaced_server_tool_name
from pyocd_debug_mcp.brain.actions import (
    ActionUnion,
    AllowedServerToolName,
    Classification,
    decision_schema_text,
    FinalizeAction,
    LoadSkillsAction,
    RunGreenCheckAction,
    RunScriptAction,
    ServerToolAction,
    TurnDecision,
    TurnkeyRunResult,
    VerificationSnapshot,
    WaitAction,
)
from pyocd_debug_mcp.brain.client_actions import (
    ClientActionSnapshot,
    ClientActionStore,
    GatedClientActionServer,
    InMemoryClientActionStore,
    render_client_action_prompt_section,
    run_client_action,
    snapshot_all_actions,
)
from pyocd_debug_mcp.brain.decision_types import ActionCall
from pyocd_debug_mcp.brain.evidence import Experiment, Hypothesis, Observation, StrategyEvaluation
from pyocd_debug_mcp.brain.events import BrainEvent, EventSink, emit_event, event_timestamp
from pyocd_debug_mcp.brain.config import BrainProviderConfig, TurnkeyInvocation
from pyocd_debug_mcp.brain.mcp_client import LocalMCPClient, MCPClientError, ToolTextResult
from pyocd_debug_mcp.brain.model_native_skills import (
    ModelNativeSkillError,
    ModelNativeSkillRegistry,
    render_model_native_skill_context,
)
from pyocd_debug_mcp.brain.provider_factory import create_decision_provider
from pyocd_debug_mcp.brain.provider_types import (
    advance_memory_sync_state,
    append_memory_entry,
    apply_deterministic_compaction,
    apply_summary_compaction,
    DecisionProvider,
    plan_memory_compaction,
    ProviderContinuationMode,
    ProviderMemoryEntry,
    ProviderMemoryResultStatus,
    ProviderPromptBundle,
    ProviderProgressUpdate,
    ProviderResumeFailure,
    ProviderResumeRecoveryChoice,
    ProviderRuntimeContext,
    ProviderSessionState,
    ProviderTurn,
    make_provider_session_state,
    render_provider_memory_text,
    provider_turn_record,
    with_provider_resume_recovery_request,
)
from pyocd_debug_mcp.brain.skills import SkillManifest, load_skills_for_context, render_skills
from pyocd_debug_mcp.brain.state import BrainState
from pyocd_debug_mcp.brain.timeout_runtime import (
    apply_invocation_timeout_policy,
    apply_turn_timeout_policy,
    sync_pending_server_timeouts,
)
from pyocd_debug_mcp.brain.tool_schemas import ToolSchemaBundle, build_tool_schema_bundle
from pyocd_debug_mcp.brain.workspace import (
    WorkspaceError,
    WorkspaceSession,
    prepare_workspace_session,
)
from pyocd_debug_mcp.reference_artifacts import resolve_reference_artifacts
from pyocd_debug_mcp.services.session_runtime import RUNS_ROOT, generate_session_id
from pyocd_debug_mcp.services.symbols import resolve_symbol
from pyocd_debug_mcp.timeouts import TurnkeyTimeoutConfig

REPO_ROOT = Path(__file__).resolve().parents[3]

MAX_NO_PROGRESS_STREAK = 3
MAX_IDENTICAL_BUILD_FAILURES = 2
MAX_STAGNANT_FIX_CYCLES = 2
MODEL_NATIVE_SKILL_ROOT = REPO_ROOT / ".codex" / "skills"


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
    brain_events: tuple[dict[str, object], ...]
    client_action_snapshots: tuple[ClientActionSnapshot, ...] = ()


ProviderResumeRecoveryHandler = Callable[[ProviderResumeFailure], ProviderResumeRecoveryChoice]


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


def _continuation_mode_for_provider(provider_kind: str) -> ProviderContinuationMode:
    return "local-primary" if provider_kind == "anthropic-api" else "remote-primary"


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
        "memory_mode": invocation.memory_mode,
        "native_sync_every": invocation.native_sync_every,
        "max_iters": invocation.max_iters,
        "serial_read_seconds": invocation.serial_read_seconds,
        "timeout_config": invocation.timeout_config.to_record(),
        "timeout_proposal": invocation.timeout_proposal.model_dump(mode="json")
        if invocation.timeout_proposal is not None
        else None,
        "iteration_estimate": invocation.iteration_estimate.model_dump(mode="json")
        if invocation.iteration_estimate is not None
        else None,
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
        "- Use read_memory with a string hex address such as 0x08000000, not an integer.\n"
        "- Once a session_id exists, do not call connect again unless you intentionally disconnected or attached to the wrong board.\n"
        "- If run_green_check fails, stay on the current session and continue debugging from that same session.\n"
        "- Gather evidence before editing code.\n"
        "- When you have a concrete suspected root cause, fill in `hypothesis`.\n"
        "- Use `strategy_evaluation` to explain why the chosen next action is the best current move.\n"
        "- Use unlock_recover only when the symptoms justify it and the task policy allows it.\n"
        "- When code edits are allowed, use your provider-native host tools to inspect, edit, and build the workspace directly before returning a governed or terminal decision.\n"
        "- Use load_skills when you need additional model-native workflow skill context on the next provider turn.\n"
        "- Keep host edits inside allowed edit roots and prefer whole-file replacements when changing source files.\n"
        "- Use run_green_check when you believe the target is healthy again.\n"
        "- Do not return final_status=healthy_confirmed or final_status=fixed until run_green_check has succeeded in this client.\n"
        f"- {benchmark_note}\n"
    )


def _build_turn_prompt(
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
    skills_text: str,
    workspace: WorkspaceSession | None,
    client_actions: ClientActionStore | None = None,
) -> str:
    verification = state.verification
    flash_artifact, symbol_artifact = _default_artifacts(invocation, board)
    return (
        "Task:\n"
        f"{invocation.task.strip()}\n\n"
        "Board facts:\n"
        f"{_format_board_facts(board, invocation)}\n\n"
        "Reference artifacts:\n"
        f"flash_artifact={flash_artifact}\n"
        f"symbol_artifact={symbol_artifact}\n\n"
        "Workspace/build context:\n"
        f"{_workspace_summary(workspace)}\n\n"
        "Current state:\n"
        f"iteration={state.iteration}\n"
        f"effective_max_iters={state.effective_max_iters or '(unset)'}\n"
        f"session_id={state.session_id or '(none)'}\n"
        f"session_ids_seen={state.session_ids_seen}\n"
        f"provider_session={state.provider_session_state.summary_record() if state.provider_session_state is not None else '(none)'}\n"
        f"flash_count={state.flash_count}\n"
        f"build_count={state.build_count}\n"
        f"recover_count={state.recover_count}\n"
        f"last_classification={state.last_classification or '(none)'}\n"
        f"last_action_summary={state.last_action_summary or '(none)'}\n"
        f"last_observation={state.last_observation_text or '(none)'}\n"
        f"last_result={state.last_result_text or '(none)'}\n"
        f"blocked_action_families={sorted(state.blocked_action_families)}\n"
        f"refused_action_families={sorted(state.refused_action_families)}\n"
        f"effective_timeouts={json.dumps(state.effective_timeout_config.to_record(), sort_keys=True)}\n"
        f"verification.flash_ok={verification.flash_ok}\n"
        f"verification.uart_ok={verification.uart_ok}\n"
        f"verification.symbol_ok={verification.symbol_ok}\n"
        f"verification.green_check_ok={verification.green_check_ok}\n\n"
        f"observations_recorded={len(state.observations)}\n"
        f"hypotheses_recorded={len(state.hypotheses)}\n"
        f"experiments_recorded={len(state.experiments)}\n"
        f"strategy_evaluations_recorded={len(state.strategy_evaluations)}\n\n"
        "Selected skills:\n"
        f"{skills_text}\n\n"
        "Model-native workflow skill context:\n"
        f"{render_model_native_skill_context(state.model_native_skills)}\n\n"
        f"{render_client_action_prompt_section(client_actions or InMemoryClientActionStore())}\n\n"
        "Available action kinds:\n"
        f"- server_tool: {', '.join(sorted(SERVER_NATIVE_ACTIONS))}\n"
        "- model-native host work: inspect/edit/build the workspace directly with your provider host tools before returning a governed/terminal decision\n"
        "- load_skills(skill_ids): load model-native workflow skill context for the next provider turn\n"
        "- run_green_check\n"
        "- wait(seconds)\n"
        "- run_script(name, inputs)\n"
        "- action_batch(calls): ordered calls using action_type plus arguments; stop on the first "
        "failure/refusal.\n"
        "- finalize(final_status, classification, root_cause, summary)\n"
    )


def _build_prompt_bundle(
    *,
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
    skills_text: str,
    workspace: WorkspaceSession | None,
    tool_schema_bundle: ToolSchemaBundle,
    client_actions: ClientActionStore | None = None,
) -> ProviderPromptBundle:
    return ProviderPromptBundle(
        system_instructions=_build_instructions(invocation),
        tool_schema_text=tool_schema_bundle.rendered_text,
        provider_memory_text=render_provider_memory_text(
            state.provider_session_state
            or make_provider_session_state(
                provider=invocation.provider,
                model=invocation.model,
                memory_mode=invocation.memory_mode,
                continuation_mode=(
                    state.provider_capabilities.continuation_mode
                    if state.provider_capabilities is not None
                    else _continuation_mode_for_provider(invocation.provider)
                ),
                native_sync_every=invocation.native_sync_every,
            )
        ),
        turn_context_text=_build_turn_prompt(
            invocation,
            board,
            state,
            skills_text,
            workspace,
            client_actions,
        ),
        turn_decision_schema_text=f"TurnDecision JSON schema:\n{decision_schema_text()}",
    )


def _model_turn_record(
    iteration: int,
    provider_turn: ProviderTurn,
    prompt_bundle: ProviderPromptBundle,
    *,
    committed_session_state: ProviderSessionState,
    compaction_record: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "iteration": iteration,
        **provider_turn_record(provider_turn),
        "committed_session_state": committed_session_state.summary_record(),
        "output_text": provider_turn.output_text,
        "decision": provider_turn.decision.model_dump(mode="json"),
        "prompt_bundle": prompt_bundle.to_record(),
        "compaction": dict(compaction_record or {}),
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


def _action_from_call(call: ActionCall) -> ActionUnion:
    args = dict(call.arguments)
    action_type = call.action_type
    namespaced_tool_name = namespaced_server_tool_name(action_type)
    if namespaced_tool_name is not None:
        embedded_tool_name = args.pop("tool_name", None)
        if embedded_tool_name is not None and embedded_tool_name != namespaced_tool_name:
            raise TurnkeyRefusal(
                "brain/conflicting-server-tool-name",
                (
                    "Namespaced server_tool action selected "
                    f"{namespaced_tool_name!r}, but arguments.tool_name was {embedded_tool_name!r}."
                ),
            )
        return ServerToolAction(
            tool_name=cast(AllowedServerToolName, namespaced_tool_name),
            arguments=_normalize_server_tool_arguments(args, namespaced_tool_name),
        )
    if action_type == "server_tool":
        tool_name = args.pop("tool_name", None)
        if not isinstance(tool_name, str):
            raise TurnkeyRefusal(
                "brain/batch-server-tool-missing-name",
                "Batched server_tool calls must include arguments.tool_name.",
            )
        if tool_name not in SERVER_NATIVE_ACTIONS:
            raise TurnkeyRefusal(
                "brain/unknown-server-tool-name",
                f"Batched server_tool call selected unknown tool {tool_name!r}.",
            )
        return ServerToolAction(
            tool_name=cast(AllowedServerToolName, tool_name),
            arguments=_normalize_server_tool_arguments(args, tool_name),
        )
    if action_type in SERVER_NATIVE_ACTIONS:
        return ServerToolAction(
            tool_name=cast(AllowedServerToolName, action_type),
            arguments=_normalize_server_tool_arguments(args, action_type),
        )
    if action_type == "wait":
        return WaitAction.model_validate({"kind": "wait", **args})
    if action_type == "run_script":
        return RunScriptAction.model_validate({"kind": "run_script", **args})
    if action_type == "run_green_check":
        return RunGreenCheckAction.model_validate({"kind": "run_green_check", **args})
    if action_type == "load_skills":
        return LoadSkillsAction.model_validate({"kind": "load_skills", **args})
    raise TurnkeyRefusal(
        "brain/unsupported-batch-action", f"Unsupported batched action: {action_type}"
    )


def _normalize_server_tool_arguments(args: dict[str, object], tool_name: str) -> dict[str, object]:
    nested = args.pop("arguments", None)
    if nested is None:
        return args
    if not isinstance(nested, dict):
        raise TurnkeyRefusal(
            "brain/invalid-server-tool-arguments",
            f"Batched server_tool call for {tool_name!r} used non-object arguments.",
        )
    normalized = dict(cast(dict[str, object], nested))
    embedded_tool_name = normalized.pop("tool_name", None)
    if embedded_tool_name is not None and embedded_tool_name != tool_name:
        raise TurnkeyRefusal(
            "brain/conflicting-server-tool-name",
            (
                "Batched server_tool call selected "
                f"{tool_name!r}, but nested arguments.tool_name was {embedded_tool_name!r}."
            ),
        )
    for key, value in args.items():
        if key in normalized and normalized[key] != value:
            raise TurnkeyRefusal(
                "brain/conflicting-server-tool-argument",
                (
                    "Batched server_tool call for "
                    f"{tool_name!r} supplied conflicting values for argument {key!r}."
                ),
            )
        normalized[key] = value
    return normalized


def _actions_for_decision(decision: TurnDecision) -> tuple[ActionUnion, ...]:
    if decision.action is not None:
        return (decision.action,)
    if decision.action_batch is None or not decision.action_batch.calls:
        raise TurnkeyRefusal(
            "brain/empty-action-batch",
            "TurnDecision action_batch must contain at least one call.",
        )
    return tuple(_action_from_call(call) for call in decision.action_batch.calls)


def _decision_action_label(decision: TurnDecision) -> str:
    if decision.action is not None:
        return decision.action.kind
    count = 0 if decision.action_batch is None else len(decision.action_batch.calls)
    return f"action_batch[{count}]"


def _decision_action_payload(decision: TurnDecision) -> dict[str, object]:
    if decision.action is not None:
        return decision.action.model_dump(mode="json")
    assert decision.action_batch is not None
    return decision.action_batch.model_dump(mode="json")


async def _record_brain_event(
    *,
    sink: EventSink | None,
    records: list[dict[str, object]],
    invocation: TurnkeyInvocation,
    state: BrainState,
    event_kind: str,
    message: str,
    details: dict[str, object] | None = None,
    session_id: str | None = None,
    iteration: int | None = None,
) -> None:
    event = BrainEvent(
        event_kind=event_kind,
        timestamp=event_timestamp(),
        board_id=state.board_id,
        iteration=state.iteration if iteration is None else iteration,
        session_id=session_id if session_id is not None else _result_session_id(state),
        provider=invocation.provider,
        model=invocation.model,
        message=message,
        details=details or {},
    )
    record = event.to_record()
    records.append(record)
    await emit_event(sink, event)


async def _record_verification_event(
    *,
    sink: EventSink | None,
    records: list[dict[str, object]],
    invocation: TurnkeyInvocation,
    state: BrainState,
    reason: str,
) -> None:
    await _record_brain_event(
        sink=sink,
        records=records,
        invocation=invocation,
        state=state,
        event_kind="verification_state_update",
        message=f"Verification snapshot updated: {reason}",
        details={
            "reason": reason,
            "verification": state.verification.model_dump(mode="json"),
        },
    )


async def _record_provider_progress_updates(
    *,
    sink: EventSink | None,
    records: list[dict[str, object]],
    invocation: TurnkeyInvocation,
    state: BrainState,
    updates: tuple[ProviderProgressUpdate, ...],
) -> None:
    for update in updates:
        await _record_brain_event(
            sink=sink,
            records=records,
            invocation=invocation,
            state=state,
            event_kind="provider_progress",
            message=update.message,
            details={
                "stage": update.stage,
                **dict(update.details),
            },
        )


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


def _append_observation(
    state: BrainState,
    *,
    source: str,
    summary: str,
    evidence_excerpt: str,
) -> Observation:
    observation = Observation(
        observation_id=f"obs-{len(state.observations) + 1:03d}",
        source=source,
        summary=summary,
        evidence_excerpt=evidence_excerpt,
    )
    state.observations.append(observation)
    return observation


def _append_hypothesis(
    state: BrainState,
    *,
    summary: str,
    status: str,
    supporting_observation_ids: tuple[str, ...],
) -> Hypothesis:
    hypothesis = Hypothesis(
        hypothesis_id=f"hyp-{len(state.hypotheses) + 1:03d}",
        summary=summary,
        status=status,
        supporting_observation_ids=supporting_observation_ids,
    )
    state.hypotheses.append(hypothesis)
    return hypothesis


def _append_experiment(
    state: BrainState,
    *,
    purpose: str,
    action_summary: str,
    result: str,
) -> Experiment:
    experiment = Experiment(
        experiment_id=f"exp-{len(state.experiments) + 1:03d}",
        purpose=purpose,
        action_summary=action_summary,
        result=result,
    )
    state.experiments.append(experiment)
    return experiment


def _append_strategy_evaluation(
    state: BrainState,
    *,
    outcome: str,
    next_action: str,
) -> StrategyEvaluation:
    evaluation = StrategyEvaluation(
        strategy_id=f"strat-{len(state.strategy_evaluations) + 1:03d}",
        outcome=outcome,
        next_action=next_action,
    )
    state.strategy_evaluations.append(evaluation)
    return evaluation


def _record_decision_evidence(
    state: BrainState,
    decision: TurnDecision,
    *,
    result_text: str,
) -> None:
    observation = _append_observation(
        state,
        source="turn-decision",
        summary=decision.observation_summary,
        evidence_excerpt=result_text,
    )
    if decision.hypothesis:
        _append_hypothesis(
            state,
            summary=decision.hypothesis,
            status="open",
            supporting_observation_ids=(observation.observation_id,),
        )
    if decision.strategy_evaluation:
        _append_strategy_evaluation(
            state,
            outcome=decision.strategy_evaluation,
            next_action=_decision_action_label(decision),
        )


def _verification_snapshot_text(snapshot: VerificationSnapshot) -> str:
    return (
        f"flash={snapshot.flash_ok} "
        f"uart={snapshot.uart_ok} "
        f"symbol={snapshot.symbol_ok} "
        f"green={snapshot.green_check_ok}"
    )


def _compact_turn_text(text: str | None, *, limit: int = 320) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    if limit <= 3:
        return value[:limit]
    return value[: limit - 3].rstrip() + "..."


def _build_provider_memory_entry(
    *,
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    session_state: ProviderSessionState,
    state: BrainState,
    decision: TurnDecision,
    result_text: str,
    workspace: WorkspaceSession | None,
) -> ProviderMemoryEntry:
    flash_artifact, symbol_artifact = _default_artifacts(invocation, board)
    return ProviderMemoryEntry(
        turn_index=session_state.next_turn_index(),
        classification=decision.classification or state.last_classification,
        observation_summary=_compact_turn_text(decision.observation_summary),
        hypothesis=_compact_turn_text(decision.hypothesis) if decision.hypothesis else None,
        action_kind=_decision_action_label(decision),
        action_summary=_compact_turn_text(
            state.last_action_summary or _decision_action_label(decision)
        ),
        result_summary=_compact_turn_text(result_text),
        verification_snapshot=_verification_snapshot_text(state.verification),
        decision_rationale=(
            _compact_turn_text(decision.strategy_evaluation)
            if decision.strategy_evaluation
            else None
        ),
        action_payload=_decision_action_payload(decision),
        result_status=_memory_result_status(result_text),
        artifact_paths=tuple(
            str(path)
            for path in (
                flash_artifact,
                symbol_artifact,
                invocation.workspace_root,
            )
            if path is not None
        ),
        changed_files=tuple(workspace.changed_files()) if workspace is not None else (),
        codebase_summary=_compact_turn_text(_workspace_summary(workspace)),
        failed_hypotheses=tuple(
            hypothesis.summary
            for hypothesis in state.hypotheses
            if hypothesis.status not in {"open", "supported"}
        ),
        refused_or_blocked_paths=tuple(
            sorted((*state.refused_action_families, *state.blocked_action_families))
        ),
        acceptance_constraints=(
            "do not finalize healthy/fixed without successful run_green_check",
            "server-native board actions must route through governed MCP tools",
            "recovery-created provider sessions must be labeled as new",
        ),
    )


def _memory_result_status(result_text: str) -> ProviderMemoryResultStatus:
    if result_text.startswith("Refused ["):
        return "refusal"
    if result_text.startswith("Blocked ["):
        return "block"
    if "Error" in result_text or "failed" in result_text.lower() or "Traceback" in result_text:
        return "failure"
    if result_text.strip():
        return "success"
    return "unknown"


async def _commit_provider_memory(
    *,
    provider: DecisionProvider,
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
    decision: TurnDecision,
    result_text: str,
    provider_metadata: dict[str, object],
    workspace: WorkspaceSession | None,
    sink: EventSink | None,
    records: list[dict[str, object]],
) -> dict[str, object]:
    current_session = state.provider_session_state
    if current_session is None:
        raise TurnkeyLoopError("Provider session state was missing during memory commit.")
    memory_entry = _build_provider_memory_entry(
        invocation=invocation,
        board=board,
        session_state=current_session,
        state=state,
        decision=decision,
        result_text=result_text,
        workspace=workspace,
    )
    updated_session = append_memory_entry(current_session, memory_entry)
    compaction_plan = plan_memory_compaction(updated_session)
    model_summary_fallback = False
    summarizer_metadata: dict[str, object] | None = None
    fallback_reason: str | None = None
    if compaction_plan is not None:
        if updated_session.memory_mode == "model-summary":
            try:
                await _record_brain_event(
                    sink=sink,
                    records=records,
                    invocation=invocation,
                    state=state,
                    event_kind="provider_progress",
                    message="Starting provider-backed memory summary compaction.",
                    details={
                        "stage": "memory_summary",
                        "memory_mode": updated_session.memory_mode,
                        "evicted_turn_count": len(compaction_plan.evicted_entries),
                    },
                )
                prior_summary_text = (
                    updated_session.memory_summary.summary_text
                    if updated_session.memory_summary is not None
                    else ""
                )
                summary_result = await provider.summarize_memory(
                    session_state=updated_session,
                    prior_summary_text=prior_summary_text,
                    evicted_entries=compaction_plan.evicted_entries,
                )
                summarizer_metadata = dict(summary_result.provider_metadata)
                updated_session = apply_summary_compaction(
                    updated_session,
                    compaction_plan,
                    summary_text=summary_result.summary_text,
                    source="model-summary",
                )
            except Exception as exc:  # noqa: BLE001 - deterministic fallback is required
                model_summary_fallback = True
                fallback_reason = f"{type(exc).__name__}: {exc}"
                await _record_brain_event(
                    sink=sink,
                    records=records,
                    invocation=invocation,
                    state=state,
                    event_kind="provider_progress",
                    message="Provider-backed memory summary failed; falling back to deterministic compaction.",
                    details={
                        "stage": "memory_summary_fallback",
                        "fallback_reason": fallback_reason,
                    },
                )
                updated_session = apply_deterministic_compaction(
                    updated_session,
                    compaction_plan,
                    source="deterministic-fallback",
                )
        else:
            updated_session = apply_deterministic_compaction(
                updated_session,
                compaction_plan,
                source="deterministic",
            )
    memory_rendered_this_turn = bool(provider_metadata.get("memory_injected"))
    updated_session = advance_memory_sync_state(
        updated_session,
        memory_rendered_this_turn=memory_rendered_this_turn,
    )
    compaction_record: dict[str, object] = {
        "memory_mode": updated_session.memory_mode,
        "continuation_mode": updated_session.continuation_mode,
        "continuation_path": updated_session.last_continuation_path,
        "memory_entry_turn_index": memory_entry.turn_index,
        "memory_rendered_this_turn": memory_rendered_this_turn,
        "recent_memory_entry_count": len(updated_session.recent_memory_entries),
        "native_sync_every": updated_session.native_sync_every,
        "turns_since_last_memory_sync": updated_session.turns_since_last_memory_sync,
        "compaction_ran": compaction_plan is not None,
        "compaction_plan": compaction_plan.to_record() if compaction_plan is not None else None,
        "summary_source": (
            updated_session.memory_summary.source
            if updated_session.memory_summary is not None
            else None
        ),
        "summary_covered_through_turn": (
            updated_session.memory_summary.covered_through_turn
            if updated_session.memory_summary is not None
            else None
        ),
        "summary_char_count": (
            updated_session.memory_summary.char_count
            if updated_session.memory_summary is not None
            else 0
        ),
        "model_summary_fallback": model_summary_fallback,
        "summarizer": summarizer_metadata,
        "fallback_reason": fallback_reason,
    }
    updated_session = updated_session.with_updated_metadata(
        {
            "last_memory_entry_turn_index": memory_entry.turn_index,
            "last_memory_mode": updated_session.memory_mode,
            "last_continuation_path": updated_session.last_continuation_path,
            "last_memory_rendered": memory_rendered_this_turn,
            "last_compaction_ran": compaction_plan is not None,
            "last_model_summary_fallback": model_summary_fallback,
            "last_compaction_summary_source": compaction_record["summary_source"],
            "last_compaction_summary_char_count": compaction_record["summary_char_count"],
            "last_summarizer": summarizer_metadata,
            "last_summarizer_fallback_reason": fallback_reason,
        }
    )
    state.provider_session_state = updated_session
    await _record_brain_event(
        sink=sink,
        records=records,
        invocation=invocation,
        state=state,
        event_kind="provider_memory_update",
        message=f"Provider memory committed for turn {memory_entry.turn_index}.",
        details={
            "provider_session": updated_session.summary_record(),
            "memory_entry": memory_entry.to_record(),
            "compaction": compaction_record,
        },
    )
    return compaction_record


async def _record_model_native_host_boundary(
    *,
    invocation: TurnkeyInvocation,
    state: BrainState,
    workspace: WorkspaceSession | None,
    sink: EventSink | None,
    records: list[dict[str, object]],
) -> None:
    if workspace is None:
        return
    changed_files = workspace.changed_files()
    if not changed_files:
        return
    await _record_brain_event(
        sink=sink,
        records=records,
        invocation=invocation,
        state=state,
        event_kind="model_native_host_work_observed",
        message="Observed provider-native host work at a governed decision boundary.",
        details={"changed_files": list(changed_files)},
    )


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
    track_stagnation: bool = True,
) -> None:
    state.verification = VerificationSnapshot(
        flash_ok=flash_ok,
        uart_ok=uart_ok,
        symbol_ok=symbol_ok,
        green_check_ok=green_check_ok,
    )
    signature = state.verification_signature()
    if track_stagnation and state.pending_fix_evaluation:
        if signature == state.last_verification_signature:
            state.stagnant_fix_cycle_count += 1
        else:
            state.stagnant_fix_cycle_count = 0
        state.pending_fix_evaluation = False
    elif signature != state.last_verification_signature:
        state.stagnant_fix_cycle_count = 0
    state.last_verification_signature = signature


def _render_refusal(code: str, message: str) -> str:
    return f"Refused [{code}]: {message}"


def _provisional_run_id() -> str:
    return f"turnkey-{generate_session_id()}"


def _prepare_run_root(run_id: str) -> Path:
    run_root = RUNS_ROOT / run_id
    for relative in ("logs", "captured-serial", "applied-patches", "run-metadata"):
        (run_root / relative).mkdir(parents=True, exist_ok=True)
    return run_root


def _prepare_provider_runtime_context(
    *,
    run_id: str,
    provider: str,
    continuation_mode: ProviderContinuationMode,
    resume_requires_stable_workdir: bool,
    host_working_directory: Path | None = None,
) -> ProviderRuntimeContext:
    runtime_root = RUNS_ROOT / "_provider-runtime" / run_id / provider
    runtime_root.mkdir(parents=True, exist_ok=True)
    working_directory = host_working_directory or runtime_root
    return ProviderRuntimeContext(
        runtime_root=str(runtime_root),
        working_directory=str(working_directory),
        transport_metadata={
            "run_id": run_id,
            "provider": provider,
            "continuation_mode": continuation_mode,
            "resume_requires_stable_workdir": resume_requires_stable_workdir,
            "provider_runtime_root": str(runtime_root),
        },
    )


def _merge_tree(source_root: Path, destination_root: Path) -> None:
    for path in source_root.rglob("*"):
        relative = path.relative_to(source_root)
        target = destination_root / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        shutil.move(str(path), str(target))


def _promote_run_root(run_root: Path, session_id: str) -> Path:
    if run_root.name == session_id:
        return run_root
    target_root = RUNS_ROOT / session_id
    if target_root.exists():
        _merge_tree(target_root, run_root)
        shutil.rmtree(target_root)
    run_root.rename(target_root)
    return target_root


def _result_session_id(state: BrainState) -> str | None:
    if state.session_id is not None:
        return state.session_id
    if state.session_ids_seen:
        return state.session_ids_seen[-1]
    return None


def _tooling_failure_result(
    state: BrainState,
    *,
    summary: str,
    root_cause: str | None = None,
) -> TurnkeyRunResult:
    return TurnkeyRunResult(
        board_id=state.board_id,
        case_id=state.case_id,
        session_id=_result_session_id(state),
        final_status="blocked",
        classification="tooling_failure",
        root_cause=root_cause or summary,
        actions_taken=list(state.actions_taken),
        mcp_tools_used=list(state.mcp_tools_used),
        files_changed=[],
        recover_used=state.recover_used,
        verification=state.verification,
        summary=summary,
    )


def _parse_hex_text(text: str, *, label: str) -> int:
    candidate = text.strip()
    try:
        return int(candidate, 0)
    except ValueError as exc:
        raise RuntimeError(f"Could not parse {label} from tool response: {candidate}") from exc


def _extract_uart_excerpt(text: str) -> str:
    marker = "excerpt="
    index = text.find(marker)
    if index < 0:
        return text
    return text[index + len(marker) :].strip()


def _normalize_flash_path(
    path_value: object,
    *,
    workspace_root: Path | None,
) -> str | None:
    if not isinstance(path_value, str):
        return None
    normalized = path_value.strip()
    if not normalized:
        return None
    candidate = Path(normalized).expanduser()
    if candidate.is_absolute() or workspace_root is None:
        return str(candidate.resolve())
    return str((workspace_root / candidate).resolve())


async def _call_tool_with_timeout(
    client: object,
    tool_name: str,
    arguments: dict[str, object] | None,
    *,
    timeout_seconds: float,
) -> ToolTextResult:
    call_tool = getattr(client, "call_tool")
    try:
        signature = inspect.signature(call_tool)
    except (TypeError, ValueError):
        signature = None
    try:
        with anyio.fail_after(timeout_seconds):
            if signature is not None and "timeout_seconds" in signature.parameters:
                return cast(
                    ToolTextResult,
                    await call_tool(tool_name, arguments, timeout_seconds=timeout_seconds),
                )
            return cast(ToolTextResult, await call_tool(tool_name, arguments))
    except TimeoutError as exc:
        raise MCPClientError(f"Tool '{tool_name}' timed out after {timeout_seconds:.0f}s.") from exc


def _tool_timeout_seconds(
    tool_name: str,
    invocation: TurnkeyInvocation,
    effective_timeout_config: TurnkeyTimeoutConfig | None = None,
) -> float:
    return (effective_timeout_config or invocation.timeout_config).tool_timeout_seconds(
        tool_name,
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
        if (
            state.session_id is not None
            and arguments.get("board_id", board.board_id) == board.board_id
            and arguments.get("unique_id") in {None, ""}
            and arguments.get("target") is None
            and arguments.get("board_config") is None
        ):
            raise TurnkeyRefusal(
                "brain/redundant-connect",
                "Already connected to this board. Reuse the current session or disconnect first.",
            )
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
    elif action.tool_name == "read_memory":
        address = arguments.get("address")
        if isinstance(address, int):
            arguments["address"] = f"0x{address:08X}"
    elif action.tool_name == "flash_firmware":
        if "path" not in arguments and invocation.flash_artifact is not None:
            arguments["path"] = str(invocation.flash_artifact)
        elif "path" in arguments:
            normalized_path = _normalize_flash_path(
                arguments.get("path"),
                workspace_root=invocation.workspace_root,
            )
            if normalized_path is not None:
                arguments["path"] = normalized_path
    elif action.tool_name == "read_serial":
        if invocation.port is not None:
            arguments.setdefault("port", invocation.port)
        arguments.setdefault("read_seconds", invocation.serial_read_seconds)
        if arguments.get("expected_text") in {None, ""}:
            expected_text = invocation.expected_uart_substring or board.expected_uart_substring
            if expected_text:
                arguments["expected_text"] = expected_text
        if (
            invocation.mode == "benchmark"
            and invocation.case_kind in {"known_good", "injected_bug"}
            and "reset_on_open" not in arguments
        ):
            arguments["reset_on_open"] = True
    elif action.tool_name == "unlock_recover" and not invocation.recover_allowed:
        raise TurnkeyRefusal(
            "brain/recover-forbidden",
            "This task does not allow unlock_recover as a valid intervention.",
        )

    result = await _call_tool_with_timeout(
        client,
        action.tool_name,
        arguments,
        timeout_seconds=_tool_timeout_seconds(
            action.tool_name,
            invocation,
            state.effective_timeout_config,
        ),
    )
    state.register_tool_use(action.tool_name)
    state.actions_taken.append(action.tool_name)
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
    elif action.tool_name == "disconnect" and result.text.startswith("Disconnected"):
        state.register_disconnect()
    if action.tool_name == "flash_firmware" and result.text.startswith("Flashed "):
        _update_verification_state(
            state,
            flash_ok=True,
            uart_ok=state.verification.uart_ok,
            symbol_ok=state.verification.symbol_ok,
            green_check_ok=state.verification.green_check_ok,
            track_stagnation=False,
        )
    if action.tool_name == "read_serial":
        matched = result.text.startswith("UART matched")
        _update_verification_state(
            state,
            flash_ok=state.verification.flash_ok,
            uart_ok=matched,
            symbol_ok=state.verification.symbol_ok,
            green_check_ok=state.verification.green_check_ok
            if not matched
            else state.verification.green_check_ok,
        )
    if action.tool_name == "unlock_recover" and "Recover completed" in result.text:
        state.recover_used = True
    if action.tool_name in {
        "connect",
        "flash_firmware",
        "unlock_recover",
        "reset",
        "halt",
        "resume",
    }:
        _append_experiment(
            state,
            purpose=f"apply MCP tool `{action.tool_name}`",
            action_summary=state.last_action_summary or action.tool_name,
            result=result.text,
        )
    return result


def _execute_load_skills(action: LoadSkillsAction, state: BrainState) -> str:
    provider_state = state.provider_session_state
    runtime_context = provider_state.runtime_context if provider_state is not None else None
    if runtime_context is None:
        raise TurnkeyLoopError(
            "Provider runtime context is unavailable, so model-native skills cannot be loaded."
        )
    registry = ModelNativeSkillRegistry(MODEL_NATIVE_SKILL_ROOT)
    try:
        result = registry.load_skills(
            skill_ids=action.skill_ids,
            session_state=state.model_native_skills,
            runtime_root=Path(runtime_context.runtime_root),
            repo_root=REPO_ROOT,
            timeout_seconds=state.effective_timeout_config.external_command_seconds,
        )
    except ModelNativeSkillError as exc:
        state.model_native_skills = state.model_native_skills.with_failure(str(exc))
        raise
    state.model_native_skills = result.state
    state.actions_taken.append("load_skills:" + ",".join(action.skill_ids))
    state.last_action_summary = "load_skills(" + ",".join(action.skill_ids) + ")"
    state.last_result_text = result.render_result_text()
    return state.last_result_text


async def _execute_wait(action: WaitAction, state: BrainState) -> str:
    await anyio.sleep(action.seconds)
    state.actions_taken.append("wait")
    state.last_action_summary = f"wait({action.seconds})"
    state.last_result_text = f"Waited {action.seconds:.2f}s."
    return state.last_result_text


async def _execute_run_script(
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    client_actions: ClientActionStore,
    client: LocalMCPClient,
    action: RunScriptAction,
    state: BrainState,
) -> str:
    snapshot = client_actions.snapshot_action(action.name)
    if snapshot is None:
        raise TurnkeyRefusal(
            "brain/client-action-not-found",
            f"No session-scoped client action named {action.name!r}.",
        )

    async def call_governed_tool(tool_name: str, arguments: dict[str, object]) -> ToolTextResult:
        return await _execute_server_tool(
            invocation,
            board,
            state,
            client,
            ServerToolAction(tool_name=cast(AllowedServerToolName, tool_name), arguments=arguments),
        )

    server_api = GatedClientActionServer(
        call_governed_tool,
        allowed_tools={
            "connect",
            "disconnect",
            "get_board_info",
            "get_state",
            "halt",
            "resume",
            "reset",
            "read_core_register",
            "read_memory",
            "flash_firmware",
            "read_serial",
            "write_serial",
            "unlock_recover",
        },
    )
    result = await run_client_action(snapshot, inputs=action.inputs, server=server_api)
    state.actions_taken.append(f"run_script:{action.name}")
    state.last_action_summary = f"run_script({action.name}, sha256={snapshot.content_sha256})"
    state.last_result_text = f"Client action {action.name} completed: {result!r}"
    return state.last_result_text


async def _execute_batched_actions(
    *,
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
    client: LocalMCPClient,
    workspace: WorkspaceSession | None,
    client_actions: ClientActionStore,
    decision: TurnDecision,
    event_sink: EventSink | None,
    brain_events: list[dict[str, object]],
    brain_trace: list[dict[str, object]],
    iteration: int,
    run_root: Path,
) -> tuple[str, Path, TurnkeyRunResult | None]:
    result_parts: list[str] = []
    raw_result_text = ""
    result: TurnkeyRunResult | None = None
    is_batch = decision.action is None
    for index, action in enumerate(_actions_for_decision(decision), start=1):
        action_started = time.perf_counter()
        if isinstance(action, FinalizeAction):
            if is_batch:
                raise TurnkeyRefusal(
                    "brain/finalize-not-allowed-in-batch",
                    "Use finalize as a single action, not inside action_batch.",
                )
            result = _final_result_from_action(state, action, workspace)
            raw_result_text = result.summary
            await _record_brain_event(
                sink=event_sink,
                records=brain_events,
                invocation=invocation,
                state=state,
                event_kind="final_result",
                message=f"Run finalized as {result.final_status}.",
                details={"result": result.model_dump(mode="json")},
            )
            break

        await _record_brain_event(
            sink=event_sink,
            records=brain_events,
            invocation=invocation,
            state=state,
            event_kind="batch_action_start"
            if is_batch or not isinstance(action, ServerToolAction)
            else "tool_start",
            message=f"Starting action {index}: `{action.kind}`.",
            details={"batch_index": index, "action": action.model_dump(mode="json")},
        )

        refused_before = set(state.refused_action_families)
        blocked_before = set(state.blocked_action_families)
        if isinstance(action, ServerToolAction):
            if action.tool_name == "connect" and state.pending_server_timeout_sync is not None:
                await sync_pending_server_timeouts(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    client=client,
                    reason="before-connect",
                )
            action_result = await _execute_server_tool(invocation, board, state, client, action)
            result_text = action_result.text
            if state.session_id is not None:
                run_root = _promote_run_root(run_root, state.session_id)
            if action.tool_name == "disconnect" and state.pending_server_timeout_sync is not None:
                await sync_pending_server_timeouts(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    client=client,
                    reason="after-disconnect",
                )
            if invocation.mode == "benchmark" and len(state.session_ids_seen) > 1:
                result = _blocked_result(
                    state,
                    classification=decision.classification or "observability_fault",
                    code="benchmark/reconnect-not-allowed",
                    message="The turnkey client opened more than one MCP session during a benchmark case.",
                )
                result_text = result.summary
            if action.tool_name == "flash_firmware" and action_result.text.startswith("Flashed "):
                await _record_verification_event(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    reason="flash succeeded",
                )
            if action.tool_name == "read_serial":
                await _record_verification_event(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    reason="UART verification attempt completed",
                )
            event_details: dict[str, object] = {
                "batch_index": index,
                "tool_name": action.tool_name,
                "arguments": action.arguments,
                "normalized_action_summary": state.last_action_summary,
                "result_text": action_result.text,
                "refusal_code": action_result.refusal_code,
                "blocked_code": action_result.blocked_code,
                "probe_uid": action_result.probe_uid,
                "route_used": action_result.route_used,
            }
        elif isinstance(action, WaitAction):
            result_text = await _execute_wait(action, state)
            event_details = {"batch_index": index, "result_text": result_text}
        elif isinstance(action, RunScriptAction):
            result_text = await _execute_run_script(
                invocation, board, client_actions, client, action, state
            )
            event_details = {"batch_index": index, "result_text": result_text}
        elif isinstance(action, LoadSkillsAction):
            result_text = _execute_load_skills(action, state)
            event_details = {
                "batch_index": index,
                "result_text": result_text,
                "model_native_skills": state.model_native_skills.to_record(),
            }
        elif isinstance(action, RunGreenCheckAction):
            result_text = await _execute_green_check(invocation, board, state, client, workspace)
            await _record_verification_event(
                sink=event_sink,
                records=brain_events,
                invocation=invocation,
                state=state,
                reason="green check completed",
            )
            event_details = {
                "batch_index": index,
                "result_text": result_text,
                "verification": state.verification.model_dump(mode="json"),
            }
        else:
            raise TurnkeyLoopError(f"Unhandled action kind: {action.kind}")

        duration_ms = int((time.perf_counter() - action_started) * 1000)
        event_details["duration_ms"] = duration_ms
        await _record_brain_event(
            sink=event_sink,
            records=brain_events,
            invocation=invocation,
            state=state,
            event_kind="batch_action_complete"
            if is_batch or not isinstance(action, ServerToolAction)
            else "tool_complete",
            message=f"Completed action {index}: `{action.kind}`.",
            details=event_details,
        )
        if state.session_id is not None and not is_batch:
            await _record_brain_event(
                sink=event_sink,
                records=brain_events,
                invocation=invocation,
                state=state,
                event_kind="session_state",
                message=f"Active session is now {state.session_id}.",
                details={
                    "session_id": state.session_id,
                    "run_root": str(run_root),
                    "probe_uid": state.probe_uid,
                    "route_used": state.route_used,
                },
            )
        if is_batch:
            brain_trace.append(
                _brain_trace_record(
                    iteration=iteration,
                    action_kind=f"batch[{index}].{action.kind}",
                    payload=action.model_dump(mode="json"),
                    result_text=result_text,
                )
            )
        raw_result_text = result_text
        result_parts.append(f"{index}. {action.kind}: {result_text}")

        if result is not None:
            break
        if (
            state.refused_action_families != refused_before
            or state.blocked_action_families != blocked_before
        ):
            break
        if (
            isinstance(action, ServerToolAction)
            and action.tool_name == "read_serial"
            and not result_text.startswith("UART matched")
        ):
            break

    return ("\n".join(result_parts) if is_batch else raw_result_text), run_root, result


async def _execute_green_check(
    invocation: TurnkeyInvocation,
    board: BoardConfig,
    state: BrainState,
    client: LocalMCPClient,
    workspace: WorkspaceSession | None,
) -> str:
    flash_artifact, symbol_artifact = _green_check_artifacts(invocation, board)
    build_text: str | None = None
    if workspace is not None and workspace.build_command:
        try:
            build = workspace.run_build(
                timeout_seconds=state.effective_timeout_config.build_seconds
            )
        except WorkspaceError as exc:
            changed_files = workspace.changed_files()
            _update_build_failure_state(state, str(exc), changed_files)
            state.last_action_summary = "run_green_check(build)"
            state.last_result_text = f"WorkspaceError: {exc}"
            raise
        state.build_count += 1
        build_text = (
            f"green-check build exit_code={build.exit_code} duration={build.duration_seconds:.2f}s"
        )
        if build.exit_code != 0:
            failure_text = (
                f"Build failed with exit code {build.exit_code}.\n"
                f"stdout:\n{build.stdout}\n"
                f"stderr:\n{build.stderr}"
            )
            changed_files = workspace.changed_files()
            _update_build_failure_state(state, failure_text, changed_files)
            state.last_action_summary = "run_green_check(build)"
            state.last_result_text = failure_text
            raise RuntimeError(failure_text)

    flash_result = await _call_tool_with_timeout(
        client,
        "flash_firmware",
        {"path": str(flash_artifact), "halt_after_reset": True},
        timeout_seconds=_tool_timeout_seconds(
            "flash_firmware",
            invocation,
            state.effective_timeout_config,
        ),
    )
    if flash_result.refusal_code or flash_result.blocked_code:
        state.last_result_text = flash_result.text
        return flash_result.text

    pc_result = await _call_tool_with_timeout(
        client,
        "read_core_register",
        {"name": "pc"},
        timeout_seconds=state.effective_timeout_config.default_tool_seconds,
    )
    if pc_result.refusal_code or pc_result.blocked_code:
        state.last_result_text = pc_result.text
        return pc_result.text
    pc = _parse_hex_text(pc_result.text, label="pc")

    symbol_ok = True
    symbol_name = invocation.expected_symbol_name
    resolved_symbol_name = "(skipped)"
    resolved_symbol_value: int | None = None
    if symbol_name is not None:
        resolved_symbol = resolve_symbol(symbol_artifact, symbol_name)
        value_result = await _call_tool_with_timeout(
            client,
            "read_memory",
            {
                "address": f"0x{resolved_symbol.address:08X}",
                "word_size": 32,
            },
            timeout_seconds=state.effective_timeout_config.default_tool_seconds,
        )
        if value_result.refusal_code or value_result.blocked_code:
            state.last_result_text = value_result.text
            return value_result.text
        resolved_symbol_name = resolved_symbol.name
        resolved_symbol_value = _parse_hex_text(
            value_result.text,
            label=f"symbol {resolved_symbol.name}",
        )
        if (
            invocation.expected_symbol_value_u32 is not None
            and resolved_symbol_value != invocation.expected_symbol_value_u32
        ):
            _update_verification_state(
                state,
                flash_ok=True,
                uart_ok=state.verification.uart_ok,
                symbol_ok=False,
                green_check_ok=False,
            )
            raise RuntimeError(
                f"{resolved_symbol.name} value mismatch: actual=0x{resolved_symbol_value:08X} "
                f"expected=0x{invocation.expected_symbol_value_u32:08X}"
            )

    expected_text = invocation.expected_uart_substring or board.expected_uart_substring
    read_serial_args: dict[str, object] = {
        "read_seconds": invocation.serial_read_seconds,
        "reset_on_open": True,
    }
    if expected_text:
        read_serial_args["expected_text"] = expected_text
    if invocation.port is not None:
        read_serial_args["port"] = invocation.port

    serial_result = await _call_tool_with_timeout(
        client,
        "read_serial",
        read_serial_args,
        timeout_seconds=_tool_timeout_seconds(
            "read_serial",
            invocation,
            state.effective_timeout_config,
        ),
    )
    if serial_result.refusal_code or serial_result.blocked_code:
        state.last_result_text = serial_result.text
        return serial_result.text
    if not serial_result.text.startswith("UART matched"):
        _update_verification_state(
            state,
            flash_ok=True,
            uart_ok=False,
            symbol_ok=symbol_ok,
            green_check_ok=False,
        )
        raise RuntimeError(serial_result.text)

    _update_verification_state(
        state,
        flash_ok=True,
        uart_ok=True,
        symbol_ok=symbol_ok,
        green_check_ok=symbol_ok,
    )
    state.actions_taken.append("run_green_check")
    state.last_action_summary = "run_green_check()"
    symbol_fragment = (
        f"symbol={resolved_symbol_name}=0x{resolved_symbol_value:08X}, "
        if resolved_symbol_value is not None
        else ""
    )
    state.last_result_text = (
        f"Green check passed on {board.board_id}: pc=0x{pc:08X}, "
        f"{symbol_fragment}uart_excerpt={_extract_uart_excerpt(serial_result.text)}"
    )
    if build_text is not None:
        state.last_result_text = f"{build_text}; {state.last_result_text}"
    _append_experiment(
        state,
        purpose="runner-owned final verification",
        action_summary="run_green_check()",
        result=state.last_result_text,
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
        session_id=_result_session_id(state),
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
    if (
        action.final_status in {"healthy_confirmed", "fixed"}
        and not state.verification.green_check_ok
    ):
        raise TurnkeyRefusal(
            "brain/finalize-without-green-check",
            "A successful run_green_check is required before finalizing a healthy or fixed result.",
        )
    changed_files = list(workspace.changed_files()) if workspace is not None else []
    return TurnkeyRunResult(
        board_id=state.board_id,
        case_id=state.case_id,
        session_id=_result_session_id(state),
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
    run_root = execution.run_root
    if run_root is None:
        return
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
    with (run_root / "logs" / "brain_events.jsonl").open("w", encoding="utf-8") as handle:
        for record in execution.brain_events:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")
    if workspace is not None:
        workspace.write_diff(run_root / "applied-patches" / "turnkey.diff")
    if execution.client_action_snapshots:
        executed_names = {
            item.removeprefix("run_script:")
            for item in execution.result.actions_taken
            if item.startswith("run_script:")
        }
        client_action_records = [
            {
                "name": snapshot.name,
                "relative_path": snapshot.relative_path,
                "description": snapshot.description,
                "content_sha256": snapshot.content_sha256,
                "executed": snapshot.name in executed_names,
            }
            for snapshot in execution.client_action_snapshots
        ]
        (run_root / "run-metadata" / "client_actions.json").write_text(
            json.dumps(client_action_records, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


async def _tooling_failure_execution(
    invocation: TurnkeyInvocation,
    *,
    summary: str,
    root_cause: str,
    event_sink: EventSink | None,
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
    provisional_run_id = _provisional_run_id()
    run_root = _prepare_run_root(provisional_run_id)
    provider_runtime_context = _prepare_provider_runtime_context(
        run_id=provisional_run_id,
        provider=invocation.provider,
        continuation_mode=_continuation_mode_for_provider(invocation.provider),
        resume_requires_stable_workdir=invocation.provider == "claude-cli",
        host_working_directory=workspace.root
        if invocation.provider == "claude-cli" and workspace is not None
        else None,
    )
    state = BrainState(
        run_mode=invocation.mode,
        board_id=board.board_id,
        task=invocation.task,
        case_id=invocation.case_id,
        case_kind=invocation.case_kind,
        selected_skill_ids=tuple(skill.skill_id for skill in selected_skills),
        provider_session_state=make_provider_session_state(
            provider=invocation.provider,
            model=invocation.model,
            memory_mode=invocation.memory_mode,
            continuation_mode=_continuation_mode_for_provider(invocation.provider),
            native_sync_every=invocation.native_sync_every,
            runtime_context=provider_runtime_context,
        ),
        effective_timeout_config=invocation.timeout_config,
        effective_max_iters=invocation.max_iters,
    )
    prompt_bundle = ProviderPromptBundle(
        system_instructions=_build_instructions(invocation),
        tool_schema_text="Curated MCP tool index (compact):\n(tool metadata unavailable because the run failed before MCP startup)",
        provider_memory_text="",
        turn_context_text=_build_turn_prompt(invocation, board, state, skills_text, workspace),
        turn_decision_schema_text=f"TurnDecision JSON schema:\n{decision_schema_text()}",
    )
    brain_events: list[dict[str, object]] = []
    await _record_brain_event(
        sink=event_sink,
        records=brain_events,
        invocation=invocation,
        state=state,
        event_kind="run_start",
        message=f"Turnkey run started for {board.board_id}.",
        details={
            "run_mode": invocation.mode,
            "case_id": invocation.case_id,
            "case_kind": invocation.case_kind,
            "selected_skill_ids": [skill.skill_id for skill in selected_skills],
            "provider_runtime_context": provider_runtime_context.summary_record(),
        },
        iteration=0,
    )
    result = _tooling_failure_result(state, summary=summary, root_cause=root_cause)
    await _record_brain_event(
        sink=event_sink,
        records=brain_events,
        invocation=invocation,
        state=state,
        event_kind="unexpected_failure",
        message=result.summary,
        details={"phase": "provider_setup"},
        iteration=0,
    )
    await _record_brain_event(
        sink=event_sink,
        records=brain_events,
        invocation=invocation,
        state=state,
        event_kind="final_result",
        message=f"Run completed as {result.final_status}.",
        details={"result": result.model_dump(mode="json")},
        iteration=0,
    )
    execution = TurnkeyExecution(
        invocation=invocation,
        board=board,
        result=result,
        state=state,
        run_root=run_root,
        prompt_text=prompt_bundle.full_prompt_text(),
        request_payload=request_payload,
        selected_skills=selected_skills,
        model_turns=(),
        brain_trace=(),
        brain_events=tuple(brain_events),
    )
    _persist_turnkey_artifacts(execution, workspace)
    return execution


async def run_turnkey(
    invocation: TurnkeyInvocation,
    *,
    provider: DecisionProvider,
    client_factory: Callable[[], LocalMCPClient] | None = None,
    client_actions: ClientActionStore | None = None,
    event_sink: EventSink | None = None,
    provider_resume_recovery: ProviderResumeRecoveryHandler | None = None,
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
    provisional_run_id = _provisional_run_id()
    run_root = _prepare_run_root(provisional_run_id)
    provider_runtime_context = _prepare_provider_runtime_context(
        run_id=provisional_run_id,
        provider=invocation.provider,
        continuation_mode=provider.capabilities.continuation_mode,
        resume_requires_stable_workdir=provider.capabilities.resume_requires_stable_workdir,
        host_working_directory=workspace.root
        if provider.capabilities.resume_requires_stable_workdir and workspace is not None
        else None,
    )
    state = BrainState(
        run_mode=invocation.mode,
        board_id=board.board_id,
        task=invocation.task,
        case_id=invocation.case_id,
        case_kind=invocation.case_kind,
        selected_skill_ids=tuple(skill.skill_id for skill in selected_skills),
        provider_session_state=make_provider_session_state(
            provider=invocation.provider,
            model=invocation.model,
            memory_mode=invocation.memory_mode,
            continuation_mode=provider.capabilities.continuation_mode,
            native_sync_every=invocation.native_sync_every,
            runtime_context=provider_runtime_context,
        ),
        provider_capabilities=provider.capabilities,
        effective_timeout_config=invocation.timeout_config,
        effective_max_iters=invocation.max_iters,
    )
    result: TurnkeyRunResult | None = None
    model_turns: list[dict[str, object]] = []
    brain_trace: list[dict[str, object]] = []
    brain_events: list[dict[str, object]] = []
    client_action_store = client_actions or InMemoryClientActionStore()
    client_action_snapshots = snapshot_all_actions(client_action_store)
    initial_prompt_text = ""

    await _record_brain_event(
        sink=event_sink,
        records=brain_events,
        invocation=invocation,
        state=state,
        event_kind="run_start",
        message=f"Turnkey run started for {board.board_id}.",
        details={
            "run_mode": invocation.mode,
            "case_id": invocation.case_id,
            "case_kind": invocation.case_kind,
            "selected_skill_ids": [skill.skill_id for skill in selected_skills],
            "provider_runtime_context": provider_runtime_context.summary_record(),
        },
        iteration=0,
    )
    if invocation.timeout_proposal is not None or invocation.iteration_estimate is not None:
        await apply_invocation_timeout_policy(
            sink=event_sink,
            records=brain_events,
            invocation=invocation,
            state=state,
        )
    resolved_client_factory = client_factory or (
        lambda: LocalMCPClient(
            startup_timeout_seconds=state.effective_timeout_config.mcp_startup_seconds
        )
    )

    try:
        async with resolved_client_factory() as client:
            if state.pending_server_timeout_sync is not None and state.session_id is None:
                await sync_pending_server_timeouts(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    client=client,
                    reason="bootstrap-before-connect",
                )
            tool_schema_bundle = build_tool_schema_bundle(await client.list_tools())
            state.tool_schema_summary = tool_schema_bundle.to_record()
            iteration = 1
            while iteration <= state.effective_max_iters:
                state.iteration = iteration
                prompt_bundle = _build_prompt_bundle(
                    invocation=invocation,
                    board=board,
                    state=state,
                    skills_text=skills_text,
                    workspace=workspace,
                    tool_schema_bundle=tool_schema_bundle,
                    client_actions=client_action_store,
                )
                if not initial_prompt_text:
                    initial_prompt_text = prompt_bundle.full_prompt_text()
                await _record_brain_event(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    event_kind="provider_turn_start",
                    message=f"Provider turn {iteration} started.",
                    details={
                        "turn_prompt_length": len(prompt_bundle.turn_context_text),
                        "tool_schema_hash": tool_schema_bundle.schema_hash,
                        "provider_session": state.provider_session_state.summary_record()
                        if state.provider_session_state is not None
                        else None,
                    },
                )
                provider_started = time.perf_counter()
                provider_session_for_turn = (
                    state.provider_session_state
                    or make_provider_session_state(
                        provider=invocation.provider,
                        model=invocation.model,
                        memory_mode=invocation.memory_mode,
                        continuation_mode=provider.capabilities.continuation_mode,
                        native_sync_every=invocation.native_sync_every,
                    )
                )
                provider_turn: ProviderTurn | None = None
                while provider_turn is None:
                    try:
                        with anyio.fail_after(state.effective_timeout_config.provider_seconds):
                            provider_turn = await provider.next_decision(
                                prompt_bundle=prompt_bundle,
                                session_state=provider_session_for_turn,
                            )
                    except ProviderResumeFailure as exc:
                        failure_record = exc.to_record()
                        await _record_brain_event(
                            sink=event_sink,
                            records=brain_events,
                            invocation=invocation,
                            state=state,
                            event_kind="provider_resume_failed",
                            message=(
                                "Provider session resume failed; no replacement "
                                "provider session has been started."
                            ),
                            details=failure_record,
                        )
                        if provider_resume_recovery is None:
                            result = _tooling_failure_result(
                                state,
                                summary=(f"Blocked [turnkey/provider-resume-failed]: {exc}"),
                                root_cause=(
                                    "Provider resume failed and the headless "
                                    "runtime failed closed without starting a "
                                    "replacement provider session."
                                ),
                            )
                            break
                        choice = provider_resume_recovery(exc)
                        await _record_brain_event(
                            sink=event_sink,
                            records=brain_events,
                            invocation=invocation,
                            state=state,
                            event_kind="provider_resume_recovery_choice",
                            message=f"Provider resume recovery choice: {choice}.",
                            details={
                                "choice": choice,
                                "failure": failure_record,
                            },
                        )
                        if choice == "retry":
                            provider_session_for_turn = (
                                state.provider_session_state or provider_session_for_turn
                            )
                            continue
                        if choice == "new-session-from-memory":
                            provider_session_for_turn = with_provider_resume_recovery_request(
                                state.provider_session_state or provider_session_for_turn,
                                action="new-session-from-memory",
                                failure=exc.record,
                            )
                            state.provider_session_state = provider_session_for_turn
                            continue
                        result = _tooling_failure_result(
                            state,
                            summary=(
                                "Blocked [turnkey/provider-resume-aborted]: "
                                "operator aborted after provider session resume failure."
                            ),
                            root_cause=(
                                "Provider resume failed and the operator chose "
                                "to abort without starting a replacement "
                                "provider session."
                            ),
                        )
                        break
                    except Exception as exc:  # noqa: BLE001 - provider/runtime failures become saved runs
                        result = _tooling_failure_result(
                            state,
                            summary=f"Blocked [turnkey/provider-failed]: {type(exc).__name__}: {exc}",
                            root_cause=f"Provider turn failed before a board diagnosis was completed: {type(exc).__name__}: {exc}",
                        )
                        await _record_brain_event(
                            sink=event_sink,
                            records=brain_events,
                            invocation=invocation,
                            state=state,
                            event_kind="unexpected_failure",
                            message=result.summary,
                            details={"error_type": type(exc).__name__, "phase": "provider_turn"},
                        )
                        break
                if result is not None:
                    break
                if provider_turn is None:
                    break
                provider_duration_ms = int((time.perf_counter() - provider_started) * 1000)
                state.provider_session_state = provider_turn.session_state
                decision = provider_turn.decision
                await _record_provider_progress_updates(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    updates=provider_turn.progress_updates,
                )
                await _record_brain_event(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    event_kind="provider_turn_complete",
                    message=f"Provider turn {iteration} completed.",
                    details={
                        "duration_ms": provider_duration_ms,
                        "response_id": provider_turn.response_id,
                        "provider_metadata": provider_turn.provider_metadata,
                        "provider_session": provider_turn.session_state.summary_record(),
                        "tool_schema_hash": tool_schema_bundle.schema_hash,
                        "raw_output": provider_turn.output_text,
                        "decision": provider_turn.decision.model_dump(mode="json"),
                    },
                )
                await _record_model_native_host_boundary(
                    invocation=invocation,
                    state=state,
                    workspace=workspace,
                    sink=event_sink,
                    records=brain_events,
                )
                if decision.timeout_proposal is not None or decision.iteration_estimate is not None:
                    await apply_turn_timeout_policy(
                        sink=event_sink,
                        records=brain_events,
                        invocation=invocation,
                        state=state,
                        client=client,
                        decision=decision,
                    )

                try:
                    result_text, run_root, action_result = await _execute_batched_actions(
                        invocation=invocation,
                        board=board,
                        state=state,
                        client=client,
                        workspace=workspace,
                        client_actions=client_action_store,
                        decision=decision,
                        event_sink=event_sink,
                        brain_events=brain_events,
                        brain_trace=brain_trace,
                        iteration=iteration,
                        run_root=run_root,
                    )
                    if action_result is not None:
                        result = action_result
                except TurnkeyRefusal as exc:
                    result_text = _render_refusal(exc.code, exc.message)
                    state.refused_action_families.add(_decision_action_label(decision))
                    state.last_action_summary = _decision_action_label(decision)
                    state.last_result_text = result_text
                    await _record_brain_event(
                        sink=event_sink,
                        records=brain_events,
                        invocation=invocation,
                        state=state,
                        event_kind="refusal",
                        message=result_text,
                        details={
                            "code": exc.code,
                            "action_kind": _decision_action_label(decision),
                        },
                    )
                except (WorkspaceError, MCPClientError, RuntimeError) as exc:
                    result_text = f"{type(exc).__name__}: {exc}"
                    state.last_action_summary = _decision_action_label(decision)
                    state.last_result_text = result_text
                    event_kind = (
                        "block"
                        if isinstance(exc, RuntimeError) and result_text.startswith("Blocked [")
                        else "unexpected_failure"
                    )
                    await _record_brain_event(
                        sink=event_sink,
                        records=brain_events,
                        invocation=invocation,
                        state=state,
                        event_kind=event_kind,
                        message=result_text,
                        details={
                            "error_type": type(exc).__name__,
                            "action_kind": _decision_action_label(decision),
                        },
                    )

                brain_trace.append(
                    _brain_trace_record(
                        iteration=iteration,
                        action_kind=_decision_action_label(decision),
                        payload=_decision_action_payload(decision),
                        result_text=result_text,
                    )
                )
                _record_decision_evidence(state, decision, result_text=result_text)
                _update_observation_state(state, decision, result_text)
                compaction_record = await _commit_provider_memory(
                    provider=provider,
                    invocation=invocation,
                    board=board,
                    state=state,
                    decision=decision,
                    result_text=result_text,
                    provider_metadata=provider_turn.provider_metadata,
                    workspace=workspace,
                    sink=event_sink,
                    records=brain_events,
                )
                model_turns.append(
                    _model_turn_record(
                        iteration,
                        provider_turn,
                        prompt_bundle,
                        committed_session_state=state.provider_session_state,
                        compaction_record=compaction_record,
                    )
                )
                blocked = _check_local_convergence(state)
                if blocked is not None:
                    result = blocked
                    await _record_brain_event(
                        sink=event_sink,
                        records=brain_events,
                        invocation=invocation,
                        state=state,
                        event_kind="block",
                        message=blocked.summary,
                        details={
                            "code": blocked.summary.split("]:", 1)[0].replace("Blocked [", "")
                        },
                    )
                    break
                if result is not None:
                    break
                iteration += 1

            if result is None:
                result = _blocked_result(
                    state,
                    classification=state.last_classification or "observability_fault",
                    code="brain/max-iters",
                    message=f"Reached effective_max_iters={state.effective_max_iters} without a final answer.",
                )
                await _record_brain_event(
                    sink=event_sink,
                    records=brain_events,
                    invocation=invocation,
                    state=state,
                    event_kind="block",
                    message=result.summary,
                    details={"code": "brain/max-iters"},
                )

            if state.session_id is not None:
                run_root = _promote_run_root(run_root, state.session_id)
                try:
                    await _call_tool_with_timeout(
                        client,
                        "disconnect",
                        {},
                        timeout_seconds=state.effective_timeout_config.default_tool_seconds,
                    )
                    state.register_disconnect()
                    await _record_brain_event(
                        sink=event_sink,
                        records=brain_events,
                        invocation=invocation,
                        state=state,
                        event_kind="session_state",
                        message="Disconnected from active session.",
                        details={"session_ids_seen": list(state.session_ids_seen)},
                    )
                except MCPClientError as exc:
                    cleanup_message = (
                        "Blocked [turnkey/final-disconnect-failed]: "
                        f"final board-session cleanup failed: {exc}"
                    )
                    result = _tooling_failure_result(
                        state,
                        summary=cleanup_message,
                        root_cause=(
                            "The turnkey loop produced a result but could not close the "
                            f"active board session {state.session_id!r}: {exc}"
                        ),
                    )
                    await _record_brain_event(
                        sink=event_sink,
                        records=brain_events,
                        invocation=invocation,
                        state=state,
                        event_kind="unexpected_failure",
                        message=cleanup_message,
                        details={
                            "error_type": type(exc).__name__,
                            "phase": "final_disconnect",
                            "session_id": state.session_id,
                            "session_ids_seen": list(state.session_ids_seen),
                        },
                    )

    except MCPClientError as exc:
        result = _tooling_failure_result(
            state,
            summary=f"Blocked [turnkey/mcp-startup-failed]: {exc}",
            root_cause=f"MCP startup failed before the first tool call: {exc}",
        )
        await _record_brain_event(
            sink=event_sink,
            records=brain_events,
            invocation=invocation,
            state=state,
            event_kind="unexpected_failure",
            message=result.summary,
            details={"error_type": type(exc).__name__, "phase": "mcp_startup"},
        )

    if result is None:
        result = _tooling_failure_result(
            state,
            summary="Blocked [turnkey/unexpected-run-state]: the turnkey loop exited without a result.",
            root_cause="The turnkey loop ended without producing a final result.",
        )

    if not brain_events or brain_events[-1].get("event_kind") != "final_result":
        await _record_brain_event(
            sink=event_sink,
            records=brain_events,
            invocation=invocation,
            state=state,
            event_kind="final_result",
            message=f"Run completed as {result.final_status}.",
            details={"result": result.model_dump(mode="json")},
        )

    if not initial_prompt_text:
        initial_prompt_text = ProviderPromptBundle(
            system_instructions=_build_instructions(invocation),
            tool_schema_text="Curated MCP tool index (compact):\n(tool metadata unavailable because MCP startup did not complete)",
            provider_memory_text="",
            turn_context_text=_build_turn_prompt(
                invocation,
                board,
                state,
                skills_text,
                workspace,
                client_action_store,
            ),
            turn_decision_schema_text=f"TurnDecision JSON schema:\n{decision_schema_text()}",
        ).full_prompt_text()

    execution = TurnkeyExecution(
        invocation=invocation,
        board=board,
        result=result,
        state=state,
        run_root=run_root,
        prompt_text=initial_prompt_text,
        request_payload=request_payload,
        selected_skills=selected_skills,
        model_turns=tuple(model_turns),
        brain_trace=tuple(brain_trace),
        brain_events=tuple(brain_events),
        client_action_snapshots=client_action_snapshots,
    )
    _persist_turnkey_artifacts(execution, workspace)
    return execution


async def run_turnkey_with_openai(
    invocation: TurnkeyInvocation,
    *,
    api_key: str,
    event_sink: EventSink | None = None,
    provider_resume_recovery: ProviderResumeRecoveryHandler | None = None,
    client_actions: ClientActionStore | None = None,
) -> TurnkeyExecution:
    config = BrainProviderConfig(provider="openai-api", api_key=api_key, model=invocation.model)
    return await run_turnkey_with_provider(
        invocation,
        provider_config=config,
        event_sink=event_sink,
        provider_resume_recovery=provider_resume_recovery,
        client_actions=client_actions,
    )


async def run_turnkey_with_provider(
    invocation: TurnkeyInvocation,
    *,
    provider_config: BrainProviderConfig,
    event_sink: EventSink | None = None,
    provider_resume_recovery: ProviderResumeRecoveryHandler | None = None,
    client_actions: ClientActionStore | None = None,
) -> TurnkeyExecution:
    try:
        provider = create_decision_provider(provider_config)
    except Exception as exc:  # noqa: BLE001 - normalize expected provider/runtime setup failures
        return await _tooling_failure_execution(
            invocation,
            summary=f"Blocked [turnkey/provider-setup-failed]: {type(exc).__name__}: {exc}",
            root_cause=f"Provider setup failed before any board session was created: {type(exc).__name__}: {exc}",
            event_sink=event_sink,
        )
    return await run_turnkey(
        invocation,
        provider=provider,
        event_sink=event_sink,
        provider_resume_recovery=provider_resume_recovery,
        client_actions=client_actions,
    )
