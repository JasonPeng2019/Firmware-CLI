"""Render a stable model-facing MCP tool schema bundle for the turnkey brain."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import cast, get_args

from pyocd_debug_mcp.brain.actions import AllowedServerToolName
from pyocd_debug_mcp.brain.mcp_client import ToolDescriptor

_CURATED_TOOL_ORDER = cast(tuple[str, ...], get_args(AllowedServerToolName))
_EMPTY_OBJECT_SCHEMA = {"type": "object", "additionalProperties": False}
_COMMON_RESPONSE_SEMANTICS = (
    "Expected policy denials are plain text: `Refused [<code>]: <message> session_id=<id>`.",
    "Expected watcher blocks are plain text: `Blocked [<code>]: <message> session_id=<id>`.",
    "Unexpected runtime/backend failures remain real tool errors rather than plain-text success/refusal output.",
)
_TOOL_RESPONSE_SEMANTICS: dict[str, tuple[str, ...]] = {
    "connect": (
        "Success text includes `session_id=...` so later log and guardrail output can be correlated to `runs/<session_id>/...`.",
        "Normal success starts with `Connected to board ... via probe ... via ...`.",
    ),
    "disconnect": (
        "Success text is `Disconnected.` when a session was active; repeated disconnects may return `Not connected.`.",
    ),
    "flash_firmware": ("Normal success starts with `Flashed ... via ...; target left ...`.",),
    "read_serial": (
        "Healthy match text starts with `UART matched ...` and includes the matched excerpt.",
    ),
    "unlock_recover": ("Successful supported recover starts with `Recover completed via ...`.",),
}
_DESCRIPTION_CHAR_LIMIT = 220
_ARG_HINT_CHAR_LIMIT = 96
_MAX_RENDERED_ARGS = 10


@dataclass(frozen=True)
class ToolSchemaEntry:
    name: str
    description: str
    input_schema: dict[str, object]
    response_semantics: tuple[str, ...] = ()

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "response_semantics": list(self.response_semantics),
        }


@dataclass(frozen=True)
class ToolSchemaBundle:
    entries: tuple[ToolSchemaEntry, ...]
    rendered_text: str
    schema_hash: str

    def to_record(self) -> dict[str, object]:
        return {
            "tool_names": [entry.name for entry in self.entries],
            "entry_count": len(self.entries),
            "schema_hash": self.schema_hash,
        }

    def entry_by_name(self, tool_name: str) -> ToolSchemaEntry | None:
        for entry in self.entries:
            if entry.name == tool_name:
                return entry
        return None


@dataclass(frozen=True)
class ToolDetailLoadResult:
    requested_tool_names: tuple[str, ...]
    loaded_tool_names: tuple[str, ...]
    missing_tool_names: tuple[str, ...]
    detail_text: str
    schema_hash: str

    def to_record(self) -> dict[str, object]:
        return {
            "requested_tool_names": list(self.requested_tool_names),
            "loaded_tool_names": list(self.loaded_tool_names),
            "missing_tool_names": list(self.missing_tool_names),
            "schema_hash": self.schema_hash,
        }

    def render_result_text(self) -> str:
        loaded = ", ".join(self.loaded_tool_names) or "(none)"
        missing = ", ".join(self.missing_tool_names) or "(none)"
        return (
            "Loaded governed tool details.\n"
            f"requested={list(self.requested_tool_names)}\n"
            f"loaded={loaded}\n"
            f"missing={missing}\n"
            f"schema_hash={self.schema_hash}"
        )


def build_tool_schema_bundle(tool_descriptors: tuple[ToolDescriptor, ...]) -> ToolSchemaBundle:
    descriptor_by_name = {descriptor.name: descriptor for descriptor in tool_descriptors}
    entries: list[ToolSchemaEntry] = []
    for tool_name in _CURATED_TOOL_ORDER:
        descriptor = descriptor_by_name.get(tool_name)
        if descriptor is None:
            continue
        entries.append(
            ToolSchemaEntry(
                name=tool_name,
                description=_normalize_description(tool_name, descriptor.description),
                input_schema=_normalize_input_schema(descriptor.input_schema),
                response_semantics=_TOOL_RESPONSE_SEMANTICS.get(tool_name, ()),
            )
        )
    rendered_text = _render_bundle(tuple(entries))
    schema_hash = hashlib.sha256(rendered_text.encode("utf-8")).hexdigest()
    return ToolSchemaBundle(
        entries=tuple(entries), rendered_text=rendered_text, schema_hash=schema_hash
    )


def load_tool_details(
    bundle: ToolSchemaBundle, tool_names: tuple[str, ...]
) -> ToolDetailLoadResult:
    requested = _normalize_tool_names(tool_names)
    loaded_entries: list[ToolSchemaEntry] = []
    missing: list[str] = []
    seen: set[str] = set()
    for tool_name in requested:
        if tool_name in seen:
            continue
        seen.add(tool_name)
        entry = bundle.entry_by_name(tool_name)
        if entry is None:
            missing.append(tool_name)
            continue
        loaded_entries.append(entry)
    return ToolDetailLoadResult(
        requested_tool_names=tuple(requested),
        loaded_tool_names=tuple(entry.name for entry in loaded_entries),
        missing_tool_names=tuple(missing),
        detail_text=render_tool_detail_entries(
            tuple(loaded_entries), schema_hash=bundle.schema_hash
        ),
        schema_hash=bundle.schema_hash,
    )


def render_tool_detail_entries(entries: tuple[ToolSchemaEntry, ...], *, schema_hash: str) -> str:
    if not entries:
        return "Loaded governed tool details:\n(no matching governed tools)"
    lines = [f"Loaded governed tool details (full; schema_hash={schema_hash}):"]
    for entry in entries:
        lines.append("")
        lines.append(f"## {entry.name}")
        lines.append(f"description: {entry.description}")
        lines.append("input_schema:")
        lines.append(json.dumps(entry.input_schema, indent=2, sort_keys=True))
        response_semantics = (*_COMMON_RESPONSE_SEMANTICS, *entry.response_semantics)
        lines.append("response_semantics:")
        lines.extend(f"- {line}" for line in response_semantics)
    return "\n".join(lines)


def _normalize_description(tool_name: str, description: str) -> str:
    text = description.strip()
    if text:
        return text
    return f"No server description was provided for `{tool_name}`. Use the input schema and tool name carefully."


def _normalize_tool_names(tool_names: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(tool_name.strip() for tool_name in tool_names)
    if not normalized or any(not tool_name for tool_name in normalized):
        raise ValueError("tool_names must contain at least one non-empty tool name")
    return normalized


def _normalize_input_schema(input_schema: dict[str, object]) -> dict[str, object]:
    if not isinstance(input_schema, dict) or not input_schema:
        return dict(_EMPTY_OBJECT_SCHEMA)
    return input_schema


def _render_bundle(entries: tuple[ToolSchemaEntry, ...]) -> str:
    if not entries:
        return "Curated MCP tool index (compact):\n(no matching MCP tools were available)"
    lines = [
        "Curated MCP tool index (compact; server enforces the actual MCP schemas):",
        "Argument marker: `!` means required, `?` means optional.",
        "Common response semantics:",
    ]
    lines.extend(f"- {line}" for line in _COMMON_RESPONSE_SEMANTICS)
    for entry in entries:
        lines.append(
            f"- {entry.name}: {_trim_single_line(entry.description, _DESCRIPTION_CHAR_LIMIT)}"
        )
        lines.append(f"  args: {_render_argument_index(entry.input_schema)}")
        if entry.response_semantics:
            lines.append("  response_semantics:")
            lines.extend(f"    - {line}" for line in entry.response_semantics)
    return "\n".join(lines)


def _render_argument_index(input_schema: dict[str, object]) -> str:
    properties = _mapping_value(input_schema.get("properties"))
    if not properties:
        return "none"
    required = set(_string_list_value(input_schema.get("required")))
    parts: list[str] = []
    for index, (name, schema_value) in enumerate(properties.items()):
        if index >= _MAX_RENDERED_ARGS:
            parts.append(f"...(+{len(properties) - _MAX_RENDERED_ARGS} more)")
            break
        marker = "!" if name in required else "?"
        hint = _schema_hint(schema_value)
        if hint:
            parts.append(f"{name}{marker}:{hint}")
        else:
            parts.append(f"{name}{marker}")
    return "; ".join(parts)


def _schema_hint(schema_value: object) -> str:
    schema = _mapping_value(schema_value)
    if not schema:
        return ""
    enum_values = _string_list_value(schema.get("enum"))
    if enum_values:
        rendered = "|".join(enum_values[:6])
        if len(enum_values) > 6:
            rendered += "|..."
        return _trim_single_line(f"enum[{rendered}]", _ARG_HINT_CHAR_LIMIT)
    const_value = schema.get("const")
    if isinstance(const_value, str):
        return _trim_single_line(f"const[{const_value}]", _ARG_HINT_CHAR_LIMIT)
    type_value = schema.get("type")
    if isinstance(type_value, str):
        if type_value == "array":
            item_hint = _schema_hint(schema.get("items"))
            return _trim_single_line(f"array[{item_hint or 'items'}]", _ARG_HINT_CHAR_LIMIT)
        if type_value == "object":
            nested = _mapping_value(schema.get("properties"))
            if nested:
                nested_names = ", ".join(list(nested)[:4])
                if len(nested) > 4:
                    nested_names += ", ..."
                return _trim_single_line(f"object[{nested_names}]", _ARG_HINT_CHAR_LIMIT)
        return _trim_single_line(type_value, _ARG_HINT_CHAR_LIMIT)
    if isinstance(type_value, list):
        text_values = [value for value in type_value if isinstance(value, str)]
        if text_values:
            return _trim_single_line("|".join(text_values), _ARG_HINT_CHAR_LIMIT)
    if "anyOf" in schema or "oneOf" in schema:
        return "union"
    return ""


def _mapping_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): nested for key, nested in value.items()}


def _string_list_value(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _trim_single_line(text: str, limit: int) -> str:
    value = " ".join(text.strip().split())
    if len(value) <= limit:
        return value
    if limit <= 3:
        return value[:limit]
    return value[: limit - 3].rstrip() + "..."
