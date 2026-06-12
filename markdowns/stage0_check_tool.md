# stage0_check.py — MCP Tool Reference

> **Purpose.** This document describes `stage0_check.py` as an MCP-callable tool: what it does,
> how to invoke it, what every output section means, and how an agent should interpret results
> and act on failures. Written for a future agent that will call this tool and must reason about
> its output without human guidance.

---

## What the tool does

`stage0_check.py` runs the automated subset of Stage 0 board validation. It confirms that a
board's debug probe is visible, its CMSIS-Pack target is installed, SWD can connect and read
memory, the silicon identity matches the board config, and the virtual COM port is present. It
optionally flashes reference firmware, reads UART output, and runs a destructive recover/unlock
cycle.

It is **data-driven**: board facts come entirely from `boards/<board>.yaml`. No board-specific
logic lives in the script itself. Adding a new board means adding a new YAML file.

It is **safe to run at any time** — it reads memory but does not write to it unless
`--reference-firmware` or `--recover-test` are passed. Without those flags it is non-destructive.

---

## Invocation

```
uv run python stage0_check.py [options]
```

**Key options:**

| Option | Description |
|---|---|
| `--board-id <id>` | Run only the named board (repeat for multiple). Default: all non-example boards in `boards/`. |
| `--board-config <path>` | Load an additional board config file outside `boards/`. |
| `--install-packs` | Automatically install missing CMSIS-Packs via `pyocd pack install`. |
| `--port <BOARD_ID=PORT>` | Override the auto-detected virtual COM port for a board. |
| `--reference-firmware <BOARD_ID=PATH>` | Flash this `.hex`/`.elf`/`.bin` file and then check UART. |
| `--expect <BOARD_ID=TEXT>` | Substring that must appear in UART output for the test to pass. |
| `--baudrate <BOARD_ID=BAUD>` | Override the UART baud rate for a board. |
| `--recover-test <BOARD_ID>` | Run the destructive recover/unlock cycle for this board. Erases flash. |
| `--serial-read-seconds <N>` | How long to listen for UART output (default: 3.0 seconds). |

**Minimal invocation (all defaults):**
```
uv run python stage0_check.py
```

**Single board, with firmware flash and UART check:**
```
uv run python stage0_check.py --board-id nrf52840dk \
  --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.hex \
  --expect nrf52840dk="Hello"
```

---

## Output structure

The script prints a sequence of named sections, each introduced by a `===` header line. Within
each section, every result line is tagged with a status token in brackets.

**Status tokens:**

| Token | Meaning |
|---|---|
| `[PASS]` | Check succeeded. No action needed. |
| `[FAIL]` | Check failed. Something must be fixed before Stage 0 is complete. |
| `[WARN]` | Non-fatal issue or skipped step. May require action depending on context. |
| `[INFO]` | Informational message. Not a result. |

The final **Summary** section consolidates all results and determines the exit code.

**Exit codes:**
- `0` — All automated checks passed (manual items may still be pending).
- `1` — One or more automated checks failed, OR pyOCD is not installed.

---

## Sections and how to interpret them

### pyOCD installation

Checks that `pyocd` is on the PATH and returns a version. If this fails, nothing else runs.

**`[FAIL] pyOCD not found`** — Run `uv sync` from the repo root to install dependencies.

---

### pyserial installation

Checks that `pyserial` is importable. If missing, the virtual COM port section is skipped but
SWD checks still run.

**`[FAIL] pyserial not found`** — Run `uv sync`.

---

### Connected probes

Lists all probes detected by `pyocd list` and attempts to match each to a board config using
`probe_hint_terms` from the board YAML.

**`[PASS] <board> probe visible`** — The probe was uniquely matched to this board.

**`[FAIL] probe not uniquely identifiable: no matching probe found`** — No connected probe matched
the board's hint terms. Check USB connection, cable (must be data, not charge-only), and J-Link
or ST-Link driver installation.

**`[FAIL] multiple matching probes found`** — More than one probe scored equally. Disconnect
extras or refine `probe_hint_terms` in the board YAML.

If no probes are detected at all, the raw output of `pyocd list` is printed to help diagnose
driver issues.

---

### CMSIS-Pack / target availability

