"""Anthropic API-backed decision provider for the turnkey brain."""

from __future__ import annotations

from anthropic import Anthropic
import anyio

from pyocd_debug_mcp.brain.provider_parsing import (
    parse_memory_summary_json,
    parse_turn_decision_json,
)
from pyocd_debug_mcp.brain.provider_types import (
    ProviderCapabilities,
    ProviderMemoryEntry,
    ProviderMemorySummaryResult,
    ProviderProgressUpdate,
    ProviderPromptBundle,
    ProviderSessionState,
    ProviderTurn,
    render_memory_summary_request,
)
from pyocd_debug_mcp.timeouts import PROVIDER_REQUEST_TIMEOUT_SECONDS


class ProviderResponseError(RuntimeError):
    """Raised when the Anthropic provider does not return a valid structured action."""


class AnthropicDecisionProvider:
    """Thin wrapper over the Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = PROVIDER_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._client = Anthropic(api_key=api_key, timeout=timeout_seconds)
        self._model = model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_native_session=False,
            supports_transcript_continuation=True,
            supports_response_id_continuation=False,
            supports_tool_schema_prompt=True,
            continuation_mode="transcript-only",
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
        retry_count = 0
        base_prompt = prompt_bundle.render_bootstrap_text(include_memory=True)
        current_prompt = base_prompt
        current_prompt_render_mode = "bootstrap/full"
        current_memory_injected = bool(prompt_bundle.provider_memory_text.strip())
        current_static_tool_schema_injected = True
        current_decision_schema_injected = True
        progress_updates: list[ProviderProgressUpdate] = [
            ProviderProgressUpdate(
                stage="provider_request",
                message="Dispatching Anthropic Messages turn from canonical local memory.",
                details={
                    "continuation_path": "transcript-memory",
                    "prompt_render_mode": current_prompt_render_mode,
                    "memory_injected": current_memory_injected,
                },
            )
        ]
        for _attempt in range(2):
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=prompt_bundle.system_instructions,
                messages=[{"role": "user", "content": current_prompt}],
            )
            output_text = _extract_text(response).strip()
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
                        message="Anthropic returned invalid structured output; retrying with a schema-correction prompt.",
                        details={"retry_count": retry_count},
                    )
                )
                continue
            response_id = getattr(response, "id", None)
            return ProviderTurn(
                decision=decision,
                output_text=output_text,
                response_id=response_id,
                session_state=session_state.with_last_continuation_path(
                    "transcript-memory",
                    metadata={"continuation_kind": "transcript"},
                ),
                provider_metadata={
                    "continuation_kind": "transcript",
                    "continuation_mode": self.capabilities.continuation_mode,
                    "continuation_path": "transcript-memory",
                    "memory_injected": current_memory_injected,
                    "provider_response_id": response_id,
                    "prompt_render_mode": current_prompt_render_mode,
                    "static_tool_schema_injected": current_static_tool_schema_injected,
                    "decision_schema_injected": current_decision_schema_injected,
                    "retry_count": retry_count,
                },
                progress_updates=tuple(progress_updates),
            )

        raise ProviderResponseError(
            f"Anthropic provider did not return a valid turnkey action: {last_error}"
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
        current_prompt = prompt
        system = "Return only one JSON object with a non-empty summary_text field."
        for _attempt in range(2):
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": current_prompt}],
            )
            output_text = _extract_text(response).strip()
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
                    "provider": "anthropic-api",
                    "model": self._model,
                    "provider_response_id": getattr(response, "id", None),
                },
            )
        raise ProviderResponseError(
            f"Anthropic provider did not return a valid memory summary: {last_error}"
        )


def _extract_text(response: object) -> str:
    content = getattr(response, "content", ())
    chunks: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            chunks.append(getattr(block, "text", ""))
    return "".join(chunks)
