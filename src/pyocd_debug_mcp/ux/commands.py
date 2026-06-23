"""Slash-command parsing for the interactive operator shell."""

from __future__ import annotations

from dataclasses import dataclass
import shlex


class ShellCommandError(RuntimeError):
    """Raised when a shell command cannot be parsed."""


@dataclass(frozen=True)
class TaskInput:
    task: str


@dataclass(frozen=True)
class SlashCommand:
    name: str
    args: tuple[str, ...]


def parse_shell_input(text: str) -> TaskInput | SlashCommand | None:
    stripped = text.strip()
    if not stripped:
        return None
    if not stripped.startswith("/"):
        return TaskInput(task=stripped)
    command_text = stripped[1:].strip()
    if not command_text:
        raise ShellCommandError("Empty slash command. Use `/help` to see available commands.")
    try:
        parts = shlex.split(command_text)
    except ValueError as exc:
        raise ShellCommandError(f"Could not parse command: {exc}") from exc
    if not parts:
        raise ShellCommandError("Empty slash command. Use `/help` to see available commands.")
    return SlashCommand(name=parts[0], args=tuple(parts[1:]))


HELP_TEXT = """\
Slash commands:
  /board <id>
  /provider <name>
  /model <name|default>
  /run <task>
  /benchmark case <case_id>
  /benchmark suite <suite_name>
  /history
  /show <session_id>
  /rerun <session_id>
  /artifacts [session_id]
  /raw on|off|last
  /help
  /quit
"""
