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

In roadmap terms, all scoped work through `R11` is complete on the official
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
- the first Codex-driven benchmark pilot

`R12` is now implemented in code, but it is not yet live-proven. The repo now
contains:

- the native Python brain package under `src/pyocd_debug_mcp/brain/`
- the top-level `skills/` tree
- the `pyocd-debug-brain` CLI
- the sibling turnkey benchmark path over the same 12-case corpus
- the frozen `R12` contract in `markdowns/curr/r12_turnkey_spec.md`

What is still missing is the live turnkey validation on the scoped pair and the
acceptance run over the same 12-case benchmark corpus.

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
- the shared SWD adapter now carries the J-Link serial-open quirk handling in
  one place:
  - always set pyOCD `jlink.non_interactive=false` for J-Link boards
  - if J-Link open-by-UID still fails with the known
    `No emulator with serial number ... found` error and exactly one matching
    probe is visible, retry the session open once without forcing the UID
- the MCP stdio path on this Windows host must not pre-run
  `pyocd list --probes` to auto-resolve an implicit J-Link UID before the real
  attach:
  - when `connect()` is called for a J-Link board without an explicit
    `unique_id` / `PYOCD_PROBE_UID`, the server now passes `unique_id=None`
    through to the shared backend and lets pyOCD choose the single attached
    probe directly
- the shared path is used by:
  - `host_bootstrap.py`
  - `stage0_check.py`
  - `tests.harness.stage1_smoke`
  - `server.connect(...)`

Rule for future files:

- do **not** call `ConnectHelper` directly from new wrappers, harnesses, or
  scripts
- always go through the shared `target_control.open_session()` /
  `adapters.swd_pyocd` path so probe-family-specific fixes such as the J-Link
  option policy and the guarded uidless retry stay centralized

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

### Turnkey Brain (`R12`) Implementation

The first turnkey product layer is now implemented in the repo.

Code that now exists:

- `src/pyocd_debug_mcp/brain/config.py`
- `src/pyocd_debug_mcp/brain/mcp_client.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/workspace.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/benchmark.py`
- `src/pyocd_debug_mcp/brain/cli.py`
- `tests/harness/r12_turnkey_benchmark.py`
- `skills/common/...`
- `skills/mcu_families/nrf52833/...`
- `skills/mcu_families/stm32l476/...`

What that code does:

- launches the existing MCP server as a local stdio subprocess
- talks to it directly without Codex CLI or manual MCP registration
- loads BYOK provider config from `OPENAI_API_KEY` and `PYOCD_TURNKEY_MODEL`
- selects board-aware YAML skills
- keeps local turnkey run state
- supports freeform `run` mode and benchmark mode
- captures turnkey artifacts into the same `runs/<session_id>/...` tree
- reuses the existing 12-case benchmark corpus instead of inventing a second
  benchmark taxonomy

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
a substrate change, before rerunning the benchmark suite, or before claiming
that new higher-level work is being run on a known-good foundation.

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
- `read_serial(expected_text="boot ok", ...)` reports `UART matched` with
  expected text `boot ok`
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
- `read_serial(expected_text="boot ok", ...)` reports `UART matched` with
  expected text `boot ok`
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

- `UART matched on <port> at <baud> baud via pyocd-native; expected=(none); reopen_count=<n>; duration=<s>; excerpt=<text>`
- or, when an explicit substring is requested:
  `UART matched on <port> at <baud> baud via pyocd-native; expected='boot ok'; reopen_count=<n>; duration=<s>; excerpt=<text>`

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

## What Should Be Verified Again Before Rerunning The Benchmark Suite

Before rerunning the benchmark suite on a host, or before starting the next
turnkey-product layer on top of this substrate, re-check these exact things:

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

The benchmark phase is implemented in the repo and is now live-proven on the
current mixed-board Mac host.

What is already tracked:

- benchmark spec in `markdowns/curr/r11_benchmark_spec.md`
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

### Live Benchmark Validation Already Completed

The following live benchmark commands were completed successfully on the current
Mac host after Codex MCP registration was added:

