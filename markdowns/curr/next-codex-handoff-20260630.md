# Next Codex Handoff - 2026-06-30 Final Audit

Purpose: start a fresh Codex session that independently checks the current
`P-Wave-0` repo after the R12 scaffold-hardening implementation and final docs
cleanup. Do not treat this handoff as proof. Use it as a map for a serious code,
product, documentation, and live-validation audit.

## Current repo state to verify first

- Branch: `P-Wave-0`
- Implementation commit to audit: `7f1360b Implement R12 scaffold hardening`
- This handoff may be committed as a doc-only commit on top of `7f1360b`.
- Expected first check:

```powershell
git status --short
git branch --show-current
git log -1 --oneline
```

Expected result before auditing: clean worktree on `P-Wave-0`. `git log -1`
may show this handoff commit; verify that `7f1360b` is in recent history and is
the implementation commit under audit. If the worktree is dirty, inspect before
changing anything.

## Read these docs first

Read in this order:

1. `README.md` - repo layout and normal project commands.
2. `markdowns/current-progress.md` - current implementation/proof status and
   remaining external proof gaps.
3. `markdowns/things-to-change.md` - hard prototype acceptance bar. This is the
   most important product-scope document.
4. `markdowns/R12_P_SPLIT.md` - Wave 1/Wave 2 scheduling and branch/module
   boundaries.
5. `markdowns/ROADMAP.md` - broader roadmap and dependency order.
6. `markdowns/firmware_agent_build_plan_concrete (10).md` - original
   step-ordered build plan and product intent.
7. `markdowns/curr/README.md` - active current-doc index.
8. `markdowns/curr/r12_turnkey_spec.md` - R12 turnkey brain contract.
9. `markdowns/curr/r12-context-scaffold-hardening_spec.md` - the feature just
   implemented and the expected behavior to audit closely.
10. `markdowns/curr/wave2-codebase-map_spec.md` - next Wave 2 Module G scope,
    useful for checking that the new scaffold is a proper substrate.
11. `markdowns/repo_file_index.md` - file map after the cleanup.

Historical evidence only, not current authority:

- `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/`
- `markdowns/tmp/curr-archive-20260630-wave1-final/`
- older `markdowns/tmp/**` archives

Those archives contain process ledgers, earlier audit notes, and run IDs. Use
them to understand what was claimed and tested, but prefer live code/tests over
archive claims.

## Product in one paragraph

Firmware-CLI is a local firmware-debug agent stack. A provider such as Codex or
Claude can do host-side reasoning and file/code work freely in its own sandbox.
The Firmware-CLI brain is the governed board gate: every provider loop ends in
one structured decision that either performs a governed board/client action,
loads more context, waits, or returns. The MCP server owns hardware tools over
pyOCD/UART/service abstractions, while the brain owns prompt assembly, provider
turns, action parsing, safety policy, state/evidence, and run artifacts.

## Wave 1 scope to audit

Wave 1 is the current implemented product slice, not the full prototype.

- Branch A: provider session and compact tool-index prompt. The provider should
  get a curated compact index, not repeated full MCP JSON schemas on ordinary
  turns.
- Branch B: action boundary, batches, client actions, model-native skill loading,
  and the free-host-work / final governed decision contract. Host-only file,
  shell, and build work must stay provider-native and must not reappear as
  governed brain actions.
- Branch C: event spine and timeout policy. Provider, brain, server, and client
  activity should be observable through the current event/artifact surfaces and
  bounded by project timeout policy.
- R12 scaffold hardening: the just-landed follow-up that makes compact indexes
  discovery-only and adds hard details-before-execution guardrails.

Wave 2 is not done. Progress UI/inspector, checkpoints, scoped green approval,
codebase-map scaffolding, cache-assisted reuse, and cleanup guard work remain
prototype-required future modules.

## New scaffold-hardening behavior to check

Audit these as product invariants:

- Model-native product skills must not default to `.codex/skills` or
  `.claude/skills`. Those are operator/developer workflow skills, not product
  runtime skill roots.
