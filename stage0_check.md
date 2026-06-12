# Stage 0 Check

This is the script doc for `stage0_check.py`.

## 1. Purpose And When To Run Vs. When Not To Run

`stage0_check.py` is the board-level Stage 0 validation script. It proves the
host can see the probe, target, and UART path for the selected boards, and it
can optionally flash a reference image, read UART output, and run a destructive
recover validation for supported recover modes.

Run it when:

- `host_bootstrap.py` has already been run for the same machine and board set
- you want a real board-level readiness check rather than only host readiness
- you want to validate exact board identity, COM selection, optional flash, or
  optional UART behavior

Do not run it when:

- the machine is still a raw host; run `setup_host.ps1` or `setup_host.sh`
- host readiness is still unknown; run `host_bootstrap.py` first
- you need the cross-script workflow; read [stage0_setup.md](./stage0_setup.md)
- you need the product server rather than Stage 0 validation; run
  `uv run pyocd-debug-mcp` only after Stage 0 is acceptable

Conflicting states:

- another tool owning the debug probe can make probe or connection checks fail
- another tool owning the serial port can make UART checks fail
- `--recover-test` is destructive and may unlock or mass-erase the target

## 2. Exact Behavior

In order, the script:

1. loads repo-local `.env` if present
2. loads tracked board configs from `boards/` plus any extra board config files
3. filters boards by `--board-id` if requested
4. checks whether `pyocd` is installed and exits early if it is not
5. checks whether `pyserial` is installed
6. enumerates probes and assigns one per board using board metadata and fallback
   matching
7. checks whether each board's pyOCD target is available and optionally
   installs missing packs
8. enumerates serial ports and resolves one per board in this order:
   - explicit `--port` override
   - vendor-assisted lookup when available
   - generic matching
   - interactive prompt if still ambiguous and the terminal is interactive
9. runs a smoke-test memory read per board
10. runs an exact silicon-identity read when the board config defines that data
11. optionally flashes the supplied reference firmware path
12. optionally reads UART output after flashing
13. optionally runs a destructive recover validation via the board's
    `recover_mode`
14. prints a summary and any still-manual validation items

Side effects:

- `--install-packs` changes the local pyOCD pack state
- `--reference-firmware` flashes the target
- `--recover-test` may unlock or mass-erase the target

## 3. Inputs

### CLI Flags

- `--board-config-dir PATH`
  Default: repo `boards/`
  Meaning: board-config directory to load by default
- `--board-config PATH`
  Repeatable extra board-config file
  Meaning: adds custom board definitions outside the tracked directory
- `--board-id ID`
  Repeatable board selector
  Default: all non-example tracked board configs plus any extra configs
- `--install-packs`
  Switch
  Meaning: auto-install missing pyOCD target packs during this run
- `--port BOARD_ID=PORT`
  Repeatable
  Meaning: authoritative manual serial-port override for the named board
- `--reference-firmware BOARD_ID=PATH`
  Repeatable
  Meaning: reference firmware artifact to flash for the named board
- `--expect BOARD_ID=TEXT`
  Repeatable
  Meaning: expected UART substring for the named board
- `--baudrate BOARD_ID=BAUD`
  Repeatable
  Meaning: override UART baudrate for the named board
- `--recover-test BOARD_ID`
  Repeatable
  Meaning: opt into destructive recover validation for the named board
- `--serial-read-seconds FLOAT`
  Default: `3.0`
  Meaning: how long to listen for UART output after opening the port

### Board-Config-Driven Inputs

The board YAML controls:

- `board_id`
- `display_name`
- `mcu_family`
- `probe_family`
- `pyocd_target`
- `pack_name`
- `probe_type`
- `probe_hint_terms`
- `serial_hint_terms`
- `test_read_address`
- `serial_baudrate`
- `uart_note`
- `requires_recover_validation`
- `recover_mode`
- `reference_uart_patterns`
- silicon-identity fields

Current `recover_mode` values:

- `nrf_pyocd_unlock`
- `manual_only`

If `recover_mode` is absent:

- boards without recover validation keep `None`
- Nordic-family boards that require recover validation default to
  `nrf_pyocd_unlock`
- other families that require recover validation default to `manual_only`

### Examples

```bash
uv run python stage0_check.py
uv run python stage0_check.py --board-id nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk --install-packs
uv run python stage0_check.py --board-id nrf52840dk --port nrf52840dk=PORT_NAME
uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=path/to/firmware.elf --expect nrf52840dk="boot ok"
uv run python stage0_check.py --board-id nrf52840dk --recover-test nrf52840dk
```

## 4. Outputs And Logs

### Section Headers

The script may print these top-level sections:

- `pyOCD installation`
- `pyserial installation`
- `Connected probes`
- `CMSIS-Pack / target availability`
- `Virtual COM / serial ports`
- `Connection test - <board>`
- `Silicon identity - <board>`
- `Reference firmware flash - <board>`
- `UART output check - <board>`
- `Recover / unlock validation - <board>`
- `Summary`
- `Manual validation still required`

