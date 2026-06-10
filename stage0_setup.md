# Stage 0 Setup

This note describes the shortest path to getting `stage0_check.py` working for any supported board.
It assumes the canonical repo layout from the current plan and the board-config workflow in `boards/`.
In this note, the reference firmware path is a **host-supplied runtime argument** used for Stage 0
validation. It is **not** stored in board YAML, and it does **not** mean a user's project firmware path.

## 1. Install Python deps

Use a venv if you want isolation, but it is not required.

Windows without activation:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install pyocd pyserial pyyaml
```

macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pyocd pyserial pyyaml
```

`pyyaml` is only needed for `.yaml` / `.yml` board files. JSON board files do not need it.

## 2. Make sure OS-level probe support exists

The script does not install probe drivers for you.

- `J-Link` boards may need SEGGER software or a CMSIS-DAP path that pyOCD can use.
- `ST-Link` boards may need ST drivers or firmware support.
- Other probes must already be visible to the OS and usable by `pyocd`.

Stage 0 only works after the host can see the debug probe and the USB serial interface.

## 3. Create or pick a board config

Board support is config-driven. Put one config file per board in `boards/`, or pass extra board files
with `--board-config`.

Minimum useful fields:

```yaml
board_id: my_board  # PROJECT-DEFINED, UNVERIFIED
display_name: "My Board"  # PROJECT-DEFINED, UNVERIFIED
mcu_family: rp2040  # HW-FIXED, UNVERIFIED
probe_family: cmsisdap  # HW-FIXED, UNVERIFIED
pyocd_target: rp2040  # VENDOR-FIXED, UNVERIFIED
serial_baudrate: 115200  # PROJECT-DEFINED, UNVERIFIED
test_read_address: 0x20000000  # HW-FIXED, UNVERIFIED
```

Useful optional fields:

- `pack_name`
- `probe_hint_terms`
- `serial_hint_terms`
- `reference_uart_patterns`
- `recover_command`
- `requires_recover_validation`
- `uart_note`

Board YAML is for board configuration only. Put board/probe values there; do not put firmware paths,
project paths, build commands, or artifact paths there.

Important distinction:

- The Stage 0 reference firmware path is supplied by the host at runtime via
  `--reference-firmware BOARD_ID=PATH`.
- A user's actual project firmware lives in the user's repo/directory, outside this server repo, and
  should be provided later as a runtime/session input to the build/flash workflow, not stored in the
  board YAML.
- `stage0_check.py` now rejects board YAML files that try to include project/session-scoped fields such
  as `reference_firmware_path`, `project_path`, `build_command`, or `artifact_path`.

Examples:

- `boards/nrf52840dk.yaml`
- `boards/nucleo_l476rg.yaml`
- `boards/example_custom_nrf52_board.yaml`
- `boards/example_custom_board.yaml`

## 4. Run the checker

Run the host-level bootstrap first:

```bash
python host_bootstrap.py
```

That checks host readiness only. After that, run `stage0_check.py` for board-level validation.

If you want it to install missing Python deps and missing target packs:

```bash
python host_bootstrap.py --install-missing --install-packs
```

By default, the script loads all non-example board files in `boards/`:

```bash
python stage0_check.py
```

To run one known board from `boards/`:

```bash
python stage0_check.py --board-id my_board
```

To add a board file outside the default `boards/` directory:

```bash
python stage0_check.py \
  --board-config path/to/my_board.yaml \
  --board-id my_board
```

If port detection is ambiguous:

```bash
python stage0_check.py \
  --board-id my_board \
  --port my_board=<serial-port>
```

If you want flash + UART validation:

```bash
python stage0_check.py \
  --board-id my_board \
  --reference-firmware my_board=path/to/built/firmware.elf \
  --expect my_board="boot ok"
```

If the board needs a destructive recover test:

```bash
python stage0_check.py \
  --board-id my_board \
  --recover-test my_board
```

## 5. What the script checks

Automated:

- `pyocd` installed
- `pyserial` installed
- probe visible
- pyOCD target pack available
- SWD connect + smoke-test register read
- virtual COM port visible
- optional flash of known-good firmware
- optional UART output capture
- optional recover/unlock command

Still manual:

- confirm the probe and COM port come from the same physical USB connection
- confirm OS-level driver/probe setup is correct
- confirm the UART output is the expected reference behavior if you do not provide `--expect`
- confirm destructive recover behavior is acceptable before using `--recover-test`

## 6. Typical failure cases

- `pyOCD not found`: install `pyocd`
- `pyserial not found`: install `pyserial`
- target missing: run with `--install-packs` or install the pack manually
- probe not found: fix the OS/probe driver path first
- COM port ambiguous: pass `--port BOARD_ID=...`
- wrong target: fix `pyocd_target` in the board config

## Verified

- Non-hardware verification: this doc matches the current generic `stage0_check.py` CLI shape.
- Non-hardware verification: the example commands avoid machine-local absolute paths and board-specific CLI aliases.

## Pending verification (esp. hardware)

- Hardware verification: flashing, UART capture, and recover flows still need to be run on real boards.
- Environment verification: each example board config still needs host-side confirmation of its `pyocd_target`, probe hints, serial hints, and reference firmware artifact.
- Architecture verification: later firmware-ingestion/build tooling still needs to prove the external
  user-project path flow on a real project directory outside this repo.
