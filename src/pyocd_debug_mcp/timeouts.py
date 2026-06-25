"""Shared timeout budgets for host, server, and turnkey runtime paths."""

from __future__ import annotations

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


def subprocess_timeout_stream_text(value: object) -> str:
    """Normalize subprocess timeout output to text for diagnostics."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
