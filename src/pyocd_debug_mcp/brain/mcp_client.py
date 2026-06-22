"""Thin stdio MCP client wrapper for the turnkey brain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import sys
from typing import Any, Protocol

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from pyocd_debug_mcp.brain.models import ToolCallResponse


class ToolClientProtocol(Protocol):
    """Subset of client behavior the runner depends on."""

    async def list_tool_names(self) -> set[str]:
        """Return the set of available tool names."""

    async def call_tool_text(
        self,
        name: str,
        arguments: dict[str, object] | None,
        *,
        timeout_seconds: float,
    ) -> ToolCallResponse:
        """Invoke one tool and flatten the result into text."""


@dataclass(frozen=True)
class ServerCommand:
    """Local server spawn parameters for the stdio MCP child."""

    command: str
    args: tuple[str, ...]
    cwd: Path | None = None
    env: dict[str, str] | None = None


def default_server_command() -> ServerCommand:
    return ServerCommand(
        command=sys.executable,
        args=("-m", "pyocd_debug_mcp.server"),
    )


class StdioToolClient(ToolClientProtocol):
    """Real stdio MCP client used by the turnkey CLI."""

    def __init__(self, server_command: ServerCommand) -> None:
        self._server_command = server_command
        self._stdio_cm: Any = None
        self._read_stream: Any = None
        self._write_stream: Any = None
        self._session: ClientSession | None = None
        self._session_cm: Any = None

    async def __aenter__(self) -> "StdioToolClient":
        params = StdioServerParameters(
            command=self._server_command.command,
            args=list(self._server_command.args),
            cwd=str(self._server_command.cwd) if self._server_command.cwd is not None else None,
            env=self._server_command.env,
        )
        self._stdio_cm = stdio_client(params)
        self._read_stream, self._write_stream = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(self._read_stream, self._write_stream)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._session_cm is not None:
            await self._session_cm.__aexit__(exc_type, exc, tb)
        if self._stdio_cm is not None:
            await self._stdio_cm.__aexit__(exc_type, exc, tb)
        self._session = None

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCP session is not open")
        return self._session

    async def list_tool_names(self) -> set[str]:
        session = self._require_session()
        result = await session.list_tools()
        return {tool.name for tool in result.tools}

    async def call_tool_text(
        self,
        name: str,
        arguments: dict[str, object] | None,
        *,
        timeout_seconds: float,
    ) -> ToolCallResponse:
        session = self._require_session()
        result = await session.call_tool(
            name,
            arguments,
            read_timeout_seconds=timedelta(seconds=timeout_seconds),
        )
        text_parts: list[str] = []
        for item in result.content:
            item_type = getattr(item, "type", "")
            if item_type == "text":
                text_parts.append(getattr(item, "text", ""))
        return ToolCallResponse(
            text="\n".join(part for part in text_parts if part).strip(),
            is_error=bool(result.isError),
        )
