> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# R12 Branch B Action Boundary Spec

## Goal in plain English

Task: implement `R12` prototype Wave 1 Branch B: action boundary, ordered
board-action batches, bounded brain-local `wait`, UART write, and
session-scoped client actions.

Roadmap anchor: `R12` prototype Wave 1 / Branch B, as split in
`markdowns/R12_P_SPLIT.md`.

Branch B makes the turnkey brain more agentic without weakening the closed MCP
server boundary. The model may do ordinary host-only work through its native
provider surface, but any board/server-native operation still closes a turn as
a governed decision and runs through the brain gate.

## Scope and non-scope

In scope:

- classify model-native host work separately from governed board/server-native
  actions;
- keep ordinary host file/shell/script authoring out of the MCP server;
- execute ordered batches of governed actions with deterministic ordering,
  result aggregation, and bounded failure behavior;
- add `wait` as a bounded brain-local action, not a server tool;
- add UART write as real hardware I/O through the UART adapter, shared service,
  MCP tool, turnkey client wrapper, and brain allowlist;
- implement a session-scoped client-action store for model-authored scripts;
- run board-touching client actions only through `run_script(name, inputs)`;
- snapshot and hash the script version that actually runs;
- inject a gated server-tool API only during governed `run_script` execution;
- record enough action/client-action evidence for Branch D/E/F to consume later.

Out of scope:

- provider-session persistence, schema prompting, or provider adapter rewrites
  beyond the action-surface text Branch B must expose;
- timeout default/clamp policy, server timeout-sync policy, or model-estimated
  budget policy;
- inspector UI, progress rendering, or provider streaming UI;
- stream checkpoint/cancel behavior for long client actions;
- scoped green approval or flipped-value test verdicts;
- provider-native tool-call conversion;
- project-persistent custom tools outside the current client session;
- broad MCP-server host command/file execution;
- raw hardware access from client scripts;
- write-memory/register tools, breakpoint mutation, or expanded debug mutation
  power.

## Reconciliation summary

Build plan:

- `R12` current prototype target says host-only work is model-native, while
  server-native board tools remain governed by the brain.
- A decision may contain an ordered batch of actions.
- The prototype adds `wait`, UART write, and client actions.
- Client actions are session-scoped scripts; scripts that call server tools are
  governed and every server call routes through the brain.
- The MCP server remains the board-control surface with deterministic guardrails.

Current code:

- `TurnDecision` in `brain/actions.py` currently carries one `action`, not an
  ordered action batch.
- `brain/decision_types.py` already contains P0 future-facing shapes for
  `ActionCall`, `ActionBatch`, and `BoardDecision`, but they are not wired into
  the active loop.
- Current local host actions (`read_file`, `replace_file`, `run_build`,
  `run_green_check`) are structured brain actions, not truly provider-native
  host work.
- `brain/client_actions.py` is only a minimal in-memory record store.
- The UART adapter/service/server path is read-only: `UARTInterface` exposes
  `open`, `close`, `reset_input_buffer`, and `read`; `server.py` exposes
  `read_serial`, not `write_serial`.
- `AllowedServerToolName` does not include `write_serial`.
- `wait` is not currently modeled as a first-class action.

Other docs or notes:

- `markdowns/R12_P_SPLIT.md` says Branch B owns action policy, host-action
  boundary, batches, `wait`, UART write, and client actions.
- `markdowns/R-12_P_Explanations.md` and
  `markdowns/curr/things-to-change.md` say the north star is: free local agent
  on top, deterministic board gate underneath, and one governed decision per
  board-facing turn.
- `markdowns/firmware_agent_mcp_architecture.md` says the CLI belongs to the
  turnkey brain/client, while the MCP server remains headless board control.

Disagreements:

- No source-of-truth conflict was found. The current code is behind the
  prototype docs, but that is expected: Branch B is the implementation packet
  for this missing behavior.
