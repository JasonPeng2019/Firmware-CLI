from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from typing import Callable, Protocol


class BoardLike(Protocol):
    board_id: str
    display_name: str
    mcu_family: str
    probe_family: str
    serial_hint_terms: tuple[str, ...]


class ProbeLike(Protocol):
    uid: str


@dataclass(frozen=True)
class SerialPortInfo:
    device: str
    description: str
    manufacturer: str
    product: str
    interface: str
    hwid: str
    serial_number: str = ""
    location: str = ""
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
                self.serial_number,
                self.location,
                "" if self.vid is None else f"{self.vid:04x}",
                "" if self.pid is None else f"{self.pid:04x}",
            ]
        ).lower()


@dataclass(frozen=True)
class SerialResolution:
    port: SerialPortInfo | None
    note: str


@dataclass(frozen=True)
class NordicComEntry:
    probe_serial: str
    port: str
    label: str


@dataclass(frozen=True)
class StlinkComEntry:
    probe_serial: str
    port: str
    location: str
    description: str
    manufacturer: str


RunCommand = Callable[[list[str]], tuple[int, str, str]]


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def is_interactive_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def normalize_port_name(port: str) -> str:
    normalized = port.strip()
    if normalized.startswith("\\\\.\\"):
        normalized = normalized[4:]
    return normalized.lower()


def _normalized_probe_uid(uid: str) -> str:
    return re.sub(r"[^0-9a-z]", "", uid.lower())


def _normalized_serial(serial: str) -> str:
    return re.sub(r"[^0-9a-z]", "", serial.lower())


def _numeric_serial_variants(value: str) -> set[str]:
    normalized = _normalized_serial(value)
    variants = {normalized}
    digits = re.sub(r"\D", "", normalized)
    if digits:
        variants.add(digits)
        variants.add(digits.lstrip("0") or "0")
    return {item for item in variants if item}


def probe_uid_matches_serial(uid: str, serial: str) -> bool:
    if not uid or not serial:
        return False

    uid_variants = _numeric_serial_variants(uid)
    serial_variants = _numeric_serial_variants(serial)
    if uid_variants & serial_variants:
        return True

    normalized_uid = _normalized_probe_uid(uid)
    normalized_serial = _normalized_serial(serial)
    return normalized_uid.endswith(normalized_serial) or normalized_serial.endswith(normalized_uid)


def score_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def parse_nrfjprog_com_output(text: str) -> list[NordicComEntry]:
    entries: list[NordicComEntry] = []
    pattern = re.compile(r"^(?P<serial>\S+)\s+(?P<port>\S+)\s+(?P<label>VCOM\d+)\s*$", re.IGNORECASE)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if not match:
            continue
        entries.append(
            NordicComEntry(
                probe_serial=match.group("serial"),
                port=match.group("port"),
                label=match.group("label").upper(),
            )
        )
    return entries


def parse_stm32_programmer_list_output(text: str) -> list[StlinkComEntry]:
    entries: list[StlinkComEntry] = []
    in_uart_section = False
    current: dict[str, str] = {}
    known_keys = {"ST-LINK SN", "Port", "Location", "Description", "Manufacturer"}

    def flush() -> None:
        if current.get("ST-LINK SN") and current.get("Port"):
            entries.append(
                StlinkComEntry(
                    probe_serial=current["ST-LINK SN"],
                    port=current["Port"],
                    location=current.get("Location", ""),
                    description=current.get("Description", ""),
                    manufacturer=current.get("Manufacturer", ""),
                )
            )
        current.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("====="):
            if in_uart_section:
                flush()
            in_uart_section = line.lower().startswith("===== uart interface")
            continue
        if not in_uart_section or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key not in known_keys:
            continue
        if key == "ST-LINK SN" and current.get("ST-LINK SN") and current.get("Port"):
            flush()
        current[key] = value

    if in_uart_section:
        flush()

    return entries


def _find_port_by_name(ports: list[SerialPortInfo], port_name: str) -> SerialPortInfo | None:
    normalized = normalize_port_name(port_name)
    for port in ports:
        if normalize_port_name(port.device) == normalized:
            return port
    return None


def _candidate_list_text(candidates: list[SerialPortInfo]) -> str:
    lines = []
    for idx, port in enumerate(candidates, start=1):
        detail = port.description or "(no description)"
        extras = [part for part in [port.manufacturer, port.serial_number, port.location] if part]
        if extras:
            detail = f"{detail} :: {' :: '.join(extras)}"
        lines.append(f"      {idx}. {port.device} :: {detail}")
    return "\n".join(lines)


def _manual_rerun_guidance(board: BoardLike, candidates: list[SerialPortInfo]) -> str:
    guidance = f"use --port {board.board_id}=PORT"
    if candidates:
        guidance += f"; candidate ports:\n{_candidate_list_text(candidates)}"
    return guidance


