# P-Wave A/B/C Merge Validation Review

## Decision

Current result: accept the Wave 1 A/B/C merge-back candidate for the attached
board/provider prototype boundary.

Branch A provider/session/schema behavior, Branch B batch/wait/UART/client
action behavior, and Branch C event/timeout/server-sync behavior all ran
together in the current `P-Wave-A` worktree.

## Findings

- No remaining merge-blocking functional failures were found after the harness
  fix.
- One real acceptance-harness bug was found and fixed: the Branch C live
  provider check treated Codex as not reaching hardware when Codex actually
  connected and read board info after recovering from an unsupported batched
  `finalize`. The harness now accepts `TurnkeyRunResult.mcp_tools_used` as
  governed hardware-touch evidence, with a focused regression test.
- No spawned provider/MCP/pyOCD/Python child processes remained after the live
  smokes. The only matching long-lived process was the pre-existing VS Code
  Codex app-server.

## Proof Boundary

Verified in this pass:

- full pytest: `338 passed`
- ruff check/fix and format: passed
- mypy over `src`: passed
- changed-file Pyright filter: `0` diagnostics
- Branch C live provider/hardware harness on `nucleo_l476rg + nrf52840dk`
  with `codex-cli` and `claude-cli`
- explicit two-turn deployed CLI smokes on the same board/provider matrix

Not claimed:

- exact official `nrf52833dk` proof
- API-provider parity
- fresh Windows/macOS host deployment proof
- killable pyOCD/vendor-worker cancellation
