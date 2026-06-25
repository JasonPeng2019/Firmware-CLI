"""OpenAI-backed decision provider for the turnkey brain."""

from __future__ import annotations

from typing import Any, cast

import anyio
from openai import OpenAI

from pyocd_debug_mcp.brain.actions import TurnDecision
from pyocd_debug_mcp.brain.provider_parsing import parse_turn_decision_json
from pyocd_debug_mcp.brain.provider_types import ProviderTurn
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

    async def next_decision(self, *, instructions: str, turn_prompt: str) -> ProviderTurn:
        return await anyio.to_thread.run_sync(self._next_decision_sync, instructions, turn_prompt)

    def _next_decision_sync(self, instructions: str, turn_prompt: str) -> ProviderTurn:
        last_error: Exception | None = None
        current_prompt = turn_prompt
        response_format = {
            "type": "json_schema",
            "name": "turn_decision",
            "strict": True,
            "schema": TurnDecision.model_json_schema(),
        }
        for _attempt in range(2):
            response = self._client.responses.create(
                model=self._model,
                instructions=instructions,
                input=current_prompt,
                text=cast(Any, {"format": response_format}),
            )
            output_text = (response.output_text or "").strip()
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
            f"OpenAI provider did not return a valid turnkey action: {last_error}"
        )
