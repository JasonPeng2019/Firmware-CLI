# Agentic Firmware Debug Tool — MCP-Centered Architecture & Build Plan

> **STATUS (2026-06): the architecture described here is IMPLEMENTED** for the
> local **stdio** server on the scoped pair — the adapters/services/guardrails
> split, the tools-vs-resources surface, deterministic guardrails below the
> client, and session-keyed runtime state all exist in `src/pyocd_debug_mcp/`.
> The `R12` turnkey brain/CLI exists as the active product layer; the current
> work is the capability prototype described in the build plan and
> `markdowns/curr/r12_turnkey_spec.md`. Still future: remote Streamable-HTTP +
> OAuth transport (`R13`). Design doc; live status in `current-progress.md`.

> This plan reformulates the project around the **MCP-server-as-core** design: one headless
> server holding the hardware tools + deterministic guardrails + convergence watcher, with two
> clients on top — the user's own agent (Claude Code, etc.) and your turnkey brain. It is the
> implementation-decisions level (what to build, in what order, with which protocols/SDKs), not code.
>
> **Verification note.** MCP specifics below are grounded in the current state (protocol revision
> 2025-11-25, `mcp` Python SDK ~1.27.0 with bundled FastMCP, Streamable HTTP transport). MCP is
> evolving fast (stateless operation, OAuth, a Tasks extension all in motion) — re-verify exact
> SDK calls at build time.

---

## Board requirement

- **Board support must be data-driven.** The two reference boards prove the initial path, but they are
  not allowed to become hardcoded special cases in Stage 0, adapters, or server wiring.
- **Any supported board must onboard through `boards/<board>.yaml`.** Probe family, pyOCD target,
  UART defaults, recovery behavior, and discovery hints belong in board definitions, not scattered code
  branches.
- **Stage 0 must consume external board definitions.** The validation script should run the same
  probe/serial/flash/UART flow against built-in boards and newly added board files, so adding support
  for another board is a config exercise first, not a code fork.
- **Board-control behavior must live in reusable internal code, not only in wrappers.** Probe detect,
  flash, UART capture, recover, and validation logic should be implemented once in shared services that
  both MCP tools and local CLI/operator flows can call.

## 0. The shape of the whole product (one server, two clients)

```
                    ┌─────────────────────────────────────────┐
                    │  YOUR HEADLESS MCP SERVER                 │
                    │  (closed source; ships as a process)      │
                    │                                           │
   user's agent ───▶│  • hardware tools (UART, SWD, …)          │
  (Claude Code)     │  • DETERMINISTIC guardrails (flash gate)  │◀─── your turnkey brain
   = their frontend │  • convergence watcher (behavioral)       │     (loop + skills +
   (you build NO UI)│  • structured logging / audit             │      orchestration)
                    │  • session state → external store (Redis) │     = needs a frontend (CLI)
                    └─────────────────────────────────────────┘
                                      │
                          adapters speak SWD/UART/USB
                                      ▼
                            probe → target MCU
```

**The two key consequences that drive everything below:**
1. **An MCP server is headless — it has no frontend.** The *client* supplies the UI. So in
   BYO-agent mode you build **no CLI and no GUI**; the user's Claude Code is the frontend.
2. **Your turnkey product is just another MCP client** of your own server. *It* is the only thing
   that needs a frontend, and that frontend is the CLI. → **The CLI belongs to the turnkey/own-brain
   product, not the MCP server as a frontend surface.** But the hardware-control implementation it uses
   should still be the same shared internal service layer the MCP tools call.

The durable guarantees (safety, convergence-watching, logging) live **in the server, below the
brain**, so they protect every client identically — yours or theirs.

---

## 1. What to build, and what you DON'T build

| Component | Build it? | Notes |
| Headless MCP server (tools + guardrails + watcher + logging) | **Yes — this is the core** | Closed source; ships as a running process, not source |
| Hardware adapters (UART, SWD-with-backends) | **Yes** | Same as before; they sit inside the server |
| Shared board-control services / operations | **Yes** | The reusable layer above adapters and below wrappers; called by MCP tools, Stage 0 flows, and your turnkey client |
| Frontend for BYO-agent mode | **No** | The user's agent app IS the frontend |
| CLI | **Only for turnkey mode** | It's the frontend for *your* brain-client |
| Your turnkey brain (loop, skills, orchestration) | **Yes — the premium tier** | An MCP client of your own server; can run server-side to stay closed |

---

## 2. The MCP server — build decisions

