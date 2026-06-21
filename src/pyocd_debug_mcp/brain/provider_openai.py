"""OpenAI-backed decision provider for the turnkey brain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

import anyio
from openai import OpenAI

from pyocd_debug_mcp.brain.actions import TurnDecision


class ProviderResponseError(RuntimeError):
    """Raised when the model does not return a valid structured action."""


@dataclass(frozen=True)
class ProviderTurn:
    decision: TurnDecision
    output_text: str
    response_id: str | None


class OpenAIDecisionProvider:
    """Thin wrapper over the OpenAI Responses API."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
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
                decision = _parse_decision_json(output_text)
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


def _parse_decision_json(output_text: str) -> TurnDecision:
    candidate = output_text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.startswith("json"):
            candidate = candidate[4:].lstrip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ProviderResponseError("Provider output did not contain a JSON object.")
    json_text = candidate[start : end + 1]
    payload = json.loads(json_text)
    return TurnDecision.model_validate(payload)
