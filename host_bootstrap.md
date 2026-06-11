# Host Bootstrap

`host_bootstrap.py` is the host-level prerequisite check that should run before
`stage0_check.py`.

It does **not** prove a board works. It only checks whether the machine is
ready to attempt board-level validation.

## What It Checks

- Python package availability for `pyocd`, `pyserial`, `pyyaml`, and
  `python-dotenv`
- `pyocd` CLI availability
- debug-probe enumeration through `pyocd`
- serial-port enumeration through `pyserial`
- board-config loading from `boards/` and any extra `--board-config` files
- pyOCD target-pack availability for the selected board configs

Optional actions:

- reconcile the canonical repo environment with `uv sync --locked` via
  `--install-missing`
- install missing pyOCD target packs with `--install-packs`

What it does **not** do:

- install OS drivers
- install vendor probe software such as SEGGER or ST tooling
- update probe firmware
- prove flashing, UART behavior, or recover behavior on real hardware

## Canonical Commands

Basic host check:

```bash
uv run python host_bootstrap.py
```

That default run is repo-wide: it checks all non-example tracked boards.
For first-time bring-up on one physical bench, prefer `--board-id <board>`.

Install missing Python deps and missing target packs:

```bash
uv run python host_bootstrap.py --install-missing --install-packs
```

Run for one specific tracked board:

```bash
uv run python host_bootstrap.py --board-id nrf52840dk
```

Include an extra board config:

```bash
uv run python host_bootstrap.py \
  --board-config path/to/my_board.yaml \
  --board-id my_board
```

The script auto-loads `.env` if present, so repo-local `PYOCD_*` defaults are
available without manual shell export.

## After It Passes

Run Stage 0 board validation:

```bash
uv run python stage0_check.py --board-id nrf52840dk
```

## Reading The Result

- If `pyocd` is missing, install the canonical repo environment with `uv sync`.
- If `pyserial` is missing, install the canonical repo environment with `uv sync`.
- If `--install-missing` is used, the script repairs the repo env by running
  `uv sync --locked`; it does not do ad hoc per-package installs.
- If `python-dotenv` is missing, repo-local `.env` defaults will not auto-load.
- If no probes are detected, the problem is usually OS driver, vendor tooling,
  or USB enumeration.
- If no serial ports are detected, the host cannot yet see the board’s UART
  interface.
- If a target pack is missing, install it with `--install-packs` or
  `uv run pyocd pack install ...`.

## Verification Status

- Non-hardware verification: this document matches the current
  `host_bootstrap.py` CLI shape.
- Pending hardware verification: probe enumeration, serial enumeration, and
  target-pack flows still need confirmation on real supported hosts.