```bash
codex mcp add pyocd-debug -- uv run pyocd-debug-mcp
codex mcp get pyocd-debug

uv run python -m tests.harness.r11_benchmark --case-id nrf52833dk__k001_reference_green
uv run python -m tests.harness.r11_benchmark --case-id nrf52833dk__f001_halted_target_silent_uart
uv run python -m tests.harness.r11_benchmark --suite pilot_v1

uv run python -m tests.harness.r11_benchmark --case-id nucleo_l476rg__b003_silent_uart
uv run python -m tests.harness.r11_benchmark --case-id nrf52833dk__b003_silent_uart
uv run python -m tests.harness.r11_benchmark --case-id nucleo_l476rg__b004_dual_signal_regression
uv run python -m tests.harness.r11_benchmark --case-id nrf52833dk__b004_dual_signal_regression
```

Observed benchmark result:

- `nucleo_l476rg__k001_reference_green`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__k001_reference_green`: `FULL_SUCCESS`, score `100`
- `nucleo_l476rg__b001_wrong_boot_text`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__b001_wrong_boot_text`: `FULL_SUCCESS`, score `100`
- `nucleo_l476rg__b002_wrong_known_value`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__b002_wrong_known_value`: `FULL_SUCCESS`, score `100`
- `nucleo_l476rg__f001_halted_target_silent_uart`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__f001_halted_target_silent_uart`: `FULL_SUCCESS`, score `100`
- suite summary: `full_success=8`, `partial_success=0`, `fail=0`,
  `average_score=100.0`
- `nucleo_l476rg__b003_silent_uart`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__b003_silent_uart`: `FULL_SUCCESS`, score `100`
- `nucleo_l476rg__b004_dual_signal_regression`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__b004_dual_signal_regression`: `FULL_SUCCESS`, score `100`

What that means:

- the frozen eight-case pilot passed end to end on the scoped pair
- the final minimal pre-wrap-up `R11` expansion landed without widening the
  runner contract, scoring rubric, result schema, or MCP surface
- the repo now distinguishes two superficially similar UART-miss diagnoses:
  - `f001_halted_target_silent_uart`: runtime/observability fault
  - `b003_silent_uart`: firmware code bug
- the repo now also exercises a combined two-symptom code repair path through
  `b004_dual_signal_regression`
- the current MCP surface was usable by a real external agent client
- the scoring rubric produced clean full-success outcomes on known-good,
  injected-bug, and observability-fault cases
- the benchmark runner captured complete run artifacts under
  `runs/<session_id>/...`
- board-aware `connect(board_id=...)` worked on the mixed-board host for both
  the STM32 and Nordic cases

## Turnkey Brain Status

The turnkey layer is now in the repo, but it is still awaiting live proof on
the scoped pair.

### Turnkey Commands

Set BYOK config first:

```bash
export OPENAI_API_KEY=...
export PYOCD_TURNKEY_MODEL=...
```

Or put those same values in the local gitignored `.env`.

Freeform verify/diagnose runs:

```bash
uv run pyocd-debug-brain run --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
```

Single-case turnkey benchmark runs:

```bash
uv run pyocd-debug-brain benchmark --case-id nucleo_l476rg__k001_reference_green --model <model>
uv run pyocd-debug-brain benchmark --case-id nrf52833dk__k001_reference_green --model <model>
uv run pyocd-debug-brain benchmark --case-id nucleo_l476rg__b003_silent_uart --model <model>
uv run pyocd-debug-brain benchmark --case-id nrf52833dk__f001_halted_target_silent_uart --model <model>
```

Full turnkey benchmark roll-up:

```bash
uv run pyocd-debug-brain benchmark --suite pilot_v1_plus_b003_b004 --model <model>
```

### What Should Be Verified In The First Live Turnkey Pass

For both `nucleo_l476rg` and `nrf52833dk`, verify:

- `pyocd-debug-brain run` creates a real `session_id`
- the CLI creates:
  - `runs/<session_id>/run-metadata/turnkey_request.json`
  - `runs/<session_id>/run-metadata/turnkey_result.json`
  - `runs/<session_id>/run-metadata/turnkey_state.json`
  - `runs/<session_id>/logs/brain_trace.jsonl`
  - `runs/<session_id>/logs/model_turns.jsonl`
  - `runs/<session_id>/logs/prompt.txt`
  - `runs/<session_id>/applied-patches/turnkey.diff`
