"""Shared provider contracts for turnkey decision backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pyocd_debug_mcp.brain.actions import TurnDecision


@dataclass(frozen=True)
class ProviderSessionState:
    provider_session_id: str | None = None
    response_id: str | None = None
    turn_index: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderProgressUpdate:
    stage: str
    message: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderTurn:
    decision: TurnDecision
    output_text: str
    response_id: str | None
    session_state: ProviderSessionState | None = None
    progress_updates: tuple[ProviderProgressUpdate, ...] = ()


class DecisionProvider(Protocol):
    async def next_decision(self, *, instructions: str, turn_prompt: str) -> ProviderTurn: ...
