# Process ledger for wave1-adversarial-audit

## Goal and roadmap anchor

Task: Wave 1 final adversarial audit loop across R12 scaffold hardening and full Wave 1 product surface.
Roadmap anchor: R12 Stage 5 Wave 1, with the scaffold-hardening follow-up in
`markdowns/curr/r12-context-scaffold-hardening_spec.md`.

## Done

- Loaded the current handoff, FirmCLI workflow skills, core superpowers
  playbooks, README, current progress, hard prototype bar, R12 split, roadmap,
  active R12 specs, Wave 2 codebase-map spec, and repo file index.
- Verified starting repo state: branch `P-Wave-0`, clean worktree, latest
  commit `a5f28b6 Add final audit handoff`, implementation commit under audit
  `7f1360b Implement R12 scaffold hardening`.
- Created this process ledger.
- Wrote the adversarial audit plan below.
- Completed first static/code audit sweep across Wave 1/R12 scaffold invariants.
- Fixed valid finding `W1-AUD-001`: prompt bundle ordering did not match the
  active scaffold spec. Provider memory rendered before loaded tool/skill
  context, and compact turnkey skills were embedded inside turn context instead
  of having a stable pre-tool-index slot.
- Fixed valid finding `W1-AUD-002`: MCP schema/argument failures raised as
  `MCPClientError` were classified as unexpected action failures instead of
  preserving focused full tool details for retry.
- Added/updated regression coverage for both findings.
- Focused verification passed:
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle or invalid_mcp_arguments or blocks_server_tool or load_tool_details" tests/test_r12_turnkey_merge.py -k "prompt or memory or schema"`
  -> `15 passed, 79 deselected`.

## In progress

- Python-change validation for the prompt-order and invalid-argument fixes.

## TODO

- Create the narrow fix spec/review artifacts for the two valid findings.
- Run the full non-hardware suite from the beginning after the final fix.
- Run the strongest provider/MCP/hardware smokes available in this session,
  with process/session hygiene checks before and after.
- Repeat the adversarial audit after the suite is green; stop only when the
  remaining findings are no-merit or explicit external proof boundaries.

## Adversarial audit plan

Important code files to read/audit:

- Brain/action boundary: `src/pyocd_debug_mcp/brain/loop.py`,
  `actions.py`, `action_policy.py`, `state.py`, `provider_types.py`,
  `events.py`, `timeout_policy.py`, and `timeout_runtime.py`.
- Context/scaffold: `model_native_skills.py`, `tool_schemas.py`,
  `client_actions.py`, `workspace.py`, and product skill metadata under
  `skills/` / `skills/model_native/` if present.
- Provider/parsing: `provider_codex_cli.py`, `provider_claude_cli.py`,
  `provider_openai.py`, `provider_anthropic.py`, `provider_parsing.py`, and
  `mcp_client.py`.
- Hardware/server substrate: `server.py`, `services/target_control.py`,
  `services/uart_capture.py`, `adapters/swd_pyocd.py`,
  `adapters/uart_pyserial.py`, `guardrails/`, and board YAMLs.
- Workflow/test infrastructure touched by this pass:
  `.codex/skills/firmcli-workflow-core/**`,
  `.codex/skills/firmcli-{build,fix-bug,review,spec-loop,specs,test-suite,write-process}/SKILL.md`,
  `.codex/skills/python-change/**`, focused tests under `tests/`, and
  `tests/harness/branch_c_tests.py`.

Product/features to inspect adversarially:

- Removed host actions: `read_file`, `replace_file`, and `run_build` must be
  structurally absent from `TurnDecision`, schema rendering, executor branches,
  batch special cases, prompts, and model-visible decisions.
- Free host work / final governed decision contract: provider-native host work
  remains outside the brain, while every provider turn still closes with one
  governed board/client/terminal/context-expansion decision.
- Compact tool index: ordinary prompts must show discovery metadata only, not
  repeated full MCP JSON schema bodies.
- Details-before-execution: governed MCP tools, governed client scripts, and
  brain-owned compound actions such as `run_green_check` must block from
  index-only context, auto-load focused details, and require a fresh provider
  decision before execution.
