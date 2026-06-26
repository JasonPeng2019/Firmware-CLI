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

# PROJECT-DEFINED (default turnkey client timeout for ordinary MCP tool calls).
TURNKEY_DEFAULT_TOOL_TIMEOUT_SECONDS = 30.0

# PROJECT-DEFINED (turnkey connect needs a longer ceiling than ordinary reads).
TURNKEY_CONNECT_TIMEOUT_SECONDS = 60.0

# PROJECT-DEFINED (turnkey flash can legitimately take much longer than reads).
TURNKEY_FLASH_TIMEOUT_SECONDS = 240.0

# PROJECT-DEFINED (turnkey recover/unlock can legitimately take much longer than reads).
TURNKEY_RECOVER_TIMEOUT_SECONDS = 180.0

# PROJECT-DEFINED (default UART read wall-clock floor for turnkey client reads).
TURNKEY_UART_TIMEOUT_SECONDS = 30.0

# PROJECT-DEFINED (extra wall-clock budget over the requested UART read window).
TURNKEY_UART_READ_GRACE_SECONDS = 12.0

# PROJECT-DEFINED (allow real workspace builds, but not indefinite hangs).
TURNKEY_BUILD_TIMEOUT_SECONDS = 1800.0

# PROJECT-DEFINED (a batch may include one full build/flash/verify cycle).
TURNKEY_BATCH_TIMEOUT_SECONDS = 1800.0

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


@dataclass(frozen=True)
class TimeoutClampRange:
    min_seconds: float
    max_seconds: float

    def validate(self, field_name: str, value: float) -> None:
        if value < self.min_seconds or value > self.max_seconds:
            raise ValueError(
                f"{field_name} must be within {self.min_seconds:g}..{self.max_seconds:g} seconds"
            )

    def clamp(self, value: float) -> float:
        return min(max(value, self.min_seconds), self.max_seconds)


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
class ServerTimeoutConfig:
    step_instruction_seconds: float = PYOCD_STEP_TIMEOUT_SECONDS
    reset_halt_seconds: float = PYOCD_RESET_HALT_TIMEOUT_SECONDS
    dap_recover_seconds: float = PYOCD_DAP_RECOVER_TIMEOUT_SECONDS
    core_recover_seconds: float = PYOCD_CORE_RECOVER_TIMEOUT_SECONDS
    flash_init_seconds: float = PYOCD_FLASH_INIT_TIMEOUT_SECONDS
    flash_program_seconds: float = PYOCD_FLASH_PROGRAM_TIMEOUT_SECONDS
    flash_erase_sector_seconds: float = PYOCD_FLASH_ERASE_SECTOR_TIMEOUT_SECONDS
    flash_erase_all_seconds: float = PYOCD_FLASH_ERASE_ALL_TIMEOUT_SECONDS
    flash_analyzer_seconds: float = PYOCD_FLASH_ANALYZER_TIMEOUT_SECONDS

    def to_record(self) -> dict[str, float]:
        return {
            "step_instruction_seconds": self.step_instruction_seconds,
            "reset_halt_seconds": self.reset_halt_seconds,
            "dap_recover_seconds": self.dap_recover_seconds,
            "core_recover_seconds": self.core_recover_seconds,
            "flash_init_seconds": self.flash_init_seconds,
            "flash_program_seconds": self.flash_program_seconds,
            "flash_erase_sector_seconds": self.flash_erase_sector_seconds,
            "flash_erase_all_seconds": self.flash_erase_all_seconds,
            "flash_analyzer_seconds": self.flash_analyzer_seconds,
        }

    def pyocd_options(self) -> dict[str, object]:
        return {
            "cpu.step.instruction.timeout": self.step_instruction_seconds,
            "reset.halt_timeout": self.reset_halt_seconds,
            "reset.dap_recover.timeout": self.dap_recover_seconds,
            "reset.core_recover.timeout": self.core_recover_seconds,
            "flash.timeout.init": self.flash_init_seconds,
            "flash.timeout.program": self.flash_program_seconds,
            "flash.timeout.erase_sector": self.flash_erase_sector_seconds,
            "flash.timeout.erase_all": self.flash_erase_all_seconds,
            "flash.timeout.analyzer": self.flash_analyzer_seconds,
        }


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


@dataclass(frozen=True)
class ServerTimeoutUpdate:
    step_instruction_seconds: float | None = None
    reset_halt_seconds: float | None = None
    dap_recover_seconds: float | None = None
    core_recover_seconds: float | None = None
    flash_init_seconds: float | None = None
    flash_program_seconds: float | None = None
    flash_erase_sector_seconds: float | None = None
    flash_erase_all_seconds: float | None = None
    flash_analyzer_seconds: float | None = None

    def changed_fields(self) -> tuple[str, ...]:
        return tuple(
            field_name
            for field_name in SERVER_TIMEOUT_UPDATE_FIELDS
            if getattr(self, field_name) is not None
        )


