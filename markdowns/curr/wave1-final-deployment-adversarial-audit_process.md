# Process ledger for wave1-final-deployment-adversarial-audit

## Goal and roadmap anchor

Task: Wave 1 final product deployment adversarial audit loop
Roadmap anchor: R12 Stage 5 Wave 1 product deployment slice, the active
R12 scaffold-hardening contract, and the delta compact-index follow-up.

## Done

- Loaded the explicitly requested FirmCLI workflow skills:
  `firmcli-write-process`, `firmcli-test-suite`, `firmcli-fix-bug`, and
  `firmcli-spec-loop`, plus their required `firmcli-workflow-core`,
  `firmcli-specs`, `firmcli-build`, `firmcli-review`, and `python-change`
  support skills.
- Loaded the handoff and governing docs:
  `markdowns/curr/next-codex-handoff-20260630.md`,
  `superpowers/agent_index_START_HERE.md`,
  `superpowers/agent_consistency_playbook.md`,
  `superpowers/agent_coding_playbook.md`,
  `superpowers/agent_doc_sync_playbook.md`,
  `superpowers/agent_portability_playbook.md`,
  `superpowers/agent_script_doc_playbook.md`,
  `superpowers/spec_build_review_loop_playbook.md`,
  `markdowns/firmware_agent_build_plan_concrete (10).md`, `README.md`,
  `markdowns/ROADMAP.md`, `markdowns/current-progress.md`,
  `markdowns/things-to-change.md`, `markdowns/R12_P_SPLIT.md`,
  `markdowns/curr/README.md`, active R12 current specs, and
  `markdowns/repo_file_index.md`.
- Loaded archived delta-index and Wave 1 audit process/review/spec artifacts
  under `markdowns/tmp/curr-archive-20260630-delta-index-final/` as history,
  not current authority.
- Confirmed starting branch/state: branch `P-Wave-0`, expected recent commits
  `c91bde5`, `a5f28b6`, and `7f1360b`, and dirty files matching the handoff's
  delta-index/audit-pass set.
- Created this process ledger.

## In progress

- None.

## TODO

- Claude CLI proof after local `claude` authentication/login is restored.
- OpenAI/Anthropic API-provider parity proof when API credentials and model
  configuration are available.
- Exact official `nrf52833dk` destructive recover/reference Stage 0 proof using
  explicit opt-in Stage 0 arguments.
- Fresh-machine Windows/macOS proof from a clean checkout.

## Limitations and known gaps

- Wave 2 modules D/E/F/G/H remain prototype-required but are not part of the
  implemented Wave 1 product slice unless a current doc or code path falsely
  claims they are done.
- Claude CLI proof may be blocked by local provider login/quota.
- OpenAI/Anthropic API-provider parity depends on credentials and model config.
- Exact official `nrf52833dk` proof depends on which Nordic board is physically
  attached in this session.
- Fresh-machine Windows/macOS proof cannot be claimed from this existing
  checkout.

## Hardware hand-off

## Open decisions and surfaced issues

Adversarial audit plan:

1. Current diff and prompt cadence:
   - inspect `provider_types.py`, `provider_openai.py`,
     `provider_codex_cli.py`, `provider_claude_cli.py`,
     `tests/test_r12_turnkey.py`, and `tests/test_r12_turnkey_merge.py`;
   - verify ordinary `remote-delta` turns include compact skill context,
     compact governed-tool index, and turn context only;
   - verify memory cadence still follows `native_sync_every` and full decision
     schema/full MCP input schemas do not leak into ordinary deltas.
2. Wave 1 action boundary:
   - ensure `read_file`, `replace_file`, and `run_build` are absent from valid
     `TurnDecision` models, executor branches, batch special cases, prompts,
     and model-visible schemas;
   - confirm host file/edit/build work remains provider-native while every
     provider turn still closes with one governed board/client/terminal or
     context-expansion decision.
