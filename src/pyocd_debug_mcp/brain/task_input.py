"""Shared task-text ingestion helpers for turnkey CLIs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TextIO

from pyocd_debug_mcp.brain.config import BrainConfigError


def add_task_input_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the mutually exclusive task-text source arguments to a run parser."""

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", help="Inline task text for simple prompts.")
    group.add_argument(
        "--task-file",
        metavar="PATH",
        help="Read task text from a UTF-8 file. Use this for long prompts or JSON examples.",
    )
    group.add_argument(
        "--task-stdin",
        action="store_true",
        help="Read task text from stdin. Use this with shell pipes or redirected files.",
    )


def resolve_task_input(args: argparse.Namespace, *, stdin: TextIO | None = None) -> str:
    """Resolve task text from exactly one CLI source.

    Argparse enforces exclusivity for normal CLI use. This helper also tolerates
    hand-built Namespace objects in tests and callers by checking attributes
    defensively.
    """

    task = getattr(args, "task", None)
    task_file = getattr(args, "task_file", None)
    task_stdin = bool(getattr(args, "task_stdin", False))
    selected = sum(value is not None for value in (task, task_file)) + int(task_stdin)
    if selected != 1:
        raise BrainConfigError("Provide exactly one of --task, --task-file, or --task-stdin.")
    if task is not None:
        return _non_empty_task_text(task, source="--task")
    if task_file is not None:
        try:
            text = Path(task_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise BrainConfigError(f"--task-file could not be read: {exc}") from exc
        return _non_empty_task_text(text, source="--task-file")
    text = (stdin or sys.stdin).read()
    return _non_empty_task_text(text, source="--task-stdin")


def _non_empty_task_text(text: str, *, source: str) -> str:
    if not text.strip():
        raise BrainConfigError(f"{source} provided empty task text.")
    return text
