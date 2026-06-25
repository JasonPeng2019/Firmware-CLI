"""Claude Code CLI-backed decision provider for the turnkey brain."""

from __future__ import annotations

import json
import subprocess
import tempfile

import anyio

from pyocd_debug_mcp.brain.provider_parsing import (
    parse_memory_summary_json,
    parse_turn_decision_json,
)
from pyocd_debug_mcp.brain.provider_types import (
    ProviderCapabilities,
    ProviderMemoryEntry,
    ProviderMemorySummaryResult,
    ProviderProgressUpdate,
    ProviderPromptBundle,
    ProviderSessionState,
    ProviderTurn,
    render_memory_summary_request,
)
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

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_native_session=False,
            supports_transcript_continuation=True,
            supports_response_id_continuation=False,
            supports_tool_schema_prompt=True,
            continuation_mode="transcript-only",
        )

    async def next_decision(
        self,
        *,
        prompt_bundle: ProviderPromptBundle,
        session_state: ProviderSessionState,
    ) -> ProviderTurn:
        return await anyio.to_thread.run_sync(
            self._next_decision_sync,
            prompt_bundle,
            session_state,
        )

    async def summarize_memory(
        self,
        *,
        session_state: ProviderSessionState,
        prior_summary_text: str,
        evicted_entries: tuple[ProviderMemoryEntry, ...],
    ) -> ProviderMemorySummaryResult:
        return await anyio.to_thread.run_sync(
            self._summarize_memory_sync,
            session_state,
            prior_summary_text,
            evicted_entries,
        )

    def _next_decision_sync(
        self,
        prompt_bundle: ProviderPromptBundle,
        session_state: ProviderSessionState,
    ) -> ProviderTurn:
        last_error: Exception | None = None
        retry_count = 0
        base_prompt = prompt_bundle.render_bootstrap_text(include_memory=True)
        current_prompt = base_prompt
        progress_updates: list[ProviderProgressUpdate] = [
            ProviderProgressUpdate(
                stage="provider_request",
                message="Dispatching Claude CLI turn from canonical local memory.",
                details={"continuation_path": "transcript-memory", "cli_mode": "print"},
            )
        ]
        for _attempt in range(2):
            with tempfile.TemporaryDirectory(prefix="pyocd-turnkey-claude-") as tmpdir:
                try:
                    result = subprocess.run(
                        _build_claude_command(
                            model=self._model,
                            instructions=prompt_bundle.system_instructions,
                            prompt=current_prompt,
                        ),
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
                    retry_count += 1
                    current_prompt = prompt_bundle.render_retry_text(
                        "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                    )
                    progress_updates.append(
                        ProviderProgressUpdate(
                            stage="provider_retry",
                            message="Claude CLI did not yield valid structured output; retrying with a schema-correction prompt.",
                            details={"retry_count": retry_count},
                        )
                    )
                    continue
                try:
                    decision = parse_turn_decision_json(output_text)
                except Exception as exc:  # noqa: BLE001 - preserve parse failures
                    last_error = exc
                    retry_count += 1
                    current_prompt = prompt_bundle.render_retry_text(
                        "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                    )
                    progress_updates.append(
                        ProviderProgressUpdate(
                            stage="provider_retry",
                            message="Claude CLI returned invalid JSON; retrying with a schema-correction prompt.",
                            details={"retry_count": retry_count},
                        )
                    )
                    continue
                return ProviderTurn(
                    decision=decision,
                    output_text=output_text,
                    response_id=None,
                    session_state=session_state.with_last_continuation_path(
                        "transcript-memory",
                    ).with_updated_metadata(
                        {
                            "continuation_kind": "transcript-memory",
                            "cli_mode": "print",
                        }
                    ),
                    provider_metadata={
                        "continuation_kind": "transcript-memory",
                        "continuation_mode": self.capabilities.continuation_mode,
                        "continuation_path": "transcript-memory",
                        "memory_injected": True,
                        "cli_mode": "print",
                        "prompt_render_mode": "bootstrap/full",
                        "static_tool_schema_injected": True,
                        "decision_schema_injected": True,
                        "retry_count": retry_count,
                    },
                    progress_updates=tuple(progress_updates),
                )

        raise ProviderResponseError(
            f"Claude CLI provider did not return a valid turnkey action: {last_error}"
        )

    def _summarize_memory_sync(
        self,
        session_state: ProviderSessionState,
        prior_summary_text: str,
        evicted_entries: tuple[ProviderMemoryEntry, ...],
    ) -> ProviderMemorySummaryResult:
        last_error: Exception | None = None
        prompt = render_memory_summary_request(
            prior_summary_text=prior_summary_text,
            evicted_entries=evicted_entries,
            summary_char_limit=session_state.summary_char_limit,
        )
        current_prompt = (
            f"{prompt}\n\n"
            "Return exactly one JSON object with a non-empty summary_text field."
        )
        system = "Return only one JSON object with a non-empty summary_text field."
        for _attempt in range(2):
            with tempfile.TemporaryDirectory(prefix="pyocd-turnkey-claude-summary-") as tmpdir:
                try:
                    result = subprocess.run(
                        _build_claude_command(
                            model=self._model,
                            instructions=system,
                            prompt=current_prompt,
                        ),
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
                        f"Claude CLI memory summarizer timed out after {self._timeout_seconds:.0f}s."
                    ) from exc
                output_text, command_error = _extract_claude_output_text(result)
                if command_error is not None:
                    last_error = command_error
                    current_prompt = (
                        f"{prompt}\n\n"
                        "Your previous reply was invalid. Return only one JSON object with a non-empty summary_text field."
                    )
                    continue
                try:
                    summary_text = parse_memory_summary_json(output_text)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    current_prompt = (
                        f"{prompt}\n\n"
                        "Your previous reply was invalid. Return only one JSON object with a non-empty summary_text field."
                    )
                    continue
                return ProviderMemorySummaryResult(
                    summary_text=summary_text,
                    provider_metadata={
                        "continuation_path": "summary-call",
                        "provider": "claude-cli",
                        "model": self._model,
                        "cli_mode": "print",
                    },
                )
        raise ProviderResponseError(
            f"Claude CLI provider did not return a valid memory summary: {last_error}"
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
