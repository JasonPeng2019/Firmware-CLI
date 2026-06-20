# Current Progress

## How To Read This Document

Use this file after `README.md` and `ROADMAP.md`.

- `README.md` explains the repo layout, the scoped board pair, and the main
  commands.
- `ROADMAP.md` explains the full project plan and dependency order.
- This file explains the current real status of the repo:
  - what has already been implemented
  - what has already been proven on hardware
  - what commands should be rerun when validating the repo again
  - what outputs are expected and why
  - what work is still unfinished

This document intentionally uses plain-English status descriptions rather than
roadmap checkpoint shorthand.

## Current Position

In roadmap terms, all scoped work through `R10` is complete on the official
board pair:

- `nrf52833dk`
- `nucleo_l476rg`

That means the following are already implemented and live-proven on the scoped
pair:

- repo/environment standardization
- board bring-up and Stage 0 validation
- shared SWD and UART substrate
- Stage 1 smoke harness
- MCP server surface over the shared services
- runtime/session logging
- flash/recover guardrails
- mutation watcher behavior

The active roadmap item is now `R11`: benchmark-driven product validation with
`Codex CLI`.

The repo also still contains `nrf52840dk`, but it is now a retained
alternate/future Nordic profile. It is not the current blocker for the scoped
project path.

## What Has Been Implemented

### Repo And Environment Foundation

These pieces are in place and are part of the working baseline:

- canonical product code under `src/pyocd_debug_mcp/`
- tracked board configs under `boards/`
- tracked reference firmware under `firmware/`
- runtime-output tree under `runs/`
- validation and harness code under `tests/`
- `uv`-based environment flow with `.python-version`
- auto-loaded local `.env` support
- shared board-config loader used by the main Python tools

### Board Bring-Up And Stage 0

These workflows exist and are live-proven:

- `host_bootstrap.py`
- `stage0_check.py`
- tracked reference firmware for:
  - `nucleo_l476rg`
  - `nrf52833dk`
- explicit serial/probe resolution and override paths
- real flash/UART validation against tracked reference artifacts
- Nordic recover/unlock validation

### Shared Hardware-Control Substrate

The repo now has one real shared control stack instead of separate one-off
paths:

- `adapters/swd_interface.py`
- `adapters/swd_pyocd.py`
- `adapters/uart_interface.py`
- `adapters/uart_pyserial.py`
- `services/target_control.py`
- `services/uart_capture.py`
- `services/symbols.py`
- `reference_artifacts.py`
- `probe_inventory.py`
- `serial_resolver.py`

Important architectural outcomes:

- probe inventory no longer depends on unsupported `pyocd list --output json`
- board-aware auto-selection now uses `pyocd list --probes`
- the shared path preserves real probe UIDs for both J-Link and ST-Link
- the shared path is used by:
  - `host_bootstrap.py`
  - `stage0_check.py`
  - `tests.harness.stage1_smoke`
  - `server.connect(...)`

### Stage 1 Smoke Harness

The tracked Stage 1 harness at `tests/harness/stage1_smoke.py` is real and
passing on both scoped boards.

It proves the following shared-service flow:

1. load board config
2. resolve reference artifacts
3. resolve the correct serial port
4. open the correct probe/session
5. flash the reference artifact
6. `reset_and_halt`
7. read `pc`
8. resolve `stage1_known_value` from the ELF
9. read back `0x1234ABCD` from target memory
10. reset/run
11. capture UART until `boot ok`

### MCP Server And Runtime Safety Layer

The current MCP server surface is implemented over the shared substrate and
has been exercised on both scoped boards.

Validated tool surface:

- `connect`
- `disconnect`
- `get_board_info`
- `get_state`
- `halt`
- `resume`
- `step`
- `reset`
- `read_core_register`
- `write_core_register`
- `read_memory`
- `read_memory_block`
- `write_memory`
- `set_breakpoint`
- `remove_breakpoint`
- `flash_firmware`
- `read_serial`
- `unlock_recover`

