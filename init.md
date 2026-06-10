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

### 4. Install and run

Each block below is the full sequence — pin the interpreter, build the
environment, verify the probe, and start the server. Run it from the project
root.

**macOS / Linux:**

```bash
uv python pin 3.12         # pin the interpreter (one-time; commit .python-version)
uv sync                    # create ./.venv, install deps, write uv.lock
uv run pyocd list          # verify the probe is visible; copy its unique ID
uv run pyocd-debug-mcp     # start the server
```

**Windows (PowerShell):**

```powershell
# If an earlier `echo > .python-version` left a UTF-16 file, remove it first.
Remove-Item .python-version -ErrorAction SilentlyContinue
uv python pin 3.12         # pin the interpreter (writes valid UTF-8)
uv sync                    # create .\.venv, install deps, write uv.lock
uv run pyocd list          # verify the probe is visible; copy its unique ID
uv run pyocd-debug-mcp     # start the server
```

`uv python pin` writes a clean `.python-version` (avoiding PowerShell's UTF-16
redirection trap). `uv sync` creates a gitignored `.venv/` and a committed
`uv.lock`, so a teammate reproduces the exact environment with the same command;
use `uv sync --no-dev` for a runtime-only install. The server speaks the MCP
stdio transport — point your MCP client (Claude Desktop, the MCP Inspector,
etc.) at the `uv run pyocd-debug-mcp` command. To test interactively instead:

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
