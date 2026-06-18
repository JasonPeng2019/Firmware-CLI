#!/usr/bin/env python3
"""
Host-level readiness checks that should run before board-level Stage 0 validation.

This script does not claim a board works. It only checks whether the host can:
- run pyOCD
- enumerate probes
- enumerate serial ports
- load board configs
- check/install target packs referenced by board configs

It may optionally reconcile the canonical Python environment and install missing pyOCD packs.
It does not install OS drivers or vendor probe software.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))

from pyocd_debug_mcp.board_config import (  # noqa: E402
    DEFAULT_BOARD_CONFIG_DIR,
    BoardConfig,
    ConfigError,
    load_selected_board_configs,
    preview_board_config_paths,
)
from pyocd_debug_mcp.local_env import load_local_env  # noqa: E402
from pyocd_debug_mcp.serial_resolver import command_exists  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
INFO = "INFO"

load_local_env()


@dataclass(frozen=True)
class DependencySpec:
    package_name: str
    import_name: str
    required: bool
    reason: str


@dataclass(frozen=True)
class ProbeInfo:
    uid: str
    description: str
    raw: str
    state: str = ""


DEPENDENCIES = (
    DependencySpec(
        package_name="pyocd",
        import_name="pyocd",
        required=True,
        reason="required to enumerate probes, targets, and packs",
    ),
    DependencySpec(
        package_name="pyserial",
        import_name="serial",
        required=True,
        reason="required to enumerate serial ports",
    ),
    DependencySpec(
        package_name="pyyaml",
        import_name="yaml",
        required=False,
        reason="required to load YAML board configs",
    ),
    DependencySpec(
        package_name="python-dotenv",
        import_name="dotenv",
        required=True,
        reason="required to auto-load repo-local .env defaults",
    ),
)


def run(cmd: list[str], capture: bool = True, cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=capture, text=True, cwd=str(cwd) if cwd else None
        )
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


def package_installed(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


def reconcile_canonical_env(package_names: list[str]) -> bool:
    if not package_names:
        return True
    repo_root = Path(__file__).resolve().parent
    cmd = ["uv", "sync", "--locked"]
    print(f"  Attempting: {' '.join(cmd)}")
    rc, _, _ = run(cmd, capture=False, cwd=repo_root)
    return rc == 0


def dependency_summary(require_yaml: bool, install_missing: bool) -> dict[str, bool]:
    header("Python dependencies")

    results: dict[str, bool] = {}
    missing_required: list[str] = []
    missing_optional: list[str] = []

    for dep in DEPENDENCIES:
        installed = package_installed(dep.import_name)
        results[dep.package_name] = installed
        if installed:
            log(PASS, f"{dep.package_name} installed")
            continue

        if dep.required or (dep.package_name == "pyyaml" and require_yaml):
            log(FAIL, f"{dep.package_name} missing - {dep.reason}")
            missing_required.append(dep.package_name)
        else:
            log(WARN, f"{dep.package_name} missing - {dep.reason}")
            missing_optional.append(dep.package_name)

    if install_missing:
        install_list = missing_required + missing_optional
        if install_list:
            ok = reconcile_canonical_env(install_list)
            if ok:
                log(PASS, "Reconciled the canonical repo environment with 'uv sync --locked'")
            else:
                log(
                    FAIL,
                    "Failed to reconcile the canonical repo environment with 'uv sync --locked'",
                )
            for dep in DEPENDENCIES:
                results[dep.package_name] = package_installed(dep.import_name)

    return results


def load_pyserial():
    try:
        from serial.tools import list_ports
    except ImportError:
        return None
    return list_ports


def list_serial_ports() -> list[str] | None:
    list_ports = load_pyserial()
    if list_ports is None:
        return None
    return [port.device for port in list_ports.comports()]


def serial_summary(pyserial_ok: bool) -> int | None:
    header("Serial ports")
    if not pyserial_ok:
        log(FAIL, "pyserial missing - cannot enumerate serial ports")
        return None

    ports = list_serial_ports()
    if ports is None:
        log(FAIL, "pyserial import failed during serial enumeration")
        return None
    if not ports:
        log(WARN, "No serial ports detected")
        return 0

    log(PASS, f"Detected {len(ports)} serial port(s)")
    for port in ports:
        print(f"    - {port}")
    return len(ports)


def list_probes() -> list[ProbeInfo]:
    rc, out, _ = run(["pyocd", "list", "--output", "json"])
    if rc != 0 or not out.strip():
        _, out, _ = run(["pyocd", "list"])
        probes: list[ProbeInfo] = []
        for line in out.splitlines():
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and not stripped.lower().startswith("no")
                and not re.fullmatch(r"-+", stripped)
            ):
                probes.append(ProbeInfo(uid="", description=stripped.lower(), raw=stripped))
        return probes

    try:
        data = json.loads(out)
        boards = data.get("boards", data) if isinstance(data, dict) else data
        probes = []
        for item in boards:
            description = " ".join(
                part for part in [item.get("description", ""), item.get("board_name", "")] if part
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


def list_target_names() -> set[str]:
    _, out, _ = run(["pyocd", "list", "--targets"])
    names: set[str] = set()
    for line in out.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or re.fullmatch(r"-+", stripped):
            continue
        names.add(stripped.split()[0].lower())
    return names


def pyocd_summary(pyocd_ok: bool) -> int | None:
    header("pyOCD host visibility")
    if not pyocd_ok:
        log(FAIL, "pyocd missing - cannot enumerate probes or targets")
        return None

    rc, out, err = run(["pyocd", "--version"])
    if rc == 0:
        log(PASS, f"pyOCD found: {out.strip()}")
    else:
        log(FAIL, f"pyOCD command failed: {(err or out).strip()[:300]}")
        return None

    probes = list_probes()
    if probes:
        log(PASS, f"Detected {len(probes)} probe(s)")
        for probe in probes:
            desc = probe.description or probe.raw
            suffix = f" [{probe.state}]" if probe.state else ""
            print(f"    - {probe.uid or '(no uid)'} :: {desc}{suffix}")
        return len(probes)
    else:
        log(WARN, "No debug probes detected by pyOCD")
        print(
            "      This usually means an OS driver / vendor tooling / USB enumeration issue, not a board-config issue."
        )
        return 0


def board_config_summary(boards: list[BoardConfig]):
    header("Board configs")
    if not boards:
        log(WARN, "No board configs selected")
        return

    log(PASS, f"Loaded {len(boards)} board config(s)")
    for board in boards:
        print(
            f"    - {board.board_id} :: {board.display_name} :: target={board.pyocd_target} :: pack={board.pack_name}"
        )


def target_pack_summary(
    boards: list[BoardConfig], pyocd_ok: bool, install_packs: bool
) -> dict[str, bool]:
    header("Target packs")
    if not boards:
        log(WARN, "No board configs selected - skipping pack checks")
        return {}
    if not pyocd_ok:
        log(FAIL, "pyocd missing - cannot check target packs")
        return {board.board_id: False for board in boards}

    installed_targets = list_target_names()
    results: dict[str, bool] = {}

    for board in boards:
        target_present = board.pyocd_target.lower() in installed_targets
        if target_present:
            log(PASS, f"{board.board_id}: target '{board.pyocd_target}' available")
            results[board.board_id] = True
            continue

        log(WARN, f"{board.board_id}: target '{board.pyocd_target}' not found")
        if install_packs:
            print(f"  Attempting: pyocd pack install {board.pack_name}")
            rc, _, _ = run(["pyocd", "pack", "install", board.pack_name], capture=False)
            if rc == 0:
                ok = board.pyocd_target.lower() in list_target_names()
                log(
                    PASS if ok else FAIL,
                    f"{board.board_id}: pack install {'succeeded' if ok else 'did not expose target'}",
                )
                results[board.board_id] = ok
            else:
                log(FAIL, f"{board.board_id}: pack install failed")
                results[board.board_id] = False
        else:
            print(f"      Fix: uv run pyocd pack install {board.pack_name}")
            results[board.board_id] = False

    return results


def vendor_serial_tool_summary(boards: list[BoardConfig]):
    header("Serial auto-detect helpers")
    if not boards:
        log(WARN, "No board configs selected - skipping vendor serial-tool hints")
        return

    needs_nrfjprog = any(
        board.mcu_family.lower().startswith("nrf") and board.probe_family == "jlink"
        for board in boards
    )
    needs_stm32_cli = any(board.probe_family == "stlink" for board in boards)

    if not needs_nrfjprog and not needs_stm32_cli:
        log(INFO, "Selected boards do not require vendor-specific serial auto-detect helpers")
        return

    if needs_nrfjprog:
        if command_exists("nrfjprog"):
            log(
                PASS,
                "nrfjprog found - Nordic J-Link serial auto-detect can use 'nrfjprog --com'",
            )
        else:
            log(
                WARN,
                "nrfjprog not found - Nordic J-Link serial auto-detect will fall back to generic matching or manual --port",
            )

    if needs_stm32_cli:
        if command_exists("STM32_Programmer_CLI"):
            log(
                PASS,
                "STM32_Programmer_CLI found - ST-LINK serial auto-detect can use 'STM32_Programmer_CLI -l'",
            )
        else:
            log(
                WARN,
                "STM32_Programmer_CLI not found - ST-LINK serial auto-detect will fall back to generic matching or manual --port",
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Host bootstrap before Stage 0 board checks")
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
        help="Board id to inspect. Repeat to select multiple boards. Defaults to all non-example board configs in the board-config-dir plus any extra board-config files.",
    )
    parser.add_argument(
        "--install-missing",
        action="store_true",
        help="Reconcile the canonical repo environment with 'uv sync --locked' if required Python packages are missing.",
    )
    parser.add_argument(
        "--install-packs",
        action="store_true",
        help="Install missing pyOCD target packs referenced by the selected board configs.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    board_config_dir = Path(args.board_config_dir).expanduser().resolve()
    extra_paths = [Path(raw_path).expanduser().resolve() for raw_path in args.board_config]
    require_yaml = any(
        path.suffix.lower() in {".yaml", ".yml"}
        for path in [*extra_paths, *preview_board_config_paths(board_config_dir)]
    )

    dependency_results = dependency_summary(
        require_yaml=require_yaml, install_missing=args.install_missing
    )
    pyocd_ok = dependency_results.get("pyocd", False)
    pyserial_ok = dependency_results.get("pyserial", False)

    probe_count = pyocd_summary(pyocd_ok)
    serial_count = serial_summary(pyserial_ok)

    boards: list[BoardConfig] = []
    board_config_ok = True
    try:
        boards = load_selected_board_configs(
            board_config_dir,
            extra_paths=extra_paths,
            requested_ids=args.board_id,
        )
    except ConfigError as exc:
        board_config_ok = False
        header("Board configs")
        log(FAIL, str(exc))

    board_config_summary(boards)
    pack_results = target_pack_summary(boards, pyocd_ok=pyocd_ok, install_packs=args.install_packs)
    vendor_serial_tool_summary(boards)
    packs_ready = bool(boards) and all(pack_results.get(board.board_id, False) for board in boards)
    host_ready = (
        pyocd_ok
        and pyserial_ok
        and board_config_ok
        and packs_ready
        and (probe_count or 0) > 0
        and (serial_count or 0) > 0
    )

    header("Summary")
    if host_ready:
        log(INFO, "Host prerequisites and board-target support are ready for stage0_check.py")
    elif not pyocd_ok or not pyserial_ok or not board_config_ok or not packs_ready:
        log(WARN, "Host is not fully ready for stage0_check.py yet")
    else:
        log(
            WARN,
            "Canonical env and board-target support are present, but attached hardware is not fully visible yet",
        )
    print("  This script does not verify flashing, UART behavior, or recovery on real hardware.")
    sys.exit(0 if host_ready else 1)


if __name__ == "__main__":
    main()
