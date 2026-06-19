from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for entry in (REPO_ROOT, SRC_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import stage0_check  # noqa: E402
from pyocd_debug_mcp.board_config import BoardConfig  # noqa: E402
from pyocd_debug_mcp.services.session_runtime import PolicyRefusal  # noqa: E402
from pyocd_debug_mcp.serial_resolver import SerialPortInfo  # noqa: E402
from pyocd_debug_mcp.target_errors import LockedTargetError, TargetConnectionError  # noqa: E402


def make_board() -> BoardConfig:
    return BoardConfig(
        board_id="nucleo_l476rg",
        display_name="Nucleo-L476RG",
        mcu_family="stm32l476",
        probe_family="stlink",
        pyocd_target="stm32l476rgtx",
        pack_name="stm32l476",
        probe_type="ST-Link",
        probe_hint_terms=("stlink",),
        serial_hint_terms=("stlink",),
        test_addr=0x08000000,
    )


def make_nordic_board() -> BoardConfig:
    return BoardConfig(
        board_id="nrf52833dk",
        display_name="nRF52833 DK",
        mcu_family="nrf52833",
        probe_family="jlink",
        pyocd_target="nrf52833",
        pack_name="nrf52833",
        probe_type="SEGGER J-Link",
        probe_hint_terms=("jlink",),
        serial_hint_terms=("jlink",),
        test_addr=0x10000000,
        requires_recover_validation=True,
        recover_mode="nrf_pyocd_unlock",
    )


def make_handle(board: BoardConfig) -> stage0_check.TargetSessionHandle:
    session_board = type("SessionBoard", (), {"name": board.display_name})()
    session = type("Session", (), {"board": session_board})()
    return stage0_check.TargetSessionHandle(
        session=session,
        board=board,
        probe_uid="probe-123",
        route_used="pyocd-native",
        target_override=board.pyocd_target,
    )


def test_check_connection_handles_locked_target_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        stage0_check,
        "read_memory_value",
        lambda board, probe, address, width_bits: stage0_check.ReadResult(
            rc=1,
            stdout="",
            stderr="LockedTargetError: locked",
            error=LockedTargetError("locked"),
        ),
    )
    monkeypatch.setattr(stage0_check, "build_recover_attempts", lambda board, probe: [])

    ok = stage0_check.check_connection(make_board(), stage0_check.ProbeInfo("123", "stlink", "raw"), True)

    assert ok is False
    captured = capsys.readouterr().out
    assert "appears access-protected" in captured


def test_check_connection_handles_typed_target_connection_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        stage0_check,
        "read_memory_value",
        lambda board, probe, address, width_bits: stage0_check.ReadResult(
            rc=1,
            stdout="",
            stderr="TargetConnectionError: unable to connect",
            error=TargetConnectionError("unable to connect"),
        ),
    )

    ok = stage0_check.check_connection(make_board(), stage0_check.ProbeInfo("123", "stlink", "raw"), True)

    assert ok is False
    captured = capsys.readouterr().out
    assert "could not connect to the target MCU" in captured


def test_read_uart_output_preserves_typed_failure_context(monkeypatch, capsys) -> None:
    monkeypatch.setattr(stage0_check, "load_pyserial", lambda: (object(), object()))

    def raise_capture(*args, **kwargs):
        raise RuntimeError("port busy")

    monkeypatch.setattr(stage0_check, "capture_uart_output", raise_capture)
    port = SerialPortInfo(
        device="/dev/cu.usbmodem144403",
        description="ST-Link",
        manufacturer="STMicroelectronics",
        product="ST-Link",
        interface="VCP",
        hwid="USB VID:PID=0483:374B",
    )

    ok = stage0_check.read_uart_output(
        make_board(),
        port,
        115200,
        1.0,
        "boot ok",
    )

    assert ok is False
    captured = capsys.readouterr().out
    assert "RuntimeError: port busy" in captured
    assert "/dev/cu.usbmodem144403" in captured
    assert "Expected: boot ok" in captured


def test_flash_reference_firmware_surfaces_policy_refusal(monkeypatch, tmp_path: Path, capsys) -> None:
    board = make_nordic_board()
    probe = stage0_check.ProbeInfo("685400693", "J-Link", "raw")
    artifact = tmp_path / "firmware.elf"
    artifact.write_text("elf", encoding="utf-8")

    monkeypatch.setattr(stage0_check.target_control, "open_session", lambda **kwargs: make_handle(board))
    monkeypatch.setattr(
        stage0_check,
        "resolve_flash_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            PolicyRefusal("flash/unsupported-suffix", "Unsupported flash artifact type '.bin'.")
        ),
    )

    result = stage0_check.flash_reference_firmware(
        board,
        probe,
        True,
        True,
        artifact,
    )

    assert result.status is False
    captured = capsys.readouterr().out
    assert "Flash refused" in captured
    assert "[flash/unsupported-suffix]" in captured


def test_run_recover_test_surfaces_policy_refusal(monkeypatch, capsys) -> None:
    board = make_nordic_board()
    probe = stage0_check.ProbeInfo("685400693", "J-Link", "raw")

    monkeypatch.setattr(stage0_check.target_control, "open_session", lambda **kwargs: make_handle(board))
    monkeypatch.setattr(
        stage0_check,
        "authorize_recover",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            PolicyRefusal("recover/manual-only", "nRF52833 DK uses manual_only recover handling.")
        ),
    )

    result = stage0_check.run_recover_test(board, probe, True, True)

    assert result is not None
    assert result.completed is False
    captured = capsys.readouterr().out
    assert "Recover policy refused" in captured
    assert "[recover/manual-only]" in captured
