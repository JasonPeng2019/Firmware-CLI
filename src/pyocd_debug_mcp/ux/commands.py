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
    arg_text: str = ""


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
    first_token = parts[0]
    arg_text = command_text[len(first_token) :].lstrip()
    return SlashCommand(name=first_token, args=tuple(parts[1:]), arg_text=arg_text)


HELP_TEXT = """\
Slash commands:
  /board <id>
  /provider <name>
  /model <name|default>
  /workspace <path|clear>
  /build-command "<cmd>"|clear
  /flash-artifact <path|default>
  /elf <path|default>
  /run <task>
  /verify [extra text]
  /diagnose [extra text]
  /repair [extra text]
  /benchmark case <case_id>
  /benchmark suite <suite_name>
  /history
  /show <session_id>
  /rerun <session_id>
  /artifacts [session_id]
  /prompt [session_id]
  /diff [session_id]
  /serial [session_id]
  /score [session_id]
  /events [session_id]
  /raw on|off|last
  /help
  /quit
"""
