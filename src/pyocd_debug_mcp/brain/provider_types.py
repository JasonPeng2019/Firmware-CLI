"""Shared provider contracts for turnkey decision backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pyocd_debug_mcp.brain.actions import TurnDecision


@dataclass(frozen=True)
class ProviderTurn:
    decision: TurnDecision
    output_text: str
    response_id: str | None


class DecisionProvider(Protocol):
    async def next_decision(self, *, instructions: str, turn_prompt: str) -> ProviderTurn: ...
