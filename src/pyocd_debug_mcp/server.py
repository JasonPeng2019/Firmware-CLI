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
import subprocess
import threading
from pathlib import Path
from typing import cast

from mcp.server.fastmcp import FastMCP

from pyocd_debug_mcp.adapters.swd_interface import TargetSessionHandle
from pyocd_debug_mcp.board_config import (
    DEFAULT_BOARD_CONFIG_DIR,
    BoardConfig,
    load_selected_board_configs,
)
from pyocd_debug_mcp.local_env import load_local_env
from pyocd_debug_mcp.probe_inventory import resolve_probe_for_board
from pyocd_debug_mcp.reference_artifacts import resolve_reference_artifacts
from pyocd_debug_mcp.serial_resolver import (
    BoardLike,
    ProbeLike,
    SerialPortInfo,
    list_serial_ports,
    resolve_serial_port,
)
from pyocd_debug_mcp.services import target_control
from pyocd_debug_mcp.services.uart_capture import capture_uart_output

load_local_env()

mcp = FastMCP("pyocd-debug")

# pyOCD is not thread-safe: serialize all probe access.
_lock = threading.Lock()
# The single live session, or None when disconnected.
_session_handle: TargetSessionHandle | None = None
NO_BOARD_CONFIG_MESSAGE = (
    "No board config loaded for this session. Pass `board_id` to `connect` "
    "(or set PYOCD_BOARD_ID) to load boards/<board>.yaml facts."
)


class _ProbeHint:
    def __init__(self, uid: str) -> None:
        self.uid = uid


def _parse_int(text: str) -> int:
    """Parse an int from a string, accepting hex (0x...), binary, or decimal."""
    return int(text, 0)


def _run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        executable = cmd[0] if cmd else "<unknown>"
        return 127, "", f"command not found: {executable}"
    return result.returncode, result.stdout or "", result.stderr or ""


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
    """Compatibility wrapper around the shared target-control option builder."""
    return target_control.build_session_options(board, target)


def _resolve_probe_uid_for_connect(
    board: BoardConfig | None,
    unique_id: str | None,
) -> str | None:
    if unique_id is not None:
        return unique_id
    env_uid = os.environ.get("PYOCD_PROBE_UID") or None
    if env_uid is not None:
        return env_uid
    if board is None:
        return None

    resolution = resolve_probe_for_board(
        board,
        run_cmd=_run_cmd,
        allow_single_fallback=True,
    )
    if resolution.probe is None:
        raise RuntimeError(
            f"Probe resolution failed for {board.display_name}: {resolution.note}"
        )
    if not resolution.probe.uid:
        raise RuntimeError(
            f"Probe resolution for {board.display_name} did not yield a unique id. "
            "Rerun with unique_id=... or set PYOCD_PROBE_UID."
        )
    return resolution.probe.uid


def _handle() -> TargetSessionHandle:
    """Return the live session handle or raise if not connected."""
    if _session_handle is None:
        raise RuntimeError("Not connected to a probe. Call `connect` first.")
    return _session_handle


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
    global _session_handle
    with _lock:
        if _session_handle is not None:
            return "Already connected. Call `disconnect` first to switch probes."

        board = resolve_board_config(board_id, board_config)
        uid = _resolve_probe_uid_for_connect(board, unique_id)
        tgt = (
            target
            or (board.pyocd_target if board else None)
            or os.environ.get("PYOCD_TARGET")
            or None
        )
        handle = target_control.open_session(board=board, unique_id=uid, target=tgt)
        _session_handle = handle
        suffix = f" [board config: {board.board_id}]" if board else ""
        board_name = handle.session.board.name if handle.session.board is not None else "<unknown>"
        return (
            f"Connected to board '{board_name}' via probe "
            f"{handle.probe_uid or '(unknown)'} via {handle.route_used}.{suffix}"
        )


