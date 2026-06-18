#!/usr/bin/env python3
"""Canonical Stage 1 smoke harness for the shared SWD + UART substrate."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
for entry in (REPO_ROOT, SRC_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from pyocd_debug_mcp.board_config import (  # noqa: E402
    DEFAULT_BOARD_CONFIG_DIR,
    BoardConfig,
    load_selected_board_configs,
)
from pyocd_debug_mcp.local_env import load_local_env  # noqa: E402
from pyocd_debug_mcp.reference_artifacts import resolve_reference_artifacts  # noqa: E402
from pyocd_debug_mcp.serial_resolver import (  # noqa: E402
    SerialPortInfo,
    is_interactive_terminal,
    list_serial_ports,
    resolve_serial_port,
)
from pyocd_debug_mcp.services import target_control  # noqa: E402
from pyocd_debug_mcp.services.symbols import read_symbol_u32  # noqa: E402
from pyocd_debug_mcp.services.uart_capture import capture_uart_output  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"
KNOWN_SYMBOL_NAME = "stage1_known_value"
KNOWN_SYMBOL_VALUE = 0x1234ABCD


@dataclass(frozen=True)
class ProbeHint:
    uid: str


def log(status: str, message: str) -> None:
    print(f"  [{status}] {message}")


def header(text: str) -> None:
    print(f"\n{'=' * 60}\n  {text}\n{'=' * 60}")


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        executable = cmd[0] if cmd else "<unknown>"
        return 127, "", f"command not found: {executable}"
    return result.returncode, result.stdout or "", result.stderr or ""


def load_board(board_id: str) -> BoardConfig:
    boards = load_selected_board_configs(DEFAULT_BOARD_CONFIG_DIR, requested_ids=[board_id])
    if not boards:
        raise RuntimeError(f"Board not found: {board_id}")
    return boards[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board-id", required=True, help="Tracked board id to validate.")
    parser.add_argument("--probe-uid", help="Probe unique id override.")
    parser.add_argument("--port", help="Serial port override for the board.")
    parser.add_argument("--flash-artifact", help="Override the flash artifact path.")
    parser.add_argument("--elf", help="Override the symbol-bearing ELF path.")
    parser.add_argument("--baudrate", type=int, help="UART baudrate override.")
    parser.add_argument(
        "--serial-read-seconds",
        type=float,
        default=3.0,
        help="How long to wait for UART output after reset.",
    )
    return parser


def resolve_port(
    board: BoardConfig,
    *,
    probe_uid: str | None,
    override: str | None,
) -> SerialPortInfo:
    ports = list_serial_ports()
    if ports is None:
        raise RuntimeError("pyserial is not installed")
    if not ports:
        raise RuntimeError("No serial ports detected")

    allow_single_fallback = len(ports) == 1
    probe = ProbeHint(probe_uid) if probe_uid else None
    resolution = resolve_serial_port(
        board=board,
        ports=ports,
        probe=probe,
        override=override,
        allow_single_fallback=allow_single_fallback,
        run_cmd=run_cmd,
        interactive=is_interactive_terminal(),
    )
    if resolution.port is None:
        raise RuntimeError(f"Serial port resolution failed: {resolution.note}")
    return resolution.port


def main() -> int:
    load_local_env()
    parser = build_parser()
    args = parser.parse_args()

    board = load_board(args.board_id.strip().lower())
    probe_uid = args.probe_uid or os.environ.get("PYOCD_PROBE_UID") or None
    baudrate = args.baudrate or board.default_baudrate
    artifact_pair = resolve_reference_artifacts(
        board,
        flash_artifact=args.flash_artifact,
        elf_path=args.elf,
    )
    serial_port = resolve_port(board, probe_uid=probe_uid, override=args.port)
    expected_text = board.expected_uart_substring or "boot ok"

    print(f"\nStage 1 smoke harness — {board.display_name} ({board.board_id})")
    print(f"flash artifact: {artifact_pair.flash_artifact}")
    print(f"symbol artifact: {artifact_pair.symbol_artifact}")
    print(f"serial port: {serial_port.device}")

    header("Flash and control")
    handle = None
    try:
        handle = target_control.open_session(
            board=board,
            unique_id=probe_uid,
            target=board.pyocd_target,
        )
        log(INFO, f"Opened session via {handle.route_used} on {handle.probe_uid or '(unknown probe)'}")
        target_control.flash_firmware(handle, artifact_pair.flash_artifact, halt_after_reset=True)
        log(PASS, f"Flashed {artifact_pair.flash_artifact.name}")

        pc = target_control.read_core_register(handle, "pc")
        log(PASS, f"Read pc=0x{pc:08X}")

        resolved = read_symbol_u32(handle, artifact_pair.symbol_artifact, KNOWN_SYMBOL_NAME)
        log(
            PASS,
            f"Resolved {resolved.name} @0x{resolved.address:08X} size={resolved.size} type={resolved.type}",
        )
        if resolved.value_u32 != KNOWN_SYMBOL_VALUE:
            raise RuntimeError(
                f"{resolved.name} value mismatch: actual=0x{resolved.value_u32:08X} "
                f"expected=0x{KNOWN_SYMBOL_VALUE:08X}"
            )
        log(PASS, f"Read {resolved.name}=0x{resolved.value_u32:08X}")

        header("UART")
        def on_port_open() -> None:
            target_control.reset(handle, halt_after=False)

        capture = capture_uart_output(
            serial_port.device,
            baudrate,
            args.serial_read_seconds,
            expected_text,
            on_port_open=on_port_open,
        )
        log(PASS, "Reset and resumed target")
        if not capture.matched:
            raise RuntimeError(
                f"UART output did not contain '{expected_text}'. Captured: {capture.excerpt or '(none)'}"
            )
        log(PASS, f"UART matched '{expected_text}'")
        if capture.excerpt:
            print(f"      Captured: {capture.excerpt}")
    except Exception as exc:  # noqa: BLE001 - surface the concrete harness failure
        header("Summary")
        log(FAIL, f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if handle is not None:
            try:
                target_control.close_session(handle)
            except Exception:  # noqa: BLE001 - do not hide the real harness result
                pass

    header("Summary")
    log(PASS, "Stage 1 smoke harness passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
