# Host Bootstrap

This is the script doc for `host_bootstrap.py`.

## 1. Purpose & when to run vs. when NOT to run

`host_bootstrap.py` is the host-level readiness check that should run before
`stage0_check.py`. It checks whether the machine can run the canonical Python
environment, enumerate probes and serial ports, load board configs, and see the
pyOCD targets required by the selected boards.

Run it when:

- the repo environment was just bootstrapped
- a new board is being brought up on a machine
- probe, serial, or pack visibility is uncertain
- you want a non-destructive readiness check before Stage 0 validation

Do not run it when:

- you need host setup automation on a raw machine; run `setup_host.ps1` or
  `setup_host.sh` first
- you need board-level flashing, UART validation, or recover behavior; run
  `stage0_check.py` after this script passes
- you need the product server itself; run `uv run pyocd-debug-mcp` after host
  bootstrap and Stage 0 are in a known-good state

Conflicting states:

- this script is safe to rerun, but results can be misleading if another tool
  currently owns the debug probe or serial port

## 2. Exact behavior

In order, the script:

1. Loads repo-local `.env` if present.
2. Checks Python dependency availability for `pyocd`, `pyserial`, `pyyaml`,
   and `python-dotenv`.
3. Optionally runs `uv sync --locked` if `--install-missing` is set and the
   canonical repo environment is incomplete.
4. Checks `pyocd --version`.
5. Enumerates probes through `pyocd`.
6. Enumerates serial ports through `pyserial`.
7. Loads tracked board configs from `boards/` plus any extra `--board-config`
   files, then filters them by `--board-id` if requested.
8. Checks whether each selected board's `pyocd_target` is already available.
9. Optionally runs `pyocd pack install ...` for missing targets when
   `--install-packs` is set.
10. Emits vendor-tool readiness hints for Nordic J-Link and ST-LINK serial
    auto-detect helpers.
11. Prints a summary and exits `0` only if the canonical environment, board
    config loading, target-pack visibility, and attached hardware visibility are
    all ready for `stage0_check.py`.

Side effects:

- may run `uv sync --locked`
- may run `pyocd pack install ...`
- does not flash, mass-erase, unlock, or open a long-lived debug session

## 3. Inputs

CLI flags:

- `--board-config-dir PATH`
  Default: repo `boards/`
  Meaning: directory of tracked board config files to inspect
- `--board-config PATH`
  Repeatable, optional
  Meaning: extra board config file outside the tracked directory
- `--board-id ID`
  Repeatable, optional
  Meaning: limit the check to selected board ids instead of all non-example
  tracked board configs plus extra configs
- `--install-missing`
  Optional switch
  Meaning: if required Python packages are missing, reconcile the repo env with
  `uv sync --locked`
- `--install-packs`
  Optional switch
  Meaning: install missing pyOCD target packs for the selected boards

Environment / config:

- `.env` is auto-loaded when present
- `PYOCD_*` variables may affect downstream `pyocd` CLI behavior because the
  script launches `pyocd` as subprocesses

Examples:

```bash
uv run python host_bootstrap.py
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python host_bootstrap.py --install-missing --install-packs
uv run python host_bootstrap.py --board-config path/to/my_board.yaml --board-id my_board
```

## 4. Outputs & logs

Meaningful section headers:

- `Python dependencies`
  Dependency availability and optional env reconciliation
- `pyOCD host visibility`
  `pyocd` CLI status plus probe enumeration
- `Serial ports`
  `pyserial` status plus serial-port enumeration
- `Board configs`
  Board-config loading and selection
- `Target packs`
  pyOCD target availability and optional pack installation
- `Serial auto-detect helpers`
  Vendor helper CLI visibility (`nrfjprog`, `STM32_Programmer_CLI`)
- `Summary`
  Final readiness decision

Status meanings:

- `[PASS]`
  This step is ready and does not block Stage 0
- `[WARN]`
  The step is incomplete or degraded but may still allow a partial workflow
- `[FAIL]`
  The step failed and blocks normal Stage 0 bring-up
- `[INFO]`
  Explanatory text, commands attempted, or summary context