- The only important ambiguity is how to treat the current structured host
  actions during the transition to model-native host work. This spec resolves
  it by keeping Branch B from adding any new broad host executor. Existing local
  workspace helpers may remain as compatibility hooks where the current provider
  path still needs them, but Branch B must classify them as host-side client
  behavior, not server-native board actions and not MCP server tools.

## Design

### Boundary model

Branch B introduces an action policy with three classes:

1. Model-native host work: ordinary file reading/writing, shell commands, local
   computation, and host-only helper script authoring. This stays outside the
   governed board decision and must not be added to the MCP server.
2. Brain/client-local actions: bounded `wait`, client-action create/update/list
   metadata, and compatibility local workspace helpers that do not touch the
   board. These may be audited by the brain, but they are not server-native.
3. Governed server-native actions: direct MCP tools, UART write, and
   board-touching client actions. These always route through the same brain gate
   used by current direct server-tool actions.

The model's final governed decision may return a result to the user or request
one ordered batch of governed actions. Host-only work is allowed before that
decision, but Branch B does not attempt to sandbox the provider or physically
prevent direct hardware bypass. The accepted soft-guardrails stance remains:
the sanctioned cooperative path is gated, logged, and easier than bypassing.

### Action policy and prompt contract

Add an action-policy module that can classify an action name as model-native,
brain-local, client-action, or server-native. The classification is the single
source used by parsing, batch execution, client-action execution, and tests.

The active prompt/schema should guide the model toward the new shape without
changing provider output format to native tool calls. The default contract
remains JSON returned to the provider wrapper. Branch B may keep backward
compatibility for the old single-action `TurnDecision`, but the branch is
accepted only when a batch-capable decision path is wired and tested.

### Batches

A batch is an ordered list of action calls. The executor runs calls strictly in
order and records one result per call.

Batch failure behavior:

- invalid, refused, blocked, timed-out, or unexpected-failure results stop the
  remaining calls by default;
- earlier successful results remain recorded;
- the aggregate result states which call stopped the batch and why;
- no later action is attempted after a stop condition;
- `finalize` is not valid inside a board-action batch. Returning/finalizing is a
  separate return decision.

Batch execution must reuse the same direct-action gate for server-native calls.
It must not call MCP tools through a new bypass path.

### Wait

`wait` is a brain-local action with a positive duration. It sleeps in the brain,
is bounded by the active timeout policy from Branch C/P0 timeout config, records
an action result, and never appears as an MCP server tool.

Until Branch C lands full timeout policy, Branch B should use the existing
configured batch/default bounds and fail closed on nonpositive or excessive
waits.

### UART write

UART write is board/server-native hardware I/O and must be built through the
normal layer stack:

- extend the UART adapter contract with write support;
- implement pyserial-backed write using pyserial's write timeout;
- add a shared UART service helper for bounded writes;
- expose an MCP `write_serial` tool with a docstring that documents when to use
  it, input text/bytes semantics, baud/port/default behavior, timeout behavior,
  and recovery guidance;
- add `write_serial` to the curated model-facing allowed server tool surface;
- add a `LocalMCPClient.write_serial(...)` wrapper;
- route turnkey `write_serial` through the same `_execute_server_tool` policy
  path as other server tools;
- log the write as a server event and watcher-relevant action.

The first prototype supports UART only. I2C, SPI, RTT, SWO, and broader device
stimulus are later work.

### Client actions

Client actions are session-scoped model-authored scripts/tools. They are stored
in the current turnkey client session, not in the Codex/Claude provider session
and not in a project-persistent store.

The model may author or edit script files using model-native host work. The
governed decision contains only a short `run_script(name, inputs)` action.
Script bodies are not embedded in `TurnDecision`.

On `run_script`:

- the brain resolves the named script from the session client-action store;
- the brain snapshots the exact script text and records a content hash before
  execution;
- the brain provides a small execution API for inputs, outputs, and gated
  server-tool calls;
- the gated server-tool API exists only during that `run_script` execution;
- every server-native call from the script routes back through the same action
  policy, timeout path, event path, and MCP client gate as a direct call;
