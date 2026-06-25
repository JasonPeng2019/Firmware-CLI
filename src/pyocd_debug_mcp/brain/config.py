"""Config and invocation models for the turnkey brain."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Literal, cast

from pyocd_debug_mcp.local_env import load_local_env

TurnkeyMode = Literal["freeform", "benchmark"]
TurnkeyProviderKind = Literal["openai-api", "anthropic-api", "codex-cli", "claude-cli"]


class BrainConfigError(RuntimeError):
    """Raised when the turnkey brain's BYOK/provider config is incomplete."""


@dataclass(frozen=True)
class BrainProviderConfig:
    provider: TurnkeyProviderKind
    model: str | None
    api_key: str | None = None


@dataclass(frozen=True)
class TurnkeyInvocation:
    mode: TurnkeyMode
    provider: TurnkeyProviderKind
    board_id: str
    task: str
    model: str | None
    max_iters: int
    serial_read_seconds: float
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
) -> BrainProviderConfig:
    load_local_env()
    provider = cast_provider(
        (provider_override or os.environ.get("PYOCD_TURNKEY_PROVIDER") or "openai-api").strip()
    )
    model = (model_override or os.environ.get("PYOCD_TURNKEY_MODEL") or "").strip() or None

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
        return BrainProviderConfig(provider=provider, api_key=api_key, model=model)

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
        return BrainProviderConfig(provider=provider, api_key=api_key, model=model)

    if provider == "codex-cli":
        _require_executable("codex", provider)
        return BrainProviderConfig(provider=provider, model=model)

    if provider == "claude-cli":
        _require_executable("claude", provider)
        return BrainProviderConfig(provider=provider, model=model)

    raise BrainConfigError(f"Unsupported turnkey provider: {provider}")


def cast_provider(raw_provider: str) -> TurnkeyProviderKind:
    candidate = raw_provider.strip().lower()
    if candidate in {"openai-api", "anthropic-api", "codex-cli", "claude-cli"}:
        return cast(TurnkeyProviderKind, candidate)
    raise BrainConfigError(
        "Unsupported provider. Use one of: openai-api, anthropic-api, codex-cli, claude-cli."
    )


def build_turnkey_invocation(
    *,
    mode: TurnkeyMode,
    provider: TurnkeyProviderKind,
    board_id: str,
    task: str,
    model: str | None,
    max_iters: int,
    serial_read_seconds: float,
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
) -> TurnkeyInvocation:
    normalized_model = model.strip() if model is not None and model.strip() else None
    return TurnkeyInvocation(
        mode=mode,
        provider=provider,
        board_id=board_id.strip().lower(),
        task=task.strip(),
        model=normalized_model,
        max_iters=max_iters,
        serial_read_seconds=serial_read_seconds,
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
    )
