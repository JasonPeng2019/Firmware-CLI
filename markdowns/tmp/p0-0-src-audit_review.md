# Review for p0-0-src-audit

Task: Independent structural audit of entire src tree after P0.0 fixes

## Verdict

CHANGES REQUESTED

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |

## Hardware hand-off status

## What's genuinely good
## Verdict

CLEAN

The intermediate review findings from the prior pass were all addressed in this
cycle. The final `src/` state is clean for the agent-verifiable surface that
was actually exercised here: strict non-hardware checks, live timeout handling,
raw-tool validation, mixed-board probe selection, and dual-board flash/UART
verification on the attached `nrf52840dk` and `nucleo_l476rg`.

## Findings

| Severity | Gate | File:line | Issue | Concrete fix |
|---|---|---|---|---|
| N/A | N/A | N/A | No open must-fix findings remain from this review pass. | Keep the new regression guards and dual-board hardware checks in the validation ladder. |

## Evidence Run

I reran the current strict checks from the repo root:

- `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default --command "uv run pytest tests/test_server_import.py tests/test_server_runtime_tools.py tests/test_probe_inventory.py tests/test_uart_capture.py -q"`
  - `uv run pytest -q` -> PASS (`209 passed`)
  - `uv run ruff check .` -> PASS
  - `uv run mypy src` -> PASS
  - targeted server/runtime tests -> PASS (`33 passed`)

Live repros on the attached boards:

- timeout recovery on `nrf52840dk`:
  - forced `client.call_tool('read_serial', ..., timeout_seconds=0.01)`
  - observed clean `MCPClientError("Tool 'read_serial' timed out ...")`
  - subsequent fresh client reconnect on the same board succeeded
- timeout recovery on `nucleo_l476rg`:
  - forced `client.call_tool('read_serial', ..., timeout_seconds=0.01)`
  - observed clean `MCPClientError("Tool 'read_serial' timed out ...")`
  - subsequent fresh client reconnect on the same board succeeded
- raw validation on both boards:
  - `client.call_tool('read_serial', {'read_seconds': -1.0})`
  - observed deterministic refusal on both boards
- mixed-board selection on Windows:
  - `connect(board_id='nrf52840dk')` now selects probe `683377322`
  - `connect(board_id='nucleo_l476rg')` now selects probe `066FFF514988525067233337`
- dual-board flash/UART proof:
  - flashed repo reference firmware on `nrf52840dk`
  - flashed repo reference firmware on `nucleo_l476rg`
  - both boards then returned `boot ok` over UART

## Hardware Hand-Off Status

Verified here:

- non-hardware suite listed above
- attached `nrf52840dk` healthy MCP smoke
- attached `nrf52840dk` timeout repro for live MCP tool-call timeout handling
- attached `nrf52840dk` raw invalid-duration repro on `read_serial`

Still pending after this review:

- second-provider proof
- fresh-machine portability proof

## What Is Genuinely Good

- The recent MCP startup cleanup fix was real and valuable; startup no longer
  fails with the earlier cancel-scope bug.
- Turnkey invocation validation is better now: invalid `max_iters` and
  `serial_read_seconds` fail early.
- The codebase is broadly more bounded than it was before this audit:
  provider calls, helper subprocesses, startup, and pyserial write windows all
  have explicit ceilings.
- The timeout path is now materially stronger:
  - no extra outer cancellation wrapper around live MCP tool calls
  - direct MCP timeout errors are normalized into `MCPClientError`
  - expected stdio cleanup noise is suppressed during teardown instead of
    crashing the client
- The raw server surface is stricter now:
  - `read_serial` rejects invalid durations/baudrates
  - memory tools reject invalid `word_size` / `length`
- Mixed-board probe selection now works correctly with both boards attached on
  this Windows host.