Checks that the board's `pyocd_target` is in the list of installed targets.

**`[PASS]`** — Target pack is present.

**`[FAIL] target not found`** — The CMSIS-Pack for this target is not installed. Fix:
```
uv run pyocd pack find <pack_name>
uv run pyocd pack install <pack_name>
```
Or re-run with `--install-packs` to do this automatically.

---

### Connection test

Attempts to read a known-safe memory address (e.g. FICR base at `0x10000000` for nRF, flash base
for STM32) via SWD to confirm the probe can talk to the MCU.

**`[PASS]`** — Connected and read successfully. SWD is working.

**`[WARN] appears access-protected`** — The chip has APPROTECT or equivalent memory protection
enabled. SWD read is blocked. The recover command is printed. For nRF52840:
```
nrfjprog --recover
```
This performs a mass erase and clears APPROTECT. **All flash contents will be lost.**

**`[FAIL] pyOCD found the probe but could not connect to the target MCU`** — Probe is visible but
the chip is unresponsive. Check power, cable quality, and (for J-Link boards) J-Link firmware
and driver versions.

**`[FAIL] Unexpected error`** — stdout and stderr from pyOCD are printed below the result. Use
these to diagnose.

---

### Silicon identity

Only runs if `silicon_id_address` and `silicon_id_expected` are set in the board YAML. Reads a
hardware register (e.g. `FICR.INFO.PART` on nRF52840 at `0x10000100`) and compares it to the
expected value, optionally masked.

This check exists to confirm the physically connected chip matches the board config before any
destructive operation (flash, recover) is allowed.

**`[PASS]`** — The masked register value matches `silicon_id_expected`.

**`[FAIL] Unable to read <label>`** — The read returned no value. Most commonly caused by
APPROTECT (recover the board first). The raw stdout/stderr from pyOCD is printed.

**`[FAIL] did not match`** — The register value does not match the expected value. The actual,
expected, and mask values are printed. This means either the wrong board config is selected, or
the physically connected chip is not the expected silicon.

The actual and expected values are printed in hex: `actual=0xXXXX, expected=0xXXXX, mask=0xXXXX`.

---

### Virtual COM / serial ports

Lists all serial ports detected by pyserial and attempts to match each to a board config using
`serial_hint_terms` from the board YAML.

**`[PASS]`** — A virtual COM port was uniquely matched to this board.

**`[FAIL] COM port not uniquely identifiable`** — No port matched, or multiple tied. If the board
has a `uart_note` field, it is printed as a hint. Use `--port BOARD_ID=/dev/tty.usbmodem...` to
override discovery.

**`[FAIL] No serial ports detected`** — No ports at all. Check USB connection and VCP driver
installation.

---

### Reference firmware flash

Only runs if `--reference-firmware BOARD_ID=PATH` is passed. Flashes the given binary using
`pyocd load`. Skipped (with WARN) if no path is supplied — this step is then marked manual in
the summary.

If `silicon_id_expected` is set and the silicon identity check failed, this step is skipped to
avoid flashing the wrong board.

**`[PASS]`** — Firmware flashed successfully.

**`[FAIL]`** — Flash failed. The stderr from pyOCD is printed. Common causes: probe not
connected, target pack missing, chip access-protected.

---

### UART output check

Only runs if reference firmware was successfully flashed. Opens the virtual COM port, reads for
`--serial-read-seconds` seconds (default 3), and checks the output.

If `--expect BOARD_ID=TEXT` is passed, the captured text must contain that substring.
If no `--expect` is given, any non-empty output counts as a pass (but the summary flags this as
requiring manual confirmation).

**`[PASS]`** — Output matched (or any output was received if no expected text was given).

**`[FAIL] did not match expected text`** — Output was received but the expected substring was not
present. The captured text is printed.

**`[FAIL] no output`** — Nothing was received within the timeout. The reference firmware may not
be running, or the wrong baud rate is configured.

**`[FAIL] Unable to read <port>`** — Serial port could not be opened. The exception is printed.

---

### Recover / unlock validation

Only runs for boards where `requires_recover_validation: true` in the board YAML, AND only when
`--recover-test <BOARD_ID>` is passed explicitly. Without the flag, this section prints a WARN
and marks the item manual in the summary.