- the normal path uses `connect(board_id=...)` with no hard-coded probe UID
- the normal path does not require an explicit serial port override
- healthy freeform runs can explain why the board is healthy rather than merely
  saying it is healthy

For the turnkey benchmark path, verify:

- the same 12 benchmark cases are reused
- each case runs from one turnkey CLI command
- no Codex CLI dependency exists in the turnkey path
- no manual `codex mcp add ...` step is needed
- known-good cases still reach full success
- observability-fault cases still diagnose non-code/runtime-state problems
- at least 6 of the 8 injected-bug cases reach full success
- no case scores below 50
- suite average is at least 85
- no forbidden recover usage appears on non-recover cases
- no case watcher-blocks because the turnkey loop thrashes

### Why Those Checks Matter

These are the core product claims for the first turnkey layer:

- parity on the same benchmark corpus that already proved the BYO-agent path
- lower operator/setup burden than the Codex-driven path
- no reliance on prompt authoring, Codex installation, or MCP registration
- no reopening of the underlying server/substrate architecture

Important runner-accounting outcome:

- the benchmark runner no longer requires exactly one MCP session directory per
  case
- the final structured `session_id` returned by Codex is the canonical case
  root
- extra MCP sessions are treated as runner warnings rather than automatic
  benchmark failures
- this change was necessary because real Codex behavior can include a short
  scouting session before the final successful verification session

Important hardening outcome from the expansion:

- the added `b004` cases exposed a real benchmark trust bug:
  the runner previously allowed agent self-reported green verification to
  override a failing runner-owned final verification
- this is now fixed:
  runner-owned final verification is authoritative for scoring and outcome
  classification
- the mirrored `b004` bug fixtures were also tightened to preserve the stable
  Stage 1 symbol-access pattern, so the intended repair is “restore the wrong
  contract values” rather than “invent a new symbol-storage scheme”

Canonical roll-up command for the expanded corpus:

```bash
uv run python -m tests.harness.r11_benchmark --suite pilot_v1_plus_b003_b004
```

What to expect from that roll-up:

- `pilot_v1` remains frozen as the original eight-case milestone
- the four new expansion cases append after the original eight
- the most important new proof is already established by the four successful
  individual runs above; the aggregate suite simply replays the same corpus in
  one command

## What Still Needs To Be Fully Done

The scoped hardware-control substrate is not the blocker anymore. The remaining
work is all in the turnkey product layer.

### Immediate Next Tasks

1. Run the first live turnkey freeform verify/diagnose pass on:
   - `nucleo_l476rg`
   - `nrf52833dk`
2. Confirm the turnkey run artifacts are written correctly into
   `runs/<session_id>/...`.
3. Run the first turnkey benchmark pilot on the frozen 12-case corpus:
   - start with one known-good case per board
   - then one bug case per board
   - then one observability-fault case per board
   - then the full `pilot_v1_plus_b003_b004` suite
4. Record the observed turnkey benchmark results back into this file and
   `README.md`.
5. Compare turnkey results against the already-proven `R11` results:
   - benchmark outcome parity
   - lower operator burden
   - no hidden Codex/MCP registration dependency
6. If the live turnkey pass exposes real gaps:
   - fix the turnkey loop, skill set, prompt bundle, or benchmark wrapper
   - do not expand the benchmark corpus again before turnkey reliability is
     stable

### What `R11` Already Proved

The first live benchmark pass has already proved all of the following:

- benchmark artifacts land in the correct `runs/<session_id>/...` tree
- both known-good cases score as healthy full-success cases
- both injected code-bug families reached full success on both boards
- the added `b003_silent_uart` family proves the agent can distinguish “missing
  application success UART because the target is halted” from “missing
  application success UART because the firmware is wrong”
- the added `b004_dual_signal_regression` family proves the agent can repair a
  combined UART-plus-symbol regression while still staying inside the one-file
  benchmark workspace contract
- both observability-fault cases were diagnosed as runtime/observability problems
  rather than code bugs
- the scoring rubric is understandable on real runs
- the runner’s capture/export path is sufficient for later analysis
- extra MCP sessions can occur in real Codex runs without invalidating the
  benchmark result, as long as the final structured `session_id` maps cleanly
  to a real run directory

### Optional Follow-Up Work After The Turnkey Pass