- Installed product skill packages are client-owned and read-only from provider
  recovery. Provider repair happens only in per-run runtime/session copies.
- Skill manifests must be validated, copied to runtime before init/context, and
  loaded with structured provider-visible failures and recovery choices.
- `load_skills(skill_ids=[...])` remains a context-expansion decision, not a
  host execution path.
- `load_tool_details(tool_names=[...])` loads full governed-tool descriptions
  and schemas into the next provider turn without executing those tools.
- Governed MCP tools, governed client actions/scripts, and brain-owned compound
  actions such as `run_green_check` must not execute from index-only context.
  If details are missing, the brain should block, auto-load focused details,
  record the guardrail, and require a fresh provider decision.
- Invalid governed-tool arguments should inject focused full details for retry.
- The original blocked call must not execute in the same step after auto-detail
  loading.
- Prompt ordering/dedupe should be canonical: safety/action boundary, compact
  skill index, compact tool index, loaded details, loaded skill context, memory,
  turn context, decision schema.
- Removed governed host actions must remain structurally absent:
  `read_file`, `replace_file`, and `run_build` are not valid `TurnDecision`
  actions, executor branches, batch special cases, or model-visible decisions.

## Source files that matter most

Brain/action boundary:

- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/action_policy.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/events.py`

Context, skills, and schemas:

- `src/pyocd_debug_mcp/brain/model_native_skills.py`
- `src/pyocd_debug_mcp/brain/tool_schemas.py`
- `src/pyocd_debug_mcp/brain/client_actions.py`
- `src/pyocd_debug_mcp/brain/workspace.py`
- product skill metadata under `skills/`

Provider and parsing surfaces:

- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_parsing.py`
- `src/pyocd_debug_mcp/brain/mcp_client.py`

Hardware/server substrate:

- `src/pyocd_debug_mcp/server.py`
- `src/pyocd_debug_mcp/services/target_control.py`
- `src/pyocd_debug_mcp/services/uart_capture.py`
- `src/pyocd_debug_mcp/adapters/swd_pyocd.py`
- `src/pyocd_debug_mcp/adapters/uart_pyserial.py`
- `src/pyocd_debug_mcp/guardrails/`
- `boards/nucleo_l476rg.yaml`
- `boards/nrf52833dk.yaml`
- `boards/nrf52840dk.yaml`

Workflow/test infrastructure touched by the pass:

- `.codex/skills/firmcli-workflow-core/SKILL.md`
- `.codex/skills/firmcli-workflow-core/references/source-map.md`
- `.codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py`
- `.codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py`
- `.codex/skills/firmcli-workflow-core/scripts/self_test_skills.py`
- `.codex/skills/firmcli-{build,fix-bug,review,spec-loop,specs,test-suite,write-process}/SKILL.md`

## Tests that matter most

Focused R12/scaffold tests:

- `tests/test_r12_turnkey.py`
- `tests/test_model_native_skills.py`
- `tests/test_p0_foundation.py`
- `tests/test_r12_turnkey_merge.py`
- `tests/test_branch_c_harness.py`
- `tests/harness/branch_c_tests.py`

Broader regression tests:

- `tests/test_r11_benchmark.py`
- `tests/harness/r12_turnkey_benchmark.py`
- `tests/harness/r11_benchmark.py`
- `tests/harness/stage1_smoke.py`
- server/service tests under `tests/test_server_*.py`, `tests/test_target_control.py`,
  `tests/test_uart_capture.py`, `tests/test_timeout_policy.py`, and
  `tests/test_ux_cli.py`

## Files that are less important for this audit

Do not ignore these permanently, but they are not the center of the final Wave 1
audit:

- `markdowns/tmp/**` - historical evidence and archived ledgers. Read only when
  you need provenance for a claim.
- `runs/**` - gitignored runtime artifacts. Useful if present, but absent older
  run IDs are expected in a cleaned checkout.
- `firmware/*/reference/build/**` - generated/reference build artifacts.
- `.pytest_cache/**`, `__pycache__/**`, temporary provider runtimes.
- Old deleted D/E/F/G/H branch names in docs. Requirement content remains, but
  those branch objects are not active.

