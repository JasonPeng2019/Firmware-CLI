# Process ledger for wave1-repeat-adversarial-audit

## Goal and roadmap anchor

Task: Repeat Wave 1 full-product adversarial spec-to-code audit, fix valid gaps, validate non-hardware suite, markdown cleanup, and push P-wave-0
Roadmap anchor: R12 Stage 5 Wave 1 hard bar in
`markdowns/firmware_agent_build_plan_concrete (10).md`,
`markdowns/things-to-change.md` Prototype Priority items 1-14 and the
implemented Wave 1 provider-native addendum. Wave 2 items remain prototype
scope but are not Wave 1 completion criteria unless an active Wave 1 spec
claims them.

## Done

- Loaded workflow skills: `firmcli-write-process`, `firmcli-spec-loop`,
  `firmcli-fix-bug`, `firmcli-test-suite`, `firmcli-markdown-audit`,
  `firmcli-workflow-core`, and `python-change`.
- Loaded authority docs and current status docs:
  `superpowers/agent_index_START_HERE.md`,
  `superpowers/agent_consistency_playbook.md`,
  `markdowns/firmware_agent_build_plan_concrete (10).md`,
  `superpowers/agent_coding_playbook.md`,
  `superpowers/agent_doc_sync_playbook.md`,
  `superpowers/spec_build_review_loop_playbook.md`, `README.md`,
  `markdowns/ROADMAP.md`, `markdowns/current-progress.md`,
  `markdowns/things-to-change.md`, and `markdowns/curr/README.md`.

## In progress

- Step 4 repeat audit and markdown cleanup.

## TODO

- Execute the audit plan below.
- For each valid Wave 1 gap, create or update a narrow `*_spec.md`, fix through
  the write-process/fix-bug discipline, and rerun affected validation.
- Run full non-hardware FirmCLI suite.
- Run realistic live Codex/Claude no-hardware multi-prompt/provider-native proof
  checks when local CLI auth/tools are available, plus API-path simulation.
- Repeat the adversarial audit after the suite is green.
- Run markdown audit, clean `markdowns/curr/`, and delete temporary mapping docs.
- Push the final repo state to `P-wave-0`.

## Audit plan

Important files to inspect:

- Brain action boundary and loop: `src/pyocd_debug_mcp/brain/actions.py`,
  `src/pyocd_debug_mcp/brain/action_policy.py`, `src/pyocd_debug_mcp/brain/loop.py`,
  `src/pyocd_debug_mcp/brain/app.py`, `src/pyocd_debug_mcp/brain/cli.py`.
- Provider/session/memory surfaces: `src/pyocd_debug_mcp/brain/provider_types.py`,
  `provider_codex_cli.py`, `provider_claude_cli.py`, `provider_openai.py`,
  `provider_anthropic.py`, `provider_factory.py`, `provider_parsing.py`.
- Skill/tool context surfaces: `src/pyocd_debug_mcp/brain/skills.py`,
  `model_native_skills.py`, `provider_native_skills.py`, `tool_schemas.py`,
  `state.py`, `skills/model_native/`, `skills/provider_native/`.
- UX/operator surfaces: `src/pyocd_debug_mcp/ux/cli.py`,
  `src/pyocd_debug_mcp/ux/shell.py`, `ux/commands.py`, `ux/history.py`,
  `ux/renderer.py`.
- Validation and harnesses: `tests/test_r12_turnkey.py`,
  `tests/test_r12_turnkey_merge.py`, `tests/test_model_native_skills.py`,
  `tests/test_provider_native_skills.py`, `tests/test_ux_cli.py`,
  `tests/harness/provider_native_skill_usage.py`,
  `tests/harness/branch_c_tests.py`, `tests/harness/r12_turnkey_benchmark.py`.
- Public docs and config: `README.md`, `.env.example`, `pyproject.toml`,
  `markdowns/current-progress.md`, `markdowns/things-to-change.md`,
  `markdowns/R12_P_SPLIT.md`, `markdowns/curr/README.md`.

Features to inspect adversarially:

- Free host work vs final governed board/client/terminal/context decision.
- Removal of stale governed host actions from schema, parser, executor, tests,
  docs, and prompts.
- `load_skills` and `load_tool_details` as context-expansion decisions, with
  strict loaded-detail guardrails before governed tool/script/compound-action
  execution.
- Compact tool and skill indexes in `remote-delta` turns without full schema or
  full memory reinjection.
- Four-tier provider memory: Tier 0 canonical state, Tier 1 detailed recent
  turns, deterministic Tier 2 mid-history, Tier 3 hard-limited summary with
  model summary only at Tier 2 overflow.
- Provider resume/continuity and fail-closed behavior for OpenAI/Codex/Claude
  remote-primary providers, and Anthropic local-primary fallback.
- Provider-native skill projection into run-local `.codex/skills` and
  `.claude/skills`, Claude `Skill(...)` allowlisting, no global writes,
  deterministic API fallback, and public CLI/rerun controls.
- Operator `pyocd-debug` shell/run/benchmark/history/show/rerun behavior,
  non-interactive stdin/BOM behavior, memory/provider controls, raw output, and
  multi-prompt isolation.
- API-provider simulation coverage without credentials.
- Process/provider/MCP/hardware cleanup evidence and absence of orphaned
  long-running processes in non-hardware validation.

Markdowns to reference:

- Spec/product guidance: `markdowns/firmware_agent_build_plan_concrete (10).md`,
  `markdowns/things-to-change.md`, `markdowns/R12_P_SPLIT.md`,
  `markdowns/ROADMAP.md`, `markdowns/current-progress.md`.
- Active Wave 1 specs: `markdowns/curr/r12_turnkey_spec.md`,
  `r12-context-scaffold-hardening_spec.md`,
  `r12-delta-compact-indexes_spec.md`,
  `r12-prompt-memory-cost-hardening_spec.md`,
  `r12-tier2-memory-bridge_spec.md`,
  `r12-provider-native-skill-bridge_spec.md`,
  `r12-provider-native-skill-invocation-proof_spec.md`,
  `r12-provider-native-ux-cli-controls_spec.md`.
- Future/non-Wave-1 boundary: `markdowns/curr/wave2-codebase-map_spec.md`.
- Codebase guidance: `README.md`, `markdowns/repo_file_index.md`,
  `superpowers/agent_coding_playbook.md`,
  `superpowers/agent_doc_sync_playbook.md`,
  `superpowers/spec_build_review_loop_playbook.md`.

Audit method:

- Map every active Wave 1 spec requirement to concrete code/tests.
- Search for stale action names, stale docs, missing CLI surfaces, and divergent
  headless-vs-UX behavior.
- Read implementation hot spots rather than trusting status docs.
- Run static and behavior tests, including focused CLI parser/help smokes and
  fake-provider/API-path tests.
- Generate criticisms first, then manually classify each as valid or no-merit
  with code evidence.
- If validation is green, repeat the audit pass to catch issues introduced by
  fixes or docs cleanup.

## Limitations and known gaps

- Hardware tests are intentionally excluded by user instruction for this run.
- Live API-provider proof cannot run without API credentials/credits; this run
  will use the strongest local fake-provider/API simulation available.
- Live Codex/Claude no-hardware checks depend on local CLI installation/auth and
  will be bounded to avoid excessive compute.

## Hardware hand-off

- None for this run unless the audit uncovers a hardware-only ambiguity. Exact
  official `nrf52833dk` proof remains an external boundary already documented.

## Open decisions and surfaced issues

- A1 valid gap: OpenAI native memory sync was mislabeled as
  `local-memory-fallback` despite carrying `previous_response_id`. Fixed.
- Repeat-audit no-merit criticism: short slash aliases such as `/native-sync`,
  `/recent-turns`, and `/mid-history-turns` are not implemented. The product
  spec and `/help` expose the full commands `/native-sync-every`,
  `/recent-turn-detail-limit`, and `/mid-history-turn-limit`; rerunning the
  smoke with the supported commands passed.

## Verified

- Pre-audit plan written in this ledger.
- Valid finding A1: OpenAI periodic native memory sync passed
  `previous_response_id` but labeled the provider metadata as
  `local-memory-fallback`. This was a real auditability/product gap because
  docs/specs require OpenAI remote-primary continuation with periodic safety
  sync. Narrow spec:
  `markdowns/curr/r12-openai-native-sync-metadata_spec.md`.
- A1 fix implemented in `src/pyocd_debug_mcp/brain/provider_openai.py`, with
  regression coverage in `tests/test_r12_turnkey_merge.py`.
- Focused A1 test:
  `uv run pytest -q tests/test_r12_turnkey_merge.py -k "openai_provider_records_native_sync_as_remote_resume or openai_provider_uses_previous_response_id"`
  -> `2 passed`.
- Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`
  -> ruff check/format passed, pyright 0 diagnostics, full pytest
  `387 passed`.
- FirmCLI suite preset:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> full pytest `387 passed`, ruff passed, mypy passed, benchmark harness
  tests `34 passed`, R11 help smoke passed.
- Live no-hardware provider-native proof:
  `uv run python -m tests.harness.provider_native_skill_usage --provider codex-cli --provider claude-cli --timeout-seconds 180 --report-root runs\provider-native-skill-usage-repeat-audit`
  -> Codex CLI and Claude CLI reports passed. Both projected run-local native
  skills, used no fallback, observed the proof token, and returned a final
  `finalize` decision.
- API simulation:
  `uv run pytest -q tests/test_r12_turnkey_merge.py -k "openai_provider or anthropic_provider or native_sync"`
  -> `6 passed`;
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_native or memory or resume or provider"`
  -> `23 passed`.
- Operator multi-command no-hardware shell smoke:
  piped `/help`, memory controls, `/history`, and `/quit` through
  `uv run pyocd-debug`. Supported commands printed the expected acknowledgements
  and no hardware/provider turn was launched.
- UX focused tests:
  `uv run pytest -q tests/test_ux_cli.py -k "shell or operator_cli or memory or provider_native"`
  -> `22 passed`.
- Repeat adversarial audit:
  stale host actions remain absent from governed action schema and executor;
  remaining `read_file`/`replace_file`/`run_build` hits are historical docs,
  tests asserting removal, workspace helper APIs, or real Zephyr/benchmark build
  helpers. OpenAI/Codex/Claude continuation paths are consistent with
  remote-primary behavior, Anthropic remains local-primary, Tier 1 -> Tier 2 ->
  Tier 3 memory code matches the four-tier spec, and placeholder/TODO search
  found only fixture text.

## Pending verification

- Markdown audit and push.