The runtime/safety layer that now exists in code includes:

- per-session `session_id` creation
- append-only JSONL event logging under `runs/<session_id>/logs/events.jsonl`
- per-session metadata under `runs/<session_id>/run-metadata/session.json`
- flash guardrails for local existing `.elf` / `.hex` files only
- recover guardrails based on board config and explicit confirmation
- mutation watcher rules for repeated flash failures, UART misses, and recover
  failures

## Live Bench Facts

These are the current real bench facts that were proven on the Mac host used
for the scoped validation.

### `nucleo_l476rg`

- probe UID: `0668FF514988525067213913`
- serial port: `/dev/cu.usbmodem144403`
- pyOCD target: `stm32l476rgtx`
- pack token: `stm32l476`
- probe and COM port were confirmed to come from the same physical board

Additional proven host quirk for this board on the current Mac host:

- `connect_mode=under-reset`
- `frequency=1000000`

That matters because direct ST-Link attach could otherwise fail with the
pyOCD/ST-Link `DP wait` error even when the board is physically present.

### `nrf52833dk`

- probe UID: `685400693`
- serial port: `/dev/cu.usbmodem0006854006931`
- pyOCD target: `nrf52833`
- pack token: `nrf52833`
- silicon identity address: `0x10000100`
- expected silicon identity value: `0x00052833`
- live silicon identity match: confirmed
- probe and COM port were confirmed to come from the same physical board

## What Has Already Been Proven On Hardware

### STM32 Proof

These live runs were completed successfully:

```bash
uv run python host_bootstrap.py --board-id nucleo_l476rg
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
```

Those runs prove:

- probe visibility
- target-pack availability
- SWD connect/read
- baseline flash
- UART `boot ok`
- symbol-resolution readback of `stage1_known_value = 0x1234ABCD`

### Nordic Proof

These live runs were completed successfully:

```bash
./firmware/nrf52833dk/reference/build_reference.sh
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

Those runs prove:

- probe visibility
- target-pack availability
- SWD connect/read
- exact silicon identity
- baseline flash
- UART `boot ok`
- recover/unlock behavior
- post-recover reachability
- symbol-resolution readback of `stage1_known_value = 0x1234ABCD`

### Server Runtime And Safety Proof

The current `server.py` implementation was exercised live against both scoped
boards. That proof covered:

- board-aware `connect(board_id=..., unique_id=None)` while both probes were
  attached
- creation of `session_id`
- creation of:
  - `runs/<session_id>/logs/events.jsonl`
  - `runs/<session_id>/run-metadata/session.json`
- default flash artifact resolution
- explicit flash artifact override
- default serial resolution
- explicit serial override
- Nordic recover success with explicit confirmation
- STM32 recover refusal because no supported recover mode is tracked
- watcher blocking for repeated bad mutation loops
- disconnect/reconnect clearing watcher block state

## Regression And Manual Validation Checklist

Use this section whenever you need to re-validate the repo on a new host, after
a substrate change, or before claiming that the current benchmark work is being
run on a known-good foundation.

### 1. Static And Contract Checks

Run from the repo root:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

Expected result:

- all commands succeed with exit code `0`

Why this is expected:

- the repo test suite, lint, and type-check path were already green when the
  current benchmark runner work landed
- a failure here means the repo is not even at the previously proven baseline,
  so hardware debugging would be misleading

### 2. Scoped Board Preflight

Run the foundation checks for both boards:

```bash
uv run python host_bootstrap.py --board-id nucleo_l476rg
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg

uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

Expected result:

- all six commands pass
- `stage0_check.py` proves flash and UART on both boards
- `stage0_check.py` proves Nordic recover on `nrf52833dk`
- `stage1_smoke.py` proves symbol resolution and UART on both boards

Why this is expected:

- both boards already passed these exact workflows on the current Mac host
- the reference firmware artifacts, board configs, and shared services are now
  aligned around those flows

### 3. MCP Server Launch

Launch the server:

