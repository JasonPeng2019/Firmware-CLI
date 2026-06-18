# Nucleo-L476RG Reference Firmware

This board package defines the repo-owned Stage 0 reference firmware for
`nucleo_l476rg`.

The intent is narrow:

- keep one tiny, deterministic baseline app in-repo
- build it into the canonical artifact name `reference/build/firmware.elf`
- use that artifact through the current `stage0_check.py` flow and later shared
  validation/flash logic
- prove that the board prints `boot ok` over the ST-LINK virtual COM port

Source of truth for the app:

- app root: `firmware/nucleo_l476rg/reference/src/`
- canonical symbol-bearing artifact:
  `firmware/nucleo_l476rg/reference/build/firmware.elf`
- optional flashable side artifact:
  `firmware/nucleo_l476rg/reference/build/firmware.hex`

Build recipe:

```bash
./firmware/nucleo_l476rg/reference/build_reference.sh
```

What that script does:

- bootstraps a small isolated `west + pyelftools` venv under
  `~/.cache/firmware-cli-zephyr-west` by default
- uses the Zephyr workspace at `~/zephyrproject` by default
- requires a usable Zephyr SDK installation
- builds the app for `nucleo_l476rg`
- cleans `reference/build/` back down to the canonical artifact surface before
  copying outputs in
- copies `zephyr/zephyr.elf` to the canonical `firmware.elf` name
- copies `zephyr/zephyr.hex` to `firmware.hex` when present
- defines one known Stage 1 symbol contract in the reference app:
  `stage1_known_value = 0x1234ABCD`

Stage 0 validation flow once the board is physically attached:

```bash
uv run python host_bootstrap.py --board-id nucleo_l476rg
uv run python stage0_check.py \
  --board-id nucleo_l476rg \
  --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf
```

The board config declares the expected UART substring, so `--expect` is not
required for the normal reference-firmware path.

Stage 1 smoke-harness flow on a live bench:

```bash
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
```

Verified:

- The repo now contains one canonical reference-firmware source tree and one
  repeatable build entrypoint for `nucleo_l476rg`.
- Zephyr board support on this host binds `zephyr,console` to `usart2`, which
  matches the tracked Stage 0 UART expectation for this board.
- The build helper completed on this Mac host and produced
  `firmware/nucleo_l476rg/reference/build/firmware.elf` plus `firmware.hex`.
- `uv run python host_bootstrap.py --board-id nucleo_l476rg` passed on this Mac
  host with:
  - probe UID `0668FF514988525067213913`
  - serial port `/dev/cu.usbmodem143303`
  - confirmed target `stm32l476rgtx`
  - confirmed pack token `stm32l476`
  - generic serial matching working even without `STM32_Programmer_CLI`
- `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware
  nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf` passed for
  flash plus UART on this Mac host and captured `boot ok`.
- `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
  passed on this Mac host and proved:
  - flash through the shared SWD service
  - `pc` read after `reset_and_halt`
  - shared symbol resolution for `stage1_known_value`
  - target-memory readback of `0x1234ABCD`
  - UART capture of `boot ok` through the shared UART service
- The human operator confirmed that the visible ST-Link debug probe and the
  visible `/dev/cu.usbmodem143303` virtual COM port were exposed by the same
  physical USB-attached `nucleo_l476rg` board during the final STM32 bench run.

Out of scope for this board package:

- The STM32 recover story is not part of the current Stage 0 contract for this
  board family.
