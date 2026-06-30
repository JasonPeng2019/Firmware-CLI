# P-Wave A/B/C Merge Validation Review

## Decision

Current result: accept the Wave 1 A/B/C merge-back candidate for the attached
board/provider prototype boundary.

Branch A provider/session/schema behavior, Branch B batch/wait/UART/client
action behavior, and Branch C event/timeout/server-sync behavior all ran
together in the current `P-Wave-A` worktree.

## Findings

- No remaining merge-blocking functional failures were found after the harness
  and cleanup fixes.
- One real acceptance-harness bug was found and fixed: the Branch C live
  provider check treated Codex as not reaching hardware when Codex actually
  connected and read board info after recovering from an unsupported batched
  `finalize`. The harness now accepts `TurnkeyRunResult.mcp_tools_used` as
  governed hardware-touch evidence, with a focused regression test.
- One real product cleanup bug was found and fixed in the later deep audit:
  final `run_turnkey` disconnect cleanup failures were swallowed. They now
  record an `unexpected_failure` event with phase `final_disconnect`, keep the
  active `session_id` visible in state, and convert the run result to
  `blocked` / `tooling_failure`.
- No spawned provider/MCP/pyOCD/Python child processes remained after the live
  smokes. The only matching long-lived process was the pre-existing VS Code
  Codex app-server.

## Proof Boundary

Verified in this pass:

- full pytest: now `340 passed` after the cleanup regression
- ruff check/fix and format: passed
- mypy over `src`: passed
- full repo-wide Pyright is now green after the June 30, 2026 baseline
  cleanup: 105 files analyzed, `0` diagnostics
- Branch C live provider/hardware harness on `nucleo_l476rg + nrf52840dk`
  with `codex-cli` and `claude-cli`
- explicit two-turn deployed CLI smokes on the same board/provider matrix
- latest live evidence after the cleanup fix:
  `runs/20260630T052616Z-4b553e39`,
  `runs/20260630T052655Z-4e591717`,
  `runs/20260630T052843Z-057bd52a`,
  `runs/20260630T052926Z-bb4b66b1`,
  `runs/20260630T053014Z-2630df0f`,
  `runs/20260630T053042Z-4a16f434`,
  `runs/20260630T053111Z-eb3e6ce0`, and
  `runs/20260630T053139Z-7449c301`

Not claimed:

- exact official `nrf52833dk` proof
- API-provider parity
- fresh Windows/macOS host deployment proof
- killable pyOCD/vendor-worker cancellation