def _prompt_for_candidate(board: BoardLike, candidates: list[SerialPortInfo]) -> SerialResolution:
    print(f"  Multiple candidate serial ports remain for {board.display_name}:")
    print(_candidate_list_text(candidates))
    print(f"  Choose a port for {board.board_id} or press Enter to abort.")
    try:
        response = input("  Selection: ").strip()
    except EOFError:
        response = ""

    if not response:
        return SerialResolution(None, f"selection aborted; {_manual_rerun_guidance(board, candidates)}")
    if not response.isdigit():
        return SerialResolution(None, f"invalid selection '{response}'; {_manual_rerun_guidance(board, candidates)}")

    selected_index = int(response)
    if not 1 <= selected_index <= len(candidates):
        return SerialResolution(None, f"selection {selected_index} is out of range; {_manual_rerun_guidance(board, candidates)}")

    selected = candidates[selected_index - 1]
    return SerialResolution(selected, f"user selected {selected.device}")


def _generic_candidates(board: BoardLike, ports: list[SerialPortInfo], probe: ProbeLike | None) -> list[SerialPortInfo]:
    scored: list[tuple[int, SerialPortInfo]] = []
    for port in ports:
        score = score_terms(port.searchable_text, board.serial_hint_terms)
        if probe and probe.uid:
            if probe_uid_matches_serial(probe.uid, port.serial_number):
                score += 100
            elif _normalized_probe_uid(probe.uid) and _normalized_probe_uid(probe.uid) in port.searchable_text:
                score += 10
        if score > 0:
            scored.append((score, port))

    if not scored:
        return []

    best_score = max(score for score, _ in scored)
    return [port for score, port in scored if score == best_score]


def _resolve_nordic_serial(
    board: BoardLike,
    ports: list[SerialPortInfo],
    probe: ProbeLike | None,
    run_cmd: RunCommand,
) -> SerialResolution | None:
    if not board.mcu_family.lower().startswith("nrf") or board.probe_family.lower() != "jlink":
        return None
    if not command_exists("nrfjprog"):
        return None

    rc, out, _ = run_cmd(["nrfjprog", "--com"])
    if rc != 0:
        return None

    entries = parse_nrfjprog_com_output(out)
    if not entries:
        return None

    matching = entries
    if probe and probe.uid:
        probe_matches = [entry for entry in entries if probe_uid_matches_serial(probe.uid, entry.probe_serial)]
        if probe_matches:
            matching = probe_matches

    matching = sorted(
        matching,
        key=lambda entry: (0 if entry.label.upper() == "VCOM0" else 1, normalize_port_name(entry.port)),
    )
    for entry in matching:
        port = _find_port_by_name(ports, entry.port)
        if port:
            return SerialResolution(port, f"resolved via nrfjprog --com ({entry.label})")
    return None


def _resolve_stlink_serial(
    board: BoardLike,
    ports: list[SerialPortInfo],
    probe: ProbeLike | None,
    run_cmd: RunCommand,
) -> SerialResolution | None:
    if board.probe_family.lower() != "stlink":
        return None
    if not command_exists("STM32_Programmer_CLI"):
        return None

    rc, out, _ = run_cmd(["STM32_Programmer_CLI", "-l"])
    if rc != 0:
        return None

    entries = parse_stm32_programmer_list_output(out)
    if not entries:
        return None

    matching = entries
    if probe and probe.uid:
        probe_matches = [entry for entry in entries if probe_uid_matches_serial(probe.uid, entry.probe_serial)]
        if probe_matches:
            matching = probe_matches

    resolved: list[SerialPortInfo] = []
    for entry in matching:
        port = _find_port_by_name(ports, entry.port)
        if port:
            resolved.append(port)

    unique: dict[str, SerialPortInfo] = {normalize_port_name(port.device): port for port in resolved}
    if len(unique) == 1:
        return SerialResolution(next(iter(unique.values())), "resolved via STM32_Programmer_CLI -l")
    return None


def resolve_serial_port(
    board: BoardLike,
    ports: list[SerialPortInfo],
    probe: ProbeLike | None,
    override: str | None,
    allow_single_fallback: bool,
    run_cmd: RunCommand,
    interactive: bool,
) -> SerialResolution:
    if override:
        port = _find_port_by_name(ports, override)
        if port:
            return SerialResolution(port, "")
        return SerialResolution(None, f"override port '{override}' not found")

    vendor_resolution = _resolve_nordic_serial(board, ports, probe, run_cmd)
    if vendor_resolution is None:
        vendor_resolution = _resolve_stlink_serial(board, ports, probe, run_cmd)
    if vendor_resolution is not None:
        return vendor_resolution

    candidates = _generic_candidates(board, ports, probe)
    if len(candidates) == 1:
        return SerialResolution(candidates[0], "")

    if allow_single_fallback and len(ports) == 1:
        return SerialResolution(ports[0], "single connected serial port assumed for this board")

    if candidates:
        if interactive:
            return _prompt_for_candidate(board, candidates)
        return SerialResolution(None, f"multiple matching serial ports found; {_manual_rerun_guidance(board, candidates)}")

    if interactive and ports:
        return _prompt_for_candidate(board, ports)
    if ports:
        return SerialResolution(None, f"no matching serial port found; {_manual_rerun_guidance(board, ports)}")
    return SerialResolution(None, "no serial ports detected")
