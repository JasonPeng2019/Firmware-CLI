# R12 Turnkey Brain v1 Spec

## Purpose

`R12` turns the already-proven scoped substrate into the first turnkey product
layer for the scoped pair:

- `nrf52833dk`
- `nucleo_l476rg`

The acceptance target for this pass is not a harder corpus. It is:

- parity on the existing 12-case `R11` suite
- much lower operator burden
- one-command execution through a repo-owned CLI

This document is the implementation source of truth for `R12`.

Current prototype amendment:

- The original `R12` acceptance layer proved the first turnkey path over the
  frozen `R11` corpus.
- The current prototype target is a stronger autonomy proof on top of that
  path. It should show that the model can work freely on host-side code,
  request governed board interactions only when needed, use live progress to
  avoid waiting blindly, and validate fixes with scoped evidence.
- Product polish, remote hosting, broad backend expansion, and shipped UI
  completeness remain later work. The prototype should prioritize capability,
  bounded execution, and debuggability.

## Frozen Product Decisions

- The turnkey brain is a native Python client.
- The turnkey brain is not a Codex CLI wrapper; it is a native Python client
  that may optionally delegate decision turns to local coding CLIs.
- The provider layer supports four backends:
  - `openai-api`
  - `anthropic-api`
  - `codex-cli`
  - `claude-cli`
- The brain owns the orchestration loop directly.
- The first CLI is dual-mode:
  - freeform task mode
  - benchmark mode
- The first `R12` benchmark uses the same 12-case corpus already frozen in
  `R11`:
  - `pilot_v1_plus_b003_b004`
- The premium value in this pass is:
  - no user-authored prompt
  - no manual MCP registration
  - no required Codex CLI dependency for the API-backed path
  - no explicit probe UID in the normal path
  - no explicit serial-port tuning in the normal path
- The scoped pair remains `nrf52833dk + nucleo_l476rg`.
- `nrf52840dk` remains retained but outside the `R12` critical path.

## Deliverables

The first `R12` implementation must add all of these:

- `src/pyocd_debug_mcp/brain/`
- `pyocd-debug-brain` console script
- `src/pyocd_debug_mcp/ux/`
- `pyocd-debug` console script
- top-level `skills/` data tree
- top-level `playbooks/turnkey/` internal deterministic helper tree
- turnkey benchmark runner alongside the existing `R11` runner
- turnkey run artifacts written into `runs/<session_id>/...`
- package-owned bundled runtime data for:
  - benchmark cases/prompts/schema
  - turnkey skill manifests
  - turnkey playbooks

The current prototype increment must add or tighten:

- persistent provider sessions where the provider supports them
- a final board-decision boundary: host-only work is model-native, while
  board/server-native work is still gated by the brain
- real MCP tool descriptions and JSON schemas in the turnkey prompt
- model-composed action batches, plus `wait` and UART write capability
- live CLI progress output and a developer inspector stream
- basic timeout hardening for every blocking layer still missing a bound
- dynamically refined timeout budgets proposed by the model, clamped by the
  brain, and mirrored into the server for subsequent operations
- client actions: model-authored scripts that persist for the client session
  and can call gated server tools only through the brain-approved API
- scoped green approval with model-made tests, including a narrow flipped-value
  check for the first benchmark/prototype surface
- chunked stream checkpoints for UART reads, builds, and long client actions

## Architecture

### Brain Package

The brain package lives under `src/pyocd_debug_mcp/brain/` and owns:

- configuration loading
- local MCP subprocess lifecycle
- model-provider interaction
- structured brain events for the operator UX layer
- state tracking
- skill loading
- local workspace editing/build support
- deterministic outer-loop control
- turnkey benchmark orchestration helpers
- provider-session state and conversation continuation
- model-native host action dispatch
- governed client-action registration/execution
- live event emission for the operator CLI and inspector
- timeout-budget clamping and server timeout synchronization

### Provider

The provider layer is now pluggable.

Frozen provider rules:

- `openai-api`
  - native OpenAI SDK + Responses API
  - requires `OPENAI_API_KEY`
  - requires explicit model via `--model` or `PYOCD_TURNKEY_MODEL`
