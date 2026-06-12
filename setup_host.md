# Setup Host

This is the script doc for `setup_host.ps1` and `setup_host.sh`.

## 1. Purpose & when to run vs. when NOT to run

These scripts automate first-run host bootstrap on a fresh machine. They install
or repair the canonical repo environment and board-family-specific host tooling,
then run `host_bootstrap.py --install-packs` unless explicitly told not to.

Run them when:

- the machine is fresh or untrusted
- `uv`, Python, Homebrew, or vendor helper CLIs may be missing
- you want the repo to self-heal into a Stage 0-ready state

Do not run them when:

- you only need a readiness check and host tooling is already in place; run
  `host_bootstrap.py`
- you need board-level validation; run `stage0_check.py` after setup and host
  bootstrap
- you need the MCP server itself; run `uv run pyocd-debug-mcp` after setup and
  Stage 0 are complete
- you are on the wrong OS for the selected script

Conflicting states:

- avoid running setup while another process is actively using the same probe or
  while you are intentionally preserving a partially configured vendor install

## 2. Exact behavior

Shared behavior:

1. Discover selected boards from the tracked board-config directory plus any
   extra board config files.
2. Filter boards by board id if requested.
3. Determine which vendor families are required by the selected boards.
4. Repair the canonical repo environment.
5. Repair or install vendor helper tooling where automation exists.
6. Run `uv run python host_bootstrap.py --install-packs` unless skipped.

Windows PowerShell (`setup_host.ps1`) additionally:

- installs Python 3.12 via `winget` if no `py` or `python` launcher exists
- installs `uv` with `pip` if needed
- adds Python scripts and vendor-tool directories to the current and user `PATH`
- installs SEGGER J-Link with `winget` when needed
- downloads and runs the Nordic nRF Command Line Tools installer when needed
- attempts PATH repair for an existing STM32CubeProgrammer install
- prints `[FAIL]` and exits `1` on script-level failure

macOS shell (`setup_host.sh`) additionally:

- ensures Homebrew exists
- installs `uv` with Homebrew if needed
- installs `libusb`
- installs Nordic tools with Homebrew cask if needed
- attempts PATH repair for an existing STM32CubeProgrammer install

Side effects:

- may install system software
- may modify user PATH on Windows
- may download vendor installers
- may run `uv sync --locked`
- may install pyOCD target packs through `host_bootstrap.py`

## 3. Inputs

PowerShell inputs (`setup_host.ps1`):

- `-BoardConfigDir PATH`
  Default: repo `boards`
- `-BoardConfig PATH`
  Repeatable
- `-BoardId ID`
  Repeatable
- `-SkipUvSync`
  Skip `uv sync --locked`
- `-SkipHostBootstrap`
  Skip `host_bootstrap.py`
- `-DryRun`
  Print intended actions without executing them

macOS shell inputs (`setup_host.sh`):

- `--board-config-dir PATH`
  Default: repo `boards`
- `--board-config PATH`
  Repeatable
- `--board-id ID`
  Repeatable
- `--skip-uv-sync`
  Skip `uv sync --locked`
- `--skip-host-bootstrap`
  Skip `host_bootstrap.py`
- `--dry-run`
  Print intended actions without executing them
- `-h` / `--help`
  Print usage and exit `0`

