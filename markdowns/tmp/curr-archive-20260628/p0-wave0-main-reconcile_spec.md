> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# p0 wave0 main reconcile

## Goal in plain English

Task: Close the useful main-to-P-Wave-0 runtime gap and revalidate against real MCP clients and attached boards
Roadmap anchor: `R12` prototype Wave 0 / `P0`

## Scope and non-scope

In scope:
- reconcile the remaining runtime-relevant `main` deltas against the stronger
  `P-Wave-0` baseline
- port only the useful `main` behavior that `P-Wave-0` still lacks
- preserve the stricter Wave 0 timeout and argument-validation hardening
- update tests to prove the merged behavior
- rerun the non-hardware ladder plus targeted real MCP client/server checks on
  the attached boards

Out of scope:
- broad doc reshuffles from `main` that do not change runtime truth
- replacing stronger `P-Wave-0` hardening with weaker `main` behavior
- reopening the Wave 0 scope beyond this reconcile pass

## Reconciliation summary

- Build plan:
  - shared services own probe/serial/runtime behavior
  - verify-don't-claim and bounded failure behavior are mandatory
  - the turnkey and UX layers must stay portable across Windows and macOS
- Current code:
  - `P-Wave-0` already contains stronger timeout, argument-validation, and test
    hardening than `main`
  - `P-Wave-0` still lacks two useful runtime behaviors that exist on `main`:
    Windows implicit J-Link connect bypass in `server.py`, and prompt-toolkit
    no-console fallback in `ux/shell.py`
- Other docs or notes:
  - `markdowns/current-progress.md` already claims the Windows implicit J-Link
    bypass exists in the shared path
- Disagreements:
  - doc drift: `current-progress.md` describes the Windows J-Link bypass, but
    the current `P-Wave-0` code does not implement it yet
  - `main` also carries weaker server-side argument validation in the same file;
    that behavior conflicts with Wave 0 hardening and must not be imported

## Design

Port the two useful `main` behaviors as small, local changes:

1. In `server.py`, skip pre-resolving an implicit J-Link UID on Windows and let
   the shared backend choose the single attached probe unless the operator
   explicitly supplied a UID.
2. In `ux/shell.py`, catch the prompt-toolkit no-console screen-buffer failure
   and retry with `DummyOutput()` so the operator shell still starts on
   Windows hosts without a real console.

Do not import the unrelated `main` regressions that removed server argument
refusals for invalid memory widths and UART read settings.

## Board-facts-as-data and origin tags

- no board facts move into code branches
- the Windows J-Link bypass keys only on the tracked `probe_family=jlink` plus
  host platform, which is consistent with the shared probe-routing contract
- no new project-defined constants are introduced

## Documentation plan

- keep this spec and the process ledger current during the reconcile pass
- leave the existing authoritative repo docs in place unless the code/docs
  mismatch persists after the fix

## Portability

- validate the Windows-specific behavior through unit tests and preserve the
  existing cross-platform fallback behavior elsewhere
- validate the shell fallback without requiring a real Windows console by
  mocking the prompt-toolkit constructor failure

## Verification plan

- targeted unit tests for:
  - Windows implicit J-Link bypass in `server.py`
  - Windows connect path passing `unique_id=None` through to the backend
  - no-console prompt-toolkit fallback in `ux/shell.py`
- non-hardware ladder:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`
- real MCP validation on attached boards using stdio client/server flows and
  board-scoped smoke commands

## Acceptance criteria

- `P-Wave-0` contains the useful runtime behavior from `main` that it was still
  missing
- the stronger Wave 0 validation/refusal behavior remains intact
- tests cover the imported behavior and stay green
- real MCP client/server validation still passes on the attached boards

## Verified

- branch reconciliation identified only two useful runtime deltas from `main`:
  the Windows implicit J-Link bypass and the prompt-toolkit no-console fallback
- `current-progress.md` already documents the J-Link bypass, so this pass also
  closes a real code/doc mismatch if the code is updated accordingly
- during live MCP validation on the attached Windows host, the STM32 stdio path
  is green and the attached Nordic board is positively identified as
  `nrf52840dk`

## Pending verification

- whether the attached Nordic board's current J-Link/target-access failure is a
  transient bench-state issue or a persistent external hardware condition
