"""Deterministic turnkey runner for health, diagnosis, and reference-contract repair."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import re
import subprocess
from pathlib import Path
import sys
import time
from uuid import uuid4

from pyocd_debug_mcp.board_config import (
    DEFAULT_BOARD_CONFIG_DIR,
    BoardConfig,
    load_selected_board_configs,
)
from pyocd_debug_mcp.brain.mcp_client import ServerCommand, StdioToolClient, ToolClientProtocol
from pyocd_debug_mcp.brain.models import (
    Experiment,
    Hypothesis,
    MutableRunState,
    Observation,
    PreparedRunContext,
    SkillSpec,
    SkillStep,
    StepResult,
    StrategyEvaluation,
    TurnkeyRunRequest,
    TurnkeyRunResult,
)
from pyocd_debug_mcp.brain.skills import DEFAULT_SKILLS_ROOT, render_template, select_skill
from pyocd_debug_mcp.reference_artifacts import REPO_ROOT, resolve_reference_artifacts

TURNKEY_RUN_ROOT = REPO_ROOT / "runs" / "turnkey"
SESSION_ID_PATTERN = re.compile(r"session_id=([A-Za-z0-9._-]+)")
SYMBOL_VALUE_PATTERN = re.compile(r"value_u32=(0x[0-9A-Fa-f]+)")
REFERENCE_MAIN_RELATIVE = Path("src") / "src" / "main.c"
WORKFLOW_STATIC = "static_mcp_sequence"
WORKFLOW_DIAGNOSE = "reference_contract_diagnose"
WORKFLOW_REPAIR = "reference_contract_repair"


class TurnkeyRunError(Exception):
    """Raised when the turnkey runner cannot prepare or complete a run."""


@dataclass(frozen=True)
class ReferenceContractDiagnosis:
    """Typed outcome from a reference-contract probe pass."""

    classification: str
    root_cause: str
    final_status: str
    symbol_ok: bool
    uart_ok: bool


def _default_server_command() -> ServerCommand:
    from pyocd_debug_mcp.brain.mcp_client import default_server_command

    return default_server_command()


def _load_board(board_id: str) -> BoardConfig:
    boards = load_selected_board_configs(DEFAULT_BOARD_CONFIG_DIR, requested_ids=[board_id])
    if len(boards) != 1:
        raise TurnkeyRunError(f"Expected exactly one board config for '{board_id}'")
    return boards[0]


def _resolve_optional_path(
    value: str | None,
    *,
    workspace_root: Path | None,
) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        if workspace_root is not None:
            path = workspace_root / path
        else:
            path = REPO_ROOT / path
    return path.resolve()


def _reference_source_root(board_id: str) -> Path:
    return (REPO_ROOT / "firmware" / board_id / "reference").resolve()


def _prepare_context(request: TurnkeyRunRequest) -> tuple[BoardConfig, PreparedRunContext]:
    board = _load_board(request.board_id)
    workspace_root = (
        Path(request.workspace_root).expanduser().resolve() if request.workspace_root else None
    )
    flash_override = _resolve_optional_path(request.flash_artifact, workspace_root=workspace_root)
    symbol_override = _resolve_optional_path(request.symbol_artifact, workspace_root=workspace_root)
    artifacts = resolve_reference_artifacts(
        board,
        flash_artifact=flash_override,
        elf_path=symbol_override,
    )
    expected_uart = request.expected_uart_substring or board.expected_uart_substring
    if not expected_uart:
        raise TurnkeyRunError(
            f"Board '{board.board_id}' does not define an expected UART substring for turnkey checks"
        )
    if request.initial_post_flash_state not in {"running", "halted"}:
        raise TurnkeyRunError(
            f"Unsupported initial_post_flash_state '{request.initial_post_flash_state}'"
        )
    board_kind = "nordic" if board.mcu_family.startswith("nrf") else "generic"
    reference_root = _reference_source_root(board.board_id)
    if not reference_root.exists():
        raise TurnkeyRunError(f"Missing reference source root for {board.board_id}: {reference_root}")
    context = PreparedRunContext(
        board_id=board.board_id,
        board_kind=board_kind,
        case_id=request.case_id,
        workspace_root=workspace_root,
        reference_source_root=reference_root,
        flash_artifact=artifacts.flash_artifact,
        symbol_artifact=artifacts.symbol_artifact,
        expected_uart_substring=expected_uart,
        build_command=request.build_command,
        initial_post_flash_state=request.initial_post_flash_state,
        stage1_symbol_name=request.stage1_symbol_name,
        stage1_symbol_value_u32=request.stage1_symbol_value_u32,
    )
    return board, context


def _template_values(context: PreparedRunContext) -> dict[str, str]:
    return {
        "board_id": context.board_id,
        "flash_artifact": str(context.flash_artifact),
        "symbol_artifact": str(context.symbol_artifact),
        "expected_uart_substring": context.expected_uart_substring,
        "stage1_symbol_name": context.stage1_symbol_name,
        "stage1_symbol_value_u32": context.stage1_symbol_value_u32,
    }


def _extract_session_id(text: str) -> str | None:
    match = SESSION_ID_PATTERN.search(text)
    if match is None:
        return None
    return match.group(1)


def _save_result(result: TurnkeyRunResult, result_root: Path) -> TurnkeyRunResult:
    result_root.mkdir(parents=True, exist_ok=True)
    output_path = result_root / f"{result.run_id}.json"
    updated_result = replace(result, result_path=str(output_path))
    output_path.write_text(json.dumps(updated_result.to_dict(), indent=2), encoding="utf-8")
    return updated_result


def _required_tools(skill: SkillSpec) -> set[str]:
    if skill.workflow_kind == WORKFLOW_STATIC:
        return {step.tool for step in skill.steps}
    if skill.workflow_kind in {WORKFLOW_DIAGNOSE, WORKFLOW_REPAIR}:
        return {
            "connect",
            "disconnect",
            "flash_firmware",
            "get_state",
            "read_symbol_u32",
            "read_serial",
        }
    raise TurnkeyRunError(f"Unsupported workflow kind: {skill.workflow_kind}")


def _shell_command_for_host(command: str) -> list[str]:
    if sys.platform == "win32":
        return ["cmd.exe", "/d", "/s", "/c", command]
    return ["bash", "-lc", command]


def _run_local_command(
    command: str,
    *,
    cwd: Path,
    timeout_seconds: float = 1800.0,
) -> str:
    try:
        result = subprocess.run(
            _shell_command_for_host(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise TurnkeyRunError(
            f"Local command timed out after {timeout_seconds:.0f}s: {command}"
        ) from exc
    if result.returncode != 0:
        raise TurnkeyRunError(
            f"Local command failed with exit code {result.returncode}: {command}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    output = (result.stdout or "").strip()
    errors = (result.stderr or "").strip()
    return "\n".join(part for part in (output, errors) if part).strip() or "command succeeded"


class TurnkeyRunner:
    """Loads skills and executes one deterministic run over the MCP server."""

    def __init__(
        self,
        *,
        skills_root: Path = DEFAULT_SKILLS_ROOT,
        result_root: Path = TURNKEY_RUN_ROOT,
    ) -> None:
        self._skills_root = skills_root
        self._result_root = result_root

    async def run(
        self,
        request: TurnkeyRunRequest,
        *,
        server_command: ServerCommand | None = None,
    ) -> TurnkeyRunResult:
        command = server_command or _default_server_command()
        async with StdioToolClient(command) as client:
            return await self.run_with_client(request, client)

    async def run_with_client(
        self,
        request: TurnkeyRunRequest,
        client: ToolClientProtocol,
    ) -> TurnkeyRunResult:
        board, context = _prepare_context(request)
        skill = select_skill(request.skill_id, board, skills_root=self._skills_root)
        if skill.requires_workspace and context.workspace_root is None:
            raise TurnkeyRunError(
                f"Skill '{skill.skill_id}' requires --workspace-root / workspace_root"
            )

        available_tools = await client.list_tool_names()
        missing_tools = sorted(_required_tools(skill) - available_tools)
        if missing_tools:
            raise TurnkeyRunError(
                f"Skill '{skill.skill_id}' requires missing MCP tools: {', '.join(missing_tools)}"
            )

        run_id = f"turnkey-{request.board_id}-{request.skill_id}-{uuid4().hex[:12]}"
        state = MutableRunState()
        template_values = _template_values(context)

        try:
            if skill.workflow_kind == WORKFLOW_STATIC:
                await self._run_static_workflow(skill, client, state, template_values)
            elif skill.workflow_kind == WORKFLOW_DIAGNOSE:
                await self._run_reference_contract_diagnose(client, state, context)
            elif skill.workflow_kind == WORKFLOW_REPAIR:
                await self._run_reference_contract_repair(client, state, context)
            else:  # pragma: no cover - guarded by loader
                raise TurnkeyRunError(f"Unsupported workflow kind: {skill.workflow_kind}")
        finally:
            await self._cleanup_if_connected(client, state)

        final_status = self._final_status(skill, state)
        result = TurnkeyRunResult(
            run_id=run_id,
            board_id=context.board_id,
            skill_id=skill.skill_id,
            case_id=context.case_id,
            final_status=final_status,
            classification=state.classification,
            root_cause=state.root_cause,
            session_id=state.session_id,
            workspace_root=str(context.workspace_root) if context.workspace_root is not None else None,
            reference_source_root=str(context.reference_source_root),
            flash_artifact=str(context.flash_artifact),
            symbol_artifact=str(context.symbol_artifact),
            steps=tuple(state.steps),
            observations=tuple(state.observations),
            hypotheses=tuple(state.hypotheses),
            experiments=tuple(state.experiments),
            strategy_evaluations=tuple(state.strategy_evaluations),
            files_changed=tuple(state.files_changed),
            verification=dict(state.verification),
            warnings=tuple(state.warnings),
        )
        return _save_result(result, self._result_root)

    async def _run_static_workflow(
        self,
        skill: SkillSpec,
        client: ToolClientProtocol,
        state: MutableRunState,
        template_values: dict[str, str],
    ) -> None:
        for step in skill.steps:
            step_result = await self._run_templated_step(step, client, template_values)
            state.steps.append(step_result)
            if step.tool == "connect" and state.session_id is None:
                state.session_id = _extract_session_id(step_result.output_text)
            if not step_result.ok:
                state.final_status = "failed"
                return
        state.final_status = "success"
        state.classification = "healthy"
        state.root_cause = "the static turnkey skill completed all expected checks"
        state.verification["green_check_ok"] = True

    async def _run_reference_contract_diagnose(
        self,
        client: ToolClientProtocol,
        state: MutableRunState,
        context: PreparedRunContext,
    ) -> None:
        connected = await self._connect(client, state, context)
        if not connected:
            state.final_status = "failed"
            state.classification = "physical_fault"
            state.root_cause = "turnkey could not connect to the board"
            return

        diagnosis = await self._probe_reference_contract(
            client,
            state,
            context,
            flash_artifact=context.flash_artifact,
            symbol_artifact=context.symbol_artifact,
            phase="initial",
        )
        if state.classification is None:
            state.classification = diagnosis.classification
        if state.root_cause is None:
            state.root_cause = diagnosis.root_cause
        state.final_status = diagnosis.final_status

    async def _run_reference_contract_repair(
        self,
        client: ToolClientProtocol,
        state: MutableRunState,
        context: PreparedRunContext,
    ) -> None:
        connected = await self._connect(client, state, context)
        if not connected:
            state.final_status = "failed"
            state.classification = "physical_fault"
            state.root_cause = "turnkey could not connect to the board"
            return

        diagnosis = await self._probe_reference_contract(
            client,
            state,
            context,
            flash_artifact=context.flash_artifact,
            symbol_artifact=context.symbol_artifact,
            phase="initial",
        )
        state.classification = diagnosis.classification
        state.root_cause = diagnosis.root_cause

        if diagnosis.classification == "healthy":
            state.final_status = "healthy_confirmed"
            return
        if diagnosis.classification != "code_bug":
            state.final_status = diagnosis.final_status
            return

        self._record_strategy_evaluation(
            state,
            outcome="selected deterministic reference-contract restore",
            next_action="replace workspace src/src/main.c with the tracked reference file and rebuild",
        )
        try:
            changed_file = self._restore_reference_main(state, context)
            if changed_file is not None:
                state.files_changed.append(changed_file)
            build_output = self._run_local_build(state, context)
        except TurnkeyRunError as exc:
            state.final_status = "unresolved"
            state.root_cause = str(exc)
            state.warnings.append(str(exc))
            return
        self._record_experiment(
            state,
            purpose="rebuild workspace after restoring the reference contract",
            action_summary=f"ran local build command in {context.workspace_root}",
            result="success",
        )
        if build_output:
            self._record_observation(
                state,
                source="local-build",
                summary="workspace rebuild completed",
                evidence_excerpt=build_output[-240:],
            )

        verification = await self._probe_reference_contract(
            client,
            state,
            context,
            flash_artifact=context.flash_artifact,
            symbol_artifact=context.symbol_artifact,
            phase="verify",
        )
        state.verification["green_check_ok"] = bool(verification.symbol_ok and verification.uart_ok)
        if verification.classification == "healthy":
            state.final_status = "fixed"
            state.root_cause = diagnosis.root_cause
            return

        state.final_status = "unresolved"
        state.root_cause = (
            "deterministic reference-contract restore completed, but post-rebuild verification "
            "did not return the board to the expected green state"
        )

    async def _connect(
        self,
        client: ToolClientProtocol,
        state: MutableRunState,
        context: PreparedRunContext,
    ) -> bool:
        step = await self._run_step(
            client,
            step_id="connect",
            tool="connect",
            arguments={"board_id": context.board_id},
            timeout_seconds=45.0,
            expected_substrings=("Connected to board", "session_id="),
        )
        state.steps.append(step)
        if step.ok:
            state.session_id = _extract_session_id(step.output_text)
            self._record_observation(
                state,
                source="connect",
                summary="connected to the board through the MCP server",
                evidence_excerpt=step.output_text,
            )
            return True
        return False

    async def _probe_reference_contract(
        self,
        client: ToolClientProtocol,
        state: MutableRunState,
        context: PreparedRunContext,
        *,
        flash_artifact: Path,
        symbol_artifact: Path,
        phase: str,
    ) -> ReferenceContractDiagnosis:
        flash_step = await self._run_step(
            client,
            step_id=f"{phase}-flash",
            tool="flash_firmware",
            arguments={
                "path": str(flash_artifact),
                "halt_after_reset": context.initial_post_flash_state == "halted",
            },
            timeout_seconds=240.0,
            expected_substrings=("Flashed",),
        )
        state.steps.append(flash_step)
        if not flash_step.ok:
            state.classification = "physical_fault"
            state.root_cause = f"firmware flash failed during the {phase} phase"
            state.final_status = "failed"
            return ReferenceContractDiagnosis(
                classification="physical_fault",
                root_cause=state.root_cause,
                final_status="failed",
                symbol_ok=False,
                uart_ok=False,
            )
        self._record_experiment(
            state,
            purpose=f"{phase} probe of the board's reference contract",
            action_summary=f"flashed {flash_artifact.name} with target left {context.initial_post_flash_state}",
            result="success",
        )

        state_step = await self._run_step(
            client,
            step_id=f"{phase}-state",
            tool="get_state",
            arguments={},
            timeout_seconds=20.0,
            expected_substrings=(),
        )
        state.steps.append(state_step)
        state_text = state_step.output_text.upper()
        target_halted = "HALTED" in state_text
        self._record_observation(
            state,
            source="get_state",
            summary=f"target state after {phase} flash is {state_step.output_text or '(empty)'}",
            evidence_excerpt=state_step.output_text,
        )

        symbol_step = await self._run_step(
            client,
            step_id=f"{phase}-symbol",
            tool="read_symbol_u32",
            arguments={
                "elf_path": str(symbol_artifact),
                "symbol_name": context.stage1_symbol_name,
            },
            timeout_seconds=30.0,
            expected_substrings=(context.stage1_symbol_name,),
        )
        state.steps.append(symbol_step)
        symbol_value = self._extract_symbol_value(symbol_step.output_text)
        symbol_ok = symbol_value == context.stage1_symbol_value_u32.upper()
        self._record_observation(
            state,
            source="read_symbol_u32",
            summary=(
                f"symbol {context.stage1_symbol_name} "
                f"{'matched' if symbol_ok else 'did not match'} the expected value"
            ),
            evidence_excerpt=symbol_step.output_text,
        )

        uart_step = await self._run_step(
            client,
            step_id=f"{phase}-uart",
            tool="read_serial",
            arguments={
                "expected_text": context.expected_uart_substring,
                "read_seconds": 3.0,
                "reset_on_open": context.initial_post_flash_state != "halted",
            },
            timeout_seconds=20.0,
            expected_substrings=(),
        )
        state.steps.append(uart_step)
        uart_ok = (
            not uart_step.error
            and "UART matched" in uart_step.output_text
            and context.expected_uart_substring in uart_step.output_text
        )
        self._record_observation(
            state,
            source="read_serial",
            summary=(
                f"UART {'matched' if uart_ok else 'did not match'} "
                f"'{context.expected_uart_substring}'"
            ),
            evidence_excerpt=uart_step.output_text,
        )

        state.verification["flash_ok"] = flash_step.ok
        state.verification["symbol_ok"] = symbol_ok
        state.verification["uart_ok"] = uart_ok
        classification, root_cause, final_status = self._classify_reference_contract(
            symbol_ok=symbol_ok,
            uart_ok=uart_ok,
            target_halted=target_halted,
        )
        self._record_hypothesis(
            state,
            summary=root_cause,
            status="supported" if classification != "unresolved" else "open",
            supporting_observation_ids=(
                state.observations[-3].observation_id,
                state.observations[-2].observation_id,
                state.observations[-1].observation_id,
            ),
        )
        self._record_strategy_evaluation(
            state,
            outcome=f"{phase} classification={classification}",
            next_action=(
                "restore the reference contract in the workspace"
                if classification == "code_bug"
                else "stop after diagnosis"
            ),
        )
        return ReferenceContractDiagnosis(
            classification=classification,
            root_cause=root_cause,
            final_status=final_status,
            symbol_ok=symbol_ok,
            uart_ok=uart_ok,
        )

    def _restore_reference_main(
        self,
        state: MutableRunState,
        context: PreparedRunContext,
    ) -> str | None:
        if context.workspace_root is None:
            raise TurnkeyRunError("Repair workflow requires a workspace root")
        source_path = context.reference_source_root / REFERENCE_MAIN_RELATIVE
        destination_path = context.workspace_root / REFERENCE_MAIN_RELATIVE
        if not source_path.is_file():
            raise TurnkeyRunError(f"Reference source file is missing: {source_path}")
        if not destination_path.is_file():
            raise TurnkeyRunError(f"Workspace source file is missing: {destination_path}")

        before_text = destination_path.read_text(encoding="utf-8")
        after_text = source_path.read_text(encoding="utf-8")
        if before_text == after_text:
            self._record_experiment(
                state=state,
                purpose="restore the tracked reference contract",
                action_summary=f"compared {destination_path}",
                result="no-op; workspace already matched the reference file",
            )
            return None
        destination_path.write_text(after_text, encoding="utf-8")
        self._record_experiment(
            state,
            purpose="restore the tracked reference contract",
            action_summary=f"copied {source_path} to {destination_path}",
            result="workspace source updated to the canonical reference file",
        )
        return str(REFERENCE_MAIN_RELATIVE).replace("\\", "/")

    def _run_local_build(self, state: MutableRunState, context: PreparedRunContext) -> str:
        if context.workspace_root is None:
            raise TurnkeyRunError("Repair workflow requires a workspace root")
        if not context.build_command:
            raise TurnkeyRunError("Repair workflow requires a build_command")
        started = time.monotonic()
        try:
            output = _run_local_command(
                context.build_command,
                cwd=context.workspace_root,
            )
        except Exception as exc:  # noqa: BLE001 - preserve reportable build failure text
            duration = time.monotonic() - started
            self._append_local_step(
                state=state,
                step_id="local-build",
                tool="local_build",
                ok=False,
                duration_seconds=duration,
                output_text="",
                error=str(exc),
            )
            raise
        duration = time.monotonic() - started
        self._append_local_step(
            state=state,
            step_id="local-build",
            tool="local_build",
            ok=True,
            duration_seconds=duration,
            output_text=output,
            error=None,
        )
        return output

    async def _run_templated_step(
        self,
        step: SkillStep,
        client: ToolClientProtocol,
        template_values: dict[str, str],
    ) -> StepResult:
        rendered_arguments = render_template(step.arguments, template_values)
        rendered_expected = tuple(
            str(render_template(item, template_values)) for item in step.expected_substrings
        )
        return await self._run_step(
            client,
            step_id=step.step_id,
            tool=step.tool,
            arguments=rendered_arguments,
            timeout_seconds=step.timeout_seconds,
            expected_substrings=rendered_expected,
        )

    async def _run_step(
        self,
        client: ToolClientProtocol,
        *,
        step_id: str,
        tool: str,
        arguments: dict[str, object],
        timeout_seconds: float,
        expected_substrings: tuple[str, ...],
    ) -> StepResult:
        started = time.monotonic()
        error: str | None = None
        try:
            response = await client.call_tool_text(
                tool,
                arguments,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - preserve original failure text in the report
            duration = time.monotonic() - started
            return StepResult(
                step_id=step_id,
                tool=tool,
                arguments=arguments,
                timeout_seconds=timeout_seconds,
                expected_substrings=expected_substrings,
                ok=False,
                duration_seconds=duration,
                output_text="",
                error=str(exc),
            )

        if response.is_error:
            error = "tool returned error"
        missing_expected = [needle for needle in expected_substrings if needle not in response.text]
        if missing_expected:
            error = f"missing expected text: {', '.join(missing_expected)}"
        duration = time.monotonic() - started
        return StepResult(
            step_id=step_id,
            tool=tool,
            arguments=arguments,
            timeout_seconds=timeout_seconds,
            expected_substrings=expected_substrings,
            ok=(error is None),
            duration_seconds=duration,
            output_text=response.text,
            error=error,
        )

    async def _cleanup_if_connected(
        self,
        client: ToolClientProtocol,
        state: MutableRunState,
    ) -> None:
        if state.session_id is None:
            return
        if state.steps and state.steps[-1].tool == "disconnect" and state.steps[-1].ok:
            return
        try:
            response = await client.call_tool_text("disconnect", {}, timeout_seconds=15.0)
        except Exception as exc:  # noqa: BLE001 - cleanup warning only
            state.warnings.append(f"disconnect cleanup failed: {exc}")
            return
        if response.is_error:
            state.warnings.append("disconnect cleanup returned an error")
            return
        state.steps.append(
            StepResult(
                step_id="disconnect",
                tool="disconnect",
                arguments={},
                timeout_seconds=15.0,
                expected_substrings=(),
                ok=True,
                duration_seconds=0.0,
                output_text=response.text,
                error=None,
            )
        )

    def _final_status(self, skill: SkillSpec, state: MutableRunState) -> str:
        if state.final_status is not None:
            return state.final_status
        if "all_steps_succeeded" in skill.final_assertions:
            if len(state.steps) != len(skill.steps):
                return "failed"
            if any(not step.ok for step in state.steps):
                return "failed"
        if not state.steps:
            return "failed"
        return "success" if all(step.ok for step in state.steps) else "failed"

    def _extract_symbol_value(self, text: str) -> str | None:
        match = SYMBOL_VALUE_PATTERN.search(text)
        if match is None:
            return None
        return match.group(1).upper()

    def _classify_reference_contract(
        self,
        *,
        symbol_ok: bool,
        uart_ok: bool,
        target_halted: bool,
    ) -> tuple[str, str, str]:
        if symbol_ok and uart_ok:
            return (
                "healthy",
                "the Stage 1 symbol and UART signature both matched the tracked reference contract",
                "healthy_confirmed",
            )
        if target_halted and symbol_ok and not uart_ok:
            return (
                "observability_fault",
                "the target stayed halted, so UART output never refreshed even though the reference symbol matched",
                "diagnosed_only",
            )
        if not target_halted and (not symbol_ok or not uart_ok):
            if not symbol_ok and not uart_ok:
                detail = "both the Stage 1 symbol value and UART signature diverged"
            elif not symbol_ok:
                detail = "the Stage 1 symbol value diverged"
            else:
                detail = "the UART signature diverged"
            return (
                "code_bug",
                f"{detail} from the tracked reference contract while the target was running",
                "diagnosed_only",
            )
        return (
            "unresolved",
            "the observed state did not match a known reference-contract diagnosis rule",
            "unresolved",
        )

    def _append_local_step(
        self,
        state: MutableRunState | None,
        *,
        step_id: str,
        tool: str,
        ok: bool,
        duration_seconds: float,
        output_text: str,
        error: str | None,
    ) -> None:
        if state is None:
            raise TurnkeyRunError("local step recording requires mutable state")
        state.steps.append(
            StepResult(
                step_id=step_id,
                tool=tool,
                arguments={},
                timeout_seconds=0.0,
                expected_substrings=(),
                ok=ok,
                duration_seconds=duration_seconds,
                output_text=output_text,
                error=error,
            )
        )

    def _record_observation(
        self,
        state: MutableRunState,
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

    def _record_hypothesis(
        self,
        state: MutableRunState,
        *,
        summary: str,
        status: str,
        supporting_observation_ids: tuple[str, ...],
    ) -> None:
        state.hypotheses.append(
            Hypothesis(
                hypothesis_id=f"hyp-{len(state.hypotheses) + 1:03d}",
                summary=summary,
                status=status,
                supporting_observation_ids=supporting_observation_ids,
            )
        )

    def _record_experiment(
        self,
        state: MutableRunState,
        *,
        purpose: str,
        action_summary: str,
        result: str,
    ) -> None:
        state.experiments.append(
            Experiment(
                experiment_id=f"exp-{len(state.experiments) + 1:03d}",
                purpose=purpose,
                action_summary=action_summary,
                result=result,
            )
        )

    def _record_strategy_evaluation(
        self,
        state: MutableRunState,
        *,
        outcome: str,
        next_action: str,
    ) -> None:
        state.strategy_evaluations.append(
            StrategyEvaluation(
                strategy_id=f"strat-{len(state.strategy_evaluations) + 1:03d}",
                outcome=outcome,
                next_action=next_action,
            )
        )
