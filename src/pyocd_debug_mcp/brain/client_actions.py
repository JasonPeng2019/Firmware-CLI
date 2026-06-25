"""Session-scoped client-action store contracts for future R12 work."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ClientActionRecord:
    name: str
    relative_path: str
    description: str | None = None


class ClientActionStore(Protocol):
    def list_actions(self) -> tuple[ClientActionRecord, ...]: ...

    def get_action(self, name: str) -> ClientActionRecord | None: ...

    def put_action(self, record: ClientActionRecord) -> None: ...


class InMemoryClientActionStore:
    """Deterministic session-local store used until client actions are implemented."""

    def __init__(self, initial_actions: Iterable[ClientActionRecord] | None = None) -> None:
        self._records: dict[str, ClientActionRecord] = {}
        for record in initial_actions or ():
            self.put_action(record)

    def list_actions(self) -> tuple[ClientActionRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda record: record.name))

    def get_action(self, name: str) -> ClientActionRecord | None:
        return self._records.get(name)

    def put_action(self, record: ClientActionRecord) -> None:
        self._records[record.name] = record
