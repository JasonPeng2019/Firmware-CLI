# Firmware CLI

`Firmware CLI` is a local embedded-debug and firmware-agent repo built around
`pyOCD`, Stage 0 validation tooling, and an MCP server surface in
`src/pyocd_debug_mcp/`.

This `README.md` is the canonical Phase A source for repo layout and naming
rules. More detailed setup and workflow notes live in the linked docs below.

## What Phase A Delivers

Phase A freezes the repo shape, the local development environment, and the
basic board-validation workflow so later stages can build on one stable
standard.

Today that means:

- one canonical source tree under `src/pyocd_debug_mcp/`
- tracked board definitions in `boards/`
- repo-owned test-firmware scaffolding in `firmware/`
- untracked runtime-output space in `runs/`
- test and harness scaffolding in `tests/`
- a local MCP server entrypoint plus host and Stage 0 validation scripts

## Canonical Tree

```text
Firmware-CLI/
├── .python-version
├── pyproject.toml
├── uv.lock
├── README.md
├── init.md
├── host_bootstrap.py
├── host_bootstrap.md
├── stage0_check.py
├── stage0_setup.md
├── boards/
│   ├── nrf52840dk.yaml
│   └── nucleo_l476rg.yaml
├── firmware/
│   ├── README.md
│   ├── nrf52840dk/
│   │   ├── reference/src/
│   │   ├── reference/build/
│   │   ├── recovery/
│   │   └── bugs/
│   └── nucleo_l476rg/
│       ├── reference/src/
│       ├── reference/build/
│       ├── recovery/
│       └── bugs/
├── runs/
│   └── README.md
├── tests/
│   ├── README.md
│   ├── fixtures/
│   ├── cases/
│   └── harness/
├── src/
│   └── pyocd_debug_mcp/
│       ├── __init__.py
│       ├── local_env.py
│       └── server.py
└── markdowns/
    ├── ROADMAP.md
    ├── firmware_agent_build_plan_concrete (10).md
    ├── firmware_agent_mcp_architecture.md
    └── build_plan_spec_gaps.md
```

## Naming Rules

- Board IDs are lowercase stable identifiers and key all per-board paths.
- Product code lives only under `src/pyocd_debug_mcp/`.
- Repo-owned reference firmware lives under `firmware/<board>/reference/`.
- The canonical symbol-bearing baseline artifact name is
  `firmware/<board>/reference/build/firmware.elf`.
- Additional flash artifacts may sit beside `firmware.elf`, but
  `firmware.elf` is the stable symbol-resolution artifact name.
- Recovery assets live under `firmware/<board>/recovery/`.
- Bug variants live under `firmware/<board>/bugs/<id>__<slug>/`.
- Runtime outputs live under `runs/<session_id>/...`.
- User firmware never lives in this repo and is always supplied later as
  runtime input.

## Environment Standard

- `.python-version` is committed and pins the team interpreter to `3.12`.
- Use `uv` as the canonical environment and command surface.
- Install `uv` first on a raw machine; this repo does not assume it already
  exists.
  Windows: `pip install uv`
  macOS: `brew install uv`
- Use `uv sync` to create `.venv/` and install the locked dependency set.
- Use `uv run ...` for repo commands so they always run inside the pinned env.
- `.env` is optional, gitignored, and auto-loaded by the MCP server and the
  Phase A host scripts when present.
- `.env` currently carries `PYOCD_PROBE_UID` and `PYOCD_TARGET`.
- `pyocd.local.yaml` is an optional per-developer pyOCD override file and is
  gitignored.
- `pyocd.yaml` is optional and only belongs in the repo once the team has a
  real shared pyOCD option to commit.
- Host and Stage 0 validation default to all non-example tracked boards.
- For first-time bring-up on one physical bench, use `--board-id <board>` to
  scope the run to the board you actually have attached.

## Board YAML Policy

Tracked board YAML is hardware-focused.

Allowed examples:

- board identity and display name
- MCU family
- probe family
- `pyocd_target`
- baudrate
- probe and serial hint terms
- recover policy such as `requires_recover_validation` and `recover_mode`
- UART expectation metadata

Forbidden examples:

- `reference_firmware_path`
- `recovery_image_path`
- project paths
- build commands
- artifact output paths
- any user- or session-scoped path

Canonical artifact locations are part of the repo tree and naming standard, not
tracked board-config fields in this Phase A layout.

## Main Workflows

Bootstrap the environment:

```bash
uv sync
```

On Windows, the preferred unattended host bootstrap entry point is:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52840dk
```

That script can install Python/`uv` if needed, sync the repo, repair vendor
tool `PATH`s, and automate the Nordic `nrfjprog` path for J-Link boards.

On macOS, the preferred host bootstrap entry point is:

```bash
bash ./setup_host.sh --board-id nrf52840dk
```

That script can install `uv`, `libusb`, and the Nordic Homebrew casks needed
for `nrfjprog`. ST-LINK boards may still require a one-time manual
STM32CubeProgrammer install before the agent can fully self-pilot.

Run host bootstrap for all tracked boards:

```bash
uv run python host_bootstrap.py
```

Run Stage 0 validation for all tracked boards:

```bash
uv run python stage0_check.py
```

On Windows PowerShell, run the same command from the repo root:

```powershell
uv run python stage0_check.py
```

If Stage 0 cannot auto-resolve the UART endpoint, it now prompts in an
interactive terminal. In non-interactive runs, re-run with
`--port BOARD_ID=PORT`.

Run host bootstrap and Stage 0 for one board on your bench:

```bash
uv run python host_bootstrap.py --board-id nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk
```

Windows PowerShell:

```powershell
uv run python host_bootstrap.py --board-id nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk
```

Vendor-assisted serial auto-detect is used when the helper CLI is available:

- Nordic + J-Link boards: `nrfjprog --com`
- ST-LINK boards: `STM32_Programmer_CLI -l`

These CLIs improve auto-detect but are not required for every board. If they
are missing or a board remains ambiguous, Stage 0 falls back to prompting or
an explicit `--port` override.

Tracked board YAML now uses a typed `recover_mode` selector rather than a
free-form recover command string. Today `stage0_check.py` supports:

- `nrf_pyocd_unlock` for Nordic APPROTECT recovery through pyOCD's built-in
  unlock and mass-erase flow
- `manual_only` for boards that need recover validation but do not yet have an
  automated Stage 0 implementation

Start the MCP server:

```bash
uv run pyocd-debug-mcp
```

## Docs

- Setup and bootstrap: [init.md](./init.md)
- Host readiness checks: [host_bootstrap.md](./host_bootstrap.md)
- Stage 0 validation flow: [stage0_setup.md](./stage0_setup.md)
- Roadmap: [markdowns/ROADMAP.md](./markdowns/ROADMAP.md)
- Concrete build plan: [markdowns/firmware_agent_build_plan_concrete (10).md](./markdowns/firmware_agent_build_plan_concrete%20%2810%29.md)
- Architecture notes: [markdowns/firmware_agent_mcp_architecture.md](./markdowns/firmware_agent_mcp_architecture.md)

Until later roadmap items intentionally revise it, this `README.md` is the
canonical repo-layout and naming reference for Phase A.
