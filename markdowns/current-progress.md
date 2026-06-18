# Current Progress

## Current Position

The repo is now in **late reachable `R7` / early `R8` on STM32**:

- the shared SWD substrate exists under
  `src/pyocd_debug_mcp/adapters/` and `src/pyocd_debug_mcp/services/`
- the shared UART substrate now exists too, with an explicit adapter split and
  bounded capture behavior
- `server.py` is thin over the shared target-control services
- `stage0_check.py` now uses the shared SWD and UART services for the delegated
  hardware-control path
- the first tracked Stage 1 smoke harness now exists at
  `tests/harness/stage1_smoke.py` and has passed on the live STM32 board

This is real `R6` completion and substantial `R7` / `R8` progress, but **not**
formal both-board closure:
the official Nordic board is still `nrf52840dk`, and that board still needs the
same Stage 0 and Stage 1 proof before `G1`, full `R7`, and full `R8` can be
called complete.

## What Was Just Proven On STM32

On the live **`nucleo_l476rg`** attached to this Mac host:

- `uv run python host_bootstrap.py --board-id nucleo_l476rg` passed
- `uv run python stage0_check.py --board-id nucleo_l476rg` passed for the
  non-destructive checks
- `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware
  nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf` passed for:
  - probe visibility
  - target availability
  - virtual COM visibility on `/dev/cu.usbmodem143303`
  - SWD connect + read
  - reference firmware flash
  - UART output capture of `boot ok`
- the confirmed STM32 facts on this host are:
  - probe UID: `0668FF514988525067213913`
  - serial port: `/dev/cu.usbmodem143303`
  - pyOCD target: `stm32l476rgtx`
  - pack token: `stm32l476`
- generic ST-Link matching worked **without** `STM32_Programmer_CLI`
- the human operator confirmed that the visible ST-Link probe and the visible
  `/dev/cu.usbmodem143303` COM port came from the same physical
  `nucleo_l476rg` board

## Stage 1 Smoke Status On STM32

The tracked Stage 1 smoke harness now passes on the live STM32 board:

- `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
  - **PASS**

That run proved the shared Stage 1 flow end to end:

- flash the canonical reference artifact through the shared SWD services
- `reset_and_halt`
- read `pc`
- resolve the fixed symbol `stage1_known_value` from
  `firmware/nucleo_l476rg/reference/build/firmware.elf`
- read target memory back at that resolved address and confirm `0x1234ABCD`
- reopen/run-capture through the shared UART service and match `boot ok`

Important implementation findings:

- the direct pyOCD Python-API flash path needed to match `pyocd load`'s
  pre-reset-and-halt sequencing on STM32/ST-Link
- the Stage 1 symbol contract needed to be flash-backed and explicitly retained
  in the reference ELF, otherwise reset-halt proof was not reliable
- the UART smoke-harness path needed to open the serial port first and trigger
  reset on port-open so the boot line was captured deterministically

The STM32 silicon-ID path remains intentionally **unset** in
`boards/nucleo_l476rg.yaml`. That is still by design in this pass: STM32 was
handled as flash-first and smoke-first, not by inventing a new STM32 identity
register contract.

## Shared Layer That Now Exists

New internal code landed under `src/pyocd_debug_mcp/`:

- `adapters/swd_interface.py`
  - internal SWD contract plus `TargetSessionHandle`
- `adapters/swd_pyocd.py`
  - pyOCD-backed implementation
  - board-aware session options
  - J-Link `jlink.non_interactive=false` workaround kept here
  - STM32-safe API flash sequencing now kept here too
- `services/target_control.py`
  - shared session open/close, target state/control, read/write, flash, recover
- `services/uart_capture.py`
  - bounded UART capture
  - expected-substring wait
  - reopen behavior
  - post-flash/post-reset capture coordination
- `adapters/uart_interface.py`
  - backend-neutral low-level UART contract
- `adapters/uart_pyserial.py`
  - pyserial-backed UART implementation
- `reference_artifacts.py`
  - canonical `firmware.elf` / `firmware.hex` artifact-pair resolution
- `services/symbols.py`
  - shared ELF symbol lookup and target-value readback

This means the main Phase A wrappers no longer each own their own pyOCD control
path.

## Wrapper Status

`server.py`

- now delegates its live target-control operations through the shared service
  layer instead of holding direct pyOCD mechanics inline

`stage0_check.py`

- still owns probe enumeration, pack checks, serial listing, CLI reporting, and
  summary generation
- now delegates:
  - connect/read
  - silicon-ID reads
  - flash
  - recover
  - UART capture

That split matches the intended near-term architecture: shared control logic,
wrapper-specific UX.

## Remaining Gaps

Still open before calling the broader milestone complete:

- **official Nordic Stage 0 is still pending**
  - `nrf52840dk` remains the official Nordic board
  - the repo-owned reference package and built artifacts now exist, but the live
    board still needs the full Stage 0 truth path: probe visibility, exact
    silicon identity, flash, UART, recover, and shared-USB confirmation
- **official Nordic scope is still blocked**
  - `nrf52833dk` is useful bench evidence, but it does not replace official
    scope closure
- **official Nordic Stage 1 shared-substrate proof is still pending**
  - the same tracked `tests/harness/stage1_smoke.py` flow now needs to pass on
    `nrf52840dk`
  - until that happens, `R7` and `R8` remain formally open even though the
    shared substrate is already proven on STM32

## Short Scope Reading

As of this file:

- `R6`: implementation-complete and STM32-proven
- `R7`: code-complete enough for both-board use, but formally blocked on the
  official Nordic board proof
- `R8`: first real smoke harness exists and passes on STM32, but is still
  waiting on the same harness run for `nrf52840dk`

## Short Resume Note

If resuming later:

> STM32 Stage 0 truth is green for flash + UART on `nucleo_l476rg`, the shared
> SWD and UART substrates are in place, and the tracked Stage 1 smoke harness at
> `tests/harness/stage1_smoke.py` now passes on STM32. `R6` is effectively
> complete on reachable hardware. The remaining blocker for formal `R7` / `R8`
> closure is still the official Nordic board: rerun Stage 0 and the same Stage 1
> smoke harness on `nrf52840dk`.