- Invalid governed-tool arguments must inject focused full details for retry
  without executing the invalid call.
- Model-native skills: default root must be product/client-owned, installed
  packages read-only, runtime copies used for init/context/recovery, structured
  failures visible to the provider, and `.codex` / `.claude` excluded as
  product runtime stores.
- Prompt ordering/dedupe: safety/action-boundary, compact skill index, compact
  tool index, loaded details, loaded skill context, memory, turn context, and
  decision schema must be canonical and non-duplicating.
- Provider failure classification: distinguish provider transport/runtime,
  invalid provider output, parser/schema bugs, adapter/state bugs, governed
  tool failures, and context-expansion failures.
- Event/timeout surface: provider, brain, server, and client activity should
  produce useful artifacts/events and respect project timeout caps.
- Product gaps: Wave 2 hard-bar modules remain intentionally unimplemented and
  must not be silently called complete; docs must draw that boundary honestly.

Markdowns to refer to for authority and guidance:

- Authority/order: `superpowers/agent_index_START_HERE.md`,
  `superpowers/agent_consistency_playbook.md`,
  `superpowers/agent_coding_playbook.md`,
  `superpowers/agent_doc_sync_playbook.md`,
  `superpowers/spec_build_review_loop_playbook.md`, and
  `markdowns/firmware_agent_build_plan_concrete (10).md`.
- Product scope/status: `markdowns/things-to-change.md`,
  `markdowns/R12_P_SPLIT.md`, `markdowns/ROADMAP.md`,
  `markdowns/current-progress.md`, and `README.md`.
- Active specs: `markdowns/curr/r12_turnkey_spec.md`,
  `markdowns/curr/r12-context-scaffold-hardening_spec.md`,
  `markdowns/curr/wave2-codebase-map_spec.md`, and
  `markdowns/curr/README.md`.
- Codebase map: `markdowns/repo_file_index.md`.

Audit method:

1. Static search for forbidden host actions, `.codex`/`.claude` product-root
   leakage, raw schema leakage, stale aliases, broad hidden failures, and
   bypassable detail guards.
2. Read the implicated code in full or in focused line ranges sufficient to
   trace behavior end to end.
3. Cross-check focused tests against each invariant; mark gaps where tests are
   missing even if the code appears correct.
4. Run focused non-hardware tests for Wave 1/R12 scaffolding.
5. Run the suite ladder. If it fails, route real defects through
   `firmcli-fix-bug` and restart the full suite.
6. Attempt provider/hardware smokes only after non-hardware checks pass, using
   task files and explicit timeouts; record any external blockers honestly.
7. Repeat static audit after fixes and suite green.

## Limitations and known gaps

- Known from authority docs before live testing: Claude CLI proof may be blocked
  by login/quota, API-provider parity may be blocked by credentials, exact
  official `nrf52833dk` proof depends on that board being attached, and
  fresh-machine portability proof cannot be claimed from this checkout alone.
- Wave 2 modules D/E/F/G/H are prototype-required but out of Wave 1 scope and
  currently unimplemented by design.

## Hardware hand-off

- Pending live discovery of attached boards and available provider credentials.

## Open decisions and surfaced issues

- Valid fixed finding `W1-AUD-001`: prompt ordering/dedupe product gap.
  Evidence: `ProviderPromptBundle.render_bootstrap_text()` rendered
  `tool_schema_text -> provider_memory_text -> turn_context_text -> schema`,
  while loaded details and loaded model-native skill context live in
  `turn_context_text`. This contradicted
  `r12-context-scaffold-hardening_spec.md`'s immediate ordering contract:
  compact skill index, compact governed-tool index, loaded details, loaded
  model-native skill context, provider memory, turn context, decision schema.
  Fix: added `skill_context_text`, render it before the compact tool index, and
  moved provider memory after turn/loaded context.
