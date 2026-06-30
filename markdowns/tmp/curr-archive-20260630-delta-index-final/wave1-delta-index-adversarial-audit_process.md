# Process ledger for wave1-delta-index-adversarial-audit

## Goal and roadmap anchor

Task: Adversarial audit of the r12 delta compact-index change and the Wave 1 R12 product surface
Roadmap anchor: R12 Stage 5 Wave 1, plus the active hard prototype bar in
`markdowns/things-to-change.md`.

## Done

- Loaded the FirmCLI workflow skills for write-process, spec-loop, test-suite,
  fix-bug, and workflow-core.
- Loaded the authority docs and active task docs:
  - `superpowers/agent_index_START_HERE.md`
  - `superpowers/agent_consistency_playbook.md`
  - `superpowers/agent_coding_playbook.md`
  - `superpowers/agent_doc_sync_playbook.md`
  - `superpowers/spec_build_review_loop_playbook.md`
  - `README.md`
  - `markdowns/ROADMAP.md`
  - `markdowns/current-progress.md`
  - `markdowns/things-to-change.md`
  - `markdowns/R12_P_SPLIT.md`
  - `markdowns/firmware_agent_build_plan_concrete (10).md`
  - `markdowns/curr/r12_turnkey_spec.md`
  - `markdowns/curr/r12-context-scaffold-hardening_spec.md`
  - `markdowns/curr/r12-delta-compact-indexes_spec.md`
  - `markdowns/curr/next-codex-handoff-20260630.md`
- Confirmed the current diff is scoped to:
  - `src/pyocd_debug_mcp/brain/provider_types.py`
  - `src/pyocd_debug_mcp/brain/provider_openai.py`
  - `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
  - `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
  - `tests/test_r12_turnkey.py`
  - `tests/test_r12_turnkey_merge.py`
  - new delta-index spec/process/review docs.
- Wrote this adversarial-audit ledger.
- Fixed valid doc-sync finding C6 by adding the new delta-index artifacts and
  this audit ledger to `markdowns/curr/README.md`.
- Fixed valid doc-sync finding C7 by changing
  `markdowns/curr/r12-delta-compact-indexes_spec.md` from proposal status to
  implemented/validated status.
- Fixed valid doc-sync finding C8 by adding a current-progress note that
  distinguishes compact index every `remote-delta` turn from memory every
  `native_sync_every` provider turns.
- Focused audit tests passed:
  - prompt/provider metadata, details, removed host action, and batch-schema
    tests: `7 passed, 88 deselected`
  - model-native skills, P0 foundation, and Branch C harness unit tests:
    `42 passed`
- Full FirmCLI suite ladder passed and wrote
  `runs/wave1-delta-index-adversarial-audit-suite-report.txt`.
- Codex CLI live attached-board Branch C harness passed:
  - `nucleo_l476rg`: `9 passed`, run root
    `runs/20260630T202123Z-c21d0a10`
  - `nrf52840dk`: `9 passed`, run root
    `runs/20260630T202328Z-f4d44973`
- Claude CLI live attempts on both attached boards were blocked by local Claude
  CLI auth: `Not logged in - Please run /login`. Hardware preconditions passed
  before provider handoff; the provider never reached a valid decision.
- Process cleanup audit after live/failing provider rows found no new matching
  leftover provider, MCP, pyOCD, or validation processes beyond the audit shell.
- Final post-doc-edit suite ladder passed and wrote
  `runs/wave1-delta-index-adversarial-audit-final-suite-report.txt`.
- Final Python-change gate passed: Ruff check/fix, Ruff format, Pyright
  `0` diagnostics across 115 analyzed files, and pytest `359 passed`.

## In progress

- Complete.

## TODO

- None for the agent-verifiable Wave 1/delta-index surface.

## Limitations and known gaps

- Wave 2 modules remain out of scope for this Wave 1 audit: progress/inspector,
  stream checkpoints, scoped green approval, codebase map/cache reuse, and
  process-tree cleanup guard.
- Exact official `nrf52833dk` proof is pending unless that board is physically
  attached; current attached Nordic proof uses `nrf52840dk`.
- API-provider parity depends on available OpenAI/Anthropic credentials.
- Claude CLI proof depends on the local Claude CLI auth/quota state.

## Hardware hand-off

- Codex CLI live proof completed on the two attached boards:
  - `uv run python -m tests.harness.branch_c_tests --board-id nucleo_l476rg --provider codex-cli --provider-timeout-seconds 240`
  - `uv run python -m tests.harness.branch_c_tests --board-id nrf52840dk --provider codex-cli --provider-timeout-seconds 240`
- Claude CLI live proof was attempted on both attached boards but is blocked by
  local provider auth. After authenticating Claude CLI, rerun:
  - `uv run python -m tests.harness.branch_c_tests --board-id nucleo_l476rg --provider claude-cli --provider-timeout-seconds 240`
  - `uv run python -m tests.harness.branch_c_tests --board-id nrf52840dk --provider claude-cli --provider-timeout-seconds 240`

