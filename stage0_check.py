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

from pyocd_debug_mcp.local_env import load_local_env

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
INFO = "INFO"

SUMMARY_PASS = "pass"
SUMMARY_FAIL = "fail"
SUMMARY_MANUAL = "manual"

DEFAULT_BOARD_CONFIG_DIR = Path(__file__).resolve().parent / "boards"  # PROJECT-DEFINED (repo layout)

PROBE_FAMILY_LABELS = {
    "jlink": "SEGGER J-Link",
    "stlink": "ST-Link",
    "cmsisdap": "CMSIS-DAP",
}

PROBE_FAMILY_HINTS = {
    "jlink": {"j-link", "jlink", "segger"},
    "stlink": {"st-link", "stlink"},
    "cmsisdap": {"cmsis-dap", "cmsisdap", "daplink"},
}

load_local_env()


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class BoardConfig:
    board_id: str
    display_name: str
    mcu_family: str
    probe_family: str
    pyocd_target: str
    pack_name: str
    probe_type: str
    probe_hint_terms: tuple[str, ...]
    serial_hint_terms: tuple[str, ...]
    test_addr: int
    default_baudrate: int = 115200
    uart_note: str = ""
    requires_recover_validation: bool = False
    recover_command: str | None = None
    expected_uart_substring: str | None = None
    source_path: Path | None = None


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


def normalize_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]
        if value.strip():
            return [value.strip()]
        return []
    if isinstance(value, (list, tuple)):
        output = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                output.append(text)
        return output
    raise ConfigError(f"Expected a string or list, got {type(value).__name__}")


