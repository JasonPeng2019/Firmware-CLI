"""Config and invocation models for the turnkey brain."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Literal, cast

from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.local_env import load_local_env
from pyocd_debug_mcp.timeouts import (
    PROVIDER_REQUEST_TIMEOUT_SECONDS,
    TurnkeyTimeoutConfig,
    default_turnkey_timeout_config,
)

TurnkeyMode = Literal["freeform", "benchmark"]
TurnkeyProviderKind = Literal["openai-api", "anthropic-api", "codex-cli", "claude-cli"]
TurnkeyMemoryMode = Literal["deterministic", "model-summary"]

DEFAULT_TURNKEY_MEMORY_MODE: TurnkeyMemoryMode = "deterministic"
DEFAULT_TURNKEY_NATIVE_SYNC_EVERY = 4


class BrainConfigError(RuntimeError):
    """Raised when the turnkey brain's BYOK/provider config is incomplete."""


@dataclass(frozen=True)
class BrainProviderConfig:
    provider: TurnkeyProviderKind
    model: str | None
    api_key: str | None = None
    timeout_seconds: float = PROVIDER_REQUEST_TIMEOUT_SECONDS


@dataclass(frozen=True)
class TurnkeyInvocation:
    mode: TurnkeyMode
    provider: TurnkeyProviderKind
    board_id: str
    task: str
    model: str | None
    max_iters: int
    serial_read_seconds: float
    memory_mode: TurnkeyMemoryMode
    native_sync_every: int
    port: str | None = None
    flash_artifact: Path | None = None
    elf: Path | None = None
    workspace_root: Path | None = None
    build_command: str | None = None
    case_id: str | None = None
    case_kind: str | None = None
    expected_uart_substring: str | None = None
    expected_symbol_name: str | None = None
    expected_symbol_value_u32: int | None = None
    code_edits_allowed: bool = False
    allowed_edit_roots: tuple[str, ...] = ()
    recover_allowed: bool = True
    timeout_config: TurnkeyTimeoutConfig = field(default_factory=default_turnkey_timeout_config)
    timeout_proposal: TimeoutProposal | None = None
    iteration_estimate: IterationEstimate | None = None

    @property
    def has_repair_context(self) -> bool:
        return self.workspace_root is not None and self.build_command is not None


def _normalize_optional_path(path_value: str | Path | None) -> Path | None:
    if path_value is None:
        return None
    return Path(path_value).expanduser().resolve()


def _require_executable(name: str, provider: TurnkeyProviderKind) -> None:
    if shutil.which(name) is None:
        raise BrainConfigError(
            f"{name} is required for provider '{provider}' but was not found in PATH."
        )


def load_provider_config(
    model_override: str | None = None,
    provider_override: TurnkeyProviderKind | None = None,
    provider_timeout_seconds: float | None = None,
) -> BrainProviderConfig:
    load_local_env()
    provider = cast_provider(
        (provider_override or os.environ.get("PYOCD_TURNKEY_PROVIDER") or "openai-api").strip()
    )
    model = (model_override or os.environ.get("PYOCD_TURNKEY_MODEL") or "").strip() or None

    timeout_seconds = (
        provider_timeout_seconds
        if provider_timeout_seconds is not None
        else PROVIDER_REQUEST_TIMEOUT_SECONDS
    )

    if provider == "openai-api":
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise BrainConfigError(
                "OPENAI_API_KEY is required for provider 'openai-api'. "
                "Set it in your environment or local .env."
            )
        if not model:
            raise BrainConfigError(
                "A model is required. Pass `--model` or set `PYOCD_TURNKEY_MODEL` in your environment or local .env."
            )
        return BrainProviderConfig(provider=provider, api_key=api_key, model=model, timeout_seconds=timeout_seconds)

    if provider == "anthropic-api":
        api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        if not api_key:
            raise BrainConfigError(
                "ANTHROPIC_API_KEY is required for provider 'anthropic-api'. "
                "Set it in your environment or local .env."
            )
        if not model:
            raise BrainConfigError(
                "A model is required. Pass `--model` or set `PYOCD_TURNKEY_MODEL` in your environment or local .env."
            )
        return BrainProviderConfig(provider=provider, api_key=api_key, model=model, timeout_seconds=timeout_seconds)

    if provider == "codex-cli":
        _require_executable("codex", provider)
        return BrainProviderConfig(provider=provider, model=model, timeout_seconds=timeout_seconds)

    if provider == "claude-cli":
        _require_executable("claude", provider)
        return BrainProviderConfig(provider=provider, model=model, timeout_seconds=timeout_seconds)

    raise BrainConfigError(f"Unsupported turnkey provider: {provider}")