@mcp.tool()
def disconnect() -> str:
    """Close the active debug session and release the probe."""
    global _session_handle
    with _lock:
        if _session_handle is None:
            return "Not connected."
        target_control.close_session(_session_handle)
        _session_handle = None
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
        handle = _session_handle
        if handle is None:
            return "Not connected. Call `connect` first."
        b = handle.board
        if b is None:
            return NO_BOARD_CONFIG_MESSAGE
        return format_board_info(b)


def _require_loaded_board(handle: TargetSessionHandle) -> BoardConfig:
    if handle.board is None:
        raise RuntimeError(NO_BOARD_CONFIG_MESSAGE)
    return handle.board


def _resolve_serial_port_for_session(
    handle: TargetSessionHandle,
    *,
    override: str | None,
) -> SerialPortInfo:
    board = _require_loaded_board(handle)
    ports = list_serial_ports()
    if ports is None:
        raise RuntimeError("pyserial is not installed")
    if not ports:
        raise RuntimeError("No serial ports detected")

    probe = _ProbeHint(handle.probe_uid) if handle.probe_uid else None
    resolution = resolve_serial_port(
        board=cast(BoardLike, board),
        ports=ports,
        probe=cast(ProbeLike | None, probe),
        override=override,
        allow_single_fallback=len(ports) == 1,
        run_cmd=_run_cmd,
        interactive=False,
    )
    if resolution.port is None:
        raise RuntimeError(f"Serial port resolution failed: {resolution.note}")
    return resolution.port


@mcp.tool()
def get_state() -> str:
    """Return the current core run state (e.g. HALTED, RUNNING, RESET)."""
    with _lock:
        return target_control.get_state(_handle())


@mcp.tool()
def halt() -> str:
    """Halt the core."""
    with _lock:
        target_control.halt(_handle())
        return "Halted."


@mcp.tool()
def resume() -> str:
    """Resume execution of the core."""
    with _lock:
        target_control.resume(_handle())
        return "Resumed."


@mcp.tool()
def step() -> str:
    """Single-step one instruction and return the new program counter."""
    with _lock:
        pc = target_control.step(_handle())
        return f"Stepped. pc=0x{pc:08X}"


@mcp.tool()
def reset(halt_after: bool = True) -> str:
    """Reset the target.

    Args:
        halt_after: If True, halt at the reset vector (reset-and-halt).
            If False, reset and let the target run.
    """
    with _lock:
        target_control.reset(_handle(), halt_after=halt_after)
        if halt_after:
            return "Reset and halted."
        return "Reset and running."


@mcp.tool()
def read_core_register(name: str) -> str:
    """Read a core register by name (e.g. "pc", "sp", "r0", "xpsr").

    Returns the value as a hex string.
    """
    with _lock:
        return f"0x{target_control.read_core_register(_handle(), name):08X}"


@mcp.tool()
def write_core_register(name: str, value: str) -> str:
    """Write a core register by name. ``value`` may be hex (0x...) or decimal."""
    with _lock:
        target_control.write_core_register(_handle(), name, _parse_int(value))
        return f"Wrote {value} to {name}."


@mcp.tool()
def read_memory(address: str, word_size: int = 32) -> str:
    """Read a single value from memory.

    Args:
        address: Memory address, hex (0x...) or decimal.
        word_size: Transfer size in bits: 8, 16, or 32.
    """
    with _lock:
        value = target_control.read_memory(_handle(), _parse_int(address), word_size)
        width = word_size // 4
        return f"0x{value:0{width}X}"


@mcp.tool()
def read_memory_block(address: str, length: int) -> str:
    """Read ``length`` bytes from memory starting at ``address``.

    Returns the bytes as a space-separated hex string.
    """
    with _lock:
        data = target_control.read_memory_block(_handle(), _parse_int(address), length)
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
        target_control.write_memory(_handle(), _parse_int(address), _parse_int(value), word_size)
        return f"Wrote {value} to {address}."


