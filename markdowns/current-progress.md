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
real **`nrf52840dk`** and **passed** for the two operations testable on that board:

- pyOCD Python-API **silicon-ID read** — ✅ PASS (`FICR.INFO.PART` = `0x00052840`,
  matching board config and oracle'd against `stage0_check.py`)
- pyOCD Python-API **recover / unlock** — ✅ PASS (mass-erase via the API, with a
  successful post-erase re-read)

This proves the pyOCD **Python-API** path does what `stage0_check.py`'s subprocess
path does for silicon-ID and recover on Nordic/J-Link hardware.

## What Is Still Not Proven

Still pending for Step 1.0d:

- pyOCD Python-API **flash** — harness written, **not yet run** (the `nrf52840dk`
  on the bench has no flash artifact; needs an artifact or a different board)
- the **STM32/ST-Link** API path — silicon-ID + flash not yet exercised on
  `nucleo_l476rg`
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

### Bench gap to resolve before flashing Nordic

Flash artifacts (`reference/build/firmware.{elf,hex}`) exist for **`nucleo_l476rg`**
and **`nrf52833dk`**, but **NOT for `nrf52840dk`** (the board connect/read was proven
on — only `.gitkeep` there). Build an artifact for whichever Nordic board is on the
bench before flashing it.

## Continue From Here

Silicon-ID and recover are proven on `nrf52840dk`. What remains to close Step 1.0d's
API-validation gate:

1. **Prove flash through the API.** The bench `nrf52840dk` has no artifact, so either
   build/point at an nRF52840 `.hex`/`.elf`, or prove flash on a board that has one.
2. **Run the harness on STM32/ST-Link (`nucleo_l476rg`)** — it has a flash artifact
   and no destructive recover, and it closes the second probe-family gap:
   - `uv run python stage0_check.py --board-id nucleo_l476rg` (subprocess truth)
   - `uv run python scratch/api_target_control_harness.py --board-id nucleo_l476rg --silicon-id`
   - `... --flash --firmware firmware/nucleo_l476rg/reference/build/firmware.elf`
   (Doing flash here covers item 1 too — proving flash on either probe family suffices,
   though proving it on both is stronger.)
3. Once flash is green on both probe families, **create
   `src/pyocd_debug_mcp/adapters/` and `src/pyocd_debug_mcp/services/`**.
4. **Implement the proven target-control operations in the shared layer**, not
   directly in `server.py`.
5. **Thin both `server.py` and `stage0_check.py`** onto those shared services.

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
> for **silicon-ID read** and **recover/unlock**. Only **flash** through the API is
> still unproven (the bench 52840 has no artifact). Next: prove flash — easiest on
> `nucleo_l476rg`, which also covers the STM32/ST-Link path — then build the shared
> `adapters/` / `services/` layer and thin both wrappers onto it.
