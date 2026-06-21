"""Config and invocation models for the turnkey brain."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pyocd_debug_mcp.local_env import load_local_env

TurnkeyMode = Literal["freeform", "benchmark"]


class BrainConfigError(RuntimeError):
    """Raised when the turnkey brain's BYOK/provider config is incomplete."""


@dataclass(frozen=True)
class BrainProviderConfig:
    api_key: str
    model: str


@dataclass(frozen=True)
class TurnkeyInvocation:
    mode: TurnkeyMode
    board_id: str
    task: str
    model: str
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


def load_provider_config(model_override: str | None = None) -> BrainProviderConfig:
    load_local_env()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise BrainConfigError(
            "OPENAI_API_KEY is required for `pyocd-debug-brain`. "
            "Set it in your environment or local .env."
        )

    model = (model_override or os.environ.get("PYOCD_TURNKEY_MODEL") or "").strip()
    if not model:
        raise BrainConfigError(
            "A model is required. Pass `--model` or set `PYOCD_TURNKEY_MODEL` in your environment or local .env."
        )

    return BrainProviderConfig(api_key=api_key, model=model)


def build_turnkey_invocation(
    *,
    mode: TurnkeyMode,
    board_id: str,
    task: str,
    model: str,
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
    return TurnkeyInvocation(
        mode=mode,
        board_id=board_id.strip().lower(),
        task=task.strip(),
        model=model.strip(),
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


def task_requires_code_fix(task: str) -> bool:
    lowered = task.lower()
    return any(
        token in lowered
        for token in (
            "fix",
            "repair",
            "patch",
            "edit",
            "rewrite",
            "change the code",
            "modify the code",
        )
    )