## Open decisions and surfaced issues

Adversarial audit plan:

1. Prompt/cadence audit:
   - `ProviderPromptBundle` render methods.
   - OpenAI, Codex CLI, and Claude CLI remote-primary prompt selection.
   - native memory sync cadence and metadata.
2. Wave 1 action-boundary audit:
   - removed governed host actions stay structurally absent.
   - provider-native host work remains outside the brain action surface.
   - `action_batch` excludes `finalize` and stops on refusal/block.
3. Scaffold guardrail audit:
   - compact indexes are discovery-only.
   - governed tools, client actions/scripts, and `run_green_check` require
     brain-owned loaded-detail flags.
   - invalid governed-tool arguments auto-load focused details for retry.
4. Product/doc audit:
   - active docs describe compact index every provider turn without changing
     memory cadence.
   - active docs do not overclaim Wave 2, exact official-board, Claude/API, or
     fresh-machine proof.
5. Test/hardware audit:
   - run focused prompt/provider tests.
   - run the full FirmCLI suite ladder.
   - run Codex live attached-board checks.
   - attempt Claude live proof or document the external auth/quota boundary.

Initial criticisms to review:

- C1: `remote-delta` might now reset the memory sync counter every turn because
  compact indexes are sent every turn.
- C2: `remote-delta` might leak full MCP schemas or full decision schemas every
  turn.
- C3: `static_tool_schema_injected` might be misleading for `remote-delta`
  because it now means compact governed-tool index, not the full decision
  schema.
- C4: compact indexes every turn might undermine scaffold hardening if the brain
  treats index visibility as execution authorization.
- C5: Wave 1 might still expose removed host actions as governed decisions.
- C6: docs may be stale because the new delta-index spec/process/review docs
  were not indexed in `markdowns/curr/README.md`.
- C7: the delta-index spec may still say proposal after implementation.
- C8: current-progress may not clearly record that compact indexes are every
  `remote-delta` turn while memory remains every `native_sync_every` turns.

Audit review:

- C1 no merit. `advance_memory_sync_state()` still keys only from provider
  metadata `memory_injected`, and `remote-delta` metadata remains
  `memory_injected=false`.
- C2 no merit. `render_remote_delta_text()` includes compact skill context,
  compact governed-tool index, and turn context only; focused tests prove memory
  and the full decision schema are absent.
- C3 no code fix. The metadata field name is historically imprecise, but the
  current value now accurately records that the compact governed-tool index was
  injected. It does not claim the full decision schema was injected.
- C4 no merit. The detail-required guardrails remain in the execution path and
  stop batches on missing details before executing the original governed call.
- C5 no merit. Removed host actions remain structurally absent from valid action
  models/schemas and are rejected if returned through stale batch syntax.
- C6 valid doc-sync issue. Fixed in `markdowns/curr/README.md`.
- C7 valid doc-sync issue. Fixed in
  `markdowns/curr/r12-delta-compact-indexes_spec.md`.
- C8 valid doc-sync issue. Fixed in `markdowns/current-progress.md`.

## Verified

- Non-hardware focused tests:
  - `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle or load_tool_details or details_required or excludes_finalize_from_action_batch or removed_host_action" tests/test_r12_turnkey_merge.py -k "previous_response_id or resumes_remote_session or resumes_remote_thread or retry_updates_prompt_metadata or removed_host"`
    -> `7 passed, 88 deselected`
  - `uv run pytest -q tests/test_p0_foundation.py tests/test_model_native_skills.py tests/test_branch_c_harness.py`
    -> `42 passed`
- Suite ladder:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/wave1-delta-index-adversarial-audit-suite-report.txt`
  -> pytest `359 passed`, Ruff, mypy, R11 benchmark tests, and R11 benchmark
  help all passed.
- Final suite ladder after doc-sync fixes:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/wave1-delta-index-adversarial-audit-final-suite-report.txt`
  -> pytest `359 passed`, Ruff, mypy, R11 benchmark tests, and R11 benchmark
  help all passed.
- Python-change gate:
  `uv run python .codex/skills/python-change/scripts/run_python_change_checks.py`
  -> Ruff check/fix passed, Ruff format left 110 files unchanged, Pyright
  reported `0` diagnostics, and pytest `359 passed`.
- Codex live artifacts show the desired provider chain on both attached boards:
  turn 1 `load_tool_details(connect,get_board_info)`, turn 2
  `action_batch(connect,get_board_info)`, turn 3 `finalize`.
- Codex live artifact metadata for `remote-delta` turns shows
  `static_tool_schema_injected=true`, `memory_injected=false`, and
  `decision_schema_injected=false`.
- Cleanup audit output:
  `No new matching leftover processes beyond this audit shell.`

## Pending verification

- Claude CLI proof after `claude /login` or equivalent local auth repair.
- OpenAI/Anthropic API-provider parity with credentials.
- Exact official `nrf52833dk` proof if the official Nordic board is attached.
- Fresh-machine deployment proof.