def parse_int(value: object, field_name: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ConfigError(f"Field '{field_name}' must be an int or numeric string")


def tokenize_hint_text(*values: str) -> set[str]:
    terms: set[str] = set()
    for value in values:
        for token in re.findall(r"[a-z0-9]+", value.lower()):
            if len(token) >= 3:
                terms.add(token)
    return terms


def default_test_address(mcu_family: str) -> int:
    lowered = mcu_family.lower()
    if lowered.startswith("nrf"):
        return 0x10000000  # HW-FIXED (nRF FICR base; safe readable smoke-test region)
    if lowered.startswith("stm32"):
        return 0x08000000  # HW-FIXED (STM32 flash base; safe readable smoke-test region)
    raise ConfigError("Custom board config must set 'test_read_address' for non-nRF/non-STM32 families")


def load_board_config_document(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise ConfigError(
                f"PyYAML is required to load {path.name}. Install it with 'pip install pyyaml' or use JSON."
            ) from exc
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ConfigError(f"{path} must contain a single YAML object")
        return data
    raise ConfigError(f"Unsupported board config format for {path}. Use .json, .yaml, or .yml.")


def make_board_config(raw: dict, source_path: Path | None) -> BoardConfig:
    forbidden_session_fields = {
        "project_path",
        "user_project_path",
        "build_command",
        "user_build_command",
        "artifact_path",
        "output_artifact_path",
        "user_output_artifact",
        "reference_firmware_path",
    }
    present_forbidden = sorted(field for field in forbidden_session_fields if field in raw)
    if present_forbidden:
        raise ConfigError(
            "Board config contains project/session-scoped fields that do not belong in boards/<board>.yaml: "
            f"{', '.join(present_forbidden)}. Supply these later as runtime/session inputs instead."
        )

    required_fields = ["board_id", "display_name", "mcu_family", "probe_family", "pyocd_target"]
    missing = [field for field in required_fields if not raw.get(field)]
    if missing:
        raise ConfigError(f"Missing required board config fields: {', '.join(missing)}")

    board_id = str(raw["board_id"]).strip().lower()
    if not re.fullmatch(r"[a-z0-9_]+", board_id):
        raise ConfigError("board_id must contain only lowercase letters, numbers, and underscores")

    display_name = str(raw["display_name"]).strip()
    mcu_family = str(raw["mcu_family"]).strip().lower()
    probe_family = str(raw["probe_family"]).strip().lower()
    pyocd_target = str(raw["pyocd_target"]).strip()
    pack_name = str(raw.get("pack_name") or pyocd_target).strip()
    probe_type = str(raw.get("probe_type") or PROBE_FAMILY_LABELS.get(probe_family, probe_family)).strip()

    if raw.get("test_read_address") is None:
        test_addr = default_test_address(mcu_family)
    else:
        test_addr = parse_int(raw["test_read_address"], "test_read_address")

    default_baudrate = parse_int(raw.get("serial_baudrate", 115200), "serial_baudrate")
    uart_note = str(raw.get("uart_note", "")).strip()

    explicit_recover = raw.get("requires_recover_validation")
    if explicit_recover is None:
        requires_recover_validation = mcu_family.startswith("nrf")
    else:
        requires_recover_validation = bool(explicit_recover)

    recover_command = raw.get("recover_command")
    if recover_command is not None:
        recover_command = str(recover_command).strip()
    elif requires_recover_validation:
        recover_command = "nrf recover"

    probe_terms = set(normalize_list(raw.get("probe_hint_terms")))
    serial_terms = set(normalize_list(raw.get("serial_hint_terms")))
    default_terms = tokenize_hint_text(board_id, display_name, mcu_family, pyocd_target)
    probe_terms.update(default_terms)
    serial_terms.update(default_terms)
    probe_terms.update(PROBE_FAMILY_HINTS.get(probe_family, set()))
    serial_terms.update(PROBE_FAMILY_HINTS.get(probe_family, set()))
    serial_terms.add("virtual com")

    expected_uart_substring = None
    if raw.get("expected_uart_substring"):
        expected_uart_substring = str(raw["expected_uart_substring"]).strip()
    else:
        patterns = normalize_list(raw.get("reference_uart_patterns"))
        if patterns:
            expected_uart_substring = patterns[0]

    return BoardConfig(
        board_id=board_id,
        display_name=display_name,
        mcu_family=mcu_family,
        probe_family=probe_family,
        pyocd_target=pyocd_target,
        pack_name=pack_name,
        probe_type=probe_type,
        probe_hint_terms=tuple(sorted(term.lower() for term in probe_terms if term)),
        serial_hint_terms=tuple(sorted(term.lower() for term in serial_terms if term)),
        test_addr=test_addr,
        default_baudrate=default_baudrate,
        uart_note=uart_note,
        requires_recover_validation=requires_recover_validation,
        recover_command=recover_command,
        expected_uart_substring=expected_uart_substring,
        source_path=source_path,
    )


def load_board_configs_from_paths(paths: list[Path]) -> list[BoardConfig]:
    boards: list[BoardConfig] = []
    for path in paths:
        if not path.exists():
            raise ConfigError(f"Board config not found: {path}")
        document = load_board_config_document(path)
        boards.append(make_board_config(document, path))
    return boards


def iter_board_config_paths(board_config_dir: Path) -> list[Path]:
    if not board_config_dir.exists():
        raise ConfigError(f"Board config directory not found: {board_config_dir}")
    if not board_config_dir.is_dir():
        raise ConfigError(f"Board config path is not a directory: {board_config_dir}")

    paths = [
        path.resolve()
        for path in sorted(board_config_dir.iterdir())
        if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml"}
    ]
    if not paths:
        raise ConfigError(f"No board config files found in: {board_config_dir}")
    return paths


def load_default_board_configs(board_config_dir: Path) -> list[BoardConfig]:
    default_paths = [
        path
        for path in iter_board_config_paths(board_config_dir)
        if not path.stem.startswith("example_")
    ]
    if not default_paths:
        raise ConfigError(
            f"No non-example board config files found in: {board_config_dir}. "
            "Add board files or pass --board-config."
        )
    return load_board_configs_from_paths(default_paths)


def merge_board_lists(builtins: list[BoardConfig], customs: list[BoardConfig]) -> list[BoardConfig]:
    merged: list[BoardConfig] = []
    seen: set[str] = set()
    for board in builtins + customs:
        if board.board_id in seen:
            raise ConfigError(f"Duplicate board_id detected: {board.board_id}")
        seen.add(board.board_id)
        merged.append(board)
    return merged


def select_boards_by_id(boards: list[BoardConfig], requested_ids: list[str]) -> list[BoardConfig]:
    if not requested_ids:
        return boards

    requested = [board_id.strip().lower() for board_id in requested_ids if board_id.strip()]
    selected = [board for board in boards if board.board_id in requested]
    missing = sorted(set(requested) - {board.board_id for board in selected})
    if missing:
        raise ConfigError(f"Requested board_id values not found: {', '.join(missing)}")
    return selected


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
        _, out, _ = run(["pyocd", "list"])
        probes: list[ProbeInfo] = []
        for line in out.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.lower().startswith("no"):
                probes.append(ProbeInfo(uid="", description=stripped.lower(), raw=stripped))
        return probes

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
        return None, "multiple matching probes found; disconnect extras or refine probe_hint_terms"

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
            check(False, f"{board.display_name} ({board.probe_type}) probe not uniquely identifiable: {note}")
        results[board.board_id] = probe

    return results


def check_target_packs(boards_to_check: list[BoardConfig], auto_install: bool) -> dict[str, bool]:
    header("CMSIS-Pack / target availability")
    _, out, _ = run(["pyocd", "list", "--targets"])
    installed_targets = out.lower()

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
                _, refreshed, _ = run(["pyocd", "list", "--targets"])
                ok = board.pyocd_target.lower() in refreshed.lower()
                check(ok, f"Pack installed, target '{board.pyocd_target}' now {'available' if ok else 'still missing'}")
                results[board.board_id] = ok
            else:
                check(False, f"Pack install failed - try manually: pyocd pack find {board.pack_name}")
                results[board.board_id] = False
        else:
            print(f"      Fix: pyocd pack find {board.pack_name}")
            print(f"           pyocd pack install {board.pack_name}")
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
    cmd.extend(["-c", f"read32 {hex(board.test_addr)} 1"])
    print(f"  Attempting: {' '.join(cmd)}")
    rc, out, err = run(cmd)

    if rc == 0 and out.strip():
        check(True, f"Connected and read {hex(board.test_addr)}: {out.strip()}")
        return True

    combined = f"{out}\n{err}".lower()
    if "approtect" in combined or "access port" in combined or "locked" in combined:
        log(WARN, f"{board.display_name} appears access-protected.")
        if board.recover_command:
            print(f'      Recover with: pyocd cmd -t {board.pyocd_target} -c "{board.recover_command}"')
        return False

    if "no connected" in combined or "no target" in combined or "unable to connect" in combined:
        check(False, "pyOCD found the probe but could not connect to the target MCU")
        print("      - Is the board powered?")
        print("      - Is the USB cable a data cable (not charge-only)?")
        if board.probe_family == "jlink":
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
        return None, "multiple matching serial ports found; use --port BOARD_ID=PORT or refine serial_hint_terms"

    if allow_single_fallback and len(ports) == 1:
        return ports[0], "single connected serial port assumed for this board"

    return None, "no matching serial port found"


def check_virtual_com_ports(
    boards_to_check: list[BoardConfig],
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
        extras = " ".join(part for part in [port.manufacturer, port.product, port.interface] if part)
        if extras:
            desc = f"{desc} :: {extras}"
        print(f"    - {port.device} :: {desc}")

    results: dict[str, SerialPortInfo | None] = {}
    allow_single_fallback = len(ports) == 1 and len(boards_to_check) == 1
    for board in boards_to_check:
        port, note = pick_serial_port(board, ports, port_overrides.get(board.board_id), allow_single_fallback)
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
    return False


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
        check(ok, f"UART output {'matched' if ok else 'did not match'} expected text on {port.device}")
        if excerpt:
            print(f"      Captured: {excerpt}")
        return ok

    ok = bool(text.strip())
    check(ok, f"UART produced {'some output' if ok else 'no output'} on {port.device}")
    if excerpt:
        print(f"      Captured: {excerpt}")
    return ok


def run_recover_test(board: BoardConfig, probe: ProbeInfo | None, target_ok: bool, enabled: bool) -> bool | None:
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
        print("  Automated checks passed, but full Stage 0 is not complete until the manual items are validated.")
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
        "--serial-read-seconds",
        type=float,
        default=3.0,
        help="How long to listen for UART output after opening the port.",
    )
    return parser


def collect_overrides(args: argparse.Namespace) -> tuple[dict[str, str], dict[str, Path], dict[str, str], dict[str, int], set[str]]:
    port_overrides = parse_key_value(args.port, "--port")
    reference_firmware_overrides = {
        board_id: resolve_firmware_path(path_text)
        for board_id, path_text in parse_key_value(args.reference_firmware, "--reference-firmware").items()
    }
    expect_overrides = parse_key_value(args.expect, "--expect")
    baudrate_overrides = {
        board_id: parse_int(value, "--baudrate")
        for board_id, value in parse_key_value(args.baudrate, "--baudrate").items()
    }
    recover_tests = {board_id.strip().lower() for board_id in args.recover_test if board_id.strip()}

    return port_overrides, reference_firmware_overrides, expect_overrides, baudrate_overrides, recover_tests


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        board_config_dir = Path(args.board_config_dir).expanduser().resolve()
        default_boards = load_default_board_configs(board_config_dir)
        custom_board_paths = [Path(raw_path).expanduser().resolve() for raw_path in args.board_config]
        custom_boards = load_board_configs_from_paths(custom_board_paths)
        boards_to_check = merge_board_lists(default_boards, custom_boards)
        boards_to_check = select_boards_by_id(boards_to_check, args.board_id)
        if not boards_to_check:
            raise ConfigError("No boards selected. Add board configs or pass --board-id for an existing board.")
        port_overrides, reference_firmware_overrides, expect_overrides, baudrate_overrides, recover_tests = collect_overrides(args)
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
    serial_ports = check_virtual_com_ports(boards_to_check, port_overrides, pyserial_ok)

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
        flash_ok = flash_reference_firmware(board, probe, target_available, reference_firmware_path)
        uart_ok = None
        if reference_firmware_path is not None:
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
            board.board_id in recover_tests,
        )

        summary_items.extend(
            [
                SummaryItem(f"{board.display_name}: probe visible", SUMMARY_PASS if probe else SUMMARY_FAIL),
                SummaryItem(
                    f"{board.display_name}: target '{board.pyocd_target}' available",
                    SUMMARY_PASS if target_available else SUMMARY_FAIL,
                ),
                SummaryItem(
                    f"{board.display_name}: connect + read register",
                    SUMMARY_PASS if conn_ok else SUMMARY_FAIL,
                ),
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

        manual_items.append(
            f"{board.display_name}: confirm the visible debug probe and COM port are exposed by the same physical USB connection."
        )

    automated_ok = print_summary(summary_items, manual_items)
    sys.exit(0 if automated_ok else 1)


if __name__ == "__main__":
    main()