- `anthropic-api`
  - native Anthropic SDK + Messages API
  - requires `ANTHROPIC_API_KEY`
  - requires explicit model via `--model` or `PYOCD_TURNKEY_MODEL`
- `codex-cli`
  - shells out to local `codex exec`
  - uses whatever auth Codex already has configured:
    - ChatGPT/Codex subscription
    - or Codex/OpenAI API-key login
  - may use `--model` / `PYOCD_TURNKEY_MODEL` when explicitly supplied
- `claude-cli`
  - shells out to local `claude --print`
  - uses whatever auth Claude Code already has configured:
    - Claude subscription / OAuth token
    - or `ANTHROPIC_API_KEY`
  - may use `--model` / `PYOCD_TURNKEY_MODEL` when explicitly supplied
- the provider wrapper stays isolated from the orchestration loop
- every provider must return the same structured next-action shape
- subscription-vs-API billing is owned by the chosen provider surface, not by
  the R12 loop

### MCP Client

The turnkey brain launches the existing MCP server locally as a stdio
subprocess:

- command: `uv run pyocd-debug-mcp`
- cwd: repo root
- the spawned-server contract is wrapped through:
  - `ServerCommand`
  - `ToolClientProtocol`
  - a transport-only stdio client
  - a higher-level parsed local client wrapper

The turnkey layer must not require:

- `codex mcp add`
- `codex exec`
- manual server launch

### Internal State

The brain tracks, at minimum:

- run mode
- board id
- active session id
- selected skills
- iteration count
- flash/build/recover counters
- last key observations
- last classification
- last mutation result
- blocked/refused action families
- workspace/build context when code edits are allowed
- typed evidence records:
  - observations
  - hypotheses
  - experiments
  - strategy evaluations

### Skills

The first skills system is data-driven and YAML-based.

Frozen layout:

- `skills/common/`
- `skills/mcu_families/nrf52833/`
- `skills/mcu_families/stm32l476/`

Every skill file must include:

- `skill_id`
- `title`
- `applies_to`
- `priority`
- `facts`
- `diagnostic_hints`
- `verification_checks`
- `forbidden_actions`

Frozen selection rules:

- load all matching `common` skills
- load all matching `mcu_family` skills
- optionally load task/case-kind-specific skills
- dedupe by `skill_id`
- render one deterministic ordered prompt bundle

### Internal Playbooks

`R12` also keeps a separate internal deterministic helper layer under:

- `playbooks/turnkey/`

These playbooks are not the primary product interface and do not replace
`run --board-id ... --task ...`.

Their first uses are:

- reference health-check
- reference-contract diagnose
- reference-contract repair
- Nordic recover/reflash/reverify

Initial skill coverage must match the current 12-case `R11` corpus:

- healthy baseline verification
- UART mismatch triage
- known-symbol mismatch triage
- halted-target silent-UART distinction
- application-silent-UART distinction
- dual-signal regression repair
- Nordic recover policy
- STM32 no-recover expectation

## Curated Model-Facing Action Surface

The model-facing action surface is smaller than the full server surface.

### MCP-backed actions exposed to the brain

- `connect`
- `disconnect`
- `get_board_info`
- `get_state`
- `halt`
- `resume`
- `reset`
- `read_core_register`
- `read_memory`
- `flash_firmware`
- `read_serial`
- `write_serial`
- `wait`
- `unlock_recover`

### Model-native host actions

Host-only file/process work may be performed without a board decision when it
does not call server-native tools and does not cross the normal host safety
policy. This is where the prototype should let the model write code, inspect
files, run local commands, and create host-only helper scripts with much less
friction than board operations.

### Local workspace actions exposed to the brain

- read one file
- replace one file
- run the case/build command
- diff against the original workspace snapshot
- run final green verification

### Client actions

Client actions are model-authored scripts saved into a client-session action
store. They are not pasted inline into a decision. The model must create or
update the named script, then choose to run it through a structured action with
inputs.

Rules:

- host-only client actions run as model-native host work
- client actions that call server-native tools are governed actions
- every server-native call inside a client action goes through the same brain
  gate as a direct tool call
- client actions persist for one client session, not globally, in this
  prototype

### Actions intentionally withheld in v1

- `write_memory`
- `write_core_register`
- `set_breakpoint`
- `remove_breakpoint`
- `read_memory_block`

