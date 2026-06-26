# Environment Bootstrap

This is the operator-facing bootstrap guide for getting a machine to the point
where the repo scripts can mostly self-pilot after a short developer setup.

The root [README.md](./README.md) is the canonical layout and naming reference.
This file goes deeper on first-run setup, local overrides, and the command
sequence that gets you from a raw machine to Stage 0 and the MCP server.
Today that flow is shell-first, but the intended architecture is that
board-validation behavior lives in shared internal code that can be called both
from `stage0_check.py`, from MCP tools, and from local programmer flows; only
raw host bootstrap remains pre-server.

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
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52833dk
```

macOS:

```bash
bash ./setup_host.sh --board-id nrf52833dk
```

These scripts can:

- repair or install the canonical repo environment
- install or repair vendor helper tooling where automation exists
- run `host_bootstrap.py --install-packs`
- optionally provision the local Zephyr workspace and SDK needed for
  repo-owned firmware rebuilds when you pass `-EnsureZephyrBuildEnv` on Windows
  or `--ensure-zephyr-build-env` on macOS

This bootstrap is intentionally narrower than a "fully self-installing fresh
machine" claim. It may still rely on one-time manual vendor-driver or
vendor-tool setup that an engineer would already need for normal board
debugging. After that bootstrap, the repo-owned readiness checks, Stage 0
validation, MCP server, and turnkey runtime are expected to behave portably on
the supported host and board matrix.

If you want the optional Nordic `nrfjprog` helper and the Windows script cannot
complete that installer because the host requires admin approval, do the
one-time manual Windows fallback:

```powershell
winget install --id NordicSemiconductor.JLink --exact --accept-package-agreements --accept-source-agreements --silent
Invoke-WebRequest -UseBasicParsing "https://nsscprodmedia.blob.core.windows.net/prod/software-and-other-downloads/desktop-software/nrf-command-line-tools/sw/versions-10-x-x/10-24-2/nrf-command-line-tools-10.24.2-x64.exe" -OutFile "$env:TEMP\nrf-command-line-tools-10.24.2-x64.exe"
Start-Process -Verb RunAs -FilePath "$env:TEMP\nrf-command-line-tools-10.24.2-x64.exe"
```

Then reopen the terminal and rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52833dk
```

`nrfjprog` improves Nordic serial auto-detect and provides a fallback flashing
path, but it is not the core prerequisite for normal J-Link-based Stage 0
bring-up. The core prerequisite is a working SEGGER J-Link install/driver path.

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
uv run python stage0_check.py --board-id nrf52833dk
uv run pyocd-debug-mcp
```

Windows PowerShell uses the same `uv run ...` commands from the repo root.

### Rebuild-capable Zephyr bootstrap

If the host must let an agent edit repo firmware, rebuild it, and flash it
without assuming preinstalled `NCS`, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nucleo_l476rg -EnsureZephyrBuildEnv
uv run pyocd-zephyr-build --ensure-only
```

```bash
bash ./setup_host.sh --board-id nucleo_l476rg --ensure-zephyr-build-env
uv run pyocd-zephyr-build --ensure-only
```

The helper resolves build prerequisites in this order:

- reuse `ZEPHYR_WORKSPACE_DIR`
- reuse the workspace implied by `ZEPHYR_BASE`
- reuse a current `west` workspace above the working directory
- reuse `~/zephyrproject`
- reuse a detected `NCS` workspace when one already exists
- otherwise bootstrap a managed upstream Zephyr workspace pinned to `v4.3.0`

SDK resolution follows the same policy:

- reuse `ZEPHYR_SDK_INSTALL_DIR`
- reuse a workspace-adjacent SDK such as `ncs/toolchains/.../opt/zephyr-sdk`
- reuse a standard Zephyr SDK location already on disk
- otherwise install a managed SDK into the local cache through the repo
  helper's own archive-download and setup flow

Current support boundary:

- Windows: managed bootstrap supported
- macOS Apple Silicon: managed bootstrap supported
- macOS Intel (`x86_64`): current Zephyr releases do not support managed SDK
  install, so point `ZEPHYR_SDK_INSTALL_DIR` at a preinstalled older supported
  SDK if you need local rebuilds on that host

Reference build commands:

```bash
uv run pyocd-zephyr-build --app-dir firmware/nucleo_l476rg/reference/src --build-dir firmware/nucleo_l476rg/reference/build --board nucleo_l476rg
uv run pyocd-zephyr-build --app-dir firmware/nrf52833dk/reference/src --build-dir firmware/nrf52833dk/reference/build --board nrf52833dk/nrf52833
```

The helper keeps the Zephyr build tree in place and defaults to incremental
`--pristine auto` rebuilds. Use `--pristine always` only when an agent needs a
forced clean reconfigure.

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

### Known-good Stage 0 commands by board

Windows PowerShell, STM32 `nucleo_l476rg`:

