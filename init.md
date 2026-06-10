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
- Use `uv sync --no-dev` if you intentionally want a runtime-only install.
- Use `uv run ...` for repo commands so they always run inside the pinned env.
- The MCP Inspector entrypoint is:

```bash
uv run mcp dev src/pyocd_debug_mcp/server.py
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
uv run python stage0_check.py --board-id nucleo_l476rg
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
