#!/usr/bin/env python3
"""
Stage 0 board and toolchain validation.

Automates the Stage 0 checks that are safe and observable from the host:
- pyOCD installed
- board probe visible
- target pack available
- SWD connect + register read
- virtual COM port visible
- optional reference firmware flash
- optional UART smoke test

Board definitions are data-driven. Board facts come from board config files,
not hardcoded board entries in this script.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))

from pyocd_debug_mcp.board_config import (
    DEFAULT_BOARD_CONFIG_DIR,
    PROBE_FAMILY_HINTS,
    BoardConfig,
    ConfigError,
    load_selected_board_configs,
    parse_int,
    validate_width_bits,
)
from pyocd_debug_mcp.local_env import load_local_env
from pyocd_debug_mcp.serial_resolver import (
    SerialPortInfo,
    command_exists,
    is_interactive_terminal,
    resolve_serial_port,
)

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
INFO = "INFO"

SUMMARY_PASS = "pass"
SUMMARY_FAIL = "fail"
SUMMARY_MANUAL = "manual"

load_local_env()


@dataclass(frozen=True)
class ProbeInfo:
    uid: str
    description: str
    raw: str
    state: str = ""

    @property
    def searchable_text(self) -> str:
        return f"{self.uid} {self.description} {self.raw}".lower()


@dataclass(frozen=True)
class SummaryItem:
    label: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class ReadResult:
    rc: int
    stdout: str
    stderr: str
    value: int | None = None

    @property
    def combined(self) -> str:
        return f"{self.stdout}\n{self.stderr}".lower()


def run(cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True)
    except FileNotFoundError:
        executable = cmd[0] if cmd else "<unknown>"
        return 127, "", f"command not found: {executable}"
    return result.returncode, result.stdout or "", result.stderr or ""


def header(text: str):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print("=" * 60)


def log(status: str, message: str):
    print(f"  [{status}] {message}")


def check(ok: bool, message: str) -> bool:
    log(PASS if ok else FAIL, message)
    return ok


def score_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def board_cli_label(board: BoardConfig) -> str:
    return board.board_id


def pyocd_base(subcommand: str, board: BoardConfig, probe: ProbeInfo | None) -> list[str]:
    cmd = ["pyocd", subcommand, "-t", board.pyocd_target]
    if probe and probe.uid:
        cmd.extend(["-u", probe.uid])
    if board.probe_family == "jlink":
        # VENDOR-FIXED, UNVERIFIED ACROSS VERSIONS (pyOCD session option; behaviour depends on
        # the pyOCD + pylink + J-Link DLL combo). pyOCD calls pylink's disable_dialog_boxes()
        # when jlink.non_interactive is True (its default). Verified here on pyOCD 0.44.1 +
        # pylink 1.7.0 + J-Link DLL V9.50: that call clears the USB emulator selection, so the
        # subsequent open-by-serial fails with "No emulator with serial number <sn> found" even
        # though the probe is present and enumerable. Turning the option off skips the call and
        # lets the open succeed. Tradeoff: a J-Link dialog (e.g. a firmware-update prompt) could
        # appear during an automated run. NOTE: the plan standardizes the shipped product on
        # CMSIS-DAP, not this SEGGER-DLL path (see surfaced conflict).
        cmd.extend(["-O", "jlink.non_interactive=false"])
    return cmd


def load_pyserial():
    try:
        import serial as serial_mod
        from serial.tools import list_ports
    except ImportError:
        return None, None
    return serial_mod, list_ports


def parse_key_value(items: list[str], option_name: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ConfigError(f"{option_name} requires BOARD_ID=VALUE, got '{item}'")
        key, value = item.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key or not value:
            raise ConfigError(f"{option_name} requires BOARD_ID=VALUE, got '{item}'")
        parsed[key] = value
    return parsed


def resolve_firmware_path(path_value: str | None, base_dir: Path | None = None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser()
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path.resolve()


def check_pyocd_installed() -> bool:
    header("pyOCD installation")
    rc, out, _ = run(["pyocd", "--version"])
    ok = rc == 0
    if ok:
        check(True, f"pyOCD found: {out.strip()}")
    else:
        check(False, "pyOCD not found - run: uv sync")
    return ok


def check_pyserial_installed() -> bool:
    header("pyserial installation")
    serial_mod, _ = load_pyserial()
    ok = serial_mod is not None
    if ok:
        version = getattr(serial_mod, "__version__", "unknown version")
        check(True, f"pyserial found: {version}")
    else:
        check(False, "pyserial not found - run: uv sync")
    return ok


def list_probes() -> list[ProbeInfo]:
    rc, out, _ = run(["pyocd", "list", "--output", "json"])
    if rc != 0 or not out.strip():
        _, out, _ = run(["pyocd", "list"])
        probes: list[ProbeInfo] = []
        for line in out.splitlines():
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and not stripped.lower().startswith("no")
                and not re.fullmatch(r"-+", stripped)
            ):
                probes.append(ProbeInfo(uid="", description=stripped.lower(), raw=stripped))
        return probes

    try:
        data = json.loads(out)
        boards = data.get("boards", data) if isinstance(data, dict) else data
        probes = []
        for item in boards:
            description = " ".join(
                part for part in [item.get("description", ""), item.get("board_name", "")] if part
            )
            probes.append(
                ProbeInfo(
                    uid=item.get("unique_id", item.get("uid", "")),
                    description=description,
                    state=item.get("state", ""),
                    raw=str(item),
                )
            )
        return probes
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []


def list_target_names() -> set[str]:
    _, out, _ = run(["pyocd", "list", "--targets"])
    names: set[str] = set()
    for line in out.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or re.fullmatch(r"-+", stripped):
            continue
        names.add(stripped.split()[0].lower())
    return names


def read_memory_value(
    board: BoardConfig,
    probe: ProbeInfo | None,
    address: int,
    width_bits: int,
) -> ReadResult:
    if probe is None:
        return ReadResult(rc=1, stdout="", stderr="probe not detected")

    width_bits = validate_width_bits(width_bits, "width_bits")
    read_len = width_bits // 8
    cmd = pyocd_base("cmd", board, probe)
    cmd.extend(["-c", f"read{width_bits} {hex(address)} {read_len}"])
    last_result = ReadResult(rc=1, stdout="", stderr="unknown read failure")
    for attempt in range(3):
        rc, out, err = run(cmd)
        last_result = ReadResult(rc=rc, stdout=out, stderr=err, value=None)
        combined = last_result.combined
        if rc == 0 and out.strip() and "error" not in combined:
            match = re.search(r":\s+([0-9a-fA-F]+)", out)
            if match:
                return ReadResult(rc=rc, stdout=out, stderr=err, value=int(match.group(1), 16))
        if attempt < 2 and (
            "j-link is already open" in combined or "could not read j-link capabilities" in combined
        ):
            time.sleep(0.25)
            continue
        break
    return last_result


def pick_probe(
    board: BoardConfig, probes: list[ProbeInfo], allow_single_fallback: bool
) -> tuple[ProbeInfo | None, str]:
    scored = []
    for probe in probes:
        score = score_terms(probe.searchable_text, board.probe_hint_terms)
        if score > 0:
            scored.append((score, probe))

    if scored:
        best_score = max(score for score, _ in scored)
        best = [probe for score, probe in scored if score == best_score]
        if len(best) == 1:
            return best[0], ""
        return None, "multiple matching probes found; disconnect extras or refine probe_hint_terms"

    if allow_single_fallback and len(probes) == 1:
        probe = probes[0]
        family_terms = tuple(PROBE_FAMILY_HINTS.get(board.probe_family, set()))
        if family_terms and score_terms(probe.searchable_text, family_terms) > 0:
            return probe, "single connected probe assumed for this board"
        return None, "single connected probe does not match the expected probe family"

    return None, "no matching probe found"


def check_probes(boards_to_check: list[BoardConfig]) -> dict[str, ProbeInfo | None]:
    header("Connected probes")
    probes = list_probes()

    if not probes:
        _, out, _ = run(["pyocd", "list"])
        print(f"  Raw output:\n{out or '  (none)'}")
        results = {}
        for board in boards_to_check:
            check(False, f"{board.display_name} ({board.probe_type}) - no probes detected")
            results[board.board_id] = None
        return results

    print(f"  Found {len(probes)} probe(s):")
    for probe in probes:
        desc = probe.description or probe.raw
        suffix = f" [{probe.state}]" if probe.state else ""
        print(f"    - {probe.uid or '(no uid)'} :: {desc}{suffix}")

    results: dict[str, ProbeInfo | None] = {}
    allow_single_fallback = len(probes) == 1 and len(boards_to_check) == 1
    for board in boards_to_check:
        probe, note = pick_probe(board, probes, allow_single_fallback)
        if probe:
            detail = f"{board.display_name} ({board.probe_type}) probe visible"
            if note:
                detail += f" - {note}"
            check(True, detail)
        else:
            check(
                False,
                f"{board.display_name} ({board.probe_type}) probe not uniquely identifiable: {note}",
            )
        results[board.board_id] = probe

    return results


def check_target_packs(boards_to_check: list[BoardConfig], auto_install: bool) -> dict[str, bool]:
    header("CMSIS-Pack / target availability")
    installed_targets = list_target_names()

    results: dict[str, bool] = {}
    for board in boards_to_check:
        target_present = board.pyocd_target.lower() in installed_targets
        if target_present:
            check(True, f"{board.display_name}: target '{board.pyocd_target}' available")
            results[board.board_id] = True
            continue

        check(False, f"{board.display_name}: target '{board.pyocd_target}' not found")
        if auto_install:
            log(INFO, f"Installing pack for {board.pack_name}...")
            rc, _, _ = run(["pyocd", "pack", "install", board.pack_name], capture=False)
            if rc == 0:
                ok = board.pyocd_target.lower() in list_target_names()
                check(
                    ok,
                    f"Pack installed, target '{board.pyocd_target}' now {'available' if ok else 'still missing'}",
                )
                results[board.board_id] = ok
            else:
                check(
                    False,
                    f"Pack install failed - try manually: uv run pyocd pack find {board.pack_name}",
                )
                results[board.board_id] = False
        else:
            print(f"      Fix: uv run pyocd pack find {board.pack_name}")
            print(f"           uv run pyocd pack install {board.pack_name}")
            print("      Or re-run with --install-packs")
            results[board.board_id] = False

    return results


def check_connection(board: BoardConfig, probe: ProbeInfo | None, target_ok: bool) -> bool:
    header(f"Connection test - {board.display_name}")

    if probe is None:
        check(False, "Skipped - probe not detected")
        return False
    if not target_ok:
        check(False, "Skipped - target pack not installed")
        return False

    cmd = pyocd_base("cmd", board, probe)
    cmd.extend(["-c", f"read32 {hex(board.test_addr)} 4"])
    print(f"  Attempting: {' '.join(cmd)}")
    result = read_memory_value(board, probe, board.test_addr, 32)

    if result.value is not None:
        check(True, f"Connected and read {hex(board.test_addr)}: {result.stdout.strip()}")
        return True

    if (
        "approtect" in result.combined
        or "access port" in result.combined
        or "locked" in result.combined
    ):
        log(WARN, f"{board.display_name} appears access-protected.")
        if board.recover_command:
            print(
                f'      Recover with: pyocd cmd -t {board.pyocd_target} -c "{board.recover_command}"'
            )
        return False

    if (
        "no connected" in result.combined
        or "no target" in result.combined
        or "unable to connect" in result.combined
    ):
        check(False, "pyOCD found the probe but could not connect to the target MCU")
        print("      - Is the board powered?")
        print("      - Is the USB cable a data cable (not charge-only)?")
        if board.probe_family == "jlink":
            print("      - J-Link firmware or drivers may need updating")
        return False

    if (
        "no emulator" in result.combined
        or "could not read j-link capabilities" in result.combined
        or "no j-link" in result.combined
        or "unable to open" in result.combined
        or "could not open" in result.combined
        or "failed to open" in result.combined
        or "access denied" in result.combined
        or "no backend available" in result.combined
        or "no usb backend" in result.combined
        or "libusb" in result.combined
    ):
        check(
            False,
            f"{board.display_name} probe is visible but the {board.probe_type} backend could not claim it",
        )
        print("      The probe enumerates on the host but the debug channel cannot be opened.")
        print("      This is almost always a USB driver-binding or exclusive-access issue, not the board:")
        print("      - Close anything else holding the probe (other pyOCD/JLink/IDE sessions, an MCP server) and replug.")
        if board.probe_family == "jlink":
            print(
                "      - The J-Link debug interface must be bound to the SEGGER J-Link driver, not generic WinUSB."
            )
            print(
                "        Reinstall the SEGGER J-Link Software pack (it rebinds the driver), then replug."
            )
        elif board.probe_family == "stlink":
            print("      - Install/repair the ST-Link USB driver, then replug.")
        else:
            print(
                "      - Ensure the debug interface is bound to the driver pyOCD expects for this probe family."
            )
        return False

    check(False, f"Unexpected error (rc={result.rc})")
    if result.stdout.strip():
        print(f"      stdout: {result.stdout.strip()[:300]}")
    if result.stderr.strip():
        print(f"      stderr: {result.stderr.strip()[:300]}")
    return False


def check_silicon_identity(
    board: BoardConfig,
    probe: ProbeInfo | None,
    target_ok: bool,
) -> bool | None:
    if board.silicon_id_addr is None or board.silicon_id_expected is None:
        return None

    header(f"Silicon identity - {board.display_name}")

    if probe is None:
        check(False, "Skipped - probe not detected")
        return False
    if not target_ok:
        check(False, "Skipped - target pack not installed")
        return False

    label = board.silicon_id_label or "silicon identity"
    cmd = pyocd_base("cmd", board, probe)
    cmd.extend(
        [
            "-c",
            f"read{board.silicon_id_width_bits} {hex(board.silicon_id_addr)} {board.silicon_id_width_bits // 8}",
        ]
    )
    print(f"  Attempting: {' '.join(cmd)}")
    result = read_memory_value(board, probe, board.silicon_id_addr, board.silicon_id_width_bits)
    if result.value is None:
        check(False, f"Unable to read {label}")
        if result.stdout.strip():
            print(f"      stdout: {result.stdout.strip()[:300]}")
        if result.stderr.strip():
            print(f"      stderr: {result.stderr.strip()[:300]}")
        return False

    mask = (
        board.silicon_id_mask
        if board.silicon_id_mask is not None
        else (1 << board.silicon_id_width_bits) - 1
    )
    actual_masked = result.value & mask
    expected_masked = board.silicon_id_expected & mask
    ok = actual_masked == expected_masked
    check(
        ok,
        f"{label} {'matched' if ok else 'did not match'} "
        f"(actual=0x{actual_masked:X}, expected=0x{expected_masked:X}, mask=0x{mask:X})",
    )
    if result.stdout.strip():
        print(f"      Raw: {result.stdout.strip()[:300]}")
    return ok


def list_serial_ports() -> list[SerialPortInfo] | None:
    _, list_ports = load_pyserial()
    if list_ports is None:
        return None

    ports = []
    for port in list_ports.comports():
        ports.append(
            SerialPortInfo(
                device=port.device,
                description=port.description or "",
                manufacturer=getattr(port, "manufacturer", "") or "",
                product=getattr(port, "product", "") or "",
                interface=getattr(port, "interface", "") or "",
                hwid=port.hwid or "",
                serial_number=getattr(port, "serial_number", "") or "",
                location=getattr(port, "location", "") or "",
                vid=getattr(port, "vid", None),
                pid=getattr(port, "pid", None),
            )
        )
    return ports


def check_virtual_com_ports(
    boards_to_check: list[BoardConfig],
    probes_by_board: dict[str, ProbeInfo | None],
    port_overrides: dict[str, str],
    pyserial_ok: bool,
) -> dict[str, SerialPortInfo | None]:
    header("Virtual COM / serial ports")

    if not pyserial_ok:
        for board in boards_to_check:
            check(False, f"{board.display_name} COM-port check skipped - pyserial is not installed")
        return {board.board_id: None for board in boards_to_check}

    ports = list_serial_ports()
    if ports is None:
        for board in boards_to_check:
            check(False, f"{board.display_name} COM-port check unavailable")
        return {board.board_id: None for board in boards_to_check}

    if not ports:
        check(False, "No serial ports detected")
        return {board.board_id: None for board in boards_to_check}

    print(f"  Found {len(ports)} serial port(s):")
    for port in ports:
        desc = port.description or "(no description)"
        extras = " ".join(
            part
            for part in [
                port.manufacturer,
                port.product,
                port.interface,
                port.serial_number,
                port.location,
            ]
            if part
        )
        if extras:
            desc = f"{desc} :: {extras}"
        print(f"    - {port.device} :: {desc}")

    results: dict[str, SerialPortInfo | None] = {}
    allow_single_fallback = len(ports) == 1 and len(boards_to_check) == 1
    interactive = is_interactive_terminal()
    for board in boards_to_check:
        resolution = resolve_serial_port(
            board=board,
            ports=ports,
            probe=probes_by_board.get(board.board_id),
            override=port_overrides.get(board.board_id),
            allow_single_fallback=allow_single_fallback,
            run_cmd=run,
            interactive=interactive,
        )
        port = resolution.port
        note = resolution.note
        if port:
            detail = f"{board.display_name} virtual COM port visible on {port.device}"
            if note:
                detail += f" - {note}"
            check(True, detail)
        else:
            check(False, f"{board.display_name} COM port not uniquely identifiable: {note}")
            if board.uart_note:
                print(f"      Note: {board.uart_note}")
        results[board.board_id] = port

    return results


def flash_reference_firmware(
    board: BoardConfig,
    probe: ProbeInfo | None,
    target_ok: bool,
    identity_ok: bool | None,
    reference_firmware_path: Path | None,
) -> bool | None:
    header(f"Reference firmware flash - {board.display_name}")

    if reference_firmware_path is None:
        log(WARN, "No reference firmware path supplied - leaving flash validation as a manual step")
        return None
    if not reference_firmware_path.exists():
        check(False, f"Reference firmware file does not exist: {reference_firmware_path}")
        return False
    if probe is None:
        check(False, "Skipped - probe not detected")
        return False
    if not target_ok:
        check(False, "Skipped - target pack not installed")
        return False
    if board.silicon_id_expected is not None and identity_ok is False:
        check(False, "Skipped - connected silicon identity does not match this board config")
        return False

    def try_nrfjprog_fallback() -> bool:
        if not (board.mcu_family.startswith("nrf") and board.probe_family == "jlink"):
            return False
        if not command_exists("nrfjprog"):
            return False

        flash_image_path = reference_firmware_path
        if reference_firmware_path.suffix.lower() != ".hex":
            hex_candidate = reference_firmware_path.with_suffix(".hex")
            if not hex_candidate.exists():
                print(
                    "      pyOCD flash failed and no sibling .hex artifact exists for the nrfjprog fallback"
                )
                return False
            flash_image_path = hex_candidate

        flash_cmd = ["nrfjprog", "--program", str(flash_image_path), "--sectorerase", "--verify", "-f", "NRF52"]
        reset_cmd = ["nrfjprog", "--reset", "-f", "NRF52"]
        print(f"  Attempting fallback: {' '.join(flash_cmd)}")
        flash_rc, flash_out, flash_err = run(flash_cmd)
        if flash_rc != 0:
            if flash_err.strip():
                print(f"      fallback stderr: {flash_err.strip()[:300]}")
            return False

        print(f"  Attempting fallback reset: {' '.join(reset_cmd)}")
        reset_rc, reset_out, reset_err = run(reset_cmd)
        if reset_rc != 0:
            if reset_err.strip():
                print(f"      reset stderr: {reset_err.strip()[:300]}")
            return False

        check(
            True,
            f"Flashed reference firmware with nrfjprog fallback: {reference_firmware_path}",
        )
        trimmed_flash_out = flash_out.strip()[:300]
        trimmed_reset_out = reset_out.strip()[:300]
        if trimmed_flash_out:
            print(f"      flash output: {trimmed_flash_out}")
        if trimmed_reset_out:
            print(f"      reset output: {trimmed_reset_out}")
        return True

    cmd = pyocd_base("load", board, probe)
    cmd.append(str(reference_firmware_path))
    print(f"  Attempting: {' '.join(cmd)}")
    rc, out, err = run(cmd)
    if rc == 0:
        check(True, f"Flashed reference firmware: {reference_firmware_path}")
        if out.strip():
            print(f"      {out.strip()[:300]}")
        return True

    check(False, f"Flash failed for {reference_firmware_path}")
    if err.strip():
        print(f"      stderr: {err.strip()[:300]}")
    return True if try_nrfjprog_fallback() else False


def read_uart_output(
    board: BoardConfig,
    port: SerialPortInfo | None,
    baudrate: int,
    read_seconds: float,
    expected_text: str | None,
) -> bool | None:
    header(f"UART output check - {board.display_name}")

    if port is None:
        check(False, "Skipped - COM port not detected")
        return False

    serial_mod, _ = load_pyserial()
    if serial_mod is None:
        check(False, "Skipped - pyserial is not installed")
        return False

    deadline = time.monotonic() + read_seconds
    captured = bytearray()
    try:
        with serial_mod.Serial(port.device, baudrate=baudrate, timeout=0.2) as handle:
            handle.reset_input_buffer()
            while time.monotonic() < deadline:
                chunk = handle.read(256)
                if chunk:
                    captured.extend(chunk)
    except Exception as exc:
        check(False, f"Unable to read {port.device} at {baudrate} baud: {exc}")
        return False

    text = captured.decode("utf-8", errors="replace")
    excerpt = text.strip().replace("\r", "\\r").replace("\n", "\\n")
    excerpt = excerpt[:300] if excerpt else ""

    if expected_text:
        ok = expected_text in text
        check(
            ok, f"UART output {'matched' if ok else 'did not match'} expected text on {port.device}"
        )
        if excerpt:
            print(f"      Captured: {excerpt}")
        return ok

    ok = bool(text.strip())
    check(ok, f"UART produced {'some output' if ok else 'no output'} on {port.device}")
    if excerpt:
        print(f"      Captured: {excerpt}")
    return ok


def run_recover_test(
    board: BoardConfig,
    probe: ProbeInfo | None,
    target_ok: bool,
    identity_ok: bool | None,
    enabled: bool,
) -> bool | None:
    if not board.requires_recover_validation:
        return None

    header(f"Recover / unlock validation - {board.display_name}")

    if not enabled:
        log(WARN, "Recover test not run - this remains a required manual Stage 0 validation")
        return None
    if probe is None:
        check(False, "Skipped - probe not detected")
        return False
    if not target_ok:
        check(False, "Skipped - target pack not installed")
        return False
    if board.silicon_id_expected is not None and identity_ok is False:
        check(False, "Skipped - connected silicon identity does not match this board config")
        return False
    if not board.recover_command:
        check(False, "Skipped - no recover command configured for this board")
        return False

    print("  Running destructive recover command. This may erase flash on the target.")
    cmd = pyocd_base("cmd", board, probe)
    cmd.extend(["-c", board.recover_command])
    print(f"  Attempting: {' '.join(cmd)}")
    rc, _, err = run(cmd)
    if rc != 0:
        check(False, "Recover command failed")
        if err.strip():
            print(f"      stderr: {err.strip()[:300]}")
        return False

    check(True, "Recover command completed")
    reconnect_ok = check_connection(board, probe, target_ok)
    return reconnect_ok


def summarise_status(status: str) -> str:
    if status == SUMMARY_PASS:
        return PASS
    if status == SUMMARY_FAIL:
        return FAIL
    return WARN


def print_summary(items: list[SummaryItem], manual_items: list[str]) -> bool:
    header("Summary")

    automated_failures = False
    pending_manual = False
    for item in items:
        symbol = summarise_status(item.status)
        suffix = f" - {item.detail}" if item.detail else ""
        print(f"  [{symbol}] {item.label}{suffix}")
        if item.status == SUMMARY_FAIL:
            automated_failures = True
        if item.status == SUMMARY_MANUAL:
            pending_manual = True

    if manual_items:
        header("Manual validation still required")
        seen = set()
        for item in manual_items:
            if item in seen:
                continue
            seen.add(item)
            print(f"  - {item}")

    print()
    if automated_failures:
        print("  Automated Stage 0 checks failed. Fix the items above and re-run.")
    elif pending_manual or manual_items:
        print(
            "  Automated checks passed, but full Stage 0 is not complete until the manual items are validated."
        )
    else:
        print("  Automated checks passed and this run covered the requested Stage 0 validations.")
    print()

    return not automated_failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage 0 board validation")
    parser.add_argument(
        "--board-config-dir",
        default=str(DEFAULT_BOARD_CONFIG_DIR),
        help="Directory containing board config files. Defaults to the repo's boards/ directory.",
    )
    parser.add_argument(
        "--board-config",
        action="append",
        default=[],
        help="Additional board config file (.json, .yaml, .yml). Repeat for multiple extra boards.",
    )
    parser.add_argument(
        "--board-id",
        action="append",
        default=[],
        help="Board id to run. Repeat to select multiple boards. Defaults to all non-example board configs in the board-config-dir plus any extra board-config files.",
    )
    parser.add_argument(
        "--install-packs",
        action="store_true",
        help="Automatically install missing CMSIS-Packs",
    )
    parser.add_argument(
        "--port",
        action="append",
        default=[],
        metavar="BOARD_ID=PORT",
        help="Override the detected virtual COM port for a board.",
    )
    parser.add_argument(
        "--reference-firmware",
        action="append",
        default=[],
        metavar="BOARD_ID=PATH",
        help="Reference firmware path for a board.",
    )
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="BOARD_ID=TEXT",
        help="Substring expected in the UART output for a board.",
    )
    parser.add_argument(
        "--baudrate",
        action="append",
        default=[],
        metavar="BOARD_ID=BAUD",
        help="Override the UART baud rate for a board.",
    )
    parser.add_argument(
        "--recover-test",
        action="append",
        default=[],
        metavar="BOARD_ID",
        help="Run the destructive recover validation for the given board_id. Repeat for multiple boards.",
    )
    parser.add_argument(
        "--confirm-shared-usb",
        action="append",
        default=[],
        metavar="BOARD_ID",
        help="Record that a human confirmed the visible debug probe and COM port come from the same physical board.",
    )
    parser.add_argument(
        "--serial-read-seconds",
        type=float,
        default=3.0,
        help="How long to listen for UART output after opening the port.",
    )
    return parser


def collect_overrides(
    args: argparse.Namespace,
) -> tuple[dict[str, str], dict[str, Path], dict[str, str], dict[str, int], set[str], set[str]]:
    port_overrides = parse_key_value(args.port, "--port")
    reference_firmware_overrides = {
        board_id: resolve_firmware_path(path_text)
        for board_id, path_text in parse_key_value(
            args.reference_firmware, "--reference-firmware"
        ).items()
    }
    expect_overrides = parse_key_value(args.expect, "--expect")
    baudrate_overrides = {
        board_id: parse_int(value, "--baudrate")
        for board_id, value in parse_key_value(args.baudrate, "--baudrate").items()
    }
    recover_tests = {board_id.strip().lower() for board_id in args.recover_test if board_id.strip()}
    confirmed_shared_usb = {
        board_id.strip().lower() for board_id in args.confirm_shared_usb if board_id.strip()
    }

    return (
        port_overrides,
        reference_firmware_overrides,
        expect_overrides,
        baudrate_overrides,
        recover_tests,
        confirmed_shared_usb,
    )


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        board_config_dir = Path(args.board_config_dir).expanduser().resolve()
        custom_board_paths = [
            Path(raw_path).expanduser().resolve() for raw_path in args.board_config
        ]
        boards_to_check = load_selected_board_configs(
            board_config_dir,
            extra_paths=custom_board_paths,
            requested_ids=args.board_id,
        )
        if not boards_to_check:
            raise ConfigError(
                "No boards selected. Add board configs or pass --board-id for an existing board."
            )
        (
            port_overrides,
            reference_firmware_overrides,
            expect_overrides,
            baudrate_overrides,
            recover_tests,
            confirmed_shared_usb,
        ) = collect_overrides(args)
    except ConfigError as exc:
        parser.error(str(exc))
        return

    print("\nStage 0 - Board and toolchain validation")
    print(f"Checking: {', '.join(board.display_name for board in boards_to_check)}")

    pyocd_ok = check_pyocd_installed()
    pyserial_ok = check_pyserial_installed()
    if not pyocd_ok:
        sys.exit(1)

    probes = check_probes(boards_to_check)
    target_ok = check_target_packs(boards_to_check, auto_install=args.install_packs)
    serial_ports = check_virtual_com_ports(boards_to_check, probes, port_overrides, pyserial_ok)

    summary_items: list[SummaryItem] = []
    manual_items: list[str] = []

    for board in boards_to_check:
        probe = probes.get(board.board_id)
        target_available = target_ok.get(board.board_id, False)
        port = serial_ports.get(board.board_id)
        reference_firmware_path = reference_firmware_overrides.get(board.board_id)
        expected_text = expect_overrides.get(board.board_id, board.expected_uart_substring)
        baudrate = baudrate_overrides.get(board.board_id, board.default_baudrate)

        conn_ok = check_connection(board, probe, target_available)
        identity_ok = check_silicon_identity(board, probe, target_available)
        flash_ok = flash_reference_firmware(
            board,
            probe,
            target_available,
            identity_ok,
            reference_firmware_path,
        )
        uart_ok = None
        if flash_ok is True:
            uart_ok = read_uart_output(
                board,
                port,
                baudrate,
                args.serial_read_seconds,
                expected_text,
            )
        recover_ok = run_recover_test(
            board,
            probe,
            target_available,
            identity_ok,
            board.board_id in recover_tests,
        )

        summary_items.extend(
            [
                SummaryItem(
                    f"{board.display_name}: probe visible", SUMMARY_PASS if probe else SUMMARY_FAIL
                ),
                SummaryItem(
                    f"{board.display_name}: target '{board.pyocd_target}' available",
                    SUMMARY_PASS if target_available else SUMMARY_FAIL,
                ),
                SummaryItem(
                    f"{board.display_name}: connect + read register",
                    SUMMARY_PASS if conn_ok else SUMMARY_FAIL,
                ),
            ]
        )

        if board.silicon_id_expected is not None:
            summary_items.append(
                SummaryItem(
                    f"{board.display_name}: exact silicon identity matches board config",
                    SUMMARY_PASS if identity_ok else SUMMARY_FAIL,
                )
            )

        summary_items.extend(
            [
                SummaryItem(
                    f"{board.display_name}: virtual COM port visible",
                    SUMMARY_PASS if port else SUMMARY_FAIL,
                ),
            ]
        )

        if flash_ok is None:
            summary_items.append(
                SummaryItem(
                    f"{board.display_name}: flash known-good reference firmware",
                    SUMMARY_MANUAL,
                    f"provide --reference-firmware {board_cli_label(board)}=PATH from the host filesystem",
                )
            )
            manual_items.append(
                f"{board.display_name}: flash a known-good reference image and verify it is the intended baseline artifact."
            )
        else:
            summary_items.append(
                SummaryItem(
                    f"{board.display_name}: flash known-good reference firmware",
                    SUMMARY_PASS if flash_ok else SUMMARY_FAIL,
                )
            )

        if reference_firmware_path is None:
            summary_items.append(
                SummaryItem(
                    f"{board.display_name}: UART output observed",
                    SUMMARY_MANUAL,
                    f"requires flashed reference firmware and optional --expect {board_cli_label(board)}=TEXT",
                )
            )
            manual_items.append(
                f"{board.display_name}: confirm the reference firmware prints over UART on the expected port and baudrate."
            )
        elif flash_ok is False:
            summary_items.append(
                SummaryItem(
                    f"{board.display_name}: UART output observed",
                    SUMMARY_FAIL,
                )
            )
        else:
            summary_items.append(
                SummaryItem(
                    f"{board.display_name}: UART output observed",
                    SUMMARY_PASS if uart_ok else SUMMARY_FAIL,
                )
            )
            if expected_text is None:
                manual_items.append(
                    f"{board.display_name}: confirm the captured UART text is the expected reference-firmware output, not just arbitrary bytes."
                )

        if board.requires_recover_validation:
            if recover_ok is None:
                summary_items.append(
                    SummaryItem(
                        f"{board.display_name}: recover / unlock cycle proven",
                        SUMMARY_MANUAL,
                        f"run with --recover-test {board_cli_label(board)} to automate the destructive check",
                    )
                )
                manual_items.append(
                    f"{board.display_name}: prove a recover/unlock cycle on this machine. This may erase flash, so it is opt-in."
                )
            else:
                summary_items.append(
                    SummaryItem(
                        f"{board.display_name}: recover / unlock cycle proven",
                        SUMMARY_PASS if recover_ok else SUMMARY_FAIL,
                    )
                )

        if board.board_id not in confirmed_shared_usb:
            manual_items.append(
                f"{board.display_name}: confirm the visible debug probe and COM port are exposed by the same physical USB connection."
            )

    automated_ok = print_summary(summary_items, manual_items)
    sys.exit(0 if automated_ok else 1)


if __name__ == "__main__":
    main()