```bash
uv run mcp dev src/pyocd_debug_mcp/server.py
```

Expected result:

- the MCP dev server starts cleanly
- tool docstrings and tool surface are visible to the MCP client

Why this is expected:

- the current repo status already includes live tool-function validation over
  this server entrypoint

### 4. STM32 Manual Runtime Validation

Use `connect(board_id="nucleo_l476rg")` as the primary path. Do not pass
`unique_id` unless you are debugging probe-selection behavior.

Run this sequence:

1. `connect(board_id="nucleo_l476rg")`
2. verify success text contains:
   - `Connected to board`
   - `[board config: nucleo_l476rg]`
   - `via pyocd-native`
   - `session_id=`
3. verify:
   - `runs/<session_id>/logs/events.jsonl`
   - `runs/<session_id>/run-metadata/session.json`
4. `get_board_info()`
5. `flash_firmware()`
6. `flash_firmware(path="<repo-root>/firmware/nucleo_l476rg/reference/build/firmware.elf", halt_after_reset=true)`
7. `flash_firmware(path="<repo-root>/firmware/nucleo_l476rg/reference/build/firmware.hex")`
8. `halt()`
9. `read_core_register(name="pc")`
10. `read_memory(address="0x08000000", word_size=32)`
11. `resume()`
12. `read_serial(reset_on_open=true)`
13. `unlock_recover(confirm=false)`
14. `unlock_recover(confirm=true)`
15. repeat `unlock_recover(confirm=true)` twice more
16. `read_memory(address="0x08000000", word_size=32)`
17. `disconnect()`
18. reconnect with `connect(board_id="nucleo_l476rg")`
19. `flash_firmware(path="/tmp/r10-missing.elf")` three times
20. `read_memory(address="0x08000000", word_size=32)`
21. `disconnect()`

Expected result:

- `connect(...)` returns a `session_id`
- default and explicit flash succeed for valid baseline artifacts
- `read_serial(...)` reports `UART matched` with expected text `boot ok`
- `unlock_recover(confirm=false)` refuses cleanly
- `unlock_recover(confirm=true)` refuses cleanly because STM32 has no tracked
  recover mode
- after repeated identical recover failures, only `unlock_recover` becomes
  blocked
- after repeated identical missing-file flash attempts, only
  `flash_firmware` becomes blocked
- read-only tools still work after watcher blocks
- disconnect/reconnect clears the block state

Why this is expected:

- the runtime session layer now logs per-session events
- the flash gate only allows real local `.elf` / `.hex` files
- the STM32 board config intentionally defines no recover path
- the watcher only blocks repeated mutation failures inside one session

### 5. Nordic Manual Runtime Validation

Use `connect(board_id="nrf52833dk")` as the primary path.

Run this sequence:

1. `connect(board_id="nrf52833dk")`
2. verify success text contains:
   - `Connected to board`
   - `[board config: nrf52833dk]`
   - `via pyocd-native`
   - `session_id=`
3. verify:
   - `runs/<session_id>/logs/events.jsonl`
   - `runs/<session_id>/run-metadata/session.json`
4. `get_board_info()`
5. `flash_firmware()`
6. `flash_firmware(path="<repo-root>/firmware/nrf52833dk/reference/build/firmware.elf", halt_after_reset=true)`
7. `flash_firmware(path="<repo-root>/firmware/nrf52833dk/reference/build/firmware.hex")`
8. `halt()`
9. `read_core_register(name="pc")`
10. `read_memory(address="0x10000000", word_size=32)`
11. `resume()`
12. `read_serial(reset_on_open=true)`
13. `unlock_recover(confirm=false)`
14. `unlock_recover(confirm=true)`
15. `flash_firmware()`
16. `read_serial(reset_on_open=true)`
17. `disconnect()`

Expected result:

- `connect(...)` returns a `session_id`
- default and explicit flash succeed for valid baseline artifacts
- `read_serial(...)` reports `UART matched` with expected text `boot ok`
- `unlock_recover(confirm=false)` refuses cleanly
- `unlock_recover(confirm=true)` succeeds
- after recover, the baseline can be reflashed and UART can be re-verified

