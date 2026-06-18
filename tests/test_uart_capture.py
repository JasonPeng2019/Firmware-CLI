from __future__ import annotations

from pyocd_debug_mcp.adapters.uart_interface import UARTInterface, UARTPortHandle
from pyocd_debug_mcp.services import uart_capture


class FakeUARTAdapter(UARTInterface):
    def __init__(
        self,
        sessions: list[list[bytes | Exception]],
        *,
        open_error: Exception | None = None,
    ) -> None:
        self._sessions = [list(session) for session in sessions]
        self._open_error = open_error

    def open(self, device: str, *, baudrate: int, timeout_seconds: float) -> UARTPortHandle:
        assert device
        assert baudrate > 0
        assert timeout_seconds > 0
        if self._open_error is not None:
            raise self._open_error
        return UARTPortHandle(
            handle=self._sessions.pop(0),
            device=device,
            baudrate=baudrate,
            timeout_seconds=timeout_seconds,
        )

    def close(self, handle: UARTPortHandle) -> None:
        return None

    def reset_input_buffer(self, handle: UARTPortHandle) -> None:
        return None

    def read(self, handle: UARTPortHandle, size: int) -> bytes:
        session = handle.handle
        if session:
            item = session.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return b""


def test_capture_uart_output_matches_expected_text_across_partial_chunks() -> None:
    adapter = FakeUARTAdapter([[b"bo", b"ot ", b"ok\r\n"]])

    result = uart_capture.capture_uart_output(
        "COM1",
        115200,
        0.05,
        "boot ok",
        reopen_attempts=0,
        per_open_window_seconds=0.05,
        adapter=adapter,
    )

    assert result.matched is True
    assert "boot ok" in result.text


def test_capture_uart_output_times_out_without_expected_text() -> None:
    adapter = FakeUARTAdapter([[b"noise only\r\n"]])

    result = uart_capture.capture_uart_output(
        "COM1",
        115200,
        0.05,
        "boot ok",
        reopen_attempts=0,
        per_open_window_seconds=0.05,
        adapter=adapter,
    )

    assert result.matched is False
    assert "noise only" in result.text


def test_capture_uart_output_reopens_once_when_first_open_is_quiet() -> None:
    adapter = FakeUARTAdapter([[b""], [b"boot ok\r\n"]])

    result = uart_capture.capture_uart_output(
        "COM1",
        115200,
        0.03,
        "boot ok",
        reopen_attempts=1,
        reopen_delay_seconds=0,
        per_open_window_seconds=0.01,
        adapter=adapter,
    )

    assert result.matched is True
    assert result.reopen_count == 1


def test_capture_uart_output_without_expected_text_reports_any_output() -> None:
    adapter = FakeUARTAdapter([[b"hello world\r\n"]])

    result = uart_capture.capture_uart_output(
        "COM1",
        115200,
        0.05,
        None,
        reopen_attempts=0,
        per_open_window_seconds=0.05,
        adapter=adapter,
    )

    assert result.has_output is True
    assert result.matched is True
    assert result.excerpt == "hello world"


def test_capture_uart_output_surfaces_open_failures() -> None:
    adapter = FakeUARTAdapter([], open_error=OSError("port busy"))

    try:
        uart_capture.capture_uart_output(
            "COM1",
            115200,
            0.05,
            "boot ok",
            reopen_attempts=0,
            per_open_window_seconds=0.05,
            adapter=adapter,
        )
    except RuntimeError as exc:
        assert "port busy" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_capture_uart_output_surfaces_mid_read_disappearance() -> None:
    adapter = FakeUARTAdapter([[b"bo", OSError("device disappeared")]])

    try:
        uart_capture.capture_uart_output(
            "COM1",
            115200,
            0.05,
            "boot ok",
            reopen_attempts=0,
            per_open_window_seconds=0.05,
            adapter=adapter,
        )
    except RuntimeError as exc:
        assert "device disappeared" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_capture_uart_output_decodes_non_utf8_with_replacement() -> None:
    adapter = FakeUARTAdapter([[b"\xffboot ok\r\n"]])

    result = uart_capture.capture_uart_output(
        "COM1",
        115200,
        0.05,
        "boot ok",
        reopen_attempts=0,
        per_open_window_seconds=0.05,
        adapter=adapter,
    )

    assert result.matched is True
    assert "\ufffd" in result.text
