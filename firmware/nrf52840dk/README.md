# nRF52840 DK Reference Firmware

This board package is the repo-owned baseline for `nrf52840dk`, the official
Nordic board in the roadmap scope.

This file is the single canonical pre-bench runbook for the official Nordic
closure packet. The baseline source/build/artifacts already exist in-repo, but
official Stage 0 and Stage 1 bench proof are still pending on live
`nrf52840dk` hardware. `nrf52833dk` remains supplemental bench evidence only
and does not close official scope.

## What Already Exists

- App root: `firmware/nrf52840dk/reference/src/`
- Canonical symbol-bearing artifact:
  `firmware/nrf52840dk/reference/build/firmware.elf`
- Preferred flash artifact:
  `firmware/nrf52840dk/reference/build/firmware.hex` if present, else
  `firmware.elf`
- Reference app behavior:
  - prints deterministic `boot ok`
  - stays alive
  - exposes the fixed Stage 1 symbol contract
    `stage1_known_value = 0x1234ABCD`

## Build Recipe

```bash
./firmware/nrf52840dk/reference/build_reference.sh
```

What that script does:

- bootstraps a small isolated `west + pyelftools` venv under
  `~/.cache/firmware-cli-zephyr-west` by default
- uses the Zephyr workspace at `~/zephyrproject` by default
- requires a usable Zephyr SDK installation
- builds the app for `nrf52840dk/nrf52840`
- cleans `reference/build/` back down to the canonical artifact surface before
  copying outputs in
- copies `zephyr/zephyr.elf` to the canonical `firmware.elf` name
- copies `zephyr/zephyr.hex` to `firmware.hex` when present

Validated toolchain note for this bench:

- this Intel macOS machine was validated with `zephyr-sdk-0.17.4`
- the current official Zephyr SDK line no longer ships macOS `x86_64` bundles,
  so Intel Macs need an older supported SDK release or another supported
  toolchain path

## Frozen Pre-Bench Board Facts

- `board_id = nrf52840dk`
- `display_name = nRF52840-DK`
- `mcu_family = nrf52840`
- `probe_family = jlink`
- `pyocd_target = nrf52840`
- `pack_name = nrf52840`
- `serial_baudrate = 115200`
- `test_read_address = 0x10000000`
- `silicon_id_address = 0x10000100`
- `silicon_id_expected = 0x00052840`
- `silicon_id_label = FICR.INFO.PART`
- `reference_uart_patterns[0] = "boot ok"`
- `requires_recover_validation = true`
- `recover_mode = nrf_pyocd_unlock`
- symbol artifact =
  `firmware/nrf52840dk/reference/build/firmware.elf`
- flash artifact preference =
  `firmware/nrf52840dk/reference/build/firmware.hex` if present, else
  `firmware.elf`

Pending host-heuristic verification only:

- `probe_hint_terms = ["j-link", "jlink", "segger", "nrf"]`
- `serial_hint_terms = ["j-link", "jlink", "segger", "nrf", "virtual com"]`

Those hint terms are intentionally frozen as the intended resolver contract, but
they are not bench-proven facts until the official board is attached again.

## Official Nordic Closure Checklist

Run these in this exact order after physically switching to `nrf52840dk`:

1. `uv run pyocd list`
2. `uv run python host_bootstrap.py --board-id nrf52840dk`
3. `./firmware/nrf52840dk/reference/build_reference.sh`
4. `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --recover-test nrf52840dk --confirm-shared-usb nrf52840dk`
5. `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`

If serial auto-resolution is ambiguous, the only rerun path is to rerun Stage 0
and/or the smoke harness with an explicit port override:

- `--port nrf52840dk=<port>`

The board config already declares the expected UART substring, so `--expect` is
not required for the normal reference-firmware path.

## Official Nordic Pass / Fail Checklist

Treat the official Nordic run as successful only if all of these are true:

- J-Link probe is visible.
- Target `nrf52840` is available.
- Silicon identity matches `0x00052840` at `0x10000100`.
- Stage 0 flashes the canonical reference artifact successfully.
- Stage 0 UART output contains `boot ok`.
- Stage 0 recover/unlock succeeds.
- The operator confirms the visible probe and COM port are the same physical
  board.
- The tracked Stage 1 smoke harness passes:
  - flash
  - `reset_and_halt`
  - `pc` read
  - symbol resolution
  - `0x1234ABCD` value readback
  - UART `boot ok`

## Current Status

Verified in repo:

- The repo contains one canonical reference-firmware source tree and one
  repeatable build entrypoint for `nrf52840dk`.
- The repo-owned reference app mirrors the existing minimal Nordic baseline
  pattern: deterministic `boot ok` UART plus the fixed Stage 1 symbol contract
  `stage1_known_value = 0x1234ABCD`.
- The build helper completed on this Mac host and produced
  `firmware/nrf52840dk/reference/build/firmware.elf` plus `firmware.hex`.

Still pending on live official hardware:

- The official `nrf52840dk` Stage 0 truth path:
  J-Link visibility, exact silicon identity, flash, UART, recover, and shared
  USB confirmation.
- The same tracked Stage 1 smoke harness run on the official `nrf52840dk`
  board after Stage 0 is green.
