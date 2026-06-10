# Host Bootstrap

This document explains what `host_bootstrap.py` does and how to run it.

`host_bootstrap.py` is the **host-level prerequisite check** that should run **before**
`stage0_check.py`.

It does **not** prove a board works. It only checks whether the machine is ready to attempt
board-level validation.

## What it does

`host_bootstrap.py` checks the host environment for:

- Python package availability for `pyocd`, `pyserial`, and `pyyaml`
- `pyocd` CLI availability
- debug probe enumeration through `pyocd`
- serial-port enumeration through `pyserial`
- board-config loading from `boards/` and any extra `--board-config` files
- pyOCD target-pack availability for the selected board configs

Optional actions:

- install missing Python packages with `--install-missing`
- install missing pyOCD target packs with `--install-packs`

What it does **not** do:

- it does not install OS drivers
- it does not install vendor probe software such as SEGGER or ST tooling
- it does not update probe firmware
- it does not prove flashing, UART behavior, or recover behavior on real hardware

## Run it in the venv

Run it with the venv’s Python directly.

Windows:

```powershell
.venv\Scripts\python.exe host_bootstrap.py
```

macOS:

```bash
.venv/bin/python host_bootstrap.py
```

This avoids depending on shell activation behavior.

## Common commands

Basic host check:

```powershell
.venv\Scripts\python.exe host_bootstrap.py
```

Install missing Python deps and missing target packs:

```powershell
.venv\Scripts\python.exe host_bootstrap.py --install-missing --install-packs
```

Run for one specific board config already in `boards/`:

```powershell
.venv\Scripts\python.exe host_bootstrap.py --board-id nrf52840dk
```

Include an extra board config outside `boards/`:

```powershell
.venv\Scripts\python.exe host_bootstrap.py `
  --board-config path\to\my_board.yaml `
  --board-id my_board
```

## What to do after it passes

After `host_bootstrap.py` shows the host is ready, run `stage0_check.py` for board-level validation.

Example:

```powershell
.venv\Scripts\python.exe stage0_check.py --board-id nrf52840dk
```

## How to read the result

- If `pyocd` is missing, install it in the venv.
- If `pyserial` is missing, install it in the venv.
- If no probes are detected, the problem is usually OS driver / vendor tooling / USB enumeration.
- If no serial ports are detected, the host cannot yet see the board’s UART interface.
- If a target pack is missing, install it with `--install-packs` or `pyocd pack install ...`.

## Verified

- Non-hardware verification: this document matches the current `host_bootstrap.py` CLI.
- Non-hardware verification: commands explicitly use the venv Python instead of assuming activation.

## Pending verification (esp. hardware)

- Hardware verification: probe enumeration, serial enumeration, and target-pack flows still need to be exercised on real machines with real probes attached.
- Environment verification: OS-driver and vendor-tooling failure modes still need confirmation across actual Windows/macOS setups.
