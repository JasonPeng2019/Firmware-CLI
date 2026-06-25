"""Codex CLI-backed decision provider for the turnkey brain."""

from __future__ import annotations

from pathlib import Path
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
    ProviderPromptBundle,
    ProviderSessionState,
    ProviderTurn,
    render_memory_summary_request,
)
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
        base_prompt = prompt_bundle.full_prompt_text(include_memory=True)
        current_prompt = base_prompt
        for _attempt in range(2):
            with tempfile.TemporaryDirectory(prefix="pyocd-turnkey-codex-") as tmpdir:
                tmp_path = Path(tmpdir)
                output_path = tmp_path / "turn_decision.json"
                prompt_text = current_prompt
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
                        timeout=self._timeout_seconds,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise ProviderResponseError(
                        f"Codex CLI timed out after {self._timeout_seconds:.0f}s."
                    ) from exc
                output_text = (
                    output_path.read_text(encoding="utf-8")
                    if output_path.exists()
                    else result.stdout.strip()
                )
                if result.returncode != 0 and not output_text:
                    last_error = ProviderResponseError(result.stderr.strip() or result.stdout.strip())
                    current_prompt = (
                        f"{base_prompt}\n\n"
                        "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
                    )
                    continue
                try:
                    decision = parse_turn_decision_json(output_text)
                except Exception as exc:  # noqa: BLE001 - preserve parse failures
                    last_error = exc
                    current_prompt = (
                        f"{base_prompt}\n\n"
                        "Your previous reply was invalid. Return only one JSON object that matches the schema exactly."
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
                            "cli_mode": "ephemeral",
                        }
                    ),
                    provider_metadata={
                        "continuation_kind": "transcript-memory",
                        "continuation_mode": self.capabilities.continuation_mode,
                        "continuation_path": "transcript-memory",
                        "memory_injected": True,
                        "cli_mode": "ephemeral",
                    },
                )

        raise ProviderResponseError(
            f"Codex CLI provider did not return a valid turnkey action: {last_error}"
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
        for _attempt in range(2):
            with tempfile.TemporaryDirectory(prefix="pyocd-turnkey-codex-summary-") as tmpdir:
                tmp_path = Path(tmpdir)
                output_path = tmp_path / "memory_summary.json"
                try:
                    result = subprocess.run(
                        _build_codex_command(
                            model=self._model,
                            working_dir=tmp_path,
                            output_path=output_path,
                        ),
                        input=current_prompt,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        capture_output=True,
                        check=False,
                        timeout=self._timeout_seconds,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise ProviderResponseError(
                        f"Codex CLI memory summarizer timed out after {self._timeout_seconds:.0f}s."
                    ) from exc
                output_text = (
                    output_path.read_text(encoding="utf-8")
                    if output_path.exists()
                    else result.stdout.strip()
                )
                if result.returncode != 0 and not output_text:
                    last_error = ProviderResponseError(result.stderr.strip() or result.stdout.strip())
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
                        "provider": "codex-cli",
                        "model": self._model,
                        "cli_mode": "ephemeral",
                    },
                )
        raise ProviderResponseError(
            f"Codex CLI provider did not return a valid memory summary: {last_error}"
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