These are intentionally excluded to optimize for turnkey reliability on the
current benchmark and task surface rather than maximum mutation power.

## CLI Contract

The repo now has two CLI layers over the same turnkey brain:

- `pyocd-debug-brain`
  - stable headless/automation surface
- `pyocd-debug`
  - operator-facing shell and pretty one-shot runner

### Freeform mode

```bash
pyocd-debug-brain run --board-id <id> --task "<text>" [options]
```

Required:

- `--board-id`
- `--task`

Optional:

- `--provider`
- `--model`
- `--port`
- `--flash-artifact`
- `--elf`
- `--max-iters`
- `--serial-read-seconds`
- `--workspace-root`
- `--build-command`

Freeform mode rules:

- If `--workspace-root` and `--build-command` are absent, the brain is
  diagnose/verify only.
- Generic freeform `run --task "fix ..."` does not pre-refuse based only on
  wording.
- Explicit repair-oriented shell flows such as `/repair` still require repair
  context and refuse shell-side until `/workspace` and `/build-command` are
  set.
- When freeform repair context is present, editable paths are constrained by
  workspace containment rather than a hardcoded `src/` root.
- The CLI owns server startup and teardown.

### Operator shell mode

```bash
pyocd-debug
pyocd-debug run --board-id <id> --task "<text>" [options]
pyocd-debug benchmark --case-id <id> [options]
pyocd-debug benchmark --suite pilot_v1_plus_b003_b004 [options]
pyocd-debug history
pyocd-debug show <session_id>
pyocd-debug rerun <session_id>
```

Frozen Pass 1 UX decisions:

- `pyocd-debug-brain` remains unchanged as the stable headless CLI.
- `pyocd-debug` is additive and reuses the exact same orchestration loop and
  benchmark path.
- the shell is implemented with `rich` + `prompt_toolkit`
- the shell consumes a structured event sink from the brain loop
- raw output policy is summary-first:
  - REPL `/raw on` prints the full raw provider reply after each completed turn
  - REPL `/raw off` hides raw output but still stores it in artifacts
  - REPL `/raw last` re-renders the last completed provider reply
  - one-shot `pyocd-debug run|benchmark` uses `--raw-output off|final|all`
- Pass 1 is turn-level-first:
  - live provider/tool/build/green-check status is visible while work is in
    progress
  - full raw provider output becomes visible after the completed turn
  - true token-level provider streaming is intentionally deferred to Pass 2

### Benchmark mode

```bash
pyocd-debug-brain benchmark --case-id <id> [options]
pyocd-debug-brain benchmark --suite pilot_v1_plus_b003_b004 [options]
```

Benchmark mode reuses the `R11` case corpus and scoring contract.

## Convergence Rules

The server watcher remains the authoritative destructive-action guardrail.
`R12` adds softer brain-level orchestration control above it.

Frozen first brain-level convergence rules:

- ask the model for an iteration estimate broken down by board calls,
  debugging headroom, likely false stops, and a fixed brain-added cushion
- clamp the final iteration budget to a brain-owned hard maximum
- stop after repeated identical build failures with no file change
- stop after repeated diagnosis-only turns with no new observation
- stop after repeated edit/build cycles with no verification improvement
- prompt the model to propose per-action timeout budgets instead of always
  using maximum defaults
- clamp model-proposed timeouts in the brain and mirror allowed updates to the
  server through a partial `set_timeouts` style update; the setter changes only
  named fields and never rewrites a config file
- apply timeout changes to subsequent operations, not in-flight operations
- use chunked checkpoints for UART reads, builds, and long client actions so
  the brain can detect progress, summarize it, and cancel when progress stalls
- interpret server `Refused [...]` and `Blocked [...]` responses as state
  transitions, not noise
- use gated early exits for `infeasible` and `needs_intervention`
- require user permission before an automated action whose estimated duration
  exceeds the unattended-duration cap
- incentivize targeted print/log instrumentation when debugging unexpected
  behavior or bug reproduction failures

`R12` does not replace `R10` guardrails. It consumes them.

## Turnkey Run Capture

The MCP server session root under `runs/<session_id>/...` remains canonical
whenever a real board session is created.

