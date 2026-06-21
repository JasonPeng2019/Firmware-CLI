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
- top-level `skills/` data tree
- turnkey benchmark runner alongside the existing `R11` runner
- turnkey run artifacts written into `runs/<session_id>/...`

## Architecture

### Brain Package

The brain package lives under `src/pyocd_debug_mcp/brain/` and owns:

- configuration loading
- local MCP subprocess lifecycle
- model-provider interaction
- state tracking
- skill loading
- local workspace editing/build support
- deterministic outer-loop control
- turnkey benchmark orchestration helpers

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
- `unlock_recover`

### Local workspace actions exposed to the brain

- read one file
- replace one file
- run the case/build command
- diff against the original workspace snapshot
- run final green verification

### Actions intentionally withheld in v1

- `write_memory`
- `write_core_register`
- `set_breakpoint`
- `remove_breakpoint`
- `read_memory_block`

These are intentionally excluded to optimize for turnkey reliability on the
current benchmark and task surface rather than maximum mutation power.

## CLI Contract

Add a new console script:

- `pyocd-debug-brain`

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
- If the task obviously requires a code fix but there is no editable workspace
  and build command, the CLI returns a deterministic refusal.
- The CLI owns server startup and teardown.

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

- stop after `max_iters`
- stop after repeated identical build failures with no file change
- stop after repeated diagnosis-only turns with no new observation
- stop after repeated edit/build cycles with no verification improvement
- interpret server `Refused [...]` and `Blocked [...]` responses as state
  transitions, not noise
- refuse edit/build actions in freeform mode unless the user provided
  workspace/build context

`R12` does not replace `R10` guardrails. It consumes them.

## Turnkey Run Capture

The MCP server session root under `runs/<session_id>/...` remains canonical.

The turnkey layer must add these artifacts:

- `run-metadata/turnkey_request.json`
- `run-metadata/turnkey_result.json`
- `run-metadata/turnkey_state.json`
- `logs/brain_trace.jsonl`
- `logs/model_turns.jsonl`
- `logs/prompt.txt`
- `applied-patches/turnkey.diff`

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
```

## Out Of Scope For This Pass

- no `nrf52840dk` critical-path work
- no new MCP server tools
- no additional provider surfaces beyond the four frozen backends above
- no reconnect-tolerant benchmark accounting
- no expanded benchmark corpus beyond the current 12 cases
- no `R13+` work
