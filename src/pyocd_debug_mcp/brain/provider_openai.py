"""OpenAI-backed decision provider for the turnkey brain."""

from __future__ import annotations

from typing import Any, cast

from anyio.to_thread import run_sync as run_sync_in_worker_thread
from openai import OpenAI

from pyocd_debug_mcp.brain.actions import TurnDecision
from pyocd_debug_mcp.brain.provider_parsing import (
    parse_memory_summary_json,
    parse_turn_decision_json,
)
from pyocd_debug_mcp.brain.provider_types import (
    build_provider_turn_metadata,
    clear_provider_resume_recovery_request,
    ProviderCapabilities,
    ProviderContinuationPath,
    ProviderMidHistoryEntry,
    ProviderMemorySummaryResult,
    ProviderProgressUpdate,
    ProviderPromptBundle,
    ProviderResumeFailure,
    ProviderResumeFailureRecord,
    ProviderSessionState,
    ProviderTurn,
    provider_resume_recovery_action,
    provider_has_local_memory,
    render_memory_summary_request,
    should_inject_native_memory_sync,
    validate_memory_summary_text,
)
from pyocd_debug_mcp.timeouts import PROVIDER_REQUEST_TIMEOUT_SECONDS


class ProviderResponseError(RuntimeError):
    """Raised when the model does not return a valid structured action."""


