"""Claude Code CLI-backed decision provider for the turnkey brain."""

from __future__ import annotations

import json
import subprocess
import tempfile

import anyio

from pyocd_debug_mcp.brain.provider_parsing import parse_turn_decision_json
from pyocd_debug_mcp.brain.provider_types import ProviderTurn
from pyocd_debug_mcp.timeouts import PROVIDER_REQUEST_TIMEOUT_SECONDS


class ProviderResponseError(RuntimeError):
    """Raised when Claude Code does not return a valid structured action."""


class ClaudeCLIDecisionProvider:
    """Decision provider that shells out to `claude --print`."""

    def __init__(
        self,
        *,
        model: str | None,
        timeout_seconds: float = PROVIDER_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def next_decision(self, *, instructions: str, turn_prompt: str) -> ProviderTurn:
        return await anyio.to_thread.run_sync(self._next_decision_sync, instructions, turn_prompt)

    def _next_decision_sync(self, instructions: str, turn_prompt: str) -> ProviderTurn:
        last_error: Exception | None = None
        current_prompt = turn_prompt
        for _attempt in range(2):
            with tempfile.TemporaryDirectory(prefix="pyocd-turnkey-claude-") as tmpdir:
                try:
                    result = subprocess.run(
                        _build_claude_command(model=self._model, instructions=instructions, prompt=current_prompt),
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        capture_output=True,
                        cwd=tmpdir,
                        check=False,
                        timeout=self._timeout_seconds,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise ProviderResponseError(
                        f"Claude CLI timed out after {self._timeout_seconds:.0f}s."
                    ) from exc
                output_text, command_error = _extract_claude_output_text(result)
                if command_error is not None:
                    last_error = command_error
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
        "json",
        "--append-system-prompt",
        instructions,
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    return command


def _extract_claude_output_text(
    result: subprocess.CompletedProcess[str],
) -> tuple[str, ProviderResponseError | None]:
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if not stdout:
        if result.returncode != 0:
            return "", ProviderResponseError(stderr or "Claude CLI returned no output.")
        return "", ProviderResponseError("Claude CLI returned an empty response.")

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        if result.returncode != 0:
            return "", ProviderResponseError(stdout or stderr or "Claude CLI request failed.")
        return stdout, None

    if isinstance(payload, dict):
        if payload.get("is_error") is True:
            message = str(payload.get("result") or payload)
            return "", ProviderResponseError(message)
        result_text = payload.get("result")
        if isinstance(result_text, str) and result_text.strip():
            return result_text.strip(), None

    if result.returncode != 0:
        return "", ProviderResponseError(stdout or stderr or "Claude CLI request failed.")
    return "", ProviderResponseError("Claude CLI returned an unrecognized JSON response.")
