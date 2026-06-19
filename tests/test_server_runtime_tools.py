from __future__ import annotations

from pathlib import Path

import pytest

from pyocd_debug_mcp import server
from pyocd_debug_mcp.adapters.swd_interface import TargetSessionHandle
from pyocd_debug_mcp.board_config import BoardConfig
from pyocd_debug_mcp.probe_inventory import ProbeInfo, ProbeResolution
from pyocd_debug_mcp.serial_resolver import SerialPortInfo
from pyocd_debug_mcp.services.uart_capture import UARTCaptureResult


def make_board() -> BoardConfig:
    return BoardConfig(
        board_id="nrf52833dk",
        display_name="nRF52833 DK",
        mcu_family="nrf52833",
        probe_family="jlink",
        pyocd_target="nrf52833",
        pack_name="nrf52833",
        probe_type="SEGGER J-Link",
        probe_hint_terms=("jlink", "segger"),
        serial_hint_terms=("jlink", "segger", "virtual com"),
        test_addr=0x10000000,
        silicon_id_addr=0x10000100,
        silicon_id_expected=0x00052833,
        silicon_id_label="FICR.INFO.PART",
        default_baudrate=115200,
        requires_recover_validation=True,
        recover_mode="nrf_pyocd_unlock",
        expected_uart_substring="boot ok",
    )


def make_handle(board: BoardConfig | None) -> TargetSessionHandle:
    session_board = type("SessionBoard", (), {"name": board.display_name if board else "Raw Target"})()
    session = type("Session", (), {"board": session_board if board else None})()
    return TargetSessionHandle(
        session=session,
        board=board,
        probe_uid="probe-123",
        route_used="pyocd-native",
        target_override=board.pyocd_target if board else "raw-target",
    )


@pytest.fixture(autouse=True)
def restore_session_handle():
    original = server._session_handle
    try:
        yield
    finally:
        server._session_handle = original


def test_flash_firmware_uses_default_board_artifact(monkeypatch, tmp_path: Path) -> None:
    board = make_board()
    handle = make_handle(board)
    artifact = tmp_path / "firmware.hex"
    artifact.write_text("hex", encoding="utf-8")
    seen: dict[str, object] = {}

    server._session_handle = handle
    monkeypatch.setattr(
        server,
        "resolve_reference_artifacts",
        lambda board_arg: type("Pair", (), {"flash_artifact": artifact})(),
    )

    def fake_flash(handle_arg, path_arg, *, halt_after_reset: bool):
        seen["handle"] = handle_arg
        seen["path"] = path_arg
        seen["halt_after_reset"] = halt_after_reset
        return path_arg

    monkeypatch.setattr(server.target_control, "flash_firmware", fake_flash)

    result = server.flash_firmware()

    assert seen["handle"] is handle
    assert seen["path"] == artifact
    assert seen["halt_after_reset"] is False
    assert result == f"Flashed {artifact} via pyocd-native; target left running."


def test_flash_firmware_uses_explicit_path_without_board_config(
    monkeypatch,
    tmp_path: Path,
) -> None:
    handle = make_handle(None)
    artifact = tmp_path / "custom.elf"
    artifact.write_text("elf", encoding="utf-8")
    seen: dict[str, object] = {}

    server._session_handle = handle

    def fake_flash(handle_arg, path_arg, *, halt_after_reset: bool):
        seen["path"] = path_arg
        seen["halt_after_reset"] = halt_after_reset
        return path_arg

    monkeypatch.setattr(server.target_control, "flash_firmware", fake_flash)

    result = server.flash_firmware(str(artifact), halt_after_reset=True)

    assert seen["path"] == artifact.resolve()
    assert seen["halt_after_reset"] is True
    assert result == f"Flashed {artifact.resolve()} via pyocd-native; target left halted."


def test_flash_firmware_requires_loaded_board_for_default_artifact() -> None:
    server._session_handle = make_handle(None)

    assert server.flash_firmware() == server.NO_BOARD_CONFIG_MESSAGE


