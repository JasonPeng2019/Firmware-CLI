# Stage 0 Setup

This is the Stage 0 operator guide. It describes the multi-script workflow from
host bootstrap through board-level Stage 0 validation. It is not the script doc
for any single executable.

Exact script interfaces live in:

- [setup_host.md](./setup_host.md)
- [host_bootstrap.md](./host_bootstrap.md)
- [stage0_check.md](./stage0_check.md)

## 1. Purpose Of This Workflow

Use this guide when the repo is cloned and you need the shortest correct path
to:

- get a fresh machine ready
- validate one attached board or all tracked boards at Stage 0
- know which script to run next based on the current runtime state

Do not use this guide as the only reference when operating one script directly.
Switch to that script's own doc for exact flags, logs, outputs, failure
symptoms, and rerun guidance.

## 2. Entry Conditions

This workflow is the right one when:

- the repo exists locally
- you want to move from raw machine or uncertain host state into Stage 0
- you need board bring-up, not just the MCP server

This workflow is not the right one when:

- you only need the canonical repo tree and naming rules; use [README.md](./README.md)
- you only need exact bootstrap commands and local override policy; use [init.md](./init.md)
- you only need one script's exact contract; use that script doc directly

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

Use `--board-id <board>` or `-BoardId <board>` when only one physical bench
board is attached and you do not want unrelated tracked boards to dominate the
result.

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

## 4. Branch Points

- If the machine is fresh or host tooling is uncertain, start with `setup_host`
  rather than `host_bootstrap.py`.
- If `setup_host` was intentionally run with `--skip-host-bootstrap` or
  `-SkipHostBootstrap`, run `uv run python host_bootstrap.py` next.
- If `host_bootstrap.py` reports missing packs, rerun it or `stage0_check.py`
  with pack installation enabled rather than moving directly to the MCP server.
- If `stage0_check.py` reports ambiguous UART selection:
  interactive run -> choose from the prompt
  non-interactive run -> rerun with `--port BOARD_ID=PORT`
- If `stage0_check.py` reports APPROTECT or access-protected symptoms on a
  Nordic board and destructive recovery is acceptable, rerun with
  `--recover-test <board>`.
- If a run ends with only manual items, treat it as partial Stage 0 completion,
  not a full bring-up pass.

## 5. Handoffs Between Steps

- From `setup_host` to `host_bootstrap.py`
  Carry forward the board selection. If you bootstrapped only one board family,
  keep the same `--board-id` / `-BoardId` focus in later steps.
- From `host_bootstrap.py` to `stage0_check.py`
  Carry forward any unresolved warnings:
  - missing vendor helper CLI
  - missing target pack
  - no probes detected
  - no serial ports detected
- From `stage0_check.py` back to itself on rerun
  Carry forward the concrete override that solved the failure:
  - `--port BOARD_ID=PORT`
  - `--reference-firmware BOARD_ID=PATH`
  - `--expect BOARD_ID=TEXT`
  - `--baudrate BOARD_ID=BAUD`
  - `--recover-test BOARD_ID`
- From Stage 0 to `pyocd-debug-mcp`
  Carry forward the known-good board target, probe path, and any `.env`
  defaults such as `PYOCD_PROBE_UID` or `PYOCD_TARGET`.

## 6. Cross-Script Troubleshooting

- `setup_host` succeeds but `host_bootstrap.py` still fails
  Read [host_bootstrap.md](./host_bootstrap.md) and fix the exact blocker it
  reported. Do not keep rerunning setup blindly.
- `host_bootstrap.py` passes enough to continue, but `stage0_check.py` fails on
  connection or identity
  Read [stage0_check.md](./stage0_check.md). This usually means target-specific
  Stage 0 state rather than raw host bootstrap state.
- `stage0_check.py` fails only on flash, UART, or recover
  Stay in Stage 0. Do not start the MCP server yet.
- `stage0_check.py` passes automated checks but leaves manual items
  Treat the remaining manual list as an operator checklist. The board is not
  fully Stage 0 complete until those items are resolved.

## 7. Board Config Expectations

Use a tracked board config from `boards/`, or pass extra board files with
`--board-config`.

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

If two nearby MCUs can both answer a generic debug read through the same probe
family, add silicon-identity metadata to the board YAML. Stage 0 will then read
that register and reject the wrong attached device even if the probe and target
family are otherwise compatible.

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
- confirm UART output is the intended reference behavior if you do not provide
  `--expect`
- confirm destructive recover behavior is acceptable before using
  `--recover-test`

Current `recover_mode` values:

- `nrf_pyocd_unlock`
- `manual_only`

## 9. Common Workflow Failures

- `pyOCD not found` or `pyserial not found`
  Fix the repo environment with `uv sync`, then rerun `host_bootstrap.py` or
  `stage0_check.py`.
- missing target pack
  Rerun with pack installation enabled.
- wrong nearby board attached
  Add or fix the board config's silicon-identity fields.
- probe not found
  Go back to `setup_host` or `host_bootstrap.py`; do not guess inside Stage 0.
- COM port ambiguous
  Respond to the interactive prompt or rerun with `--port BOARD_ID=...`.
- nRF board fails identity or connection after a power cycle with APPROTECT
  symptoms
  Rerun:

```powershell
uv run python stage0_check.py --board-id nrf52840dk --recover-test nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk
```

If this repeats every power cycle, the currently flashed firmware is likely
re-locking the chip.

## 10. Linked Script Docs

- Host setup automation: [setup_host.md](./setup_host.md)
- Host readiness checks: [host_bootstrap.md](./host_bootstrap.md)
- Board-level Stage 0 validation: [stage0_check.md](./stage0_check.md)
- MCP server runtime: [pyocd_debug_mcp.md](./pyocd_debug_mcp.md)

## Verification Status

Verified:

- this operator guide's sequence, branch points, and handoffs match the current
  `setup_host`, `host_bootstrap.py`, and `stage0_check.py` roles
- this flow matches the current `stage0_check.py` CLI shape and shared board
  loader behavior
- The `nrf52833dk` flash, UART, and recover path is bench-verified on this Mac
  host when a reference artifact is supplied

Pending verification:

- The unattended Windows bootstrap path still needs a real Windows bench run
- The `nucleo_l476rg` Stage 0 path and its reference baseline remain later
  bench work
