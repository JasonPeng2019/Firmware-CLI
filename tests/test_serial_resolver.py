from __future__ import annotations

from dataclasses import dataclass

from pyocd_debug_mcp import serial_resolver
from pyocd_debug_mcp.serial_resolver import (
    SerialPortInfo,
    parse_nrfjprog_com_output,
    parse_stm32_programmer_list_output,
    resolve_serial_port,
)


@dataclass(frozen=True)
class FakeBoard:
    board_id: str
    display_name: str
    mcu_family: str
    probe_family: str
    serial_hint_terms: tuple[str, ...]


@dataclass(frozen=True)
class FakeProbe:
    uid: str


def make_port(device: str, description: str, serial_number: str = "", location: str = "") -> SerialPortInfo:
    return SerialPortInfo(
        device=device,
        description=description,
        manufacturer="TestVendor",
        product="TestProduct",
        interface="",
        hwid=f"SER={serial_number} LOCATION={location}",
        serial_number=serial_number,
        location=location,
    )


def test_parse_nrfjprog_com_output_dual_vcom() -> None:
    text = "\n1050237188 COM14 VCOM0\n1050237188 COM15 VCOM1\n"
    entries = parse_nrfjprog_com_output(text)

    assert [(entry.probe_serial, entry.port, entry.label) for entry in entries] == [
        ("1050237188", "COM14", "VCOM0"),
        ("1050237188", "COM15", "VCOM1"),
    ]


def test_parse_stm32_programmer_list_output_uart_section() -> None:
    text = """
===== STLink Interface =====
-------- Connected ST-LINK Probes List --------
ST-Link Probe 0 :
 ST-LINK SN : 002B00213037510B35333131
-----------------------------------------------
===== UART Interface =====
Total number of serial ports available: 1
Board Name : STLINK-V3SET
ST-LINK SN: 002B00213037510B35333131
Port: COM129
Location: \\\\.\\COM129
Description: STMicroelectronics STLink Virtual COM Port
Manufacturer: STMicroelectronics
"""
    entries = parse_stm32_programmer_list_output(text)

    assert len(entries) == 1
    assert entries[0].probe_serial == "002B00213037510B35333131"
    assert entries[0].port == "COM129"


def test_malformed_vendor_output_yields_no_entries() -> None:
    assert parse_nrfjprog_com_output("not a mapping") == []
    assert parse_stm32_programmer_list_output("===== UART Interface =====\nPort only") == []


def test_port_override_wins() -> None:
    board = FakeBoard("custom", "Custom", "custom", "cmsisdap", ("uart",))
    ports = [make_port("COM3", "UART Port"), make_port("COM4", "UART Port")]

    result = resolve_serial_port(
        board=board,
        ports=ports,
        probe=None,
        override="COM4",
        allow_single_fallback=False,
        run_cmd=lambda cmd: (127, "", ""),
        interactive=False,
    )

    assert result.port is not None
    assert result.port.device == "COM4"


def test_nordic_dual_port_prefers_vcom0(monkeypatch) -> None:
    board = FakeBoard(
        "nrf52840dk",
        "nRF52840-DK",
        "nrf52840",
        "jlink",
        ("jlink", "segger", "virtual com"),
    )
    probe = FakeProbe("001050263657")
    ports = [
        make_port("COM7", "JLink CDC UART Port", serial_number="001050263657", location="1-3:x.2"),
        make_port("COM8", "JLink CDC UART Port", serial_number="001050263657", location="1-3:x.0"),
    ]

    monkeypatch.setattr(
        serial_resolver,
        "resolve_command_path",
        lambda name: "nrfjprog" if name == "nrfjprog" else None,
    )

    result = resolve_serial_port(
        board=board,
        ports=ports,
        probe=probe,
        override=None,
        allow_single_fallback=False,
        run_cmd=lambda cmd: (0, "1050263657 COM8 VCOM0\n1050263657 COM7 VCOM1\n", ""),
        interactive=False,
    )

    assert result.port is not None
    assert result.port.device == "COM8"
    assert "nrfjprog" in result.note


