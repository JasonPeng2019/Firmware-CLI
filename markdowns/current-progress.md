# Current Progress

## Current Position

The repo is now green through `R10 / G5` for the scoped board pair:

- scoped board pair: `nrf52833dk + nucleo_l476rg`
- `R0` through `R5`: effectively closed for the scoped pair
- `R6`: closed
- `R7`: closed for the scoped pair
- `R8`: closed for the scoped pair
- `R9`: closed for the scoped pair
- `R10`: closed for the scoped pair
- green gates:
  - `G1` (`R2` + `R3`)
  - `G3` (`R6` + `R7` + `R8`)
  - `G4` (`R9`)
  - `G5` (`R10`)
- active frontier:
  - `R11`
  - `G6`

That means the scoped substrate is now frozen through `R10`, and `R11`
benchmark implementation is underway. The remaining work is to run the live
Codex benchmark pilot and turn the first corpus into real product-validation
evidence.

`nrf52840dk` is still retained in the repo, but it is now an alternate/future
Nordic profile rather than the official blocker for the current Phase A /
Phase B path.

## `R10 / G5` Verification Summary

The implementation source of truth for this pass is
`markdowns/r10_contract.md`.

Verified on `2026-06-18` on the current macOS bench host, using the live
scoped pair and the real `server.py` tool functions in-terminal:

- boards:
  - `nucleo_l476rg`
  - `nrf52833dk`
- session creation:
  - `connect(board_id=..., unique_id=None)` produced visible `session_id=...`
  - `runs/<session_id>/logs/events.jsonl` and
    `runs/<session_id>/run-metadata/session.json` were created
- flash guardrails:
  - default tracked baseline flash succeeded on both boards
  - explicit valid `.elf` succeeded on both boards
  - explicit valid `.hex` succeeded on both boards
  - missing-path flash refused deterministically
  - invalid-suffix `.bin` flash refused deterministically
- recover policy:
  - `nrf52833dk` refused without confirmation, succeeded with
    `confirm=true`, then accepted baseline restore + UART reconfirmation
  - `nucleo_l476rg` refused without confirmation and refused
    deterministically with `confirm=true` because no supported recover mode is
    tracked
- mutation watchers:
  - repeated identical flash failures blocked only `flash_firmware`
  - repeated identical UART misses blocked only `read_serial`
  - repeated identical recover failures blocked only `unlock_recover`
  - read-only tools still worked after the block
  - `disconnect()` then new `connect()` cleared block state

What landed in code and was then live-proven:

- `R10b` runtime substrate:
  - single active runtime session model
  - generated `session_id` on successful `connect`
  - append-only JSONL events under `runs/<session_id>/logs/events.jsonl`
  - per-session metadata under `runs/<session_id>/run-metadata/session.json`
  - structured event fields for tool name, board, probe, route, normalized
    args, outcome kind, error/refusal code, and duration
- `R10a` shared guardrails:
  - shared flash gate for local existing `.elf` / `.hex` artifacts only
  - shared recover gate for confirmation, tracked recover-mode support, and
    one-success-per-session policy
  - the same flash/recover policy is now callable from `server.py` and
    `stage0_check.py`
- `R10c` first watcher pass:
  - structured-event-based mutation watcher
  - repeated flash failures block only `flash_firmware`
  - repeated UART misses block only `read_serial`
  - repeated recover failures block only `unlock_recover`
  - block state clears when the session ends and a new session starts

## Manual `R10 / G5` Validation Checklist

Status: verified on `2026-06-18` on the current macOS host via real
`server.py` tool-function calls. Keep this checklist as the rerun procedure for
future benches and regressions.

Use this checklist exactly when re-validating `R10 / G5` on a future host or
after a regression fix.

### Preflight from repo root

