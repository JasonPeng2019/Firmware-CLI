> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# compact tool schema index

## Goal in plain English

Task: Compact turnkey MCP tool prompt injections to a small schema index
Roadmap anchor: R12 / Stage 5 Wave 1 Branch A and Branch B prompt boundary.

The turnkey brain should still tell the model which governed MCP tools exist and
which arguments matter, but it must stop injecting full repeated MCP input
schema bodies into provider prompts. The provider prompt should carry a compact
tool index: tool name, short description, required and optional argument names,
and the stable response/refusal semantics the brain owns. The actual MCP server
schemas remain available through the server/client path and remain the source
of truth for validation; they are not reprinted as full JSON in the brain prompt.

## Scope and non-scope

In scope:

- Replace the rendered model-facing MCP tool schema bundle with a compact index.
- Keep the curated allowlist and existing server/board action boundary.
- Keep tool descriptions sourced from live MCP metadata, trimmed for prompt use.
- Preserve enough argument signal for the model: property names, required vs.
  optional, basic type/enum hints, and nested-object/array markers.
- Keep the schema hash and artifacts useful for provenance.
- Add focused tests that fail if full JSON schema bodies return to the prompt.
- Sync the build plan, R12 split/spec docs, current progress, and handoff docs.

Out of scope:

- Changing the MCP server tool definitions, docstrings, or protocol schemas.
- Changing `TurnDecision` schema injection.
- Adding provider-native direct MCP tool calls.
- Broad Wave 2 skill-body cache/on-demand loading beyond this compact tool
  index.
- Claiming Claude or real-board proof while Claude quota or board access blocks
  it.

## Reconciliation summary

- Build plan: Stage 5 now requires cheap static context and says large static
  prompt blocks should not be reprinted every turn. It also says model-native
  host work stays outside governed brain actions and that only board/server
  decisions should cross the governed boundary.
- Current code: `tool_schemas.py` filters the live MCP tools to the curated
  allowlist but renders every `input_schema` as pretty JSON in the provider
  prompt. The prompt bundle injects that text on bootstrap/sync prompts.
- Other docs or notes: `things-to-change.md` and `r12_turnkey_spec.md` still
  describe forwarding descriptions and JSON schemas; those statements need to
  be narrowed to a compact index.
- Disagreements: no settled design conflict. This is a prompt-footprint
  correction to the already-settled tool metadata forwarding feature.

## Design

`ToolSchemaEntry` continues to store the normalized full input schema in memory
and artifacts, because that is useful provenance and supports future changes.
The rendered prompt text changes from "full schema body" to "compact index":

- header naming it a compact governed MCP tool index;
- common response/refusal semantics;
- one bullet per curated tool in `AllowedServerToolName` order;
- short description, collapsed to one line and bounded;
- `args:` with each property rendered as `name!` when required and `name?` when
  optional, followed by concise type/enum hints;
- response semantics lines for tools that have stable known text.

The renderer must not emit raw full-schema field names such as `input_schema:`,
`properties`, `additionalProperties`, or multi-line JSON object bodies. The
actual schema remains in the live MCP descriptor and the `ToolSchemaEntry`
record; only the prompt injection is compact.

## Board-facts-as-data and origin tags

No board facts change. The compact prompt is PROJECT-DEFINED Stage 5 behavior.
The MCP tool schemas themselves remain VENDOR/PROJECT-defined through the MCP
server metadata path and are not hardcoded in the prompt renderer.

## Documentation plan

Update:

- `markdowns/firmware_agent_build_plan_concrete (10).md`
- `markdowns/curr/r12_turnkey_spec.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/things-to-change.md`
- `markdowns/current-progress.md`
- `markdowns/curr/next-codex-handoff-20260630.md`
- `markdowns/repo_file_index.md`

## Portability

No OS-specific behavior changes. Prompt rendering uses pure Python data
structures and path-free text formatting.

## Verification plan

- Focused pytest for compact tool index rendering.
- Focused pytest for prompt bundle records and Branch B no-host-action checks.
- Full Python-change gate: Ruff, format, Pyright, full pytest.
- Codex CLI smoke using the real turnkey public entrypoint if provider quota
  and local environment allow it.
- Claude/live-board proof remains an explicit handoff if quota or hardware
  blocks it.

## Acceptance criteria

- Provider prompt tool injection is a compact index, not repeated full JSON
  schema bodies.
- Curated tool order and filtering still work.
- The compact index includes every curated live tool, description summary,
  required/optional arguments, basic type/enum hints, and response/refusal
  semantics.
- Actual MCP schemas are not removed from the client descriptors or internal
  `ToolSchemaEntry` records.
- Prompt bundle metadata still records tool-schema length and hash.
- Docs no longer claim full JSON schema bodies are injected into provider
  prompts.

## Verified

- Not yet.

## Pending verification

- Focused pytest, full Python-change gate, Codex smoke, Claude quota reset
  handoff, and live attached-board proof.
