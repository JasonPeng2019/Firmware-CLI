# UX Layer Gap Checklist

This document is the current-state checklist for the operator-facing UX layer.

It compares `markdowns/UXLayer.md` against the shipped Pass 1 implementation.
It does **not** replace `UXLayer.md`, does **not** change the current `R12`
acceptance surface, and does **not** authorize a shell/runtime redesign.

The goal of this checklist is narrower:

- freeze what is already implemented
- freeze what is only partial
- freeze what is still missing
- freeze what is intentionally deferred to Pass 2

## Scope And Reconciliation

Current repo truth:

- the current UX shell is a real Pass 1 implementation, not a pure proposal
- the current headless and benchmark truth remains owned by
  `pyocd-debug-brain`
- the current operator shell remains additive through `pyocd-debug`
- the current shell is a per-run shell with history + rerun, not a persistent
  live-session owner

Important reconciliations:

- do **not** force true live session resume into the current shell
- do **not** add a shell-only `/disconnect` control while the shell still owns
  turnkey runs at the invocation level rather than a persistent connected
  session
- do **not** treat missing provider token streaming as a Pass 1 defect; it is
  explicit Pass 2 work

## Checklist

### Event Substrate

- Status: `implemented`
- Repo truth:
  - structured event contract exists in `brain/events.py`
  - the turnkey loop emits normalized events directly
  - run artifacts persist `runs/<session_id>/logs/brain_events.jsonl`
- Next action:
  - keep the current event model stable enough for Pass 2 streaming to target
    the same sink

### One-Shot Pretty CLI

- Status: `implemented`
- Repo truth:
  - `pyocd-debug run ...` exists
  - `pyocd-debug benchmark ...` exists
  - both reuse the shared turnkey invocation path rather than duplicating loop
    logic
- Next action:
  - preserve exit-code and automation behavior parity with
    `pyocd-debug-brain`

### REPL Shell

- Status: `implemented`
- Repo truth:
  - `pyocd-debug` with no args launches a REPL shell
  - slash commands exist for board/provider/model/run/benchmark/history/show/
    rerun/artifacts/raw/help/quit
- Next action:
  - keep the shell thin over existing turnkey invocations

### Tool Activity Rendering

- Status: `implemented`
- Repo truth:
  - tool start/complete activity is surfaced live
  - tool names and short argument summaries are rendered during runs
- Next action:
  - tighten argument-summary formatting only if noise becomes a real operator
    problem

### Evidence Summary Rendering

- Status: `implemented`
- Repo truth:
  - completed provider turns already render observation/classification and
    optional hypothesis/strategy summaries
- Next action:
  - keep the summary shape concise and stable

### Refusal / Block / Failure Rendering

- Status: `implemented`
- Repo truth:
  - refusal, block, and failure panels are visually distinct
  - the shell does not collapse policy denials into generic errors
- Next action:
  - add rerun-hint emphasis later only if live operator runs show confusion

### History / Show / Rerun

- Status: `implemented`
- Repo truth:
  - recent sessions can be listed
  - saved run summaries can be shown
  - prior requests can be rerun into a fresh session
- Important rule:
  - this is **inspect + rerun**, not true active-session resume
- Next action:
  - keep this distinction explicit in future docs and shell help text

### Artifact Discovery

- Status: `implemented`
- Repo truth:
  - artifact tables and safe previews exist
  - session bundles expose request/result/state/session/benchmark artifacts
  - shortcut commands now exist for common artifact views:
    - `/prompt`
    - `/diff`
    - `/serial`
    - `/score`
    - `/events`
- Next action:
  - add richer preview/rendering polish only if live operator use exposes a
    real discovery problem

### Non-TTY Fallback

- Status: `implemented`
- Repo truth:
  - renderer checks terminal capability and falls back to plain output rather
    than requiring live Rich status rendering
- Next action:
  - keep non-TTY behavior stable for CI and transcript capture

### Raw-Output Policy

- Status: `implemented`
- Repo truth:
  - one-shot CLI supports `--raw-output off|final|all`
  - shell supports `/raw on|off|last`
  - the REPL now defaults to summary-first output with raw turns opt-in
- Next action:
  - keep true provider streaming deferred to Pass 2

### True Provider Streaming

- Status: `deferred to Pass 2`
- Repo truth:
  - provider output becomes visible after a completed provider turn
  - token/partial-output streaming is not yet implemented
- Next action:
  - extend providers with incremental output events without changing the shell
    command surface

### Interactive Repair Context

- Status: `implemented`
- Repo truth:
  - one-shot CLI supports `--workspace-root` and `--build-command`
  - one-shot CLI supports explicit flash/symbol overrides
  - the REPL now exposes matching context-setting commands:
    - `/workspace <path|clear>`
    - `/build-command "<cmd>"|clear`
    - `/flash-artifact <path|default>`
    - `/elf <path|default>`
- Next action:
  - keep the persisted v1 context limited to workspace/build/flash/elf only

### Guided Operator Flow

- Status: `implemented`
- Repo truth:
  - the shell has generic control commands and can run freeform tasks or
    benchmarks
  - the shell now provides thin guided commands over the existing turnkey path:
    - `/verify [extra text]`
    - `/diagnose [extra text]`
    - `/repair [extra text]`
- Next action:
  - keep guided commands declarative and easy to extend without forking the
    shell execution path

## Remaining UX Backlog

These are the concrete pieces that still remain after the shipped Pass 1 shell
work:

- true provider token/partial-output streaming
- any live reconnect/resume of an active session
- deeper guided flow polish beyond the current thin verify/diagnose/repair
  wrappers
- richer artifact rendering polish beyond the current shortcut previews

## Pass 2 Boundary

The following remain deliberate Pass 2 items and should not be mislabeled as
Pass 1 defects:

- true provider token/partial-output streaming
- any live reconnect/resume of an active session

## Verification Commands

These are the non-mutating checks that ground this checklist:

```bash
uv run pytest -q tests/test_ux_cli.py tests/test_r12_turnkey.py
uv run pyocd-debug --help
uv run pyocd-debug-brain --help
```

## Acceptance For This Checklist

This checklist is complete when:

- every major `UXLayer.md` requirement is classified
- every `partial` or `missing` item has one explicit next implementation action
- the Pass 1 vs Pass 2 boundary is explicit
- no checklist item silently changes the current shell/session model

## Verified

- `markdowns/UXLayer.md` was re-read against the current implementation.
- The current UX code was re-checked in:
  - `src/pyocd_debug_mcp/ux/`
  - `src/pyocd_debug_mcp/brain/events.py`
  - `src/pyocd_debug_mcp/brain/loop.py`
- `uv run pytest -q tests/test_ux_cli.py tests/test_r12_turnkey.py` passed in
  this session.
- `uv run pyocd-debug --help` and `uv run pyocd-debug-brain --help` both worked
  in this session.

## Pending Verification

- Live operator-shell usage on the scoped pair still needs to reconfirm the UX
  rough edges under real provider/board activity.
- The new summary-first raw-output default still needs fresh live validation on
  the scoped pair.
