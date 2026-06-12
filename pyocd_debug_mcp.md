# pyOCD Debug MCP

This is the script doc for the `pyocd-debug-mcp` console entrypoint backed by
`src/pyocd_debug_mcp/server.py`.

## 1. Purpose And When To Run Vs. When Not To Run

`pyocd-debug-mcp` starts the local MCP server that exposes pyOCD-backed debug
tools over stdio. It is the runtime entrypoint an MCP client uses after setup
and Stage 0 are already acceptable.

Run it when:

- the host is already bootstrapped
- the active bench board already passed enough Stage 0 validation
- an MCP client or MCP Inspector session needs local board access

Do not run it when:

- the machine still needs bootstrap; run `setup_host`
- board visibility is still uncertain; run `host_bootstrap.py`
- the board itself still needs Stage 0 validation; run `stage0_check.py`

Conflicting states:

- the server keeps one live debug session open at a time
- another tool owning the same probe can make `connect` fail

## 2. Exact Behavior

On startup, the entrypoint:

1. loads repo-local `.env` if present
2. builds a FastMCP server named `pyocd-debug`
3. keeps one global pyOCD session for the process lifetime
4. serializes all probe access behind one lock
5. runs the MCP server over stdio transport

At runtime:

- `connect` opens the one live pyOCD session
- all other tools operate on that session
- `disconnect` closes it
- uncaught pyOCD or runtime errors surface back to the MCP client as tool
  errors

Side effects:

- opens and holds a live debug session
- can halt, resume, step, reset, read, write, and set or clear breakpoints

## 3. Inputs

### Process Startup

- `uv run pyocd-debug-mcp`
  Normal local server startup
- `uv run mcp dev src/pyocd_debug_mcp/server.py`
  Inspector or development startup path

The server itself does not define extra CLI flags in the current
implementation.

### Environment

- `.env`
  auto-loaded when present
- `PYOCD_PROBE_UID`
  used by `connect()` when the caller does not pass `unique_id`
- `PYOCD_TARGET`
  used by `connect()` when the caller does not pass `target`

### Tool-Level Inputs

- `connect(unique_id=None, target=None)`
- `disconnect()`
- `get_state()`
- `halt()`
- `resume()`
- `step()`
- `reset(halt_after=True)`
- `read_core_register(name)`
- `write_core_register(name, value)`
- `read_memory(address, word_size=32)`
- `read_memory_block(address, length)`
- `write_memory(address, value, word_size=32)`
- `set_breakpoint(address)`
- `remove_breakpoint(address)`

Numeric string inputs accept hex or decimal according to the current helper
implementation.

## 4. Outputs And Logs

### Process-Level Behavior

- on normal startup, the process begins serving MCP over stdio
- MCP clients or Inspector will see the tool schema listed above
- the process stays attached to stdio until terminated

### Tool Response Meanings

Common successful responses:

- `Connected to board '...' via probe ...`
- `Disconnected.`
- `Halted.`
- `Resumed.`
- `Stepped. pc=0x...`
- `Reset and halted.`
- `Reset and running.`
- `0x...` from register or memory reads
- `Wrote ...`
- `Breakpoint set at ...`
- `Breakpoint removed at ...`

Common non-exception guard responses:

- `Already connected. Call \`disconnect\` first to switch probes.`
- `Not connected.`

Common exception text visible to the MCP client:

- `Not connected to a probe. Call \`connect\` first.`
- `No matching debug probe found.`

What they mean:

- `Already connected...`
  the process already owns one probe session and refuses to switch implicitly
- `Not connected.`
  `disconnect` was called with no live session
- `Not connected to a probe. Call \`connect\` first.`
  a stateful tool was called before `connect`
- `No matching debug probe found.`
  pyOCD could not find a probe matching the requested or environment-derived
  selection

### Exit Codes

- `0`
  clean process shutdown
- non-zero
  startup or runtime exception terminated the process

## 5. Failure Modes

- Symptom: the server process fails to start because Python modules are missing
  Cause: repo environment is incomplete
  Fix: run `uv sync`
  Rerun: `uv run pyocd-debug-mcp`

- Symptom: `No matching debug probe found.`
  Cause: no probe matched the requested or environment-derived selection
  Fix: repair host visibility or call `connect` with a correct `unique_id` or
  `target`
  Rerun: `host_bootstrap.py`, `stage0_check.py`, then `connect`

- Symptom: `Not connected to a probe. Call \`connect\` first.`
  Cause: a stateful tool was called before `connect`
  Fix: call `connect`
  Rerun: `connect`

- Symptom: `Already connected. Call \`disconnect\` first to switch probes.`
  Cause: one live session is already active
  Fix: call `disconnect`, then `connect` again
  Rerun: `disconnect`, then `connect`

- Symptom: a read, write, or breakpoint tool returns an MCP error after a
  successful `connect`
  Cause: pyOCD reached the probe but the target state or requested operation is
  invalid
  Fix: validate the board again with `stage0_check.py`, then reconnect and
  retry
  Rerun: `uv run python stage0_check.py --board-id <board>`, then restart the
  server or reconnect

## 6. Rerun Guidance

- If startup fails, repair the environment or host readiness first.
- If `connect` fails, switch to `host_bootstrap.py` or `stage0_check.py`
  instead of guessing at probe state.
- If a tool says the server is not connected, call `connect`.
- If a tool says the server is already connected to the wrong thing, call
  `disconnect` and reconnect intentionally.
- If a target-level tool errors after connection, validate the board again with
  Stage 0 before continuing.

## 7. Prerequisite Sequence

Run these in order:

1. on a fresh machine, run `setup_host.ps1` or `setup_host.sh`
2. run `uv run python host_bootstrap.py`
3. run `uv run python stage0_check.py --board-id <board>` for the active bench
4. start the server:
   `uv run pyocd-debug-mcp`
5. from the MCP client, call `connect`

Preconditions this script assumes:

- the repo environment is installed
- the local machine can reach the USB-attached board
- the board is in a state where pyOCD can attempt a connection

Auto-handled by earlier scripts:

- environment installation and vendor-tool repair
- host readiness validation
- Stage 0 board validation

Agent-must-run explicitly:

- start the server process
- call `connect`
- choose `unique_id` or `target` when defaults are insufficient

## 8. Verification Status

Verified:

- non-hardware verification: this doc matches the current server tool surface
  and startup model in `server.py`

Pending verification:

- live MCP Inspector validation against real hardware
- behavior of all tool calls on both supported board families
