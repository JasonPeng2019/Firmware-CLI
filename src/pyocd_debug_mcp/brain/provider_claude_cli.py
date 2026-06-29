"""Claude Code CLI-backed decision provider for the turnkey brain."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

import anyio

from pyocd_debug_mcp.brain.provider_parsing import (
    parse_memory_summary_json,
    parse_turn_decision_json,
)
from pyocd_debug_mcp.brain.provider_types import (
    build_provider_turn_metadata,
    clear_provider_resume_recovery_request,
    ProviderCapabilities,
    ProviderContinuationPath,
    ProviderMemoryEntry,
    ProviderMemorySummaryResult,
    ProviderProgressUpdate,
    ProviderPromptBundle,
    ProviderResumeFailure,
    ProviderResumeFailureRecord,
    ProviderRuntimeContext,
    ProviderSessionState,
    ProviderTurn,
    provider_resume_recovery_action,
    provider_has_local_memory,
    render_memory_summary_request,
    should_inject_native_memory_sync,
)
from pyocd_debug_mcp.timeouts import PROVIDER_REQUEST_TIMEOUT_SECONDS


class ProviderResponseError(RuntimeError):
    """Raised when Claude Code does not return a valid structured action."""


class ClaudeCLIDecisionProvider:
    """Decision provider that shells out to `claude --print`."""

    def __init__(
        self,
        *,
        model: str | None,
        timeout_seconds: float = PROVIDER_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_native_session=True,
            supports_transcript_continuation=True,
            supports_response_id_continuation=False,
            supports_tool_schema_prompt=True,
            continuation_mode="remote-primary",
            remote_strategy="claude-session-resume",
            resume_requires_stable_workdir=True,
            supports_transactional_fork=True,
        )

    async def next_decision(
        self,
        *,
        prompt_bundle: ProviderPromptBundle,
        session_state: ProviderSessionState,
    ) -> ProviderTurn:
        return await anyio.to_thread.run_sync(
            self._next_decision_sync,
            prompt_bundle,
            session_state,
        )

    async def summarize_memory(
        self,
        *,
        session_state: ProviderSessionState,
        prior_summary_text: str,
        evicted_entries: tuple[ProviderMemoryEntry, ...],
    ) -> ProviderMemorySummaryResult:
        return await anyio.to_thread.run_sync(
            self._summarize_memory_sync,
            session_state,
            prior_summary_text,
            evicted_entries,
        )

    def _next_decision_sync(
        self,
        prompt_bundle: ProviderPromptBundle,
        session_state: ProviderSessionState,
    ) -> ProviderTurn:
        session_state = _ensure_runtime_context(session_state)
        working_dir = _require_runtime_working_directory(session_state)
        committed_session_id = (
            session_state.native_handle.native_session_id
            if session_state.native_handle is not None
            else None
        )
        has_local_memory = bool(prompt_bundle.provider_memory_text.strip()) or provider_has_local_memory(
            session_state
        )
        recovery_action = provider_resume_recovery_action(session_state)
        explicit_new_session_recovery = recovery_action == "new-session-from-memory"
        use_local_memory = False
        native_sync_used = False
        fresh_session = False
        resumed_session = False
        fork_retry_used = False
        continuation_path: ProviderContinuationPath = "remote-resume"
        prompt_render_mode = "bootstrap/full"
        current_resume_session_id: str | None = None

        if explicit_new_session_recovery:
            use_local_memory = has_local_memory
            continuation_path = "local-memory-fallback" if use_local_memory else "remote-resume"
            prompt_render_mode = "remote-sync" if use_local_memory else "bootstrap/full"
            fresh_session = True
        elif committed_session_id is None:
            use_local_memory = has_local_memory
            continuation_path = "local-memory-fallback" if use_local_memory else "remote-resume"
            prompt_render_mode = "remote-sync" if use_local_memory else "bootstrap/full"
            fresh_session = True
        elif should_inject_native_memory_sync(session_state):
            use_local_memory = True
            continuation_path = "remote-resume"
            prompt_render_mode = "remote-sync"
            native_sync_used = True
            resumed_session = True
            current_resume_session_id = committed_session_id
        else:
            continuation_path = "remote-resume"
            prompt_render_mode = "remote-delta"
            resumed_session = True
            current_resume_session_id = committed_session_id

        if prompt_render_mode == "remote-delta":
            current_prompt = prompt_bundle.render_remote_delta_text()
        elif prompt_render_mode == "remote-sync":
            current_prompt = prompt_bundle.render_remote_sync_text(include_memory=use_local_memory)
        else:
            current_prompt = prompt_bundle.render_bootstrap_text(include_memory=use_local_memory)
        current_prompt_render_mode = prompt_render_mode
        current_memory_injected = use_local_memory
        current_static_tool_schema_injected = prompt_render_mode != "remote-delta"
        current_decision_schema_injected = prompt_render_mode != "remote-delta"
        current_fork_session = False
        retry_count = 0
        last_error: Exception | None = None
        progress_updates: list[ProviderProgressUpdate] = [
            ProviderProgressUpdate(
                stage="provider_request",
                message="Dispatching Claude Code CLI turn.",
                details={
                    "continuation_path": continuation_path,
                    "prompt_render_mode": current_prompt_render_mode,
                    "memory_injected": current_memory_injected,
                    "fresh_session": fresh_session,
                    "resumed_session": resumed_session,
                    "working_directory": str(working_dir),
                    "resume_recovery_action": recovery_action,
                },
            )
        ]
        if explicit_new_session_recovery:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Starting a new Claude session from saved provider memory after explicit recovery.",
                    details={
                        "replaced_session_id": committed_session_id,
                        "memory_available": has_local_memory,
                    },
                )
            )
        elif resumed_session and committed_session_id is not None:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Using Claude remote session resume.",
                    details={"session_id": committed_session_id},
                )
            )
        elif use_local_memory:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Claude remote handle is missing; bootstrapping from canonical local memory.",
                    details={"memory_available": has_local_memory},
                )
            )
        else:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Starting a fresh Claude remote session.",
                    details={"fresh_session": True},
                )
            )
        if native_sync_used:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="memory_sync",
                    message="Injecting canonical local memory into the resumed Claude turn.",
                    details={"native_sync_every": session_state.native_sync_every},
                )
            )

        for _attempt in range(3):
            try:
                result = subprocess.run(
                    _build_claude_command(
                        model=self._model,
                        instructions=prompt_bundle.system_instructions,
                        resume_session_id=current_resume_session_id,
                        fork_session=current_fork_session,
                    ),
                    input=current_prompt,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    cwd=working_dir,
                    check=False,
                    timeout=self._timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise ProviderResponseError(
                    f"Claude CLI timed out after {self._timeout_seconds:.0f}s."
                ) from exc

            output_text, returned_session_id, command_error = _extract_claude_output_text(result)
            if command_error is not None:
                last_error = command_error
                if current_resume_session_id is not None:
                    raise ProviderResumeFailure(
                        ProviderResumeFailureRecord(
                            provider="claude-cli",
                            remote_strategy=self.capabilities.remote_strategy,
                            continuation_mode=self.capabilities.continuation_mode,
                            continuation_path="remote-resume",
                            remote_handle_kind="session_id",
                            expected_handle_id=current_resume_session_id,
                            turn_index=session_state.next_turn_index(),
                            failure_text=str(command_error),
                            local_memory_available=has_local_memory,
                        )
                    )
                break

            try:
                decision = parse_turn_decision_json(output_text)
            except Exception as exc:  # noqa: BLE001 - preserve parse failures
                last_error = exc
                if current_resume_session_id is not None and not current_fork_session:
                    retry_count += 1
                    current_fork_session = True
                    current_resume_session_id = committed_session_id
                    continuation_path = "remote-fork"
                    current_prompt = prompt_bundle.render_retry_text(
                        "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                    )
                    current_prompt_render_mode = "retry"
                    current_memory_injected = False
                    current_static_tool_schema_injected = False
                    current_decision_schema_injected = True
                    fork_retry_used = True
                    progress_updates.append(
                        ProviderProgressUpdate(
                            stage="provider_retry",
                            message="Claude returned invalid structured output; retrying from the committed parent session via --fork-session.",
                            details={
                                "retry_count": retry_count,
                                "parent_session_id": committed_session_id,
                            },
                        )
                    )
                    continue
                if current_resume_session_id is None and retry_count == 0:
                    retry_count += 1
                    current_prompt = prompt_bundle.render_retry_text(
                        "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                    )
                    current_prompt_render_mode = "retry"
                    current_memory_injected = False
                    current_static_tool_schema_injected = False
                    current_decision_schema_injected = True
                    progress_updates.append(
                        ProviderProgressUpdate(
                            stage="provider_retry",
                            message="Claude returned invalid structured output; retrying with a schema-correction prompt.",
                            details={"retry_count": retry_count},
                        )
                    )
                    continue
                break

            effective_session_id = returned_session_id
            if effective_session_id is None:
                if current_fork_session:
                    effective_session_id = committed_session_id
                elif current_resume_session_id is not None:
                    effective_session_id = current_resume_session_id
            resumed_remote = current_resume_session_id is not None
            fresh_remote_turn = not resumed_remote
            recovery_record = session_state.metadata.get("resume_recovery_failure")
            turn_metadata = build_provider_turn_metadata(
                capabilities=self.capabilities,
                continuation_path=continuation_path,
                prompt_render_mode=current_prompt_render_mode,
                memory_injected=current_memory_injected,
                static_tool_schema_injected=current_static_tool_schema_injected,
                decision_schema_injected=current_decision_schema_injected,
                retry_count=retry_count,
                remote_handle_kind="session_id",
                remote_handle_id=effective_session_id,
                fresh_remote_turn=fresh_remote_turn,
                resumed_remote=resumed_remote,
                native_sync_used=native_sync_used,
                working_directory=str(working_dir),
                extra={
                    "session_id": effective_session_id,
                    "session_id_present": returned_session_id is not None,
                    "fresh_session": fresh_remote_turn,
                    "resumed_session": resumed_remote,
                    "fork_retry_used": fork_retry_used,
                    "resume_recovery_action": recovery_action,
                    "recovery_created_new_session": explicit_new_session_recovery,
                    "replaced_remote_handle_id": (
                        committed_session_id if explicit_new_session_recovery else None
                    ),
                    "resume_recovery_failure": recovery_record,
                },
            )
            updated_session = session_state.with_native_handle_update(
                native_session_id=effective_session_id,
                provider_fields=(
                    {"claude_session_id": effective_session_id}
                    if effective_session_id is not None
                    else None
                ),
            ).with_runtime_transport_metadata(
                {
                    "working_directory": str(working_dir),
                    "claude_session_id": effective_session_id,
                    "remote_strategy": self.capabilities.remote_strategy,
                }
            ).with_last_continuation_path(
                continuation_path,
                metadata=turn_metadata,
            )
            if explicit_new_session_recovery:
                updated_session = clear_provider_resume_recovery_request(
                    updated_session
                ).with_updated_metadata(
                    {
                        "last_recovery_created_new_session": True,
                        "last_replaced_remote_handle_id": committed_session_id,
                    }
                )
            return ProviderTurn(
                decision=decision,
                output_text=output_text,
                response_id=None,
                session_state=updated_session,
                provider_metadata=turn_metadata,
                progress_updates=tuple(progress_updates),
            )

        raise ProviderResponseError(
            f"Claude CLI provider did not return a valid turnkey action: {last_error}"
        )

    def _summarize_memory_sync(
        self,
        session_state: ProviderSessionState,
        prior_summary_text: str,
        evicted_entries: tuple[ProviderMemoryEntry, ...],
    ) -> ProviderMemorySummaryResult:
        last_error: Exception | None = None
        prompt = render_memory_summary_request(
            prior_summary_text=prior_summary_text,
            evicted_entries=evicted_entries,
            summary_char_limit=session_state.summary_char_limit,
        )
        current_prompt = (
            f"{prompt}\n\n"
            "Return exactly one JSON object with a non-empty summary_text field."
        )
        system = "Return only one JSON object with a non-empty summary_text field."
        working_dir = (
            Path(session_state.runtime_context.working_directory)
            if session_state.runtime_context is not None
            else None
        )
        for _attempt in range(2):
            try:
                result = subprocess.run(
                    _build_claude_command(
                        model=self._model,
                        instructions=system,
                        no_session_persistence=True,
                    ),
                    input=current_prompt,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    cwd=str(working_dir) if working_dir is not None else None,
                    check=False,
                    timeout=self._timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise ProviderResponseError(
                    f"Claude CLI memory summarizer timed out after {self._timeout_seconds:.0f}s."
                ) from exc
            output_text, _session_id, command_error = _extract_claude_output_text(result)
            if command_error is not None:
                last_error = command_error
                current_prompt = (
                    f"{prompt}\n\n"
                    "Your previous reply was invalid. Return only one JSON object with a non-empty summary_text field."
                )
                continue
            try:
                summary_text = parse_memory_summary_json(output_text)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                current_prompt = (
                    f"{prompt}\n\n"
                    "Your previous reply was invalid. Return only one JSON object with a non-empty summary_text field."
                )
                continue
            return ProviderMemorySummaryResult(
                summary_text=summary_text,
                provider_metadata={
                    "continuation_path": "summary-call",
                    "provider": "claude-cli",
                    "model": self._model,
                    "remote_strategy": self.capabilities.remote_strategy,
                },
            )
        raise ProviderResponseError(
            f"Claude CLI provider did not return a valid memory summary: {last_error}"
        )


def _build_claude_command(
    *,
    model: str | None,
    instructions: str,
    resume_session_id: str | None = None,
    fork_session: bool = False,
    no_session_persistence: bool = False,
) -> list[str]:
    command = [
        "claude",
        "--print",
        "--output-format",
        "json",
        "--append-system-prompt",
        instructions,
    ]
    if model:
        command.extend(["--model", model])
    if no_session_persistence:
        command.append("--no-session-persistence")
    if resume_session_id:
        command.extend(["--resume", resume_session_id])
        if fork_session:
            command.append("--fork-session")
    return command


def _extract_claude_output_text(
    result: subprocess.CompletedProcess[str],
) -> tuple[str, str | None, ProviderResponseError | None]:
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if not stdout:
        if result.returncode != 0:
            return "", None, ProviderResponseError(stderr or "Claude CLI returned no output.")
        return "", None, ProviderResponseError("Claude CLI returned an empty response.")

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        if result.returncode != 0:
            return "", None, ProviderResponseError(stdout or stderr or "Claude CLI request failed.")
        return stdout, None, None

    if isinstance(payload, dict):
        session_id = payload.get("session_id")
        if payload.get("is_error") is True:
            message = str(payload.get("result") or payload)
            return "", None, ProviderResponseError(message)
        result_text = payload.get("result")
        if isinstance(result_text, str) and result_text.strip():
            return result_text.strip(), session_id if isinstance(session_id, str) else None, None

    if result.returncode != 0:
        return "", None, ProviderResponseError(stdout or stderr or "Claude CLI request failed.")
    return "", None, ProviderResponseError("Claude CLI returned an unrecognized JSON response.")


def _require_runtime_working_directory(session_state: ProviderSessionState) -> str:
    runtime_context = session_state.runtime_context
    if runtime_context is None or not runtime_context.working_directory:
        raise ProviderResponseError(
            "Claude CLI remote continuation requires a stable provider runtime working directory."
        )
    path = Path(runtime_context.working_directory)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _ensure_runtime_context(session_state: ProviderSessionState) -> ProviderSessionState:
    if session_state.runtime_context is not None and session_state.runtime_context.working_directory:
        return session_state
    working_dir = tempfile.mkdtemp(prefix="pyocd-turnkey-claude-runtime-")
    return session_state.with_runtime_context(
        ProviderRuntimeContext(
            runtime_root=working_dir,
            working_directory=working_dir,
            transport_metadata={"auto_seeded_runtime_context": True},
        )
    )