Why this is expected:

- `nrf52833dk` has a tracked recover policy
- its reference baseline is already known-good and recover-safe on the current
  Mac bench

### 6. Nordic UART Watcher Validation

Use a fresh Nordic session:

1. `connect(board_id="nrf52833dk")`
2. `read_serial(expected_text="__never_matches__", reset_on_open=true, read_seconds=3.0)`
3. repeat the same call three more times
4. verify the fourth call is blocked
5. run `get_state()` or `read_memory(address="0x10000000", word_size=32)`
6. `disconnect()`
7. reconnect with `connect(board_id="nrf52833dk")`
8. `read_serial(reset_on_open=true)`
9. `flash_firmware(path="/tmp/r10-guardrail.bin")`
10. `disconnect()`

Before this check, create an invalid flash artifact:

```bash
printf 'not firmware\n' > /tmp/r10-guardrail.bin
```

Expected result:

- the first three bad UART checks produce non-match summaries, not crashes
- the fourth identical UART miss is blocked
- read-only tools still work while UART reads are blocked
- reconnect clears the block state
- `.bin` flashing refuses deterministically

Why this is expected:

- the watcher tracks repeated identical UART misses per session
- the flash guardrail explicitly rejects unsupported suffixes

### 7. Expected Response Shapes

These response shapes are important because the repo now depends on them being
stable and understandable.

`connect(...)` success should contain:

- `Connected to board`
- `[board config: <board_id>]`
- `via pyocd-native`
- `session_id=<id>`

Why expected:

- the runtime layer now creates a named session on successful connect

`flash_firmware(...)` success should look like:

- `Flashed <path> via pyocd-native; target left running.`
- or `Flashed <path> via pyocd-native; target left halted.`

Why expected:

- the wrapper now reports both the artifact identity and the post-flash target
  state

`read_serial(...)` success should look like:

- `UART matched on <port> at <baud> baud via pyocd-native; expected='boot ok'; reopen_count=<n>; duration=<s>; excerpt=<text>`

Why expected:

- the UART service now returns bounded, deterministic capture summaries instead
  of ambiguous empty success

Recover refusal should look like:

- `Refused [<code>]: <message> session_id=<id>`

Watcher block should look like:

- `Blocked [<code>]: <message> session_id=<id>`

Why expected:

- the runtime policy layer distinguishes deliberate refusal from unexpected
  backend failure

## What Should Be Verified Again Before Running The Benchmark Pilot

Before claiming the benchmark phase is working on a host, re-check these exact
things:

- both scoped boards still pass Stage 0 and Stage 1 smoke
  - because the benchmark runner assumes known-good baseline behavior exists
- board-aware auto-selection still chooses the correct probe while both boards
  are attached
  - because the benchmark prompts are supposed to connect by `board_id`, not by
    hard-coded probe UID
- `session_id` creation and `runs/<session_id>/...` logging still happen
  - because benchmark artifacts are keyed off the session directory
- default artifact resolution still points at the tracked baseline per board
  - because the runner and server both depend on that contract
- recover behavior still differs correctly by board
  - `nrf52833dk` should recover
  - `nucleo_l476rg` should refuse
- watcher state still clears on disconnect/reconnect
  - because the benchmark runner assumes each case starts from a clean session

## Benchmark Phase Status

The benchmark phase is implemented in the repo, but it is not yet live-proven.

What is already tracked:

- benchmark spec in `markdowns/r11_benchmark_spec.md`
- case format under `tests/cases/<case_id>/case.yaml`
- Codex result schema under `tests/cases/r11_result_schema.json`
- pilot suite ordering under `tests/cases/suites.yaml`
- tracked known-good, injected-bug, and observability-fault cases
- bug fixture trees under `firmware/<board>/bugs/<id>__<slug>/`
- canonical runner at `tests/harness/r11_benchmark.py`

