# nRF52840 DK Reference Firmware

This board package defines the repo-owned Stage 0 reference firmware for
`nrf52840dk`, the official Nordic board in the roadmap scope.

The intent is narrow:

- keep one tiny, deterministic baseline app in-repo
- build it into the canonical artifact name `reference/build/firmware.elf`
- use that artifact through the current `stage0_check.py` flow and later shared
  validation/flash logic
- prove that the board prints `boot ok` over the virtual COM port

Source of truth for the app:

- app root: `firmware/nrf52840dk/reference/src/`
- canonical symbol-bearing artifact: `firmware/nrf52840dk/reference/build/firmware.elf`
- optional flashable side artifact: `firmware/nrf52840dk/reference/build/firmware.hex`

Build recipe:

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
- defines one known Stage 1 symbol contract in the reference app:
  `stage1_known_value = 0x1234ABCD`

Validated toolchain note for this bench:

- this Intel macOS machine was validated with `zephyr-sdk-0.17.4`
- the current official Zephyr SDK line no longer ships macOS `x86_64` bundles,
  so Intel Macs need an older supported SDK release or another supported
  toolchain path

Official Stage 0 validation flow once the board is physically attached:

```bash
uv run pyocd list
uv run python host_bootstrap.py --board-id nrf52840dk
./firmware/nrf52840dk/reference/build_reference.sh
uv run python stage0_check.py \
  --board-id nrf52840dk \
  --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf \
  --recover-test nrf52840dk \
  --confirm-shared-usb nrf52840dk
```

Stage 1 smoke-harness proof after the Stage 0 truth path is green:

```bash
uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk
```

The board config declares the expected UART substring, so `--expect` is not
required for the normal reference-firmware path.

Verified:

- The repo now contains one canonical reference-firmware source tree and one
  repeatable build entrypoint for `nrf52840dk`.
- The repo-owned reference app is deliberately aligned with the existing
  minimal Nordic Stage 0 baseline pattern: repeated `boot ok` over UART with no
  extra board-specific behavior.
- The reference app now also carries one fixed Stage 1 symbol-resolution
  contract: `stage1_known_value = 0x1234ABCD`.
- The build helper completed on this Mac host and produced
  `firmware/nrf52840dk/reference/build/firmware.elf` plus `firmware.hex`.

Pending verification:

- The official `nrf52840dk` Stage 0 path still needs the full real bench proof:
  J-Link visibility, exact silicon identity, flash, UART, recover, and shared
  USB confirmation.
- The tracked Stage 1 smoke harness still needs to be run on the official
  `nrf52840dk` board after the Stage 0 truth path is green.
