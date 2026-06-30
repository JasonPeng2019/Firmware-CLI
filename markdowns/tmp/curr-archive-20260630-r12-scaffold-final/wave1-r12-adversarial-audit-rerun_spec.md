> STATUS: ACTIVE HARD BAR - adversarial audit rerun for the R12
> context-scaffold hardening changes and the current Wave 1 product slice.

# wave1 r12 adversarial audit rerun

## Goal in plain English

Task: Audit the newly implemented R12 detail-loading/context scaffold and the
entire current Wave 1 A/B/C product slice, then fix only valid code/product
gaps and rerun the deployment-grade suite as far as this host can truthfully
prove it.
Roadmap anchor: R12 Wave 1 A/B/C plus the scaffold-hardening prerequisite for
Wave 2 Module G.

## Adversarial audit plan

Important code files to inspect:

- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/action_policy.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/tool_schemas.py`
- `src/pyocd_debug_mcp/brain/model_native_skills.py`
- `src/pyocd_debug_mcp/brain/client_actions.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_parsing.py`
- `src/pyocd_debug_mcp/brain/mcp_client.py`
- `src/pyocd_debug_mcp/server.py`
- `src/pyocd_debug_mcp/ux/`
- `tests/test_r12_turnkey.py`
- `tests/test_model_native_skills.py`
- `tests/test_p0_foundation.py`
- `tests/test_r12_turnkey_merge.py`
- `tests/test_branch_c_harness.py`
- `tests/harness/branch_c_tests.py`

Important product features to inspect:

- Compact governed-tool index remains discovery-only and omits full schemas on
  ordinary turns.
- `load_tool_details` loads focused full schemas and records brain-owned
  loaded-detail flags.
- Missing-detail calls for governed MCP tools, governed client actions, and
  `run_green_check` fail closed, auto-load details, and require a fresh
  provider decision.
- Governed client-action scripts route server calls back through the same brain
  gate as direct tool actions.
- Invalid governed-tool arguments auto-load focused details for retry context.
- Model-native skills load from a product/client root, copy to runtime before
  init/context, expose structured failures, and never mutate installed sources.
- Removed host actions remain absent from action schemas, parsing, executor
  branches, and prompt-visible governed decisions.
- Provider session/memory artifacts accurately describe each turn, including
  finalization.
- Wave 1 A/B/C behavior still respects provider continuity, action boundary,
  event/timeout behavior, and public CLI/operator-shell contracts.
- Hardware/provider proof claims stay honest about this host's attached boards,
  Claude login state, API credentials, and exact official-board availability.

Markdown/product guidance to refer to:

- `markdowns/firmware_agent_build_plan_concrete (10).md`
- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/ROADMAP.md`
- `markdowns/current-progress.md`
- `markdowns/curr/r12_turnkey_spec.md`
- `markdowns/curr/r12-context-scaffold-hardening_spec.md`
- `markdowns/curr/wave2-codebase-map_spec.md`
- `markdowns/curr/next-codex-handoff-20260630.md`
- `markdowns/tmp/curr-archive-20260630-wave1-final/wave1-adversarial-audit-20260630_spec.md`
- `markdowns/tmp/curr-archive-20260630-wave1-final/wave1-adversarial-audit-20260630_review.md`

## Audit findings

### Finding 1 - valid high severity

`run_script` detail loading guards only the client-action object itself. Once
the script detail is loaded, the injected `server.call_tool(...)` path calls
`_execute_server_tool` directly and can execute an inner governed MCP tool whose
own loaded-detail flag is still false. That violates the scaffold-hardening
contract that governed tools and governed tool-scripts require brain-owned
loaded-detail flags before execution.

Concrete fix: pass the tool-schema bundle into the client-action execution path
and enforce the same missing-detail block inside the injected server API. If a
script asks for an inner tool without loaded details, auto-load that tool detail,
raise a structured details-required block, record it, and require a fresh
provider decision. Add a focused regression that proves `write_serial` is not
called until its own detail was loaded.

### Finding 2 - valid medium severity

Successful `finalize` produces a run result, but state and provider-memory
records can keep the previous `last_action_summary`. After detail-loading
turns, artifacts can misleadingly say the last action was
`load_tool_details(...)` even though the turn was `finalize`. This is not a
hardware safety bug, but it weakens the run artifacts and memory ledger the
product depends on.

Concrete fix: update state on successful finalize before recording the final
event and before committing provider memory. Add a regression that final-state
and final-turn memory both summarize `finalize`.

### Finding 3 - valid medium severity

The prompt tells the provider to load details before using brain-owned compound
actions, but `load_tool_details(tool_names=["run_green_check"])` originally
treated `run_green_check` as an unknown MCP tool. A live benchmark provider did
exactly that, received an `unknown_tool` failure, then had to trigger a later
first-use block to load the same contract. The final benchmark still passed, but
the product guidance and context-loading surface were inconsistent.

Concrete fix: allow `load_tool_details` to load the `run_green_check`
compound-action contract when that name is requested. Keep true unknown names
as structured failures. Add a regression and a live Codex no-hardware smoke for
proactive `run_green_check` detail loading.

### Reviewed as no merit or not actionable

