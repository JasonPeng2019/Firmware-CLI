# Current Progress

## How To Read This Document

Use this file after `README.md` and `ROADMAP.md`.

- `README.md` explains the repo layout, the scoped board pair, and the main
  command surface.
- `ROADMAP.md` explains the full delivery order and why the pieces depend on
  each other.
- This file is the current live status source:
  - what is implemented
  - what was re-proved in the latest clean rerun
  - what commands still matter
  - what outputs are expected and why they matter
  - what work is still open right now

This file is intentionally current-state only. Older exploratory logs and stale
frontier notes do not belong here.

## Current Position

The scoped board pair is still:

- `nrf52833dk`
- `nucleo_l476rg`

What is already true:

- the shared bring-up, SWD, UART, Stage 1 smoke, MCP server, runtime-safety,
  and benchmark substrate are implemented
- the scoped pair is live-proven through the full `R11` benchmark layer
- the turnkey brain and the additive `pyocd-debug` operator shell are
  implemented in code
- the turnkey provider/prompt layer now has explicit hybrid session continuity
  and live tool-schema prompting:
  - the brain always persists canonical compact local memory across turns
  - OpenAI uses native Responses API continuation when healthy, with local
    fallback and periodic safety sync
  - Anthropic, Codex CLI, and Claude CLI use the same local-memory session
    model without fake durable remote sessions
  - the model-facing tool block now comes from live MCP tool metadata filtered
    to the curated brain tool surface
- the Codex-backed turnkey path has already cleared the frozen 12-case turnkey
  suite on the scoped pair

What is still open:

- the required second-provider turnkey proof on the scoped pair is not green
  yet
- broader fresh-machine portability proof is still open

So the repo is **not** waiting on more shared-board substrate work before new
turnkey validation. The current boundary is:

- lower layers are green on the scoped pair
- Codex-backed turnkey proof exists
- second-provider closure and fresh-machine portability still need work

## What Is Implemented

### Repo And Environment Baseline

The repo now has:

- canonical product code under `src/pyocd_debug_mcp/`
- tracked board configs under `boards/`
- tracked reference firmware under `firmware/`
- shared runtime output under `runs/`
- `uv`-based environment management with `.python-version`
- bundled runtime data for the installed product:
  - benchmark cases
  - turnkey skills
  - turnkey playbooks

### Board Bring-Up And Shared Hardware Control

The board/toolchain surface that exists today includes:

- `host_bootstrap.py`
- `stage0_check.py`
- `tests.harness.stage1_smoke`
- shared probe inventory and board-aware selection
- shared serial resolution with vendor-assisted paths when available
- shared SWD control through pyOCD
- shared UART capture
- shared symbol resolution
- typed target/service errors

### MCP Server And Runtime Safety

The current server/runtime layer includes:

- the live MCP server in `src/pyocd_debug_mcp/server.py`
- session ids and per-session run trees
- structured event logging under `runs/<session_id>/logs/events.jsonl`
- flash guardrails
- recover guardrails
- mutation watcher behavior

### Benchmark And Turnkey Product Layer

The product layer that exists today includes:

- the shared benchmark contract/runtime helpers in
  `src/pyocd_debug_mcp/benchmark_support.py`
- the shared Stage 1 green verifier in
  `src/pyocd_debug_mcp/reference_smoke.py`
- the turnkey brain in `src/pyocd_debug_mcp/brain/`
- the operator-facing shell in `src/pyocd_debug_mcp/ux/`
- decision-provider backends for:
  - `openai-api`
  - `anthropic-api`
  - `codex-cli`
  - `claude-cli`
- a session-aware provider contract with:
  - declared provider capabilities
  - loop-owned provider session state
  - canonical compact memory entries plus compacted summary state
  - persisted continuation and compaction metadata in turnkey state and
    model-turn artifacts
- live MCP tool metadata loading plus a curated tool-schema prompt bundle in
  `src/pyocd_debug_mcp/brain/tool_schemas.py`
- the frozen 12-case benchmark corpus:
  - `k001`
  - `b001`
  - `b002`
  - `b003`
  - `b004`
  - `f001`
  mirrored across both scoped boards

## Latest Clean-Slate Proof Boundary

This section records the latest rerun that matters for the current repo truth.

Host:

- macOS mixed-board bench host

Visible probes in the latest rerun:

- STM32 ST-Link `0668FF514988525067213913`
- Nordic J-Link `685400693`

