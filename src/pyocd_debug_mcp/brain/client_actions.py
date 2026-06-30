"""Session-scoped client-action store contracts for R12."""

from __future__ import annotations

import ast
import hashlib
import inspect
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


CLIENT_ACTION_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9_.-]+$"
)  # PROJECT-DEFINED (JSON/prompt-stable id)


class ClientActionLoadError(ValueError):
    """Raised when CLI-provided client-action registrations are invalid."""


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


def parse_client_action_spec(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise ClientActionLoadError("client action must be NAME=PATH")
    name, path_text = raw.split("=", 1)
    name = name.strip()
    path_text = path_text.strip()
    if not name:
        raise ClientActionLoadError("client action name cannot be empty")
    if not CLIENT_ACTION_NAME_PATTERN.fullmatch(name):
        raise ClientActionLoadError(
            "client action name may contain only letters, digits, underscore, dash, and dot"
        )
    if not path_text:
        raise ClientActionLoadError("client action path cannot be empty")
    return name, path_text


def load_client_actions_from_specs(
    specs: Iterable[str],
    *,
    base_dir: Path | None = None,
) -> InMemoryClientActionStore:
    records: list[ClientActionRecord] = []
    seen_names: set[str] = set()
    root = (base_dir or Path.cwd()).resolve()
    for raw in specs:
        name, path_text = parse_client_action_spec(raw)
        if name in seen_names:
            raise ClientActionLoadError(f"duplicate client action name: {name}")
        seen_names.add(name)
        path = Path(path_text).expanduser()
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        if not path.exists() or not path.is_file():
            raise ClientActionLoadError(f"client action file does not exist: {path_text}")
        content = path.read_text(encoding="utf-8", errors="replace")
        if not content.strip():
            raise ClientActionLoadError(f"client action file is empty: {path_text}")
        try:
            parsed = ast.parse(content, filename=str(path))
        except SyntaxError as exc:
            raise ClientActionLoadError(
                f"client action {name!r} is not valid Python: {exc.msg}"
            ) from exc
        if not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run"
            for node in parsed.body
        ):
            raise ClientActionLoadError(f"client action {name!r} must define run(inputs, server)")
        description = _description_from_module(parsed) or path.stem.replace("_", "-")
        records.append(
            ClientActionRecord(
                name=name,
                relative_path=path_text,
                description=description,
                content=content,
            )
        )
    return InMemoryClientActionStore(records)


def snapshot_all_actions(store: ClientActionStore) -> tuple[ClientActionSnapshot, ...]:
    snapshots: list[ClientActionSnapshot] = []
    for record in store.list_actions():
        snapshot = store.snapshot_action(record.name)
        if snapshot is not None:
            snapshots.append(snapshot)
    return tuple(snapshots)


def render_client_action_prompt_section(store: ClientActionStore) -> str:
    snapshots = snapshot_all_actions(store)
    if not snapshots:
        return "Registered client actions:\n(none)"
    lines = ["Registered client actions:"]
    for snapshot in snapshots:
        description = snapshot.description or "(none)"
        lines.append(
            "- "
            f"name={snapshot.name}; "
            f"path={snapshot.relative_path}; "
            f"sha256={snapshot.content_sha256}; "
            f"description={description}"
        )
    return "\n".join(lines)


def _description_from_module(module: ast.Module) -> str | None:
    docstring = ast.get_docstring(module)
    if not docstring:
        return None
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


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
