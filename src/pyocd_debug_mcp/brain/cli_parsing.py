"""Shared CLI parsing helpers for turnkey planning-hook arguments."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
from typing import Any, cast

from pyocd_debug_mcp.brain.config import BrainConfigError
from pyocd_debug_mcp.brain.decision_types import IterationEstimate, TimeoutProposal
from pyocd_debug_mcp.timeouts import (
    TurnkeyTimeoutConfig,
    TurnkeyTimeoutUpdate,
    apply_turnkey_timeout_update,
    default_turnkey_timeout_config,
)


def parse_json_object(raw: str, *, flag_name: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BrainConfigError(f"{flag_name} must be valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise BrainConfigError(f"{flag_name} must decode to a JSON object.")
    return payload


def parse_timeout_config_json(raw: str | None) -> TurnkeyTimeoutConfig | None:
    if raw is None:
        return None
    payload = parse_json_object(raw, flag_name="--timeout-config-json")
    allowed_fields = {field.name for field in fields(TurnkeyTimeoutUpdate)}
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise BrainConfigError(
            "--timeout-config-json contains unsupported keys: " + ", ".join(unknown_fields)
        )
    try:
        update = TurnkeyTimeoutUpdate(**cast(dict[str, Any], payload))
        return apply_turnkey_timeout_update(default_turnkey_timeout_config(), update)
    except (TypeError, ValueError) as exc:
        raise BrainConfigError(f"--timeout-config-json is invalid: {exc}") from exc


def parse_timeout_proposal_json(raw: str | None) -> TimeoutProposal | None:
    if raw is None:
        return None
    payload = parse_json_object(raw, flag_name="--timeout-proposal-json")
    try:
        return TimeoutProposal.model_validate(payload)
    except Exception as exc:
        raise BrainConfigError(f"--timeout-proposal-json is invalid: {exc}") from exc


def parse_iteration_estimate_json(raw: str | None) -> IterationEstimate | None:
    if raw is None:
        return None
    payload = parse_json_object(raw, flag_name="--iteration-estimate-json")
    try:
        return IterationEstimate.model_validate(payload)
    except Exception as exc:
        raise BrainConfigError(f"--iteration-estimate-json is invalid: {exc}") from exc


def add_planning_hook_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--timeout-config-json",
        help="Optional JSON object of turnkey timeout overrides applied over repo defaults.",
    )
    parser.add_argument(
        "--timeout-proposal-json",
        help="Optional JSON object carrying the future model timeout proposal shape.",
    )
    parser.add_argument(
        "--iteration-estimate-json",
        help="Optional JSON object carrying the future model iteration-estimate shape.",
    )
