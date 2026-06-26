"""Anthropic API-backed decision provider for the turnkey brain."""

from __future__ import annotations

from anthropic import Anthropic
import anyio

from pyocd_debug_mcp.brain.provider_parsing import parse_turn_decision_json
from pyocd_debug_mcp.brain.provider_types import ProviderTurn
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
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def next_decision(
        self,
        *,
        instructions: str,
        turn_prompt: str,
        timeout_seconds: float | None = None,
    ) -> ProviderTurn:
        effective_timeout = self._timeout_seconds if timeout_seconds is None else timeout_seconds
        return await anyio.to_thread.run_sync(
            self._next_decision_sync,
            instructions,
            turn_prompt,
            effective_timeout,
        )

    def _next_decision_sync(
        self,
        instructions: str,
        turn_prompt: str,
        timeout_seconds: float,
    ) -> ProviderTurn:
        client = Anthropic(api_key=self._api_key, timeout=timeout_seconds)
        last_error: Exception | None = None
        current_prompt = turn_prompt
        for _attempt in range(2):
            response = client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=instructions,
                messages=[{"role": "user", "content": current_prompt}],
            )
            output_text = _extract_text(response).strip()
            try:
                decision = parse_turn_decision_json(output_text)
            except Exception as exc:  # noqa: BLE001 - preserve structured parse failures
                last_error = exc
                current_prompt = (
                    f"{turn_prompt}\n\n"
                    "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                )
                continue
            return ProviderTurn(
                decision=decision,
                output_text=output_text,
                response_id=getattr(response, "id", None),
            )

        raise ProviderResponseError(
            f"Anthropic provider did not return a valid turnkey action: {last_error}"
        )


def _extract_text(response: object) -> str:
    content = getattr(response, "content", ())
    chunks: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            chunks.append(getattr(block, "text", ""))
    return "".join(chunks)
