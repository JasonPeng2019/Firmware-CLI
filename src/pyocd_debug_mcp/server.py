"""Minimal MCP server exposing pyOCD debug control to an LLM client.

Design notes
------------
* A debug session is *stateful* (halt state, breakpoints, and the live target
  connection all persist across calls), so we hold a single pyOCD ``Session``
  open for the lifetime of the server rather than opening one per tool call.
  Connecting is therefore an explicit ``connect`` tool, mirroring how an
  operator selects a specific probe and target.
* pyOCD's target access is blocking and **not thread-safe**. FastMCP may invoke
  tools concurrently, so every probe access is serialized behind a single lock.
* pyOCD calls block; for fast operations (register/memory reads) that is fine.
  Long operations such as flashing should be offloaded (e.g. ``anyio.to_thread``)
  so they don't stall the event loop — left out here to keep the starter small.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from pyocd.core.helpers import ConnectHelper
from pyocd.core.session import Session
from pyocd.core.target import Target

from pyocd_debug_mcp.board_config import (
    DEFAULT_BOARD_CONFIG_DIR,
    BoardConfig,
    load_selected_board_configs,
)
from pyocd_debug_mcp.local_env import load_local_env

load_local_env()

mcp = FastMCP("pyocd-debug")

# pyOCD is not thread-safe: serialize all probe access.
_lock = threading.Lock()
# The single live session, or None when disconnected.
_session: Session | None = None
# The board definition the active session was opened with, or None in raw-target
# mode (connect called without a board_id). Lets tools read board-config facts.
_active_board: BoardConfig | None = None


def _parse_int(text: str) -> int:
    """Parse an int from a string, accepting hex (0x...), binary, or decimal."""
    return int(text, 0)


def resolve_board_config(board_id: str | None, board_config: str | None) -> BoardConfig | None:
    """Load one board definition through the shared loader, or None if unselected.

    This is the server's single path to ``boards/<board>.yaml`` — the same loader
    the Stage 0 CLI uses — so a custom ST/nRF board's facts (pyOCD target, recover
    policy, silicon id, baud) reach the MCP tools, not just the CLI.

    ``board_id``/``board_config`` fall back to the ``PYOCD_BOARD_ID`` /
    ``PYOCD_BOARD_CONFIG`` environment variables (the stdio-launch config
    channel). Returns ``None`` when no board is named, so ``connect`` still works
    with a raw target. Raises ``ConfigError`` if a named board cannot be found or
    a config file is malformed.
    """
    bid = (board_id or os.environ.get("PYOCD_BOARD_ID") or "").strip()
    if not bid:
        return None
    extra = board_config or os.environ.get("PYOCD_BOARD_CONFIG") or None
    extra_paths = [Path(extra)] if extra else []
    boards = load_selected_board_configs(
        DEFAULT_BOARD_CONFIG_DIR,
        extra_paths=extra_paths,
        requested_ids=[bid],
    )
    return boards[0]


def format_board_info(b: BoardConfig) -> str:
    """Render a loaded board definition's facts as a stable text block."""
    lines = [
        f"board_id: {b.board_id}",
        f"display_name: {b.display_name}",
        f"mcu_family: {b.mcu_family}",
        f"probe_family: {b.probe_family}",
        f"pyocd_target: {b.pyocd_target}",
        f"default_baudrate: {b.default_baudrate}",
        f"test_read_address: 0x{b.test_addr:08X}",
        f"requires_recover_validation: {b.requires_recover_validation}",
        f"recover_mode: {b.recover_mode or '(none)'}",
    ]
    if b.silicon_id_addr is not None and b.silicon_id_expected is not None:
        width_nibbles = b.silicon_id_width_bits // 4
        lines.append(
            f"silicon_id: addr=0x{b.silicon_id_addr:08X} "
            f"expected=0x{b.silicon_id_expected:0{width_nibbles}X} "
            f"({b.silicon_id_label or 'silicon identity'})"
        )
    if b.uart_note:
        lines.append(f"uart_note: {b.uart_note}")
    return "\n".join(lines)


def build_session_options(board: BoardConfig | None, target: str | None) -> dict[str, object] | None:
    """Build pyOCD session options from shared board facts.

    Keep probe-family-specific pyOCD quirks in one place so different wrappers
    can converge on the same connection behavior later.
    """
    options: dict[str, object] = {}
    if target:
        options["target_override"] = target
    if board and board.probe_family == "jlink":
        # Match the Stage 0 CLI's verified workaround for J-Link open-by-serial.
        options["jlink.non_interactive"] = False
    return options or None


def _target() -> Target:
    """Return the live target or raise if not connected."""
    if _session is None:
        raise RuntimeError("Not connected to a probe. Call `connect` first.")
    return _session.target


