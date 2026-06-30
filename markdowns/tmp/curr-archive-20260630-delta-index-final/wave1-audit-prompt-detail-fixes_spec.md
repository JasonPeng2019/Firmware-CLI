> STATUS: IMPLEMENTATION SPEC - reconciled against the active R12 Wave 1
> scaffold-hardening spec during the adversarial audit loop.

# wave1 audit prompt detail fixes

## Goal in plain English

Task: Fix Wave 1 adversarial audit prompt ordering and invalid MCP argument retry gaps
Roadmap anchor: R12 Stage 5 Wave 1

## Scope and non-scope

In scope:

- Make provider prompt assembly match the immediate scaffold-hardening order:
  compact turnkey skill context, compact governed-tool index, loaded context /
  turn context, provider memory, then the final decision schema.
- Remove duplicated compact turnkey skill context from the dynamic turn context.
- Preserve focused governed-tool details when an invalid MCP tool call fails
  through schema/argument validation at the MCP client boundary.
- Make the provider-facing action-batch contract explicit enough that providers
  do not put `finalize` inside `action_batch`.
- Add focused regression tests for prompt ordering and retry context behavior.

Out of scope:

- Building the full product model-native skill library.
- Implementing Wave 2 modules D/E/F/G/H.
- Changing the provider-native free host work contract.
- Treating non-argument MCP failures as retryable argument mistakes.
- Changing the runtime behavior that refuses unsupported batched actions.

## Reconciliation summary

- Build plan: R12 Wave 1 removes brain-owned host file/build actions while
  preserving provider-native host work and a governed final decision.
- Current code: the action boundary already removed the old governed host
  actions, but prompt assembly still rendered provider memory before loaded
  detail context and embedded compact skill context inside turn context.
- Other docs or notes:
  `markdowns/curr/r12-context-scaffold-hardening_spec.md` requires compact
  skill/tool context to be stable and front-loaded, with loaded details before
  memory and final schema.
- Disagreements: none for Wave 1. Missing full model-native skill content and
  Wave 2 hard-bar modules remain explicit scope boundaries, not fixes here.

## Design

- Add a separate `skill_context_text` field to `ProviderPromptBundle` so compact
  turnkey skills are not hidden inside turn context.
- Render bootstrap prompts in this order:
  `skill_context_text`, `tool_schema_text`, `turn_context_text`,
  `provider_memory_text`, `turn_decision_schema_text`.
- Keep adapter-specific message splitting intact by changing only the bundle
  render contract and tests that assert exact retry prompt text.
- Classify `MCPClientError` text as invalid arguments only when it has
  argument/schema/missing-field wording. Auto-load focused tool detail for
  those cases and preserve non-argument MCP failures as real tooling failures.
- Enumerate valid provider-facing `action_batch.calls[].action_type` values in
  the decision schema and explicitly exclude `finalize`.
- Keep the runtime refusal for unsupported batched actions as a defense in
  depth.

## Board-facts-as-data and origin tags

- No board facts or YAML board metadata are changed by this fix.
- All runtime board interactions remain through existing governed MCP tools and
  client actions.

## Documentation plan

- Record the adversarial audit plan, findings, classifications, and verification
  status in `markdowns/curr/wave1-adversarial-audit_process.md`.
- Keep this narrow spec/review pair as the auditable process record for the two
  implementation fixes made during the audit.

## Portability

- No new dependencies, generated paths, or machine-specific state.
- Runtime behavior still tolerates a missing product skill root through the
  existing structured missing-root/missing-skill path.

## Verification plan

- Focused pytest coverage for R12 turnkey prompt/detail behavior.
- Python-change gate: Ruff autofix/format, Pyright JSON, and pytest.
- FirmCLI suite ladder after the Python gate passes.
- Best-effort live provider/MCP/hardware smokes after non-hardware checks pass.

## Acceptance criteria

- Provider bootstrap text has a stable compact skill-context section before the
  compact tool index.
- Provider memory renders after loaded detail/turn context and before the final
  decision schema.
- Turn context no longer duplicates compact turnkey skill text.
- Invalid governed MCP arguments that surface as `MCPClientError` auto-load
  focused tool details for the next provider turn.
- Non-argument MCP errors still propagate as tooling failures.
- Provider-facing schema excludes `finalize` from batch action types.
- Focused and full non-hardware suites pass.

## Verified

- Focused regression command passed:
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle or invalid_mcp_arguments or blocks_server_tool or load_tool_details" tests/test_r12_turnkey_merge.py -k "prompt or memory or schema"`
  -> `15 passed, 79 deselected`.
- Final focused regression command passed:
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle or invalid_mcp_arguments or load_tool_details or action_batch or turn_decision_schema_excludes_finalize" tests/test_r12_turnkey_merge.py -k "prompt or memory or schema"`
  -> `16 passed, 79 deselected`.
- Python-change gate passed with Ruff, format, Pyright, and `359 passed`.
- Suite ladder passed and wrote
  `runs/wave1-adversarial-audit-suite-report.txt`.
- Codex CLI provider + live hardware smokes passed on both attached boards on
  the final code: `runs/20260630T191305Z-97e20d79` for `nucleo_l476rg` and
  `runs/20260630T191450Z-8fedbe20` for `nrf52840dk`.

## Pending verification

- Claude CLI provider proof is blocked by local auth: `Not logged in - Please
  run /login`.
- API-provider and fresh-machine proof remain external boundaries.
