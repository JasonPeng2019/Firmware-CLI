"""Codex CLI-backed decision provider for the turnkey brain."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

import anyio

from pyocd_debug_mcp.brain.provider_parsing import parse_turn_decision_json
from pyocd_debug_mcp.brain.provider_types import ProviderTurn
from pyocd_debug_mcp.timeouts import PROVIDER_REQUEST_TIMEOUT_SECONDS


class ProviderResponseError(RuntimeError):
    """Raised when Codex CLI does not return a valid structured action."""


class CodexCLIDecisionProvider:
    """Decision provider that shells out to `codex exec`."""

    def __init__(
        self,
        *,
        model: str | None,
        timeout_seconds: float = PROVIDER_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def next_decision(
        self,
        *,
        instructions: str,
        turn_prompt: str,
        timeout_seconds: float | None = None,
    ) -> ProviderTurn:
        effective_timeout = self._timeout_seconds if timeout_seconds is None else timeout_seconds
        return await anyio.to_thread.run_sync(
            self._next_decision_sync,
            instructions,
            turn_prompt,
            effective_timeout,
        )

    def _next_decision_sync(
        self,
        instructions: str,
        turn_prompt: str,
        timeout_seconds: float | None = None,
    ) -> ProviderTurn:
        effective_timeout = self._timeout_seconds if timeout_seconds is None else timeout_seconds
        last_error: Exception | None = None
        current_prompt = turn_prompt
        for _attempt in range(2):
            with tempfile.TemporaryDirectory(prefix="pyocd-turnkey-codex-") as tmpdir:
                tmp_path = Path(tmpdir)
                output_path = tmp_path / "turn_decision.json"
                prompt_text = _compose_prompt(instructions, current_prompt)
                try:
                    result = subprocess.run(
                        _build_codex_command(
                            model=self._model,
                            working_dir=tmp_path,
                            output_path=output_path,
                        ),
                        input=prompt_text,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        capture_output=True,
                        check=False,
                        timeout=effective_timeout,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise ProviderResponseError(
                        f"Codex CLI timed out after {effective_timeout:.0f}s."
                    ) from exc
                output_text = (
                    output_path.read_text(encoding="utf-8")
                    if output_path.exists()
                    else result.stdout.strip()
                )
                if result.returncode != 0 and not output_text:
                    last_error = ProviderResponseError(result.stderr.strip() or result.stdout.strip())
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
            f"Codex CLI provider did not return a valid turnkey action: {last_error}"
        )


def _build_codex_command(
    *,
    model: str | None,
    working_dir: Path,
    output_path: Path,
) -> list[str]:
    command = [
        "codex",
        "-a",
        "never",
        "-s",
        "danger-full-access",
        "exec",
        "-C",
        str(working_dir),
        "--skip-git-repo-check",
        "--ignore-rules",
        "--ephemeral",
        "--color",
        "never",
        "-o",
        str(output_path),
    ]
    if model:
        command.extend(["--model", model])
    command.append("-")
    return command


def _compose_prompt(instructions: str, turn_prompt: str) -> str:
    return f"{instructions.strip()}\n\n{turn_prompt.strip()}\n"
