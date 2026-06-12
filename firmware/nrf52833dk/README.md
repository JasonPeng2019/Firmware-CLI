# nRF52833 DK Reference Firmware

This board package defines the repo-owned Stage 0 reference firmware for
`nrf52833dk`.

The intent is narrow:

- keep one tiny, deterministic baseline app in-repo
- build it into the canonical artifact name `reference/build/firmware.elf`
- flash that artifact through `stage0_check.py`
- prove that the board prints `boot ok` over the virtual COM port

Source of truth for the app:

- app root: `firmware/nrf52833dk/reference/src/`
- canonical symbol-bearing artifact: `firmware/nrf52833dk/reference/build/firmware.elf`
- optional flashable side artifact: `firmware/nrf52833dk/reference/build/firmware.hex`

Build recipe:

```bash
./firmware/nrf52833dk/reference/build_reference.sh
```

What that script does:

- bootstraps a small isolated `west + pyelftools` venv under
  `~/.cache/firmware-cli-zephyr-west` by default
- uses the Zephyr workspace at `~/zephyrproject` by default
- requires a usable Zephyr SDK installation
- builds the app for `nrf52833dk/nrf52833`
- cleans `reference/build/` back down to the canonical artifact surface before
  copying outputs in
- copies `zephyr/zephyr.elf` to the canonical `firmware.elf` name
- copies `zephyr/zephyr.hex` to `firmware.hex` when present

Validated toolchain note for this bench:

- this Intel macOS machine was validated with `zephyr-sdk-0.17.4`
- the current official Zephyr SDK line no longer ships macOS `x86_64` bundles,
  so Intel Macs need an older supported SDK release or another supported
  toolchain path

Stage 0 validation flow:

```bash
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py \
  --board-id nrf52833dk \
  --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf
```

Destructive recover validation:

```bash
uv run python stage0_check.py \
  --board-id nrf52833dk \
  --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf \
  --recover-test nrf52833dk \
  --confirm-shared-usb nrf52833dk
```

The board config now declares the expected UART substring, so `--expect` is not
required for the normal reference-firmware path.

Verified:

- The attached board profile `nrf52833dk` is already host-visible and passes the
  non-flash parts of Stage 0 on this bench.
- The local Zephyr board support sets `zephyr,console = &uart0` at `115200` for
  `nrf52833dk/nrf52833`, which matches the Stage 0 serial expectations.
- The repo-owned reference app builds into
  `firmware/nrf52833dk/reference/build/firmware.elf` on this Mac bench.
- The same artifact was flashed to the attached board and produced Zephyr's boot
  banner plus repeated `boot ok` lines on
  `/dev/cu.usbmodem0006854006931`.
- `uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf`
  now passes the automated flash and UART checks on this bench.
- A full destructive Stage 0 run with `--recover-test nrf52833dk` completed on
  this Mac bench, and the board remained reachable after the unlock cycle.
- The human operator confirmed that the visible J-Link debug probe and the
  visible `/dev/cu.usbmodem0006854006931` virtual COM port were exposed by the
  same physical USB-attached `nrf52833dk` board during the final bench run.

Pending verification:

- The reference build helper and Stage 0 path are bench-verified on this Intel
  macOS host; the same flow still needs real confirmation on other supported
  hosts, especially Windows.
