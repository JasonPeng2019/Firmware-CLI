"""Shared timeout budgets for host, server, and turnkey runtime paths."""

from __future__ import annotations

from dataclasses import dataclass, replace

# PROJECT-DEFINED (runtime command ceiling for probe/vendor enumeration helpers).
DEFAULT_EXTERNAL_COMMAND_TIMEOUT_SECONDS = 30.0

# PROJECT-DEFINED (long setup command ceiling; allows uv sync without unbounded waits).
SETUP_COMMAND_TIMEOUT_SECONDS = 900.0

# PROJECT-DEFINED (local MCP startup should fail before any tool-level timeout applies).
MCP_STARTUP_TIMEOUT_SECONDS = 30.0

# PROJECT-DEFINED (model providers can be slow, but must not block forever).
PROVIDER_REQUEST_TIMEOUT_SECONDS = 300.0

# PROJECT-DEFINED (explicit pyOCD operation ceilings; mirrors/tightens pyOCD defaults).
PYOCD_STEP_TIMEOUT_SECONDS = 2.0
PYOCD_RESET_HALT_TIMEOUT_SECONDS = 2.0
PYOCD_DAP_RECOVER_TIMEOUT_SECONDS = 2.0
PYOCD_CORE_RECOVER_TIMEOUT_SECONDS = 2.0
PYOCD_FLASH_INIT_TIMEOUT_SECONDS = 5.0
PYOCD_FLASH_PROGRAM_TIMEOUT_SECONDS = 10.0
PYOCD_FLASH_ERASE_SECTOR_TIMEOUT_SECONDS = 10.0
PYOCD_FLASH_ERASE_ALL_TIMEOUT_SECONDS = 240.0
PYOCD_FLASH_ANALYZER_TIMEOUT_SECONDS = 30.0

# PROJECT-DEFINED (current turnkey client-side backstop defaults).
TURNKEY_DEFAULT_TOOL_TIMEOUT_SECONDS = 30.0
TURNKEY_CONNECT_TIMEOUT_SECONDS = 60.0
TURNKEY_FLASH_TIMEOUT_SECONDS = 240.0
TURNKEY_RECOVER_TIMEOUT_SECONDS = 180.0
TURNKEY_UART_TIMEOUT_SECONDS = 30.0
TURNKEY_UART_READ_GRACE_SECONDS = 12.0  # PROJECT-DEFINED (extra wall-clock budget over the requested UART read window)
TURNKEY_BUILD_TIMEOUT_SECONDS = 1800.0  # PROJECT-DEFINED (allow real workspace builds, but not indefinite hangs)
TURNKEY_BATCH_TIMEOUT_SECONDS = 1800.0  # PROJECT-DEFINED (a batch may include one full build/flash/verify cycle)


@dataclass(frozen=True)
class TurnkeyTimeoutConfig:
    default_tool_seconds: float = TURNKEY_DEFAULT_TOOL_TIMEOUT_SECONDS
    connect_seconds: float = TURNKEY_CONNECT_TIMEOUT_SECONDS
    flash_seconds: float = TURNKEY_FLASH_TIMEOUT_SECONDS
    recover_seconds: float = TURNKEY_RECOVER_TIMEOUT_SECONDS
    uart_read_seconds: float = TURNKEY_UART_TIMEOUT_SECONDS
    uart_read_grace_seconds: float = TURNKEY_UART_READ_GRACE_SECONDS
    build_seconds: float = TURNKEY_BUILD_TIMEOUT_SECONDS
    batch_seconds: float = TURNKEY_BATCH_TIMEOUT_SECONDS
    external_command_seconds: float = DEFAULT_EXTERNAL_COMMAND_TIMEOUT_SECONDS
    provider_seconds: float = PROVIDER_REQUEST_TIMEOUT_SECONDS
    mcp_startup_seconds: float = MCP_STARTUP_TIMEOUT_SECONDS

    def to_record(self) -> dict[str, float]:
        return {
            "default_tool_seconds": self.default_tool_seconds,
            "connect_seconds": self.connect_seconds,
            "flash_seconds": self.flash_seconds,
            "recover_seconds": self.recover_seconds,
            "uart_read_seconds": self.uart_read_seconds,
            "uart_read_grace_seconds": self.uart_read_grace_seconds,
            "build_seconds": self.build_seconds,
            "batch_seconds": self.batch_seconds,
            "external_command_seconds": self.external_command_seconds,
            "provider_seconds": self.provider_seconds,
            "mcp_startup_seconds": self.mcp_startup_seconds,
        }

    def tool_timeout_seconds(self, tool_name: str, *, serial_read_seconds: float) -> float:
        if tool_name == "connect":
            return self.connect_seconds
        if tool_name == "flash_firmware":
            return self.flash_seconds
        if tool_name == "unlock_recover":
            return self.recover_seconds
        if tool_name == "read_serial":
            return max(self.uart_read_seconds, serial_read_seconds + self.uart_read_grace_seconds)
        return self.default_tool_seconds


@dataclass(frozen=True)
class TurnkeyTimeoutUpdate:
    default_tool_seconds: float | None = None
    connect_seconds: float | None = None
    flash_seconds: float | None = None
    recover_seconds: float | None = None
    uart_read_seconds: float | None = None
    uart_read_grace_seconds: float | None = None
    build_seconds: float | None = None
    batch_seconds: float | None = None
    external_command_seconds: float | None = None
    provider_seconds: float | None = None
    mcp_startup_seconds: float | None = None


def default_turnkey_timeout_config() -> TurnkeyTimeoutConfig:
    return TurnkeyTimeoutConfig()


def apply_turnkey_timeout_update(
    base: TurnkeyTimeoutConfig,
    update: TurnkeyTimeoutUpdate | None,
) -> TurnkeyTimeoutConfig:
    if update is None:
        return base
    current = base
    for field_name in (
        "default_tool_seconds",
        "connect_seconds",
        "flash_seconds",
        "recover_seconds",
        "uart_read_seconds",
        "uart_read_grace_seconds",
        "build_seconds",
        "batch_seconds",
        "external_command_seconds",
        "provider_seconds",
        "mcp_startup_seconds",
    ):
        value = getattr(update, field_name)
        if value is None:
            continue
        if value <= 0:
            raise ValueError(f"{field_name} must be > 0")
        current = replace(current, **{field_name: value})
    return current


def subprocess_timeout_stream_text(value: object) -> str:
    """Normalize subprocess timeout output to text for diagnostics."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
