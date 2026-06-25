"""Async stdio MCP client wrapper for the local turnkey brain."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import re
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol

import anyio
from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.exceptions import McpError

from pyocd_debug_mcp.timeouts import MCP_STARTUP_TIMEOUT_SECONDS

REPO_ROOT = Path(__file__).resolve().parents[3]
SESSION_ID_PATTERN = re.compile(r"session_id=([A-Za-z0-9T\-]+)")
PROBE_UID_PATTERN = re.compile(r"via probe ([^ ]+)")
ROUTE_PATTERN = re.compile(r" via ([A-Za-z0-9._-]+)(?:\.| \[)")
REFUSAL_PATTERN = re.compile(r"^Refused \[([^\]]+)\]: ")
BLOCK_PATTERN = re.compile(r"^Blocked \[([^\]]+)\]: ")


class MCPClientError(RuntimeError):
    """Raised when the turnkey brain's MCP client cannot complete an operation."""


class ToolClientProtocol(Protocol):
    """Transport-level MCP client surface used by the turnkey brain."""

    async def __aenter__(self) -> "ToolClientProtocol":
        """Enter the underlying session context."""

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Leave the underlying session context."""

    async def list_tool_descriptors(self) -> tuple["ToolDescriptor", ...]:
        """Return the currently available tool metadata."""

    async def call_tool_text(
        self,
        name: str,
        arguments: dict[str, object] | None,
        *,
        timeout_seconds: float | None = None,
    ) -> "ToolTextResult":
        """Call one tool and flatten its text result."""


@dataclass(frozen=True)
class ServerCommand:
    """Spawn parameters for the local stdio MCP child."""

    command: str
    args: tuple[str, ...]
    cwd: Path | None = None
    env: dict[str, str] | None = None


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    description: str
    input_schema: dict[str, Any]

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


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


def _is_mcp_timeout_error(exc: BaseException) -> bool:
    if not isinstance(exc, McpError):
        return False
    if getattr(exc, "error", None) is not None and getattr(exc.error, "code", None) == 408:
        return True
    return "timed out while waiting for response" in str(exc).lower()


def _is_expected_stdio_cleanup_error(exc: BaseException) -> bool:
    grouped = getattr(exc, "exceptions", None)
    if grouped is not None:
        return all(_is_expected_stdio_cleanup_error(item) for item in grouped)
    if isinstance(exc, (anyio.BrokenResourceError, anyio.ClosedResourceError, ProcessLookupError)):
        return True
    if isinstance(exc, RuntimeError):
        lowered = str(exc).lower()
        return "cancel scope" in lowered or "this cancel scope is not active" in lowered
    if isinstance(exc, AttributeError):
        return "_exceptions" in str(exc)
    return False


def default_server_command(repo_root: Path = REPO_ROOT) -> ServerCommand:
    return ServerCommand(
        command="uv",
        args=("run", "pyocd-debug-mcp"),
        cwd=repo_root,
    )


class StdioToolClient:
    """Transport-only stdio MCP client."""

    def __init__(self, server_command: ServerCommand) -> None:
        self._server_command = server_command
        self._stdio_manager: Any = None
        self._session: ClientSession | None = None

    @staticmethod
    async def _safe_close(
        closer: Any,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if closer is None:
            return
        try:
            await closer.__aexit__(exc_type, exc, tb)
        except BaseException as cleanup_exc:
            if not _is_expected_stdio_cleanup_error(cleanup_exc):
                raise

    async def __aenter__(self) -> "StdioToolClient":
        params = StdioServerParameters(
            command=self._server_command.command,
            args=list(self._server_command.args),
            cwd=self._server_command.cwd,
            env=self._server_command.env,
        )
        manager = stdio_client(params)
        session: ClientSession | None = None
        try:
            read_stream, write_stream = await manager.__aenter__()
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()
        except BaseException as exc:
            if session is not None:
                await self._safe_close(session, type(exc), exc, exc.__traceback__)
            await self._safe_close(manager, type(exc), exc, exc.__traceback__)
            raise
        self._stdio_manager = manager
        self._session = session
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is not None:
            await self._safe_close(self._session, exc_type, exc, tb)
            self._session = None
        if self._stdio_manager is not None:
            await self._safe_close(self._stdio_manager, exc_type, exc, tb)
            self._stdio_manager = None

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise MCPClientError("The local MCP client has not been started.")
        return self._session

    async def list_tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        session = self._require_session()
        tools = await session.list_tools()
        return tuple(
            ToolDescriptor(
                name=tool.name,
                description=(tool.description or "").strip(),
                input_schema=dict(tool.inputSchema or {}),
            )
            for tool in tools.tools
        )

    async def call_tool_text(
        self,
        name: str,
        arguments: dict[str, object] | None,
        *,
        timeout_seconds: float | None = None,
    ) -> ToolTextResult:
        session = self._require_session()
        timeout = timedelta(seconds=timeout_seconds) if timeout_seconds is not None else None
        try:
            result = await session.call_tool(
                name,
                arguments=arguments,
                read_timeout_seconds=timeout,
            )
        except McpError as exc:
            if _is_mcp_timeout_error(exc):
                raise MCPClientError(
                    f"Tool '{name}' timed out after {(timeout_seconds or 0.0):.0f}s."
                ) from exc
            raise MCPClientError(str(exc)) from exc
        return ToolTextResult(
            tool_name=name,
            text=_result_text(result).strip(),
            is_error=bool(result.isError),
        )


class LocalMCPClient:
    """Parsed async wrapper over the repo's local stdio MCP server."""

    def __init__(
        self,
        repo_root: Path = REPO_ROOT,
        *,
        server_command: ServerCommand | None = None,
        startup_timeout_seconds: float | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._transport: ToolClientProtocol = StdioToolClient(
            server_command or default_server_command(repo_root)
        )
        self.available_tools: tuple[str, ...] = ()
        self._startup_timeout_seconds = (
            MCP_STARTUP_TIMEOUT_SECONDS if startup_timeout_seconds is None else startup_timeout_seconds
        )
        self.tool_descriptors: tuple[ToolDescriptor, ...] = ()

    async def __aenter__(self) -> "LocalMCPClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.stop()

    async def start(self) -> None:
        if self.available_tools:
            return

        async def _startup() -> tuple[ToolDescriptor, ...]:
            await self._transport.__aenter__()
            return await self._transport.list_tool_descriptors()

        try:
            descriptors = await asyncio.wait_for(_startup(), timeout=self._startup_timeout_seconds)
        except TimeoutError as exc:
            await self._transport.__aexit__(type(exc), exc, exc.__traceback__)
            raise MCPClientError(
                f"Local MCP server startup timed out after {self._startup_timeout_seconds:.0f}s."
            ) from exc
        except Exception as exc:
            await self._transport.__aexit__(type(exc), exc, exc.__traceback__)
            raise
        self.tool_descriptors = tuple(sorted(descriptors, key=lambda item: item.name))
        self.available_tools = tuple(descriptor.name for descriptor in self.tool_descriptors)

    async def stop(self) -> None:
        await self._transport.__aexit__(None, None, None)
        self.available_tools = ()
        self.tool_descriptors = ()

    async def list_tool_names(self) -> set[str]:
        if not self.tool_descriptors:
            raise MCPClientError("The local MCP client has not been started.")
        return {descriptor.name for descriptor in self.tool_descriptors}

    async def list_tools(self) -> tuple[ToolDescriptor, ...]:
        if not self.tool_descriptors:
            raise MCPClientError("The local MCP client has not been started.")
        return self.tool_descriptors

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, object] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> ToolTextResult:
        if not self.available_tools:
            raise MCPClientError("The local MCP client has not been started.")
        if self.available_tools and tool_name not in self.available_tools:
            raise MCPClientError(f"Server does not expose tool '{tool_name}'.")
        result = await self._transport.call_tool_text(
            tool_name,
            arguments,
            timeout_seconds=timeout_seconds,
        )
        if result.is_error:
            raise MCPClientError(result.text or f"Tool call failed: {tool_name}")
        return result

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
