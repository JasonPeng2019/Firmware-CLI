# UX Layer

> **Status:** Pass 1 implemented, Pass 2 pending. This document now records the
> implemented client-facing terminal UX layer over the existing `R12` turnkey
> brain. It does **not** override
> `markdowns/firmware_agent_build_plan_concrete (10).md` or
> `markdowns/curr/r12_turnkey_spec.md`; it is the concrete UX-layer design note
> for the current implementation and the follow-up token-streaming pass.

## Non-Negotiable First Change

Before anything else can be done, add a structured event stream or callback
hook from the brain loop.

This prerequisite is now implemented in `src/pyocd_debug_mcp/brain/events.py`
and threaded through the turnkey loop. The new operator shell consumes those
events directly and the run artifacts now also persist
`runs/<session_id>/logs/brain_events.jsonl`.

This is the one concrete prerequisite for a serious CLI UX layer. Without it,
the repo can only produce end-of-run summaries and post-hoc artifacts. That is
enough for automation and benchmarks, but it is not enough for a Codex-style or
Claude-style operator experience.

Why this must come first:

- the current brain loop returns a rich final object, but it does not expose a
  live, structured stream of per-turn and per-tool events
- a richer shell needs to render progress while the brain is still running, not
  only after it finishes
- the shell must consume normalized events, not scrape human text back out of
  stdout or out of `runs/<session_id>/...`
- the same event stream is also the cleanest basis for session history,
  artifact discovery, richer error rendering, and later hosted/client work

What this first change should provide:

- an event sink or callback on the main turnkey loop
- one structured event shape for:
  - loop lifecycle
  - provider turn start/end
  - tool start/end
  - file read/replace
  - build start/end
  - green-check start/end
  - refusal/block/failure
  - verification-state updates
  - final result emission
- stable event fields such as:
  - `event_kind`
  - `timestamp`
  - `board_id`
  - `session_id`
  - `provider`
  - `model`
  - `tool_name`
  - `arguments_summary`
  - `duration_ms`
  - `outcome`
  - `verification_snapshot`
  - `message`

This was the blocker item ahead of shell polish. The implementation now uses
that event stream as the single live-rendering substrate instead of scraping
stdout or replaying artifacts after the fact.

## Purpose

The current `R12` implementation already has a usable headless product core:

- a native Python turnkey brain
- a stable `pyocd-debug-brain` CLI
- a local MCP subprocess client
- multiple provider backends
- run artifacts under `runs/<session_id>/...`
- benchmark runners and score reporting

What it does **not** yet have is a strong operator-facing terminal shell.

The goal of this proposal is to define a pure CLI UX layer that sits on top of
the existing brain/runtime and makes the product feel closer to Codex CLI or
Claude Code while preserving the current scriptable surface.

## Implemented Pass 1

The current repo now ships the Pass 1 UX layer with these implemented pieces:

- a separate operator-facing console script:
  - `pyocd-debug`
- the headless CLI remains unchanged:
  - `pyocd-debug-brain`
- the new UX package under `src/pyocd_debug_mcp/ux/`
- structured event emission from the turnkey loop
- Rich + `prompt_toolkit` shell mode with:
  - interactive REPL feel
  - live provider/tool/build/green-check status
  - visible evidence summaries after completed provider turns
  - raw-output toggling after completed turns
  - history/show/rerun flows over `runs/<session_id>/...`
- pretty one-shot wrappers:
  - `pyocd-debug run ...`
  - `pyocd-debug benchmark ...`
  - `pyocd-debug history`
  - `pyocd-debug show <session_id>`
  - `pyocd-debug rerun <session_id>`

What is deliberately **not** implemented yet:

- token-by-token provider streaming
- live reconnection into an already-running session
- any MCP server API changes
- any benchmark schema/corpus changes

That remaining streaming work is the explicit Pass 2 follow-up.

## Current Barebones CLI: Exact Specification

This section freezes what the repo currently exposes today. The UX layer should
be built on top of this, not by pretending the current CLI already does more
than it really does.