def test_read_serial_defaults_to_board_contract(monkeypatch) -> None:
    board = make_board()
    handle = make_handle(board)
    port = SerialPortInfo(
        device="/dev/cu.usbmodem0001",
        description="J-Link",
        manufacturer="SEGGER",
        product="J-Link",
        interface="VCOM",
        hwid="USB VID:PID=1366:0105",
    )
    seen: dict[str, object] = {}

    server._session_handle = handle

    def fake_resolve(handle_arg, *, override: str | None):
        seen["override"] = override
        return port

    def fake_capture(device, baudrate, read_seconds, expected_text, *, on_port_open=None):
        seen["device"] = device
        seen["baudrate"] = baudrate
        seen["read_seconds"] = read_seconds
        seen["expected_text"] = expected_text
        seen["has_hook"] = on_port_open is not None
        return UARTCaptureResult(
            text="boot ok\r\n",
            expected_text=expected_text,
            reopen_count=1,
            duration_seconds=0.5,
        )

    monkeypatch.setattr(server, "_resolve_serial_port_for_session", fake_resolve)
    monkeypatch.setattr(server, "capture_uart_output", fake_capture)

    result = server.read_serial()

    assert seen["override"] is None
    assert seen["device"] == "/dev/cu.usbmodem0001"
    assert seen["baudrate"] == 115200
    assert seen["read_seconds"] == 3.0
    assert seen["expected_text"] == "boot ok"
    assert seen["has_hook"] is False
    assert result == (
        "UART matched on /dev/cu.usbmodem0001 at 115200 baud via pyocd-native; "
        "expected='boot ok'; reopen_count=1; duration=0.50s; excerpt=boot ok"
    )


def test_read_serial_uses_port_override(monkeypatch) -> None:
    board = make_board()
    handle = make_handle(board)
    port = SerialPortInfo(
        device="COM7",
        description="J-Link",
        manufacturer="SEGGER",
        product="J-Link",
        interface="VCOM",
        hwid="USB VID:PID=1366:0105",
    )
    seen: dict[str, object] = {}

    server._session_handle = handle

    def fake_resolve(handle_arg, *, override: str | None):
        seen["override"] = override
        return port

    monkeypatch.setattr(server, "_resolve_serial_port_for_session", fake_resolve)
    monkeypatch.setattr(
        server,
        "capture_uart_output",
        lambda device, baudrate, read_seconds, expected_text, *, on_port_open=None: UARTCaptureResult(
            text="boot ok\r\n",
            expected_text=expected_text,
            reopen_count=0,
            duration_seconds=0.25,
        ),
    )

    result = server.read_serial(port="COM99", read_seconds=1.5)

    assert seen["override"] == "COM99"
    assert "COM7" in result
    assert "duration=0.25s" in result


def test_read_serial_requires_loaded_board() -> None:
    server._session_handle = make_handle(None)

    assert server.read_serial() == server.NO_BOARD_CONFIG_MESSAGE


def test_unlock_recover_refuses_without_confirmation() -> None:
    server._session_handle = make_handle(make_board())

    assert (
        server.unlock_recover()
        == "Refusing to run recover without confirm=True. This operation may erase flash."
    )


def test_unlock_recover_delegates_when_confirmed(monkeypatch) -> None:
    board = make_board()
    handle = make_handle(board)
    server._session_handle = handle
    seen: dict[str, object] = {}

    def fake_recover(handle_arg):
        seen["handle"] = handle_arg
        return "pyOCD API mass erase"

    monkeypatch.setattr(server.target_control, "recover_target", fake_recover)

    result = server.unlock_recover(confirm=True)

    assert seen["handle"] is handle
    assert result == "Recover completed via pyOCD API mass erase on nrf52833dk via pyocd-native."


def test_unlock_recover_requires_loaded_board() -> None:
    server._session_handle = make_handle(None)

    assert server.unlock_recover(confirm=True) == server.NO_BOARD_CONFIG_MESSAGE


def test_connect_uses_board_aware_auto_probe_selection(monkeypatch) -> None:
    board = make_board()
    seen: dict[str, object] = {}

    monkeypatch.delenv("PYOCD_PROBE_UID", raising=False)
    monkeypatch.delenv("PYOCD_TARGET", raising=False)
    monkeypatch.setattr(server, "resolve_board_config", lambda board_id, board_config: board)
    monkeypatch.setattr(
        server,
        "resolve_probe_for_board",
        lambda board_arg, *, run_cmd, allow_single_fallback: ProbeResolution(
            probe=ProbeInfo(
                uid="685400693",
                description="Segger J-Link OB-SAM3U128-V2-NordicSem",
                raw="probe row",
                state="n/a",
            ),
            note="",
            probes=tuple(),
        ),
    )

    def fake_open_session(*, board, unique_id, target):
        seen["board"] = board
        seen["unique_id"] = unique_id
        seen["target"] = target
        return TargetSessionHandle(
            session=type("Session", (), {"board": type("Board", (), {"name": "nRF52833 DK"})()})(),
            board=board,
            probe_uid=unique_id,
            route_used="pyocd-native",
            target_override=target,
        )

    monkeypatch.setattr(server.target_control, "open_session", fake_open_session)

    result = server.connect(board_id="nrf52833dk")

    assert seen["board"] is board
    assert seen["unique_id"] == "685400693"
    assert seen["target"] == "nrf52833"
    assert "Connected to board" in result
    assert "685400693" in result
    assert "[board config: nrf52833dk]" in result