- scripts cannot import or receive a raw MCP client, serial port handle, SWD
  handle, board probe UID shortcut, or unrestricted hardware object.

Host-only scripts that do not call server-native tools may remain model-native
and do not require governed execution. Branch B only governs scripts when they
touch the server/board or when the model explicitly asks the brain to run a
registered client action.

### Integration boundaries

Branch B should keep broad edits to `brain/loop.py`, `brain/actions.py`,
`brain/cli.py`, and `server.py` small. Most behavior should live in focused
modules for policy, batches, and client actions, with narrow integration hooks
into the existing loop and MCP client.

Branch B may consume P0 shapes from `decision_types.py` and existing timeout
config values. It must not redesign Branch A provider sessions or Branch C
timeout clamps/events. If Branch A's schema bundle is present, Branch B should
use it for model-facing action text; otherwise Branch B should keep its prompt
change localized and merge-safe.

## Board-facts-as-data and origin tags

No board-specific values may be introduced in Branch B.

Required value origins:

- `write_serial` action/tool name: `PROJECT-DEFINED` from this spec and the
  `R12` prototype target.
- `wait` action name: `PROJECT-DEFINED` from this spec and the `R12` prototype
  target.
- maximum/default wait and batch bounds: `PROJECT-DEFINED`; use existing
  timeout config where available rather than new literals.
- UART baudrate: comes from board config unless explicitly overridden by the
  caller; no hardcoded baudrate.
- UART port: comes from serial resolution or explicit caller override; no
  hardcoded `COM*` or `/dev/*` paths.
- UART write timeout: derived from the active timeout config or pyserial open
  timeout; no unbounded write path.
- client-action script hash algorithm: `PROJECT-DEFINED`; choose one standard
  library hash and record it in code comments when implemented.

## Documentation plan

- This spec is the `/specs` proposal for Branch B.
- If the implementation adds `write_serial`, the MCP tool docstring in
  `src/pyocd_debug_mcp/server.py` is the user/model-facing documentation for
  that tool. Do not add a sidecar MCP-tool markdown file.
- If prompt/action schema text changes, update the owning brain prompt/schema
  doc or code-generated schema source in the same implementation unit.
- If client-action artifacts are added to `runs/<session_id>/...`, update the
  R12 turnkey run-capture documentation or `r12_turnkey_spec.md` only if the
  artifact contract changes beyond what it already describes.
- If implementation discovers that this spec contradicts the build plan, stop
  and get sign-off before changing the build plan.

## Portability

Branch B must preserve Windows/macOS portability:

- use `pathlib` for client-action storage paths;
- do not use shell-specific script execution for governed client actions;
- do not assume executable bit behavior;
- do not hardcode serial ports or path separators;
- preserve UTF-8-with-replacement capture behavior for subprocess/script output;
- keep script execution bounded and return control on timeout;
- ensure pyserial write behavior is tested with fakes and does not depend on a
  platform-specific serial implementation.

No new install step is expected. If a later implementation requires an extra
runtime dependency for script isolation, that dependency must be added through
the normal package/lock workflow and documented as part of the same build pass.

## Verification plan

Non-hardware tests required:

- action-policy tests classify model-native, brain-local, client-action, and
  server-native actions correctly;
- parsing/schema tests accept ordered batches and reject malformed batches;
- batch executor tests prove strict ordering, result aggregation, early stop on
  refusal/block/timeout/failure, and no execution of later calls after stop;
- `wait` tests prove nonpositive durations are refused, bounded waits return,
  and excessive waits are clamped or refused according to the active config;
- client-action store tests cover create/update/list/get/run metadata and
  deterministic sorting;
- client-action execution tests prove script snapshot and hash capture;
- gated API tests prove scripts cannot receive raw MCP/serial/SWD handles and
  that every server-native script call goes through the same brain gate;
- UART adapter/service tests use fakes to prove write data, timeout, flush/close
  behavior, invalid baud/read/write argument refusals, and text/bytes handling;