### Installed Console Scripts

The current repo declares these console scripts in `pyproject.toml`:

- `pyocd-debug-mcp`
- `pyocd-debug-brain`

This document is about the current `pyocd-debug-brain` surface.

### Current Subcommands

The current turnkey CLI has exactly two subcommands:

- `pyocd-debug-brain run`
- `pyocd-debug-brain benchmark`

There is no current shell mode, no REPL mode, no history mode, and no resume
mode.

### `run` Command: Current Contract

Current syntax:

```bash
pyocd-debug-brain run \
  --board-id <id> \
  --task "<text>" \
  [--provider <provider>] \
  [--model <model>] \
  [--port <port>] \
  [--flash-artifact <path>] \
  [--elf <path>] \
  [--max-iters <n>] \
  [--serial-read-seconds <seconds>] \
  [--workspace-root <path>] \
  [--build-command "<cmd>"]
```

Required arguments:

- `--board-id`
- `--task`

Optional arguments:

- `--provider`
- `--model`
- `--port`
- `--flash-artifact`
- `--elf`
- `--max-iters`
- `--serial-read-seconds`
- `--workspace-root`
- `--build-command`

Current behavior:

- this is a one-shot command, not a persistent shell
- it constructs a `TurnkeyInvocation`
- it loads a provider config
- it runs the brain to completion
- it prints a final summary only
- it exits

Current refusal behavior:

- if the task text appears to require code repair but no
  `--workspace-root` + `--build-command` are provided, the command refuses with
  `Refused [turnkey/missing-workspace-context]: ...`

Current provider behavior:

- provider defaults from `.env` / environment via `PYOCD_TURNKEY_PROVIDER`
- if unset, the current default provider is `openai-api`
- model defaults from `PYOCD_TURNKEY_MODEL` unless `--model` is passed
- provider options currently supported:
  - `openai-api`
  - `anthropic-api`
  - `codex-cli`
  - `claude-cli`

Current provider prerequisites:

- `openai-api` requires `OPENAI_API_KEY` and a model
- `anthropic-api` requires `ANTHROPIC_API_KEY` and a model
- `codex-cli` requires a local `codex` executable in `PATH`
- `claude-cli` requires a local `claude` executable in `PATH`

### `benchmark` Command: Current Contract

Current syntax:

```bash
pyocd-debug-brain benchmark \
  (--case-id <case> | --suite <suite>) \
  [--provider <provider>] \
  [--model <model>] \
  [--max-iters <n>] \
  [--serial-read-seconds <seconds>]
```

Required argument group:

- exactly one of `--case-id` or `--suite`

Optional arguments:

- `--provider`
- `--model`
- `--max-iters`
- `--serial-read-seconds`

Current behavior:

- for one case, it runs the turnkey benchmark case and prints one case summary
- for a suite, it runs the suite and prints one case summary per case, then one
  suite summary
- it reuses the `R11`-style printed benchmark summary shape rather than a
  richer interactive display

### Current Exit-Code Contract

Current `run` exit behavior:

- exit `0` when final status is:
  - `fixed`
  - `healthy_confirmed`
  - `diagnosed_only`
- exit `1` otherwise
- exit `2` for `BrainConfigError`

Current `benchmark` exit behavior:

- exit `0` only when the case or suite satisfies the current benchmark
  acceptance rule
- exit `1` otherwise
- exit `2` for `BrainConfigError`

### Current Human-Visible Output

For `run`, the CLI currently prints only a final block:

```text
[FINAL_STATUS] board=<board_id> session_id=<session_id or (none)>
classification: <classification>
summary: <summary>
root_cause: <root cause>
verification: flash_ok=<bool> uart_ok=<bool> symbol_ok=<bool> green_check_ok=<bool>
run_root: <path>
```

For `benchmark --case-id`, it currently prints:

```text
[OUTCOME_LABEL] <case_id> score=<score> session_id=<session_id or (missing)>
    - <reason 1>
    - <reason 2>
```

For `benchmark --suite`, it prints one case line per case and then:

```text
Suite <suite_name>: full_success=<n> partial_success=<n> fail=<n> average_score=<float>
```

### Current Artifact Behavior

The current CLI already creates and/or depends on these artifacts:

- MCP-session artifacts under `runs/<session_id>/...`
- turnkey artifacts such as:
  - `run-metadata/turnkey_request.json`
  - `run-metadata/turnkey_result.json`
  - `run-metadata/turnkey_state.json`
  - `logs/brain_trace.jsonl`
  - `logs/model_turns.jsonl`
  - `logs/prompt.txt`
  - `applied-patches/turnkey.diff`

This is important: the product already has strong machine-readable outputs. The
weakness is not the artifact model. The weakness is the live operator
experience.

### Current Internal Structure That The UX Layer Should Reuse

The current barebones CLI is intentionally thin. The important product logic
already lives elsewhere:

- `brain/cli.py` is only the entrypoint and final printer
- `brain/loop.py` owns the real orchestration loop
- `brain/mcp_client.py` owns local MCP server startup and tool calls
- `brain/benchmark.py` owns turnkey benchmark execution

This separation is good and should be preserved.

### Current Limitations

The current CLI is barebones in exactly these ways:

- no interactive shell or REPL feel
- no live streaming while the agent is thinking
- no visible tool-by-tool activity
- no visible observation / hypothesis / strategy summaries during a run
- no session browser
- no resume/history interface
- no richer refusal/block/error panels
- no artifact browser or artifact shortcuts
- no guided flow for common operator tasks
- no distinction between headless automation output and operator-friendly output

## Design Decision: Keep The Current CLI As The Headless Surface

The current `pyocd-debug-brain` command should remain the stable headless and
automation-oriented surface.

Why:

- scripts, CI, and benchmark docs already depend on this shape
- the current CLI has clean exit codes and deterministic text output
- the core orchestration logic is already properly separated from presentation
- operator-shell iteration should not destabilize the benchmark or automation
  path

So the right move is not to turn the existing CLI entrypoint into a giant mixed
presentation/runtime file. The right move is to keep the current headless CLI
stable and add a richer client-facing CLI UX layer on top of the same brain
core.

## Proposed Pure CLI UX Layer

### Product Shape

The UX layer should be a pure terminal shell, not a web frontend and not a
separate remote service.

It should feel like a modern agent CLI:

- interactive
- streaming
- session-aware
- artifact-aware
- explainable
- still scriptable when needed

This means:

- the brain remains the headless engine
- the UX layer becomes the operator shell
- both share the same `TurnkeyInvocation`, `TurnkeyExecution`, provider layer,
  and MCP client

### Recommended Integration Model

Recommended design:

- keep `pyocd-debug-brain` as the current stable command
- add a new operator-facing command or subcommand for the richer shell

Two viable naming options:

- `pyocd-debug-brain console`
- `pyocd-debug`

Recommendation:

- prefer a separate client-facing command such as `pyocd-debug`

Reason:

- it cleanly separates headless automation from operator UX
- it lets the project keep the current benchmark/docs surface intact
- it gives room for a richer shell without overloading the benchmark CLI

### UX Layer Goals

The pure CLI UX layer should provide:

- an interactive shell or REPL feel
- streaming progress while the agent is thinking/acting
- visible tool activity
- visible reasoning/evidence summaries
- clean session lifecycle and resume/history
- richer error/refusal presentation
- better artifact discovery
- a more guided operator flow

### UX Layer Non-Goals

This first UX layer should **not**:

- redesign the MCP server API
- replace the current benchmark runner
- duplicate the orchestration loop
- scrape stdout or logs as its primary state source
- add a web application requirement
- widen the model-facing action surface

## Required UX Features: Exact Integration Expectations

### 1. Interactive Shell Or REPL Feel

The operator should be able to stay in one terminal session and work through
multiple runs without retyping the full command every time.

The shell should support:

- opening into an interactive prompt
- selecting provider/model defaults once for a session
- selecting a board once for a session
- issuing high-level commands such as:
  - verify
  - diagnose
  - repair
  - benchmark
  - history
  - resume
  - artifacts
  - disconnect
  - quit