Board-specific serial ports in the latest rerun:

- `nucleo_l476rg` -> `/dev/cu.usbmodem143103`
- `nrf52833dk` -> `/dev/cu.usbmodem0006854006931`

What this clean-slate rerun re-proved:

- non-hardware check ladder is green
- packaged wheel still builds
- `host_bootstrap.py --board-id <board>` is now a real board-attached
  readiness check:
  - it requires a uniquely matched probe
  - it attempts board-specific serial resolution
  - it prints the matched probe UID/description
  - it prints the matched serial port
- STM32 Stage 0 still passes
- STM32 Stage 1 smoke still passes
- Nordic Stage 0 still passes, including recover
- Nordic Stage 1 smoke still passes

## Commands To Rerun Now

These are the commands that matter for validating the current repo. They are
listed in the same order you should run them.

### Non-Hardware Regression Ladder

1. `uv run pytest -q`
   Expected:
   - suite passes cleanly
   Why:
   - proves the Python-side contract, benchmark/runtime helpers, UX shell
     behavior, and packaging/runtime assumptions still hold

2. `uv run ruff check .`
   Expected:
   - no lint failures
   Why:
   - catches drift and broken local edits before board time is wasted

3. `uv run mypy src`
   Expected:
   - no type failures
   Why:
   - the board-control and turnkey layers are typed enough that mypy catches
     real regressions early

4. `uv build --wheel`
   Expected:
   - the wheel builds successfully
   Why:
   - proves the packaged product still assembles, including bundled runtime
     data that the turnkey/runtime path depends on

### Host / Bootstrap Ladder

1. `uv run pyocd list --probes`
   Expected:
   - both scoped-board probes are visible:
     - STM32 ST-Link `0668FF514988525067213913`
     - Nordic J-Link `685400693`
   Why:
   - proves the host can actually see the attached debug interfaces before any
     repo logic is blamed

2. `uv run python host_bootstrap.py --board-id nucleo_l476rg`
   Expected:
   - `Selected-board attachment readiness`
   - matched probe UID `0668FF514988525067213913`
   - matched serial port `/dev/cu.usbmodem143103`
   - summary:
     `Selected board attachment and host prerequisites are ready for stage0_check.py`
   Why:
   - proves the stricter STM32 board-attached bootstrap path is green

3. `uv run python host_bootstrap.py --board-id nrf52833dk`
   Expected:
   - `Selected-board attachment readiness`
   - matched probe UID `685400693`
   - matched serial port `/dev/cu.usbmodem0006854006931`
   - summary:
     `Selected board attachment and host prerequisites are ready for stage0_check.py`
   Why:
   - proves the stricter Nordic board-attached bootstrap path is green

Important bootstrap rule:

- when `--board-id` is present, a green result now means the selected board is
  attached and visible enough to start `stage0_check.py`
- if probe matching is missing or ambiguous, the command must fail
- if serial matching is ambiguous, the command must warn with rerun guidance
  such as `--port BOARD_ID=PORT`

### Real Board Proof Ladder

1. `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg`
   Expected:
   - probe visible
   - target `stm32l476rgtx` available
   - virtual COM port `/dev/cu.usbmodem143103`
   - reference flash succeeds
   - UART output contains `boot ok`
   - summary says the requested Stage 0 validations were covered
   Why:
   - proves the current STM32 reference path still flashes and talks over the
     shared substrate