- Valid fixed finding `W1-AUD-002`: invalid MCP-argument failure classification
  gap. Evidence: `_execute_batched_actions()` auto-loaded focused tool details
  only when `_execute_server_tool()` returned a `ToolTextResult`; MCP
  schema/argument failures that surfaced as `MCPClientError` went to the outer
  unexpected-failure path. Fix: classify only argument/schema-like
  `MCPClientError`s as invalid governed-tool calls, auto-load focused details,
  record a retryable result, and leave non-argument MCP failures as real
  tooling failures.
- No-merit criticism: `read_file`, `replace_file`, and `run_build` strings still
  appear in `workspace.py` and tests. Evidence: they are internal workspace
  helper method names and regression tests asserting old governed actions are
  rejected/absent; they are not `TurnDecision` variants or executor branches.
- No-merit / explicit-scope criticism: `skills/model_native/` is absent in this
  checkout. Evidence: the scaffold-hardening spec makes the full product skill
  library out of scope and explicitly allows structured missing-root/missing
  skill failures; the product-root default is no longer `.codex` or `.claude`.
- Explicit boundary: Wave 2 progress/inspector, checkpoints, scoped green
  approval, codebase map/cache reuse, and cleanup guard modules remain
  unimplemented by design and cannot be called Wave 1 defects unless a doc or
  code path claims they are complete.

## Verified

- Non-hardware verified so far: starting branch/worktree/commit state and
  authority-doc loading.
- Focused R12 prompt/detail regression tests verified the two fixed findings.

## Pending verification

- None for agent-verifiable Wave 1 surfaces in this checkout.
- External boundaries remain: Claude CLI login, API-provider credentials,
  fresh-machine proof, full model-native product skill content, and Wave 2
  modules.

## Final audit update

- Created `markdowns/curr/wave1-audit-prompt-detail-fixes_spec.md` and
  `markdowns/curr/wave1-audit-prompt-detail-fixes_review.md` as the narrow
  process artifacts for the valid code/product fixes.
- Python-change gate passed after fixes:
  `uv run python .codex/skills/python-change/scripts/run_python_change_checks.py`
  -> Ruff check/format, Pyright JSON, and `uv run pytest -q` all passed with
  `359 passed`.
- FirmCLI non-hardware suite ladder passed:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/wave1-adversarial-audit-suite-report.txt`
  -> pytest, Ruff, mypy, R11 benchmark tests, and R11 benchmark help all passed.
- Hardware-only live checks passed on both attached boards:
  `nucleo_l476rg` and `nrf52840dk`.
- Live Codex CLI provider + hardware smokes passed on both attached boards on
  the final code:
  `runs/20260630T191305Z-97e20d79` for `nucleo_l476rg` and
  `runs/20260630T191450Z-8fedbe20` for `nrf52840dk`.
- Live provider traces after hardening showed the desired chain:
  `load_tool_details(connect,get_board_info)` -> governed `connect` and
  `get_board_info` -> standalone `finalize`, with no refused batch-finalize
  correction path.
- A parallel final rerun briefly failed the Nordic Stage 0 hardware precondition
  while the Nucleo hardware run was active. The same Nordic command passed when
  rerun alone, so this was classified as a parallel hardware/probe precondition
  artifact, not a Wave 1 product failure.
- Claude CLI live proof is externally blocked in this checkout:
  `claude-cli` returned `Not logged in - Please run /login`.
- Cleanup/process hygiene snapshot after long provider/hardware checks showed
  the existing Codex/app MCP baseline processes; no new harness orphan requiring
  cleanup was identified.

## Final surfaced issues

- Valid fixed finding `W1-AUD-003`: live Codex provider initially tried to put
  `finalize` inside `action_batch` on the Nordic run. The brain correctly
  refused it and the provider corrected itself, so this was not an executor
  defect, but it was a product/schema clarity gap. Fix: enumerate valid
  `action_batch.calls[].action_type` values in the provider-facing decision
  schema, explicitly exclude `finalize`, and update the prompt to say finalize
  is a single action only.

## Final verdict

- Agent-verifiable Wave 1/R12 scaffold audit is clean after fixes.
- Remaining criticisms are no-merit or explicit boundaries: full product
  model-native skill content, Claude CLI login, fresh-machine portability, API
  provider credentials, and Wave 2 hard-bar modules.