3. Scaffold hardening:
   - confirm product model-native skills do not default to `.codex/skills` or
     `.claude/skills`;
   - confirm skill source packages are copied to runtime before init/context,
     failures are structured, and source packages are not provider-repair
     targets;
   - confirm compact indexes are discovery-only and governed tools, governed
     client actions/scripts, and `run_green_check` require loaded-detail flags;
   - confirm missing-detail calls block, auto-load focused details, record an
     event/result, and require a fresh decision rather than executing the
     original call.
4. Provider/session/product behavior:
   - inspect strict resume/fresh-session behavior for OpenAI, Codex CLI, and
     Claude CLI;
   - inspect provider metadata and run artifacts for prompt render mode,
     memory injection, decision-schema injection, and tool-index injection.
5. Timeout/event/cleanup surface:
   - check Branch C timeout/event behavior and cleanup claims against current
     tests and process hygiene requirements;
   - audit for broad hidden failures or swallowed cleanup/provider exceptions
     that would make deployment evidence untrustworthy.
6. Product/docs:
   - ensure current docs distinguish Wave 1 from Wave 2, Codex proof from
     Claude/API proof, retained `nrf52840dk` from official `nrf52833dk`, and
     non-hardware proof from live board proof;
   - ensure active `curr` docs index this audit and do not leave completed
     process ledgers competing with current status.
7. Validation:
   - run focused tests, suite ladder, Python-change gate if needed, live
     provider/hardware checks where available, artifact spot checks, and
     before/after process audits.

Important files to inspect:

- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/action_policy.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/events.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_parsing.py`
- `src/pyocd_debug_mcp/brain/tool_schemas.py`
- `src/pyocd_debug_mcp/brain/model_native_skills.py`
- `src/pyocd_debug_mcp/brain/client_actions.py`
- `src/pyocd_debug_mcp/brain/mcp_client.py`
- `src/pyocd_debug_mcp/brain/timeout_policy.py`
- `src/pyocd_debug_mcp/timeouts.py`
- `src/pyocd_debug_mcp/server.py`
- `tests/test_r12_turnkey.py`
- `tests/test_r12_turnkey_merge.py`
- `tests/test_model_native_skills.py`
- `tests/test_p0_foundation.py`
- `tests/test_branch_c_harness.py`
- `tests/harness/branch_c_tests.py`

Audit execution and classification:

- Valid gap, fixed: this fresh active audit ledger was not listed in
  `markdowns/curr/README.md`. Added it to the active-doc and verified-doc
  index so the current work surface is discoverable.
- No-merit criticism: remote-delta prompt rendering might have regressed
  provider memory cadence. Code and live artifacts show memory cadence still
  follows provider metadata (`memory_injected=false` on ordinary delta turns in
  the live Codex runs).
- No-merit criticism: compact tool/skill indexes might leak full schemas into
  steady deltas. Tests and live artifacts show bootstrap includes the decision
  schema, while ordinary remote-delta turns omit `decision_schema_injected` and
  retain only compact index visibility plus loaded detail state.
- No-merit criticism: compact indexes might bypass governed-detail guardrails.
  Code inspection and live runs show providers first choose
  `load_tool_details(connect,get_board_info)`, then on a later turn execute the
  governed MCP calls.
- No-merit criticism: removed host actions might still be product-executable.
  `read_file`, `replace_file`, and `run_build` now appear only in docs, tests,
  or internal helper names; they are absent from `TurnDecision` action variants,
  action policy, model-visible schema, and executor branches.
- No-merit criticism: Codex CLI resume might silently restart a new thread in
  steady state. Live artifacts show the bootstrap turn creates a thread and
  turns 2-3 use `resumed_thread=true`, `prompt_render_mode=remote-delta`, and
  the same thread id.
- External boundary: Claude CLI rows reach hardware preconditions but the local
  CLI returns `Not logged in - Please run /login`; no valid Claude provider
  decision reaches hardware in this environment.
- External boundary: official `nrf52833dk` row sees the Nordic probe, but the
  current Branch C harness precondition does not pass the destructive
  `--recover-test` and explicit reference-firmware Stage 0 inputs required by
  that official board proof. The retained attached `nrf52840dk` row is green.
- Product boundary: Wave 2 hard-bar modules D/E/F/G/H remain pending by design;
  current Wave 1 docs still mark Claude/API, exact official `nrf52833dk`, and
  fresh-machine proof as not complete.

## Verified

- Focused prompt/provider/detail regression subset:
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle or load_tool_details or details_required or excludes_finalize_from_action_batch or removed_host_action or invalid_mcp_arguments or turn_decision_schema_excludes_finalize or disconnect_cleanup_fails" tests/test_r12_turnkey_merge.py -k "previous_response_id or resumes_remote_session or resumes_remote_thread or retry_updates_prompt_metadata or removed_host or resume_failure" tests/test_model_native_skills.py tests/test_p0_foundation.py tests/test_branch_c_harness.py`
  passed with `15 passed, 122 deselected`.
