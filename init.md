# Environment Bootstrap

- Purpose:
  Get a fresh machine from zero to a working one-board Stage 0 run.
- Scope:
  This is the practical setup guide.
- Repo:
  A local MCP server over `pyOCD` for a physically attached Cortex-M target.
- Canonical layout and naming:
  [README.md](./README.md)

## Quick Start

- Run everything from the repo root.
- Install `uv`.
- Run `uv sync`.
- Check that pyOCD can see your probe.
- Run `host_bootstrap.py` for your board.
- Run `stage0_check.py` for your board.

macOS / Linux:

```bash
uv sync
uv run pyocd list
uv run python host_bootstrap.py --board-id <board_id>
uv run python stage0_check.py --board-id <board_id>
```

Windows (PowerShell):

```powershell
uv sync
uv run pyocd list
uv run python host_bootstrap.py --board-id <board_id>
uv run python stage0_check.py --board-id <board_id>
```

- Important:
  `uv run python stage0_check.py` with no `--board-id` checks all non-example
  tracked boards, not just the one you have attached.

## Prerequisites

- `uv` is the canonical environment manager.
- Package floor:
  `pyproject.toml` supports Python `3.10+`.
- A debug probe must already be physically attached.
- The host OS must already support that probe.
- Team-standard interpreter:
  `.python-version = 3.12`.
- You do not need to create or activate a venv manually.

Install `uv`:

Windows (PowerShell):

```powershell
pip install uv
```

macOS:

```bash
brew install uv
```

Linux:

- Install `uv` with your normal method.
- Open a new shell so `uv` is on `PATH`.

Bootstrap the repo environment:

```bash
uv sync
```

- `uv sync` creates `.venv/` automatically.
- `uv sync` installs runtime and dev dependencies from `uv.lock`.
- Use `uv sync --no-dev` only if you intentionally want a runtime-only install.
- After this, use `uv run ...` for repo commands.

## Native Probe Dependencies

- The repo does not install OS drivers for you.
- Stage 0 only works after the host can see:
  - the debug probe
  - the board's USB serial interface

If probe enumeration fails, install the missing host dependency first:

- macOS:
  `brew install libusb`
- Debian / Ubuntu:
  `sudo apt install libusb-1.0-0`
- Windows:
  Install the probe's required USB driver path or vendor tooling.
  - For generic CMSIS-DAP probes, this may mean a WinUSB driver path such as
    Zadig.
  - Vendor probes such as ST-Link or J-Link may ship their own driver/tooling.
- Linux:
  You may also need pyOCD udev rules from the upstream pyOCD repo.

If you install Linux udev rules, reload them with:

```bash
sudo udevadm control --reload
sudo udevadm trigger
```

## Canonical Bootstrap Flow

- Sanity check that the environment is usable:

```bash
uv sync
uv run pyocd list
uv run python host_bootstrap.py
uv run pyocd-debug-mcp
```

- `uv run pyocd list` proves pyOCD can see at least one probe.
- `uv run pyocd list` also shows the probe UID you may later want in `.env` as
  `PYOCD_PROBE_UID`.
- `uv run python host_bootstrap.py` checks host readiness only.
- `uv run pyocd-debug-mcp` starts the MCP stdio server that MCP clients connect
  to.
- MCP Inspector entrypoint:

```bash
uv run mcp dev src/pyocd_debug_mcp/server.py
```

## Board YAML Overview

- Stage 0 is config-driven.
- Every board is described by one YAML or JSON board-config file.
- Two normal paths:
  - use an existing tracked file in `boards/`
  - create a new file and pass it with `--board-config`
- Board YAML is for board metadata only.
- Runtime inputs such as firmware paths belong on the CLI, not in board YAML.

## Use An Existing Board YAML

Tracked non-example board files:

- `boards/nrf52833dk.yaml`
- `boards/nrf52840dk.yaml`
- `boards/nucleo_l476rg.yaml`

Example template files:

- `boards/example_custom_nrf52_board.yaml`
- `boards/example_custom_board.yaml`

- `example_*.yaml` files are templates only.
- They are intentionally excluded from the default no-argument Stage 0 sweep.

For one attached board, use:

```bash
uv run python host_bootstrap.py --board-id <board_id>
uv run python stage0_check.py --board-id <board_id>
```

Example:

```bash
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk
```

Use this pattern whenever:

- only one physical board is connected
- the repo tracks multiple reference boards
- you want to avoid failures caused by unrelated tracked boards

## Create A New Board YAML

Two options:

1. Create a temporary local file anywhere and pass it with `--board-config`.
2. Add a shared tracked file under `boards/`.

Naming rule for shared tracked files:

```text
boards/<board_id>.yaml
```

- For shared non-example board files, the filename should match the canonical
  `board_id`.
- The `example_*.yaml` files are the intentional exception.

Good starting templates:

- `boards/example_custom_nrf52_board.yaml`
- `boards/example_custom_board.yaml`

Required fields:

```yaml
board_id: my_board
display_name: "My Board"
mcu_family: nrf52833
probe_family: jlink
pyocd_target: nrf52833
```

Rules:

- `board_id`:
  lowercase letters, numbers, and underscores only
- `display_name`:
  human-facing label shown in script output
- `mcu_family`:
  hardware family such as `nrf52833` or `stm32l476`
- `probe_family`:
  stable family label such as `jlink`, `stlink`, or `cmsisdap`
- `pyocd_target`:
  real pyOCD target name

Additional family rule:

