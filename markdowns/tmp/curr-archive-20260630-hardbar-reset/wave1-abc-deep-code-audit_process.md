# Process ledger for wave1-abc-deep-code-audit

## Goal and roadmap anchor

Task: Deep adversarial audit for Wave 1 A/B/C combined product quality after
Pyright cleanup.

Roadmap anchor: Wave 1 / R12 A+B+C merge-back validation, with cleanup guard
behavior linked to Wave 2 Branch H for the broader process-tree work.

## Done

- Re-read the required workflow skills, Claude workflow mirrors, and
  superpowers authority docs before editing.
- Ran adversarial searches for subprocess calls without explicit timeouts,
  direct pyOCD `ConnectHelper` usage outside the shared backend/inventory,
  broad exception handling and hidden pass paths, production `type: ignore` /
  `Any` typing escapes, hardcoded serial ports/host paths/OS assumptions,
  unbounded sleeps/loops, and file deletion/write surfaces.
- Manually reviewed the hits. Most were valid existing seams, tests, examples,
  or already-documented Wave 2 cleanup work. One Wave 1 product bug was valid:
  final `run_turnkey` disconnect cleanup failures were swallowed, so a run could
  look final while a known active board session failed to close.
- Created `markdowns/curr/wave1-turnkey-cleanup-failure_spec.md`.
- Fixed `src/pyocd_debug_mcp/brain/loop.py` so final disconnect cleanup failure
  records an `unexpected_failure` event with phase `final_disconnect`, keeps the
  active `session_id` visible in state, and replaces the run result with
  `blocked` / `tooling_failure`.
- Added
  `tests/test_r12_turnkey.py::test_run_turnkey_blocks_when_final_disconnect_cleanup_fails`.
- Reviewed the scoped fix in
  `markdowns/curr/wave1-turnkey-cleanup-failure_review.md`; verdict `CLEAN`.
- Confirmed the broader process-tree / provider child cleanup guard remains
  Wave 2 Branch H, not an unfinished Wave 1 requirement.

## In progress

Done for the agent-verifiable Wave 1 surface.

## TODO

None for the valid Wave 1 bug found in this audit.

## Limitations and known gaps

- This pass did not implement killable pyOCD/vendor workers or full
  provenance-based child-process tree reaping. That larger deployment hygiene
  layer is already tracked in `markdowns/curr/things-to-change.md` and
  `markdowns/R12_P_SPLIT.md` as Wave 2 Branch H.
- The attached Nordic board is `nrf52840dk`, not the official `nrf52833dk`.
  Official-pair proof remains pending until the correct board is attached.
- The live deployment smokes intentionally did not flash or run real code-repair
  build/green checks in this pass; those heavier repair cases have historical
  Branch A/B evidence, while this audit focused on the current A/B/C code after
  the Pyright cleanup and cleanup-failure fix.

## Hardware hand-off

- For official-pair closure, rerun the same Branch C harness and public CLI
  smoke matrix on an actual `nrf52833dk` plus `nucleo_l476rg`.
- For Wave 2 Branch H, add forced-hang process-tree and board-session cleanup
  tests once the killable worker/provenance layer exists.

## Open decisions and surfaced issues

- No new settled-decision conflict surfaced.
- The only valid product issue found was the final disconnect cleanup failure
  visibility bug, now fixed.
- Broader child-process cleanup remains a known future feature, not a Wave 1
  merge blocker.

## Verified

- Targeted regression:
  `uv run pytest -q tests/test_r12_turnkey.py -k "disconnect_cleanup_fails or invocation_default_timeout_for_disconnect"`
  -> `2 passed, 54 deselected`.
- Full Pyright after the new test: `uv run pyright --outputjson` -> 105 files,
  0 diagnostics.
- Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`
  -> ruff check/fix passed, ruff format passed, full Pyright passed, full
  pytest -> `340 passed`.
- FirmCLI suite ladder:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> `340` pytest tests, ruff, mypy over 68 source files, `34` R11 benchmark
  tests, and R11 benchmark help all passed.
- Live Branch C provider/hardware harness on `nucleo_l476rg`:
  `uv run python tests\harness\branch_c_tests.py --board-id nucleo_l476rg --provider codex-cli --provider claude-cli --provider-timeout-seconds 120 --fail-on-skip`
  -> `11 passed, 0 failed, 0 skipped`; run roots
  `runs/20260630T052616Z-4b553e39` and
  `runs/20260630T052655Z-4e591717`.
- Live Branch C provider/hardware harness on `nrf52840dk`:
  `uv run python tests\harness\branch_c_tests.py --board-id nrf52840dk --provider codex-cli --provider claude-cli --provider-timeout-seconds 120 --fail-on-skip`
  -> `11 passed, 0 failed, 0 skipped`; run roots
  `runs/20260630T052843Z-057bd52a` and
  `runs/20260630T052926Z-bb4b66b1`.
- Public deployed CLI two-turn smokes passed by artifact semantics on both
  attached boards and both providers. Each run used turn 1
  `action_batch(connect,get_board_info)` and turn 2 `finalize`; `mcp_tools_used`
  recorded `connect,get_board_info`:
  - `runs/20260630T053014Z-2630df0f` (`nucleo_l476rg` + `codex-cli`)
  - `runs/20260630T053042Z-4a16f434` (`nucleo_l476rg` + `claude-cli`)
  - `runs/20260630T053111Z-eb3e6ce0` (`nrf52840dk` + `codex-cli`)
  - `runs/20260630T053139Z-7449c301` (`nrf52840dk` + `claude-cli`)
- Process audits before/after the Python gate, suite ladder, live harnesses,
  and public CLI smokes showed no new leftover spawned provider/MCP/pyOCD or
  validation children. The only matching long-lived tree was pre-existing:
  VS Code/Codex app-server-owned `codex`, `uv`, `pyocd-debug-mcp`, and Python
  children.
- Repeat adversarial search after the fix found no further valid Wave 1 issues:
  direct `ConnectHelper` use is confined to shared probe inventory / pyOCD
  adapter code, remaining `pass` hits are close-failure suppression or tests,
  and the final no-timeout/silent-cleanup search had no matches.

## Pending verification

- Official `nrf52833dk` current-branch proof.
- API-provider parity and fresh-host proof.
- Future Wave 2 Branch H forced-hang child-process cleanup proof.
