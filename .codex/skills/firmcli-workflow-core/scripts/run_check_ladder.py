from __future__ import annotations

import argparse
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


PRESETS = {
    "none": [],
    "default": [
        "uv run pytest -q",
        "uv run ruff check .",
        "uv run mypy src",
    ],
    "suite": [
        "uv run pytest -q",
        "uv run ruff check .",
        "uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py",
        "uv run pytest -q tests/test_r11_benchmark.py",
        "uv run python -m tests.harness.r11_benchmark --help",
    ],
}


@dataclass
class Result:
    command: str
    returncode: int
    duration_s: float
    output: str


def is_project_root(path: Path) -> bool:
    return (path / ".codex" / "skills").is_dir() and (path / "superpowers").is_dir()


def repo_root(start: Path | None = None) -> Path:
    here = start or Path(__file__).resolve()
    for parent in here.parents:
        if is_project_root(parent):
            return parent
        candidate = parent / "Firmware-CLI"
        if is_project_root(candidate):
            return candidate
    raise RuntimeError("Could not locate the Firmware-CLI project root")


def render_summary(results: list[Result]) -> str:
    lines = ["Summary:"]
    for result in results:
        status = "PASS" if result.returncode == 0 else "FAIL"
        lines.append(f"- {status} | {result.duration_s:.2f}s | {result.command}")
    return "\n".join(lines)


def render_report(results: list[Result]) -> str:
    sections = [render_summary(results), ""]
    for result in results:
        status = "PASS" if result.returncode == 0 else "FAIL"
        sections.append(f"== {status} :: {result.command} ==")
        sections.append(result.output.rstrip() or "[no output]")
        sections.append("")
    return "\n".join(sections).rstrip() + "\n"


def run_command(command: str, cwd: Path) -> Result:
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    duration = time.perf_counter() - start
    output = (completed.stdout or "") + (completed.stderr or "")
    return Result(command, completed.returncode, duration, output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Firmware-CLI non-hardware validation ladder."
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        default="default",
        help="Command preset to start from.",
    )
    parser.add_argument(
        "--command",
        action="append",
        default=[],
        help="Additional command to run after the preset commands. Repeat as needed.",
    )
    parser.add_argument(
        "--cwd",
        default=None,
        help="Working directory for the commands. Defaults to the Firmware-CLI project root.",
    )
    parser.add_argument(
        "--report-path",
        help="Optional file path to write the full report to.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failing command.",
    )
    args = parser.parse_args()

    cwd = repo_root() if args.cwd is None else Path(args.cwd).resolve()
    commands = list(PRESETS[args.preset]) + list(args.command)
    results: list[Result] = []

    for command in commands:
        result = run_command(command, cwd)
        results.append(result)
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"[{status}] {result.command} ({result.duration_s:.2f}s)")
        if result.output.strip():
            print(result.output.rstrip())
        print()
        if result.returncode != 0 and args.fail_fast:
            break

    report = render_report(results)
    print(render_summary(results))

    if args.report_path:
        target = Path(args.report_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report, encoding="utf-8")

    return 0 if all(result.returncode == 0 for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
