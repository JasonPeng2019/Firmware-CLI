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

Destructive or inherently physical checks are kept explicit:
- nRF recover/unlock is opt-in because it erases flash
- "one physical USB cable exposes both endpoints" still needs manual confirmation
"""

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
INFO = "INFO"

SUMMARY_PASS = "pass"
SUMMARY_FAIL = "fail"
SUMMARY_MANUAL = "manual"


@dataclass(frozen=True)
class BoardConfig:
    key: str
    name: str
    pyocd_target: str
    pack_name: str
    probe_type: str
    probe_hint_terms: tuple[str, ...]
    serial_hint_terms: tuple[str, ...]
    test_addr: int
    default_baudrate: int = 115200
    uart_note: str = ""
    requires_recover_validation: bool = False


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
class SerialPortInfo:
    device: str
    description: str
    manufacturer: str
    product: str
    interface: str
    hwid: str
    vid: int | None = None
    pid: int | None = None

    @property
    def searchable_text(self) -> str:
        return " ".join(
            [
                self.device,
                self.description,
                self.manufacturer,
                self.product,
                self.interface,
                self.hwid,
                "" if self.vid is None else f"{self.vid:04x}",
                "" if self.pid is None else f"{self.pid:04x}",
            ]
        ).lower()


@dataclass(frozen=True)
class SummaryItem:
    label: str
    status: str
    detail: str = ""


BOARDS = {
    "nrf": BoardConfig(
        key="nrf",
        name="nRF52840-DK",
        pyocd_target="nrf52840",
        pack_name="nrf52840",
        probe_type="SEGGER J-Link",
        probe_hint_terms=("j-link", "jlink", "segger", "nrf"),
        serial_hint_terms=("j-link", "jlink", "segger", "nrf", "virtual com"),
        test_addr=0x10000000,
        default_baudrate=115200,
        requires_recover_validation=True,
    ),
    "nucleo": BoardConfig(
        key="nucleo",
        name="Nucleo-L476RG",
        pyocd_target="stm32l476rg",
        pack_name="stm32l476",
        probe_type="ST-Link/V2-1",
        probe_hint_terms=("st-link", "stlink", "stm32", "nucleo"),
        serial_hint_terms=("st-link", "stlink", "stm32", "nucleo", "virtual com"),
        test_addr=0x08000000,
        default_baudrate=115200,
        uart_note="Reference firmware should print on USART2 at 115200 8N1.",
    ),
}


def run(cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=capture, text=True)
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


def board_arg_name(board: BoardConfig, suffix: str) -> str:
    return f"--{board.key}-{suffix}"


def pyocd_base(subcommand: str, board: BoardConfig, probe: ProbeInfo | None) -> list[str]:
    cmd = ["pyocd", subcommand, "-t", board.pyocd_target]
    if probe and probe.uid:
        cmd.extend(["-u", probe.uid])
    return cmd


def load_pyserial():
    try:
        import serial as serial_mod
        from serial.tools import list_ports
    except ImportError:
        return None, None
    return serial_mod, list_ports


def check_pyocd_installed() -> bool:
    header("pyOCD installation")
    rc, out, _ = run(["pyocd", "--version"])
    ok = rc == 0
    if ok:
        check(True, f"pyOCD found: {out.strip()}")
    else:
        check(False, "pyOCD not found - run: pip install pyocd")
    return ok


def check_pyserial_installed() -> bool:
    header("pyserial installation")
    serial_mod, _ = load_pyserial()
    ok = serial_mod is not None
    if ok:
        version = getattr(serial_mod, "__version__", "unknown version")
        check(True, f"pyserial found: {version}")
    else:
        check(False, "pyserial not found - run: pip install pyserial")
    return ok


def list_probes() -> list[ProbeInfo]:
    rc, out, _ = run(["pyocd", "list", "--output", "json"])
    if rc != 0 or not out.strip():
        rc, out, _ = run(["pyocd", "list"])
        probes: list[ProbeInfo] = []
        for line in out.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.lower().startswith("no"):
                probes.append(ProbeInfo(uid="", description=stripped.lower(), raw=stripped))
        return probes

    import json

    try:
        data = json.loads(out)
        boards = data.get("boards", data) if isinstance(data, dict) else data
        probes = []
        for item in boards:
            description = " ".join(
                part for part in [item.get("description", ""), item.get("board_name", "")]
                if part
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


def pick_probe(board: BoardConfig, probes: list[ProbeInfo], allow_single_fallback: bool) -> tuple[ProbeInfo | None, str]:
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
        return None, "multiple matching probes found; disconnect extras or refine detection"

    if allow_single_fallback and len(probes) == 1:
        return probes[0], "single connected probe assumed for this board"

    return None, "no matching probe found"


def check_probes(boards_to_check: list[BoardConfig]) -> dict[str, ProbeInfo | None]:
    header("Connected probes")
    probes = list_probes()

    if not probes:
        _, out, _ = run(["pyocd", "list"])
        print(f"  Raw output:\n{out or '  (none)'}")
        results = {}
        for board in boards_to_check:
            check(False, f"{board.name} ({board.probe_type}) - no probes detected")
            results[board.key] = None
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
            detail = f"{board.name} ({board.probe_type}) probe visible"
            if note:
                detail += f" - {note}"
            check(True, detail)
        else:
            check(False, f"{board.name} ({board.probe_type}) probe not uniquely identifiable: {note}")
        results[board.key] = probe

    return results


def check_target_packs(boards_to_check: list[BoardConfig], auto_install: bool) -> dict[str, bool]:
    header("CMSIS-Pack / target availability")
    _, out, _ = run(["pyocd", "list", "--targets"])
    installed_targets = out.lower()

    results: dict[str, bool] = {}
    for board in boards_to_check:
        target_present = board.pyocd_target in installed_targets
        if target_present:
            check(True, f"Target '{board.pyocd_target}' available")
            results[board.key] = True
            continue

        check(False, f"Target '{board.pyocd_target}' not found")
        if auto_install:
            log(INFO, f"Installing pack for {board.pack_name}...")
            rc, _, _ = run(["pyocd", "pack", "install", board.pack_name], capture=False)
            if rc == 0:
                _, refreshed, _ = run(["pyocd", "list", "--targets"])
                ok = board.pyocd_target in refreshed.lower()
                check(ok, f"Pack installed, target '{board.pyocd_target}' now {'available' if ok else 'still missing'}")
                results[board.key] = ok
            else:
                check(False, f"Pack install failed - try manually: pyocd pack find {board.pack_name}")
                results[board.key] = False
        else:
            print(f"      Fix: pyocd pack find {board.pack_name}")
            print(f"           pyocd pack install {board.pack_name}")
            print("      Or re-run with --install-packs")
            results[board.key] = False

    return results


def check_connection(board: BoardConfig, probe: ProbeInfo | None, target_ok: bool) -> bool:
    header(f"Connection test - {board.name}")

    if probe is None:
        check(False, "Skipped - probe not detected")
        return False
    if not target_ok:
        check(False, "Skipped - target pack not installed")
        return False

    cmd = pyocd_base("cmd", board, probe)
    cmd.extend(["-c", f"read32 {hex(board.test_addr)} 1"])
    print(f"  Attempting: {' '.join(cmd)}")
    rc, out, err = run(cmd)

    if rc == 0 and out.strip():
        check(True, f"Connected and read {hex(board.test_addr)}: {out.strip()}")
        return True

    combined = f"{out}\n{err}".lower()
    if "approtect" in combined or "access port" in combined or "locked" in combined:
        log(WARN, "nRF52840 appears access-protected.")
        print("      Recover with: pyocd cmd -t nrf52840 -c \"nrf recover\"")
        print("      This erases flash but restores SWD access.")
        return False

    if "no connected" in combined or "no target" in combined or "unable to connect" in combined:
        check(False, "pyOCD found the probe but could not connect to the target MCU")
        print("      - Is the board powered?")
        print("      - Is the USB cable a data cable (not charge-only)?")
        if board.key == "nrf":
            print("      - J-Link firmware or drivers may need updating")
        return False

    check(False, f"Unexpected error (rc={rc})")
    if err.strip():
        print(f"      stderr: {err.strip()[:300]}")
    return False


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
                vid=getattr(port, "vid", None),
                pid=getattr(port, "pid", None),
            )
        )
    return ports


def pick_serial_port(
    board: BoardConfig,
    ports: list[SerialPortInfo],
    override: str | None,
    allow_single_fallback: bool,
) -> tuple[SerialPortInfo | None, str]:
    if override:
        for port in ports:
            if port.device.lower() == override.lower():
                return port, ""
        return None, f"override port '{override}' not found"

    scored = []
    for port in ports:
        score = score_terms(port.searchable_text, board.serial_hint_terms)
        if score > 0:
            scored.append((score, port))

    if scored:
        best_score = max(score for score, _ in scored)
        best = [port for score, port in scored if score == best_score]
        if len(best) == 1:
            return best[0], ""
        return None, "multiple matching serial ports found; use an explicit override"

    if allow_single_fallback and len(ports) == 1:
        return ports[0], "single connected serial port assumed for this board"

    return None, "no matching serial port found"


def check_virtual_com_ports(
    boards_to_check: list[BoardConfig],
    port_overrides: dict[str, str | None],
    pyserial_ok: bool,
) -> dict[str, SerialPortInfo | None]:
    header("Virtual COM / serial ports")

    if not pyserial_ok:
        for board in boards_to_check:
            check(False, f"{board.name} COM-port check skipped - pyserial is not installed")
        return {board.key: None for board in boards_to_check}

    ports = list_serial_ports()
    if ports is None:
        for board in boards_to_check:
            check(False, f"{board.name} COM-port check unavailable")
        return {board.key: None for board in boards_to_check}

    if not ports:
        check(False, "No serial ports detected")
        return {board.key: None for board in boards_to_check}

    print(f"  Found {len(ports)} serial port(s):")
    for port in ports:
        desc = port.description or "(no description)"
        extras = " ".join(part for part in [port.manufacturer, port.product, port.interface] if part)
        if extras:
            desc = f"{desc} :: {extras}"
        print(f"    - {port.device} :: {desc}")

    results: dict[str, SerialPortInfo | None] = {}
    allow_single_fallback = len(ports) == 1 and len(boards_to_check) == 1
    for board in boards_to_check:
        port, note = pick_serial_port(board, ports, port_overrides.get(board.key), allow_single_fallback)
        if port:
            detail = f"{board.name} virtual COM port visible on {port.device}"
            if note:
                detail += f" - {note}"
            check(True, detail)
        else:
            check(False, f"{board.name} COM port not uniquely identifiable: {note}")
            if board.uart_note:
                print(f"      Note: {board.uart_note}")
        results[board.key] = port

    return results


def resolve_firmware_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    return Path(path_value).expanduser().resolve()


def flash_firmware(board: BoardConfig, probe: ProbeInfo | None, target_ok: bool, firmware_path: Path | None) -> bool | None:
    header(f"Reference firmware flash - {board.name}")

    if firmware_path is None:
        log(WARN, "No firmware path supplied - leaving flash validation as a manual step")
        return None
    if not firmware_path.exists():
        check(False, f"Firmware file does not exist: {firmware_path}")
        return False
    if probe is None:
        check(False, "Skipped - probe not detected")
        return False
    if not target_ok:
        check(False, "Skipped - target pack not installed")
        return False

    cmd = pyocd_base("load", board, probe)
    cmd.append(str(firmware_path))
    print(f"  Attempting: {' '.join(cmd)}")
    rc, out, err = run(cmd)
    if rc == 0:
        check(True, f"Flashed reference firmware: {firmware_path}")
        if out.strip():
            print(f"      {out.strip()[:300]}")
        return True

    check(False, f"Flash failed for {firmware_path}")
    if err.strip():
        print(f"      stderr: {err.strip()[:300]}")
    return False


def read_uart_output(
    board: BoardConfig,
    port: SerialPortInfo | None,
    baudrate: int,
    read_seconds: float,
    expected_text: str | None,
) -> bool | None:
    header(f"UART output check - {board.name}")

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
        check(ok, f"UART output {'matched' if ok else 'did not match'} expected text on {port.device}")
        if excerpt:
            print(f"      Captured: {excerpt}")
        return ok

    ok = bool(text.strip())
    check(ok, f"UART produced {'some output' if ok else 'no output'} on {port.device}")
    if excerpt:
        print(f"      Captured: {excerpt}")
    return ok


def run_nrf_recover_test(board: BoardConfig, probe: ProbeInfo | None, target_ok: bool, enabled: bool) -> bool | None:
    if board.key != "nrf":
        return None

    header("nRF recover / unlock validation")

    if not enabled:
        log(WARN, "Recover test not run - this remains a required manual Stage 0 validation")
        return None
    if probe is None:
        check(False, "Skipped - probe not detected")
        return False
    if not target_ok:
        check(False, "Skipped - target pack not installed")
        return False

    print("  Running destructive recover command. This erases flash on the nRF52840-DK.")
    cmd = pyocd_base("cmd", board, probe)
    cmd.extend(["-c", "nrf recover"])
    print(f"  Attempting: {' '.join(cmd)}")
    rc, out, err = run(cmd)
    if rc != 0:
        check(False, "nRF recover command failed")
        if err.strip():
            print(f"      stderr: {err.strip()[:300]}")
        return False

    check(True, "nRF recover command completed")
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
        for item in manual_items:
            print(f"  - {item}")

    print()
    if automated_failures:
        print("  Automated Stage 0 checks failed. Fix the items above and re-run.")
    elif pending_manual or manual_items:
        print("  Automated checks passed, but full Stage 0 is not complete until the manual items are validated.")
    else:
        print("  Automated checks passed and this run covered the requested Stage 0 validations.")
    print()

    return not automated_failures


def main():
    parser = argparse.ArgumentParser(description="Stage 0 board validation")
    parser.add_argument(
        "--board",
        choices=["nrf", "nucleo", "both"],
        default="both",
        help="Which board(s) to check (default: both)",
    )
    parser.add_argument(
        "--install-packs",
        action="store_true",
        help="Automatically install missing CMSIS-Packs",
    )
    parser.add_argument(
        "--nrf-firmware",
        help="Path to the known-good nRF reference firmware image to flash",
    )
    parser.add_argument(
        "--nucleo-firmware",
        help="Path to the known-good Nucleo reference firmware image to flash",
    )
    parser.add_argument(
        "--nrf-port",
        help="Override the detected nRF virtual COM port (for example COM7)",
    )
    parser.add_argument(
        "--nucleo-port",
        help="Override the detected Nucleo virtual COM port (for example COM8)",
    )
    parser.add_argument(
        "--nrf-baudrate",
        type=int,
        default=BOARDS["nrf"].default_baudrate,
        help="Baud rate for the nRF UART read check",
    )
    parser.add_argument(
        "--nucleo-baudrate",
        type=int,
        default=BOARDS["nucleo"].default_baudrate,
        help="Baud rate for the Nucleo UART read check",
    )
    parser.add_argument(
        "--nrf-expect",
        help="Substring expected in the nRF UART output after flashing",
    )
    parser.add_argument(
        "--nucleo-expect",
        help="Substring expected in the Nucleo UART output after flashing",
    )
    parser.add_argument(
        "--serial-read-seconds",
        type=float,
        default=3.0,
        help="How long to listen for UART output after opening the port",
    )
    parser.add_argument(
        "--nrf-recover-test",
        action="store_true",
        help="Run the destructive 'nrf recover' validation on the nRF52840-DK",
    )
    args = parser.parse_args()

    boards_to_check = list(BOARDS.values()) if args.board == "both" else [BOARDS[args.board]]
    firmware_paths = {
        "nrf": resolve_firmware_path(args.nrf_firmware),
        "nucleo": resolve_firmware_path(args.nucleo_firmware),
    }
    port_overrides = {
        "nrf": args.nrf_port,
        "nucleo": args.nucleo_port,
    }
    baudrates = {
        "nrf": args.nrf_baudrate,
        "nucleo": args.nucleo_baudrate,
    }
    expected_text = {
        "nrf": args.nrf_expect,
        "nucleo": args.nucleo_expect,
    }

    print("\nStage 0 - Board and toolchain validation")
    print(f"Checking: {', '.join(board.name for board in boards_to_check)}")

    pyocd_ok = check_pyocd_installed()
    pyserial_ok = check_pyserial_installed()
    if not pyocd_ok:
        sys.exit(1)

    probes = check_probes(boards_to_check)
    target_ok = check_target_packs(boards_to_check, auto_install=args.install_packs)
    serial_ports = check_virtual_com_ports(boards_to_check, port_overrides, pyserial_ok)

    summary_items: list[SummaryItem] = []
    manual_items: list[str] = []

    for board in boards_to_check:
        probe = probes.get(board.key)
        target_available = target_ok.get(board.key, False)
        port = serial_ports.get(board.key)

        conn_ok = check_connection(board, probe, target_available)
        flash_ok = flash_firmware(board, probe, target_available, firmware_paths[board.key])
        uart_ok = None
        if firmware_paths[board.key] is not None:
            uart_ok = read_uart_output(
                board,
                port,
                baudrates[board.key],
                args.serial_read_seconds,
                expected_text[board.key],
            )
        recover_ok = run_nrf_recover_test(
            board,
            probe,
            target_available,
            args.nrf_recover_test,
        )

        summary_items.extend(
            [
                SummaryItem(f"{board.name}: probe visible", SUMMARY_PASS if probe else SUMMARY_FAIL),
                SummaryItem(
                    f"{board.name}: target '{board.pyocd_target}' available",
                    SUMMARY_PASS if target_available else SUMMARY_FAIL,
                ),
                SummaryItem(
                    f"{board.name}: connect + read register",
                    SUMMARY_PASS if conn_ok else SUMMARY_FAIL,
                ),
                SummaryItem(
                    f"{board.name}: virtual COM port visible",
                    SUMMARY_PASS if port else SUMMARY_FAIL,
                ),
            ]
        )

        if flash_ok is None:
            summary_items.append(
                SummaryItem(
                    f"{board.name}: flash known-good reference firmware",
                    SUMMARY_MANUAL,
                    f"provide {board_arg_name(board, 'firmware')} to automate this step",
                )
            )
            manual_items.append(
                f"{board.name}: flash a known-good reference image and verify it is the intended baseline artifact."
            )
        else:
            summary_items.append(
                SummaryItem(
                    f"{board.name}: flash known-good reference firmware",
                    SUMMARY_PASS if flash_ok else SUMMARY_FAIL,
                )
            )

        if firmware_paths[board.key] is None:
            summary_items.append(
                SummaryItem(
                    f"{board.name}: UART output observed",
                    SUMMARY_MANUAL,
                    f"requires flashed reference firmware and optional {board_arg_name(board, 'expect')}",
                )
            )
            manual_items.append(
                f"{board.name}: confirm the reference firmware prints over UART on the expected port and baudrate."
            )
        elif uart_ok is None:
            summary_items.append(
                SummaryItem(f"{board.name}: UART output observed", SUMMARY_MANUAL)
            )
        else:
            summary_items.append(
                SummaryItem(
                    f"{board.name}: UART output observed",
                    SUMMARY_PASS if uart_ok else SUMMARY_FAIL,
                )
            )
            if expected_text[board.key] is None:
                manual_items.append(
                    f"{board.name}: confirm the captured UART text is the expected reference-firmware output, not just arbitrary bytes."
                )

        if board.requires_recover_validation:
            if recover_ok is None:
                summary_items.append(
                    SummaryItem(
                        f"{board.name}: recover / unlock cycle proven",
                        SUMMARY_MANUAL,
                        "run with --nrf-recover-test to automate the destructive check",
                    )
                )
                manual_items.append(
                    f"{board.name}: prove an nRF recover/unlock cycle on this machine. This erases flash, so it is opt-in."
                )
            else:
                summary_items.append(
                    SummaryItem(
                        f"{board.name}: recover / unlock cycle proven",
                        SUMMARY_PASS if recover_ok else SUMMARY_FAIL,
                    )
                )

        manual_items.append(
            f"{board.name}: confirm the visible debug probe and COM port are exposed by the same physical USB connection."
        )

    automated_ok = print_summary(summary_items, manual_items)
    sys.exit(0 if automated_ok else 1)


if __name__ == "__main__":
    main()
