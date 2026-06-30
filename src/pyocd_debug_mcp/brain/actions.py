"""Structured action/result contracts for the turnkey brain."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pyocd_debug_mcp.brain.decision_types import (
    ActionBatch,
    ActionCall,
    BoardDecision,
    EarlyExitVerdict,
    IterationEstimate,
    TimeoutProposal,
)

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
    "write_serial",
    "unlock_recover",
]

FinalStatus = Literal["fixed", "healthy_confirmed", "diagnosed_only", "unresolved", "blocked"]
Classification = Literal[
    "healthy", "code_bug", "observability_fault", "physical_fault", "tooling_failure"
]


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


class RunGreenCheckAction(_StrictModel):
    kind: Literal["run_green_check"] = "run_green_check"


class LoadSkillsAction(_StrictModel):
    kind: Literal["load_skills"] = "load_skills"
    skill_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_skill_ids(self) -> LoadSkillsAction:
        normalized = tuple(skill_id.strip() for skill_id in self.skill_ids)
        if any(not skill_id for skill_id in normalized):
            raise ValueError("skill_ids must contain non-empty skill IDs.")
        self.skill_ids = normalized
        return self


class WaitAction(_StrictModel):
    kind: Literal["wait"] = "wait"
    seconds: float = Field(gt=0, le=30)


class RunScriptAction(_StrictModel):
    kind: Literal["run_script"] = "run_script"
    name: str = Field(min_length=1)
    inputs: dict[str, object] = Field(default_factory=dict)


class FinalizeAction(_StrictModel):
    kind: Literal["finalize"] = "finalize"
    final_status: FinalStatus
    classification: Classification
    root_cause: str
    summary: str


ActionUnion = Annotated[
    ServerToolAction
    | LoadSkillsAction
    | RunGreenCheckAction
    | WaitAction
    | RunScriptAction
    | FinalizeAction,
    Field(discriminator="kind"),
]


class TurnDecision(_StrictModel):
    observation_summary: str
    classification: Classification | None = None
    hypothesis: str | None = None
    strategy_evaluation: str | None = None
    action: ActionUnion | None = None
    action_batch: ActionBatch | None = None
    timeout_proposal: TimeoutProposal | None = None
    iteration_estimate: IterationEstimate | None = None

    @model_validator(mode="after")
    def _require_single_action_or_batch(self) -> TurnDecision:
        has_action = self.action is not None
        has_batch = self.action_batch is not None and bool(self.action_batch.calls)
        if has_action == has_batch:
            raise ValueError("Provide exactly one of action or non-empty action_batch.")
        return self


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
    return json.dumps(turn_decision_output_schema(), indent=2, sort_keys=True)


def result_schema_text() -> str:
    return json.dumps(TurnkeyRunResult.model_json_schema(), indent=2, sort_keys=True)


def turn_decision_output_schema() -> dict[str, object]:
    action_variants: list[dict[str, object]] = [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "tool_name", "arguments"],
            "properties": {
                "kind": {"type": "string", "const": "server_tool"},
                "tool_name": {
                    "type": "string",
                    "enum": [
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
                        "write_serial",
                        "unlock_recover",
                    ],
                },
                "arguments": {"type": "object", "additionalProperties": True},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "skill_ids"],
            "properties": {
                "kind": {"type": "string", "const": "load_skills"},
                "skill_ids": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "seconds"],
            "properties": {
                "kind": {"type": "string", "const": "wait"},
                "seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 30},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "name", "inputs"],
            "properties": {
                "kind": {"type": "string", "const": "run_script"},
                "name": {"type": "string", "minLength": 1},
                "inputs": {"type": "object", "additionalProperties": True},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind"],
            "properties": {
                "kind": {"type": "string", "const": "run_green_check"},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "final_status", "classification", "root_cause", "summary"],
            "properties": {
                "kind": {"type": "string", "const": "finalize"},
                "final_status": {
                    "type": "string",
                    "enum": [
                        "fixed",
                        "healthy_confirmed",
                        "diagnosed_only",
                        "unresolved",
                        "blocked",
                    ],
                },
                "classification": {
                    "type": "string",
                    "enum": [
                        "healthy",
                        "code_bug",
                        "observability_fault",
                        "physical_fault",
                        "tooling_failure",
                    ],
                },
                "root_cause": {"type": "string", "minLength": 1},
                "summary": {"type": "string", "minLength": 1},
            },
        },
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "TurnDecision",
        "type": "object",
        "additionalProperties": False,
        "required": ["observation_summary", "classification"],
        "properties": {
            "observation_summary": {"type": "string", "minLength": 1},
            "classification": {
                "type": ["string", "null"],
                "enum": [
                    "healthy",
                    "code_bug",
                    "observability_fault",
                    "physical_fault",
                    "tooling_failure",
                    None,
                ],
            },
            "hypothesis": {"type": ["string", "null"]},
            "strategy_evaluation": {"type": ["string", "null"]},
            "timeout_proposal": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "properties": {
                    "default_tool_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "connect_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "flash_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "recover_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "uart_read_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "uart_read_grace_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "build_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "batch_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "external_command_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "provider_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                    "mcp_startup_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
                },
            },
            "iteration_estimate": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "properties": {
                    "board_tool_calls": {"type": ["integer", "null"], "minimum": 0},
                    "debug_cycles": {"type": ["integer", "null"], "minimum": 0},
                    "false_termination_retries": {"type": ["integer", "null"], "minimum": 0},
                    "safety_buffer": {"type": ["integer", "null"], "minimum": 0},
                    "requested_max_iterations": {"type": ["integer", "null"], "minimum": 1},
                },
            },
            "action": {"oneOf": action_variants},
            "action_batch": {
                "type": "object",
                "additionalProperties": False,
                "required": ["calls"],
                "properties": {
                    "calls": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["action_type", "arguments"],
                            "properties": {
                                "action_type": {"type": "string", "minLength": 1},
                                "arguments": {"type": "object", "additionalProperties": True},
                            },
                        },
                    }
                },
            },
        },
        "oneOf": [{"required": ["action"]}, {"required": ["action_batch"]}],
    }


__all__ = [
    "ActionBatch",
    "ActionCall",
    "AllowedServerToolName",
    "BoardDecision",
    "Classification",
    "EarlyExitVerdict",
    "FinalizeAction",
    "IterationEstimate",
    "LoadSkillsAction",
    "RunGreenCheckAction",
    "RunScriptAction",
    "ServerToolAction",
    "TimeoutProposal",
    "TurnDecision",
    "TurnkeyRunResult",
    "VerificationSnapshot",
    "WaitAction",
    "decision_schema_text",
    "result_schema_text",
    "turn_decision_output_schema",
]