- Separate model-native/P0/Branch C deterministic checks:
  `uv run pytest -q tests/test_model_native_skills.py tests/test_p0_foundation.py tests/test_branch_c_harness.py`
  passed with `42 passed`.
- Full suite ladder:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/wave1-final-deployment-adversarial-audit-suite-report.txt`
  passed (`pytest 359 passed`, Ruff, mypy, R11 benchmark tests, and R11 harness
  help).
- Final suite ladder after the audit ledger update:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/wave1-final-deployment-adversarial-audit-final-suite-report.txt`
  passed (`pytest 359 passed`, Ruff, mypy, R11 benchmark tests, and R11 harness
  help).
- Python-change gate:
  `uv run python .codex/skills/python-change/scripts/run_python_change_checks.py`
  passed (Ruff check/fix, Ruff format, Pyright `0` diagnostics, pytest
  `359 passed`).
- Live Codex CLI Branch C, retained Nordic board:
  `uv run python -m tests.harness.branch_c_tests --board-id nrf52840dk --provider codex-cli --provider-timeout-seconds 240`
  passed `9 passed, 0 failed, 0 skipped`; log
  `runs/wave1-final-branch-c-nrf52840-codex.log`; run root
  `runs/20260630T210005Z-4e0dd0e4`.
- Live Codex CLI Branch C, Nucleo board:
  `uv run python -m tests.harness.branch_c_tests --board-id nucleo_l476rg --provider codex-cli --provider-timeout-seconds 240`
  passed `9 passed, 0 failed, 0 skipped`; log
  `runs/wave1-final-branch-c-nucleo-codex.log`; run root
  `runs/20260630T210158Z-66cd4110`.
- Codex artifact spot check for both live run roots:
  provider turn 1 used `bootstrap/full` with decision schema, turns 2-3 used
  `remote-delta`, `resumed_thread=true`, `decision_schema_injected=false`,
  `memory_injected=false`, and `static_tool_schema_injected=true`; action chain
  was `load_tool_details`, then `action_batch(connect,get_board_info)`, then
  `finalize`.
- Claude CLI Branch C attempts:
  `runs/wave1-final-branch-c-nucleo-claude.log` and
  `runs/wave1-final-branch-c-nrf52840-claude.log` both passed hardware
  preconditions and hardware-only checks, then skipped/fail provider rows
  because `claude-cli` reported `Not logged in - Please run /login`.
- Official `nrf52833dk` Branch C attempt:
  `runs/wave1-final-branch-c-nrf52833-codex.log` passed deterministic checks,
  probe visibility, and Codex provider dry-run; it failed Stage 0 preconditions
  because exact official-board proof requires explicit destructive
  recover/reference-firmware Stage 0 inputs.
- Process hygiene:
  baseline `runs/wave1-final-deployment-process-baseline.json` and after
  snapshot `runs/wave1-final-deployment-process-after.json` show no new matching
  long-lived `branch_c_tests`, provider, pytest, pyright, ruff, mypy, or
  harness process left behind by this audit pass beyond pre-existing Codex app
  and MCP server processes.
- `git diff --check` passed on the final tree with line-ending warnings only.

## Pending verification

- Claude CLI after local login.
- API providers with credentials.
- Exact official `nrf52833dk` destructive Stage 0 proof.
- Fresh-machine proof.