### Status Meanings

- `[PASS]`
  That automated check succeeded
- `[FAIL]`
  That automated check failed or was skipped because a required dependency for
  that automated check was missing
- `[WARN]`
  The step is opt-in, degraded, manual, or still needs a human decision
- `[INFO]`
  Explanatory text or attempted commands

### Important Observable Lines

- `[PASS] pyOCD found: <version>`
  `pyocd` is installed and runnable
- `[FAIL] pyOCD not found - run: uv sync`
  the script exits `1` immediately after the installation checks
- `[PASS] pyserial found: <version>`
  serial enumeration can proceed
- `[FAIL] pyserial not found - run: uv sync`
  serial checks will fail later in the run
- `Raw output:`
  a verbatim dump of fallback `pyocd list` output before board-level probe
  matching results
- `[PASS] <board> (<probe family>) - detected`
  a probe match was found for that board
- `[FAIL] <board> (<probe family>) - no probes detected`
  no probe was detected at all
- `[FAIL] <board> (<probe family>) - probes detected, but none matched this board`
  probes exist, but the script could not defensibly map one to this board
- `[PASS] <board>: target '<target>' available`
  the pyOCD target exists already
- `[FAIL] <board>: target '<target>' not found`
  the target is missing and no auto-install path succeeded in this run
- `Fix: uv run pyocd pack install <pack>`
  manual rerun guidance for a missing target pack
- `Attempting: pyocd pack install <pack>`
  auto-install is in progress because `--install-packs` was set
- `[PASS] <board> virtual COM port visible on <port> - <note>`
  COM resolution succeeded and the note explains which resolver path won
- `[FAIL] <board> COM port not uniquely identifiable: <note>`
  no safe port selection was made
- `Found <n> serial port(s):`
  pyserial enumeration succeeded and candidate ports are listed below it
- `[FAIL] No serial ports detected`
  no serial endpoints were visible at all
- `[PASS] Connected and read <address>: <value>`
  SWD smoke-test memory read worked
- `[WARN] <board> appears access-protected.`
  pyOCD could see the probe but the target likely needs recovery or unlock
- `[FAIL] pyOCD found the probe but could not connect to the target MCU`
  probe enumeration succeeded but target-level access failed
- `[FAIL] Unable to read <silicon label>`
  silicon-identity read failed
- `[PASS] <silicon label> matched (actual=..., expected=..., mask=...)`
  exact board identity check succeeded
- `[FAIL] <silicon label> did not match (actual=..., expected=..., mask=...)`
  the attached board does not match this config or the config is wrong
- `[WARN] No reference firmware path supplied - leaving flash validation as a manual step`
  flash and UART checks remain partial unless rerun with `--reference-firmware`
- `[PASS] Flashed reference firmware: <path>`
  flash completed successfully
- `[FAIL] Flash failed for <path>`
  flash was attempted and failed
- `[PASS] UART output matched expected text on <port>`
  deterministic UART expectation succeeded
- `[FAIL] UART output did not match expected text on <port>`
  UART produced output, but the expected substring was absent
- `[PASS] UART produced some output on <port>`
  no explicit expectation was provided, but bytes were observed
- `[FAIL] UART produced no output on <port>`
  no bytes were observed during the configured read window
- `[WARN] Recover test not run - this remains a required manual Stage 0 validation`
  recover validation is still outstanding because the run did not opt into it
- `[FAIL] Skipped - this board's recover_mode is manual_only`
  the board requires recover validation, but Stage 0 has no automation for that
  family yet
- `[PASS] Recover completed via <label>`
  destructive recover succeeded
- `[FAIL] Recover flow failed`
  every attempted recover backend failed
- `Automated Stage 0 checks failed. Fix the items above and re-run.`
  exit code `1`
- `Automated checks passed, but full Stage 0 is not complete until the manual items are validated.`
  exit code `0`, but manual validation remains
- `Automated checks passed and this run covered the requested Stage 0 validations.`
  exit code `0` and no manual items remain for the requested checks

### Exit Codes

- `0`
  no automated failures remained, even if manual validation is still pending
- `1`
  one or more automated checks failed
- `2`
  `argparse` usage or CLI error

## 5. Failure Modes

- Symptom: `[FAIL] pyOCD not found - run: uv sync`
  Cause: repo environment is incomplete
  Fix: run `uv sync`
  Rerun: `uv run python stage0_check.py ...`

- Symptom: `[FAIL] pyserial not found - run: uv sync`
  Cause: repo environment is incomplete
  Fix: run `uv sync`
  Rerun: `uv run python stage0_check.py ...`

- Symptom: `<board>: target '<target>' not found`
  Cause: required pyOCD target pack is missing
  Fix: rerun with `--install-packs` or install the pack manually
  Rerun: `uv run python stage0_check.py --board-id <board> --install-packs`

