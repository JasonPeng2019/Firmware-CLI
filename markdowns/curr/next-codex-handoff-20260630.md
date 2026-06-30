# Next Codex Handoff - 2026-06-30 Wave 1 Final Double Check

Purpose: start a fresh Codex session that independently audits the current
`P-Wave-0` repo after the R12 scaffold-hardening work, the delta compact-index
change, and the latest adversarial audit. Do not treat this file or prior run
logs as proof. Use it as the map for a serious code, product, documentation,
provider, MCP, and real-hardware audit.

The next session should verify the implementation from first principles, rerun
the strongest practical tests, inspect live artifacts rather than trusting exit
codes alone, and only call the surface clean if the code, docs, product behavior,
and real attached-board proof all line up.

## Current Repo State To Verify First

- Branch expected: `P-Wave-0`
- Recent commits expected:
  - `c91bde5 0-set-added features wave 1`
  - `a5f28b6 Add final audit handoff`
  - `7f1360b Implement R12 scaffold hardening`
- The working tree is expected to be dirty with the current uncommitted
  delta-index and audit-pass changes. Do not assume a clean tree.

Expected first commands:

```powershell
git status --short
git branch --show-current
git log -3 --oneline
git diff --stat
```

Expected dirty files from the latest pass:

- Modified code/tests:
  - `src/pyocd_debug_mcp/brain/provider_types.py`
  - `src/pyocd_debug_mcp/brain/provider_openai.py`
  - `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
  - `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
  - `tests/test_r12_turnkey.py`
  - `tests/test_r12_turnkey_merge.py`
- Modified docs:
  - `markdowns/curr/README.md`
  - `markdowns/current-progress.md`
  - `markdowns/curr/next-codex-handoff-20260630.md`
- New docs:
  - `markdowns/curr/r12-delta-compact-indexes_spec.md`
- Archived evidence now under
  `markdowns/tmp/curr-archive-20260630-delta-index-final/`:
  - `r12-delta-compact-indexes_process.md`
  - `r12-delta-compact-indexes_review.md`
  - `wave1-delta-index-adversarial-audit_process.md`
  - `wave1-adversarial-audit_process.md`
  - `wave1-audit-prompt-detail-fixes_spec.md`
  - `wave1-audit-prompt-detail-fixes_review.md`

If additional dirty files exist, inspect them before editing. Do not revert
anything unless the user explicitly asks.

## Read These Docs First

Read in this order:

1. `superpowers/agent_index_START_HERE.md`
2. `superpowers/agent_consistency_playbook.md`
3. `markdowns/firmware_agent_build_plan_concrete (10).md`
4. `superpowers/agent_coding_playbook.md`
5. `superpowers/agent_doc_sync_playbook.md`
6. `superpowers/spec_build_review_loop_playbook.md`
7. `README.md`
8. `markdowns/current-progress.md`
9. `markdowns/things-to-change.md`
10. `markdowns/R12_P_SPLIT.md`
11. `markdowns/ROADMAP.md`
12. `markdowns/curr/README.md`
13. `markdowns/curr/r12_turnkey_spec.md`
14. `markdowns/curr/r12-context-scaffold-hardening_spec.md`
15. `markdowns/curr/r12-delta-compact-indexes_spec.md`
16. `markdowns/curr/wave2-codebase-map_spec.md`
17. `markdowns/repo_file_index.md`
18. `markdowns/tmp/curr-archive-20260630-delta-index-final/r12-delta-compact-indexes_process.md`
19. `markdowns/tmp/curr-archive-20260630-delta-index-final/r12-delta-compact-indexes_review.md`
20. `markdowns/tmp/curr-archive-20260630-delta-index-final/wave1-delta-index-adversarial-audit_process.md`

Historical evidence only, not current authority:

- `markdowns/tmp/**`
- older run IDs in `runs/**`
- archived Wave 1/scaffold process ledgers

Use archived docs and old run roots to understand history, but prefer live code,
current docs, and fresh test output.

## Product In One Paragraph

Firmware-CLI is a local firmware-debug agent stack. A provider such as Codex or
Claude can reason and do host-side file/code/build work freely in its own
provider sandbox. The Firmware-CLI brain is the governed board gate: each
provider turn ends in one structured `TurnDecision` that either loads context,
waits, performs a governed board/client action, or finalizes. The local MCP
server owns hardware access over pyOCD/UART/service abstractions. The brain owns
prompt assembly, provider turns, action parsing, detail-before-execution
guardrails, timeout/convergence policy, state/evidence, and run artifacts.