Important observable lines:

- `Attempting: uv sync --locked`
  The script is reconciling the canonical repo environment
- `Attempting: pyocd pack install <pack>`
  The script is trying to install a missing target pack
- `Host prerequisites and board-target support are ready for stage0_check.py`
  The script will exit `0`
- `Host is not fully ready for stage0_check.py yet`
  The script will exit `1`
- `Canonical env and board-target support are present, but attached hardware is not fully visible yet`
  The script will exit `1`

Exit codes:

- `0`
  Host readiness is sufficient for `stage0_check.py`
- `1`
  One or more required checks failed
- `2`
  `argparse` usage / CLI error

## 5. Failure modes

- Symptom: `[FAIL] pyocd missing - cannot enumerate probes or targets`
  Cause: repo environment is not installed correctly
  Fix: run `uv sync` or rerun this script with `--install-missing`
  Rerun: `uv run python host_bootstrap.py --install-missing`

- Symptom: `[FAIL] pyserial missing - cannot enumerate serial ports`
  Cause: repo environment is incomplete
  Fix: run `uv sync` or rerun with `--install-missing`
  Rerun: `uv run python host_bootstrap.py --install-missing`

- Symptom: `[FAIL] <path> is missing required field ...`
  Cause: invalid board config
  Fix: correct the board file
  Rerun: `uv run python host_bootstrap.py ...`

- Symptom: `[WARN] No debug probes detected by pyOCD`
  Cause: no board attached, driver/tooling issue, USB issue, or another process
  owns the probe
  Fix: attach the board, close conflicting probe users, or repair host tooling
  Rerun: `uv run python host_bootstrap.py --board-id <board>`

- Symptom: `[WARN] No serial ports detected`
  Cause: UART interface is not visible to the OS yet
  Fix: repair USB / driver / vendor-tooling setup and reconnect the board
  Rerun: `uv run python host_bootstrap.py --board-id <board>`

- Symptom: `[WARN] <board>: target '<target>' not found`
  Cause: required pack is missing
  Fix: rerun with `--install-packs` or install the pack manually
  Rerun: `uv run python host_bootstrap.py --board-id <board> --install-packs`

- Symptom: `[WARN] nrfjprog not found ...` or `[WARN] STM32_Programmer_CLI not found ...`
  Cause: vendor helper CLI is absent
  Fix: run `setup_host` or install the vendor tool manually
  Rerun: `powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId <board>`
  or `bash ./setup_host.sh --board-id <board>`

## 6. Rerun guidance

- If the script exits `0`, run `stage0_check.py` next.
- If only Python packages are missing, rerun with `--install-missing`.
- If only target packs are missing, rerun with `--install-packs`.
- If vendor serial helpers are missing for a fresh machine, rerun `setup_host`
  for the same board family.
- If probe/serial visibility is still missing after setup repair, stop and
  surface that the remaining blocker is host USB / driver / vendor-tooling
  state.

## 7. Prerequisite sequence

Ordered sequence:

1. On a raw machine, run `setup_host.ps1` or `setup_host.sh`
2. From the repo root, run:
   `uv run python host_bootstrap.py [--board-id <board>]`
3. If host bootstrap passes, run `stage0_check.py`
4. If Stage 0 passes enough for your workflow, start `uv run pyocd-debug-mcp`

Preconditions this script assumes:

- the repo exists locally
- `uv` can be installed or is already available
- supported board configs exist

Auto-handled by setup scripts:

- installing Python and `uv` on Windows
- installing `uv` and `libusb` on macOS
- repairing vendor-tool `PATH` entries

Agent-must-run explicitly:

- choose `--board-id` when only one physical bench board should be considered
- rerun with `--install-missing` or `--install-packs` when the first pass
  surfaces those gaps

## 8. Verification status

Verified:

- non-hardware verification: this doc matches the current `host_bootstrap.py`
  CLI shape and summary behavior

Pending verification:

- hardware-backed confirmation of probe enumeration, serial enumeration, and
  pack-install flows on supported Windows and macOS hosts
