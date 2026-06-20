# Current Progress

## Current Position

The repo is currently at **Step 1.0d / early `R7`**:

- the `server.py` pyOCD **Python API** path has now been validated on a real
  **`nrf52840dk`** for the subset it already implements
- `server.py` was patched so J-Link boards inherit the same
  `jlink.non_interactive=false` workaround already used by `stage0_check.py`
- the current MCP server surface is now proven for:
  - `connect`
  - `get_board_info`
  - `get_state`
  - `read_memory`
  - `read_core_register`
  - `halt`
  - `resume`
  - `reset`
  - `step`
  - `disconnect`

This means the current `server.py` API path is no longer just theoretical on
Nordic/J-Link hardware for the operations above.

## What Was Just Proven

On a real **`nrf52840dk`** board:

- MCP Inspector connection worked
- `board_id=nrf52840dk` loaded the tracked board config correctly
- J-Link open-by-serial succeeded after carrying over the Stage 0 workaround
- memory reads worked, including:
  - `0x10000000`
  - `0x10000100` (`FICR.INFO.PART`)
- core control worked:
  - halt
  - resume
  - reset
  - step
  - register reads

## Harness Results — Bench-Confirmed (nrf52840dk)

The throwaway API harness (`scratch/api_target_control_harness.py`) was run on the
real **`nrf52840dk`** and **passed** for all three operations:

- pyOCD Python-API **silicon-ID read** — ✅ PASS (`FICR.INFO.PART` = `0x00052840`,
  matching board config and oracle'd against `stage0_check.py`)
- pyOCD Python-API **recover / unlock** — ✅ PASS (mass-erase via the API, with a
  successful post-erase re-read)
- pyOCD Python-API **flash** — ✅ PASS (programmed `firmware/nrf52840dk/reference/build/firmware.elf`
  via `FileProgrammer`; confirmed running correctly afterward, not just written —
  see "Flash Validated" below)

This proves the pyOCD **Python-API** path does what `stage0_check.py`'s subprocess
path does for silicon-ID, recover, and flash on Nordic/J-Link hardware. All three
target-control operations not yet in `server.py` are now bench-proven on this
probe family.

## Flash Validated (nrf52840dk) — exact steps run

The `nrf52840dk` on the bench turned out to already have flash artifacts
(`firmware/nrf52840dk/reference/build/firmware.{elf,bin}`, plus source under
`firmware/nrf52840dk/reference/src/`: an LED-chase + UART blink firmware with no
SDK/RTOS), so the "Bench gap to resolve before flashing Nordic" noted below was
already closed — no new firmware had to be built.

1. **Confirmed board identity.** `pyocd list` reported the probe as
   `Segger J-Link OB-nRF5340-NordicSemi`, which looked like a mismatch against the
   physical `nRF52840-DK` on the bench. Confirmed with the operator that the
   physical board is genuinely the `nRF52840-DK` — the OB-firmware string is just a
   stale/generic label, not the actual silicon. (Worth remembering: don't trust the
   J-Link OB label over the operator's physical board ID.)

2. **First oracle attempt failed — probe already open.**
   ```
   uv run python stage0_check.py --board-id nrf52840dk \
     --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf
   ```
   Failed with `J-Link is already open.` — caused by a leftover MCP Inspector
   session (`mcp dev src/pyocd_debug_mcp/server.py`) and a stray
   `mcp run src/pyocd_debug_mcp/server.py` process from earlier manual testing,
   both still holding the probe open via an un-`disconnect`-ed session. Killed both
   process groups to free the probe. **Lesson:** an MCP client that calls `connect`
   and never calls `disconnect` (or a crashed/abandoned Inspector tab) will block
   any other tool — including `stage0_check.py` — from opening the same probe.

3. **Re-ran the oracle — surfaced APPROTECT.**
   ```
   uv run python stage0_check.py --board-id nrf52840dk \
     --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf \
     --port nrf52840dk=/dev/cu.usbmodem0010502864801 \
     --expect nrf52840dk="blink firmware starting"
   ```
   This time it ran cleanly but failed on connect/silicon-ID with:
   `NRF52840 APPROTECT enabled: not automatically unlocking`. This is the same
   root cause behind the earlier `"No cores were discovered!"` error seen from MCP
   Inspector's `connect` tool on this chip — the debug AP was locked, not a wiring
   or workaround problem.

4. **Recover/unlock via the API harness (destructive — confirmed with the operator
   first, since it mass-erases).**
   ```
   uv run python scratch/api_target_control_harness.py --board-id nrf52840dk \
     --recover --confirm-recover
   ```
   Result: `[PASS] Mass erase completed.` and
   `[PASS] Re-read after erase OK: 0x52840 @0x10000100` — the chip was unlocked and
   immediately readable again.

5. **Silicon-ID + flash via the API harness.**
   ```
   uv run python scratch/api_target_control_harness.py --board-id nrf52840dk \
     --silicon-id --flash --firmware firmware/nrf52840dk/reference/build/firmware.elf
   ```
   Result: `[PASS] silicon-id`, `[PASS] flash`. The harness's `do_flash` leaves the
   core **reset-and-halted** after programming, by design.

6. **Real-world confirmation the flashed firmware actually runs**, not just that
   bytes were written:
   ```
   uv run pyocd cmd -t nrf52840 -O jlink.non_interactive=false -c "reset"
   ```
   then read the UART directly (the harness/stage0 don't capture UART for this
   board) — captured the LED-chase text the firmware's `main.c` prints
   (`LED1 on (P0.13)`, `LED2 on (P0.14)`, ... repeating), confirming the flashed
   image is genuinely executing on-target, matching the physical LED chase.

## What Is Still Not Proven

Still pending for Step 1.0d:

- the **STM32/ST-Link** API path — silicon-ID + flash not yet exercised on
  `nucleo_l476rg` (this is now the *only* remaining hardware-validation gap before
  the shared layer can be built with both probe families bench-confirmed)
- the shared `adapters/` + `services/` layer — not created
- migration of `server.py` and `stage0_check.py` onto shared services

## Harness Built (Step 1.0d, item 1)

A throwaway API-path harness was written under `scratch/` (not shipped; deleted
once the operations are proven and migrated):

- `scratch/api_target_control_harness.py` — exercises **silicon-ID read, flash,
  and recover/unlock** through the pyOCD **Python API**, reusing the proven
  `board_config` loader and the same session-open + J-Link `non_interactive=false`
  workaround `server.py` uses. Out of scope (by design): enumeration, pack-install,
  serial discovery, UART, and Stage 0 CLI ergonomics.
- `scratch/README.md` — oracle workflow and exact `uv run` commands.
- Safety: read-only by default; `--flash` requires `--firmware PATH`; `--recover`
  is destructive and double-gated behind `--confirm-recover`.
- Verified to import and parse (`--help`); **not run against hardware** — that is a
  bench action for the operator.

### Bench gap to resolve before flashing Nordic — CLOSED

Flash artifacts (`reference/build/firmware.{elf,hex}`) exist for **`nucleo_l476rg`**
and **`nrf52833dk`**, and it turned out **`nrf52840dk` already had one too**
(`firmware/nrf52840dk/reference/build/firmware.{elf,bin}` plus source) — no new
firmware had to be built. Flash through the pyOCD API is now proven on
`nrf52840dk` (see "Flash Validated" above).

## Continue From Here

Silicon-ID, recover, **and flash** are all proven on `nrf52840dk` (J-Link). What
remains to close Step 1.0d's API-validation gate:

1. **Run the harness on STM32/ST-Link (`nucleo_l476rg`)** — it has a flash artifact
   and no destructive recover, and it closes the only remaining probe-family gap:
   - `uv run python stage0_check.py --board-id nucleo_l476rg` (subprocess truth)
   - `uv run python scratch/api_target_control_harness.py --board-id nucleo_l476rg --silicon-id`
   - `... --flash --firmware firmware/nucleo_l476rg/reference/build/firmware.elf`
   - Note: unlike the Nordic boards, ST-Link has no destructive recover path here —
     `do_recover` no-ops (`INFO`, not a failure) for any `recover_mode` other than
     `nrf_pyocd_unlock`, so the ST-Link harness run skips that step by design.
2. Once flash is green on both probe families, **create
   `src/pyocd_debug_mcp/adapters/` and `src/pyocd_debug_mcp/services/`**.
3. **Implement the proven target-control operations in the shared layer**, not
   directly in `server.py`.
4. **Thin both `server.py` and `stage0_check.py`** onto those shared services.

## Discipline: keep the probe abstraction honest (one-probe-family risk)

The service layer is being built while only a **J-Link** board is on the bench; the
STM32/ST-Link board is not yet available. That makes it easy to silently bake
J-Link assumptions into the shared code, because there is nothing to test them
against yet.

**Rule:** keep probe specifics — the J-Link `jlink.non_interactive=false` option,
native-vs-CMSIS-DAP routing, locked-target handling, etc. — routed through
`board_config` / the probe backend, **never as scattered `if probe == ...` branches**
in the service or wrapper layers. The code already does this (the J-Link option is
applied conditionally from `board.probe_family`); keep doing it religiously.

Building with only J-Link present puts the burden on **you** to keep ST-Link
assumptions out, since you cannot yet verify you did. This discipline is exactly
what makes the eventual STM32/ST-Link bring-up a **drop-in** rather than a rewrite —
the STM32 then becomes a verification of the abstraction, not a trigger to redesign
it.

## Important Constraint

Do **not** grow `server.py` into a full Stage 0 implementation before the
shared layer exists.

The current plan is:

- validate the existing API path first
- prove missing API operations in a temporary harness
- write real implementations into shared services
- make both wrappers call those services

## Current Short Version

If resuming work later:

> `server.py` is bench-validated on `nrf52840dk` for connect/read/control. The API
> harness (`scratch/api_target_control_harness.py`) has now PASSED on `nrf52840dk`
> for **silicon-ID read**, **recover/unlock**, and **flash** (flashed firmware was
> confirmed running via live UART output, not just written). The chip needed
> APPROTECT recover/unlock before any of this worked — `do_recover` mass-erases it.
> The only remaining hardware-validation gap is the **STM32/ST-Link** path on
> `nucleo_l476rg` — once that's green, build the shared `adapters/` / `services/`
> layer and thin both wrappers onto it.