**This is destructive — it erases flash.** It is opt-in precisely because it is irreversible.

Runs the board's `recover_command` (e.g. `nrf recover` for nRF52840) via `pyocd cmd`, then
re-runs the connection test to confirm the chip is accessible again.

**`[PASS]`** — Recover command ran and the chip reconnected successfully.

**`[FAIL]`** — Recover command failed or the chip did not reconnect after recovery.

---

### Summary

The final section lists every check with a consolidated status, followed by any items that remain
as required manual validations.

The last line of the summary is the overall verdict:
- `Automated Stage 0 checks failed.` — Exit code 1. Fix the FAILed items.
- `Automated checks passed, but full Stage 0 is not complete until the manual items are validated.` — Exit code 0. Manual steps still required.
- `Automated checks passed and this run covered the requested Stage 0 validations.` — Exit code 0. Full automated coverage for this run.

**Manual items** are checks the script cannot perform without additional inputs or explicit opt-in
(flash path not supplied, UART confirmation, recover cycle not yet run). These are not failures —
they are pending human or agent actions.

---

## Failure patterns and agent actions

| What you see | Most likely cause | Action |
|---|---|---|
| No probes detected | USB not connected, or driver missing | Check USB; install J-Link or ST-Link drivers |
| Probe visible but connection WARN: access-protected | APPROTECT enabled on nRF, or RDP on STM32 | Run `nrfjprog --recover` (nRF) or STM32 equivalent; re-run script |
| Silicon identity FAIL: unable to read | APPROTECT blocking FICR reads | Recover first, then re-run |
| Silicon identity FAIL: did not match | Wrong board config selected, or unexpected silicon | Verify `--board-id` matches the physical board |
| Target pack not found | CMSIS-Pack not installed | Run `uv run pyocd pack install <pack_name>` or use `--install-packs` |
| Flash FAIL | Chip locked, probe lost, wrong target | Check connection test first; all prior checks must pass before flash |
| UART no output | Wrong baud rate, firmware not running, wrong port | Try `--baudrate`, check COM port detection, reflash |
| Recover test FAIL | pyOCD version or driver issue | Try `nrfjprog --recover` directly; check J-Link driver version |

---

## Board config fields that affect this tool

All board facts are read from `boards/<board>.yaml`. The fields this tool reads:

| Field | Effect |
|---|---|
| `board_id` | Used to match `--board-id` and key all per-board results |
| `display_name` | Human-facing label in output |
| `pyocd_target` | Target passed to every `pyocd` command |
| `pack_name` | Token used for `pyocd pack install` |
| `probe_family` / `probe_hint_terms` | Controls probe matching |
| `serial_hint_terms` | Controls virtual COM port matching |
| `test_read_address` | Address read during connection test |
| `silicon_id_address` / `silicon_id_expected` / `silicon_id_mask` | Silicon identity check; omit all to skip the check |
| `silicon_id_width_bits` | Register width for silicon read (8/16/32, default 32) |
| `silicon_id_label` | Human-facing label for the identity check |
| `serial_baudrate` | Default baud rate for UART check |
| `requires_recover_validation` | Whether recover/unlock is a required Stage 0 step |
| `recover_command` | pyOCD commander command string for unlock (e.g. `nrf recover`) |
| `expected_uart_substring` | Default expected UART text (overridden by `--expect`) |

---

## Verified / Pending verification

**Verified** (by reading the current `stage0_check.py` source):
- All CLI flags and their behavior
- All output section names, status tokens, and exit codes
- Silicon identity logic (mask, width, label)
- APPROTECT detection strings (`approtect`, `access port`, `locked`) in connection test
- Recovery skipping flash/recover when silicon identity fails
- Summary status mapping (`SUMMARY_PASS` → `[PASS]`, `SUMMARY_FAIL` → `[FAIL]`, `SUMMARY_MANUAL` → `[WARN]`)

**Pending hardware verification:**
- Exact pyOCD output strings that trigger APPROTECT detection (verified against source code string
  matching, not against live hardware output)
- UART output behavior and timing on real boards
- Recover cycle behavior on nRF52840-DK and Nucleo-L476RG under real conditions
