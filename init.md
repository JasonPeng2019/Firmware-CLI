# Environment Bootstrap

This is the operator-facing bootstrap guide for getting a fresh machine to the
point where the repo scripts can mostly self-pilot.

The root [README.md](./README.md) is the canonical layout and naming reference.
This file goes deeper on first-run setup, local overrides, and the command
sequence that gets you from a raw machine to Stage 0 and the MCP server.

## Prerequisites

- `uv` as the canonical environment manager for this repo
- a supported debug probe and target board
- host USB support for the probe family in use

The team-standard interpreter is pinned in `.python-version` as `3.12`.

## Raw Machine Setup

If this is a fresh machine, do these steps first.

### 1. Install `uv`

Windows PowerShell:

```powershell
pip install uv
```

macOS:

```bash
brew install uv
```

Open a new shell after install so `uv` is on `PATH`.

### 2. Use the setup script for your OS

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52840dk
```

macOS:

```bash
bash ./setup_host.sh --board-id nrf52840dk
```

These scripts can:

- repair or install the canonical repo environment
- install or repair vendor helper tooling where automation exists
- run `host_bootstrap.py --install-packs`

If the selected board needs Nordic `nrfjprog` and the Windows script cannot
complete that installer because the host requires admin approval, do the
one-time manual Windows fallback:

```powershell
winget install --id NordicSemiconductor.JLink --exact --accept-package-agreements --accept-source-agreements --silent
Invoke-WebRequest -UseBasicParsing "https://nsscprodmedia.blob.core.windows.net/prod/software-and-other-downloads/desktop-software/nrf-command-line-tools/sw/versions-10-x-x/10-24-2/nrf-command-line-tools-10.24.2-x64.exe" -OutFile "$env:TEMP\nrf-command-line-tools-10.24.2-x64.exe"
Start-Process -Verb RunAs -FilePath "$env:TEMP\nrf-command-line-tools-10.24.2-x64.exe"
```

Then reopen the terminal and rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52840dk
```

### 3. Do not create or activate a venv manually

You do not need to run `python -m venv ...`, activate `.venv`, or deactivate it
later for repo commands.

This repo uses `uv` as the canonical environment manager. The first `uv sync`
creates `.venv/` automatically and installs the locked dependency set.

## Canonical Bootstrap Flow

Run all commands from the repo root.

### Shared command sequence

```bash
uv sync
uv run pyocd list
uv run python host_bootstrap.py
uv run python stage0_check.py --board-id nrf52840dk
uv run pyocd-debug-mcp
```

Windows PowerShell uses the same `uv run ...` commands from the repo root.

### What each step does

- `uv sync`
  Creates `.venv/` and installs the locked dependency set.
- `uv run pyocd list`
  Quick probe-enumeration smoke test.
- `uv run python host_bootstrap.py`
  Host readiness check for dependencies, probe visibility, serial visibility,
  board configs, and target packs.
- `uv run python stage0_check.py --board-id <board>`
  Board-level Stage 0 validation.
- `uv run pyocd-debug-mcp`
  Starts the MCP server after Stage 0 is acceptable.

## Native Probe Dependencies

If probe enumeration fails, install or repair the host-level dependency first.

- macOS: `brew install libusb`
- Debian / Ubuntu: `sudo apt install libusb-1.0-0`
- Windows: install the probe's required USB driver path or vendor tooling

Linux users may also need pyOCD's udev rules from the upstream pyOCD repo.

## Stage 0 Commands By OS

macOS / Linux:

```bash
uv run python stage0_check.py
uv run python stage0_check.py --board-id nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk --recover-test nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk --port nrf52840dk=/dev/tty.usbmodemXXXX
uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=path/to/firmware.elf
```

Windows PowerShell:

```powershell
uv run python stage0_check.py
uv run python stage0_check.py --board-id nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk --recover-test nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk --port nrf52840dk=COM8
uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=path/to/firmware.elf
```

When UART auto-detect is supported, `stage0_check.py` tries:

- `nrfjprog --com` for Nordic J-Link boards
- `STM32_Programmer_CLI -l` for ST-LINK boards

If that still leaves the port ambiguous, interactive runs prompt you to pick a
port. Non-interactive runs fail with an explicit `--port BOARD_ID=PORT` rerun
hint.

## Local Override Policy

Machine-local values must not be committed as tracked repo state.

Use these override layers:

- `.env`
  Optional, gitignored, auto-loaded by the MCP server and the Phase A host
  scripts. Use it for `PYOCD_PROBE_UID` and `PYOCD_TARGET`.
- `pyocd.local.yaml`
  Optional, gitignored, for per-developer pyOCD tweaks once needed.
- `pyocd.yaml`
  Optional and committed only when the team has a real shared pyOCD option to
  standardize.

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
- Bench bring-up operator guide (setup_host, host_bootstrap, stage0_check): [stage0_setup.md](./stage0_setup.md)
- MCP server runtime tools: documented in the tool docstrings in `src/pyocd_debug_mcp/server.py` (read by the MCP client over the protocol)
- Roadmap: [markdowns/ROADMAP.md](./markdowns/ROADMAP.md)

## Verification Status

Verified:

- non-hardware verification: this document's command sequence and related-doc
  links match the current repo layout and root scripts

Pending verification:

- first-run bootstrap behavior on a truly fresh Windows host
- first-run bootstrap behavior on a truly fresh macOS host