@mcp.tool()
def set_breakpoint(address: str) -> str:
    """Set a hardware/software breakpoint at ``address``."""
    with _lock:
        target_control.set_breakpoint(_handle(), _parse_int(address))
        return f"Breakpoint set at {address}."


@mcp.tool()
def remove_breakpoint(address: str) -> str:
    """Remove the breakpoint at ``address``."""
    with _lock:
        target_control.remove_breakpoint(_handle(), _parse_int(address))
        return f"Breakpoint removed at {address}."


@mcp.tool()
def flash_firmware(path: str | None = None, halt_after_reset: bool = False) -> str:
    """Flash firmware through the shared target-control service layer.

    Args:
        path: Optional explicit artifact path. When omitted, resolve the default
            flash artifact for the connected session's loaded board config.
            Returns the resolved path in the success text.
        halt_after_reset: If True, leave the target halted after flashing.
            If False, reset and let it run.
    """
    with _lock:
        handle = _handle()
        if path is None:
            if handle.board is None:
                return NO_BOARD_CONFIG_MESSAGE
            artifact = resolve_reference_artifacts(handle.board).flash_artifact
        else:
            artifact = Path(path).expanduser().resolve()

        flashed = target_control.flash_firmware(
            handle,
            artifact,
            halt_after_reset=halt_after_reset,
        )
        state = "halted" if halt_after_reset else "running"
        return f"Flashed {flashed} via {handle.route_used}; target left {state}."


@mcp.tool()
def read_serial(
    expected_text: str | None = None,
    read_seconds: float = 3.0,
    baudrate: int | None = None,
    port: str | None = None,
    reset_on_open: bool = False,
) -> str:
    """Capture bounded UART output through the shared serial-resolution and UART services.

    Defaults come from the connected board config when available:
    expected UART text, baudrate, and serial-port selection heuristics.
    Set ``port`` to override serial resolution explicitly. Set ``reset_on_open``
    to trigger a target reset immediately after the UART port opens so boot text
    is captured deterministically.
    """
    with _lock:
        handle = _handle()
        if handle.board is None:
            return NO_BOARD_CONFIG_MESSAGE

        board = handle.board
        resolved_port = _resolve_serial_port_for_session(handle, override=port)
        resolved_baudrate = baudrate or board.default_baudrate
        resolved_expected_text = expected_text if expected_text is not None else board.expected_uart_substring

        on_port_open = None
        if reset_on_open:

            def on_port_open() -> None:
                target_control.reset(handle, halt_after=False)

        capture = capture_uart_output(
            resolved_port.device,
            resolved_baudrate,
            read_seconds,
            resolved_expected_text,
            on_port_open=on_port_open,
        )
        expectation_label = (
            f"expected='{resolved_expected_text}'"
            if resolved_expected_text is not None
            else "expected=(any output)"
        )
        verdict = "matched" if capture.matched else "did not match"
        excerpt = capture.excerpt or "(none)"
        return (
            f"UART {verdict} on {resolved_port.device} at {resolved_baudrate} baud via {handle.route_used}; "
            f"{expectation_label}; reopen_count={capture.reopen_count}; "
            f"duration={capture.duration_seconds:.2f}s; excerpt={excerpt}"
        )


@mcp.tool()
def unlock_recover(confirm: bool = False) -> str:
    """Run the shared recover/unlock path for the connected board.

    This is a destructive action. When ``confirm`` is false the tool refuses
    without touching hardware. Boards whose tracked config has no supported
    ``recover_mode`` fail deterministically instead of pretending success.
    """
    with _lock:
        handle = _handle()
        if handle.board is None:
            return NO_BOARD_CONFIG_MESSAGE
        if not confirm:
            return "Refusing to run recover without confirm=True. This operation may erase flash."

        backend = target_control.recover_target(handle)
        return f"Recover completed via {backend} on {handle.board.board_id} via {handle.route_used}."


def main() -> None:
    """Console entry point. Runs the server over stdio transport by default."""
    mcp.run()


if __name__ == "__main__":
    main()
