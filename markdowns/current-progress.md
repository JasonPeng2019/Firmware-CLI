# Current Progress

## Current Position

The repo is now in active `R10 / G5` work for the scoped board pair:

- scoped board pair: `nrf52833dk + nucleo_l476rg`
- `R0` through `R5`: effectively closed for the scoped pair
- `R6`: closed
- `R7`: closed for the scoped pair
- `R8`: closed for the scoped pair
- `R9`: closed for the scoped pair
- green gates:
  - `G1` (`R2` + `R3`)
  - `G3` (`R6` + `R7` + `R8`)
  - `G4` (`R9`)
- active frontier:
  - `R10`
  - `G5`

That means the scoped substrate is frozen through `R9`, and the current work
is the first safety/runtime layer on top of that substrate.

`nrf52840dk` is still retained in the repo, but it is now an alternate/future
Nordic profile rather than the official blocker for the current Phase A /
Phase B path.

## `R10 / G5` Status

The implementation source of truth for this pass is
`markdowns/r10_contract.md`.

What has landed so far:

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

What is not yet being claimed:

- `G5` is not yet green
- no `R11+` work has started
- the new safety/runtime behavior still needs its live scoped-pair validation
  before the roadmap can move past `R10`

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

The next meaningful project work is not more Phase A cleanup. It is the
roadmap's `R10` safety/runtime substrate.

## Still Open

Not blockers for the scoped gates, but still real work:

- `nrf52840dk` remains an alternate Nordic profile with repo-owned baseline
  source/build assets and still needs live bench proof if future support for
  that board becomes a goal
- a Windows follow-up for the official `nrf52833dk` bench path would further
  strengthen the new scope decision, even though repo-level `R0` is already
  considered proven

## Short Resume Note

If resuming later:

> The official scoped pair is now `nrf52833dk + nucleo_l476rg`. Both boards are
> green through Stage 0, the tracked Stage 1 smoke harness, and the current MCP
> tool surface. The multi-probe J-Link/ST-Link selection bug is fixed through
> shared `pyocd list --probes` inventory. The next roadmap frontier is `R10`,
> not more scoped Phase A / Phase B bring-up.
