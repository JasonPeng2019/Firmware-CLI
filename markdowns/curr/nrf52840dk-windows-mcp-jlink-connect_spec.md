> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# nrf52840dk windows mcp jlink connect

## Goal in plain English

Task: Fix Windows MCP J-Link implicit connect on nrf52840dk while preserving the no-subprocess-poison constraint
Roadmap anchor: `R12` / Wave 0 runtime hardening

## Scope and non-scope

In scope:
- reproduce the failure on the attached `nrf52840dk`
- identify whether the bug is in shared substrate, MCP stdio wrapping, or
  Windows J-Link connect policy
- implement the smallest correct fix in the probe-resolution/connect path
- add regression tests and rerun live MCP validation on the attached board

Out of scope:
- unrelated branch/doc reconciliation beyond the facts this bug changes
- broad changes to the SWD adapter that are not needed for this Windows
  implicit-connect failure

## Reconciliation summary

- Build plan:
  - shared board-control logic and probe quirks stay centralized in the shared
    service path
  - Windows/macOS portability must be preserved
- Current code:
  - Stage 0 and Stage 1 on `nrf52840dk` are green on this host
  - MCP stdio `connect(board_id=\"nrf52840dk\")` fails when no explicit J-Link
    UID is passed
  - MCP stdio `connect(board_id=\"nrf52840dk\", unique_id=\"683377322\")`
    succeeds on the same host and board
- Other docs or notes:
  - `current-progress.md` currently overstates the Windows J-Link rule as
    “always pass unique_id=None”
- Disagreements:
  - the broad Windows J-Link bypass fixed one class of issue but regressed
    `nrf52840dk` MCP attach on this host
  - the real bad path is the subprocess fallback behind probe resolution, not
    API-derived UID resolution itself

## Design

Keep the Windows no-subprocess-poison rule, but narrow it:

- for implicit Windows J-Link connect, resolve probes through the pyOCD Python
  API path only
- if that yields a UID, use the UID
- if that yields nothing, fall back to `unique_id=None`
- never pre-run the subprocess probe-list path for this case

This preserves the original protection while restoring working MCP attach for
boards like `nrf52840dk`.

## Board-facts-as-data and origin tags

- no board facts move into code branches
- the policy remains keyed on tracked probe family plus host platform, not on
  ad hoc user-machine values

## Documentation plan

- correct the over-broad Windows J-Link statement in `current-progress.md`

## Portability

- keep existing API-first probe enumeration on every platform
- make the Windows special-case narrower, not broader

## Verification plan

- targeted repro:
  - Stage 0 on `nrf52840dk`
  - Stage 1 smoke on `nrf52840dk`
  - MCP stdio `connect(board_id=\"nrf52840dk\")` before and after the fix
- regression tests for:
  - API-only no-subprocess fallback in probe inventory
  - Windows J-Link implicit connect using API-derived UID
  - Windows J-Link implicit connect returning `None` only when API resolution is empty
- non-hardware ladder:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`

## Acceptance criteria

- Stage 0 and Stage 1 remain green on `nrf52840dk`
- MCP stdio `connect(board_id=\"nrf52840dk\")` succeeds without an explicit UID
- the Windows no-subprocess-poison rule remains true
- regression tests cover the narrower policy

## Verified

- hardware repro exists and is stable:
  - `stage0_check.py` passes on `nrf52840dk`
  - `stage1_smoke.py` passes on `nrf52840dk`
  - MCP stdio connect fails only when the Windows implicit-connect path drops
    the UID
  - MCP stdio connect succeeds immediately when the same board is given the
    explicit J-Link UID `683377322`
- root cause is now confirmed:
  - the broad Windows J-Link “always use `unique_id=None`” rule was too coarse
  - the real unsafe path was the subprocess probe-list fallback, not the pyOCD
    API probe enumeration path
- targeted regression tests are green
- default non-hardware ladder is green
- live MCP validation is green on the attached `nrf52840dk` with implicit
  `connect(board_id="nrf52840dk")`:
  - `connect`
  - `get_board_info`
  - `read_memory(0x10000100)`
  - `reset(halt_after=False)`
  - `read_serial(expected_text="boot ok", reset_on_open=True)`
  - `disconnect`

## Pending verification

- none for the bug's intended scope
