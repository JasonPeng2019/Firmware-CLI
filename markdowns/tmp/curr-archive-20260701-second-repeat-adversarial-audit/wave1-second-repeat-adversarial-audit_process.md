# Process ledger for wave1-second-repeat-adversarial-audit

## Goal and roadmap anchor

Task: Second repeat Wave 1 adversarial audit after OpenAI native-sync metadata fix
Roadmap anchor: R12 Stage 5 Wave 1 hard bar in
`markdowns/firmware_agent_build_plan_concrete (10).md`,
`markdowns/things-to-change.md` Prototype Priority items 1-14, and the active
Wave 1 specs in `markdowns/curr/`.

## Done

- Loaded FirmCLI workflows: `firmcli-write-process`, `firmcli-test-suite`,
  `firmcli-fix-bug`, `firmcli-spec-loop`, `firmcli-markdown-audit`, and
  `firmcli-workflow-core`.
- Loaded authority/current docs: superpowers index and consistency/coding/doc
  sync/spec-loop playbooks, build plan, `README.md`,
  `markdowns/current-progress.md`, `markdowns/ROADMAP.md`,
  `markdowns/things-to-change.md`, and `markdowns/curr/README.md`.

## In progress

- None.

## TODO

- None.

## Audit plan

Important files to inspect:

- Brain decision/action boundary: `src/pyocd_debug_mcp/brain/actions.py`,
  `action_policy.py`, `loop.py`, `app.py`, `cli.py`, `client_actions.py`.
- Provider/session/memory paths: `provider_types.py`, `provider_openai.py`,
  `provider_anthropic.py`, `provider_codex_cli.py`, `provider_claude_cli.py`,
  `provider_factory.py`, `provider_parsing.py`, `provider_native_skills.py`.
- Skill/tool context paths: `skills.py`, `model_native_skills.py`,
  `tool_schemas.py`, `state.py`, `skills/model_native/`,
  `skills/provider_native/`.
- Operator/product UX paths: `src/pyocd_debug_mcp/ux/cli.py`,
  `ux/shell.py`, `ux/commands.py`, `ux/history.py`, `ux/renderer.py`.
- Harness/tests: `tests/test_r12_turnkey.py`,
  `tests/test_r12_turnkey_merge.py`, `tests/test_provider_native_skills.py`,
  `tests/test_provider_native_skill_usage_harness.py`, `tests/test_ux_cli.py`,
  `tests/harness/provider_native_skill_usage.py`, and
  `tests/harness/branch_c_tests.py`.
- Public docs/config: `README.md`, `.env.example`,
  `markdowns/current-progress.md`, `markdowns/things-to-change.md`,
  `markdowns/R12_P_SPLIT.md`, `markdowns/curr/README.md`.

Features to inspect:

- Free host-side work with exactly one final governed board/client/context or
  terminal decision.
- Structural absence of stale governed `read_file`, `replace_file`, and
  `run_build` actions from schemas, parser, policy, executor, batches, prompts,
  and docs.
- `load_skills` and `load_tool_details` as context-expansion turns, including
  detail-required guardrails before governed execution.
- Compact skill/tool indexes in ordinary `remote-delta` turns without full
  schema or full memory reinjection.
- Four-tier memory: Tier 0 state, Tier 1 recent details, deterministic Tier 2
  mid-history from Tier 1, Tier 3 hard-limited summary with model compression
  only at Tier 2 overflow.
- OpenAI/Codex/Claude remote-primary continuation metadata and fail-closed
  resume behavior; Anthropic local-primary behavior.
- Provider-native skill projection: run-local `.codex/skills` and
  `.claude/skills`, Claude `Skill(...)` allowlisting, no global writes,
  marker-based overwrite refusal, and API fallback.
- Public UX run/benchmark/shell/rerun controls for memory and provider-native
  skills, including noninteractive stdin command handling.
- Provider/API simulation, live no-hardware Codex/Claude native-skill proof,
  and process cleanup evidence.

Markdowns to reference:

- Product/spec guidance: `markdowns/firmware_agent_build_plan_concrete (10).md`,
  `markdowns/things-to-change.md`, `markdowns/R12_P_SPLIT.md`,
  `markdowns/ROADMAP.md`, `markdowns/current-progress.md`.
- Active Wave 1 specs: `r12_turnkey_spec.md`,
  `r12-context-scaffold-hardening_spec.md`,
  `r12-delta-compact-indexes_spec.md`,
  `r12-prompt-memory-cost-hardening_spec.md`,
  `r12-tier2-memory-bridge_spec.md`,
  `r12-provider-native-skill-bridge_spec.md`,
  `r12-provider-native-skill-invocation-proof_spec.md`,
  `r12-provider-native-ux-cli-controls_spec.md`, and
  `r12-openai-native-sync-metadata_spec.md`.
- Future/non-Wave-1 boundary: `wave2-codebase-map_spec.md`.
- Codebase guidance: `README.md`, `markdowns/repo_file_index.md`, and the
  superpowers playbooks.

Audit method:

- Search for stale action names, TODO/slop markers, missing CLI flags, broken
  references, provider metadata divergence, and accidental global provider
  writes.
- Read hot code paths directly, not just status docs.
- Run focused parser/help/API/memory/provider-native checks, then the full
  suite ladder.
- Review live provider reports at the decision/output level.
- Repeat the adversarial sweep after validation is green.

## Audit execution

Searches and direct inspections completed:

- Stale governed action sweep for `read_file`, `replace_file`,
  `run_build`, `FileReadAction`, `ReplaceFileAction`, and `RunBuildAction`
  across `src`, `tests`, `skills`, `playbooks`, `README.md`, active specs,
  `things-to-change.md`, and `R12_P_SPLIT.md`.