### SDK & framework
- **Official `mcp` Python SDK**, using the bundled **FastMCP** high-level interface
  (`@mcp.tool()` decorators). FastMCP is the recommended path and ships inside the official SDK —
  not a third-party add-on. Drop to the raw SDK only if you need custom transport/low-level control
  (you likely won't for v1).
- **Return typed text/content blocks, not raw dicts.** A known gotcha: a tool returning a raw
  Python dict renders in the Inspector but can come back truncated inside the client. Return strings/
  content text blocks.

### Transport
- **Two transports, two stages:**
  - **stdio** — local; the client launches your server as a subprocess. **Use this for v1 / local
    bench use.** Lowest latency (single-digit ms), simplest, no auth needed. This is the default for
    Claude Desktop / Claude Code local servers.
  - **Streamable HTTP** — remote; your server runs as a web service reachable by multiple clients.
    Adds ~5–25 ms/round-trip. **Use this when you offer a hosted option.** Requires OAuth 2.1.
- **Build local (stdio) first; go remote (HTTP) only when sharing.** This matches the hardware
  reality anyway: the server must run on the bench machine that owns the USB link to the board.
- Validate every tool with the **MCP Inspector** before wiring a real client — surfaces schema
  errors that otherwise fail silently in the client.

### State (the convergence watcher's foundation)
- MCP sessions are currently **stateful** — each client-server connection is an isolated session
  carrying tool-execution context. So the server *can* remember prior tool calls in a session,
  which is exactly what behavioral convergence detection needs.
- **BUT the ecosystem is moving toward stateless servers for horizontal scaling.** Decision:
  **externalize session state into an external store (e.g. Redis) keyed by session ID from day one**,
  even on a single instance. This makes you stateless-ready and is the explicitly recommended pattern.
- For the local stdio bench case, a single warm process is fine, but still key the watcher's memory
  by session so the remote path is a config change, not a rewrite.

### Auth
- stdio/local: no auth needed.
- Remote/HTTP: **implement OAuth 2.1 from the start** — API-key auth is being deprecated for
  enterprise and retrofitting OAuth later is significantly harder. Build it in when you add HTTP.

### Long-running hardware operations
- Hardware ops like "flash then run 30 s and capture serial" don't return instantly. Watch the
  **Tasks extension** (server returns a task handle; client drives `tasks/get` / `tasks/cancel`).
  It's evolving — don't depend on it yet, but design tool returns so a later move to task-handles
  isn't a rewrite (e.g. a tool can return a "run id" you poll via another tool in the interim).

---

## 3. Tools the server exposes (MCP "tools" primitive)

Each is a `@mcp.tool()` wrapping a shared internal service method, which in turn
uses adapters/guardrails as needed. The same service methods should also be
callable by non-MCP local flows such as `stage0_check.py` or the turnkey
programmer. Note MCP's primitive split:
- **Tools** = actions with side effects → flash, reset, halt, resume, apply_patch.
- **Resources** = read-only data → current serial buffer, last register dump, memory read.
  Modeling reads as *resources* and actions as *tools* matches MCP's security model and makes the
  read/write distinction explicit to any client.

| Name | Primitive | Wraps |
|---|---|---|
| `flash_firmware` | tool (gated) | shared flash service over the SWD backend |
| `reset_and_halt` / `halt` / `resume` | tool | shared control service over the SWD backend |
| `apply_patch` | tool | source edit service (full-file v1, diffs later) |
| `read_register` / `read_memory` | resource | shared read services over the SWD backend |
| `read_serial` | resource | shared UART capture/read service |
| `resolve_symbol` | resource | shared symbol-resolution service |

---

## 4. Guardrails IN THE SERVER (not in any brain)

This is the design pivot: because two different brains drive the server, guardrails must live
below the brain so they bind both.

- **Pre-flash safety gate (deterministic).** Inside `flash_firmware`, before the adapter touches
  hardware: validate image, refuse fuse/option-byte writes, require a known-good recovery image.
  Returns a refusal through the protocol if unsafe. Binds your brain AND the user's Claude Code.
- **Behavioral convergence watcher (deterministic backbone).** The server sees every tool call in a
  session. Hash each flashed image / patch; detect (a) exact repetition, (b) non-shrinking failure
  signature, (c) oscillation between states. On "stuck": **refuse further action tool calls** and
  return a non-convergence notice. This is the lever that works even against an opaque external
  brain — you can't stop their loop, but a server that won't flash stops the damage.
  - *Limit to state honestly:* you detect clear-cut thrashing fully; the fuzzy "exploring vs.
    circling" judgment needs the reasoning trace you don't have for external brains. Optional
    watcher-*model* may add a fuzzy advisory layer, but deterministic signals are the hard stops
    (don't let an LLM watcher be the sole judge — shared blind spots).
- **Structured logging / audit.** Log every tool call in a structured format. One mechanism, three
  payoffs: feeds the convergence watcher, becomes the engineer-feedback feature, and pre-conforms to
  the coming MCP audit spec.

---

## 5. The turnkey brain — the ONLY part with a frontend

- It is an **MCP client** of your own server (same server the user's Claude Code would hit).
- It holds the parts that are *yours* and premium: the agent loop, **skills injection** (structured
  per-chip/peripheral knowledge — the validated moat), hypothesis→experiment orchestration, and the
  loop-aware convergence logic that needs to see the reasoning arc.
- **Frontend = CLI**. Embedded engineers live in the terminal. A GUI can come later; the CLI is the
  v1 frontend and must show live progress rather than only end-of-run summaries.
- **Keys:** BYOK (user supplies their API key in config) is the default and keeps the moat intact.
  You can also point your own keys at it for a fully managed offering.
- **Closed-source:** keep the brain's valuable logic server-side if real secrecy matters (local
  Python is easy to decompile). The commodity part (adapters) is what's hard to hide; the moat
  (skills, orchestration) is what you keep server-side — which lines up cleanly.

Current `R12` prototype control model:

- **Persistent provider sessions:** API-backed providers should continue the
  same inference session/conversation across turns. CLI-backed providers may
  remain wrapper based until their surfaces support true persistence, but the
  brain contract should be session-oriented.
- **Free host work, governed board work:** host-only file/process/code actions
  are model-native. Any action that touches server-native tools, hardware, or
  the board must be expressed as the model's final structured board decision and
  executed by the brain.
- **Three action classes:** model actions are host-only, client actions are
  model-authored session scripts, and server tools are hardware/server-native.
  Client actions that call server tools are governed exactly like direct server
  tool calls.
- **Schemas, not summaries:** the prompt includes the real MCP tool
  descriptions/schemas so the model composes valid calls and ordered batches.
- **Batches:** one board decision may contain an ordered sequence of governed
  actions, including `wait` and UART write in the prototype surface.
- **Timeouts:** the model may propose per-action timeout and iteration budgets,
  but the brain clamps them, enforces unattended hard caps, and syncs allowed
  timeout changes to the server for subsequent operations.
- **Progress and checkpoints:** UART reads, builds/external commands, and long
  client actions can emit chunks/checkpoints. The brain records them, streams
  operator progress, may ask the model for a checkpoint/cancel verdict, and
  ignores any non-verdict text from that checkpoint turn.
- **Inspector:** developer builds can mirror prompt turns, provider stream text,
  parsed decisions, tool calls, server observations, and state snapshots into a
  terminal/log stream for debugging.
- **Canonical memory + selective recall:** the brain owns structured memory
  independent of provider session internals. It stores a working snapshot,
  exact recent boundary decisions, compact older history, artifact refs, and
  code/workspace context. Each prompt can receive pinned facts plus a short
  memory index/table of contents; full memory entries are recalled selectively
  by profile, task, or model request.
- **Static-context efficiency:** selected skill safety lines and a compact skill
  index stay always visible, while expensive skill bodies and repeated static
  prompt blocks are loaded or reused on demand. Artifact/result cache may skip
  deterministic setup repeats, but never replaces required final live proof.

---

## 6. Build order (revised around MCP)

1. **Adapters, hand-tested** (UART then SWD/pyOCD on the L476RG) — unchanged; still the first mile.
2. **Wrap adapters as a local stdio MCP server** with FastMCP. Validate with MCP Inspector.
3. **Add the deterministic guardrails inside the server** (flash gate first, then the convergence
   watcher with session-keyed external state).
4. **Connect a real external client** (your own Claude Code) to prove BYO-agent mode end to end —
   no frontend of your own yet.
5. **Build the turnkey brain as a second client** + its CLI frontend; add skills injection.
6. **Only when sharing remotely:** add Streamable HTTP transport + OAuth 2.1.

---

## 7. Tiering that falls out of the architecture (commercial)

- **BYO-agent tier:** your headless server + their agent. They get safe hardware tools + behavioral
  anti-thrash protection; they bring their own brain. You build no UI. (Honest line to customers: the
  protection here is behavioral and slightly coarser than turnkey — a reason to upsell, not a flaw to hide.)
- **Turnkey tier:** your server + your brain (skills, full orchestration, loop-aware convergence) +
  CLI. The premium product.
- Same codebase, two products; closed-source throughout (server ships as a process exposing an
  interface; brain logic can stay server-side).

---

## Standing risk
MCP is mid-transition: stateful→stateless, OAuth maturing, Tasks extension in flux. The *shape* here
is sound; the exact SDK calls, transport config, and state/auth APIs will shift — confirm against the
live spec and `mcp` SDK at build time. And as always, progress is gated on Phase-1 adapters working on
the L476RG before any of the MCP layer matters.
