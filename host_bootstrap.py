#!/usr/bin/env python3
"""
Host-level readiness checks that should run before board-level Stage 0 validation.

This script does not claim a board works. It only checks whether the host can:
- run pyOCD
- enumerate probes
- enumerate serial ports
- load board configs
- check/install target packs referenced by board configs

It may optionally install missing Python dependencies and missing pyOCD packs.
It does not install OS drivers or vendor probe software.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
INFO = "INFO"

DEFAULT_BOARD_CONFIG_DIR = Path(__file__).resolve().parent / "boards"  # PROJECT-DEFINED (repo layout)
BOARD_CONFIG_SUFFIXES = {".json", ".yaml", ".yml"}  # PROJECT-DEFINED (supported config formats)


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class DependencySpec:
    package_name: str
    import_name: str
    required: bool
    reason: str


@dataclass(frozen=True)
class BoardHostSpec:
    board_id: str
    display_name: str
    pyocd_target: str
    pack_name: str
    source_path: Path


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
)


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


def package_installed(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


def pip_install(package_names: list[str]) -> bool:
    if not package_names:
        return True
    cmd = [sys.executable, "-m", "pip", "install", *package_names]
    print(f"  Attempting: {' '.join(cmd)}")
    rc, _, _ = run(cmd, capture=False)
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
            ok = pip_install(install_list)
            if ok:
                log(PASS, f"Installed packages: {', '.join(install_list)}")
            else:
                log(FAIL, f"Failed to install packages: {', '.join(install_list)}")
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


def serial_summary(pyserial_ok: bool):
    header("Serial ports")
    if not pyserial_ok:
        log(FAIL, "pyserial missing - cannot enumerate serial ports")
        return

    ports = list_serial_ports()
    if ports is None:
        log(FAIL, "pyserial import failed during serial enumeration")
        return
    if not ports:
        log(WARN, "No serial ports detected")
        return

    log(PASS, f"Detected {len(ports)} serial port(s)")
    for port in ports:
        print(f"    - {port}")


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


def pyocd_summary(pyocd_ok: bool):
    header("pyOCD host visibility")
    if not pyocd_ok:
        log(FAIL, "pyocd missing - cannot enumerate probes or targets")
        return

    rc, out, err = run(["pyocd", "--version"])
    if rc == 0:
        log(PASS, f"pyOCD found: {out.strip()}")
    else:
        log(FAIL, f"pyOCD command failed: {(err or out).strip()[:300]}")
        return

    probes = list_probes()
    if probes:
        log(PASS, f"Detected {len(probes)} probe(s)")
        for probe in probes:
            desc = probe.description or probe.raw
            suffix = f" [{probe.state}]" if probe.state else ""
            print(f"    - {probe.uid or '(no uid)'} :: {desc}{suffix}")
    else:
        log(WARN, "No debug probes detected by pyOCD")
        print("      This usually means an OS driver / vendor tooling / USB enumeration issue, not a board-config issue.")


def load_board_config_document(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise ConfigError(
                f"PyYAML is required to load {path.name}. Install it with 'pip install pyyaml' or use JSON."
            ) from exc
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        raise ConfigError(f"Unsupported board config format for {path}. Use .json, .yaml, or .yml.")

    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a single object")
    return data


def iter_board_config_paths(board_config_dir: Path) -> list[Path]:
    if not board_config_dir.exists():
        raise ConfigError(f"Board config directory not found: {board_config_dir}")
    if not board_config_dir.is_dir():
        raise ConfigError(f"Board config path is not a directory: {board_config_dir}")

    return [
        path.resolve()
        for path in sorted(board_config_dir.iterdir())
        if path.is_file() and path.suffix.lower() in BOARD_CONFIG_SUFFIXES
    ]


def preview_board_config_paths(board_config_dir: Path) -> list[Path]:
    if not board_config_dir.exists() or not board_config_dir.is_dir():
        return []
    return [
        path.resolve()
        for path in sorted(board_config_dir.iterdir())
        if path.is_file() and path.suffix.lower() in BOARD_CONFIG_SUFFIXES
    ]


def load_board_specs(board_config_dir: Path, extra_paths: list[Path], selected_ids: list[str]) -> list[BoardHostSpec]:
    default_paths = [
        path
        for path in iter_board_config_paths(board_config_dir)
        if not path.stem.startswith("example_")
    ]
    merged_paths = default_paths + extra_paths

    boards: list[BoardHostSpec] = []
    seen_ids: set[str] = set()
    for path in merged_paths:
        data = load_board_config_document(path)
        for field in ("board_id", "display_name", "pyocd_target"):
            if not data.get(field):
                raise ConfigError(f"{path} is missing required field '{field}'")
        board_id = str(data["board_id"]).strip().lower()
        if board_id in seen_ids:
            raise ConfigError(f"Duplicate board_id detected: {board_id}")
        seen_ids.add(board_id)
        boards.append(
            BoardHostSpec(
                board_id=board_id,
                display_name=str(data["display_name"]).strip(),
                pyocd_target=str(data["pyocd_target"]).strip(),
                pack_name=str(data.get("pack_name") or data["pyocd_target"]).strip(),
                source_path=path,
            )
        )

    if selected_ids:
        requested = [board_id.strip().lower() for board_id in selected_ids if board_id.strip()]
        boards = [board for board in boards if board.board_id in requested]
        missing = sorted(set(requested) - {board.board_id for board in boards})
        if missing:
            raise ConfigError(f"Requested board_id values not found: {', '.join(missing)}")

    return boards


def board_config_summary(boards: list[BoardHostSpec]):
    header("Board configs")
    if not boards:
        log(WARN, "No board configs selected")
        return

    log(PASS, f"Loaded {len(boards)} board config(s)")
    for board in boards:
        print(f"    - {board.board_id} :: {board.display_name} :: target={board.pyocd_target} :: pack={board.pack_name}")


def target_pack_summary(boards: list[BoardHostSpec], pyocd_ok: bool, install_packs: bool):
    header("Target packs")
    if not boards:
        log(WARN, "No board configs selected - skipping pack checks")
        return
    if not pyocd_ok:
        log(FAIL, "pyocd missing - cannot check target packs")
        return

    _, out, _ = run(["pyocd", "list", "--targets"])
    installed_targets = out.lower()

    for board in boards:
        target_present = board.pyocd_target.lower() in installed_targets
        if target_present:
            log(PASS, f"{board.board_id}: target '{board.pyocd_target}' available")
            continue

        log(WARN, f"{board.board_id}: target '{board.pyocd_target}' not found")
        if install_packs:
            print(f"  Attempting: pyocd pack install {board.pack_name}")
            rc, _, _ = run(["pyocd", "pack", "install", board.pack_name], capture=False)
            if rc == 0:
                _, refreshed, _ = run(["pyocd", "list", "--targets"])
                ok = board.pyocd_target.lower() in refreshed.lower()
                log(PASS if ok else FAIL, f"{board.board_id}: pack install {'succeeded' if ok else 'did not expose target'}")
            else:
                log(FAIL, f"{board.board_id}: pack install failed")
        else:
            print(f"      Fix: pyocd pack install {board.pack_name}")


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
        help="Install missing Python dependencies with pip.",
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

    dependency_results = dependency_summary(require_yaml=require_yaml, install_missing=args.install_missing)
    pyocd_ok = dependency_results.get("pyocd", False)
    pyserial_ok = dependency_results.get("pyserial", False)

    pyocd_summary(pyocd_ok)
    serial_summary(pyserial_ok)

    boards: list[BoardHostSpec] = []
    try:
        boards = load_board_specs(board_config_dir, extra_paths, args.board_id)
    except ConfigError as exc:
        header("Board configs")
        log(FAIL, str(exc))

    board_config_summary(boards)
    target_pack_summary(boards, pyocd_ok=pyocd_ok, install_packs=args.install_packs)

    header("Summary")
    if not pyocd_ok or not pyserial_ok:
        log(WARN, "Host is not fully ready for stage0_check.py yet")
    else:
        log(INFO, "If probes and serial ports are visible above, proceed to stage0_check.py for board-level validation")
    print("  This script does not verify flashing, UART behavior, or recovery on real hardware.")


if __name__ == "__main__":
    main()
