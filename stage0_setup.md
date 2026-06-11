# Stage 0 Setup

This note describes the shortest path to getting `stage0_check.py` working for
any supported board under the frozen Phase A repo standard.

It assumes:

- the canonical repo layout from [README.md](./README.md)
- the `uv`-managed environment from [init.md](./init.md)
- board definitions in `boards/`

Important distinction:

- board YAML stays hardware-focused
- canonical artifact locations live in the repo tree and naming rules
- Stage 0 still receives a reference firmware path as a runtime argument

That runtime path may point at the canonical repo-owned baseline location later,
for example `firmware/<board>/reference/build/firmware.elf`, but it is not
stored in tracked board YAML.

The canonical firmware tree may still be scaffolding before `R4` baselines are
actually populated. Until those baseline artifacts exist, flash and UART
validation still require an explicit runtime `--reference-firmware` path.

## 1. Bootstrap The Canonical Environment

```bash
uv sync
```

That installs the Phase A tooling, including `pyocd`, `pyserial`, `pyyaml`, and
`python-dotenv`.

## 2. Make Sure Probe Support Exists On The Host

The script does not install probe drivers for you.

- `J-Link` boards may need SEGGER tooling or a pyOCD-compatible path
- `ST-Link` boards may need ST driver or firmware support
- other probes must already be visible to the OS and usable by `pyocd`

Stage 0 only works after the host can see both the debug probe and the USB
serial interface.

## 3. Use A Tracked Board Config

Board support is config-driven. Put one tracked config per board in `boards/`,
or pass extra board files with `--board-config`.

Minimum useful fields:

```yaml
board_id: my_board
display_name: "My Board"
mcu_family: rp2040
probe_family: cmsisdap
pyocd_target: rp2040
serial_baudrate: 115200
test_read_address: 0x20000000
```

Useful optional fields:

- `pack_name`
- `probe_hint_terms`
- `serial_hint_terms`
- `reference_uart_patterns`
- `recover_command`
- `requires_recover_validation`
- `uart_note`

Tracked board YAML must not contain:

- `reference_firmware_path`
- `recovery_image_path`
- project paths
- build commands
- artifact output paths
- any user- or session-scoped path

Examples:

- `boards/nrf52840dk.yaml`
- `boards/nucleo_l476rg.yaml`
- `boards/example_custom_nrf52_board.yaml`
- `boards/example_custom_board.yaml`

## 4. Run Host Bootstrap First

```bash
uv run python host_bootstrap.py
```

If you want it to install missing Python packages and missing target packs:

```bash
uv run python host_bootstrap.py --install-missing --install-packs
```

`--install-missing` reconciles the canonical repo environment with
`uv sync --locked`; it does not do ad hoc per-package installs.

The script auto-loads `.env` if present, so repo-local `PYOCD_*` defaults are
available without manual shell export.

## 5. Run Stage 0 Validation

By default, the script loads all non-example board files in `boards/`:

```bash
uv run python stage0_check.py
```

That default is for repo-wide validation across all tracked reference boards.
For first-time bring-up on one physical bench, prefer `--board-id <board>` so
an unrelated tracked board does not dominate the result.

Run one tracked board:

```bash
uv run python stage0_check.py --board-id my_board
```

Add a board file outside the default `boards/` directory:

```bash
uv run python stage0_check.py \
  --board-config path/to/my_board.yaml \
  --board-id my_board
```

If serial detection is ambiguous:

```bash
uv run python stage0_check.py \
  --board-id my_board \
  --port my_board=<serial-port>
```

If you want flash plus UART validation:

```bash
uv run python stage0_check.py \
  --board-id my_board \
  --reference-firmware my_board=path/to/firmware.elf \
  --expect my_board="boot ok"
```

If the board needs a destructive recover test:

```bash
uv run python stage0_check.py \
  --board-id my_board \
  --recover-test my_board
```

## 6. What The Script Checks

Automated:

- `pyocd` installed
- `pyserial` installed
- probe visible
- pyOCD target pack available
- SWD connect plus smoke-test register read
- virtual COM port visible
- optional flash of known-good firmware
- optional UART output capture
- optional recover or unlock command

Still manual:

- confirm the probe and COM port come from the same physical USB connection
- confirm OS-level driver and probe setup is correct
- confirm UART output is the intended reference behavior if you do not provide
  `--expect`
- confirm destructive recover behavior is acceptable before using
  `--recover-test`

## 7. Typical Failure Cases

- `pyOCD not found`: run `uv sync`
- `pyserial not found`: run `uv sync`
- target missing: run with `--install-packs` or install the pack manually
- probe not found: fix the OS and probe-driver path first
- COM port ambiguous: pass `--port BOARD_ID=...`
- wrong target: fix `pyocd_target` in the board config

## Verification Status

- Non-hardware verification: this doc matches the current generic
  `stage0_check.py` CLI shape.
- Pending hardware verification: flashing, UART capture, and recover flows still
  need to be run on real boards.