class OpenAIDecisionProvider:
    """Thin wrapper over the OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = PROVIDER_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        self._model = model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_native_session=True,
            supports_transcript_continuation=False,
            supports_response_id_continuation=True,
            supports_tool_schema_prompt=True,
            continuation_mode="remote-primary",
            remote_strategy="openai-response-chain",
        )

    async def next_decision(
        self,
        *,
        prompt_bundle: ProviderPromptBundle,
        session_state: ProviderSessionState,
    ) -> ProviderTurn:
        return await run_sync_in_worker_thread(
            self._next_decision_sync,
            prompt_bundle,
            session_state,
        )

    async def summarize_memory(
        self,
        *,
        session_state: ProviderSessionState,
        prior_summary_text: str,
        evicted_entries: tuple[ProviderMidHistoryEntry, ...],
    ) -> ProviderMemorySummaryResult:
        return await run_sync_in_worker_thread(
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
        last_error: Exception | None = None
        retry_count = 0
        previous_response_id = (
            session_state.native_handle.response_id
            if session_state.native_handle is not None
            else None
        )
        committed_response_id = previous_response_id
        has_local_memory = bool(
            prompt_bundle.provider_memory_text.strip()
        ) or provider_has_local_memory(session_state)
        recovery_action = provider_resume_recovery_action(session_state)
        explicit_new_session_recovery = recovery_action == "new-session-from-memory"
        use_local_memory = False
        native_sync_used = False
        fresh_session = False
        continuation_path: ProviderContinuationPath = "remote-resume"
        prompt_render_mode = "bootstrap/full"
        if explicit_new_session_recovery:
            previous_response_id = None
            use_local_memory = has_local_memory
            continuation_path = "local-memory-fallback" if use_local_memory else "remote-resume"
            prompt_render_mode = "remote-sync" if use_local_memory else "bootstrap/full"
            fresh_session = True
        elif previous_response_id is None:
            use_local_memory = has_local_memory
            continuation_path = "local-memory-fallback" if use_local_memory else "remote-resume"
            prompt_render_mode = "remote-sync" if use_local_memory else "bootstrap/full"
            fresh_session = True
        elif should_inject_native_memory_sync(session_state):
            use_local_memory = True
            continuation_path = "remote-resume"
            native_sync_used = True
            prompt_render_mode = "remote-sync"
        else:
            prompt_render_mode = "remote-delta"
        if prompt_render_mode == "remote-delta":
            current_prompt = prompt_bundle.render_remote_delta_text()
        elif prompt_render_mode == "remote-sync":
            current_prompt = prompt_bundle.render_remote_sync_text(include_memory=use_local_memory)
        else:
            current_prompt = prompt_bundle.render_bootstrap_text(include_memory=use_local_memory)
        current_prompt_render_mode = prompt_render_mode
        current_memory_injected = use_local_memory
        current_static_tool_schema_injected = bool(prompt_bundle.tool_schema_text.strip())
        current_decision_schema_injected = prompt_render_mode != "remote-delta"
        progress_updates: list[ProviderProgressUpdate] = [
            ProviderProgressUpdate(
                stage="provider_request",
                message="Dispatching OpenAI Responses turn.",
                details={
                    "continuation_path": continuation_path,
                    "prompt_render_mode": current_prompt_render_mode,
                    "native_response_id_present": previous_response_id is not None,
                    "memory_injected": current_memory_injected,
                    "fresh_session": fresh_session,
                    "resume_recovery_action": recovery_action,
                },
            )
        ]
        if explicit_new_session_recovery:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Starting a new OpenAI Responses chain from saved provider memory after explicit recovery.",
                    details={
                        "replaced_response_id": committed_response_id,
                        "memory_available": has_local_memory,
                    },
                )
            )
        elif native_sync_used:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="memory_sync",
                    message="Injecting canonical local memory into the OpenAI native continuation turn.",
                    details={"native_sync_every": session_state.native_sync_every},
                )
            )
        elif previous_response_id is not None:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Using OpenAI native continuation with the prior response id.",
                    details={"previous_response_id": previous_response_id},
                )
            )
        elif use_local_memory:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Native continuation handle is missing; falling back to canonical local memory.",
                    details={"memory_available": has_local_memory},
                )
            )
        else:
            progress_updates.append(
                ProviderProgressUpdate(
                    stage="continuation",
                    message="Starting a new native OpenAI turn with the bootstrap prompt.",
                    details={"fresh_session": True},
                )
            )
        response_format = {
            "type": "json_schema",
            "name": "turn_decision",
            "strict": True,
            "schema": TurnDecision.model_json_schema(),
        }
        for _attempt in range(2):
            kwargs: dict[str, Any] = {
                "model": self._model,
                "instructions": prompt_bundle.system_instructions,
                "input": current_prompt,
                "text": cast(Any, {"format": response_format}),
            }
            if previous_response_id:
                kwargs["previous_response_id"] = previous_response_id
            try:
                response = self._client.responses.create(
                    **kwargs,
                )
            except Exception as exc:  # noqa: BLE001 - provider SDK error is part of resume failure
                if previous_response_id:
                    raise ProviderResumeFailure(
                        ProviderResumeFailureRecord(
                            provider="openai-api",
                            remote_strategy=self.capabilities.remote_strategy,
                            continuation_mode=self.capabilities.continuation_mode,
                            continuation_path="remote-resume",
                            remote_handle_kind="response_id",
                            expected_handle_id=previous_response_id,
                            turn_index=session_state.next_turn_index(),
                            failure_text=f"{type(exc).__name__}: {exc}",
                            local_memory_available=has_local_memory,
                        )
                    ) from exc
                raise
            output_text = (response.output_text or "").strip()
            try:
                decision = parse_turn_decision_json(output_text)
            except Exception as exc:  # noqa: BLE001 - preserve structured parse failures
                last_error = exc
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
                        message="OpenAI returned invalid structured output; retrying with a schema-correction prompt.",
                        details={"retry_count": retry_count},
                    )
                )
                continue
            response_id = getattr(response, "id", None)
            recovery_record = session_state.metadata.get("resume_recovery_failure")
            prompt_accounting = prompt_bundle.prompt_accounting(
                prompt_render_mode=current_prompt_render_mode,
                rendered_prompt_text=current_prompt,
                memory_injected=current_memory_injected,
                static_tool_schema_injected=current_static_tool_schema_injected,
                decision_schema_injected=current_decision_schema_injected,
            )
            turn_metadata = build_provider_turn_metadata(
                capabilities=self.capabilities,
                continuation_path=continuation_path,
                prompt_render_mode=current_prompt_render_mode,
                memory_injected=current_memory_injected,
                static_tool_schema_injected=current_static_tool_schema_injected,
                decision_schema_injected=current_decision_schema_injected,
                retry_count=retry_count,
                remote_handle_kind="response_id",
                remote_handle_id=response_id,
                fresh_remote_turn=previous_response_id is None,
                resumed_remote=previous_response_id is not None,
                native_sync_used=native_sync_used,
                extra={
                    "native_response_id_present": response_id is not None,
                    "native_session_used": bool(previous_response_id),
                    "fresh_session": previous_response_id is None,
                    "resume_recovery_action": recovery_action,
                    "recovery_created_new_session": explicit_new_session_recovery,
                    "replaced_remote_handle_id": (
                        committed_response_id if explicit_new_session_recovery else None
                    ),
                    "resume_recovery_failure": recovery_record,
                    "rendered_prompt": prompt_accounting,
                },
            )
            updated_session = session_state.with_native_handle_update(
                response_id=response_id,
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
                        "last_replaced_remote_handle_id": committed_response_id,
                    }
                )
            return ProviderTurn(
                decision=decision,
                output_text=output_text,
                response_id=response_id,
                session_state=updated_session,
                provider_metadata=turn_metadata,
                progress_updates=tuple(progress_updates),
            )

        raise ProviderResponseError(
            f"OpenAI provider did not return a valid turnkey action: {last_error}"
        )

    def _summarize_memory_sync(
        self,
        session_state: ProviderSessionState,
        prior_summary_text: str,
        evicted_entries: tuple[ProviderMidHistoryEntry, ...],
    ) -> ProviderMemorySummaryResult:
        last_error: Exception | None = None
        prompt = render_memory_summary_request(
            prior_summary_text=prior_summary_text,
            evicted_entries=evicted_entries,
            summary_char_limit=session_state.summary_char_limit,
        )
        response_format = {
            "type": "json_schema",
            "name": "provider_memory_summary",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["summary_text"],
                "properties": {
                    "summary_text": {"type": "string", "minLength": 1},
                },
            },
        }
        current_prompt = prompt
        for _attempt in range(2):
            response = self._client.responses.create(
                model=self._model,
                instructions="Return only one JSON object with a compact summary_text field.",
                input=current_prompt,
                text=cast(Any, {"format": response_format}),
            )
            output_text = (response.output_text or "").strip()
            try:
                summary_text = validate_memory_summary_text(
                    parse_memory_summary_json(output_text),
                    char_limit=session_state.summary_char_limit,
                )
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
                    "response_id": getattr(response, "id", None),
                    "provider": "openai-api",
                    "model": self._model,
                },
            )
        raise ProviderResponseError(
            f"OpenAI provider did not return a valid memory summary: {last_error}"
        )