- The absence of `skills/model_native/` packages in this checkout is not by
  itself a bug for this hardening pass. The spec allows the prototype to return
  a structured missing-skill result if no product skills are installed.
- The compact index omitting full JSON schema bodies is required behavior, not
  a regression.
- Provider-native host tools remain outside the brain's sandbox by accepted
  product stance. The brain governs board/server access, context expansion,
  client scripts, waits, green checks, and finalization.
- Exact official `nrf52833dk`, Claude, API-provider, and fresh-machine proof
  gaps are real external proof gaps, not code findings that can be fixed in
  this checkout without the missing hardware/auth/credentials.

## Verification plan

- Focused regression for the valid findings:
  `uv run pytest -q tests/test_r12_turnkey.py -k "client_action or finalize"`.
- Broader focused R12 context checks:
  `uv run pytest -q tests/test_p0_foundation.py tests/test_model_native_skills.py tests/test_r12_turnkey.py`.
- Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`.
- Suite gate:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`.
- Real MCP stdio smoke with `LocalMCPClient`.
- Real Codex no-hardware multi-turn smokes for detail loading and finalization.
- Real attached-board checks on the boards present here:
  `nucleo_l476rg` and retained alternate `nrf52840dk`.
- Claude/API/exact official `nrf52833dk` rows are attempted only if auth,
  credentials, and hardware are actually available; otherwise record the exact
  blocker and handoff command.

## Acceptance criteria

- Client-action inner server calls cannot bypass loaded server-tool detail
  flags.
- Missing inner tool details auto-load focused details, block the current
  script turn, and require a fresh provider decision.
- Finalize turns leave state and provider-memory action summaries that say
  `finalize`, not the previous action.
- `load_tool_details(["run_green_check"])` loads the brain-owned compound
  contract without an unknown-tool failure.
- Full pytest, Ruff, Pyright, and suite preset are green after fixes.
- Live MCP/provider/hardware checks are rerun and recorded honestly, with no
  invented proof for unavailable provider/hardware rows.

## Verified

- Initial audit plan completed on 2026-06-30.
- Focused regressions:
  `uv run pytest -q tests/test_r12_turnkey.py -k "load_tool_details_can_load_green_check_contract or run_script_inner_tool_requires_loaded_details or finalize_updates_state_and_memory_action_summary"`
  -> `3 passed`.
- Broader focused scaffold set:
  `uv run pytest -q tests/test_p0_foundation.py tests/test_model_native_skills.py tests/test_r12_turnkey.py`
  -> `96 passed`.
- Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`
  -> Ruff pass, Ruff format pass, Pyright `0`, full pytest `357 passed`.
- Suite preset:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/wave1-r12-adversarial-audit-rerun-suite-report-final.txt`
  -> all rows passed.
- Real stdio MCP smoke:
  `live_tools=21`, `curated_entries=13`, loaded details for
  `connect,write_serial,read_serial`, schema hash
  `abdeec0b6c74481fe1921fef5f869b3d548b49ca7cabde9ddbc36c802acd42d3`.
- Real Codex no-hardware multi-turn smokes:
  - `runs/turnkey-20260630T175222Z-3d3d5875`: loaded `connect` details, then
    finalized without MCP calls; final memory action summary is
    `finalize(diagnosed_only)`.
  - `runs/turnkey-20260630T175315Z-4bfd53d1`: loaded `read_serial` details,
    then finalized without MCP calls.
  - `runs/turnkey-20260630T180611Z-7d401cde`: proactively loaded
    `run_green_check` details, no `unknown_tool`, then finalized without MCP
    calls.
- Real attached-board Stage 1 smokes after final code changes:
  - `nucleo_l476rg`: flash, PC, symbol `0x1234ABCD`, UART `boot ok` passed.
  - `nrf52840dk`: flash, PC, symbol `0x1234ABCD`, UART `boot ok` passed.
- Real Branch C provider/hardware harness with Codex CLI before the final
  compound-detail polish, still after the inner-tool/finalize fixes:
  - `nucleo_l476rg`: `9 passed`, run root `runs/20260630T175615Z-7e6be5fd`.
  - `nrf52840dk`: `9 passed`, run root `runs/20260630T175817Z-f3358d8f`.
- Real known-good R12 benchmark rows with Codex CLI before the final
  compound-detail polish, still after the inner-tool/finalize fixes:
  - `nucleo_l476rg__k001_reference_green` -> `FULL_SUCCESS`, session
    `20260630T175943Z-048a784d`.
  - `nrf52840dk__k001_reference_green` -> `FULL_SUCCESS`, session
    `20260630T180133Z-f1e6f315`.
- Claude CLI availability attempt:
  `uv run pyocd-debug-brain run --provider claude-cli ...` -> blocked because
  Claude returned `Not logged in - Please run /login`.
- API-provider availability: `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` were
  missing in this shell.
- Process audit after validation found no obvious suite-spawned leftover
  children. Matching long-lived `codex`, `node_repl`, and `pyocd-debug-mcp`
  process trees were owned by the Codex/VS Code app-server environment.

## Pending verification

- Exact official `nrf52833dk` proof on physical `0x52833` silicon.
- Claude CLI rows after `claude /login`.
- API-provider rows after credentials and explicit models are available.
- Fresh-machine Windows/macOS deployment proof remains outside this host.