The prompt should show live context, for example:

```text
[nrf52833dk][codex-cli][session:20260623T...] >
```

The shell should still allow one-shot execution for users who do not want a
persistent session.

### 2. Streaming Progress While The Agent Is Thinking/Acting

The UX layer should render progress from the structured event stream, not from
text scraping.

Minimum live states to render:

- provider thinking
- tool starting
- tool finished
- build starting
- build finished
- green check running
- finalizing

Minimum visual behavior:

- visible spinner or status line while waiting
- per-step completion status
- elapsed time for long actions such as flash/build/green check

### 3. Visible Tool Activity

Every MCP-backed action should be surfaced as operator-visible activity.

The operator should be able to see:

- which tool is being called
- the board/session it applies to
- a short arguments summary
- whether it succeeded, refused, blocked, or failed
- how long it took

Examples:

- `connect(board_id=nrf52833dk)`
- `flash_firmware(default reference artifact)`
- `read_serial(expected='boot ok', read_seconds=3.0)`
- `unlock_recover(confirm=true)`

This must be concise enough to scan, but explicit enough that the operator can
tell what the agent is doing to the hardware.

### 4. Visible Reasoning And Evidence Summaries

The UX layer should not expose hidden chain-of-thought, but it should expose
the structured summaries the product already has:

- latest observation summary
- latest classification
- current hypothesis
- current strategy evaluation
- current verification snapshot

This is important because the turnkey brain is already producing evidence-like
state, but the current CLI hides it until the run is over.

The UX shell should show brief evidence summaries after each turn, for example:

- `Observation: UART matched but known symbol readback is wrong.`
- `Hypothesis: firmware constant is incorrect; runtime path looks healthy.`
- `Next move: inspect source file before editing.`

### 5. Clean Session Lifecycle And Resume / History

The UX layer should make session history a first-class operator concept.

It should support:

- seeing the current `session_id`
- listing recent sessions from `runs/`
- viewing the run root for a past session
- reopening a past session summary
- explicitly starting a fresh session

Important rule:

- the UX layer should distinguish between viewing a previous run and actually
  resuming active control of a board

For the first version, "resume/history" can mean session inspection and rerun
guidance rather than true live reconnection to an in-progress agent run.

### 6. Richer Error / Refusal Presentation

The current product already has stable refusal and block text:

- `Refused [code]: ...`
- `Blocked [code]: ...`

The UX layer should render these as clearer operator panels, for example:

- refusal code
- what action was refused
- why it was refused
- whether it is user-fixable
- the exact rerun hint

This is especially important for:

- missing workspace/build context
- unsupported recover on STM32
- invalid flash artifact paths/suffixes
- mutation watcher blocks

Unexpected runtime/backend failures should remain visibly different from policy
refusals.

### 7. Better Artifact Discovery

The UX layer should make the existing run artifacts easy to discover.

At minimum the operator should be able to see or open:

- run root
- prompt text
- model turns
- brain trace
- turnkey request/result/state JSON
- event log
- final serial excerpt
- diff / applied patch
- benchmark score files when in benchmark mode

The operator should not need to manually browse `runs/<session_id>/...` unless
they want to.

### 8. More Guided Operator Flow

The UX layer should offer guided entry points for the common workflows people
will actually use:

- verify this board is healthy
- diagnose a failing firmware image
- repair a benchmark case
- inspect the last run
- rerun with a different provider/model
- browse benchmark results

The goal is to reduce operator burden without weakening the current safety and
benchmark contracts.

## Proposed Architecture

### Core Rule

The UX layer must wrap the existing brain. It must not become a second
orchestration engine.

### Proposed New Package

Recommended location:

- `src/pyocd_debug_mcp/ux/`

Suggested files:

- `events.py`
- `renderer.py`
- `shell.py`
- `history.py`
- `commands.py`
- `artifacts.py`

Suggested responsibilities:

- `events.py`
  - normalized event shapes
  - event sink / callback interfaces
