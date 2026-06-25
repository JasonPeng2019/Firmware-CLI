"""Shared parsing helpers for turnkey provider outputs."""

from __future__ import annotations

import json

from pyocd_debug_mcp.brain.actions import TurnDecision


def parse_turn_decision_json(output_text: str) -> TurnDecision:
    candidate = output_text.strip()
    candidate = _extract_json_candidate(candidate)
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Provider output did not contain a JSON object.")
    payload = json.loads(candidate[start : end + 1])
    return TurnDecision.model_validate(payload)


def parse_memory_summary_json(output_text: str) -> str:
    candidate = _extract_json_candidate(output_text.strip())
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Provider output did not contain a summary JSON object.")
    payload = json.loads(candidate[start : end + 1])
    summary_text = payload.get("summary_text")
    if not isinstance(summary_text, str) or not summary_text.strip():
        raise ValueError("Provider summary output did not contain a non-empty summary_text.")
    return summary_text.strip()


def _extract_json_candidate(candidate: str) -> str:
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.startswith("json"):
            candidate = candidate[4:].lstrip()
    return candidate