def cast_provider(raw_provider: str) -> TurnkeyProviderKind:
    candidate = raw_provider.strip().lower()
    if candidate in {"openai-api", "anthropic-api", "codex-cli", "claude-cli"}:
        return cast(TurnkeyProviderKind, candidate)
    raise BrainConfigError(
        "Unsupported provider. Use one of: openai-api, anthropic-api, codex-cli, claude-cli."
    )


def cast_memory_mode(raw_mode: str) -> TurnkeyMemoryMode:
    candidate = raw_mode.strip().lower()
    if candidate in {"deterministic", "model-summary"}:
        return cast(TurnkeyMemoryMode, candidate)
    raise BrainConfigError(
        "Unsupported memory mode. Use one of: deterministic, model-summary."
    )


def resolve_memory_mode(memory_mode_override: str | None = None) -> TurnkeyMemoryMode:
    raw_value = memory_mode_override
    if raw_value is None:
        raw_value = os.environ.get("PYOCD_TURNKEY_MEMORY_MODE")
    if raw_value is None or not raw_value.strip():
        return DEFAULT_TURNKEY_MEMORY_MODE
    return cast_memory_mode(raw_value)


def resolve_native_sync_every(native_sync_every_override: int | None = None) -> int:
    if native_sync_every_override is not None:
        if native_sync_every_override < 0:
            raise BrainConfigError("native sync cadence must be 0 or a positive integer.")
        return native_sync_every_override
    raw_value = (os.environ.get("PYOCD_TURNKEY_NATIVE_SYNC_EVERY") or "").strip()
    if not raw_value:
        return DEFAULT_TURNKEY_NATIVE_SYNC_EVERY
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise BrainConfigError(
            "PYOCD_TURNKEY_NATIVE_SYNC_EVERY must be an integer >= 0."
        ) from exc
    if value < 0:
        raise BrainConfigError("PYOCD_TURNKEY_NATIVE_SYNC_EVERY must be >= 0.")
    return value


def build_turnkey_invocation(
    *,
    mode: TurnkeyMode,
    provider: TurnkeyProviderKind,
    board_id: str,
    task: str,
    model: str | None,
    max_iters: int,
    serial_read_seconds: float,
    memory_mode: TurnkeyMemoryMode | None = None,
    native_sync_every: int | None = None,
    port: str | None = None,
    flash_artifact: str | Path | None = None,
    elf: str | Path | None = None,
    workspace_root: str | Path | None = None,
    build_command: str | None = None,
    case_id: str | None = None,
    case_kind: str | None = None,
    expected_uart_substring: str | None = None,
    expected_symbol_name: str | None = None,
    expected_symbol_value_u32: int | None = None,
    code_edits_allowed: bool = False,
    allowed_edit_roots: tuple[str, ...] = (),
    recover_allowed: bool = True,
    timeout_config: TurnkeyTimeoutConfig | None = None,
    timeout_proposal: TimeoutProposal | None = None,
    iteration_estimate: IterationEstimate | None = None,
) -> TurnkeyInvocation:
    if max_iters <= 0:
        raise BrainConfigError("max_iters must be > 0.")
    if serial_read_seconds <= 0:
        raise BrainConfigError("serial_read_seconds must be > 0.")
    normalized_model = model.strip() if model is not None and model.strip() else None
    return TurnkeyInvocation(
        mode=mode,
        provider=provider,
        board_id=board_id.strip().lower(),
        task=task.strip(),
        model=normalized_model,
        max_iters=max_iters,
        serial_read_seconds=serial_read_seconds,
        memory_mode=resolve_memory_mode(memory_mode),
        native_sync_every=resolve_native_sync_every(native_sync_every),
        port=(port or None),
        flash_artifact=_normalize_optional_path(flash_artifact),
        elf=_normalize_optional_path(elf),
        workspace_root=_normalize_optional_path(workspace_root),
        build_command=build_command,
        case_id=case_id,
        case_kind=case_kind,
        expected_uart_substring=expected_uart_substring,
        expected_symbol_name=expected_symbol_name,
        expected_symbol_value_u32=expected_symbol_value_u32,
        code_edits_allowed=code_edits_allowed,
        allowed_edit_roots=allowed_edit_roots,
        recover_allowed=recover_allowed,
        timeout_config=timeout_config or default_turnkey_timeout_config(),
        timeout_proposal=timeout_proposal,
        iteration_estimate=iteration_estimate,
    )