## Current Feature Under Double Check

Latest delta-index change:

- Ordinary remote-primary `remote-delta` provider turns now include:
  - compact skill context;
  - compact governed-tool index;
  - current turn context.
- Ordinary `remote-delta` turns still exclude:
  - compact provider memory;
  - full `TurnDecision` schema;
  - full MCP input schemas.
- Memory cadence is unchanged:
  - `native_sync_every` controls compact provider-memory injection;
  - default remains every 10 provider turns;
  - `--native-sync-every 0` disables periodic memory sync.
- Full schemas/details are still available through bootstrap/sync/retry and
  explicit or auto-focused detail-loading paths.
- Provider metadata now treats `static_tool_schema_injected=true` on
  `remote-delta` when the compact governed-tool index is present. This does not
  mean the full decision schema was injected; `decision_schema_injected` remains
  false for normal `remote-delta`.

Important implementation points:

- `ProviderPromptBundle.render_remote_delta_text()` in
  `src/pyocd_debug_mcp/brain/provider_types.py`
- metadata updates in:
  - `provider_openai.py`
  - `provider_codex_cli.py`
  - `provider_claude_cli.py`
- tests in:
  - `tests/test_r12_turnkey.py`
  - `tests/test_r12_turnkey_merge.py`

## Wave 1 Scope To Audit

Wave 1 is the current implemented product slice. It is not the full prototype.

- Branch A: provider sessions and compact tool-index prompting.
  - OpenAI uses Responses continuation.
  - Codex CLI resumes a Codex thread.
  - Claude CLI resumes a Claude Code session when logged in.
  - Anthropic API remains local-primary because Messages is stateless.
  - Compact tool metadata should be visible without repeating full JSON schema
    bodies on ordinary turns.
- Branch B: action boundary, batches, client actions, model-native skill
  loading, and free host work followed by final governed decisions.
  - Host file/edit/build work must remain provider-native, not governed brain
    actions.
  - `read_file`, `replace_file`, and `run_build` must remain structurally absent
    from valid `TurnDecision` actions, executor branches, batch special cases,
    and model-visible decisions.
  - `load_skills(skill_ids=[...])` is context expansion, not generic host
    execution.
  - `run_script` is governed only for registered client actions and all server
    calls inside it go back through the brain gate.
- Branch C: event spine and timeout policy.
  - provider/brain/server/client activity should be evented and artifacted;
  - timeouts should be clamped inside project hard caps;
  - server timeout sync is brain-only/internal and not model-facing.
- Scaffold hardening:
  - compact indexes are discovery-only;
  - full details must be loaded before governed tool/script/compound execution;
  - missing details block, auto-load focused details if possible, record an
    event, and require a fresh provider decision.

Wave 2 is not done. Progress UI/inspector, stream checkpoints, scoped green
approval, codebase map/cache reuse, and process-tree cleanup guard remain
prototype-required future modules.

## Product Invariants To Double Check

Audit these as must-not-regress invariants:

- Product model-native skills must not default to `.codex/skills` or
  `.claude/skills`.
- Installed product skill packages are client-owned/read-only from provider
  recovery; provider repair happens only in runtime/session copies.
- Skill manifests are validated, copied to runtime before init/context, and
  loaded with structured provider-visible failures and recovery choices.
- `load_tool_details(tool_names=[...])` loads full governed-tool descriptions
  and schemas into the next provider turn without executing tools.
- Governed MCP tools, governed client actions/scripts, and `run_green_check`
  cannot execute from index-only context.
- The original missing-detail call must not execute in the same step after
  auto-detail loading.
- Invalid governed-tool arguments should auto-inject focused full details for
  retry.
- `action_batch` must exclude `finalize`, execute ordered non-final actions,
  and stop on the first refusal/block/failure that changes blocked/refused
  state.
- Prompt ordering should remain:
  safety/action-boundary rules, compact skill index, compact governed-tool
  index, loaded tool/client/compound details, loaded skill context, provider
  memory when cadence says so, turn context, decision schema.
- Ordinary `remote-delta` must include compact indexes but not memory or full
  schemas.
- Provider-memory cadence is by provider turns, not top-level user prompts.
- A top-level user prompt may contain multiple internal provider turns.

## Important Source Files

Brain/action boundary:

- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/action_policy.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/events.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`

Prompt/session/provider surfaces:

- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_parsing.py`
- `src/pyocd_debug_mcp/brain/tool_schemas.py`
- `src/pyocd_debug_mcp/brain/skills.py`
- `src/pyocd_debug_mcp/brain/model_native_skills.py`