TURNKEY_TIMEOUT_CLAMP_RANGES: dict[str, TimeoutClampRange] = {
    "default_tool_seconds": TimeoutClampRange(5.0, 90.0),
    "connect_seconds": TimeoutClampRange(15.0, 180.0),
    "flash_seconds": TimeoutClampRange(60.0, 600.0),
    "recover_seconds": TimeoutClampRange(60.0, 600.0),
    "uart_read_seconds": TimeoutClampRange(5.0, 120.0),
    "uart_read_grace_seconds": TimeoutClampRange(1.0, 30.0),
    "build_seconds": TimeoutClampRange(120.0, 3600.0),
    "batch_seconds": TimeoutClampRange(120.0, 3600.0),
    "external_command_seconds": TimeoutClampRange(10.0, 120.0),
    "provider_seconds": TimeoutClampRange(30.0, 600.0),
    "mcp_startup_seconds": TimeoutClampRange(10.0, 90.0),
}

SERVER_TIMEOUT_CLAMP_RANGES: dict[str, TimeoutClampRange] = {
    "step_instruction_seconds": TimeoutClampRange(0.5, 5.0),
    "reset_halt_seconds": TimeoutClampRange(1.0, 10.0),
    "dap_recover_seconds": TimeoutClampRange(1.0, 15.0),
    "core_recover_seconds": TimeoutClampRange(1.0, 15.0),
    "flash_init_seconds": TimeoutClampRange(2.0, 30.0),
    "flash_program_seconds": TimeoutClampRange(5.0, 60.0),
    "flash_erase_sector_seconds": TimeoutClampRange(5.0, 60.0),
    "flash_erase_all_seconds": TimeoutClampRange(60.0, 600.0),
    "flash_analyzer_seconds": TimeoutClampRange(10.0, 120.0),
}

TURNKEY_TIMEOUT_UPDATE_FIELDS = tuple(TURNKEY_TIMEOUT_CLAMP_RANGES)
SERVER_TIMEOUT_UPDATE_FIELDS = tuple(SERVER_TIMEOUT_CLAMP_RANGES)


def default_server_timeout_config() -> ServerTimeoutConfig:
    return ServerTimeoutConfig()


def default_turnkey_timeout_config() -> TurnkeyTimeoutConfig:
    return TurnkeyTimeoutConfig()


def validate_turnkey_timeout_update(update: TurnkeyTimeoutUpdate) -> None:
    for field_name in TURNKEY_TIMEOUT_UPDATE_FIELDS:
        value = getattr(update, field_name)
        if value is None:
            continue
        TURNKEY_TIMEOUT_CLAMP_RANGES[field_name].validate(field_name, value)


def validate_server_timeout_update(update: ServerTimeoutUpdate) -> None:
    for field_name in SERVER_TIMEOUT_UPDATE_FIELDS:
        value = getattr(update, field_name)
        if value is None:
            continue
        SERVER_TIMEOUT_CLAMP_RANGES[field_name].validate(field_name, value)


def server_timeout_update_to_record(update: ServerTimeoutUpdate | None) -> dict[str, float] | None:
    if update is None:
        return None
    return {
        field_name: value
        for field_name in update.changed_fields()
        if (value := getattr(update, field_name)) is not None
    }


def merge_server_timeout_updates(
    base: ServerTimeoutUpdate | None,
    new: ServerTimeoutUpdate | None,
) -> ServerTimeoutUpdate | None:
    if base is None:
        return new
    if new is None:
        return base
    payload = {
        **(server_timeout_update_to_record(base) or {}),
        **(server_timeout_update_to_record(new) or {}),
    }
    if not payload:
        return None
    return ServerTimeoutUpdate(**payload)


def apply_turnkey_timeout_update(
    base: TurnkeyTimeoutConfig,
    update: TurnkeyTimeoutUpdate | None,
) -> TurnkeyTimeoutConfig:
    if update is None:
        return base
    validate_turnkey_timeout_update(update)
    current = base
    for field_name in TURNKEY_TIMEOUT_UPDATE_FIELDS:
        value = getattr(update, field_name)
        if value is None:
            continue
        current = replace(current, **{field_name: value})
    return current


