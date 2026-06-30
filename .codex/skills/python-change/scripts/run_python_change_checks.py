from __future__ import annotations

import argparse
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


COMMANDS = (
    "uv run ruff check --fix .",
    "uv run ruff format .",
    "uv run pyright --outputjson",
    "uv run pytest -q",
)


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    duration_s: float
    output: str


def is_repo_root(path: Path) -> bool:
    return (path / "pyproject.toml").is_file() and (path / ".codex" / "skills").is_dir()


def repo_root(start: Path | None = None) -> Path:
    here = start or Path(__file__).resolve()
    for parent in (here, *here.parents):
        if is_repo_root(parent):
            return parent
        candidate = parent / "Firmware-CLI"
        if is_repo_root(candidate):
            return candidate
    raise RuntimeError("Could not locate the Firmware-CLI repo root")


def run_command(command: str, cwd: Path) -> CommandResult:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    duration_s = time.perf_counter() - started
    output = (completed.stdout or "") + (completed.stderr or "")
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        duration_s=duration_s,
        output=output,
    )


def print_result(result: CommandResult) -> None:
    status = "PASS" if result.returncode == 0 else "FAIL"
    print(f"[{status}] {result.command} ({result.duration_s:.2f}s)")
    if result.output.strip():
        print(result.output.rstrip())
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the required Firmware-CLI Python-change validation gate."
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Directory to run checks from. Defaults to the Firmware-CLI repo root.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Run every command even if an earlier command fails.",
    )
    args = parser.parse_args()

    cwd = args.cwd.resolve() if args.cwd is not None else repo_root()
    results: list[CommandResult] = []

    for command in COMMANDS:
        result = run_command(command, cwd)
        results.append(result)
        print_result(result)
        if result.returncode != 0 and not args.continue_on_error:
            break

    print("Summary:")
    for result in results:
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"- {status} | {result.duration_s:.2f}s | {result.command}")

    return 0 if all(result.returncode == 0 for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