def test_stlink_resolves_from_cubeprogrammer(monkeypatch) -> None:
    board = FakeBoard(
        "nucleo_l476rg", "Nucleo-L476RG", "stm32l476", "stlink", ("st-link", "stm32")
    )
    probe = FakeProbe("002B00213037510B35333131")
    ports = [
        make_port(
            "COM9",
            "STMicroelectronics STLink Virtual COM Port",
            serial_number="002B00213037510B35333131",
        ),
        make_port("COM10", "USB Serial Device", serial_number="other"),
    ]
    output = """
===== UART Interface =====
Total number of serial ports available: 1
Board Name : STLINK-V3SET
ST-LINK SN: 002B00213037510B35333131
Port: COM9
Location: \\\\.\\COM9
Description: STMicroelectronics STLink Virtual COM Port
Manufacturer: STMicroelectronics
"""

    monkeypatch.setattr(
        serial_resolver,
        "resolve_command_path",
        lambda name: "STM32_Programmer_CLI" if name == "STM32_Programmer_CLI" else None,
    )

    result = resolve_serial_port(
        board=board,
        ports=ports,
        probe=probe,
        override=None,
        allow_single_fallback=False,
        run_cmd=lambda cmd: (0, output, ""),
        interactive=False,
    )

    assert result.port is not None
    assert result.port.device == "COM9"
    assert "STM32_Programmer_CLI" in result.note


def test_vendor_tool_missing_falls_back_to_generic(monkeypatch) -> None:
    board = FakeBoard("nrf52840dk", "nRF52840-DK", "nrf52840", "jlink", ("segger", "uart"))
    ports = [make_port("COM7", "Segger UART Port")]

    monkeypatch.setattr(serial_resolver, "resolve_command_path", lambda name: None)

    result = resolve_serial_port(
        board=board,
        ports=ports,
        probe=None,
        override=None,
        allow_single_fallback=True,
        run_cmd=lambda cmd: (127, "", ""),
        interactive=False,
    )

    assert result.port is not None
    assert result.port.device == "COM7"


def test_single_port_fallback_no_regression() -> None:
    board = FakeBoard("solo", "Solo Board", "custom", "cmsisdap", tuple())
    ports = [make_port("COM11", "Only Port")]

    result = resolve_serial_port(
        board=board,
        ports=ports,
        probe=None,
        override=None,
        allow_single_fallback=True,
        run_cmd=lambda cmd: (127, "", ""),
        interactive=False,
    )

    assert result.port is not None
    assert result.port.device == "COM11"
    assert "single connected serial port" in result.note


def test_ambiguous_unsupported_board_prompts_in_interactive_mode(monkeypatch) -> None:
    board = FakeBoard("weird", "Weird Board", "custom", "cmsisdap", ("uart",))
    ports = [make_port("COM1", "UART Port A"), make_port("COM2", "UART Port B")]

    monkeypatch.setattr("builtins.input", lambda prompt="": "2")

    result = resolve_serial_port(
        board=board,
        ports=ports,
        probe=None,
        override=None,
        allow_single_fallback=False,
        run_cmd=lambda cmd: (127, "", ""),
        interactive=True,
    )

    assert result.port is not None
    assert result.port.device == "COM2"
    assert "user selected" in result.note


def test_ambiguous_unsupported_board_fails_non_interactive() -> None:
    board = FakeBoard("weird", "Weird Board", "custom", "cmsisdap", ("uart",))
    ports = [make_port("COM1", "UART Port A"), make_port("COM2", "UART Port B")]

    result = resolve_serial_port(
        board=board,
        ports=ports,
        probe=None,
        override=None,
        allow_single_fallback=False,
        run_cmd=lambda cmd: (127, "", ""),
        interactive=False,
    )

    assert result.port is None
    assert "--port weird=PORT" in result.note