- Symptom: `<board> ... no probes detected`
  Cause: board absent, USB issue, driver/tooling issue, or another process owns
  the probe
  Fix: repair host visibility first
  Rerun: `uv run python host_bootstrap.py --board-id <board>`

- Symptom: `<board> ... probes detected, but none matched this board`
  Cause: the probe exists, but matching by hints or family was inconclusive
  Fix: narrow the run to the correct board, fix the board config, or disconnect
  unrelated hardware
  Rerun: `uv run python stage0_check.py --board-id <board>`

- Symptom: `COM port not uniquely identifiable: ...`
  Cause: auto-detect remained ambiguous
  Fix: choose a port in the prompt or rerun with `--port`
  Rerun: `uv run python stage0_check.py --board-id <board> --port <board>=<port>`

- Symptom: `No serial ports detected`
  Cause: UART interface is not visible to the OS at all
  Fix: repair host USB, vendor tooling, or board connection
  Rerun: `uv run python host_bootstrap.py --board-id <board>`

- Symptom: `<board> appears access-protected.`
  Cause: locked target, especially Nordic APPROTECT
  Fix: rerun with `--recover-test` if the board's recover mode supports it
  Rerun: `uv run python stage0_check.py --board-id <board> --recover-test <board>`

- Symptom: `Skipped - this board's recover_mode is manual_only`
  Cause: the board requires recover validation, but Stage 0 has no automated
  recover implementation for that family yet
  Fix: perform the recover proof manually and record it outside the script
  Rerun: rerun the normal board check after manual recovery if needed

- Symptom: `<silicon label> did not match (actual=..., expected=..., mask=...)`
  Cause: wrong board is attached, or the board config's silicon identity is wrong
  Fix: attach the correct board or fix the YAML
  Rerun: `uv run python stage0_check.py --board-id <board>`

- Symptom: `Reference firmware file does not exist: ...`
  Cause: bad runtime path
  Fix: correct the artifact path
  Rerun: `uv run python stage0_check.py --board-id <board> --reference-firmware <board>=<path>`

- Symptom: `Unable to read <port> at <baud> baud: ...`
  Cause: wrong port, wrong baudrate, busy port, or no UART output
  Fix: fix the port or baudrate, close the competing serial user, or reflash a
  known-good image
  Rerun: `uv run python stage0_check.py --board-id <board> --port ... --baudrate ...`

- Symptom: `UART output did not match expected text`
  Cause: wrong firmware, wrong expectation string, or incomplete boot output
  Fix: flash the intended reference firmware, extend the UART read time if
  appropriate, or correct `--expect`
  Rerun: `uv run python stage0_check.py --board-id <board> --reference-firmware ... --expect ...`

- Symptom: nRF silicon identity fails again after a power cycle
  Cause: firmware is likely re-enabling APPROTECT on boot
  Fix: rerun recover, then rerun the normal check
  Rerun:
  `uv run python stage0_check.py --board-id nrf52840dk --recover-test nrf52840dk`
  then
  `uv run python stage0_check.py --board-id nrf52840dk`

## 6. Rerun Guidance

- If only packs are missing, rerun with `--install-packs`.
- If only serial selection is ambiguous, rerun with `--port`.
- If flash remained manual, rerun with `--reference-firmware`.
- If UART should be deterministic, rerun with `--expect`.
- If baudrate is wrong, rerun with `--baudrate`.
- If a Nordic board is locked, rerun with `--recover-test`.
- If the script ends with only manual items, use the summary output as the
  remaining Stage 0 checklist and do not treat the run as full bring-up.

## 7. Prerequisite Sequence

Run these in order:

1. on a fresh machine, run `setup_host.ps1` or `setup_host.sh`
2. run `uv run python host_bootstrap.py [--board-id <board>]`
3. run `uv run python stage0_check.py [--board-id <board>]`
4. rerun with `--install-packs`, `--port`, `--reference-firmware`, `--expect`,
   `--baudrate`, or `--recover-test` only as needed
5. after Stage 0 is acceptable, run `uv run pyocd-debug-mcp`

Preconditions this script assumes:

- the repo environment is installed
- the board is physically attached
- the host can at least attempt probe enumeration

Auto-handled by earlier scripts:

- environment installation and vendor-tool repair by `setup_host`
- host readiness triage by `host_bootstrap.py`

Agent-must-run explicitly:

- choose `--board-id` for single-bench bring-up
- provide `--reference-firmware`, `--expect`, and `--baudrate` when those
  checks should be automated deterministically
- explicitly opt into `--recover-test` for destructive validation

## 8. Verification Status

Verified:

- non-hardware verification: this doc matches the current `stage0_check.py`
  CLI shape and the main section headers it emits
- non-hardware verification: serial-resolver tests and board-config tests pass

Pending verification:

- flash, UART, and recover behavior on all supported board families
- bench confirmation of every `recover_mode` branch beyond the currently tested
  Nordic path