Client action and workspace surfaces:

- `src/pyocd_debug_mcp/brain/client_actions.py`
- `src/pyocd_debug_mcp/brain/workspace.py`
- `src/pyocd_debug_mcp/brain/timeout_policy.py`
- `src/pyocd_debug_mcp/timeouts.py`

MCP/server/hardware substrate:

- `src/pyocd_debug_mcp/brain/mcp_client.py`
- `src/pyocd_debug_mcp/server.py`
- `src/pyocd_debug_mcp/services/target_control.py`
- `src/pyocd_debug_mcp/services/uart_capture.py`
- `src/pyocd_debug_mcp/adapters/swd_pyocd.py`
- `src/pyocd_debug_mcp/adapters/uart_pyserial.py`
- `src/pyocd_debug_mcp/guardrails/`
- `boards/nucleo_l476rg.yaml`
- `boards/nrf52833dk.yaml`
- `boards/nrf52840dk.yaml`

Operator/UX and CLI:

- `src/pyocd_debug_mcp/brain/cli.py`
- `src/pyocd_debug_mcp/brain/app.py`
- `src/pyocd_debug_mcp/brain/benchmark.py`
- `src/pyocd_debug_mcp/ux/`

Workflow/test infrastructure:

- `.codex/skills/firmcli-workflow-core/SKILL.md`
- `.codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py`
- `.codex/skills/python-change/scripts/run_python_change_checks.py`
- `.codex/skills/firmcli-specs/SKILL.md`
- `.codex/skills/firmcli-build/SKILL.md`
- `.codex/skills/firmcli-review/SKILL.md`
- `.codex/skills/firmcli-spec-loop/SKILL.md`
- `.codex/skills/firmcli-fix-bug/SKILL.md`
- `.codex/skills/firmcli-test-suite/SKILL.md`
- `.codex/skills/firmcli-write-process/SKILL.md`

## Tests And Harnesses That Matter

Focused R12/Wave 1:

- `tests/test_r12_turnkey.py`
- `tests/test_r12_turnkey_merge.py`
- `tests/test_model_native_skills.py`
- `tests/test_p0_foundation.py`
- `tests/test_branch_c_harness.py`
- `tests/harness/branch_c_tests.py`

Broader regression:

- `tests/test_r11_benchmark.py`
- `tests/harness/r11_benchmark.py`
- `tests/harness/r12_turnkey_benchmark.py`
- `tests/harness/stage1_smoke.py`
- `tests/test_server_*.py`
- `tests/test_target_control.py`
- `tests/test_uart_capture.py`
- `tests/test_timeout_policy.py`
- `tests/test_ux_cli.py`

## Files Less Important For This Audit

Do not ignore these forever, but they are not the center of the Wave 1 final
double check:

- `markdowns/tmp/**` - historical evidence only.
- older `runs/**` - useful if present, but gitignored and not authoritative.
- `firmware/*/reference/build/**` - generated/reference build outputs.
- `.pytest_cache/**`, `__pycache__/**`, temporary provider runtimes.
- old deleted D/E/F/G/H branch names in docs. Requirement content remains, but
  those git branches are not active.

## Audit Plan For The Next Session

1. Confirm branch, dirty files, and recent commits.
2. Read the docs listed above.
3. Review the current diff line by line.
4. Audit the whole Wave 1 product surface adversarially:
   - prompt/cadence bugs;
   - schema or detail-loading bypasses;
   - hidden full-schema leakage on ordinary turns;
   - stale governed host actions;
   - provider fallback that silently creates fresh sessions;
   - source skill mutation paths;
   - broad exception handling that hides product failures;
   - timeout/event behavior that is not actually bounded/observable;
   - doc claims not backed by code or runs.
5. Run non-hardware checks.
6. Run live MCP/hardware/provider checks on both attached boards.
7. Inspect artifacts, not just exit codes:
   - `logs/model_turns.jsonl`
   - `logs/brain_events.jsonl`
   - `logs/brain_trace.jsonl`
   - `runs/<session_id>/run-metadata/turnkey_state.json`
   - `runs/<session_id>/run-metadata/turnkey_result.json`
8. If valid issues are found, use the FirmCLI workflow:
   - write/update a narrow spec;
   - fix through the smallest correct change;
   - run Python-change for Python edits;
   - rerun focused checks and the full suite;
   - rerun live hardware/provider checks from the beginning.
9. If only no-merit criticisms remain, document why they are no-merit with code
   and artifact evidence.

## Baseline Non-Hardware Commands To Run

