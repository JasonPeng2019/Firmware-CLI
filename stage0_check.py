#!/usr/bin/env python3
"""
Stage 0 — Board & toolchain validation.
Confirms pyOCD can see both probes, has the right target packs installed,
and can connect + read a register on each board.

Usage:
    python stage0_check.py                  # check both boards
    python stage0_check.py --board nrf      # check nRF52840-DK only
    python stage0_check.py --board nucleo   # check Nucleo-L476RG only
    python stage0_check.py --install-packs  # auto-install missing packs, then check
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass, field

# ── Target config ─────────────────────────────────────────────────────────────

@dataclass
class BoardConfig:
    name: str
    pyocd_target: str          # exact target string for -t flag
    pack_name: str             # search term for `pyocd pack find`
    probe_hint: str            # substring to match in probe UID/description
    test_addr: int             # address to read as a smoke-test
    probe_type: str            # human label

BOARDS = {
    "nrf": BoardConfig(
        name="nRF52840-DK",
        pyocd_target="nrf52840",
        pack_name="nrf52840",
        probe_hint="jlink",
        test_addr=0x10000000,  # FICR base — always readable
        probe_type="SEGGER J-Link",
    ),
    "nucleo": BoardConfig(
        name="Nucleo-L476RG",
        pyocd_target="stm32l476rg",
        pack_name="stm32l476",
        probe_hint="stlink",
        test_addr=0x08000000,  # flash base
        probe_type="ST-Link/V2-1",
    ),
}

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "✓"
FAIL = "✗"
WARN = "⚠"

def run(cmd: list[str], capture=True) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=capture, text=True)
    return result.returncode, result.stdout, result.stderr

def header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)

def check(ok: bool, msg: str):
    symbol = PASS if ok else FAIL
    print(f"  [{symbol}] {msg}")
    return ok

# ── Check steps ───────────────────────────────────────────────────────────────

def check_pyocd_installed() -> bool:
    header("pyOCD installation")
    rc, out, _ = run(["pyocd", "--version"])
    ok = rc == 0
    check(ok, f"pyocd found: {out.strip()}" if ok else "pyocd not found — run: pip install pyocd")
    return ok

def list_probes() -> list[dict]:
    """Returns list of dicts with keys: uid, description, state."""
    rc, out, _ = run(["pyocd", "list", "--output", "json"])
    if rc != 0 or not out.strip():
        # Fall back to text parsing
        rc, out, _ = run(["pyocd", "list"])
        probes = []
        for line in out.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.lower().startswith("no"):
                probes.append({"raw": line, "uid": "", "description": line.lower(), "state": ""})
        return probes

    import json
    try:
        data = json.loads(out)
        # pyocd list --output json returns {"boards": [...]}
        boards = data.get("boards", data) if isinstance(data, dict) else data
        return [
            {
                "uid": b.get("unique_id", b.get("uid", "")),
                "description": (b.get("description", "") + " " + b.get("board_name", "")).lower(),
                "state": b.get("state", ""),
                "raw": str(b),
            }
            for b in boards
        ]
    except (json.JSONDecodeError, KeyError):
        return []

def check_probes(boards_to_check: list[BoardConfig]) -> dict[str, bool]:
    header("Connected probes")
    probes = list_probes()

    if not probes:
        rc, out, _ = run(["pyocd", "list"])
        print(f"  Raw output:\n{out or '  (none)'}")
        for b in boards_to_check:
            check(False, f"{b.name} ({b.probe_type}) — no probes detected at all")
        return {b.pack_name: False for b in boards_to_check}

    print(f"  Found {len(probes)} probe(s):")
    for p in probes:
        print(f"    • {p.get('uid') or p.get('raw', '?')}")

    found = {}
    for b in boards_to_check:
        matched = any(b.probe_hint in p["description"] for p in probes)
        # J-Link sometimes shows as "jlink" or contains serial number only — widen match
        if not matched and b.probe_hint == "jlink":
            matched = any("j-link" in p["description"] or "jlink" in p["description"] for p in probes)
        if not matched:
            # If only one probe and one board, assume it's that board
            if len(probes) == 1 and len(boards_to_check) == 1:
                matched = True
        check(matched, f"{b.name} ({b.probe_type}) probe visible")
        found[b.pack_name] = matched

    return found

def check_target_packs(boards_to_check: list[BoardConfig], auto_install: bool) -> dict[str, bool]:
    header("CMSIS-Pack / target availability")
    _, out, _ = run(["pyocd", "list", "--targets"])
    installed_targets = out.lower()

    results = {}
    for b in boards_to_check:
        target_present = b.pyocd_target in installed_targets
        if target_present:
            check(True, f"Target '{b.pyocd_target}' available")
            results[b.pack_name] = True
            continue

        check(False, f"Target '{b.pyocd_target}' not found")

        if auto_install:
            print(f"  [ ] Installing pack for {b.pack_name}...")
            rc, out, err = run(["pyocd", "pack", "install", b.pack_name], capture=False)
            if rc == 0:
                # Re-check
                _, out2, _ = run(["pyocd", "list", "--targets"])
                ok = b.pyocd_target in out2.lower()
                check(ok, f"Pack installed, target '{b.pyocd_target}' now {'available' if ok else 'still missing'}")
                results[b.pack_name] = ok
            else:
                check(False, f"Pack install failed — try manually: pyocd pack find {b.pack_name}")
                results[b.pack_name] = False
        else:
            print(f"      Fix: pyocd pack find {b.pack_name}")
            print(f"           pyocd pack install {b.pack_name}")
            print(f"      Or re-run with --install-packs")
            results[b.pack_name] = False

    return results

def check_connection(b: BoardConfig, probe_found: bool, target_ok: bool) -> bool:
    header(f"Connection test — {b.name}")

    if not probe_found:
        check(False, "Skipped — probe not detected (board plugged in?)")
        return False
    if not target_ok:
        check(False, "Skipped — target pack not installed")
        return False

    print(f"  Attempting: pyocd cmd -t {b.pyocd_target} (read {hex(b.test_addr)})")
    cmd = ["pyocd", "cmd", "-t", b.pyocd_target, "-c", f"read32 {hex(b.test_addr)} 1"]
    rc, out, err = run(cmd)

    if rc == 0 and out.strip():
        check(True, f"Connected and read {hex(b.test_addr)}: {out.strip()}")
        return True

    # Check for APPROTECT (nRF-specific)
    combined = (out + err).lower()
    if "approtect" in combined or "access port" in combined or "locked" in combined:
        print(f"  [{WARN}] nRF52840 APPROTECT may be active — chip is access-protected.")
        print(f"      Recover with: pyocd cmd -t nrf52840 -c 'nrf recover'")
        print(f"      This erases flash but restores SWD access.")
        return False

    if "no connected" in combined or "no target" in combined or "unable to connect" in combined:
        check(False, "pyOCD found the probe but could not connect to the target MCU.")
        print(f"      • Is the board powered?")
        print(f"      • Is the USB cable a data cable (not charge-only)?")
        if b.probe_hint == "jlink":
            print(f"      • J-Link firmware may need updating (SEGGER J-Link Software pack)")
        return False

    check(False, f"Unexpected error (rc={rc})")
    if err.strip():
        print(f"      stderr: {err.strip()[:300]}")
    return False

def print_summary(results: list[tuple[str, bool]]):
    header("Summary")
    all_pass = True
    for label, ok in results:
        check(ok, label)
        if not ok:
            all_pass = False
    print()
    if all_pass:
        print("  All checks passed. Stage 0 target discovery complete.")
        print("  Next: Step 0.2 — probe-specific setup (J-Link drivers / nRF recover cycle)")
    else:
        print("  Some checks failed. Fix the items above, then re-run this script.")
    print()

# ── Main ──────────────────────────────────────────────────────────────────────

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
    args = parser.parse_args()

    boards_to_check = (
        list(BOARDS.values()) if args.board == "both"
        else [BOARDS[args.board]]
    )

    print("\nStage 0 — Board & toolchain validation")
    print(f"Checking: {', '.join(b.name for b in boards_to_check)}")

    if not check_pyocd_installed():
        sys.exit(1)

    probe_found = check_probes(boards_to_check)
    target_ok = check_target_packs(boards_to_check, auto_install=args.install_packs)

    summary = []
    for b in boards_to_check:
        pf = probe_found.get(b.pack_name, False)
        tok = target_ok.get(b.pack_name, False)
        conn_ok = check_connection(b, pf, tok)
        summary += [
            (f"{b.name}: probe visible",          pf),
            (f"{b.name}: target '{b.pyocd_target}' available", tok),
            (f"{b.name}: connect + read register", conn_ok),
        ]

    print_summary(summary)
    all_ok = all(ok for _, ok in summary)
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
