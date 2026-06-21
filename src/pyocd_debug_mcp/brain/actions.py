"""Structured action/result contracts for the turnkey brain."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

AllowedServerToolName = Literal[
    "connect",
    "disconnect",
    "get_board_info",
    "get_state",
    "halt",
    "resume",
    "reset",
    "read_core_register",
    "read_memory",
    "flash_firmware",
    "read_serial",
    "unlock_recover",
]

FinalStatus = Literal["fixed", "healthy_confirmed", "diagnosed_only", "unresolved", "blocked"]
Classification = Literal["healthy", "code_bug", "observability_fault", "physical_fault"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VerificationSnapshot(_StrictModel):
    flash_ok: bool = False
    uart_ok: bool = False
    symbol_ok: bool = False
    green_check_ok: bool = False


class ServerToolAction(_StrictModel):
    kind: Literal["server_tool"] = "server_tool"
    tool_name: AllowedServerToolName
    arguments: dict[str, object] = Field(default_factory=dict)


class ReadFileAction(_StrictModel):
    kind: Literal["read_file"] = "read_file"
    path: str


class ReplaceFileAction(_StrictModel):
    kind: Literal["replace_file"] = "replace_file"
    path: str
    content: str


class RunBuildAction(_StrictModel):
    kind: Literal["run_build"] = "run_build"
    build_command: str | None = None


class RunGreenCheckAction(_StrictModel):
    kind: Literal["run_green_check"] = "run_green_check"


class FinalizeAction(_StrictModel):
    kind: Literal["finalize"] = "finalize"
    final_status: FinalStatus
    classification: Classification
    root_cause: str
    summary: str


ActionUnion = Annotated[
    ServerToolAction
    | ReadFileAction
    | ReplaceFileAction
    | RunBuildAction
    | RunGreenCheckAction
    | FinalizeAction,
    Field(discriminator="kind"),
]


class TurnDecision(_StrictModel):
    observation_summary: str
    classification: Classification | None = None
    action: ActionUnion


class TurnkeyRunResult(_StrictModel):
    case_id: str | None = None
    board_id: str
    session_id: str | None = None
    final_status: FinalStatus
    classification: Classification
    root_cause: str
    actions_taken: list[str]
    mcp_tools_used: list[str]
    files_changed: list[str]
    recover_used: bool
    verification: VerificationSnapshot
    summary: str


def decision_schema_text() -> str:
    return json.dumps(TurnDecision.model_json_schema(), indent=2, sort_keys=True)


def result_schema_text() -> str:
    return json.dumps(TurnkeyRunResult.model_json_schema(), indent=2, sort_keys=True)