Run these first and stop if any fail:

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
printf 'not firmware\n' > /tmp/r10-guardrail.bin
```

Known bench facts for reruns only, not as the primary selection path:

- `nucleo_l476rg`
  - probe UID: `0668FF514988525067213913`
  - serial port: `/dev/cu.usbmodem144403`
- `nrf52833dk`
  - probe UID: `685400693`
  - serial port: `/dev/cu.usbmodem0006854006931`

### Inspector launch

Run:

```bash
uv run mcp dev src/pyocd_debug_mcp/server.py
```

Use `connect(board_id=..., unique_id=None)` as the primary validation path.
Only pass `unique_id` for debugging reruns.

### STM32 session: safe path + recover-policy + flash watcher

1. `connect(board_id="nucleo_l476rg")`
2. Verify success text contains:
   - `Connected to board`
   - `[board config: nucleo_l476rg]`
   - `via pyocd-native`
   - `session_id=`
3. Extract `session_id` and verify:
   - `runs/<session_id>/logs/events.jsonl`
   - `runs/<session_id>/run-metadata/session.json`
4. `get_board_info()`
5. `flash_firmware()`
   - expect `Flashed ... via pyocd-native; target left running.`
6. `flash_firmware(path="<repo-root>/firmware/nucleo_l476rg/reference/build/firmware.elf", halt_after_reset=true)`
   - expect `target left halted`
7. `flash_firmware(path="<repo-root>/firmware/nucleo_l476rg/reference/build/firmware.hex")`
   - expect success
8. `halt()`
9. `read_core_register(name="pc")`
10. `read_memory(address="0x08000000", word_size=32)`
11. `resume()`
12. `read_serial(reset_on_open=true)`
   - expect `UART matched ... expected='boot ok'`
13. `unlock_recover(confirm=false)`
   - expect `Refused [recover/confirmation-required]: ... session_id=<id>`
14. `unlock_recover(confirm=true)`
   - expect deterministic refusal with code `recover/unsupported-mode`
15. `unlock_recover(confirm=true)` again
   - expect the same deterministic refusal
16. `unlock_recover(confirm=true)` a third time
   - expect `Blocked [watch/recover-repetition]: ... session_id=<same id>`
17. `read_memory(address="0x08000000", word_size=32)`
   - must still work
18. `disconnect()`
19. New session: `connect(board_id="nucleo_l476rg")`
   - verify a new `session_id`
20. `flash_firmware(path="/tmp/r10-missing.elf")`
   - expect refusal with code `flash/missing-file`
21. `flash_firmware(path="/tmp/r10-missing.elf")` again
   - expect the same refusal
22. `flash_firmware(path="/tmp/r10-missing.elf")` a third time
   - expect `Blocked [watch/flash-repetition]: ...`
23. `read_memory(address="0x08000000", word_size=32)`
   - must still work
24. `disconnect()`

### Nordic session: safe path + real recover

1. `connect(board_id="nrf52833dk")`
2. Verify success text contains:
   - `Connected to board`
   - `[board config: nrf52833dk]`
   - `via pyocd-native`
   - `session_id=`
3. Verify:
   - `runs/<session_id>/logs/events.jsonl`
   - `runs/<session_id>/run-metadata/session.json`
4. `get_board_info()`
5. `flash_firmware()`
   - expect default tracked baseline success
6. `flash_firmware(path="<repo-root>/firmware/nrf52833dk/reference/build/firmware.elf", halt_after_reset=true)`
   - expect `target left halted`
7. `flash_firmware(path="<repo-root>/firmware/nrf52833dk/reference/build/firmware.hex")`
   - expect success
8. `halt()`
9. `read_core_register(name="pc")`
10. `read_memory(address="0x10000000", word_size=32)`
11. `resume()`
12. `read_serial(reset_on_open=true)`
   - expect `UART matched ... expected='boot ok'`
13. `unlock_recover(confirm=false)`
   - expect `Refused [recover/confirmation-required]: ... session_id=<id>`
14. `unlock_recover(confirm=true)`
   - expect `Recover completed via ... on nrf52833dk via pyocd-native.`
15. `flash_firmware()`
   - restore the baseline immediately after recover
16. `read_serial(reset_on_open=true)`
   - reconfirm `boot ok`
17. `disconnect()`

### Nordic session: UART watcher

1. `connect(board_id="nrf52833dk")`
2. `read_serial(expected_text="__never_matches__", reset_on_open=true, read_seconds=3.0)`
   - expect a non-match summary, not a crash
3. Repeat the same call a second time
   - expect the same non-match summary
4. Repeat the same call a third time
   - expect the same non-match summary and watcher state to be armed
5. Repeat the same call a fourth time
   - expect `Blocked [watch/uart-miss-repetition]: ...`
6. `get_state()` or `read_memory(address="0x10000000", word_size=32)`
   - must still work
7. `disconnect()`
8. New session: `connect(board_id="nrf52833dk")`
   - verify a new `session_id`
9. `read_serial(reset_on_open=true)`
   - must succeed again
10. `flash_firmware(path="/tmp/r10-guardrail.bin")`
    - expect refusal with code `flash/unsupported-suffix`
11. `disconnect()`

### Expected response shapes

- `connect(...)`
  - contains `Connected to board`
  - contains `[board config: <board_id>]`
  - contains `via pyocd-native`
  - contains `session_id=<id>`
- `flash_firmware(...)` success
  - `Flashed <path> via pyocd-native; target left running.`
  - or `Flashed <path> via pyocd-native; target left halted.`
- `read_serial(...)` success
  - `UART matched on <port> at <baud> baud via pyocd-native; expected='boot ok'; reopen_count=<n>; duration=<s>; excerpt=<text>`
- `unlock_recover(...)` refusal
  - `Refused [<code>]: <message> session_id=<id>`
- watcher block
  - `Blocked [<code>]: <message> session_id=<id>`

### Promotion rule

If any live check fails:

- keep `R10 / G5` in progress
- record:
  - failing step
  - board id
  - observed response
  - expected response
- fix only the minimal code needed to match `markdowns/r10_contract.md`
- rerun the full affected board session plus one clean sanity pass on the other board

## What Changed In This Pass

Two important repo issues were closed before the live proof reruns:

- the shared probe-selection path no longer relies on unsupported
  `pyocd list --output json`
- a new shared helper inventories probes via supported
  `pyocd list --probes`, preserves real probe UIDs, and applies board-aware
  selection consistently in:
  - `host_bootstrap.py`
  - `stage0_check.py`
  - `tests.harness.stage1_smoke`
  - `server.connect(...)`

This was necessary because with both boards attached, the old lossy probe
parsing could drop the J-Link UID and open the wrong probe for the Nordic
board.

The shared pyOCD backend also now carries one board-aware STM32 host quirk that
was proven on this Mac bench:

- `nucleo_l476rg` opens reliably with:
  - `connect_mode=under-reset`
  - `frequency=1000000`

Without that, direct ST-Link attach could fail with the pyOCD / ST-Link
`DP wait` error on this host even though the target was physically present.

## Live Bench Facts — Scoped Pair

### `nucleo_l476rg`

Confirmed on the current Mac bench:

- probe UID: `0668FF514988525067213913`
- serial port: `/dev/cu.usbmodem144403`
- pyOCD target: `stm32l476rgtx`
- pack token: `stm32l476`
- probe and COM port were confirmed to come from the same physical board

Live proofs now completed:

- `uv run python host_bootstrap.py --board-id nucleo_l476rg`
- `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg`
- `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`

Those runs prove:

- probe visibility
- target availability
- SWD connect/read
- flash of the tracked reference baseline
- UART `boot ok`
- Stage 1 symbol-resolution readback of `stage1_known_value = 0x1234ABCD`

### `nrf52833dk`

Confirmed on the current Mac bench:

- probe UID: `685400693`
- serial port: `/dev/cu.usbmodem0006854006931`
- pyOCD target: `nrf52833`
- pack token: `nrf52833`
- silicon identity:
  - address `0x10000100`
  - expected `0x00052833`
  - matched on live hardware
- probe and COM port were confirmed to come from the same physical board

Live proofs now completed:

- `./firmware/nrf52833dk/reference/build_reference.sh`
- `uv run python host_bootstrap.py --board-id nrf52833dk`
- `uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk`
- `uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk`

Those runs prove:

- probe visibility
- target availability
- SWD connect/read
- exact silicon identity
- flash of the tracked reference baseline
- UART `boot ok`
- recover / unlock
- post-recover reachability
- Stage 1 symbol-resolution readback of `stage1_known_value = 0x1234ABCD`

## Shared Substrate Status

The shared substrate that now exists under `src/pyocd_debug_mcp/` is real and
live-proven on the scoped pair:

- `adapters/swd_interface.py`
- `adapters/swd_pyocd.py`
- `adapters/uart_interface.py`
- `adapters/uart_pyserial.py`
- `services/target_control.py`
- `services/uart_capture.py`
- `services/symbols.py`
- `reference_artifacts.py`
- `probe_inventory.py`

This means the main wrappers no longer each own their own disconnected
hardware-control path.

## Stage 1 / `R8` Status

The tracked Stage 1 harness at `tests/harness/stage1_smoke.py` now passes on
both scoped boards.

It proves one repeatable shared-service flow:

1. load board config
2. resolve artifact pair
3. resolve the correct serial port
4. open the correct probe/session
5. flash the reference artifact
6. `reset_and_halt`
7. read `pc`
8. resolve `stage1_known_value` from the ELF
9. read back `0x1234ABCD` from target memory
10. reset/run
11. capture UART until `boot ok`

That closes the scoped `R8` proof requirement.

## MCP Surface / `R9` Status

The current live MCP tool surface has now been exercised against both scoped
boards through the real `server.py` tool functions while both probes were
attached.

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

Important live behavior that is now proven:

- `connect(board_id=..., unique_id=None)` auto-selects the correct probe for
  both boards while both probes are attached
- default flash artifact resolution works on both boards
- explicit flash artifact override works on both boards
- default serial resolution works on both boards
- explicit serial override works on both boards
- Nordic recover succeeds and the baseline can be restored immediately after
  the erase
- STM32 recover refuses cleanly when `confirm=False` and fails deterministically
  when `confirm=True` because the tracked board has no recover mode
- post-disconnect not-connected behavior is deterministic

That is enough to treat scoped `R9` / `G4` as green.

## Scope Reading

For the scoped board pair:

- `R0`: closed
- `R1`: closed
- `R2`: closed on `nucleo_l476rg`
- `R3`: closed on `nrf52833dk`
- `R4`: closed for the scoped pair
- `R5`: closed enough for the current shared-loader architecture
- `R6`: closed
- `R7`: closed for the scoped pair
- `R8`: closed for the scoped pair
- `R9`: closed for the scoped pair
- `R10`: closed for the scoped pair

The next meaningful project work is the live `R11` benchmark pilot over the
now-tracked spec, corpus, and runner.

## `R11` Benchmark Implementation Status

The implementation source of truth for this phase is
`markdowns/r11_benchmark_spec.md`.

What is now tracked in-repo:

- frozen case contract under `tests/cases/<case_id>/case.yaml`
- frozen Codex result schema under `tests/cases/r11_result_schema.json`
- frozen pilot suite ordering under `tests/cases/suites.yaml`
- first corpus:
  - 2 known-good cases
  - 4 injected code-bug cases
  - 2 host-induced observability-fault cases
- tracked bug fixtures under `firmware/<board>/bugs/<id>__<slug>/`
- canonical runner at `tests/harness/r11_benchmark.py`

Runner prerequisites:

```bash
codex mcp add pyocd-debug -- uv run pyocd-debug-mcp
codex mcp get pyocd-debug
```

Runner entrypoints:

```bash
uv run python -m tests.harness.r11_benchmark --case-id nucleo_l476rg__k001_reference_green
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

