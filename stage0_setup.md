# Stage 0 Setup — The Bench Bring-Up Operator Guide

This is the single operator guide for the current bench/setup CLI flow. It takes a fresh machine from
"repo cloned" to a Stage-0-ready board and then to the MCP server. It covers the cross-script sequence,
the operator-facing flags you actually choose, and a consolidated troubleshooting table.

Today these steps are run at a terminal. `setup_host.*` and `host_bootstrap.py` are still pre-server host
bootstrap checks. `stage0_check.py` is the current CLI/operator wrapper for board validation, but that
validation logic is intended to become callable through MCP tools and other
local programmer flows as well so an external agent or local orchestrator can
run the same checks without shelling the whole script. These scripts do not
each carry a standalone doc; this guide is their consolidated home (per
`superpowers/agent_script_doc_playbook.md` §2). For a script's exhaustive flag
list, run it with `--help`. For the MCP server's runtime tools, the descriptions
live in the tool docstrings in `src/pyocd_debug_mcp/server.py` (the MCP client
reads those over the protocol; there is no sidecar doc).

Related docs, each with one home:

- Canonical repo tree and naming rules: [README.md](./README.md)
- Environment bootstrap, pinned interpreter, local-override policy: [init.md](./init.md)

## 1. Purpose Of This Workflow

Use this guide when the repo is cloned and you need the shortest correct path to:

- get a fresh machine ready
- validate one attached board or all tracked boards at Stage 0
- know which script to run next based on the current runtime state

## 2. Entry Conditions

This workflow is the right one when:

- the repo exists locally
- you want to move from raw machine or uncertain host state into Stage 0
- you need board bring-up, not just the MCP server

This workflow is not the right one when:

- you only need the canonical repo tree and naming rules; use [README.md](./README.md)
- you only need exact bootstrap commands and local override policy; use [init.md](./init.md)
- you only need the MCP server's runtime tools; those are described in the `server.py` docstrings, read
  by the MCP client over the protocol

## 3. Ordered Sequence

Run these steps in order from the repo root.

### Step 1: Install `uv`

Windows PowerShell:

```powershell
pip install uv
```

macOS:

```bash
brew install uv
```

