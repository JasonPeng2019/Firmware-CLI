# Process ledger for wave1-r12-adversarial-audit-rerun

## Goal and roadmap anchor

Task: Run an adversarial audit loop over the R12 context-scaffold hardening
implementation and the current Wave 1 A/B/C product slice.
Roadmap anchor: R12 Wave 1 A/B/C plus scaffold-hardening before Wave 2 Module G.

## Done

- Loaded the named workflow skills:
  - `firmcli-write-process`
  - `firmcli-test-suite`
  - `firmcli-spec-loop`
  - `firmcli-fix-bug`
  - `firmcli-workflow-core`
  - `firmcli-specs`
  - `firmcli-build`
  - `firmcli-review`
  - `python-change`
- Re-read the authority/product docs needed for this audit:
  - `README.md`
  - `markdowns/ROADMAP.md`
  - `markdowns/current-progress.md`
  - `markdowns/R12_P_SPLIT.md`
  - `markdowns/things-to-change.md`
  - `markdowns/curr/r12_turnkey_spec.md`
  - `markdowns/curr/r12-context-scaffold-hardening_spec.md`
  - `markdowns/curr/next-codex-handoff-20260630.md`
  - previous Wave 1 adversarial audit spec/review/process artifacts.
- Audited the current implementation against the loaded-detail guardrail and
  Wave 1 product boundary.
- Found two valid fixable gaps:
  - inner server-tool calls from governed client-action scripts can bypass the
    inner tool's loaded-detail flag;
  - successful finalize turns leave stale `last_action_summary`/memory action
    summaries.
- Found a third valid product-context gap during live benchmark artifact review:
  proactive `load_tool_details(["run_green_check"])` was treated as an
  `unknown_tool`, even though the prompt asks providers to load brain-owned
  compound-action details before use.
- Created `markdowns/curr/wave1-r12-adversarial-audit-rerun_spec.md` with the
  full audit plan, important files/features/docs, findings, reviewed no-merit
  criticisms, verification plan, and acceptance criteria.
- Fixed the inner client-action server-tool guard in `loop.py`:
  - the injected `server.call_tool(...)` path now enforces the inner MCP tool's
    loaded-detail flag before calling `_execute_server_tool`;
  - missing inner details auto-load focused tool details, record
    `details_required`, and require a fresh provider decision.
- Fixed successful finalization artifact state:
  - `state.last_action_summary` becomes `finalize(<status>)`;
  - final-turn memory records now summarize finalization instead of the
    previous action.
- Fixed proactive compound-action detail loading:
  - `load_tool_details(["run_green_check"])` now loads the `run_green_check`
    contract into `loaded_compound_action_details`.
- Added focused regressions in `tests/test_r12_turnkey.py` for all three gaps.
- Ran focused tests:
  - inner tool/finalize subset -> `4 passed` before the third finding;
  - final focused subset after all fixes -> `3 passed`;
  - broader scaffold set -> `96 passed`.
- Ran Python-change gate after all fixes:
  Ruff pass, Ruff format pass, Pyright `0`, full pytest `357 passed`.
- Ran FirmCLI suite preset after all fixes:
  all rows passed; report at
  `runs/wave1-r12-adversarial-audit-rerun-suite-report-final.txt`.
- Ran real stdio MCP smoke:
  `21` live tools, `13` curated entries, focused details loaded for
  `connect`, `write_serial`, `read_serial`.
- Ran real Codex no-hardware multi-turn smokes:
  - `runs/turnkey-20260630T175222Z-3d3d5875`
  - `runs/turnkey-20260630T175315Z-4bfd53d1`
  - `runs/turnkey-20260630T180611Z-7d401cde`
- Attempted Claude CLI provider row; blocked by `Not logged in - Please run
  /login`.
- Checked API-provider environment; both `OPENAI_API_KEY` and
  `ANTHROPIC_API_KEY` were missing.
- Ran real attached-board Stage 1 smokes after final code changes:
  `nucleo_l476rg` and `nrf52840dk` both passed flash/PC/symbol/UART.
- Ran real Branch C provider/hardware harnesses with Codex CLI before the final
  compound-detail polish:
  - `nucleo_l476rg`: `9 passed`, `runs/20260630T175615Z-7e6be5fd`
  - `nrf52840dk`: `9 passed`, `runs/20260630T175817Z-f3358d8f`
- Ran real known-good R12 benchmark rows with Codex CLI before the final
  compound-detail polish:
  - `nucleo_l476rg__k001_reference_green` -> `FULL_SUCCESS`,
    `20260630T175943Z-048a784d`
  - `nrf52840dk__k001_reference_green` -> `FULL_SUCCESS`,
    `20260630T180133Z-f1e6f315`
- Repeated the adversarial audit after fixes:
  - governed client scripts no longer bypass inner tool-detail flags;
  - finalization state/memory no longer uses stale previous-action summaries;
  - proactive `run_green_check` detail loading no longer fails as unknown;
  - removed governed host actions remain absent;
  - compact MCP index remains compact and focused full details are on-demand;
  - remaining criticisms are external proof gaps or future Wave 2 scope.

## In progress

- None.

## TODO

- None for the agent-verifiable local scope.

## Limitations and known gaps

- Exact official `nrf52833dk` proof depends on attaching a physical board whose
  silicon identity is `0x52833`; this checkout currently has an attached Nordic
  alternate identified earlier as `nrf52840`.
- Claude CLI and API-provider rows depend on local auth/credentials. They must
  be attempted only if available and otherwise recorded as blocked.

## Verified

- Audit plan/spec created.
- Focused regressions green.
- Python-change gate green with Pyright `0`.
- FirmCLI suite preset green.
- Live MCP, Codex provider, and attached-board checks completed as recorded
  above.

## Pending verification

- Exact official `nrf52833dk` physical-board proof.
- Claude CLI rows after login.
- API provider rows after credentials/model selection.
- Fresh-machine deployment proof.