### Benchmark Runner Commands

Runner prerequisite:

```bash
codex mcp add pyocd-debug -- uv run pyocd-debug-mcp
codex mcp get pyocd-debug
```

Single-case entrypoint:

```bash
uv run python -m tests.harness.r11_benchmark --case-id nucleo_l476rg__k001_reference_green
```

Pilot suite entrypoint:

```bash
uv run python -m tests.harness.r11_benchmark --suite pilot_v1
```

Frozen pilot order:

1. `nucleo_l476rg__k001_reference_green`
2. `nrf52833dk__k001_reference_green`
3. `nucleo_l476rg__b001_wrong_boot_text`
4. `nrf52833dk__b001_wrong_boot_text`
5. `nucleo_l476rg__b002_wrong_known_value`
6. `nrf52833dk__b002_wrong_known_value`
7. `nucleo_l476rg__f001_halted_target_silent_uart`
8. `nrf52833dk__f001_halted_target_silent_uart`

### Local Benchmark Validation Already Completed

These local checks already passed when the benchmark runner landed:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py tests/test_r11_benchmark.py
uv run pytest -q tests/test_r11_benchmark.py
uv run python -m tests.harness.r11_benchmark --help
```

Why those results are expected:

- the benchmark runner, schema validation, workspace isolation, and scoring
  logic already have local test coverage in the repo

### Current Host-Local Blocker

On the current host, the live pilot is still blocked until Codex MCP
registration is present.

Current observed output:

```text
Error: No MCP server named 'pyocd-debug' found.
```

That came from:

```bash
codex mcp get pyocd-debug
```

What should be done next:

```bash
codex mcp add pyocd-debug -- uv run pyocd-debug-mcp
codex mcp get pyocd-debug
```

Expected result after registration:

- `codex mcp get pyocd-debug` reports the registered MCP server config instead
  of the missing-server error

Why this is expected:

- the benchmark runner is intentionally designed to use a pre-registered Codex
  MCP server rather than mutating that registration automatically

## What Still Needs To Be Fully Done

The repo is not waiting on more scoped substrate work. The remaining work is
benchmark and product-validation work.

### Immediate Next Tasks

1. Register the local Codex MCP server on the host that will run the pilot.
2. Re-run the scoped board preflight checks so the pilot starts from a known
   green baseline.
3. Run the two known-good benchmark cases first.
4. Run the four injected code-bug cases.
5. Run the two observability-fault cases.
6. Inspect the captured run artifacts under `runs/<session_id>/...`.
7. Record the real pilot results back into this file and `README.md`.

### What The First Pilot Must Prove

The first live benchmark pass still needs to prove all of the following:

- one MCP session per benchmark case is captured correctly
- benchmark artifacts land in the correct `runs/<session_id>/...` tree
- both known-good cases score as healthy full-success cases
- at least one injected code-bug case per board reaches full success
- the observability-fault cases are diagnosed as runtime/observability problems
  rather than code bugs
- the scoring rubric is understandable on real runs
- the runner’s capture/export path is sufficient for later analysis

### Optional Follow-Up Work After The Pilot

These are real tasks, but they are not the current blocker:

- Windows follow-up for the official `nrf52833dk` bench path
- future live proof for `nrf52840dk` if that alternate profile becomes a real
  support target
- corpus expansion after the first eight-case pilot is trustworthy

## Short Resume Note

If resuming later:

> The scoped pair is `nrf52833dk + nucleo_l476rg`. Everything through the
> runtime/safety layer is implemented and already live-proven on that pair:
> Stage 0, the Stage 1 smoke harness, the current MCP surface, per-session
> logging, flash/recover guardrails, and the mutation watcher. The remaining
> work is the live `Codex CLI` benchmark pilot. The immediate blocker on this
> host is missing Codex MCP registration for `pyocd-debug`, and the next
> concrete steps are `codex mcp add ...`, rerun the scoped preflight, then run
> the frozen eight-case pilot suite.