## Suggested audit plan for the next session

1. Confirm branch, commit, and clean worktree.
2. Read the docs listed above, especially `things-to-change.md`,
   `r12-context-scaffold-hardening_spec.md`, and `current-progress.md`.
3. Code-review the key files with an adversarial stance:
   - look for reintroduced governed host actions;
   - look for details-required bypasses;
   - look for source skill mutation paths;
   - look for prompt duplication or raw schema leakage on ordinary turns;
   - look for broad `except Exception` paths that hide product failures;
   - look for mismatches between docs and code.
4. Run the non-hardware validation ladder.
5. Run real MCP and hardware smokes if the boards/providers are available.
6. Review the provider transcripts/artifacts, not just process exit codes. The
   desired behavior is provider-native host work followed by a clear final
   governed/context/return decision, with details loaded before risky execution.
7. If valid issues are found, fix them with the normal FirmCLI process and rerun
   failed checks from the beginning. If only weak or no-merit criticisms remain,
   document that explicitly.

## Validation commands to rerun

Baseline Python/code gate:

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py
```

Expected at last handoff: Ruff pass, format pass, Pyright `0`, pytest
`357 passed`.

Suite ladder:

```powershell
uv run python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\next-codex-final-audit-suite-report.txt
```

Expected at last handoff: all rows pass, including pytest, Ruff, mypy,
`tests/test_r11_benchmark.py`, and `r11_benchmark --help`.

Focused tests if iterating:

```powershell
uv run pytest -q tests/test_r12_turnkey.py tests/test_model_native_skills.py tests/test_p0_foundation.py tests/test_r12_turnkey_merge.py tests/test_branch_c_harness.py
```

Markdown audit if docs change:

```powershell
python .codex\skills\firmcli-markdown-audit\scripts\inventory_markdowns.py --root markdowns --output markdowns\tmp\_markdown_audit_inventory.md
python .codex\skills\firmcli-markdown-audit\scripts\check_markdown_references.py --root markdowns --all --output markdowns\tmp\_markdown_audit_refs.md
python .codex\skills\firmcli-markdown-audit\scripts\find_markdown_overlap.py --root markdowns --output markdowns\tmp\_markdown_audit_overlap.md
```

Delete temporary `_markdown_audit_*` files before committing. The reference
checker may still flag older gitignored run IDs and shorthand historical paths;
distinguish those from active broken references.

Hardware/live validation:

- Use attached-board checks on the real available boards. The last pass used
  `nucleo_l476rg` and `nrf52840dk`.
- Exact official `nrf52833dk` proof is still pending unless that board is
  actually attached.
- Claude CLI and native API-provider proof are still pending unless login/quota
  and credentials are available.
- Prefer live `pyocd`/MCP/provider runs that exercise multiple provider turns
  and at least one detail-loading path before a governed action.

## Known remaining gaps

These are real gaps, not hidden failures in the current code:

- Claude CLI proof depends on login/quota availability.
- OpenAI/Anthropic API-provider parity depends on credentials.
- Exact official `nrf52833dk` proof depends on that board being attached.
- Fresh-machine portability proof is still pending.
- Wave 2 modules remain unimplemented: progress UI/inspector, checkpoints,
  scoped green approval, codebase-map scaffolding/cache reuse, and cleanup guard.
- Future client-owned global bug-reporting is design-only until remote/backend
  infrastructure exists.

## What not to regress

- Do not add generic host execution to the brain or MCP server.
- Do not make `.codex/skills` or `.claude/skills` the product skill root.
- Do not let provider recovery mutate installed product skill source packages.
- Do not execute a governed tool/script/compound action in the same step that
  auto-loaded its missing details.
- Do not claim exact official-board, Claude, API, or fresh-machine proof unless
  that proof was actually run in the current environment.
- Do not use archived `markdowns/tmp/**` ledgers as current authority when they
  conflict with `current-progress.md`, `things-to-change.md`, or `curr/README.md`.
