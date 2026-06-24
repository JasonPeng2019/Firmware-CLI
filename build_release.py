#!/usr/bin/env python3
"""
Build a distributable, compiled binary of the `pyocd-debug` operator CLI.

Spike scope, see markdowns/curr/cli_distribution_spike_spec.md: packages only
`pyocd-debug` (src/pyocd_debug_mcp/ux/cli.py:main) via Nuitka, which compiles
through C to a native binary rather than bundling Python source/bytecode.

Versioning: the `[project].version` field in pyproject.toml is the single
source of truth. This script bumps the patch version automatically when the
content hash of `src/pyocd_debug_mcp/` differs from the last recorded build
(dist/.last_build_hash, gitignored); pass --bump/--set-version to override.

Platform limitation (VENDOR-FIXED, Nuitka): Nuitka does not cross-compile.
This script only ever produces a binary for the host OS/arch it runs on.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src" / "pyocd_debug_mcp"
ENTRY_POINT = SRC_DIR / "ux" / "cli.py"
PYPROJECT = REPO_ROOT / "pyproject.toml"
DIST_DIR = REPO_ROOT / "dist"
LAST_HASH_FILE = DIST_DIR / ".last_build_hash"

VERSION_RE = re.compile(r'^version = "(\d+)\.(\d+)\.(\d+)"$', re.MULTILINE)


class BuildError(RuntimeError):
    pass


def read_current_version() -> tuple[int, int, int]:
    text = PYPROJECT.read_text()
    match = VERSION_RE.search(text)
    if not match:
        raise BuildError(f"could not find a `version = \"X.Y.Z\"` line in {PYPROJECT}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def write_version(version: tuple[int, int, int]) -> None:
    text = PYPROJECT.read_text()
    new_text = VERSION_RE.sub(f'version = "{version[0]}.{version[1]}.{version[2]}"', text, count=1)
    PYPROJECT.write_text(new_text)


def bump(version: tuple[int, int, int], kind: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if kind == "major":
        return major + 1, 0, 0
    if kind == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def hash_source_tree() -> str:
    digest = hashlib.sha256()
    for path in sorted(SRC_DIR.rglob("*.py")):
        digest.update(str(path.relative_to(REPO_ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def read_last_hash() -> str | None:
    if not LAST_HASH_FILE.exists():
        return None
    return LAST_HASH_FILE.read_text().strip()


def write_last_hash(value: str) -> None:
    DIST_DIR.mkdir(exist_ok=True)
    LAST_HASH_FILE.write_text(value + "\n")


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def binary_name(version: tuple[int, int, int]) -> str:
    os_name = platform.system().lower()  # PROJECT-DEFINED: human-readable platform tag in the filename
    arch = platform.machine().lower()
    suffix = ".exe" if os_name == "windows" else ""
    return f"pyocd-debug-{version[0]}.{version[1]}.{version[2]}-{os_name}-{arch}{suffix}"


def run_nuitka(output_name: str) -> None:
    DIST_DIR.mkdir(exist_ok=True)
    cmd = [
        sys.executable,
        "-m", "nuitka",
        "--onefile",
        "--standalone",
        "--remove-output",
        "--no-pyi-file",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={output_name}",
        str(ENTRY_POINT),
    ]
    print("+ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        raise BuildError(f"nuitka build failed with exit code {result.returncode}")


def write_build_info(output_name: str, version: tuple[int, int, int]) -> None:
    info = {
        "version": f"{version[0]}.{version[1]}.{version[2]}",
        "git_commit": current_git_commit(),
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_os": platform.system(),
        "host_arch": platform.machine(),
        "entry_point": str(ENTRY_POINT.relative_to(REPO_ROOT)),
    }
    info_path = DIST_DIR / f"{output_name}.build_info.json"
    info_path.write_text(json.dumps(info, indent=2) + "\n")
    print(f"wrote {info_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", choices=["patch", "minor", "major"], help="force a version bump")
    parser.add_argument("--set-version", help="set an explicit X.Y.Z version instead of bumping")
    args = parser.parse_args(argv)

    try:
        current_version = read_current_version()
        source_hash = hash_source_tree()
        last_hash = read_last_hash()

        if args.set_version:
            parts = args.set_version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                raise BuildError("--set-version expects X.Y.Z with integer parts")
            target_version = (int(parts[0]), int(parts[1]), int(parts[2]))
        elif args.bump:
            target_version = bump(current_version, args.bump)
        elif last_hash is not None and last_hash == source_hash:
            print("no source changes since last build; reusing current version")
            target_version = current_version
        elif last_hash is None:
            print("no prior build recorded; building current version as-is")
            target_version = current_version
        else:
            target_version = bump(current_version, "patch")
            print("source changed since last build; bumping patch version")

        if target_version != current_version:
            write_version(target_version)
            print(f"version: {'.'.join(map(str, current_version))} -> {'.'.join(map(str, target_version))}")
        else:
            print(f"version: {'.'.join(map(str, target_version))} (unchanged)")

        output_name = binary_name(target_version)
        run_nuitka(output_name)
        write_build_info(output_name, target_version)
        write_last_hash(source_hash)

        print(f"\nbuilt: dist/{output_name}")
        return 0
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
