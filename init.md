# Environment Bootstrap

This document is the detailed setup guide for the Phase A repo standard.

The root [README.md](./README.md) is the canonical layout and naming reference.
This file goes deeper on environment bootstrap, local overrides, and the main
developer command surface.

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — the canonical environment manager for
  this repo
- **A debug probe** — CMSIS-DAP, ST-Link, J-Link, or equivalent, attached to a
  supported Cortex-M target
- **Platform USB support for the probe** — libusb, vendor drivers, or vendor
  tooling as needed by the probe family

The team-standard interpreter is pinned in `.python-version` as `3.12`.
`pyproject.toml` still declares the broader package floor, but development and
validation should use the pinned Phase A environment.

## Raw Machine Setup

If this is a fresh machine, do these steps first.

On Windows, the preferred unattended entry point is:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52833dk
```

That script can install Python and `uv`, run `uv sync --locked`, repair common
vendor-tool `PATH` issues, automate Nordic `nrfjprog` setup for J-Link
boards, and then resolve board selection through the same validated loader used
by the Python Phase A tools.

### 1. Install `uv`

Windows (PowerShell):

```powershell
pip install uv
```

macOS:

```bash
brew install uv
```

Then open a new shell so `uv` is on `PATH`.

If `uv` is not installed yet, nothing else in this repo will work.

### 2. Do not create a venv manually

You do not need to run `python -m venv ...` and you do not need to activate a
virtual environment yourself.

This repo uses `uv` as the canonical environment manager. The first `uv sync`
creates `.venv/` automatically and installs the locked dependency set.

### 3. Bootstrap the repo environment

From the repo root:

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

After that, use `uv run ...` for repo commands.

## Native Probe Dependencies

If probe enumeration fails, install the missing host-level dependency first.

- **macOS:** `brew install libusb`
- **Debian / Ubuntu:** `sudo apt install libusb-1.0-0`
- **Windows:** install the probe’s required USB driver path or vendor tooling

Linux users may also need pyOCD’s udev rules from the upstream pyOCD repo.

## Canonical Bootstrap Flow

Run all commands from the repo root.

### macOS / Linux

```bash
uv sync
uv run pyocd list
uv run python host_bootstrap.py
uv run pyocd-debug-mcp
```

### Windows (PowerShell)

```powershell
uv sync
uv run pyocd list
uv run python host_bootstrap.py
uv run pyocd-debug-mcp
```

Notes:

- `uv sync` creates `.venv/`, installs runtime and dev dependencies, and honors
  the committed `uv.lock`.
- `uv sync` is the step that creates the repo venv; there is no separate
  manual venv creation step.
- Use `uv sync --no-dev` if you intentionally want a runtime-only install.
- Use `uv run ...` for repo commands so they always run inside the pinned env.
- `host_bootstrap.py` and `stage0_check.py` default to all non-example tracked
  boards. For first-time bring-up on one physical bench, prefer
  `--board-id <board>`.
- `stage0_check.py` now tries vendor-assisted UART auto-detect where supported:
  `nrfjprog --com` for Nordic J-Link boards and
  `STM32_Programmer_CLI -l` for ST-LINK boards.
- If UART auto-detect remains ambiguous, the script prompts in an interactive
  terminal. In non-interactive runs, re-run with `--port BOARD_ID=PORT`.
- The MCP Inspector entrypoint is:

```bash
uv run mcp dev src/pyocd_debug_mcp/server.py
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

## Local Override Policy

Machine-local values must not be committed as tracked repo state.

Use these override layers:

- **`.env`** — optional, gitignored, auto-loaded by the MCP server and the
  Phase A host scripts. Use it for:
  - `PYOCD_PROBE_UID`
  - `PYOCD_TARGET`
- **`pyocd.local.yaml`** — optional, gitignored, for per-developer pyOCD
  tweaks once needed
- **`pyocd.yaml`** — optional and committed only when the team has a real
  shared pyOCD option to standardize

Tracked board YAML remains hardware-focused and must not store user paths,
build commands, or artifact output locations.

The `connect` tool still accepts `unique_id` and `target` arguments directly,
which override `.env` defaults at runtime.

## Main Developer Commands

```bash
uv run python host_bootstrap.py
uv run python stage0_check.py
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk
uv run pyocd-debug-mcp
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
```

## Related Docs

- Repo layout and naming: [README.md](./README.md)
- Host readiness checks: [host_bootstrap.md](./host_bootstrap.md)
- Stage 0 validation flow: [stage0_setup.md](./stage0_setup.md)
- Roadmap: [markdowns/ROADMAP.md](./markdowns/ROADMAP.md)

## Verification Status

Verified:

- The command surface documented here matches the current checked-in repo.
- The `nrf52833dk` bootstrap plus Stage 0 flow is bench-verified on this Mac
  host.

Pending verification:

- The unattended Windows bootstrap path still needs a real Windows bench run.
- The STM32 board path remains later bench work.