Implementation validation completed locally:

- `uv run pytest -q` passed with the full repo test suite green
- `uv run ruff check .` passed
- `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py tests/test_r11_benchmark.py`
  passed
- `uv run pytest -q tests/test_r11_benchmark.py` passed
- `uv run python -m tests.harness.r11_benchmark --help` passed

Current live-pilot blocker on this host:

- `codex mcp get pyocd-debug` still reports no registered MCP server named
  `pyocd-debug`
- live `R11` pilot runs remain pending until this prerequisite is completed:

```bash
codex mcp add pyocd-debug -- uv run pyocd-debug-mcp
codex mcp get pyocd-debug
```

## Still Open

Not blockers for the scoped gates, but still real work:

- `nrf52840dk` remains an alternate Nordic profile with repo-owned baseline
  source/build assets and still needs live bench proof if future support for
  that board becomes a goal
- a Windows follow-up for the official `nrf52833dk` bench path would further
  strengthen the new scope decision, even though repo-level `R0` is already
  considered proven
- `R11` implementation has started, but no live Codex pilot results are being
  claimed yet in this pass
- the first live benchmark run still needs to prove:
  - one-session-per-case capture works under real `codex exec`
  - benchmark artifacts land correctly under `runs/<session_id>/...`
  - the pilot scoring/rubric is interpretable on real outcomes

## Short Resume Note

If resuming later:

> The official scoped pair is now `nrf52833dk + nucleo_l476rg`. Both boards are
> green through Stage 0, the tracked Stage 1 smoke harness, and the current MCP
> tool surface. The multi-probe J-Link/ST-Link selection bug is fixed through
> shared `pyocd list --probes` inventory. `R11` benchmark implementation is now
> in the repo through the frozen case format, first corpus, Codex result
> schema, and `tests/harness/r11_benchmark.py`. The next meaningful step is the
> live Codex pilot, not more scoped bring-up work.
