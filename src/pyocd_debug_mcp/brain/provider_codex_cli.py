"""Codex CLI-backed decision provider for the turnkey brain."""

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
    """Raised when Codex CLI does not return a valid structured action."""


class CodexCLIDecisionProvider:
    """Decision provider that shells out to `codex exec`."""

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
            remote_strategy="codex-thread-resume",
            resume_requires_stable_workdir=False,
            supports_transactional_fork=False,
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
        committed_thread_id = _native_thread_id(session_state)
        has_local_memory = bool(
            prompt_bundle.provider_memory_text.strip()
        ) or provider_has_local_memory(session_state)
        recovery_action = provider_resume_recovery_action(session_state)
        explicit_new_session_recovery = recovery_action == "new-session-from-memory"
        use_local_memory = False
        native_sync_used = False
        fresh_session = False
        resumed_thread = False
        continuation_path: ProviderContinuationPath = "remote-resume"
        prompt_render_mode = "bootstrap/full"
        current_resume_thread_id: str | None = None

        if explicit_new_session_recovery:
            use_local_memory = has_local_memory
            continuation_path = "local-memory-fallback" if use_local_memory else "remote-resume"
            prompt_render_mode = "remote-sync" if use_local_memory else "bootstrap/full"
            fresh_session = True
        elif committed_thread_id is None:
            use_local_memory = has_local_memory
            continuation_path = "local-memory-fallback" if use_local_memory else "remote-resume"
            prompt_render_mode = "remote-sync" if use_local_memory else "bootstrap/full"
            fresh_session = True
        elif should_inject_native_memory_sync(session_state):
            use_local_memory = True
            continuation_path = "remote-resume"
            prompt_render_mode = "remote-sync"
            native_sync_used = True
            resumed_thread = True
            current_resume_thread_id = committed_thread_id
        else:
            continuation_path = "remote-resume"
            prompt_render_mode = "remote-delta"
            resumed_thread = True
            current_resume_thread_id = committed_thread_id

        if prompt_render_mode == "remote-delta":
            current_prompt = prompt_bundle.render_remote_delta_text()
        elif prompt_render_mode == "remote-sync":
            current_prompt = (
                prompt_bundle.render_remote_sync_text(include_memory=use_local_memory)
                if current_resume_thread_id is not None
                else prompt_bundle.full_prompt_text(include_memory=use_local_memory).strip()
            )
        else:
            current_prompt = prompt_bundle.full_prompt_text(include_memory=use_local_memory).strip()
        current_prompt_render_mode = prompt_render_mode
        current_memory_injected = use_local_memory
        current_static_tool_schema_injected = prompt_render_mode != "remote-delta"
        current_decision_schema_injected = prompt_render_mode != "remote-delta"
        retry_count = 0
        same_thread_retry_used = False
        last_error: Exception | None = None
        progress_updates: list[ProviderProgressUpdate] = [
            ProviderProgressUpdate(
                stage="provider_request",
                message="Dispatching Codex CLI turn.",
                details={
                    "continuation_path": continuation_path,
                    "prompt_render_mode": current_prompt_render_mode,
                    "memory_injected": current_memory_injected,
                    "fresh_session": fresh_session,
                    "resumed_thread": resumed_thread,
                    "working_directory": str(working_dir),
                    "resume_recovery_action": recovery_action,
                },
            )
        ]
        if explicit_new_session_recovery:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Starting a new Codex thread from saved provider memory after explicit recovery.",
                    details={
                        "replaced_thread_id": committed_thread_id,
                        "memory_available": has_local_memory,
                    },
                )
            )
        elif resumed_thread and committed_thread_id is not None:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Using Codex remote thread resume.",
                    details={"thread_id": committed_thread_id},
                )
            )
        elif use_local_memory:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Codex thread handle is missing; bootstrapping from canonical local memory.",
                    details={"memory_available": has_local_memory},
                )
            )
        else:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Starting a fresh Codex remote thread.",
                    details={"fresh_session": True},
                )
            )
        if native_sync_used:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="memory_sync",
                    message="Injecting canonical local memory into the resumed Codex turn.",
                    details={"native_sync_every": session_state.native_sync_every},
                )
            )

        for _attempt in range(3):
            output_path = working_dir / "turn_decision.json"
            stream_path = working_dir / "turn_decision.stream.jsonl"
            output_path.unlink(missing_ok=True)
            stream_path.unlink(missing_ok=True)
            try:
                result = subprocess.run(
                    _build_codex_command(
                        model=self._model,
                        working_dir=working_dir,
                        output_path=output_path,
                        resume_thread_id=current_resume_thread_id,
                    ),
                    input=current_prompt,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    cwd=str(working_dir),
                    check=False,
                    timeout=self._timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise ProviderResponseError(
                    f"Codex CLI timed out after {self._timeout_seconds:.0f}s."
                ) from exc

            stdout_text = result.stdout
            output_text = (
                output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
            )
            returned_thread_id = _extract_codex_thread_id(stdout_text)
            if not output_text and result.returncode == 0:
                output_text = _extract_codex_agent_message(stdout_text)
            if result.returncode != 0 and not output_text:
                last_error = ProviderResponseError(result.stderr.strip() or stdout_text.strip())
                if current_resume_thread_id is not None:
                    raise ProviderResumeFailure(
                        ProviderResumeFailureRecord(
                            provider="codex-cli",
                            remote_strategy=self.capabilities.remote_strategy,
                            continuation_mode=self.capabilities.continuation_mode,
                            continuation_path="remote-resume",
                            remote_handle_kind="thread_id",
                            expected_handle_id=current_resume_thread_id,
                            turn_index=session_state.next_turn_index(),
                            failure_text=str(last_error),
                            local_memory_available=has_local_memory,
                        )
                    )
                break

            try:
                decision = parse_turn_decision_json(output_text)
            except Exception as exc:  # noqa: BLE001 - preserve parse failures
                last_error = exc
                if not same_thread_retry_used and (returned_thread_id or current_resume_thread_id):
                    retry_count += 1
                    same_thread_retry_used = True
                    current_resume_thread_id = returned_thread_id or current_resume_thread_id
                    continuation_path = "remote-resume"
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
                            message="Codex returned invalid structured output; retrying once in the same remote thread.",
                            details={
                                "retry_count": retry_count,
                                "thread_id": current_resume_thread_id,
                            },
                        )
                    )
                    continue
                if current_resume_thread_id is None:
                    retry_count += 1
                    current_resume_thread_id = None
                    current_memory_injected = has_local_memory
                    continuation_path = (
                        "local-memory-fallback" if has_local_memory else "remote-resume"
                    )
                    current_prompt_render_mode = (
                        "remote-sync" if has_local_memory else "bootstrap/full"
                    )
                    current_static_tool_schema_injected = True
                    current_decision_schema_injected = True
                    current_prompt = (
                        prompt_bundle.full_prompt_text(include_memory=has_local_memory).strip()
                        if has_local_memory
                        else prompt_bundle.full_prompt_text(include_memory=False).strip()
                    )
                    progress_updates.append(
                        ProviderProgressUpdate(
                            stage="provider_retry",
                            message="Codex same-thread retry did not stabilize; restarting from canonical local memory.",
                            details={"retry_count": retry_count},
                        )
                    )
                    continue
                break

            effective_thread_id = returned_thread_id or current_resume_thread_id
            resumed_remote = current_resume_thread_id is not None
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
                remote_handle_kind="thread_id",
                remote_handle_id=effective_thread_id,
                fresh_remote_turn=fresh_remote_turn,
                resumed_remote=resumed_remote,
                native_sync_used=native_sync_used,
                working_directory=str(working_dir),
                extra={
                    "thread_id": effective_thread_id,
                    "thread_id_present": returned_thread_id is not None,
                    "fresh_session": fresh_remote_turn,
                    "resumed_thread": resumed_remote,
                    "same_thread_retry_used": same_thread_retry_used,
                    "resume_recovery_action": recovery_action,
                    "recovery_created_new_session": explicit_new_session_recovery,
                    "replaced_remote_handle_id": (
                        committed_thread_id if explicit_new_session_recovery else None
                    ),
                    "resume_recovery_failure": recovery_record,
                },
            )
            updated_session = (
                session_state.with_native_handle_update(
                    native_session_id=effective_thread_id,
                    provider_fields=(
                        {"codex_thread_id": effective_thread_id}
                        if effective_thread_id is not None
                        else None
                    ),
                )
                .with_runtime_transport_metadata(
                    {
                        "working_directory": str(working_dir),
                        "codex_thread_id": effective_thread_id,
                        "remote_strategy": self.capabilities.remote_strategy,
                    }
                )
                .with_last_continuation_path(
                    continuation_path,
                    metadata=turn_metadata,
                )
            )
            if explicit_new_session_recovery:
                updated_session = clear_provider_resume_recovery_request(
                    updated_session
                ).with_updated_metadata(
                    {
                        "last_recovery_created_new_session": True,
                        "last_replaced_remote_handle_id": committed_thread_id,
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
            f"Codex CLI provider did not return a valid turnkey action: {last_error}"
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
            f"{prompt}\n\nReturn exactly one JSON object with a non-empty summary_text field."
        )
        for _attempt in range(2):
            with tempfile.TemporaryDirectory(prefix="pyocd-turnkey-codex-summary-") as tmpdir:
                tmp_path = Path(tmpdir)
                output_path = tmp_path / "memory_summary.json"
                try:
                    result = subprocess.run(
                        _build_codex_command(
                            model=self._model,
                            working_dir=tmp_path,
                            output_path=output_path,
                            resume_thread_id=None,
                            ephemeral=True,
                        ),
                        input=current_prompt,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        capture_output=True,
                        check=False,
                        timeout=self._timeout_seconds,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise ProviderResponseError(
                        f"Codex CLI memory summarizer timed out after {self._timeout_seconds:.0f}s."
                    ) from exc
                output_text = (
                    output_path.read_text(encoding="utf-8")
                    if output_path.exists()
                    else _extract_codex_agent_message(result.stdout)
                ).strip()
                if result.returncode != 0 and not output_text:
                    last_error = ProviderResponseError(
                        result.stderr.strip() or result.stdout.strip()
                    )
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
                        "provider": "codex-cli",
                        "model": self._model,
                        "remote_strategy": self.capabilities.remote_strategy,
                        "cli_mode": "summary-ephemeral",
                    },
                )
        raise ProviderResponseError(
            f"Codex CLI provider did not return a valid memory summary: {last_error}"
        )