The turnkey layer now creates a provisional run root before provider creation
or MCP startup. That provisional run root is renamed to the real
`runs/<session_id>/...` path the first time a session is created.

If no board session is ever created, the provisional run root remains in place
with `session_id=null` and a turnkey result that uses:

- `final_status=blocked`
- `classification=tooling_failure`

The turnkey layer must add these artifacts:

- `run-metadata/turnkey_request.json`
- `run-metadata/turnkey_result.json`
- `run-metadata/turnkey_state.json`
- `logs/brain_events.jsonl`
- `logs/brain_trace.jsonl`
- `logs/model_turns.jsonl`
- `logs/prompt.txt`
- `logs/provider_stream.jsonl`
- `logs/parsed_decisions.jsonl`
- `logs/tool_calls.jsonl`
- `logs/stream_checkpoints.jsonl`
- `logs/inspector_events.jsonl`
- `applied-patches/turnkey.diff`

The state artifact must include the typed evidence trail:

- observations
- hypotheses
- experiments
- strategy evaluations
- timeout budget proposals and clamped values
- client actions created and invoked
- scoped green-test scripts and flipped-value results

In benchmark mode, also persist:

- `run-metadata/benchmark_case.json`
- `run-metadata/benchmark_result.json`
- `run-metadata/score.json`
- `run-metadata/firmware_identity.json`

Frozen benchmark session rule for `R12`:

- one benchmark case equals one MCP session
- if the turnkey client reconnects mid-case, count that case as a benchmark
  failure in this first version

## Benchmark Contract

`R12` benchmarking is a sibling path to `R11`, not a rewrite of it.

Frozen benchmark rules:

- reuse `pilot_v1_plus_b003_b004`
- reuse the existing case manifests
- reuse the existing rubric unless a turnkey-only field is strictly necessary
- keep `r11_benchmark.py` behavior intact

The first turnkey benchmark proves product value through lower operator burden:

- no custom prompt authoring
- no required `codex exec`
- no required `codex mcp add`
- no explicit probe UID in the normal path
- no explicit serial port in the normal path
- no manual MCP server launch

The prototype capability increment additionally proves:

- the model can keep a persistent working session instead of reopening every
  turn
- the model can do substantial host-side code work without asking the board gate
  for every step
- board interactions remain explicit final decisions, batched when useful, and
  visible to the operator
- the operator can see progress and inspect brain/provider/server traffic while
  long work is still running
- timeout choices become task-sensitive instead of hardcoded maximum waits
- scoped green approval can be driven by model-made scripts and a narrow
  flipped-value check

## Acceptance Threshold

The first `R12` closure target is:

- both known-good cases reach full success
- both observability-fault cases reach full success with correct non-code
  diagnosis and no source edits
- at least 6 of the 8 injected-bug cases reach full success
- no case scores below 50
- suite average is at least 85
- no forbidden recover usage on non-recover cases
- no watcher-blocked runs caused by turnkey thrash
- the normal path uses `connect(board_id=...)` with no hard-coded UID or port
  tuning
- every case is runnable from one turnkey CLI command

This proves:

- parity on the existing corpus
- lower operator/setup burden

It does not require higher raw score than the `R11` BYO-agent path.

## Manual Validation Sequence

Before live turnkey validation, the scoped substrate must still be green:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python host_bootstrap.py --board-id nucleo_l476rg
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

Then validate:

```bash
uv run pyocd-debug-brain run --provider openai-api --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why." --model <model>
uv run pyocd-debug-brain run --provider anthropic-api --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why." --model <model>
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider claude-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain benchmark --provider openai-api --suite pilot_v1_plus_b003_b004 --model <model>
uv run pyocd-debug run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug benchmark --case-id nrf52833dk__k001_reference_green
uv run pyocd-debug history
```

## Out Of Scope For This Pass

- no `nrf52840dk` critical-path work
- no broad MCP server expansion beyond the prototype's required UART write,
  wait, timeout-sync, and stream/progress plumbing
- no additional provider surfaces beyond the four frozen backends above
- no reconnect-tolerant benchmark accounting
- no token-level provider streaming in Pass 1; that is the deliberate next UX
  follow-up after the current shell lands
- no expanded benchmark corpus beyond the current 12 cases
- no `R13+` work