- For `nrf*` and `stm32*` boards, `stage0_check.py` can derive a default
  `test_read_address`.
- For other MCU families, you must supply it yourself.

Example:

```yaml
test_read_address: 0x20000000
```

Recommended fields:

- `pack_name`
- `serial_baudrate`
- `probe_hint_terms`
- `serial_hint_terms`
- `expected_uart_substring` or `reference_uart_patterns`
- `requires_recover_validation`
- `recover_command`
- `uart_note`
- `silicon_id_address`
- `silicon_id_expected`
- `silicon_id_mask`
- `silicon_id_width_bits`
- `silicon_id_label`

Exact identity fields matter when nearby chips can both answer generic debug
reads.

Example:

```yaml
silicon_id_address: 0x10000100
silicon_id_expected: 0x00052833
silicon_id_label: "FICR.INFO.PART"
```

Do not put these in board YAML:

- `reference_firmware_path`
- `recovery_image_path`
- project paths
- build commands
- artifact output paths
- any user- or session-scoped path

Minimal Nordic example:

```yaml
board_id: my_board
display_name: "My Board"
mcu_family: nrf52833
probe_family: jlink
pyocd_target: nrf52833
silicon_id_address: 0x10000100
silicon_id_expected: 0x00052833
silicon_id_label: "FICR.INFO.PART"
```

Minimal STM32 example:

```yaml
board_id: my_board
display_name: "My Board"
mcu_family: stm32l476
probe_family: stlink
pyocd_target: stm32l476rgtx
```

Minimal non-nRF / non-STM32 example:

```yaml
board_id: my_board
display_name: "My Board"
mcu_family: rp2040
probe_family: cmsisdap
pyocd_target: rp2040
test_read_address: 0x20000000
```

## Validate A New Board YAML

Host readiness:

- If the file is outside `boards/`:

```bash
uv run python host_bootstrap.py \
  --board-config path/to/my_board.yaml \
  --board-id my_board
```

- If the file is already tracked in `boards/`:

```bash
uv run python host_bootstrap.py --board-id my_board
```

What `host_bootstrap.py` checks:

- Python dependencies
- pyOCD CLI visibility
- probe enumeration
- serial-port enumeration
- board-config loading
- pyOCD target-pack availability

If the target pack is missing:

```bash
uv run python host_bootstrap.py --install-packs --board-id my_board
```

or:

```bash
uv run pyocd pack install <pack_name>
```

Board-level Stage 0 validation:

- If the file is outside `boards/`:

```bash
uv run python stage0_check.py \
  --board-config path/to/my_board.yaml \
  --board-id my_board
```

- If the file is already tracked in `boards/`:

```bash
uv run python stage0_check.py --board-id my_board
```

- This is the minimum correct one-board Stage 0 bring-up path.
- Do not use the bare no-argument `stage0_check.py` command unless you really
  intend to validate every tracked non-example board.

## Flash, UART, And Recover Validation

Base flash + UART validation:

```bash
uv run python stage0_check.py \
  --board-id my_board \
  --reference-firmware my_board=path/to/firmware.elf \
  --expect my_board="boot ok"
```

- If the file is outside `boards/`, also add:
  `--board-config path/to/my_board.yaml`

Ambiguous serial-port matching:

```bash
uv run python stage0_check.py \
  --board-id my_board \
  --port my_board=<serial-port>
```

Windows example:

```powershell
uv run python stage0_check.py --board-id my_board --port my_board=COM3
```

Destructive recover validation:

```bash
uv run python stage0_check.py \
  --board-id my_board \
  --recover-test my_board
```

- This may erase flash on the device.

## Local Overrides

Use these machine-local layers:

- `.env`:
  optional, gitignored, auto-loaded by the MCP server and Phase A host scripts
- Start from:
  `.env.example`
- Put these in `.env` when useful:
  - `PYOCD_PROBE_UID`
  - `PYOCD_TARGET`
- `pyocd.local.yaml`:
  optional, gitignored, for per-developer pyOCD tweaks
- `pyocd.yaml`:
  optional, committed only when the team has a real shared pyOCD option

- Tracked board YAML must stay hardware-focused.
- The MCP `connect` tool can still take `unique_id` and `target` directly.

## Main Commands

```bash
uv run python host_bootstrap.py
uv run python stage0_check.py
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk
uv run python host_bootstrap.py --board-config path/to/my_board.yaml --board-id my_board
uv run python stage0_check.py --board-config path/to/my_board.yaml --board-id my_board
uv run pyocd-debug-mcp
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
```

## Available MCP Tools

- `connect`
- `disconnect`
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

## Expected Results

- `uv run pyocd list` should show your probe.
- `uv run python host_bootstrap.py --board-id my_board` should confirm host
  readiness for that board config.
- `uv run python stage0_check.py --board-id my_board` should pass automated
  Stage 0 checks if:
  - the YAML is correct
  - the target pack is installed
  - the hardware is visible

Even after automated checks pass, full Stage 0 still requires:

- flash a known-good reference image
- confirm expected UART behavior
- prove recover/unlock if required
- confirm the visible probe and serial port belong to the same physical board

## Related Docs

- Repo layout and naming: [README.md](./README.md)
- Host readiness checks: [host_bootstrap.md](./host_bootstrap.md)
- Stage 0 validation flow: [stage0_setup.md](./stage0_setup.md)
- Roadmap: [markdowns/ROADMAP.md](./markdowns/ROADMAP.md)