def apply_server_timeout_update(
    base: ServerTimeoutConfig,
    update: ServerTimeoutUpdate | None,
) -> ServerTimeoutConfig:
    if update is None:
        return base
    validate_server_timeout_update(update)
    current = base
    for field_name in SERVER_TIMEOUT_UPDATE_FIELDS:
        value = getattr(update, field_name)
        if value is None:
            continue
        current = replace(current, **{field_name: value})
    return current


def clamp_turnkey_timeout_value(field_name: str, value: float) -> float:
    return TURNKEY_TIMEOUT_CLAMP_RANGES[field_name].clamp(value)


def clamp_server_timeout_value(field_name: str, value: float) -> float:
    return SERVER_TIMEOUT_CLAMP_RANGES[field_name].clamp(value)


def server_timeouts_from_turnkey_config(config: TurnkeyTimeoutConfig) -> ServerTimeoutConfig:
    default_ratio = config.default_tool_seconds / TURNKEY_DEFAULT_TOOL_TIMEOUT_SECONDS
    connect_ratio = config.connect_seconds / TURNKEY_CONNECT_TIMEOUT_SECONDS
    recover_ratio = config.recover_seconds / TURNKEY_RECOVER_TIMEOUT_SECONDS
    flash_ratio = config.flash_seconds / TURNKEY_FLASH_TIMEOUT_SECONDS
    return ServerTimeoutConfig(
        step_instruction_seconds=clamp_server_timeout_value(
            "step_instruction_seconds",
            PYOCD_STEP_TIMEOUT_SECONDS * default_ratio,
        ),
        reset_halt_seconds=clamp_server_timeout_value(
            "reset_halt_seconds",
            PYOCD_RESET_HALT_TIMEOUT_SECONDS * connect_ratio,
        ),
        dap_recover_seconds=clamp_server_timeout_value(
            "dap_recover_seconds",
            PYOCD_DAP_RECOVER_TIMEOUT_SECONDS * recover_ratio,
        ),
        core_recover_seconds=clamp_server_timeout_value(
            "core_recover_seconds",
            PYOCD_CORE_RECOVER_TIMEOUT_SECONDS * recover_ratio,
        ),
        flash_init_seconds=clamp_server_timeout_value(
            "flash_init_seconds",
            PYOCD_FLASH_INIT_TIMEOUT_SECONDS * flash_ratio,
        ),
        flash_program_seconds=clamp_server_timeout_value(
            "flash_program_seconds",
            PYOCD_FLASH_PROGRAM_TIMEOUT_SECONDS * flash_ratio,
        ),
        flash_erase_sector_seconds=clamp_server_timeout_value(
            "flash_erase_sector_seconds",
            PYOCD_FLASH_ERASE_SECTOR_TIMEOUT_SECONDS * flash_ratio,
        ),
        flash_erase_all_seconds=clamp_server_timeout_value(
            "flash_erase_all_seconds",
            PYOCD_FLASH_ERASE_ALL_TIMEOUT_SECONDS * flash_ratio,
        ),
        flash_analyzer_seconds=clamp_server_timeout_value(
            "flash_analyzer_seconds",
            PYOCD_FLASH_ANALYZER_TIMEOUT_SECONDS * flash_ratio,
        ),
    )


def derive_server_timeout_update(
    config: TurnkeyTimeoutConfig,
    *,
    changed_turnkey_fields: set[str] | frozenset[str] | tuple[str, ...],
) -> ServerTimeoutUpdate | None:
    changed = set(changed_turnkey_fields)
    if not changed:
        return None
    resolved = server_timeouts_from_turnkey_config(config)
    payload: dict[str, float] = {}
    if "default_tool_seconds" in changed:
        payload["step_instruction_seconds"] = resolved.step_instruction_seconds
    if "connect_seconds" in changed:
        payload["reset_halt_seconds"] = resolved.reset_halt_seconds
    if "recover_seconds" in changed:
        payload["dap_recover_seconds"] = resolved.dap_recover_seconds
        payload["core_recover_seconds"] = resolved.core_recover_seconds
    if "flash_seconds" in changed:
        payload["flash_init_seconds"] = resolved.flash_init_seconds
        payload["flash_program_seconds"] = resolved.flash_program_seconds
        payload["flash_erase_sector_seconds"] = resolved.flash_erase_sector_seconds
        payload["flash_erase_all_seconds"] = resolved.flash_erase_all_seconds
        payload["flash_analyzer_seconds"] = resolved.flash_analyzer_seconds
    if not payload:
        return None
    return ServerTimeoutUpdate(**payload)


def subprocess_timeout_stream_text(value: object) -> str:
    """Normalize subprocess timeout output to text for diagnostics."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