2. `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
   Expected:
   - `Flashed firmware.hex`
   - `Read pc=...`
   - `Resolved stage1_known_value`
   - `Read stage1_known_value=0x1234ABCD`
   - `UART matched 'boot ok'`
   - final summary:
     `Stage 1 smoke harness passed`
   Why:
   - proves SWD + ELF + memory read + UART still work together as one system on
     STM32

3. `uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk`
   Expected:
   - probe visible
   - target `nrf52833` available
   - exact silicon identity match at `FICR.INFO.PART`
   - virtual COM port `/dev/cu.usbmodem0006854006931`
   - reference flash succeeds
   - UART output contains `boot ok`
   - recover completes successfully
   - summary says the requested Stage 0 validations were covered
   Why:
   - proves the current Nordic scoped path still covers attach, flash, UART,
     and recover on the real board

4. `uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk`
   Expected:
   - `Flashed firmware.hex`
   - `Read pc=...`
   - `Resolved stage1_known_value`
   - `Read stage1_known_value=0x1234ABCD`
   - `UART matched 'boot ok'`
   - final summary:
     `Stage 1 smoke harness passed`
   Why:
   - proves the full shared SWD + UART + symbol contract still holds on the
     Nordic board

## Latest Observed Results From This Pass

These are the latest real rerun results that back the current status.

### Non-Hardware

- `uv run pytest -q`
  - passed: `244 passed`
- `uv run ruff check .`
  - passed
- `uv run mypy src`
  - passed
- `uv build --wheel`
  - passed

### Turnkey Provider/Prompt Refactor

- the Branch A provider-session and tool-schema refactor is green under the
  current non-hardware ladder
- direct automated coverage now proves:
  - provider capability and provider-session serialization
  - curated MCP tool-schema extraction and stable rendering order
  - canonical provider memory recording without recursive prompt nesting
  - deterministic memory compaction and compaction-on-char-overflow
  - model-summary compaction fallback to deterministic summary
  - OpenAI native continuation with local fallback and periodic safety sync
  - Anthropic, Codex CLI, and Claude CLI local-memory continuation semantics
  - loop-owned provider session state threading across turns
  - CLI and shell forwarding for `--memory-mode` and `--native-sync-every`

### Host / Bootstrap

- `uv run pyocd list --probes`
  - passed with both scoped-board probes visible
- `uv run python host_bootstrap.py --board-id nucleo_l476rg`
  - passed
  - matched probe:
    `0668FF514988525067213913`
  - matched serial:
    `/dev/cu.usbmodem143103`
- `uv run python host_bootstrap.py --board-id nrf52833dk`
  - passed
  - matched probe:
    `685400693`
  - matched serial:
    `/dev/cu.usbmodem0006854006931`

### Board Proof

- `uv run python stage0_check.py --board-id nucleo_l476rg ...`
  - passed
  - UART captured:
    `boot ok`
- `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
  - passed
  - symbol readback:
    `0x1234ABCD`
- `uv run python stage0_check.py --board-id nrf52833dk ... --recover-test nrf52833dk ...`
  - passed
  - silicon identity matched:
    `0x00052833`
  - UART captured:
    `boot ok`
  - recover:
    `Recover completed via pyOCD API mass erase`
- `uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk`
  - passed
  - symbol readback:
    `0x1234ABCD`

## What Is Still Open

The remaining live work is no longer “make the shared board substrate real.”
That part is already green on the scoped pair.

What still needs to be done now:

1. Finish the second-provider turnkey proof on the scoped pair.
   Current blocker:
   - the required non-Codex provider path is still not green end to end
   - until that proof exists, the turnkey layer is still open even though the
     Codex-backed full-suite proof is already green

2. Re-run the turnkey closure ladder once the second provider is configured and
   behaving correctly.
   That means:
   - freeform healthy verification on both scoped boards
   - the pilot cases
   - the full frozen 12-case suite
   - the same no-UID/no-port-tuning rule the Codex path already satisfies

3. Do the broader fresh-machine portability proof.
   Still open:
   - true fresh-machine Windows managed-Zephyr/no-NCS validation
   - true fresh-machine macOS managed-Zephyr/no-NCS validation

## Immediate Next Steps

If you are continuing from the current repo state, do this next:

1. Keep the current baseline frozen.
   - do not add more SERIAL or new prototype work until this clean-slate status
     is the agreed baseline

2. Fix or finish the second-provider turnkey path.
   - rerun the turnkey ladder after that provider path is actually usable on
     this host

3. After the second provider is green, update the repo-facing R12 status and
   only then move on to the next product-layer work

## Verification Status

Verified here:

- non-hardware ladder:
  - `pytest`
  - `ruff`
  - `mypy`
  - wheel build
- strict board-scoped `host_bootstrap.py --board-id ...` behavior on both
  scoped boards
- STM32 Stage 0 rerun
- STM32 Stage 1 smoke rerun
- Nordic Stage 0 rerun
- Nordic Stage 1 smoke rerun

Non-hardware verified:

- the repo truth docs now agree that the active frontier is the still-open
  turnkey closure work, not `R11`

Pending hardware or provider proof:

- second-provider turnkey closure on the scoped pair
- fresh-machine Windows managed-Zephyr/no-NCS validation
- fresh-machine macOS managed-Zephyr/no-NCS validation