@mcp.tool()
def connect(
    unique_id: str | None = None,
    target: str | None = None,
    board_id: str | None = None,
    board_config: str | None = None,
) -> str:
    """Open a debug session to a connected probe.

    Args:
        unique_id: Whole or partial probe serial/unique ID to select a specific
            probe. Omit when exactly one probe is attached. Defaults to the
            ``PYOCD_PROBE_UID`` environment variable if unset.
        target: Target type override, e.g. "stm32f407vg" or "nrf52833". Takes
            precedence over a board config. Omit to use the selected board's
            target (when ``board_id`` is given), else the ``PYOCD_TARGET``
            environment variable, else pyOCD auto-detection.
        board_id: Load facts from ``boards/<board_id>.yaml`` through the shared
            board-config loader — pyOCD target, recover policy, silicon id, baud.
            Lets a custom ST/nRF board connect by id with no hand-passed target;
            call ``get_board_info`` to see the loaded facts. Defaults to the
            ``PYOCD_BOARD_ID`` environment variable.
        board_config: Path to an extra board-config file outside the tracked
            ``boards/`` directory, for a custom board. Defaults to the
            ``PYOCD_BOARD_CONFIG`` environment variable.
    """
    global _session, _active_board
    with _lock:
        if _session is not None:
            return "Already connected. Call `disconnect` first to switch probes."

        board = resolve_board_config(board_id, board_config)
        uid = unique_id or os.environ.get("PYOCD_PROBE_UID") or None
        tgt = (
            target
            or (board.pyocd_target if board else None)
            or os.environ.get("PYOCD_TARGET")
            or None
        )
        options = build_session_options(board, tgt)

        # auto_open=False so we control the open() explicitly for a long-lived
        # session; blocking=False + return_first=True keep it headless.
        session = ConnectHelper.session_with_chosen_probe(
            blocking=False,
            return_first=True,
            unique_id=uid,
            auto_open=False,
            options=options,
        )
        if session is None:
            raise RuntimeError("No matching debug probe found.")

        session.open()
        _session = session
        _active_board = board
        suffix = f" [board config: {board.board_id}]" if board else ""
        return (
            f"Connected to board '{session.board.name}' via probe "
            f"{session.probe.unique_id}.{suffix}"
        )


@mcp.tool()
def disconnect() -> str:
    """Close the active debug session and release the probe."""
    global _session, _active_board
    with _lock:
        if _session is None:
            return "Not connected."
        _session.close()
        _session = None
        _active_board = None
        return "Disconnected."


@mcp.tool()
def get_board_info() -> str:
    """Return the facts from the board config the session was opened with.

    Reports the ``boards/<board>.yaml`` definition active for this session —
    pyOCD target, MCU and probe family, recover policy, silicon-id expectation,
    default UART baud, and the smoke-test read address. Returns a notice when
    ``connect`` was called without a ``board_id`` (raw-target mode), where these
    facts were not loaded.
    """
    with _lock:
        b = _active_board
        if b is None:
            return (
                "No board config loaded for this session. Pass `board_id` to "
                "`connect` (or set PYOCD_BOARD_ID) to load boards/<board>.yaml facts."
            )
        return format_board_info(b)


@mcp.tool()
def get_state() -> str:
    """Return the current core run state (e.g. HALTED, RUNNING, RESET)."""
    with _lock:
        return _target().get_state().name


@mcp.tool()
def halt() -> str:
    """Halt the core."""
    with _lock:
        _target().halt()
        return "Halted."


@mcp.tool()
def resume() -> str:
    """Resume execution of the core."""
    with _lock:
        _target().resume()
        return "Resumed."


@mcp.tool()
def step() -> str:
    """Single-step one instruction and return the new program counter."""
    with _lock:
        t = _target()
        t.step()
        return f"Stepped. pc=0x{t.read_core_register('pc'):08X}"


@mcp.tool()
def reset(halt_after: bool = True) -> str:
    """Reset the target.

    Args:
        halt_after: If True, halt at the reset vector (reset-and-halt).
            If False, reset and let the target run.
    """
    with _lock:
        t = _target()
        if halt_after:
            t.reset_and_halt()
            return "Reset and halted."
        t.reset()
        return "Reset and running."


@mcp.tool()
def read_core_register(name: str) -> str:
    """Read a core register by name (e.g. "pc", "sp", "r0", "xpsr").

    Returns the value as a hex string.
    """
    with _lock:
        return f"0x{_target().read_core_register(name):08X}"


@mcp.tool()
def write_core_register(name: str, value: str) -> str:
    """Write a core register by name. ``value`` may be hex (0x...) or decimal."""
    with _lock:
        _target().write_core_register(name, _parse_int(value))
        return f"Wrote {value} to {name}."


@mcp.tool()
def read_memory(address: str, word_size: int = 32) -> str:
    """Read a single value from memory.

    Args:
        address: Memory address, hex (0x...) or decimal.
        word_size: Transfer size in bits: 8, 16, or 32.
    """
    with _lock:
        value = _target().read_memory(_parse_int(address), word_size)
        width = word_size // 4
        return f"0x{value:0{width}X}"


@mcp.tool()
def read_memory_block(address: str, length: int) -> str:
    """Read ``length`` bytes from memory starting at ``address``.

    Returns the bytes as a space-separated hex string.
    """
    with _lock:
        data = _target().read_memory_block8(_parse_int(address), length)
        return " ".join(f"{b:02X}" for b in data)


@mcp.tool()
def write_memory(address: str, value: str, word_size: int = 32) -> str:
    """Write a single value to memory.

    Args:
        address: Memory address, hex (0x...) or decimal.
        value: Value to write, hex (0x...) or decimal.
        word_size: Transfer size in bits: 8, 16, or 32.
    """
    with _lock:
        _target().write_memory(_parse_int(address), _parse_int(value), word_size)
        return f"Wrote {value} to {address}."


@mcp.tool()
def set_breakpoint(address: str) -> str:
    """Set a hardware/software breakpoint at ``address``."""
    with _lock:
        _target().set_breakpoint(_parse_int(address))
        return f"Breakpoint set at {address}."


@mcp.tool()
def remove_breakpoint(address: str) -> str:
    """Remove the breakpoint at ``address``."""
    with _lock:
        _target().remove_breakpoint(_parse_int(address))
        return f"Breakpoint removed at {address}."


def main() -> None:
    """Console entry point. Runs the server over stdio transport by default."""
    mcp.run()


if __name__ == "__main__":
    main()
