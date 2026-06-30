> STATUS: IMPLEMENTED AND VALIDATED - compact indexes now render in ordinary
> `remote-delta` turns while memory and full schemas keep their existing
> cadence.

# r12 delta compact indexes

## Goal in plain English

Task: Include compact skill and governed-tool indexes in `remote-delta` provider
turns so every internal provider decision sees the stable action/context surface,
while memory and full schemas keep their existing cadence.

Roadmap anchor: R12 Stage 5 Wave 1.

## Scope and non-scope

In scope:

- Change `ProviderPromptBundle.render_remote_delta_text()` so steady-state
  native-resume turns include:
  - compact turnkey/model-native skill context
  - compact governed MCP tool index
  - current turn context
- Keep provider memory injection governed by `native_sync_every`.
- Keep full decision schema and full MCP input schemas out of ordinary
  `remote-delta` turns.
- Update provider metadata/tests so "static tool schema injected" accurately
  means the compact governed-tool index was included, even when the full
  decision schema was not.
- Add focused tests for `remote-delta` prompt composition and provider metadata.

Out of scope:

- Sending full MCP `input_schema:` bodies every turn.
- Sending full model-native skill bodies every turn.
- Changing the provider memory cadence or `--native-sync-every` semantics.
- Changing retry prompts beyond existing schema-correction behavior.
- Implementing Wave 2 codebase-map injection.

## Reconciliation summary

- Build plan: Stage 5 says provider-native sessions are preferred, compact
  local memory is periodically injected every 10 provider turns by default, full
  tool schemas and other large static prompt blocks should not be reprinted
  every turn, and compact governed-tool plus selected-skill indexes should be
  available every provider turn.
- Current code: `ProviderPromptBundle.render_remote_delta_text()` currently
  renders only `turn_context_text`. That keeps tokens low, but it depends on the
  provider's native thread remembering the compact skill/tool action surface.
- Active R12 scaffold docs: the scaffold hardening work established compact
  skill context and compact governed-tool index as the stable prompt prelude,
  with full details loaded on demand.
- Disagreements: no settled-decision conflict. This change aligns the code with
  the build plan's compact-index-every-turn direction while preserving the
  explicit memory and full-schema throttles.

## Design

- Keep `ProviderPromptBundle` as the single prompt-section carrier.
- Change `render_remote_delta_text()` from:
  `turn_context_text`
  to:
  `skill_context_text`, `tool_schema_text`, `turn_context_text`
- Do not include `provider_memory_text` in `remote-delta`.
- Do not include `turn_decision_schema_text` in `remote-delta`.
- Keep `render_remote_sync_text()` and `render_bootstrap_text()` as full renders
  that include compact indexes, turn context, optional provider memory, and the
  decision schema.
- Keep retry prompts as `turn_context_text`, `turn_decision_schema_text`, and
  correction note. Retry is a schema-repair path, not the normal steady-state
  delta.
- Treat provider metadata field `static_tool_schema_injected` as true for
  `remote-delta` because the compact governed-tool index is now present.
  `decision_schema_injected` remains false for `remote-delta`.
- No adapter-specific branching should be needed: Codex CLI, Claude CLI,
  OpenAI, and future remote-primary providers should all call the same bundle
  render method.
- `anthropic-api` remains local-primary and already receives the full bootstrap
  prompt on each call because that backend has no native remote session.

## Board-facts-as-data and origin tags

- No board facts, YAML board metadata, pyOCD targets, serial ports, or hardware
  constants are changed.
- Prompt-cadence behavior is PROJECT-DEFINED by the R12 Stage 5 design.

## Documentation plan

- This spec is the authoritative task design artifact for the change.
- Create/update a process ledger for the write-process run.
- If code behavior changes, record the verification and any provider/hardware
  boundaries in the process ledger and final review artifact.

## Portability

- No new dependencies or machine-specific paths.
- The change is pure prompt assembly and metadata; it should behave the same on
  Windows/macOS/Linux.
- Token cost increases slightly on each remote-primary provider turn because
  compact indexes are sent every time. This is intentional and bounded because
  full schemas and memory remain gated.

## Verification plan

- Focused unit tests:
  - `ProviderPromptBundle.render_remote_delta_text()` includes compact skill
    context, compact tool index, and turn context.
  - `remote-delta` provider calls for OpenAI/Codex/Claude use the new delta
    body and record compact tool index injection.
  - `remote-delta` still does not inject memory or full decision schema.
- Python-change gate:
  `uv run python .codex/skills/python-change/scripts/run_python_change_checks.py`
- FirmCLI suite ladder:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/r12-delta-compact-indexes-suite-report.txt`
- Provider/hardware smoke if credentials/session state are available:
  use the existing Branch C harness with Codex CLI and attached boards, bounded
  with explicit timeouts.

## Acceptance criteria

- Normal `remote-delta` prompts include compact skill context, compact governed
  tool index, and current turn context.
- Normal `remote-delta` prompts exclude provider memory and full decision
  schema.
- `native_sync_every` still controls memory injection cadence.
- Full/bootstrap/sync prompt ordering remains:
  compact skill context, compact governed-tool index, turn context, optional
  provider memory, decision schema.
- Retry prompt behavior remains focused on turn context, full decision schema,
  and the correction note.
- Focused tests, Python-change gate, and FirmCLI suite ladder pass.
- Any live provider/hardware proof is reported separately from non-hardware
  verification.

## Verified

- Reconciliation completed against:
  - `markdowns/firmware_agent_build_plan_concrete (10).md`
  - `markdowns/curr/r12_turnkey_spec.md`
  - `markdowns/curr/r12-context-scaffold-hardening_spec.md`
  - current provider prompt/render code and tests
- Focused prompt/provider tests passed.
- Python-change gate passed with Ruff, format, Pyright, and `359 passed`.
- FirmCLI suite ladder passed and wrote
  `runs/r12-delta-compact-indexes-suite-report.txt`.
- Codex CLI provider + live hardware smoke passed on both attached boards:
  `runs/20260630T200822Z-b69e332f` for `nucleo_l476rg` and
  `runs/20260630T201005Z-f2c1d62b` for `nrf52840dk`.

## Pending verification

- Claude CLI live proof remains blocked unless the local Claude CLI is logged
  in.
- API-provider parity remains dependent on available API credentials.