### Step 2: Run the OS bootstrap script

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52833dk
```

macOS:

```bash
bash ./setup_host.sh --board-id nrf52840dk
```

Use `--board-id <board>` or `-BoardId <board>` when only one physical bench board is attached and you do
not want unrelated tracked boards to dominate the result.

### Step 3: Run host readiness checks

```bash
uv run python host_bootstrap.py
```

For one board:

```bash
uv run python host_bootstrap.py --board-id nrf52840dk
```

### Step 4: Run Stage 0 board validation

```bash
uv run python stage0_check.py
```

For one board:

```bash
uv run python stage0_check.py --board-id nrf52840dk
```

### Step 5: Start the MCP server after Stage 0 is acceptable

```bash
uv run pyocd-debug-mcp
```

## 3b. Per-Script Essentials

For each script: its purpose in one line, the operator-facing flags worth choosing (run `--help` for the
full list), and what its "ready/done" signal looks like.

### `setup_host.ps1` / `setup_host.sh` — first-run host automation

Installs or repairs the canonical environment and board-family vendor tooling on a fresh machine, then
runs `host_bootstrap.py --install-packs` unless skipped. **Destructive only in the sense of installing
system software / modifying user PATH (Windows).**

- Operator-facing flags: `-BoardId`/`--board-id` (scope to the attached board); `-SkipHostBootstrap`/
  `--skip-host-bootstrap`; `-SkipUvSync`/`--skip-uv-sync`; `-DryRun`/`--dry-run` (print intended actions,
  change nothing).
- Windows additionally automates: Python 3.12 via `winget`, `uv` via `pip`, PATH repair, SEGGER J-Link,
  Nordic nRF Command Line Tools; attempts PATH repair for an existing STM32CubeProgrammer install.
- macOS additionally automates: Homebrew, `uv`, `libusb`, Nordic tools via cask; attempts ST PATH repair.
- Ready signal: `... host setup script completed.` and exit `0`. Exit `1` = script-level failure;
  `setup_host.sh` exit `2` = invalid CLI option.

### `host_bootstrap.py` — non-destructive host readiness check

Checks that the machine can run the canonical Python env, enumerate probes and serial ports, load board
configs, and see the required pyOCD targets. **Does not flash, mass-erase, unlock, or open a long-lived
session.** Safe to rerun.

- Operator-facing flags: `--board-id` (scope); `--install-missing` (reconcile the env with
  `uv sync --locked` if Python deps are missing); `--install-packs` (install missing target packs);
  `--board-config PATH` (extra board file).
- Ready signal: `Host prerequisites and board-target support are ready for stage0_check.py` and exit `0`.
  Exit `1` = a required check failed; exit `2` = CLI usage error.

### `stage0_check.py` — board-level Stage 0 validation

The current CLI/operator surface for Stage 0 board validation. It proves probe + target + SWD read +
silicon identity + virtual COM are present for the selected boards, and can optionally flash a reference
image, read UART, and run a destructive recover cycle. Data-driven: all board facts come from
`boards/<board>.yaml`. Non-destructive **unless** `--reference-firmware` or `--recover-test` is passed.
Treat the board-validation behavior here as shared product logic rather than a permanent CLI-only boundary;
the intended direction is for the same validation operations to become callable through MCP tools and other
local programmer flows too.

- Operator-facing flags: `--board-id` (scope); `--install-packs`; `--port BOARD_ID=PORT` (authoritative
  serial override); `--reference-firmware BOARD_ID=PATH` (flash this artifact); `--expect BOARD_ID=TEXT`
  (required UART substring); `--baudrate BOARD_ID=BAUD`; `--recover-test BOARD_ID` (**destructive** —
  unlock/mass-erase); `--serial-read-seconds N` (default `3.0`).
- Status tokens in output: `[PASS]` succeeded · `[FAIL]` failed/blocked · `[WARN]` opt-in, degraded, or
  needs a human decision · `[INFO]` context.
- Ready signal: exit `0` with either "Automated checks passed and this run covered the requested Stage 0
  validations." (full coverage) or "...not complete until the manual items are validated." (manual items
  remain). Exit `1` = an automated check failed; exit `2` = CLI usage error.

### `uv run pyocd-debug-mcp` — the MCP server

The runtime entrypoint backing `server.py`. In today's shell-first workflow, start it after Stage 0 is
acceptable. Its per-tool behavior (`connect`, `halt`, `read_memory`, …) is documented in the tool
docstrings the MCP client reads over the protocol — there is no sidecar doc. Long-term, board-validation
operations that currently sit behind `stage0_check.py` should also be exposed here as MCP tools, but raw
machine bootstrap still begins outside the server. Operating note: it holds **one** live debug session;
call `connect` before any target tool, and `disconnect` before switching probes. `connect` accepts an
optional `board_id` (or `PYOCD_BOARD_ID` env; plus `board_config`/`PYOCD_BOARD_CONFIG` for a custom board
file) to load that board's facts from `boards/<board>.yaml` through the **same shared loader the Stage 0
scripts use** — then it needs no raw `target`, and `get_board_info` reports the loaded facts.

## 4. Branch Points

- If the machine is fresh or host tooling is uncertain, start with `setup_host` rather than
  `host_bootstrap.py`.
- If `setup_host` was intentionally run with `--skip-host-bootstrap` or `-SkipHostBootstrap`, run
  `uv run python host_bootstrap.py` next.
- If `host_bootstrap.py` reports missing packs, rerun it or `stage0_check.py` with pack installation
  enabled rather than moving directly to the MCP server.
- If `stage0_check.py` reports ambiguous UART selection:
  interactive run -> choose from the prompt
  non-interactive run -> rerun with `--port BOARD_ID=PORT`
- If `stage0_check.py` reports APPROTECT or access-protected symptoms on a Nordic board and destructive
  recovery is acceptable, rerun with `--recover-test <board>`.
- If a run ends with only manual items, treat it as partial Stage 0 completion, not a full bring-up pass.

## 5. Handoffs Between Steps

- From `setup_host` to `host_bootstrap.py`
  Carry forward the board selection. If you bootstrapped only one board family, keep the same
  `--board-id` / `-BoardId` focus in later steps.
- From `host_bootstrap.py` to `stage0_check.py`
  Carry forward any unresolved warnings: missing vendor helper CLI, missing target pack, no probes
  detected, no serial ports detected.
- From `stage0_check.py` back to itself on rerun
  Carry forward the concrete override that solved the failure: `--port BOARD_ID=PORT`,
  `--reference-firmware BOARD_ID=PATH`, `--expect BOARD_ID=TEXT`, `--baudrate BOARD_ID=BAUD`,
  `--recover-test BOARD_ID`.
- From Stage 0 to `pyocd-debug-mcp`
  Carry forward the known-good board target, probe path, and any `.env` defaults such as
  `PYOCD_PROBE_UID` or `PYOCD_TARGET`.

## 6. Consolidated Troubleshooting

Symptom (what you see in output) -> cause -> fix -> what to rerun. Ordered roughly by where in the
sequence it appears.

| Symptom | Cause | Fix -> rerun |
|---|---|---|
| `setup_host.ps1 currently supports Windows host automation only.` / `setup_host.sh currently supports macOS only.` | Wrong setup script for this OS | Run the OS-matching setup script |
| `winget is required ... but was not found.` (Windows) | Unattended install path unavailable | Install Python/vendor tools manually -> rerun `setup_host.ps1` |
| `Python install completed but no python launcher was found on PATH.` / `uv install completed but uv was not found on PATH.` | Install succeeded but PATH is stale | Reopen the shell -> rerun the setup script |
| `[WARN] STM32_Programmer_CLI not found ...` | ST tool missing; no verified silent ST installer | Install STM32CubeProgrammer manually -> rerun `setup_host` or `host_bootstrap.py` |
| `host_bootstrap.py reported that setup is still incomplete.` | Env repaired but probe/serial/pack readiness still failed | Read the `host_bootstrap.py` output, fix the named blocker -> rerun `host_bootstrap.py` |
| `[FAIL] pyOCD not found - run: uv sync` / `pyocd missing` / `pyserial missing` / `pyOCD not found` / `pyserial not found` | Repo environment incomplete | `uv sync` (or `host_bootstrap.py --install-missing`) -> rerun the same script |
| `[FAIL] <path> is missing required field ...` | Invalid board config | Correct the board YAML -> rerun |
| `[WARN] No debug probes detected` / `<board> ... no probes detected` | Board absent, USB/cable (charge-only) issue, driver/tooling issue, or another process owns the probe | Repair host visibility -> rerun `host_bootstrap.py --board-id <board>` |
| `<board> ... probes detected, but none matched this board` | Probe exists but hint/family match was inconclusive | Narrow to the right `--board-id`, fix `probe_hint_terms`, or disconnect unrelated hardware -> rerun `stage0_check.py --board-id <board>` |
| `<board>: target '<target>' not found` / `[WARN] target '<target>' not found` | Required pyOCD target pack missing | Rerun with `--install-packs` (or `uv run pyocd pack install <pack>`) |
| `[FAIL] No serial ports detected` / `COM port not uniquely identifiable: ...` | UART not visible, or auto-detect ambiguous | Repair host USB/vendor tooling, or choose the port in the prompt / rerun with `--port <board>=<port>` |
| `[WARN] <board> appears access-protected.` / `pyOCD found the probe but could not connect to the target MCU` | Locked target (esp. Nordic APPROTECT), or power/cable/firmware issue | If recover is supported and acceptable: rerun with `--recover-test <board>`; else check power/cable/probe firmware |
| `[FAIL] Unable to read <silicon label>` | Silicon-identity read failed, commonly APPROTECT | Recover first, then rerun the normal board check |
| `<silicon label> did not match (actual=..., expected=..., mask=...)` | Wrong board attached, or the config's silicon identity is wrong | Attach the correct board or fix the YAML -> rerun `stage0_check.py --board-id <board>` |
| `Reference firmware file does not exist: ...` | Bad runtime artifact path | Correct the path -> rerun with `--reference-firmware <board>=<path>` |
| `[FAIL] Flash failed for <path>` | Probe lost, target pack missing, or chip access-protected | Confirm prior checks pass (connection first), recover if locked -> rerun flash |
| `UART output did not match expected text` / `UART produced no output` / `Unable to read <port> at <baud> baud` | Wrong firmware, wrong `--expect`, wrong port/baud, busy port, or too-short read window | Flash the intended image, fix `--expect`/`--port`/`--baudrate`, or raise `--serial-read-seconds` -> rerun |
| `Skipped - this board's recover_mode is manual_only` | Board needs recover validation but has no Stage 0 automation for its family yet | Perform the recover proof manually, record it -> rerun the normal check |
| nRF identity/connection fails again after a power cycle | Flashed firmware is likely re-enabling APPROTECT on boot | Rerun `--recover-test <board>` then the normal check; if it repeats every cycle, the firmware is re-locking |

