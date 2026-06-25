"""OpenAI-backed decision provider for the turnkey brain."""

from __future__ import annotations

from typing import Any, cast

import anyio
from openai import OpenAI

from pyocd_debug_mcp.brain.actions import TurnDecision
from pyocd_debug_mcp.brain.provider_parsing import (
    parse_memory_summary_json,
    parse_turn_decision_json,
)
from pyocd_debug_mcp.brain.provider_types import (
    ProviderCapabilities,
    ProviderContinuationPath,
    ProviderMemoryEntry,
    ProviderMemorySummaryResult,
    ProviderPromptBundle,
    ProviderSessionState,
    ProviderTurn,
    provider_has_local_memory,
    render_memory_summary_request,
    should_inject_native_memory_sync,
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
            continuation_mode="native-primary",
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
        last_error: Exception | None = None
        previous_response_id = (
            session_state.native_handle.response_id
            if session_state.native_handle is not None
            else None
        )
        use_local_memory = False
        continuation_path: ProviderContinuationPath = "native"
        if previous_response_id is None:
            use_local_memory = provider_has_local_memory(session_state)
            continuation_path = "local-memory-fallback" if use_local_memory else "native"
        elif should_inject_native_memory_sync(session_state):
            use_local_memory = True
            continuation_path = "local-memory-fallback"
        current_prompt = prompt_bundle.user_prompt_text(include_memory=use_local_memory)
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
            response = self._client.responses.create(
                **kwargs,
            )
            output_text = (response.output_text or "").strip()
            try:
                decision = parse_turn_decision_json(output_text)
            except Exception as exc:  # noqa: BLE001 - preserve structured parse failures
                last_error = exc
                current_prompt = (
                    f"{prompt_bundle.user_prompt_text(include_memory=use_local_memory)}\n\n"
                    "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                )
                continue
            response_id = getattr(response, "id", None)
            return ProviderTurn(
                decision=decision,
                output_text=output_text,
                response_id=response_id,
                session_state=session_state.with_native_handle_update(
                    response_id=response_id,
                ).with_last_continuation_path(
                    continuation_path,
                    metadata={
                        "continuation_mode": self.capabilities.continuation_mode,
                        "continuation_path": continuation_path,
                        "native_response_id_present": response_id is not None,
                        "native_session_used": bool(previous_response_id),
                        "memory_injected": use_local_memory,
                        "native_sync_used": use_local_memory and previous_response_id is not None,
                    },
                ),
                provider_metadata={
                    "continuation_mode": self.capabilities.continuation_mode,
                    "continuation_path": continuation_path,
                    "memory_injected": use_local_memory,
                    "native_sync_used": use_local_memory and previous_response_id is not None,
                },
            )

        raise ProviderResponseError(
            f"OpenAI provider did not return a valid turnkey action: {last_error}"
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
                    "response_id": getattr(response, "id", None),
                    "provider": "openai-api",
                    "model": self._model,
                },
            )
        raise ProviderResponseError(
            f"OpenAI provider did not return a valid memory summary: {last_error}"
        )