Examples:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52840dk
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nucleo_l476rg -SkipHostBootstrap
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -DryRun -BoardId nrf52840dk
```

```bash
bash ./setup_host.sh --board-id nrf52840dk
bash ./setup_host.sh --board-id nucleo_l476rg --skip-host-bootstrap
bash ./setup_host.sh --dry-run --board-id nrf52840dk
```

## 4. Outputs & logs

Common section headers:

- `Windows host setup` / `macOS host setup`
- `Python` (Windows only)
- `Homebrew` (macOS only)
- `uv`
- `Repo environment`
- `SEGGER J-Link` / `Nordic nRF Command Line Tools` / `Nordic tools`
- `STM32CubeProgrammer`
- `Host bootstrap`
- `Done`
- `Failed` (Windows only explicit failure section)

Status meanings:

- `[PASS]`
  This step succeeded or was already satisfied
- `[WARN]`
  The script found a gap it could not fully automate
- `[INFO]`
  The script is describing a selected board or dry-run action
- `[FAIL]`
  The script is aborting or the attempted action failed

Important observable lines:

- `DRY RUN: ...`
  The script would have performed that action, but did not change the machine
- `Selected boards: ...`
  Confirms which board families drive the setup choices
- `uv installed ...`, `nrfjprog installed`, `STM32_Programmer_CLI found after PATH repair`
  Tooling was repaired or installed
- `host_bootstrap.py reported that setup is still incomplete.`
  The automation ran but the machine still is not Stage 0-ready
- `Windows host setup script completed.` / `macOS host setup script completed.`
  The script reached its success path

Exit codes:

- `setup_host.ps1`
  - `0` success
  - `1` script-level failure
- `setup_host.sh`
  - `0` success or `--help`
  - `1` runtime failure or unsupported OS
  - `2` invalid CLI option

## 5. Failure modes

- Symptom: `setup_host.ps1 currently supports Windows host automation only.`
  or `setup_host.sh currently supports macOS only.`
  Cause: wrong script for the current OS
  Fix: run the OS-matching setup script
  Rerun: the other setup script

- Symptom: `No board configs were selected.`
  Cause: no tracked board configs matched the requested selection
  Fix: correct `--board-id` / `-BoardId` or board-config paths
  Rerun: same setup script with corrected board selection

- Symptom: `winget is required ... but was not found.`
  Cause: Windows unattended install path is unavailable
  Fix: install Python or vendor tools manually, then rerun
  Rerun: `powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 ...`

- Symptom: `Python install completed but no python launcher was found on PATH.`
  Cause: install succeeded but PATH did not update as expected
  Fix: reopen the shell or repair Python manually
  Rerun: the PowerShell setup script

- Symptom: `uv install completed but uv was not found on PATH.`
  Cause: install succeeded but PATH is still stale
  Fix: reopen the shell or repair PATH manually
  Rerun: the matching setup script

- Symptom: `nRF Command Line Tools install completed but nrfjprog was not found.`
  Cause: Nordic install failed or PATH repair failed
  Fix: inspect the vendor install and rerun
  Rerun: the matching setup script for the same board family

- Symptom: `[WARN] STM32_Programmer_CLI not found ...`
  Cause: ST tool is missing and the script does not have a verified unattended
  ST installer flow
  Fix: install STM32CubeProgrammer manually, then rerun
  Rerun: the matching setup script or `host_bootstrap.py`

- Symptom: `host_bootstrap.py reported that setup is still incomplete.`
  Cause: the environment was repaired, but probe/serial/pack readiness still
  failed
  Fix: inspect `host_bootstrap.py` output, repair the specific blocker, rerun
  Rerun: `uv run python host_bootstrap.py ...` or the setup script again

## 6. Rerun guidance

- If setup completes successfully, run `stage0_check.py` next.
- If you used `SkipHostBootstrap` / `--skip-host-bootstrap`, run
  `uv run python host_bootstrap.py` manually after setup finishes.
- If you used `SkipUvSync` / `--skip-uv-sync`, run `uv sync --locked` before
  expecting repo scripts to work.
- If only ST tooling is missing, install STM32CubeProgrammer manually and rerun
  the setup script or `host_bootstrap.py`.
- If `host_bootstrap.py` still fails after setup, switch to that script's doc
  and resolve the surfaced blocker rather than rerunning setup blindly.

## 7. Prerequisite sequence

Ordered sequence:

1. Clone or open the repo
2. Choose the matching setup script for the current OS
3. Run:
   - Windows:
     `powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId <board>`
   - macOS:
     `bash ./setup_host.sh --board-id <board>`
4. If setup succeeds, run `uv run python stage0_check.py --board-id <board>`
5. After Stage 0 is acceptable, run `uv run pyocd-debug-mcp`

Auto-handled by these setup scripts:

- Python / `uv` install on Windows
- Homebrew / `uv` / `libusb` setup on macOS
- Nordic tool installation where scripted
- PATH repair for known vendor install locations
- `host_bootstrap.py --install-packs` unless explicitly skipped

Agent-must-run explicitly:

- choose the board selection
- rerun after manual STM32CubeProgrammer install if needed
- move on to `stage0_check.py` and later scripts

## 8. Verification status

Verified:

- non-hardware verification: this doc matches the current setup-script flags
  and control flow
- non-hardware verification: `setup_host.ps1` now emits `[FAIL]` and exits `1`
  on script-level failure

Pending verification:

- full unattended Windows install path on a truly fresh host
- full unattended macOS path on a truly fresh host
- all vendor-tool repair branches on supported board families
