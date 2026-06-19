# R10 Contract

This document is the implementation source of truth for `R10`.

It defines the runtime-safety contract for the current scoped board pair:

- `nrf52833dk`
- `nucleo_l476rg`

It does **not** start `R11+`, does **not** change the scoped board pair, and
does **not** add new MCP tools.

## Runtime Model

- The server keeps the current **single active live debug session** model.
- A new `session_id` is generated only after a successful `connect(...)`.
- `disconnect()` closes the active session and clears any watcher block state.
- A new `connect(...)` starts a fresh runtime session with a new `session_id`.

## Session Output Layout

On successful `connect(...)`, create:

```text
runs/<session_id>/
├── logs/
│   └── events.jsonl
├── captured-serial/
├── applied-patches/
└── run-metadata/
    └── session.json
```

- `events.jsonl` is append-only.
- `session.json` is a machine-readable summary of the active / closed session.
- Pre-session tool failures may be logged outside a session-specific directory,
  but they do not create a scoped runtime session.

## Structured Event Logging

Every completed server tool action is logged as a structured event.

Minimum fields:

- `event_id`
- `session_id`
- `timestamp`
- `tool_name`
- `board_id`
- `probe_uid`
- `route_used`
- `normalized_args`
- `outcome_kind`
- `error_code`
- `duration_ms`

Rules:

- `outcome_kind` is one of: `success`, `refused`, `failed`, `blocked`
- no raw memory blocks are persisted to the event log
- no firmware bytes are persisted to the event log
- `read_serial` logs only bounded metadata plus a bounded excerpt

## Flash Policy

- Only existing local `.elf` and `.hex` files are flashable.
- Directories, missing paths, empty paths, `.bin`, and URL-like paths are
  refused deterministically.
- `flash_firmware()` with no explicit path continues to resolve the tracked
  board baseline exactly as today.
- Default artifact resolution requires an active connected session and a loaded
  board config.
- Explicit path flashing is allowed in this pass, but it must be:
  - local
  - existing
  - a file
  - `.elf` or `.hex`

Required artifact identity metadata:

- resolved absolute path
- suffix
- size bytes
- SHA-256
- whether the artifact was default-resolved or explicitly supplied

This pass does **not** add MCU/ABI heuristic checks.

## Recover Policy

- Recover requires an active connected session.
- Recover requires a loaded board config.
- Recover requires explicit confirmation from the caller.
- Recover requires a supported tracked `recover_mode`.
- Unsupported recover cases are deterministic refusals, not backend-looking
  text.
- After one successful recover in a session, a second recover in the same
  session is refused. The operator must disconnect and reconnect first.

## Refusal / Block Rendering

Stable plain-text responses:

- refusal:
  - `Refused [<code>]: <message> session_id=<id>`
- watcher block:
  - `Blocked [<code>]: <message> session_id=<id>`

Unexpected backend/runtime failures remain real tool errors.

## Shared Policy Boundary

- `server.py` owns:
  - session creation / teardown
  - event logging
  - refusal rendering
  - watcher invocation
- Shared flash/recover guardrail code is reused by:
  - `server.py`
  - `stage0_check.py`
- `stage0_check.py` does **not** adopt the server session store or watcher in
  this pass.

## Convergence Watcher

The first watcher is **mutation-focused**.

Watched action families:

- `flash_firmware`
- `read_serial`
- `unlock_recover`

Read-only tools are logged but never blocked in this pass.

`connect(...)` failures before session creation are logged but are not
watcher-blocked in this pass.

Block rules:

- block after **2 identical flash failures** in the same session when artifact
  identity and failure code are the same
- block after **3 identical UART misses** in the same session when board, port,
  baudrate, expected text, and failure code are the same, with no intervening
  successful UART match
- block after **2 identical recover failures** in the same session when board
  and failure code are the same
- repeated `reset` + `read_serial` miss cycles are treated as UART-miss
  repetition, not as a separate reset-only rule

Block scope:

- UART repetition blocks only future `read_serial`
- flash repetition blocks only future `flash_firmware`
- recover repetition blocks only future `unlock_recover`

Block state clears only when the active session ends and a new one starts.

## Out Of Scope For This Pass

- multi-session server behavior
- new MCP tools
- `R11+`
- re-promoting `nrf52840dk` into the scoped critical path
