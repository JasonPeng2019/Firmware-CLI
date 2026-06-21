"""Async stdio MCP client wrapper for the local turnkey brain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO_ROOT = Path(__file__).resolve().parents[3]
SESSION_ID_PATTERN = re.compile(r"session_id=([A-Za-z0-9T\-]+)")
PROBE_UID_PATTERN = re.compile(r"via probe ([^ ]+)")
ROUTE_PATTERN = re.compile(r" via ([A-Za-z0-9._-]+)(?:\.| \[)")
REFUSAL_PATTERN = re.compile(r"^Refused \[([^\]]+)\]: ")
BLOCK_PATTERN = re.compile(r"^Blocked \[([^\]]+)\]: ")


class MCPClientError(RuntimeError):
    """Raised when the turnkey brain's MCP client cannot complete an operation."""


@dataclass(frozen=True)
class ToolTextResult:
    tool_name: str
    text: str
    is_error: bool = False

    @property
    def refusal_code(self) -> str | None:
        match = REFUSAL_PATTERN.match(self.text)
        return match.group(1) if match else None

    @property
    def blocked_code(self) -> str | None:
        match = BLOCK_PATTERN.match(self.text)
        return match.group(1) if match else None

    @property
    def session_id(self) -> str | None:
        match = SESSION_ID_PATTERN.search(self.text)
        return match.group(1) if match else None

    @property
    def probe_uid(self) -> str | None:
        match = PROBE_UID_PATTERN.search(self.text)
        return match.group(1) if match else None

    @property
    def route_used(self) -> str | None:
        match = ROUTE_PATTERN.search(self.text)
        return match.group(1) if match else None


def _result_text(result: types.CallToolResult) -> str:
    parts: list[str] = []
    for block in result.content:
        if isinstance(block, types.TextContent):
            parts.append(block.text)
        elif isinstance(block, types.EmbeddedResource) and isinstance(block.resource, types.TextResourceContents):
            parts.append(block.resource.text)
    if parts:
        return "\n".join(part for part in parts if part)
    if result.structuredContent is not None:
        return str(result.structuredContent)
    return ""


class LocalMCPClient:
    """Thin async wrapper over the repo's local stdio MCP server."""

    def __init__(self, repo_root: Path = REPO_ROOT) -> None:
        self._repo_root = repo_root
        self._stdio_manager: Any = None
        self._session: ClientSession | None = None
        self.available_tools: tuple[str, ...] = ()

    async def __aenter__(self) -> "LocalMCPClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.stop()

    async def start(self) -> None:
        if self._session is not None:
            return
        params = StdioServerParameters(
            command="uv",
            args=["run", "pyocd-debug-mcp"],
            cwd=self._repo_root,
        )
        self._stdio_manager = stdio_client(params)
        read_stream, write_stream = await self._stdio_manager.__aenter__()
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()
        tools = await session.list_tools()
        self.available_tools = tuple(sorted(tool.name for tool in tools.tools))
        self._session = session

    async def stop(self) -> None:
        if self._session is not None:
            await self._session.__aexit__(None, None, None)
            self._session = None
        if self._stdio_manager is not None:
            await self._stdio_manager.__aexit__(None, None, None)
            self._stdio_manager = None

    async def call_tool(self, tool_name: str, arguments: dict[str, object] | None = None) -> ToolTextResult:
        if self._session is None:
            raise MCPClientError("The local MCP client has not been started.")
        if self.available_tools and tool_name not in self.available_tools:
            raise MCPClientError(f"Server does not expose tool '{tool_name}'.")
        result = await self._session.call_tool(tool_name, arguments=arguments)
        text = _result_text(result).strip()
        if result.isError:
            raise MCPClientError(text or f"Tool call failed: {tool_name}")
        return ToolTextResult(tool_name=tool_name, text=text, is_error=False)

    async def connect(
        self,
        *,
        board_id: str,
        unique_id: str | None = None,
        target: str | None = None,
        board_config: str | None = None,
    ) -> ToolTextResult:
        return await self.call_tool(
            "connect",
            {
                "board_id": board_id,
                "unique_id": unique_id,
                "target": target,
                "board_config": board_config,
            },
        )

    async def disconnect(self) -> ToolTextResult:
        return await self.call_tool("disconnect", {})

    async def get_board_info(self) -> ToolTextResult:
        return await self.call_tool("get_board_info", {})

    async def get_state(self) -> ToolTextResult:
        return await self.call_tool("get_state", {})

    async def halt(self) -> ToolTextResult:
        return await self.call_tool("halt", {})

    async def resume(self) -> ToolTextResult:
        return await self.call_tool("resume", {})

    async def reset(self, *, halt_after: bool = False) -> ToolTextResult:
        return await self.call_tool("reset", {"halt_after": halt_after})

    async def read_core_register(self, *, name: str) -> ToolTextResult:
        return await self.call_tool("read_core_register", {"name": name})

    async def read_memory(self, *, address: str, word_size: int = 32) -> ToolTextResult:
        return await self.call_tool(
            "read_memory",
            {"address": address, "word_size": word_size},
        )

    async def flash_firmware(
        self,
        *,
        path: str | None = None,
        halt_after_reset: bool = False,
    ) -> ToolTextResult:
        arguments: dict[str, object] = {"halt_after_reset": halt_after_reset}
        if path is not None:
            arguments["path"] = path
        return await self.call_tool("flash_firmware", arguments)

    async def read_serial(
        self,
        *,
        expected_text: str | None = None,
        read_seconds: float = 3.0,
        baudrate: int | None = None,
        port: str | None = None,
        reset_on_open: bool = False,
    ) -> ToolTextResult:
        return await self.call_tool(
            "read_serial",
            {
                "expected_text": expected_text,
                "read_seconds": read_seconds,
                "baudrate": baudrate,
                "port": port,
                "reset_on_open": reset_on_open,
            },
        )

    async def unlock_recover(self, *, confirm: bool = False) -> ToolTextResult:
        return await self.call_tool("unlock_recover", {"confirm": confirm})
