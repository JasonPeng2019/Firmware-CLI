"""Branch B action-boundary classification for turnkey execution."""

from __future__ import annotations

from typing import Literal

ActionClass = Literal["model_native_host", "brain_local", "client_action", "server_native"]

MODEL_NATIVE_HOST_ACTIONS = frozenset(
    {
        "read_file",
        "replace_file",
        "run_build",
        "run_green_check",
    }
)
BRAIN_LOCAL_ACTIONS = frozenset({"wait"})
CLIENT_ACTIONS = frozenset({"run_script"})
SERVER_NATIVE_ACTIONS = frozenset(
    {
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
    }
)

SERVER_TOOL_ACTION_PREFIX = "server_tool:"


def namespaced_server_tool_name(action_type: str) -> str | None:
    """Return the server tool selected by a `server_tool:<name>` action."""
    if not action_type.startswith(SERVER_TOOL_ACTION_PREFIX):
        return None
    tool_name = action_type.removeprefix(SERVER_TOOL_ACTION_PREFIX)
    if tool_name in SERVER_NATIVE_ACTIONS:
        return tool_name
    return None


def classify_action(action_type: str) -> ActionClass:
    if namespaced_server_tool_name(action_type) is not None:
        return "server_native"
    if action_type in MODEL_NATIVE_HOST_ACTIONS:
        return "model_native_host"
    if action_type in BRAIN_LOCAL_ACTIONS:
        return "brain_local"
    if action_type in CLIENT_ACTIONS:
        return "client_action"
    if action_type == "server_tool" or action_type in SERVER_NATIVE_ACTIONS:
        return "server_native"
    raise ValueError(f"Unsupported action type: {action_type}")