- `renderer.py`
  - pretty terminal rendering
  - progress lines
  - refusal/block/error panels
  - artifact shortcuts
- `shell.py`
  - interactive loop / REPL controller
- `history.py`
  - recent session discovery from `runs/`
  - run summary loading
- `commands.py`
  - high-level operator commands mapped to existing brain invocations
- `artifacts.py`
  - run-root browsing helpers

### Integration Point

The structured event stream should come from the existing brain loop.

The loop should expose something like:

- `event_sink(event)` callback
- or an async event iterator / queue

The UX layer should subscribe to that stream and render:

- progress
- tool activity
- evidence summaries
- errors/refusals
- final outcome

The headless CLI should remain able to ignore the event stream entirely.

### Why This Architecture Is Better Than A CLI Rewrite

This architecture is the better fit for the current repo because:

- the current core is already separated cleanly enough to support it
- benchmark and automation paths stay stable
- UX experimentation does not destabilize the loop
- the same runtime can later support richer terminal behavior, batch mode, and
  possibly other client surfaces without forking product logic

## Recommended Implementation Sequence

### Phase 1: Add The Event Stream

Land the structured event sink first.

Exit criteria:

- the brain loop emits normalized events
- no public CLI behavior changes yet
- unit tests cover the event shapes

### Phase 2: Add A Pretty Non-Interactive Mode

Add a formatted one-shot rendering layer over the current `run` and `benchmark`
paths.

Exit criteria:

- one-shot runs show streaming progress
- one-shot runs still preserve deterministic exit codes
- benchmark output remains scriptable

### Phase 3: Add The Interactive Shell

Add the operator-facing REPL shell on top of the same invocation layer.

Exit criteria:

- interactive board/provider selection
- session-aware prompt
- guided run/benchmark/history flows

### Phase 4: Add Session History And Artifact Browsing

Make `runs/<session_id>/...` easy to inspect from the shell.

Exit criteria:

- list recent runs
- show summaries
- open artifact paths

### Phase 5: Tighten Refusal And Failure UX

Make policy and runtime failures easier to understand.

Exit criteria:

- refusal/block/failure categories are visually distinct
- rerun guidance is visible

## Acceptance Criteria For The UX Layer

The UX layer should only be considered real when all of the following are true:

- the current `pyocd-debug-brain` headless contract still works unchanged
- the UX shell consumes structured events instead of scraping text
- a user can run a healthy-board verification flow without manually opening
  `runs/<session_id>/...`
- a user can tell which tool the agent is using in real time
- a user can see concise reasoning/evidence summaries during the run
- a user can inspect recent sessions from inside the shell
- policy refusals and watcher blocks are clearly distinguishable from runtime
  errors
- benchmark and automation paths remain stable and scriptable

## Final Recommendation

The right move is:

- keep the current `pyocd-debug-brain` CLI as the stable headless and
  automation-oriented interface
- add one structured event stream or callback hook from the brain loop before
  any UI work
- build a richer pure CLI operator shell on top of the existing brain/runtime
  rather than fusing presentation concerns into the current thin entrypoint

That gives the project both:

- a stable machine-friendly interface
- a much stronger human-facing terminal product

## Verified

- the current barebones CLI shape described here was verified against:
  - `src/pyocd_debug_mcp/brain/cli.py`
  - `src/pyocd_debug_mcp/brain/config.py`
  - `src/pyocd_debug_mcp/brain/actions.py`
  - `src/pyocd_debug_mcp/brain/loop.py`
  - `src/pyocd_debug_mcp/brain/mcp_client.py`
  - `src/pyocd_debug_mcp/brain/benchmark.py`
  - `tests/harness/r11_benchmark.py`
  - `pyproject.toml`

## Pending Verification

- whether the final operator-facing command should be `pyocd-debug` or a new
  subcommand under `pyocd-debug-brain`
- the exact terminal rendering library choice
- the exact event schema to freeze for live rendering
- whether session "resume" should mean inspection-only in v1 or true live
  reconnection
