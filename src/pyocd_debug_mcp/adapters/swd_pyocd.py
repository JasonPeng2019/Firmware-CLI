"""pyOCD-backed SWD adapter implementation."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
from typing import cast

from pyocd.core.exceptions import TransferError  # type: ignore[import-untyped]
from pyocd.core.helpers import ConnectHelper  # type: ignore[import-untyped]
from pyocd.flash.eraser import FlashEraser  # type: ignore[import-untyped]
from pyocd.flash.file_programmer import FileProgrammer  # type: ignore[import-untyped]

from pyocd_debug_mcp.adapters.swd_interface import SWDInterface, TargetSessionHandle
from pyocd_debug_mcp.board_config import BoardConfig
from pyocd_debug_mcp.target_errors import (
    LockedTargetError,
    ProbeNotFoundError,
    TargetConnectionError,
    UnsupportedArtifactError,
)

ROUTE_PYOCD_NATIVE = "pyocd-native"
SUPPORTED_FLASH_SUFFIXES = frozenset({".elf", ".hex"})


def _typed_backend_error(exc: Exception) -> TargetConnectionError:
    message = f"{type(exc).__name__}: {exc}"
    lowered = message.lower()
    if any(term in lowered for term in ("approtect", "access port", "locked target", "device locked")):
        return LockedTargetError(message)
    return TargetConnectionError(message)


def build_session_options(
    board: BoardConfig | None,
    target: str | None,
) -> dict[str, object] | None:
    """Build pyOCD session options from shared board facts."""

    options: dict[str, object] = {}
    if target:
        options["target_override"] = target
    if board and board.probe_family == "jlink":
        # Match the Stage 0/J-Link open-by-serial workaround proven on hardware.
        options["jlink.non_interactive"] = False
    if board and board.board_id == "nucleo_l476rg":
        # Current STM32 bench truth on this host requires connecting under reset
        # at a lower SWD clock to avoid STLink "DP wait" attach failures.
        options["connect_mode"] = "under-reset"
        options["frequency"] = 1_000_000
    return options or None


class PyOCDSWDInterface(SWDInterface):
    """Single native pyOCD route used during the early shared-service phase."""

    def open(
        self,
        *,
        board: BoardConfig | None,
        unique_id: str | None,
        target: str | None,
    ) -> TargetSessionHandle:
        probe_uid = unique_id or os.environ.get("PYOCD_PROBE_UID") or None
        target_override = (
            target
            or (board.pyocd_target if board else None)
            or os.environ.get("PYOCD_TARGET")
            or None
        )
        options = build_session_options(board, target_override)
        session = ConnectHelper.session_with_chosen_probe(
            blocking=False,
            return_first=True,
            unique_id=probe_uid,
            auto_open=False,
            options=options,
        )
        if session is None:
            raise ProbeNotFoundError("No matching debug probe found.")

        try:
            session.open()
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            try:
                session.close()
            except Exception:  # noqa: BLE001 - do not hide the open failure
                pass
            raise _typed_backend_error(exc) from exc
        return TargetSessionHandle(
            session=session,
            board=board,
            probe_uid=session.probe.unique_id or probe_uid,
            route_used=ROUTE_PYOCD_NATIVE,
            target_override=target_override,
        )

    def close(self, handle: TargetSessionHandle) -> None:
        handle.session.close()

    def get_state(self, handle: TargetSessionHandle) -> str:
        try:
            return cast(str, handle.session.target.get_state().name)
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def read_memory(self, handle: TargetSessionHandle, address: int, width_bits: int) -> int:
        try:
            return cast(int, handle.session.target.read_memory(address, width_bits))
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def read_memory_block(self, handle: TargetSessionHandle, address: int, length: int) -> list[int]:
        try:
            return list(cast(list[int], handle.session.target.read_memory_block8(address, length)))
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def write_memory(
        self,
        handle: TargetSessionHandle,
        address: int,
        value: int,
        width_bits: int,
    ) -> None:
        try:
            handle.session.target.write_memory(address, value, width_bits)
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def read_core_register(self, handle: TargetSessionHandle, name: str) -> int:
        try:
            return cast(int, handle.session.target.read_core_register(name))
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def write_core_register(self, handle: TargetSessionHandle, name: str, value: int) -> None:
        try:
            handle.session.target.write_core_register(name, value)
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def halt(self, handle: TargetSessionHandle) -> None:
        try:
            handle.session.target.halt()
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def resume(self, handle: TargetSessionHandle) -> None:
        try:
            handle.session.target.resume()
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def step(self, handle: TargetSessionHandle) -> None:
        try:
            handle.session.target.step()
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def reset(self, handle: TargetSessionHandle) -> None:
        try:
            handle.session.target.reset()
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def reset_and_halt(self, handle: TargetSessionHandle) -> None:
        try:
            handle.session.target.reset_and_halt()
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def flash(
        self,
        handle: TargetSessionHandle,
        firmware: Path,
        *,
        halt_after_reset: bool,
    ) -> None:
        if firmware.suffix.lower() not in SUPPORTED_FLASH_SUFFIXES:
            raise UnsupportedArtifactError(
                f"Unsupported artifact type '{firmware.suffix}' - use one of: "
                f"{', '.join(sorted(SUPPORTED_FLASH_SUFFIXES))}"
            )

        target = handle.session.target
        # Match `pyocd load`'s proven pre-reset sequence. On STM32/ST-Link, skipping
        # this can make the Python API flash path fail even though the CLI succeeds.
        try:
            target.reset_and_halt()
            # Keep transport stdout protocol-clean when the backend emits progress bars.
            with contextlib.redirect_stdout(io.StringIO()):
                FileProgrammer(handle.session).program(str(firmware))
            if halt_after_reset:
                target.reset_and_halt()
            else:
                target.reset()
        except TransferError as exc:
            # `pyocd load` tolerates a transient transfer drop during the final reset.
            if halt_after_reset:
                raise _typed_backend_error(exc) from exc
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def recover(self, handle: TargetSessionHandle) -> None:
        try:
            FlashEraser(handle.session, FlashEraser.Mode.MASS).erase()
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def set_breakpoint(self, handle: TargetSessionHandle, address: int) -> None:
        try:
            handle.session.target.set_breakpoint(address)
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc

    def remove_breakpoint(self, handle: TargetSessionHandle, address: int) -> None:
        try:
            handle.session.target.remove_breakpoint(address)
        except Exception as exc:  # noqa: BLE001 - preserve backend context
            raise _typed_backend_error(exc) from exc
