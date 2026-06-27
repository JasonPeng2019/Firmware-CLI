"""Session-scoped client-action store contracts for R12."""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ClientActionRecord:
    name: str
    relative_path: str
    description: str | None = None
    content: str = ""


@dataclass(frozen=True)
class ClientActionSnapshot:
    name: str
    relative_path: str
    description: str | None
    content: str
    content_sha256: str


class ClientActionStore(Protocol):
    def list_actions(self) -> tuple[ClientActionRecord, ...]: ...

    def get_action(self, name: str) -> ClientActionRecord | None: ...

    def put_action(self, record: ClientActionRecord) -> None: ...

    def snapshot_action(self, name: str) -> ClientActionSnapshot | None: ...


class InMemoryClientActionStore:
    """Deterministic session-local client-action store."""

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

    def snapshot_action(self, name: str) -> ClientActionSnapshot | None:
        record = self.get_action(name)
        if record is None:
            return None
        digest = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        return ClientActionSnapshot(
            name=record.name,
            relative_path=record.relative_path,
            description=record.description,
            content=record.content,
            content_sha256=digest,
        )


class GatedClientActionServer:
    """Narrow async server API injected only while a client action is running."""

    def __init__(self, call_tool: Any, allowed_tools: Iterable[str]) -> None:
        self._call_tool = call_tool
        self._allowed_tools = frozenset(allowed_tools)

    async def call_tool(self, tool_name: str, arguments: dict[str, object] | None = None) -> Any:
        if tool_name not in self._allowed_tools:
            raise PermissionError(f"Client action cannot call server tool: {tool_name}")
        return await self._call_tool(tool_name, arguments or {})


async def run_client_action(
    snapshot: ClientActionSnapshot,
    *,
    inputs: dict[str, object],
    server: GatedClientActionServer,
) -> object:
    """Run a snapshotted async client action with a gated server API."""

    globals_dict: dict[str, object] = {
        "__builtins__": {
            "bool": bool,
            "dict": dict,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "str": str,
            "sum": sum,
        }
    }
    locals_dict: dict[str, object] = {}
    exec(compile(snapshot.content, snapshot.relative_path, "exec"), globals_dict, locals_dict)
    run_func = locals_dict.get("run") or globals_dict.get("run")
    if not callable(run_func):
        raise ValueError(f"Client action {snapshot.name!r} must define run(inputs, server).")
    result = run_func(inputs, server)
    if inspect.isawaitable(result):
        return await result
    return result