- Provider continuation sweep for `continuation_path`,
  `local-memory-fallback`, `remote-resume`, `remote-fork`,
  `native_sync_used`, `previous_response_id`, `resume_failure`, and
  fail-closed metadata across brain providers, tests, and docs.
- Memory sweep for `recent_turn_detail`, `mid_history`, `memory_summary`,
  Tier 2/Tier 3 labels, native sync cadence, and rendered-vs-available
  accounting.
- Slop-marker sweep for TODO/FIXME/HACK/stub/placeholder/not-implemented,
  global `.codex` / `.claude` writes, and `.agents` context leakage.
- Direct code reads of `actions.py`, `action_policy.py`,
  `provider_types.py`, `provider_native_skills.py`,
  `provider_openai.py`, `provider_codex_cli.py`, `provider_claude_cli.py`,
  `ux/cli.py`, and `ux/shell.py`.

Audit criticisms reviewed:

- Stale action search hits had no merit. They were historical docs, tests that
  assert removal, workspace helper APIs, or real Zephyr/benchmark helper build
  functions, not governed provider action variants.
- TODO/placeholder search hits had no merit. They were fixture placeholder
  strings or harness explanatory text, not product code gaps.
- `.agents` and global-provider-directory hits had no merit. They were docs or
  tests proving runtime context exclusion and run-local provider-native
  projection, not global writes.
- A provider metadata sweep initially failed because of PowerShell quote
  parsing. A safer follow-up sweep and direct inspection confirmed OpenAI
  native memory sync uses `previous_response_id`, records `native_sync_used`,
  and keeps `remote-resume` metadata.

No valid new Wave 1 spec, product, architecture, portability, or code-quality
gap was found in this repeat loop. Therefore no new spec or fix-bug loop was
needed after the previous OpenAI native-sync metadata fix.

## Validation

Software-side validation completed:

- `uv run pyocd-debug --help` passed.
- `uv run pyocd-debug run --help` passed and exposed memory/provider-native
  controls.
- `uv run pyocd-debug benchmark --help` passed and exposed
  memory/provider-native controls.
- Focused Wave 1 tests passed:
  `34 passed, 103 deselected`.
- Provider-native projection and usage harness tests passed:
  `11 passed`.
- Noninteractive operator shell smoke passed for `/help`, memory controls,
  provider-native cadence controls, `/history`, and `/quit`.
- Full suite ladder passed:
  - `uv run pytest -q`: `387 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`:
    passed
  - `uv run pytest -q tests/test_r11_benchmark.py`: `34 passed`
  - `uv run python -m tests.harness.r11_benchmark --help`: passed
- Live no-hardware provider-native proof passed:
  `uv run python -m tests.harness.provider_native_skill_usage --provider codex-cli --provider claude-cli --timeout-seconds 180 --report-root runs\provider-native-skill-usage-second-repeat-audit`
  - Codex CLI returned a valid `finalize` decision, observed hidden token
    `FIRMCLI_NATIVE_SKILL_USAGE_CODEX_CLI_411f10ef`, did not fall back to
    `load_skills`, and recorded `remote-resume`.
  - Claude CLI returned a valid `finalize` decision, observed hidden token
    `FIRMCLI_NATIVE_SKILL_USAGE_CLAUDE_CLI_e427a351`, did not fall back to
    `load_skills`, recorded `remote-resume`, and passed
    `Skill(firmcli-native-usage-proof)` in the native tool allowlist.
- Process snapshots before/after the live provider proof showed only
  pre-existing Codex app/app-server and `pyocd-debug-mcp` processes; no new
  harness provider process was left behind.

Repeat audit after the green suite found only the same no-merit categories
listed above.

## Markdown audit

- Ran `inventory_markdowns.py --root markdowns`; inventory completed.
- Ran `find_markdown_overlap.py --root markdowns`; overlap candidates were
  expected roadmap/spec-template overlap and did not require consolidation in
  this pass.
- Ran `check_markdown_references.py --root markdowns --all`; the helper exited
  nonzero due historical archive/runtime-artifact references. Narrow review
  found no false references from `markdowns/curr/`, `markdowns/current-progress.md`,
  `markdowns/things-to-change.md`, or `README.md`.
- Removed temporary markdown-audit report files.
- Moved this completed process ledger out of `markdowns/curr/` into
  `markdowns/tmp/curr-archive-20260701-second-repeat-adversarial-audit/`.
- Reran the suite ladder after doc cleanup; it remained green with
  `387 passed`, ruff, mypy, R11 benchmark tests, and R11 benchmark help.

## Limitations and known gaps

- Hardware tests are intentionally excluded by the user for this repeat run.
- Live API-provider calls require credentials/credits; this pass uses
  fake-provider/API simulations through the real provider adapters and loop.
- Exact official `nrf52833dk`, live API credentials, fresh-machine proof, and
  Wave 2 prototype modules remain documented external boundaries.

## Hardware hand-off

- None for this run. No hardware validation requested or required.

## Open decisions and surfaced issues

- No valid new issues surfaced in this repeat loop.

## Verified

- Pre-audit plan written in this ledger.
- Full repeat adversarial audit completed.
- Audit review completed; all criticisms were no-merit against the current code
  and product behavior.
- Full non-hardware suite ladder green.
- Live no-hardware Codex/Claude provider-native proof green.
- Markdown audit completed and `markdowns/curr/` cleaned.
- No hardware tests were run, by instruction.

## Pending verification

- None.