Python-change gate:

```powershell
uv run python .codex/skills/python-change/scripts/run_python_change_checks.py
```

Expected from the last pass:

- Ruff check/fix passed.
- Ruff format left 110 files unchanged.
- Pyright reported `0` diagnostics across 115 analyzed files.
- pytest `359 passed`.

Suite ladder:

```powershell
uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/next-codex-wave1-final-double-check-suite-report.txt
```

Expected from the last pass:

- pytest `359 passed`;
- Ruff passed;
- mypy passed;
- `tests/test_r11_benchmark.py` passed with `34 passed`;
- `python -m tests.harness.r11_benchmark --help` passed.

Focused checks if iterating:

```powershell
uv run pytest -q tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py tests/test_model_native_skills.py tests/test_p0_foundation.py tests/test_branch_c_harness.py
```

Targeted delta-index check:

```powershell
uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle or load_tool_details or details_required or excludes_finalize_from_action_batch or removed_host_action" tests/test_r12_turnkey_merge.py -k "previous_response_id or resumes_remote_session or resumes_remote_thread or retry_updates_prompt_metadata or removed_host"
```

## Live Hardware, MCP, Provider, Multi-Turn Validation Target

The next session should do more than one unit smoke if provider auth and board
access allow it. The desired final double-check is a full product deployment
exercise:

- real local MCP server path, not mocked client only;
- both real attached boards:
  - `nucleo_l476rg`
  - `nrf52840dk` if that is the attached Nordic board, or `nrf52833dk` if the
    official board is attached;
- real provider backends:
  - `codex-cli`;
  - `claude-cli` if logged in;
  - API providers only if credentials and model config are available;
- multiple internal provider turns inside each prompt;
- multiple top-level user prompts in one product session where possible;
- provider should be self-directed on host side and return a final governed
  decision only at the brain boundary;
- details should be loaded before governed tool/client/compound execution;
- run artifacts should prove provider session state, remote-delta prompt
  metadata, decisions, tool calls, events, board evidence, and final result.

Minimum attached-board harness rows:

```powershell
uv run python -m tests.harness.branch_c_tests --board-id nucleo_l476rg --provider codex-cli --provider-timeout-seconds 240
uv run python -m tests.harness.branch_c_tests --board-id nrf52840dk --provider codex-cli --provider-timeout-seconds 240
```

If Claude CLI is authenticated:

```powershell
uv run python -m tests.harness.branch_c_tests --board-id nucleo_l476rg --provider claude-cli --provider-timeout-seconds 240
uv run python -m tests.harness.branch_c_tests --board-id nrf52840dk --provider claude-cli --provider-timeout-seconds 240
```

If the official `nrf52833dk` is attached, replace the retained-board Nordic
rows with `--board-id nrf52833dk`, and include the recover-capable Stage 0/Stage
1 checks from `r12_turnkey_spec.md`.

Recommended full-product multi-prompt proof:

1. Start `pyocd-debug` in an interactive shell if the environment supports it.
2. Run at least three top-level prompts back to back:
   - verify STM32 reference health;
   - verify Nordic reference health;
   - run a small diagnose/repair-style prompt with a workspace/build context if
     a safe fixture is available.
3. Confirm each top-level prompt creates its own run root and own provider
   session state.
4. Confirm history/show/rerun can identify the runs separately.
5. Confirm no provider session, board session, workspace mutation, timeout
   config, or convergence counter leaks incorrectly between prompts.

If interactive shell automation is not practical, use the closest available
headless equivalent with multiple separate `pyocd-debug run` or
`pyocd-debug-brain run` prompts, then document that this does not fully prove
one interactive shell session.

Example headless commands:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Load details as needed, connect to this board, read board info, then return a concise diagnosis of whether the reference target is reachable."
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52840dk --task "Load details as needed, connect to this board, read board info, then return a concise diagnosis of whether the reference target is reachable."
```

After live runs, inspect artifacts. For each run root:

```powershell
Get-Content runs\<run_id>\logs\model_turns.jsonl
Get-Content runs\<run_id>\logs\brain_events.jsonl
Get-Content runs\<run_id>\run-metadata\turnkey_state.json
Get-Content runs\<run_id>\run-metadata\turnkey_result.json
```

Specific artifact expectations:

- bootstrap/full first turn includes compact indexes and decision schema;
- remote-delta follow-up turns include compact indexes;
- remote-delta follow-up turns show `memory_injected=false` unless a native sync
  turn is due;
- remote-delta follow-up turns show `decision_schema_injected=false`;
- details are loaded before `connect`, `get_board_info`, `read_serial`,
  `flash_firmware`, `run_script`, or `run_green_check`;
- no missing-detail blocked call executes in the same step;
- no stale host action appears as a valid governed action.

## Cleanup/Process Hygiene To Run Around Live Checks

Before live provider/hardware checks, snapshot matching processes:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'Firmware-CLI|pyocd-debug|branch_c_tests|codex|claude|pyocd|pytest|pyright|ruff|mypy|uv run' } |
  Select-Object ProcessId,ParentProcessId,Name,CommandLine |
  ConvertTo-Json -Depth 3 |
  Set-Content -Encoding utf8 runs\next-codex-process-baseline.json
```

