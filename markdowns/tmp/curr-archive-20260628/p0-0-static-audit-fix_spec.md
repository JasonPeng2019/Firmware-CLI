> STATUS: IN PROGRESS - authority for the current P0.0 static audit / fix pass.

# P0.0 Static Audit Fix

## Goal in plain English

Task: Static audit and timeout hardening fixes before layered validation.

This pass is the "fix what we can prove from code inspection" gate before the
full layered validation plan. The target is not new prototype functionality. The
target is to remove code paths that can leak a child/session, accept obviously
bad loop budgets, or misstate current repo truth before we spend bench time on
real hardware validation.

Roadmap anchor: `R12` Wave 0 / `P0.0` clean-slate reproof.

## Scope and non-scope

In scope:

- static audit of current client/server/brain timeout and startup paths
- fix any concrete code-level bug found by inspection that is small,
  high-confidence, and regression-testable now
- add regression tests for each landed fix
- sync touched documentation when the current docs are materially stale
- run targeted non-hardware checks plus targeted live checks on the currently
  connected `nrf52840dk`

Out of scope:

- implementing the deferred prototype redesign items from `things-to-change.md`
- second-provider proof
- fresh-machine portability proof
- large architecture rewrites
- speculative hardware changes without a concrete failing signal

## Reconciliation summary

- Build plan:
  - the build plan requires bounded waits, clean substrate behavior, and shared
    service correctness before higher-level orchestration work
  - this pass is aligned with that requirement: fix substrate/runtime hygiene
    first, then validate
- Current code:
  - timeout hardening already exists in many places, but one startup-failure
    cleanup path is still unsafe
  - turnkey invocation values still accept invalid iteration/read budgets and
    only fail later, deeper in the loop
  - `README.md` still describes older `R12` closure status and stale `curr/`
    doc links
- Other docs or notes:
  - `current-progress.md`, `ROADMAP.md`, and `p0_0_layered_validation_plan.md`
    already reflect the narrowed Wave 0 / prototype boundary
- Disagreements:
  - `README.md` is currently behind the rest of repo status and must be brought
    back into sync as part of this unit

## Static findings being fixed in this pass

### Finding 1 - MCP startup failure can leak a partially opened child/session

Code path:

- `src/pyocd_debug_mcp/brain/mcp_client.py`

Problem:

- `StdioToolClient.__aenter__()` opens the stdio manager, creates the MCP
  session, and calls `session.initialize()`
- if any step after the child process starts throws a non-timeout exception,
  cleanup is not guaranteed
- `LocalMCPClient.start()` only forces cleanup on `TimeoutError`, not on other
  startup failures such as `initialize()` failure or `list_tool_names()` failure

Why it matters:

- this directly violates the "do not keep listening after an error" requirement
- it is exactly the kind of startup bug that can leave a transport or child
  process alive after the client has already failed

Fix shape:

- make `StdioToolClient.__aenter__()` exception-safe
- broaden `LocalMCPClient.start()` cleanup to all startup exceptions, not only
  timeout exceptions
- keep cleanup idempotent

### Finding 2 - turnkey loop budgets accept invalid values and fail too late

Code path:

- `src/pyocd_debug_mcp/brain/config.py`
- `src/pyocd_debug_mcp/brain/cli.py`
- benchmark entry points that reuse `build_turnkey_invocation(...)`

Problem:

- `max_iters` is accepted as any integer
- `serial_read_seconds` is accepted as any float
- `max_iters <= 0` currently falls through into a runtime "max-iters reached"
  style outcome instead of a user-facing config error
- `serial_read_seconds <= 0` can produce nonsensical loop/read behavior instead
  of failing at the boundary

Why it matters:

- invalid runtime budgets should fail immediately and deterministically
- this is portable and board-agnostic; it should not depend on live hardware to
  discover

Fix shape:

- validate both values centrally in `build_turnkey_invocation(...)`
- raise `BrainConfigError` with clear user-facing messages
- let both CLI modes inherit the same validation through the shared builder

### Finding 3 - repo status doc drift in `README.md`

Code path:

- `README.md`

Problem:

- stale links still point at removed `curr/` docs
- top-level status text still says `R12` is open only because second-provider
  proof is red, which no longer matches the narrowed prototype/Wave 0 boundary

Why it matters:

- the test-suite workflow requires the docs that define the current surface to
  agree with one another
- stale repo status causes validation and hand-off confusion

Fix shape:

- update only the sections touched by this audit:
  - current status text
  - docs list
  - `curr/` / `tmp/` references
  - verification wording where it is now outdated

## Design

Principles for this pass:

- fix the smallest correct layer
- add a regression guard for each real bug
- avoid speculative rewrites
- keep the runtime boundary deterministic: bad startup and bad config should
  stop cleanly, not drift into later behavior

## Board-facts-as-data and origin tags

No board schema change in this pass.

Any hardware validation added here must stay board-portable:

- use `board_id`-driven paths
- do not hardcode probe UID or serial port
- keep commands portable across the existing tracked boards and host OSes even
  if only the `nrf52840dk` is physically present for this pass

## Documentation plan

- update this spec with the audit scope and verification matrix
- sync `README.md` if the landed fixes change current repo truth
- do not rewrite roadmap/architecture docs unless the code change actually
  invalidates them

