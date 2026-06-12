#!/usr/bin/env python3
"""
nRF52840 APPROTECT recovery via pyOCD.

Uses pyOCD's built-in auto_unlock option, which triggers a CTRL-AP mass erase
and restores SWD access without requiring nrfjprog or nRF Command Line Tools.

WARNING: mass erase destroys all flash contents on the target.
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))

from pyocd_debug_mcp.local_env import load_local_env

load_local_env()

logging.basicConfig(level=logging.WARNING)

PYOCD_TARGET = "nrf52840"  # VENDOR-FIXED (nRF52840 pyOCD target string)


def main() -> None:
    print("nRF52840 APPROTECT recovery")
    print("WARNING: this performs a mass erase — all flash contents will be lost.")
    print()

    try:
        from pyocd.core.helpers import ConnectHelper
        from pyocd.core import exceptions as pyocd_exceptions
    except ImportError:
        print("[FAIL] pyOCD not found. Run: uv sync")
        sys.exit(1)

    try:
        with ConnectHelper.session_with_chosen_probe(
            target_override=PYOCD_TARGET,
            options={"auto_unlock": True},
        ) as session:
            target = session.board.target
            if target is None:
                print("[FAIL] Connected but target is None after recovery attempt")
                sys.exit(1)

            # Confirm APPROTECT is now disabled via CTRL-AP status register.
            # CTRL_AP_APPROTECTSTATUS = 0x0 means protected, 0x1 means unlocked.
            # HW-FIXED register offsets from nRF52840 PS / pyOCD target_nRF52.py
            ctrl_ap = target.dp.aps[0x1]  # HW-FIXED (CTRL-AP is always AP index 1 on nRF52)
            approtect_status = ctrl_ap.read_reg(0x00C)  # HW-FIXED (CTRL_AP_APPROTECTSTATUS offset)
            if approtect_status != 0x1:
                print(f"[FAIL] CTRL_AP_APPROTECTSTATUS = 0x{approtect_status:X} (expected 0x1 = unlocked)")
                sys.exit(1)
            print(f"[PASS] CTRL_AP_APPROTECTSTATUS = 0x{approtect_status:X} (unlocked)")

            # Confirm AHB-AP memory access works by reading FICR.INFO.PART.
            # This register is behind the AHB-AP which APPROTECT fully blocks.
            # A successful read with the correct value is proof SWD access is restored.
            # HW-FIXED: FICR.INFO.PART at 0x10000100, expected value 0x00052840 (nRF52840 part code)
            ficr_part = target.read32(0x10000100)  # HW-FIXED (nRF52840 FICR.INFO.PART)
            if ficr_part != 0x00052840:
                print(f"[FAIL] FICR.INFO.PART = 0x{ficr_part:08X} (expected 0x00052840 for nRF52840)")
                sys.exit(1)
            print(f"[PASS] FICR.INFO.PART = 0x{ficr_part:08X} (nRF52840 confirmed, AHB-AP accessible)")

            print()
            print("[PASS] Recovery complete — re-run stage0_check.py to confirm.")
    except pyocd_exceptions.TargetError as exc:
        print(f"[FAIL] Recovery failed: {exc}")
        print("       If this persists, install nrfjprog and run: nrfjprog --recover")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
nRF52840 APPROTECT recovery via pyOCD.

Uses pyOCD's built-in auto_unlock option, which triggers a CTRL-AP mass erase
and restores SWD access without requiring nrfjprog or nRF Command Line Tools.

WARNING: mass erase destroys all flash contents on the target.
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))

from pyocd_debug_mcp.local_env import load_local_env

load_local_env()

logging.basicConfig(level=logging.WARNING)

PYOCD_TARGET = "nrf52840"  # VENDOR-FIXED (nRF52840 pyOCD target string)


def main() -> None:
    print("nRF52840 APPROTECT recovery")
    print("WARNING: this performs a mass erase — all flash contents will be lost.")
    print()

    try:
        from pyocd.core.helpers import ConnectHelper
        from pyocd.core import exceptions as pyocd_exceptions
    except ImportError:
        print("[FAIL] pyOCD not found. Run: uv sync")
        sys.exit(1)

    try:
        with ConnectHelper.session_with_chosen_probe(
            target_override=PYOCD_TARGET,
            options={"auto_unlock": True},
        ) as session:
            target = session.board.target
            if target is None:
                print("[FAIL] Connected but target is None after recovery attempt")
                sys.exit(1)

            # Confirm APPROTECT is now disabled via CTRL-AP status register.
            # CTRL_AP_APPROTECTSTATUS = 0x0 means protected, 0x1 means unlocked.
            # HW-FIXED register offsets from nRF52840 PS / pyOCD target_nRF52.py
            ctrl_ap = target.dp.aps[0x1]  # HW-FIXED (CTRL-AP is always AP index 1 on nRF52)
            approtect_status = ctrl_ap.read_reg(0x00C)  # HW-FIXED (CTRL_AP_APPROTECTSTATUS offset)
            if approtect_status != 0x1:
                print(f"[FAIL] CTRL_AP_APPROTECTSTATUS = 0x{approtect_status:X} (expected 0x1 = unlocked)")
                sys.exit(1)
            print(f"[PASS] CTRL_AP_APPROTECTSTATUS = 0x{approtect_status:X} (unlocked)")

            # Confirm AHB-AP memory access works by reading FICR.INFO.PART.
            # This register is behind the AHB-AP which APPROTECT fully blocks.
            # A successful read with the correct value is proof SWD access is restored.
            # HW-FIXED: FICR.INFO.PART at 0x10000100, expected value 0x00052840 (nRF52840 part code)
            ficr_part = target.read32(0x10000100)  # HW-FIXED (nRF52840 FICR.INFO.PART)
            if ficr_part != 0x00052840:
                print(f"[FAIL] FICR.INFO.PART = 0x{ficr_part:08X} (expected 0x00052840 for nRF52840)")
                sys.exit(1)
            print(f"[PASS] FICR.INFO.PART = 0x{ficr_part:08X} (nRF52840 confirmed, AHB-AP accessible)")

            print()
            print("[PASS] Recovery complete — re-run stage0_check.py to confirm.")
    except pyocd_exceptions.TargetError as exc:
        print(f"[FAIL] Recovery failed: {exc}")
        print("       If this persists, install nrfjprog and run: nrfjprog --recover")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
