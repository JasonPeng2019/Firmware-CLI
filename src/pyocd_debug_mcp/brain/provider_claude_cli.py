"""Claude Code CLI-backed decision provider for the turnkey brain."""

from __future__ import annotations

import subprocess
import tempfile

import anyio

from pyocd_debug_mcp.brain.provider_parsing import parse_turn_decision_json
from pyocd_debug_mcp.brain.provider_types import ProviderTurn


class ProviderResponseError(RuntimeError):
    """Raised when Claude Code does not return a valid structured action."""


class ClaudeCLIDecisionProvider:
    """Decision provider that shells out to `claude --print`."""

    def __init__(self, *, model: str | None) -> None:
        self._model = model

    async def next_decision(self, *, instructions: str, turn_prompt: str) -> ProviderTurn:
        return await anyio.to_thread.run_sync(self._next_decision_sync, instructions, turn_prompt)

    def _next_decision_sync(self, instructions: str, turn_prompt: str) -> ProviderTurn:
        last_error: Exception | None = None
        current_prompt = turn_prompt
        for _attempt in range(2):
            with tempfile.TemporaryDirectory(prefix="pyocd-turnkey-claude-") as tmpdir:
                result = subprocess.run(
                    _build_claude_command(model=self._model, instructions=instructions, prompt=current_prompt),
                    text=True,
                    capture_output=True,
                    cwd=tmpdir,
                    check=False,
                )
                output_text = result.stdout.strip()
                if result.returncode != 0 and not output_text:
                    last_error = ProviderResponseError(result.stderr.strip())
                    current_prompt = (
                        f"{turn_prompt}\n\n"
                        "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                    )
                    continue
                try:
                    decision = parse_turn_decision_json(output_text)
                except Exception as exc:  # noqa: BLE001 - preserve parse failures
                    last_error = exc
                    current_prompt = (
                        f"{turn_prompt}\n\n"
                        "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                    )
                    continue
                return ProviderTurn(
                    decision=decision,
                    output_text=output_text,
                    response_id=None,
                )

        raise ProviderResponseError(
            f"Claude CLI provider did not return a valid turnkey action: {last_error}"
        )


def _build_claude_command(*, model: str | None, instructions: str, prompt: str) -> list[str]:
    command = [
        "claude",
        "--print",
        "--output-format",
        "text",
        "--append-system-prompt",
        instructions,
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    return command