When a tool says "fix host visibility," go back to `setup_host` / `host_bootstrap.py` — do not guess at
probe state from inside Stage 0.

## 7. Board Config Expectations

Use a tracked board config from `boards/`, or pass extra board files with `--board-config`.

Minimum useful fields:

```yaml
board_id: my_board
display_name: "My Board"
mcu_family: rp2040
probe_family: cmsisdap
pyocd_target: rp2040
serial_baudrate: 115200
test_read_address: 0x20000000
```

Useful optional fields:

- `pack_name`
- `silicon_id_address`
- `silicon_id_expected`
- `silicon_id_mask`
- `silicon_id_width_bits`
- `silicon_id_label`
- `probe_hint_terms`
- `serial_hint_terms`
- `reference_uart_patterns`
- `recover_mode`
- `requires_recover_validation`
- `uart_note`

Tracked board YAML must not contain:

- `reference_firmware_path`
- `recovery_image_path`
- project paths
- build commands
- artifact output paths
- any user- or session-scoped path

Examples:

- `boards/nrf52833dk.yaml`
- `boards/nrf52840dk.yaml`
- `boards/nucleo_l476rg.yaml`
- `boards/example_custom_nrf52_board.yaml`
- `boards/example_custom_board.yaml`

If two nearby MCUs can both answer a generic debug read through the same probe family, add
silicon-identity metadata to the board YAML. Stage 0 will then read that register and reject the wrong
attached device even if the probe and target family are otherwise compatible.