```powershell
uv run python host_bootstrap.py --board-id nucleo_l476rg --install-packs
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
```

Windows PowerShell, Nordic `nrf52833dk`:

```powershell
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
```

Use the STM32 form when proving the Nucleo-L476RG path on a fresh Windows host:
the `--install-packs` flag is the repo-standard way to provision the pinned
STM32L4 pack before Stage 0 tries to attach and flash.

## Native Probe Dependencies

If probe enumeration fails, install or repair the host-level dependency first.

- macOS: `brew install libusb`
- Debian / Ubuntu: `sudo apt install libusb-1.0-0`
- Windows: install the probe's required USB driver (see the per-family steps below)

Linux users may also need pyOCD's udev rules from the upstream pyOCD repo.

### Windows ST-Link driver (Nucleo / ST-Link boards)

On Windows the ST-Link enumerates as a composite device: its virtual COM port
gets Windows' generic serial driver automatically (so a `COM*` port appears even
when the debug side is unusable), but the **debug interface** needs a driver
pyOCD can talk to. The signature of this problem is `uv run pyocd list` printing
`No available debug probes are connected` while a `COM*` port is still visible.

1. Install the **ST-Link driver**. The representative path (what an STM32
   developer typically already has) is **STM32CubeProgrammer** — it bundles the
   driver and lets you independently confirm the board connects. The standalone
   **STSW-LINK009** driver also works. Accept any Windows driver-install prompt
   during setup.
2. Unplug and replug the board.
3. Verify:

   ```powershell
   uv run pyocd list
   ```

   The ST-Link should appear with a unique ID and the board name. Verified on a
   real Windows host: ST's driver alone is sufficient for pyOCD here — **no
   WinUSB/Zadig step was required**.
4. **Fallback only if step 3 still shows no probe:** pyOCD reaches ST-Link through
   libusb, which on some setups needs the debug interface bound to **WinUSB**. Use
   **Zadig** to install WinUSB on the **ST-Link debug interface** — not the `COM*`
   serial interface, or you lose the virtual COM port.

Operating note: the ST-Link is exclusive-access. Close STM32CubeProgrammer (and
any IDE or other pyOCD session) before running `pyocd list`, `stage0_check.py`,
or the MCP server, or the probe looks missing because another process holds it.

## Target Packs (CMSIS-Pack)

pyOCD resolves a board's exact target (for example `stm32l476rgtx`) from a
CMSIS-Pack. Targets pyOCD does not build in are provisioned **deterministically**
from `packs/manifest.yaml`: each pack is pinned by direct URL + sha256, fetched on
demand, verified, and loaded by pyOCD via its `pack` option in the shared backend.
This is the shipped path and it does **not** depend on the live `pyocd pack` index.

Provisioning is automatic — fetch any missing pinned packs with:

```powershell
uv run python host_bootstrap.py --install-packs
```

This downloads each missing pack into `packs/`, verifies its sha256, and the
target then resolves identically for `stage0_check.py`, the MCP server, and the
Stage 1 harness — offline after the first fetch.

**Do not use `pyocd pack update` / `pyocd pack install` for this.** That
index-based flow bulk-fetches ~1500 vendor descriptors from many servers and
**silently drops whole families** (e.g. STM32L4) on restrictive or slow networks,
so `pyocd pack install stm32l476` can report `No matching devices` even when the
board and connection are fine. The pinned manifest removes that single point of
failure. (See [packs/live_index_repair.md](./packs/live_index_repair.md) for
diagnosing and repairing the live index itself if you need it for other targets.)

If you do need the live index repaired for interactive pyOCD pack commands, run:

```powershell
uv run pyocd-pack-repair
```

Or repair only the exact failing STM32L4 DFP:

```powershell
uv run pyocd-pack-repair --vendor Keil --pack-name STM32L4xx_DFP
```

To add or update a pin, or to fetch a pack manually when the bench has no network,
see [packs/README.md](./packs/README.md).

## Stage 0 Commands By OS

macOS / Linux:

```bash
uv run python stage0_check.py
uv run python stage0_check.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --recover-test nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --port nrf52833dk=/dev/tty.usbmodemXXXX
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=path/to/firmware.elf
```

Windows PowerShell:

```powershell
uv run python stage0_check.py
uv run python stage0_check.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --recover-test nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --port nrf52833dk=COM8
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=path/to/firmware.elf
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
  scripts. Use it for `PYOCD_PROBE_UID` and `PYOCD_TARGET`, and optionally
  `PYOCD_BOARD_ID` / `PYOCD_BOARD_CONFIG` to have the server resolve a board's
  facts from `boards/<board>.yaml` through the shared loader (then `connect`
  needs no raw target; the `get_board_info` tool reports the loaded facts).
  The same file also carries the turnkey brain's provider settings:
  `PYOCD_TURNKEY_PROVIDER`, optional `PYOCD_TURNKEY_MODEL`, and provider
  credentials such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.
- `pyocd.local.yaml`
  Optional, gitignored, for per-developer pyOCD tweaks once needed.
- `pyocd.yaml`
  Optional and committed only when the team has a real shared pyOCD option to
  standardize.

Tracked board YAML remains hardware-focused and must not store user paths,
build commands, or artifact output locations.

The `connect` tool still accepts `unique_id`, `target`, `board_id`, and
`board_config` arguments directly, which override the matching `.env` defaults
at runtime. An explicit `target` takes precedence over a board config's
`pyocd_target`.

## Main Developer Commands

```bash
uv run python host_bootstrap.py
uv run python stage0_check.py
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk
uv run pyocd-debug-mcp
uv run pyocd-debug-brain --help
uv run pyocd-debug-brain run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider claude-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain benchmark --case-id nrf52833dk__k001_reference_green --model <model>
uv run pyocd-debug --help
uv run pyocd-debug
uv run pyocd-debug run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug benchmark --case-id nrf52833dk__k001_reference_green
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
```

Turnkey notes:

- `pyocd-debug-brain` launches the local MCP server itself; do not pre-launch
  the server for the normal turnkey path.
- `pyocd-debug` is the new operator-facing CLI over the same brain/runtime:
  - no args launches an interactive REPL shell
  - `run` and `benchmark` reuse the same turnkey logic with prettier live
    rendering
  - `history`, `show`, and `rerun` inspect saved `runs/<session_id>/...`
    artifacts
  - the REPL now defaults to summary-first rendering; use `/raw on` to show
    completed raw provider turns live
  - the REPL now supports persistent repair/artifact context:
    - `/workspace`
    - `/build-command`
    - `/flash-artifact`
    - `/elf`
  - the REPL now supports guided commands:
    - `/verify`
    - `/diagnose`
    - `/repair`
  - the REPL now supports artifact shortcuts:
    - `/prompt`
    - `/diff`
    - `/serial`
    - `/score`
    - `/events`
  - in non-TTY output contexts it falls back to plain printing instead of
    requiring Rich live rendering support
- Valid turnkey providers are:
  - `openai-api`
  - `anthropic-api`
  - `codex-cli`
  - `claude-cli`
- API-backed providers use native SDK credentials:
  - `OPENAI_API_KEY` for `openai-api`
  - `ANTHROPIC_API_KEY` for `anthropic-api`
- CLI-backed providers inherit the CLI's own auth:
  - `codex-cli` can use the existing Codex/ChatGPT subscription or Codex's
    API-key login
  - `claude-cli` can use the existing Claude subscription/OAuth token or
    `ANTHROPIC_API_KEY`
- Freeform `run` mode is diagnose/verify only unless you also supply both:
  - `--workspace-root`
  - `--build-command`
- Benchmark mode reuses the frozen 12-case corpus from
  `pilot_v1_plus_b003_b004`.
- current UX-layer status:
  - Pass 1 is implemented with structured brain events, live tool/progress
    rendering, evidence summaries, and raw-output toggling after completed
    turns
  - true token-level provider streaming is still the next follow-up

## Related Docs

- Repo layout and naming: [README.md](./README.md)
- Bench bring-up operator guide (setup_host, host_bootstrap, stage0_check): [stage0_setup.md](./stage0_setup.md)
- MCP server runtime tools: documented in the tool docstrings in `src/pyocd_debug_mcp/server.py` (read by the MCP client over the protocol)
- Roadmap: [markdowns/ROADMAP.md](./markdowns/ROADMAP.md)

## Verification Status

Verified:

- non-hardware verification: this document's command sequence and related-doc
  links match the current repo layout and root scripts
- the shared-service Stage 0 path is bench-proven on this Mac host for the
  scoped pair: `nucleo_l476rg` and `nrf52833dk`
- the canonical Windows `R0` bootstrap path has been verified on a real
  Windows host
- the Codex-backed turnkey path is now live-proven on the scoped pair through
  the full frozen `pilot_v1_plus_b003_b004` suite

Still open:

- the Claude CLI turnkey path is not yet live-proven on this host because
  `uv run pyocd-debug-brain run --provider claude-cli --model sonnet ...`
  currently fails before any board action with a provider-side 404 for the
  resolved model slug
- Windows ST-Link probe visibility is verified on a real Windows host: after
  installing the ST-Link driver via STM32CubeProgrammer and replugging, pyOCD
  enumerates the Nucleo ST-Link with no WinUSB/Zadig step
- the CMSIS-Pack `No matching devices` failure is a partial live index (ST
  families missing) reproduced across clean rebuilds on this Windows host; it is
  worked around deterministically by the pinned-fetch provisioning
  (`packs/manifest.yaml` + `host_bootstrap.py --install-packs`), which is
  bench-verified to resolve the exact `stm32l476rgtx` target from a local pack

Pending verification:

- `nrf52840dk` remains a retained alternate Nordic profile and still needs live
  proof if future support for that board becomes a project goal