def _build_codex_command(
    *,
    model: str | None,
    working_dir: Path,
    output_path: Path,
    resume_thread_id: str | None = None,
    ephemeral: bool = False,
) -> list[str]:
    command = [
        "codex",
        "-a",
        "never",
        "-s",
        "danger-full-access",
        "exec",
    ]
    if resume_thread_id is None:
        command.extend(
            [
                "-C",
                str(working_dir),
                "--skip-git-repo-check",
                "--ignore-rules",
                "--json",
                "-o",
                str(output_path),
            ]
        )
        if ephemeral:
            command.append("--ephemeral")
        if model:
            command.extend(["--model", model])
        command.append("-")
        return command

    command.extend(
        [
            "resume",
            "--skip-git-repo-check",
            "--ignore-rules",
            "--json",
            "-o",
            str(output_path),
            resume_thread_id,
        ]
    )
    if model:
        command.extend(["--model", model])
    command.append("-")
    return command


def _extract_codex_thread_id(stdout_text: str) -> str | None:
    for line in stdout_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "thread.started":
            thread_id = payload.get("thread_id")
            if isinstance(thread_id, str) and thread_id.strip():
                return thread_id.strip()
    return None


def _extract_codex_agent_message(stdout_text: str) -> str:
    last_message = ""
    for line in stdout_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if payload.get("type") != "item.completed":
            continue
        item = payload.get("item")
        if not isinstance(item, dict):
            continue
        if item.get("type") != "agent_message":
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            last_message = text.strip()
    return last_message


def _native_thread_id(session_state: ProviderSessionState) -> str | None:
    if session_state.native_handle is None:
        return None
    if session_state.native_handle.native_session_id:
        return session_state.native_handle.native_session_id
    thread_id = session_state.native_handle.provider_fields.get("codex_thread_id")
    if isinstance(thread_id, str) and thread_id.strip():
        return thread_id.strip()
    return None


def _require_runtime_working_directory(session_state: ProviderSessionState) -> Path:
    runtime_context = session_state.runtime_context
    if runtime_context is None or not runtime_context.working_directory:
        raise ProviderResponseError(
            "Codex CLI remote continuation requires a stable provider runtime working directory."
        )
    path = Path(runtime_context.working_directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_runtime_context(session_state: ProviderSessionState) -> ProviderSessionState:
    if (
        session_state.runtime_context is not None
        and session_state.runtime_context.working_directory
    ):
        return session_state
    working_dir = tempfile.mkdtemp(prefix="pyocd-turnkey-codex-runtime-")
    return session_state.with_runtime_context(
        ProviderRuntimeContext(
            runtime_root=working_dir,
            working_directory=working_dir,
            transport_metadata={"auto_seeded_runtime_context": True},
        )
    )
