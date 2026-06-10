# pyocd-debug-mcp

An MCP server that exposes embedded debug, flash, and inspection control over an
Arm Cortex-M target via [pyOCD](https://pyocd.io). It runs locally on a machine
with a debug probe physically attached over USB.

## Setup

### 1. Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — manages the Python version, virtual
  environment, and dependencies.
- **Python 3.10+** — the floor required by the MCP SDK. The project pins a
  concrete version via `.python-version` (3.12); uv installs it automatically.
- **A debug probe** — CMSIS-DAP (DAPLink), ST-Link, J-Link, etc., connected via
  USB, attached to a Cortex-M target.

### 2. Native dependency: libusb

pyOCD talks to probes through libusb. A bundled copy ships with pyOCD's
dependencies on most platforms, but if probe enumeration fails, install the
system package:

- **macOS:** `brew install libusb`
- **Debian / Ubuntu:** `sudo apt install libusb-1.0-0`
- **Windows:** install the probe's WinUSB driver (e.g. via Zadig for generic
  CMSIS-DAP probes); vendor probes like ST-Link ship their own driver.

### 3. Linux only: udev rules

On Linux you must grant user-space access to the probe, or pyOCD will not see
it. pyOCD ships udev rules in its
[repository `udev/` directory](https://github.com/pyocd/pyOCD/tree/main/udev);
copy the relevant `.rules` file into `/etc/udev/rules.d/`, then reload:

```bash
sudo udevadm control --reload
sudo udevadm trigger
```

Unplug and replug the probe afterward.

### 4. Install

From the project root:

Powershell:
Remove-Item .python-version
uv python pin 3.12

```bash
# Pin the interpreter the environment is built from (one-time; commit this file).
echo "3.12" > .python-version

# Create ./.venv and install runtime + dev dependencies, writing uv.lock.
uv sync
```

This creates a gitignored `.venv/` and a committed `uv.lock`. A teammate runs
the same `uv sync` to reproduce the exact environment. For a runtime-only
install (no dev tools), use `uv sync --no-dev`.

### 5. Verify the probe is visible

```bash
uv run pyocd list
```

If your probe appears here, the server can reach it. Copy the unique ID shown
for use below.

### 6. Run the server

```bash
uv run pyocd-debug-mcp
```

The server speaks the MCP stdio transport. Point your MCP client (Claude
Desktop, the MCP Inspector, etc.) at this command. To test interactively:

```bash
uv run mcp dev src/pyocd_debug_mcp/server.py
```

## Local overrides

Nothing on one machine should be load-bearing for anyone else. Per-developer
settings live outside version control:

- **`.env`** — copy from `.env.example`. Set `PYOCD_PROBE_UID` (your probe's
  unique ID) and `PYOCD_TARGET` (your chip, e.g. `stm32f407vg`). These become
  the defaults for the `connect` tool. Gitignored.
- **`pyocd.yaml`** (committed) for shared, project-wide pyOCD options; a
  gitignored `pyocd.local.yaml` for per-developer tweaks.

The `connect` tool also accepts `unique_id` and `target` arguments directly,
which override the environment defaults.

## Development

```bash
uv run pytest        # tests
uv run ruff check .  # lint
uv run ruff format . # format
uv run mypy src      # type check
```

## Available tools

`connect`, `disconnect`, `get_state`, `halt`, `resume`, `step`, `reset`,
`read_core_register`, `write_core_register`, `read_memory`, `read_memory_block`,
`write_memory`, `set_breakpoint`, `remove_breakpoint`.