- server tests prove `write_serial` requires a loaded board/session context,
  resolves port/baud correctly, records events, and returns stable text;
- MCP client tests prove `LocalMCPClient.write_serial(...)` passes arguments and
  timeout correctly;
- loop tests prove direct `write_serial`, batched `write_serial`, `wait`, and
  governed `run_script` update state/action logs without bypassing policy;
- regression tests prove existing single-action decisions still work until final
  integration intentionally removes any compatibility path.

Non-hardware ladder:

```powershell
uv run pytest -q
uv run ruff check .
uv run mypy src
```

Recommended focused suites during build:

```powershell
uv run pytest -q tests/test_p0_foundation.py tests/test_uart_capture.py tests/test_server_runtime_tools.py tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py
```

Pending hardware proof:

```powershell
uv run python host_bootstrap.py --board-id nucleo_l476rg
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg

uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

After Branch B is merged with the required A/C hooks, run a turnkey smoke that
uses a batch containing `connect`, `write_serial` where the reference firmware
can safely receive UART input, `wait`, `read_serial`, and `disconnect`. If the
current reference firmware has no command parser, UART write hardware proof may
be limited to "bytes written without serial/backend failure" until a command
echo fixture exists; do not claim device-level stimulus response unless the
firmware actually observes and reports it.

## Acceptance criteria

Branch B is complete when:

- the model-facing decision path supports an ordered batch of governed actions;
- direct server-tool actions still route through the existing brain gate;
- batch execution is ordered, bounded, logged, and stops deterministically on
  the first blocking failure;
- `wait` is implemented as a bounded brain-local action and is not exposed as an
  MCP server tool;
- UART write exists through adapter, service, MCP tool, MCP client wrapper,
  action allowlist, and brain execution path;
- `write_serial` has an MCP tool docstring suitable for client consumption;
- session-scoped client actions can be registered, listed, updated, and run by
  name with inputs;
- governed client-action execution snapshots and hashes the exact script that
  ran;
- board-touching client-action server calls route through the same gate as
  direct server-tool calls;
- no general host shell/file executor is added to the MCP server;
- existing R12 single-action behavior remains green or has a documented and
  tested compatibility migration;
- the required non-hardware ladder passes;
- hardware UART write and Branch B turnkey smoke are either proven on the
  scoped pair or explicitly marked pending hardware with exact hand-off
  commands.

## Verified

- This spec began as a documentation-only proposal; product-code behavior is
  now tracked by the implementation and process ledger.
- The spec is aligned with the build plan's `R12` prototype target:
  host freedom, governed board actions, batches, `wait`, UART write, and client
  actions.
- The spec reconciles against the current `P-Wave-B` code shape: P0 action
  shapes exist, but Branch B behavior is not yet implemented.
- The spec preserves the closed MCP server boundary from the MCP architecture
  doc and the Branch B clarification docs.
- Implementation pass completed on `P-Wave-B` after this proposal was written.
- Full non-hardware ladder passed:
  - `uv run pytest -q` -> 277 passed
  - `uv run ruff check .` -> passed
  - `uv run mypy src` -> passed
- Real hardware and real MCP proof passed on the two physically connected
  boards:
  - `nucleo_l476rg`
  - `nrf52840dk`
- Real turnkey Branch B batch smoke passed on those two physical boards with
  one MCP session per board and an ordered
  `connect -> write_serial -> read_serial` batch.
- Real turnkey full Branch B feature smoke passed on those two physical boards
  with one MCP session per board and an ordered
  `connect -> wait -> run_script(write_serial) -> read_serial` batch.

## Pending verification

- Exact `nrf52833dk` hardware proof remains pending because the connected
  Nordic board reports `FICR.INFO.PART=0x52840`, not `0x52833`.
- Branch B has not been merged with Branch A/C.
- Manual shared-USB confirmation remains pending for `nrf52840dk`; automated
  Stage 0 checks passed, but the Stage 0 report still listed that manual item.