After live provider/hardware checks, snapshot again and compare. Do not
broad-kill by process name. Only clean up a spawned process if it can be tied to
the current run by PID, parent PID, command line, run root, or other precise
provenance. Treat leftover spawned provider, MCP, pyOCD, serial, or validation
children as a suite failure or explicit deployment ambiguity.

## Last Known Verification From This Session

Last pass results to independently rerun, not trust:

- Focused prompt/provider/delta tests:
  - `7 passed, 88 deselected`
- P0/model-native/Branch C unit tests:
  - `42 passed`
- Suite ladder:
  - pytest `359 passed`, Ruff, mypy, R11 tests, R11 help passed
- Python-change gate:
  - Ruff, format, Pyright `0`, pytest `359 passed`
- Codex CLI attached-board Branch C harness:
  - `nucleo_l476rg`: `9 passed`, run root
    `runs/20260630T202123Z-c21d0a10`
  - `nrf52840dk`: `9 passed`, run root
    `runs/20260630T202328Z-f4d44973`
- Artifact spot-check from those Codex runs:
  - turn 1: `load_tool_details(connect,get_board_info)`;
  - turn 2: `action_batch(connect,get_board_info)`;
  - turn 3: `finalize`;
  - remote-delta turns had `static_tool_schema_injected=true`,
    `memory_injected=false`, and `decision_schema_injected=false`.
- Claude CLI attached-board attempts:
  - hardware preconditions passed;
  - provider blocked with `Not logged in - Please run /login`;
  - no valid Claude provider decision reached hardware.
- Process cleanup audit:
  - no new matching leftover processes beyond the audit shell.

## Known Remaining Gaps

These are real gaps unless the next session proves otherwise:

- Claude CLI proof requires local Claude login/quota availability.
- OpenAI/Anthropic API-provider parity requires credentials and model config.
- Exact official `nrf52833dk` proof requires that board to be attached; the
  current attached Nordic board has usually been `nrf52840dk`.
- Fresh-machine Windows/macOS deployment proof remains pending.
- Wave 2 modules remain unimplemented:
  - progress UI/inspector;
  - stream checkpoints;
  - scoped green approval;
  - codebase map/cache reuse;
  - process-tree cleanup guard.
- Future client-owned global bug reporting remains design-only until
  remote/backend infrastructure exists.

## What Not To Regress

- Do not add generic host execution to the brain or MCP server.
- Do not make `.codex/skills` or `.claude/skills` the product skill root.
- Do not allow provider recovery to mutate installed product skill packages.
- Do not execute a governed tool/script/compound action in the same step that
  auto-loaded its missing details.
- Do not put `finalize` inside `action_batch`.
- Do not re-add `read_file`, `replace_file`, or `run_build` as governed model
  actions.
- Do not change memory sync cadence while fixing compact index behavior.
- Do not claim exact official-board, Claude, API, fresh-machine, or
  multi-prompt one-shell proof unless it was actually run in the current
  session.

## Stop Conditions For The Next Session

Stop and report clearly if:

- Claude/API provider auth is unavailable;
- only the retained `nrf52840dk` is attached when official `nrf52833dk` proof is
  requested;
- interactive `pyocd-debug` multi-prompt proof cannot be automated in the
  current Codex environment;
- a live check leaves a spawned provider/MCP/pyOCD/serial process that cannot be
  safely attributed and cleaned up;
- a valid audit finding requires changing a settled product decision rather
  than fixing implementation drift.

## Final Output Expected From The Next Session

The next session should close with:

- exact files inspected and changed, if any;
- adversarial findings, separated into valid and no-merit;
- commands run and real outcomes;
- live run roots for each hardware/provider row;
- artifact evidence that provider behavior matched the product contract;
- cleanup/orphan-process evidence;
- remaining external proof boundaries;
- whether the agent-verifiable Wave 1/delta-index surface is clean.
