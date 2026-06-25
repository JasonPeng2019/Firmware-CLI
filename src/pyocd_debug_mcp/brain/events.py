"""Structured event contracts for the turnkey brain and operator UX layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import inspect
from pathlib import Path
from typing import Any, TypeAlias


def event_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return str(value)


@dataclass(frozen=True)
class BrainEvent:
    event_kind: str
    timestamp: str
    board_id: str
    iteration: int | None
    session_id: str | None
    provider: str
    model: str | None
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "event_kind": self.event_kind,
            "timestamp": self.timestamp,
            "board_id": self.board_id,
            "iteration": self.iteration,
            "session_id": self.session_id,
            "provider": self.provider,
            "model": self.model,
            "message": self.message,
            "details": _jsonable(self.details),
        }


EventSink: TypeAlias = Callable[[BrainEvent], object | Awaitable[object]]


async def emit_event(sink: EventSink | None, event: BrainEvent) -> None:
    if sink is None:
        return
    result = sink(event)
    if inspect.isawaitable(result):
        await result
