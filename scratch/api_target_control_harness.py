#!/usr/bin/env python3
"""Step 1.0d throwaway harness — prove the pyOCD PYTHON-API target-control path.

Why this exists
---------------
`server.py` already proves connect / read / core-control through the pyOCD Python
API on real hardware. It does NOT yet prove the three target-control operations
that `stage0_check.py` only exercises via *subprocess* (`pyocd cmd`, `pyocd load`,
`pyocd erase --mass`):

    * silicon-ID read (read a known FICR/DBGMCU address and compare to board data)
    * flash a known-good artifact
    * recover / unlock (nRF APPROTECT mass-erase)

This harness exercises exactly those three, through the pyOCD **Python API**, so
the API path is proven to do what the subprocess path already does — the Step 1.0d
de-risk. It deliberately does NOT reproduce Stage 0's enumeration / pack-install /
serial-discovery / UART / CLI-reporting behavior. Those are out of scope.

It is THROWAWAY. It lives under scratch/ and is not shipped. Once these operations
are proven on the bench, write them into src/pyocd_debug_mcp/services/ and delete
this file.

Oracle
------
Every result here should match what `stage0_check.py` reports for the same board.
Run stage0 first (subprocess truth), then this harness (API truth), and compare:

    uv run python stage0_check.py --board-id nucleo_l476rg
    uv run python scratch/api_target_control_harness.py --board-id nucleo_l476rg --silicon-id

Safety
------
* Default action is READ-ONLY (connect + silicon-ID).
* --flash requires an explicit --firmware PATH.
* --recover is DESTRUCTIVE (mass-erase) and requires --confirm-recover.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Reuse the proven shared loaders rather than reinventing board parsing.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))

from pyocd_debug_mcp.board_config import (  # noqa: E402
    DEFAULT_BOARD_CONFIG_DIR,
    RECOVER_MODE_NRF_PYOCD_UNLOCK,
    BoardConfig,
    ConfigError,
    load_selected_board_configs,
)
from pyocd_debug_mcp.local_env import load_local_env  # noqa: E402

load_local_env()

PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"
WARN = "WARN"


def log(status: str, message: str) -> None:
    print(f"  [{status}] {message}")


def header(text: str) -> None:
    print(f"\n{'=' * 60}\n  {text}\n{'=' * 60}")


def open_session(board: BoardConfig, unique_id: str | None):
    """Open a pyOCD session the same way server.py does (the proven path).

    Carries over the J-Link open workaround stage0_check.py already relies on:
    pyOCD calls pylink's disable_dialog_boxes() when jlink.non_interactive is True
    (its default), which clears the USB emulator selection and makes open-by-serial
    fail with "No emulator with serial number ... found". Turning it off skips that.
    """
    from pyocd.core.helpers import ConnectHelper

    uid = unique_id or os.environ.get("PYOCD_PROBE_UID") or None
    options: dict[str, object] = {"target_override": board.pyocd_target}
    if board.probe_family == "jlink":
        options["jlink.non_interactive"] = False

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
    return session


def check_silicon_id(session, board: BoardConfig) -> bool:
    """Read the board's silicon-ID address via the API and compare to board data.

    Oracle: `stage0_check.py`'s `check_silicon_identity` does the same read via
    `pyocd cmd -c readNN`. The masked value here must match that.
    """
    header(f"Silicon-ID read (API) — {board.display_name}")
    if board.silicon_id_addr is None or board.silicon_id_expected is None:
        log(INFO, "Board config defines no silicon identity — skipping (not a failure).")
        return True

    width = board.silicon_id_width_bits
    raw = read_word(session, board.silicon_id_addr, width)
    mask = board.silicon_id_mask if board.silicon_id_mask is not None else (1 << width) - 1
    actual = raw & mask
    expected = board.silicon_id_expected & mask
    ok = actual == expected
    label = board.silicon_id_label or "silicon identity"
    log(
        PASS if ok else FAIL,
        f"{label}: actual=0x{actual:X} expected=0x{expected:X} mask=0x{mask:X} "
        f"(read @0x{board.silicon_id_addr:08X}, {width}-bit)",
    )
    return ok


def read_word(session, address: int, width_bits: int) -> int:
    return session.target.read_memory(address, width_bits)


def do_flash(session, firmware: Path) -> bool:
    """Flash an artifact through pyOCD's Python API (FileProgrammer).

    Oracle: `stage0_check.py` flashes via the `pyocd load <path>` subprocess. This
    is the API equivalent and the specific thing Step 1.0d must prove on hardware.
    FileProgrammer infers format from the extension (.hex/.elf); a raw .bin would
    need a base address, which is intentionally not supported here.
    """
    header(f"Flash (API) — {firmware.name}")
    if not firmware.exists():
        log(FAIL, f"Firmware artifact does not exist: {firmware}")
        return False
    if firmware.suffix.lower() not in {".hex", ".elf"}:
        log(FAIL, f"Unsupported artifact type '{firmware.suffix}' — use .hex or .elf.")
        return False

    from pyocd.flash.file_programmer import FileProgrammer

    log(INFO, f"Programming {firmware} ...")
    FileProgrammer(session).program(str(firmware))
    session.target.reset_and_halt()
    log(PASS, f"Flashed and reset-halted: {firmware}")
    return True


def do_recover(session, board: BoardConfig) -> bool:
    """Destructive recover/unlock via the API (mass erase).

    Oracle: `stage0_check.py`'s recover flow runs `pyocd cmd -c unlock` then
    `pyocd erase --mass`. The API equivalent of the mass-erase fallback is the
    FlashEraser in MASS mode. NOTE (build-plan flag): the exact programmatic
    unlock/mass-erase entry point is pyOCD-version-specific — confirm against the
    installed pyOCD and reconfirm on upgrades.
    """
    header(f"Recover / unlock (API, DESTRUCTIVE) — {board.display_name}")
    if board.recover_mode != RECOVER_MODE_NRF_PYOCD_UNLOCK:
        log(
            INFO,
            f"recover_mode={board.recover_mode!r} — no built-in API recover for this "
            "board family; skipping (not a failure).",
        )
        return True

    from pyocd.flash.eraser import FlashEraser

    log(WARN, "Performing MASS ERASE — this irreversibly wipes the chip.")
    FlashEraser(session, FlashEraser.Mode.MASS).erase()
    log(PASS, "Mass erase completed.")

    # Prove the chip is reachable again after the destructive cycle.
    if board.silicon_id_addr is not None:
        try:
            raw = read_word(session, board.silicon_id_addr, board.silicon_id_width_bits)
            log(PASS, f"Re-read after erase OK: 0x{raw:X} @0x{board.silicon_id_addr:08X}")
        except Exception as exc:  # noqa: BLE001 — harness wants the raw failure
            log(FAIL, f"Could not re-read target after erase: {exc}")
            return False
    return True


def load_board(args: argparse.Namespace) -> BoardConfig:
    extra = [Path(args.board_config).expanduser().resolve()] if args.board_config else []
    boards = load_selected_board_configs(
        Path(args.board_config_dir).expanduser().resolve(),
        extra_paths=extra,
        requested_ids=[args.board_id],
    )
    if not boards:
        raise ConfigError(f"Board not found: {args.board_id}")
    return boards[0]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--board-id", required=True, help="Board id from boards/<board>.yaml")
    p.add_argument(
        "--board-config-dir",
        default=str(DEFAULT_BOARD_CONFIG_DIR),
        help="Directory of board configs (defaults to repo boards/).",
    )
    p.add_argument("--board-config", help="Extra board-config file outside boards/.")
    p.add_argument("--probe-uid", help="Probe serial/unique id (else PYOCD_PROBE_UID).")
    p.add_argument("--silicon-id", action="store_true", help="Run the silicon-ID read check.")
    p.add_argument("--flash", action="store_true", help="Flash --firmware via the API.")
    p.add_argument("--firmware", help="Path to the .hex/.elf artifact to flash.")
    p.add_argument("--recover", action="store_true", help="Run the destructive recover/unlock.")
    p.add_argument(
        "--confirm-recover",
        action="store_true",
        help="Required acknowledgement that --recover mass-erases the chip.",
    )
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Default to the read-only check when no step is selected.
    if not (args.silicon_id or args.flash or args.recover):
        args.silicon_id = True

    if args.flash and not args.firmware:
        parser.error("--flash requires --firmware PATH")
    if args.recover and not args.confirm_recover:
        parser.error("--recover is destructive (mass erase) — pass --confirm-recover to proceed")

    try:
        board = load_board(args)
    except ConfigError as exc:
        parser.error(str(exc))
        return 2

    print(f"\nStep 1.0d API harness — board: {board.display_name} ({board.board_id})")
    print(f"pyocd_target={board.pyocd_target} probe_family={board.probe_family}")

    session = None
    results: list[tuple[str, bool]] = []
    try:
        session = open_session(board, args.probe_uid)
        log(PASS, f"Opened session via probe {session.probe.unique_id}")

        if args.silicon_id:
            results.append(("silicon-id", check_silicon_id(session, board)))
        if args.flash:
            results.append(("flash", do_flash(session, Path(args.firmware).expanduser().resolve())))
        if args.recover:
            results.append(("recover", do_recover(session, board)))
    except Exception as exc:  # noqa: BLE001 — harness wants the raw failure surfaced
        header("FAILURE")
        log(FAIL, f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if session is not None:
            session.close()

    header("Summary (oracle against stage0_check.py)")
    all_ok = True
    for name, ok in results:
        log(PASS if ok else FAIL, name)
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