## 8. What Stage 0 Automates Vs. Leaves Manual

Automated:

- `pyocd` installed
- `pyserial` installed
- probe visible
- pyOCD target pack available
- SWD connect plus smoke-test register read
- exact silicon identity match, when the board config supplies silicon-id fields
- virtual COM port visible
- optional flash of known-good firmware
- optional UART output capture
- optional recover validation for supported families

Still manual:

- confirm the probe and COM port come from the same physical USB connection
- confirm OS-level driver and probe setup is correct
- confirm UART output is the intended reference behavior if you do not provide `--expect`
- confirm destructive recover behavior is acceptable before using `--recover-test`

Current `recover_mode` values:

- `nrf_pyocd_unlock`
- `manual_only`

## Verification Status

Verified:

- this operator guide's sequence, branch points, handoffs, and per-script essentials match the current
  `setup_host`, `host_bootstrap.py`, and `stage0_check.py` roles, flags, and output
- this flow matches the current `stage0_check.py` CLI shape and shared board loader behavior
- the `nrf52833dk` flash, UART, and recover path is bench-verified on this Mac host when a reference
  artifact is supplied

Pending verification:

- the unattended Windows bootstrap path still needs a real Windows bench run
- the `nucleo_l476rg` reference baseline now exists and builds, but its physical Stage 0 flash and UART
  proof still need a real `nucleo_l476rg` bench run