These are real tasks, but they are not the current blocker:

- Windows follow-up for the official `nrf52833dk` bench path
- future live proof for `nrf52840dk` if that alternate profile becomes a real
  support target
- further corpus expansion after the current twelve-case set is trustworthy

## nRF52840 Bench-Check Prerequisites

Before bench-checking `nrf52840dk`, do the following. These exist because the
52840 has no committed reference artifact yet and because the toolchain choice
must match what the agent will use when it rebuilds firmware.

1. **Install NCS (nRF/Nordic only).** Install **nRF Connect SDK (NCS)** via the
   nRF Connect for VS Code extension (Toolchain Manager). The GUI/IDE is only the
   installer — builds run from `west` / the board build script afterward, so the
   IDE is not otherwise needed. What you actually need is the **NCS workspace**
   (the `zephyr/`, `nrf/`, `nrfxlib/` repos) plus a Zephyr SDK toolchain.
2. **NCS is Nordic-only.** This applies to `nrf52840dk` (and other nRF boards),
   **not** to the STM32 `nucleo_l476rg`, which stays on upstream Zephyr.
3. **Why NCS.** It is the common production path for nRF (and required for the
   SoftDevice Controller / Nordic BLE mesh later), and the agent rebuilds firmware
   with whatever toolchain the board's build script targets — so testing on NCS
   keeps your build and the agent's rebuild on the same toolchain. (A plain
   upstream-Zephyr build also works for the trivial reference app, but standardize
   on one toolchain per board.)
4. **Produce a real 52840 reference artifact (cannot be downloaded).** The
   `stage1_smoke` contract needs the firmware to print `boot ok` and expose
   `stage1_known_value = 0x1234ABCD`; no prebuilt hex satisfies that. Create
   `firmware/nrf52840dk/reference/` mirroring `firmware/nrf52833dk/reference/`
   (`src/` + a `build_reference.sh` with `BOARD=nrf52840dk/nrf52840`), then build
   it to `firmware/nrf52840dk/reference/build/firmware.{elf,hex}`.
5. **Point the build at the NCS workspace with env vars, not code edits.** The
   existing `build_*.sh` is already `west build` against `$WORKSPACE_DIR`:
   - `ZEPHYR_WORKSPACE_DIR=<NCS workspace root>` — the directory that **contains**
     `zephyr/`, `nrf/`, `nrfxlib/`, `.west/` (e.g. `~/ncs/<version>`), **not** the
     inner `zephyr/` folder (pointing at the inner one loses the Nordic modules).
   - `ZEPHYR_SDK_INSTALL_DIR=<NCS's bundled Zephyr SDK>` — set explicitly, because
     the script's auto-detect only finds a standalone `zephyr-sdk-*`.
   - If `west` complains about a version mismatch against the NCS manifest, use
     NCS's own `west` instead of the script's pip-installed one.
6. **Keep provenance consistent.** If you standardize nRF builds on NCS, rebuild
   and re-verify the existing `nrf52833dk` baseline under NCS too, so committed
   artifacts match what the agent rebuilds. Do not leave `nrf52833dk`
   upstream-Zephyr-built while `nrf52840dk` is NCS-built (functionally equivalent
   for these printk apps, but keep provenance consistent). Record the 52840
   artifact's toolchain provenance in the "Live Bench Facts" section once proven.
7. **Then run the standard validation** with `--board-id nrf52840dk`:
   `host_bootstrap.py` → `stage0_check.py` (with `--reference-firmware` and, since
   it is Nordic, `--recover-test`) → `tests.harness.stage1_smoke` → the MCP server
   runtime/manual matrix. Note the host it was proven on (if it is this Windows
   host, that also advances the open Windows-bench follow-up).

## Short Resume Note

If resuming later:

> The scoped pair is `nrf52833dk + nucleo_l476rg`. Everything through the
> full `R11` benchmark layer is already implemented and live-proven on that
> pair: Stage 0, the Stage 1 smoke harness, the current MCP surface,
> per-session logging, flash/recover guardrails, the mutation watcher, and the
> frozen 12-case Codex benchmark corpus. `R12` is now implemented in code as
> a native Python turnkey brain plus `pyocd-debug-brain`, but it still needs
> live freeform and benchmark validation on the same scoped pair.