## Portability

This pass must stay portable by construction:

- startup cleanup tests use fakes, not OS-specific process assumptions
- invocation validation tests are pure Python
- hardware commands must use the existing CLI/server entrypoints with `board_id`
  and no hard-coded Windows-only probe/port values
- the live bench check on `nrf52840dk` is evidence for the current host+board,
  not a claim that STM32, Claude, or fresh-machine portability is complete

## Verification plan

Define the test matrix before running anything.

### Non-hardware regression matrix

| Surface | Check | Success result | Failure result |
|---|---|---|---|
| MCP startup cleanup | new unit test: startup `list_tool_names()` failure calls transport cleanup | test observes `__aexit__` called and `available_tools == ()` | failure leaks the fake transport or leaves tools populated |
| MCP startup cleanup | new unit test: `StdioToolClient.__aenter__()` cleans up manager/session on `initialize()` failure | test observes both session and stdio manager exited | failure leaves either resource open |
| Turnkey budget validation | new unit test: `build_turnkey_invocation(max_iters=0)` raises `BrainConfigError` | explicit config error | invalid invocation is accepted |
| Turnkey budget validation | new unit test: `build_turnkey_invocation(serial_read_seconds=0)` raises `BrainConfigError` | explicit config error | invalid invocation is accepted |
| Doc sync | targeted grep / readback on `README.md` links and status text | stale `curr/` links removed and status wording matches current docs | stale links/status remain |

### Validation ladder to run after patching

1. targeted pytest for the new regression tests
2. broader turnkey/server test files that cover the touched surfaces
3. repo check ladder preset for default hygiene
4. targeted live client/server smoke checks on `nrf52840dk`

### Live hardware check matrix for this pass

| Surface | Command family | Success result | Failure result |
|---|---|---|---|
| Server startup | start local MCP server / local brain client on the connected board | server starts, `connect(board_id=...)` works, clean disconnect | startup/connect fails or hangs |
| Timeout-hardened connect path | turnkey or direct MCP `connect` using `board_id=nrf52840dk` | returns promptly with session id, no leaked session on failure | hang, repeated waiting, or bad cleanup |
| UART/read path touched by validation budgets | direct `read_serial` or turnkey verify-style read with bounded duration | returns within expected bound with text or deterministic miss | unbounded wait, stuck transport, or orphaned session |

## Acceptance criteria

- startup failure cleanup is exception-safe for both timeout and non-timeout
  startup failures
- live MCP tool timeouts now report cleanly without crashing client teardown
- invalid turnkey iteration/read budgets are rejected before the loop starts
- raw MCP server inputs now reject invalid UART durations/baudrates and invalid
  memory word sizes/block lengths deterministically
- mixed-board Windows probe selection now resolves the correct Nordic J-Link
  even when the STM32 ST-Link is attached at the same time
- new regression tests cover the landed fixes
- touched docs no longer contradict current repo truth
- the targeted non-hardware suite is green
- the targeted `nrf52840dk` live checks either pass or produce a concrete,
  portable bug report with the exact failing command
- dual-board reference flash + UART verification is green on the attached
  `nrf52840dk` and `nucleo_l476rg`

## Verified

- static inspection confirms Finding 1 and Finding 2 are real code issues, not
  hypothetical style concerns
- static inspection confirms `README.md` currently lags `current-progress.md`
  and the newer Wave 0 / P0.0 docs
- targeted regression checks are green:
  - `uv run pytest tests/test_r12_turnkey_merge.py -q`
  - `uv run pytest tests/test_r12_turnkey.py -q`
- full non-hardware ladder is green on the final patch set:
  - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default --command "uv run pytest tests/test_server_import.py tests/test_server_runtime_tools.py tests/test_probe_inventory.py tests/test_uart_capture.py -q"`
  - result: `pytest -q` green, `ruff check .` green, `mypy src` green, targeted server/runtime tests green
- live `nrf52840dk` smoke is green for the touched runtime surface:
  - local MCP startup now succeeds through `LocalMCPClient.start()`
  - direct stdio client path can list tools cleanly
  - `connect(board_id='nrf52840dk')` succeeded with auto probe selection
  - `get_board_info` returned the expected tracked board facts
  - `read_serial(read_seconds=1.0)` returned promptly with `boot ok`
  - clean shutdown completed after the live run
- CLI boundary validation now rejects invalid iteration budgets immediately:
  - `uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52840dk --task "verify" --max-iters 0`
  - observed output: `max_iters must be > 0.`
- mixed-board Windows selection bug was reproduced and fixed:
  - with both `nrf52840dk` and `nucleo_l476rg` attached, Nordic connect now
    resolves probe UID `683377322` instead of falling through to the ST-Link
- full dual-board live proof is now green:
  - `nrf52840dk`
    - timeout repro returns clean `MCPClientError`
    - reconnect after timeout succeeds
    - default reference flash succeeds
    - UART returns `boot ok`
    - invalid `read_seconds=-1.0` is refused
  - `nucleo_l476rg`
    - timeout repro returns clean `MCPClientError`
    - reconnect after timeout succeeds
    - default reference flash succeeds
    - UART returns `boot ok`
    - invalid `read_seconds=-1.0` is refused

## Pending verification

- second-provider live proof
- fresh-machine portability proof
