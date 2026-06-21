"""Shared parsing helpers for turnkey provider outputs."""

from __future__ import annotations

import json

from pyocd_debug_mcp.brain.actions import TurnDecision


def parse_turn_decision_json(output_text: str) -> TurnDecision:
    candidate = output_text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.startswith("json"):
            candidate = candidate[4:].lstrip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Provider output did not contain a JSON object.")
    payload = json.loads(candidate[start : end + 1])
    return TurnDecision.model_validate(payload)
