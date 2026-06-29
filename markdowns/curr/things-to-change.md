# Things To Change

This backlog is ordered by implementation priority: earliest prototype-enabling
changes first, later MVP/product polish last. The old entry numbers are preserved
so existing cross-references like "entry #7" still point to the same change.

# Prototype Priority

ONLY INCLUDE for the first capability prototype:

1. Persistent session and model memory.
   - Future spec for the stronger canonical memory/recovery layer:
     `markdowns/curr/canonical-memory-layer_spec.md`.
     Implement later when improving recovery reliability and the
     `anthropic-api` / Claude API facet; it is not implemented in the current
     Branch A recovery work.
2. Free host work with a final governed board-decision boundary.
3. Real tool schemas in the prompt.
4. Basic timeout hardening and timeout audit fixes.
5. Model-estimated iteration and timeout budgets inside brain caps.
6. Batches, `wait`, and UART write.
7. Client actions / model-authored scripts.
8. Progress output and developer inspector.
9. Stream checkpoints for UART/build/client-action flows.
10. Scoped green approval via model-made flipped tests.
11. Prompt incentive for targeted debug prints.
12. Proof escalation ladder for expensive live validation.
13. Cache-assisted artifact/result reuse for setup and repeated non-final checks.
14. Skill index/on-demand skill bodies for static-context efficiency.

# Later MVP / Nice-To-Have Priority

Defer until after the prototype proves the core loop:

- broader project-level persistent custom tools;
- skill-guided A/B/C host-work experiments;
- provider-native tool-call output format;
- wider device stimulus beyond UART;
- broad shipped-product UI polish.

-----

## Design in one paragraph (the north star these entries serve)

**Codex (the model) works freely on the host all turn; the brain is purely the
*board gate*; and every turn ends with exactly one decision that either *uses the
board (through the brain)* or *returns without it*.** Three consequences the rest of
this doc elaborates:

1. **The model can do anything on the host** — files, shell, local scripts — bounded
   only by the provider sandbox (`danger-full-access`), **not** by the brain. The
   brain governs the *board*, never the host (entry #11; see the accepted stance).
2. **The board is reachable only through the brain — structurally, not by rule.**
   The server (hardware) tools are locked behind the brain: the brain owns the MCP
   session and the gated client API exists only inside a governed decision, so there
   is no other sanctioned path to the board. (A model reaching *raw* hardware around
   the brain is the accepted soft-guardrails residual.)
3. **Every turn closes with one governed decision**, which is binary in spirit:
   *perform a board action* (a server-native decision — `run_script`, `flash`,
   `read_memory`, …) **or** *return* (a terminal/communication decision —
   `done` / no-op, `respond_to_user`, `needs_clarification`, `infeasible`). A
   decision always closes the turn (keeping the brain's `BrainState`/convergence
   boundary), but "return" means the turn touched no board.

So: a free local agent on top, a deterministic board-gate underneath, and one
governed decision per turn as the seam between them. Entries #9, #11, and #12 define
this directly; the others (memory, batches, device I/O, timeouts, verdicts, scripts,
projects) hang off it.

### Non-regression rule: do not re-gate inert local work

No local inert action may require a `TurnDecision` unless it feeds convergence,
bounded execution, firmware-deliverable state, or hardware access. File reads,
directory listing, local scratch computation, native script authoring, and pure-local
script execution stay model-native/free and are only observed at the next governed
boundary. If a future entry appears to require a brain turn for those actions, read
it as describing the current bridge or deterministic CI mode, not the prototype
north star.

## Contents

### Prototype foundation and safety

- [Priority Order](#priority-order)
- [Cross-cutting: maintaining the native session over Claude / Codex API credits](#cross-cutting-maintaining-the-native-session-over-claude--codex-api-credits)
- [Accepted design stance: direct hardware access is not sandboxed](#accepted-design-stance-direct-hardware-access-is-not-sandboxed)
- [2. Separate deterministic safety-state from model reasoning-context (give the brain real memory)](#2-separate-deterministic-safety-state-from-model-reasoning-context-give-the-brain-real-memory)
- [11. Two tool classes: model-native (free) vs server-native (governed)](#11-two-tool-classes-model-native-free-vs-server-native-governed)
- [12. The model only outputs a decision when it needs the board](#12-the-model-only-outputs-a-decision-when-it-needs-the-board)
- [1. Forward real MCP tool descriptions/schemas into the turnkey brain prompt](#1-forward-real-mcp-tool-descriptionsschemas-into-the-turnkey-brain-prompt)
- [18. Replace fixed max-iters defaults with model-estimated iteration budgets](#18-replace-fixed-max-iters-defaults-with-model-estimated-iteration-budgets)
- [17. Prompt the model to instrument unexpected failures with targeted prints](#17-prompt-the-model-to-instrument-unexpected-failures-with-targeted-prints)
- [8. Gated early-exit verdicts: infeasible, needs_intervention, ambiguous](#8-gated-early-exit-verdicts-infeasible-needs_intervention-ambiguous)

### Prototype execution surface and bounded waits

- [14. Bound every blocking call (timeout and hang audit)](#14-bound-every-blocking-call-timeout-and-hang-audit)
- [15. Full timeout and hang audit (whole repo)](#15-full-timeout-and-hang-audit-whole-repo)
- [7. Timeouts, hang-prevention, and a wait action](#7-timeouts-hang-prevention-and-a-wait-action)
- [5. Model-composed batches: a sequence of tool calls per turn](#5-model-composed-batches-a-sequence-of-tool-calls-per-turn)
- [6. Device input tools: UART write (and future I2C/SPI stimulus)](#6-device-input-tools-uart-write-and-future-i2cspi-stimulus)
- [9. Model-authored scripts (code mode) over the gated server-tool API](#9-model-authored-scripts-code-mode-over-the-gated-server-tool-api)

### Prototype visibility, checkpoints, and proof

- [19. Live provider progress with separate authoritative decisions](#19-live-provider-progress-with-separate-authoritative-decisions)
- [20. Developer turn inspector for live brain/provider/server traffic](#20-developer-turn-inspector-for-live-brainproviderserver-traffic)
- [21. Model-cancellable checkpoints for chunked UART/build/client-action streams](#21-model-cancellable-checkpoints-for-chunked-uartbuildclient-action-streams)
- [16. Scoped success gates (replace the whole-board green check)](#16-scoped-success-gates-replace-the-whole-board-green-check)
- [22. Proof escalation ladder for expensive live validation](#22-proof-escalation-ladder-for-expensive-live-validation)
- [23. Cache-assisted artifact/result reuse for setup and repeated non-final checks](#23-cache-assisted-artifactresult-reuse-for-setup-and-repeated-non-final-checks)
- [3. Inject skills as a cached index + on-demand bodies, not a full per-turn block](#3-inject-skills-as-a-cached-index--on-demand-bodies-not-a-full-per-turn-block)

### Later MVP / nice-to-have backlog

- [13. Skill-guided self-directed host work (A/B/C experiment)](#13-skill-guided-self-directed-host-work-abc-experiment)
- [10. Projects: persistent client-side custom skills and tools](#10-projects-persistent-client-side-custom-skills-and-tools)
- [4. (Optional) Switch the output format to provider-native tool calls](#4-optional-switch-the-output-format-to-provider-native-tool-calls)

---

## Priority Order

Use this order for implementation planning. The detailed entries below are now
laid out in the same sequence.

1. **Foundation / P0** - persistent session, model memory, host-vs-board action
   boundary, final board decision shape, tool schemas, iteration estimate shape,
   early-exit verdicts, and print-instrumentation prompt incentive.
2. **Bounded execution / Wave 1 base** - close timeout audit gaps, make timeouts
   structured outcomes, add model-proposed timeout budgets, add `wait`, and keep
   all bounds inside brain/server hard caps.
3. **Action capability / Wave 1 branch work** - add batches, UART write, and
   client actions / model-authored scripts.
4. **Visibility / Wave 2 branch work** - add live provider/brain progress,
   developer inspector logs, stream checkpoints for UART/build/client-action
   flows, skill index/on-demand skill bodies, cache-assisted setup/result
   reuse, and canonical memory index/selective recall as additive parallel
   branches.
5. **Prototype proof gate** - add scoped green approval with manual or narrow
   flipped-value tests and the proof escalation ladder.
6. **Later MVP polish** - projects, broad skill-guided host experiments,
   provider-native tool calls, and wider product/UI polish.

---

## Cross-cutting: provider-session integration for Codex and Claude

All session work below assumes the entry #2 direction: one persistent provider
conversation with the deterministic brain underneath. The brain remains the
governed executor and safety gate; provider sessions are the model reasoning
context.

Current implemented bridge:

- **Codex subscription / Codex CLI.** The current adapter shells out once per
  brain turn and resumes one persisted Codex thread with
  `codex exec resume <thread_id>`. This is a real logical conversation resume,
  but it is still a subprocess-per-turn wrapper with CLI output parsing.
- **Claude subscription / Claude Code CLI.** The current adapter shells out once
  per brain turn and resumes one persisted Claude session with
  `claude --print --resume <session_id>`. This is a real logical conversation
  resume, but it is still a subprocess-per-turn wrapper with CLI output parsing.
- **OpenAI API credits.** The OpenAI adapter uses Responses
  `previous_response_id` as the server-side conversation handle.
- **Anthropic API credits.** The Anthropic Messages surface is stateless at the
  message API layer, so the adapter owns and resends compact conversation
  history.

Final integration target:

- Keep one repo-owned `DecisionProvider` / provider-session protocol.
- Move Codex from `codex exec resume` to Codex SDK or app-server style
  thread/turn APIs.
- Move Claude from `claude --print --resume` to the Claude Agent SDK session
  interface.
- Treat CLI resume as the compatibility fallback, not the final high-reliability
  product surface.
- If a mode promises one continuous provider session, a failed resume must fail
  closed or ask the operator. Automatic fresh-session fallback is allowed only in
  an explicitly labeled recovery mode.

Session resume policy to implement:

- Real-session providers are OpenAI Responses with `previous_response_id`,
  Codex CLI with `thread_id`, and Claude CLI with `session_id`.
- Strict continuity should be the deployment default. Once a handle exists inside
  a top-level prompt, a later turn must resume that handle or stop.
- Interactive recovery may offer exactly three choices: retry resume, start a
  new provider session from saved local memory, or abort.
- Headless recovery must fail closed by default. Starting a new provider session
  should require an explicit future flag/config and must be labeled in events and
  artifacts.
- Anthropic API is excluded from real-session strictness because its continuity
  is brain-owned memory, not provider-owned session resume.

Two caveats specific to this product, true for every entry:

- **Provider caching is TTL-bound and our turns are slow.** API "KV cache" is
  provider prompt caching, which expires (Anthropic ~5 min default, 1 hr opt-in;
  OpenAI prefix cache minutes). Hardware ops are long —
  `FLASH_TIMEOUT_SECONDS=240`, `RECOVER_TIMEOUT_SECONDS=180`
  ([loop.py:49](../src/pyocd_debug_mcp/brain/loop.py#L49)) — so a flash/recover
  turn can outlast the cache window and evict the prefix. Prefer Anthropic's
  1-hour cache and do not assume cache hits across slow turns.
- **Raw API re-owns compaction.** The CLIs give auto-compaction for free; over
  the raw API there is none. If a session outgrows the context window, summarizing
  is our responsibility. The brain-owned action ledger (entry #2) is the
  deterministic spine that must survive whatever compaction we add.

In the default session design (entries #1-#3 plus the host/board split in #9/#11/#12)
the model keeps returning a `TurnDecision` JSON object only for the turn-closing
governed/terminal decision; history accumulates as ordinary conversation turns
(the model's JSON reply becomes the assistant message, the next governed result is
appended as the user message), and tool descriptions + skills live as **cached
text in the session prefix**. The append-only shape is what preserves the KV cache
— a JSON object in an assistant message caches exactly as well as a native tool
call would. Switching the output format to the provider's native `tools` parameter
and `tool_result` blocks is a **separate, optional** change (entry #4), not required
for memory or caching.

---

## Accepted design stance: direct hardware access is not sandboxed

**Decision (accepted):** on the CLI providers the model already runs with full
code execution — codex is invoked `-a never -s danger-full-access`
([provider_codex_cli.py:87](../src/pyocd_debug_mcp/brain/provider_codex_cli.py#L87))
— so it can in principle bypass the brain and drive the probe / serial port
directly (enumerate USB, run `pyocd`, open the serial port), around the flash gate
and convergence watcher. We **accept** this rather than sandboxing the provider.

**Scope of the softness — read this carefully.** The *only* thing being conceded
is that **direct hardware access is not physically prevented**. This is **not** a
statement that the brain's gates are weak or advisory. On the normal path — the
model acting *through* the brain, which is what the providers do today — the flash
gate, the convergence watcher, and the entry #8 verdict gates are **fully
enforced**: the brain refuses the operation unless its checks pass. The single
ceiling we accept is that no brain-side gate is absolute against a model that
*deliberately goes around the brain entirely* via direct hardware access; we take
that ceiling instead of sandboxing, and we still design every gate as a real,
enforced check on the cooperative path. In particular, this stance does **not**
soften the early-termination gates in entry #8 — those stay hard.

**Mitigation (incentive-level, proportionate to the cooperative-model threat).**
We do not sandbox the bypass; we make it never the rational move, with defense in
depth:

- **Capability gap.** The MCP server brings SWD, drivers preloaded at setup,
  resolved board facts (target/baud/addresses), session state, and helpers like
  connect-by-board-id. The raw sandbox has none of it — going direct is strictly
  more work and less capable. The sanctioned path is the path of least resistance.
- **Structural friction.** The brain holds the *only* live probe handle; the
  provider subprocess is spawned separately in a temp dir with no session handle
  and no probe reference. To bypass, the model would have to independently
  enumerate USB and stand up `pyocd`/serial from scratch.
- **Per-prompt reminder (legibility).** A standing instruction to prefer the MCP
  server's tools and not drive the probe directly — because the server has the
  drivers, board config, and SWD the model needs. This also covers entry #9
  session tools (use gated reads, never touch hardware directly).
- **Gate -> hand-off, not brute-force.** A standing instruction that a *genuine
  dead-end* — persistent gating with no legitimate path, a convergence block, or
  any situation whose only "way forward" is going around the brain — means
  **terminate and hand off to the human** (route through entry #8
  `needs_intervention` / `infeasible`), as a first-priority response rather than
  brute-forcing or bypassing. This removes the motivation in the one window where
  it was highest (a stuck/blocked model). **Distinguish** this from a *corrective
  refusal* (e.g. "use `board_id`", "reuse the session", "recover forbidden") — those
  are guidance to apply and continue, not cues to terminate.
- **Deterministic backstop.** The convergence watcher still force-terminates the
  loop on a hard block, so brute-force continuation inside the brain is bounded
  regardless of whether the model honors the instructions above.

Residual (accepted): a model that deliberately ignores all of the above and goes
around the brain is not physically stopped. That is the ceiling we took instead of
sandboxing; for a cooperative SOTA model the mitigation above is treated as
sufficient.

---

## 2. Separate deterministic safety-state from model reasoning-context (give the brain real memory)

### Problem / current behavior

The original problem was that the decision model had almost no memory: the loop
rebuilt the prompt from scratch and every provider behaved like a cold
`text -> TurnDecision JSON` function.

Current status: Branch A has partially closed that gap. Provider session state,
Codex thread resume, Claude session resume, OpenAI Responses continuation,
canonical local memory, prompt delta rendering, and coarse provider progress are
implemented. The remaining problem is no longer "no session continuity"; it is
that the subscription-backed providers still depend on subprocess-per-turn CLI
wrappers, permissive fresh-session recovery, and CLI output parsing. Those are
good enough for the current prototype bridge, but they are not the final robust
provider integration.

Consequence: the deterministic convergence watcher
(`_check_local_convergence`, [loop.py:835](../src/pyocd_debug_mcp/brain/loop.py#L835))
can detect and *stop* thrashing, but nothing in the prompt **points the model in
a non-thrashing direction**. Anti-thrash is a floor, not guidance. The model
re-derives its understanding from a thin snapshot every turn and can re-walk
investigation paths it already exhausted.

### What the change is

Stop conflating two different concerns the current design merges into
`BrainState`:

1. **Deterministic safety-state** — "have I thrashed, am I allowed to flash, is
   it verified green?" Stays in Python, hash-based, gates the loop. `BrainState`
   is correct for this; keep it.
2. **Model reasoning-context** — "what is my evolving theory, what have I ruled
   out, what did each experiment return?" This should be real, accumulating
   model memory, not a per-turn scalar snapshot.

For the goal of **one most-accurate / most-efficient agent** (explicitly not
optimizing for cross-provider comparison or provider symmetry), the recommended
shape is to **give the model a persistent, append-only session while keeping the
turnkey brain exactly where it is** — as the executor and gate for governed
boundaries. Note this is one axis only (session/memory) and is independent of the
output-format axis: **we keep the `TurnDecision` JSON return for the final
governed/terminal decision of a turn.** (Switching to native tool calls is a
separate, optional change — entry #4.) Keeping JSON here must not be read as
keeping old per-local-action mediation; entries #9, #11, and #12 supersede that
for model-native host work.

- Run the model in **one logical persistent session** instead of re-prompting it
  cold each turn. The model works freely inside that session and returns a
  `TurnDecision` JSON object only to close the turn with a governed board/build/
  firmware-deliverable action or a terminal/communication decision. History
  accumulates naturally as conversation turns. Current CLI resume adapters
  satisfy this as a prototype bridge. The final implementation should use
  provider SDK/session APIs for Codex and Claude so the brain gets structured
  turn lifecycle, streaming events, and explicit session management without
  scraping subprocess output.
- Treat each `TurnDecision` as a **memory checkpoint**, not as a record of every
  private or model-native substep. For short board loops this can be compact.
  For long self-directed runs, the model must make the checkpoint more detailed:
  summarize the user prompt being handled, the current plan, important host-side
  work already done inside the provider session, decisions made, hypotheses
  opened/closed, files read or changed, and why the next governed action or
  terminal answer is correct. This keeps the brain-owned memory useful without
  forcing the model to emit JSON for every local thought or host operation.
- Keep the deterministic brain **unchanged underneath**: it still parses the
  returned governed decision, dispatches the selected server-native/client-action/
  terminal action, applies the existing checks (argument normalization, refusals,
  flash gate, convergence blocks in `_execute_server_tool`
  [loop.py:513](../src/pyocd_debug_mcp/brain/loop.py#L513)), runs the tool against
  the MCP server when needed, observes workspace/tool-store diffs at the boundary,
  and appends the result into the session as the next user turn.
- `BrainState` still exists, derived from observed tool results exactly as now,
  and still drives convergence refusals — but it is the safety spine, no longer
  the model's memory.

This is both more accurate (full reasoning continuity, including the model's own
prior `TurnDecision` reasoning fields, which now persist in the conversation) and
more efficient (append-only conversation is KV-cache friendly: stable cached
prefix + only the newest tool-result computed). The KV-cache win comes from the
append-only **session**, not from any change to the output format — a JSON object
in an assistant message caches as well as a native tool call. The current
re-serialization approach is actively cache-hostile because the mutating
"Current state" block invalidates the cache mid-prompt every turn.

### Reject: per-turn prompt re-serialization as the primary path (keep only for CI)

The alternative of "feed more state into the rebuilt prompt each turn" was
considered and rejected as the *primary* design: it grows the prompt and busts
the KV cache every turn (mutating middle tokens). Retain that deterministic,
replayable mode **only** as a `--deterministic` benchmark/CI mode so regressions
in the agent itself stay reproducible. Two modes over one executor, not two
products.

### Sub-change: brain-owned, outcome-bearing action ledger injected every turn

Whichever execution mode is active, maintain and inject a compact, deterministic,
**ground-truth** action ledger (derived from observed results, like `BrainState`
— never the model's self-report). It is cheap (one line per action) and directly
supplies direction, not just thrash-detection.

Crucially it must carry the **result value of each action, not a binary ok/fail**
— the value is the signal (`read_core_register pc=0x08000af2`, `read_memory
0x20000000 -> 0xDEADBEEF`, `read_serial SILENT excerpt="\x00"`, `run_build FAILED
exit=1 "undefined reference to uart_init"`). A checkmark throws away exactly the
datum that points the model somewhere.

Tier by recency, but **every tier keeps the actual result**, never collapsing to
a checkmark:

- **Tier 1 (last ~3-5 turns):** full result text verbatim.
- **Tier 2 (older):** one-line distilled result — extracted salient
  value/verdict plus a short capped excerpt (<=120 chars). Keeps the fact,
  drops the bulk.
- **Tier 3 (only if still overflowing):** collapse oldest to
  `action -> outcome + key value`, still never a bare ok/fail.

Distillation should be a small per-tool "salient result extractor" with a generic
truncation fallback. Half of it already exists: `ToolTextResult` parses
`session_id` / `probe_uid` / `refusal_code` / `blocked_code`
([mcp_client.py:66](../src/pyocd_debug_mcp/brain/mcp_client.py#L66)) and the loop
already extracts `pc` and the UART excerpt
([loop.py:449](../src/pyocd_debug_mcp/brain/loop.py#L449),
[loop.py:457](../src/pyocd_debug_mcp/brain/loop.py#L457)).

In the native-session design this ledger has a second, sharper justification: it
is the **compaction-proof anchor**. Provider auto-compaction is lossy and may
summarize away a precise old observation; a brain-owned ledger re-pinned every
turn survives compaction and preserves the "what have I tried and what happened"
spine regardless of how the harness summarizes.

### Sub-change: memory index + selective recall

Do not make the model reread full memory every turn. Keep the full canonical
memory durable, but render a short **memory index / table of contents** into the
prompt:

- stable memory id or turn range;
- one-line model-generated title/description;
- brain-derived action kind, result status, and key observed values;
- tags such as `flash`, `uart`, `build`, `code-edit`, `refusal`, `blocked`,
  `hypothesis-supported`, or `hypothesis-refuted`;
- changed files and artifact refs when relevant;
- pinned/critical flags for facts that must stay visible.

For the last N boundary decisions, keep one row per move. For older history,
compact to range rows with model-generated descriptions anchored to structured
facts. Then inject the working snapshot, pinned critical facts, the short memory
index, and selected full memory entries only when the current task, render
profile, or model request needs them.

This is a stronger attention mechanism, not a second source of truth. The
model-generated title helps orientation, but the brain anchors each row to exact
tool results, artifacts, changed files, and verification facts. The goal is to
reduce compute while giving the model an efficient way to know what happened and
what detailed memory can be recalled.

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/provider_types.py` + provider adapters** - keep
   the session-capable provider contract, but split adapter implementations by
   transport quality:
   - current bridge: CLI resume wrappers for `codex-cli` and `claude-cli`;
   - final Codex adapter: SDK/app-server thread and turn APIs;
   - final Claude adapter: Claude Agent SDK session API;
   - API adapters: OpenAI Responses handle and Anthropic client-owned history.
   No native tool-calling is required for this change; that remains entry #4.
2. **`src/pyocd_debug_mcp/brain/loop.py`** — split `run_turnkey` into:
   - a persistent-session executor that lets the provider perform model-native
     host work inside its own session, appends each governed result as the next
     user turn, parses the returned turn-closing `TurnDecision`, and dispatches
     only the governed action through the brain gate; and
   - the existing re-serializing loop, retained as the deterministic mode.
   Add `_format_action_ledger(state)` and inject it in both modes.
3. **`src/pyocd_debug_mcp/brain/state.py`** — extend the records behind
   `actions_taken` / `mcp_tools_used` to store the distilled result per action
   (today they store only names), so the ledger renderer has ground-truth result
   data to draw from.
4. **`src/pyocd_debug_mcp/brain/provider_types.py` / canonical memory module** -
   add memory-index rows, pinned-fact rows, and selective-recall renderers over
   the canonical memory store.
5. **`src/pyocd_debug_mcp/brain/mcp_client.py`** — extend the per-tool salient
   result extraction beyond the current fields.

### Wave placement

Implement the memory index/selective-recall layer in **Wave 2 Branch H**, in
parallel with Branch D (progress/inspector), Branch E (stream checkpoints),
Branch F (scoped green approval), and Branch G (static context/cache reuse).
Branch H should consume Branch A provider-memory/session state and Branch C
event shapes, but it should not own provider session semantics, progress UI,
cache keys, skill body loading, or final integration prompt rewrites.

### What it is supposed to do

- Give the model accumulating, ground-truth context so prompts are more accurate
  and the agent is *directed* away from exhausted paths, not merely halted when
  it loops.
- Preserve KV cache / compute efficiency via an append-only native session
  instead of an ever-growing, cache-busting rebuilt prompt.
- Keep all deterministic safety guarantees by moving the guardrails *below* the
  native loop as the tool executor/gate, unchanged in spirit.

### Constraints / watch-outs

- **Reproducibility.** Native sessions + sampling make runs non-deterministic.
  Retain a deterministic mode for the frozen 12-case benchmark / CI so agent
  regressions remain catchable; do not delete the replayable path.
- **Lossy compaction at long horizons.** Relying on provider auto-compaction
  trades no-memory for lossy-memory and couples correctness to an opaque,
  versioned heuristic. Moot at the current ~12-18 turn horizon; the brain-owned
  ledger mitigates it when it matters.
- **Caching is provider-managed.** Free on native-session / server-side
  conversation paths; on a hand-rolled raw message array (e.g. Anthropic
  Messages) it requires explicit `cache_control` breakpoints.
- **Whitelist coupling.** The native loop must still expose only
  `AllowedServerToolName` ([actions.py:10](../src/pyocd_debug_mcp/brain/actions.py#L10)),
  not the server's full tool set. Pairs naturally with change #1 (forward tool
  descriptions for exactly those tools).
- **Doc-sync + verify.** Update the README turnkey section / R12 turnkey spec in
  the same unit of work, and re-run the suite before claiming the new path works.

### Native-session (API) note

On API credits the session is the conversation itself, so the reasoning-context
(prior tool calls, results, the model's own `tool_use` turns) is carried by the
provider — OpenAI server-side via `previous_response_id`, Anthropic by our resent
message array. The brain-owned action ledger is still injected, but its job
shifts: it is the **deterministic, compaction-proof** restatement of ground-truth
results that must survive any summarization we add when a raw-API session
outgrows the window. Mind the TTL-vs-slow-hardware caveat from the cross-cutting
section: a flash/recover turn can evict the cached prefix, so do not assume the
prior turns are cache-cheap to re-read after a long hardware op.

### Status

Partially implemented by Branch A. The current branch has provider session
state, CLI resume handles, OpenAI Responses continuation, local memory,
prompt-delta rendering, tool schema forwarding, and provider progress events.

Still open for the final integration:

- replace Codex subprocess resume with Codex SDK/app-server thread APIs;
- replace Claude subprocess resume with Claude Agent SDK sessions;
- harden `anthropic-api` memory from compact per-turn notes into a real
  outcome-bearing firmware-debugging ledger before claiming Claude API parity;
- implement strict one-provider-session mode so resume failure stops the run or
  asks the operator instead of silently starting a fresh provider session;
- retain the CLI resume adapters as compatibility fallback and CI-friendly
  smoke paths.

Claude API-specific work:

- The current `anthropic-api` path is stateless at the provider API layer. It
  gets continuity only from the brain-rendered memory block.
- Upgrade that memory block to preserve exact tool arguments, observed values,
  build artifacts, source edits, failed hypotheses, ruled-out paths, refusal and
  block reasons, and acceptance constraints.
- Add tests that force compaction and prove old critical facts survive into a
  later Anthropic API turn.
- Run the Anthropic API repair slice after ledger hardening; do not infer
  performance from Claude Code CLI session-resume proof.

---

## 11. Two tool classes: model-native (free) vs server-native (governed)

### Problem / current behavior

Today every model action is a `TurnDecision` the brain mediates — even inert local
work. Design 2 (entry #9) showed authoring is inert and should not be gated, and the
two-class discussion generalizes it: the brain should govern only what touches the
board or feeds its safety/convergence/bounding, and leave inert local work free.
Without a stated rule, each op is classified ad hoc.

### What the change is

Define two classes of capability in the client:

- **Model-native tools** — purely local, inert, reversible, and irrelevant to
  hardware/convergence/bounding: read/list/write files, shell utilities
  (`cd`/`ls`/`mkdir`/`grep`/`cat`), authoring + running *pure-local* scripts, local
  computation over already-gathered data. The model runs these **freely in its
  sandbox**, in its native flow, **not** as decisions — the brain does not gate them.
- **Server-native tools** — reach hardware or governed effects: `flash`,
  `read_memory`/`read_serial`, `write_memory`, `recover`, UART write; running a
  hardware-touching script; and brain-tracked ops (`run_build`, firmware-*source*
  edits) that feed convergence or are the repair deliverable. Invoked **only via a
  governed decision** the brain dispatches, gates, and bounds.

### The dividing line — governance, not destructiveness

The brain governs an op iff **any** of these holds:

1. it touches hardware / external side effects;
2. it feeds convergence / state tracking;
3. it needs hang / timeout bounding.

Otherwise it is model-native. This is why a *harmless* hardware read
(`read_memory`) is **server-native** (it needs timeouts + convergence), and a
`run_build` that touches no hardware is still **governed** (it feeds the
repeated-build-failure block and is the deliverable). The axis is "must the brain
govern it," not "is it dangerous."

### Transitive script classification + how it is enforced

A script's class = whether it reaches a server-native tool:

- calls a server-native tool (transitively) -> **the script is server-native** ->
  runs only via a governed `run_script` decision;
- calls none -> **model-native** -> runs free.

This is **enforced by capability scoping, not model self-labeling:** the gated
server-tool client API is **in scope only during a `run_script` execution.** A free
native script has no hardware client handle, so it *structurally cannot* reach a
server-native tool through the sanctioned channel. If a script wants hardware it
must go through `run_script` (the only context where the brain injects the API).
(A script reaching *raw* hardware around the API is the accepted soft-guardrails
bypass — possible, disincentivized, not the sanctioned path.)

### Scope: the brain governs the board, not the host

"Model-native runs free" means the brain does not gate it — **host-machine safety
(filesystem, disk, network) is the provider sandbox's job, not the brain's.** Under
the [accepted stance](#accepted-design-stance-direct-hardware-access-is-not-sandboxed)
the model already has full host access (`danger-full-access`), so this grants
nothing new. Read "safe" as "the brain protects the *board*"; the *host* is the
sandbox's concern (which we have accepted is soft).

### Gate vs observe

Model-native does **not** mean invisible. The brain still **observes** effects —
snapshots the tool store / diffs the workspace at the decision boundary — so the
free phase is auditable. The distinction is **gate vs. observe**, not see vs. not.

### Reclassifies the current action set

- `read_file` -> **model-native** (was a brain action).
- `server_tool`, `run_script`, `run_build`, firmware-source `replace_file` ->
  **server-native / governed.**

### Where it belongs

1. **`actions.py`** — the action union is the set of **server-native** actions only
   (`server_tool`, `run_script`, `run_build`, firmware-edit, plus the terminal /
   communication decisions of entry #12). Model-native ops are not actions.
2. **brain runner** — provide the gated client API only inside `run_script`; run
   free scripts in the sandbox without it.
3. **audit** — snapshot the tool store / diff the workspace at the decision boundary.

### Constraints / watch-outs

- **Enforcement is capability-scoping** (API only in `run_script`), not model
  self-labeling.
- **Board vs host scope** — host safety is the sandbox's (accepted soft), not the
  brain's.
- **Observe, don't gate** model-native ops, for audit.
- **Doc-sync + verify.** This reclassifies the action set; update the README / R12
  spec and verify a model-native script runs free while a hardware-touching one is
  forced through `run_script`.

### Status

Proposal only. Not yet specced, not yet implemented. Unifies the principle behind
Design 2 (entry #9), batches (entry #5), and the turn structure (entry #12).

---

## 12. The model only outputs a decision when it needs the board

### Problem / current behavior

Today every turn forces a `TurnDecision` through the brain even when the model is
doing inert local work — throttling it and conflating "thinking / local work" with
"interacting with the board." Entry #11 splits the tool classes; this entry states
the **output contract** that falls out of that split.

### What the change is

Invert the default: by default the model has **free reign on the user's computer**
(model-native tools, entry #11), and it produces a **decision to the brain only to
interact with the board — or to terminate / communicate.** The final output of a
turn is *always* a decision, but the decision may be:

- **a board interaction** — a server-native action (`run_script` / `flash` /
  `read_memory` / …); or
- **"do nothing with the board"** — because the model did not need it: a terminal /
  communication decision — `respond_to_user(text)`, `needs_clarification`
  (-> entry #8 `needs_intervention`), `infeasible` (-> entry #8), or `done` / no-op.

So: the model can do whatever it wants locally, *regardless*; the **decision** is
specifically the **board-interaction gate**. "I need the board -> here is my
governed decision." "I don't -> here is my text / terminal output."

### The decision union (governed only)

- **server-native actions** (board interaction), and
- **terminal / communication**: `respond_to_user(text)`, `needs_clarification`,
  `infeasible`, `done` / no-op.

Local model-native work is **not** in this union — it is not a decision at all.

### Why

- Removes the throttle: inert local work no longer round-trips the brain.
- The brain's loop governs exactly the thing that matters — board interaction —
  and nothing else.
- Cleanly supports **text-only turns** (answer / ask / explain) with no hardware
  action, which the current "every turn is a hardware-shaped decision" cannot.

### Where it belongs

1. **`actions.py`** — the decision union adds `respond_to_user(text)` and
   `done` / no-op alongside the server-native actions and the entry #8 verdicts.
2. **`loop.py`** — a turn = free model-native phase, then **exactly one** governed
   decision that closes it; `done` / `respond_to_user` end the turn without any
   board interaction.

### What it is supposed to do

- Make "needs the board" the *only* reason to produce a governed decision, while the
  model works freely otherwise — the principled turn loop behind entries #9 and #11.

### Constraints / watch-outs

- **A decision still closes every turn** (even `done` / `respond_to_user`), so the
  brain always has a defined turn boundary for `BrainState` / convergence.
- **The board is always gated**, regardless of how free the local phase is — board
  interaction happens *only* through the decision.
- **One governed decision per turn** is sufficient because a single `run_script`
  can orchestrate many gated calls (entries #5/#9); "one decision" bounds the
  governance points, not the work.
- **Doc-sync + verify.** Update the README / R12 spec; verify a turn that needs no
  board ends in a `done` / text decision without any gated call.

### Status

Proposal only. Not yet specced, not yet implemented. The output-contract companion
to entry #11's tool-class split.

---

## 1. Forward real MCP tool descriptions/schemas into the turnkey brain prompt

### Problem / current behavior

The turnkey brain does **not** tell the decision model (codex-cli, claude-cli,
or the native API providers) what each `server_tool` actually does. The model
is used as a pure text -> `TurnDecision` JSON function and never speaks MCP, so
the only things it learns about the tools are:

- a bare list of tool **names** in the turn prompt's "Available action kinds"
  section (`_build_turn_prompt`, [src/pyocd_debug_mcp/brain/loop.py:238](../src/pyocd_debug_mcp/brain/loop.py#L238)),
- a freeform `arguments` bag in the decision schema
  (`turn_decision_output_schema`, [src/pyocd_debug_mcp/brain/actions.py:141](../src/pyocd_debug_mcp/brain/actions.py#L141)) —
  `{"type": "object", "additionalProperties": true}`, i.e. no per-tool argument
  shape at all,
- a handful of hand-written usage rules in the static instructions
  (`_build_instructions`, [src/pyocd_debug_mcp/brain/loop.py:176](../src/pyocd_debug_mcp/brain/loop.py#L176)) —
  e.g. "connect with board_id", "read_memory takes a hex string", "no cortex_m".

Meanwhile the MCP server already carries rich, canonical tool docstrings
(the README calls these the source of truth that "the MCP client reads over the
protocol"). The turnkey client **discards** them: `StdioToolClient.list_tool_names`
([src/pyocd_debug_mcp/brain/mcp_client.py:160](../src/pyocd_debug_mcp/brain/mcp_client.py#L160))
keeps only `tool.name` and throws away `tool.description` and `tool.inputSchema`.

Net effect: a BYO-agent (the user's own Claude Code) connecting directly gets
the full tool descriptions and input schemas, but our own turnkey brain flies on
tool names + a few rules + the model's pretrained priors. The documentation
exists and is free to forward; we just don't.

### What the change is

Surface the server-provided tool metadata (description + input schema) that we
already receive over MCP, and inject a rendered version of it into the turn
prompt so the decision model sees, per allowed tool:

- the human-readable description (the existing docstring),
- the argument names, types, and which are required.

This keeps the docstring as the single source of truth (no sidecar tool docs —
consistent with the `superpowers-tool-docs` rule) and simply stops dropping it
on the floor in the turnkey path.

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/mcp_client.py`** — stop discarding metadata.
   - `ToolClientProtocol` / `StdioToolClient`: add a method (e.g.
     `list_tools()` returning name + description + inputSchema) alongside the
     existing `list_tool_names`, or widen the existing call to return full
     `types.Tool` objects.
   - `LocalMCPClient.start` ([mcp_client.py:208](../src/pyocd_debug_mcp/brain/mcp_client.py#L208))
     currently stores only `available_tools: tuple[str, ...]`. Add a parallel
     `tool_specs` mapping `name -> (description, input_schema)` populated at
     startup.

2. **`src/pyocd_debug_mcp/brain/loop.py`** — render and inject.
   - Add a helper (e.g. `_format_tool_catalog(client, allowed_names)`) that
     renders only the **whitelisted** tools (`AllowedServerToolName`,
     [actions.py:10](../src/pyocd_debug_mcp/brain/actions.py#L10)) — do not leak
     the tools the brain deliberately does not expose (step, write_memory,
     breakpoints, etc.).
   - Splice that catalog into `_build_turn_prompt`
     ([loop.py:196](../src/pyocd_debug_mcp/brain/loop.py#L196)), replacing or
     augmenting the bare-name "Available action kinds" list. The client is
     created inside `run_turnkey` ([loop.py:998](../src/pyocd_debug_mcp/brain/loop.py#L998)),
     so the catalog must be fetched after `client.start()` and threaded into the
     per-turn prompt build.

3. **(Optional, stronger) `src/pyocd_debug_mcp/brain/actions.py`** — the
   `server_tool.arguments` schema stays freeform, but the rendered catalog gives
   the model the per-tool argument shape in prose. Tightening the actual schema
   per tool is a larger, separate change and should stay out of scope here.

### What it is supposed to do

- Give the turnkey model the same tool understanding a direct MCP client already
  has, sourced from the one canonical place (the docstrings), so behavior does
  not depend on model priors about what `unlock_recover` or `read_core_register`
  mean.
- Reduce malformed/!misused tool calls and the wasted retry turns they cost
  (today the only correction signal is the next-turn `last_result` text).
- Stay within the brain's deliberately narrow surface: only whitelisted tools
  are described, so this does not widen what the model can do — only what it
  understands about what it is already allowed to do.

### Constraints / watch-outs

- **Prompt size.** In the current bridge / deterministic mode, full docstrings +
  schemas for 12 tools add tokens to every rebuilt turn prompt. In the persistent
  session path they should live in the cached prefix. Render compactly either way;
  consider one-line descriptions + a terse arg list rather than full schema JSON.
- **Whitelist coupling.** The catalog must be filtered by `AllowedServerToolName`,
  not by the server's full tool set, or it will advertise tools the loop will
  reject. This is the same *curated-allowlist* discipline as entry #3's
  `load_skill` scoping (the model may only name items from a brain-curated set,
  never something outside it) and entry #5's per-step batch gating — one principle,
  applied to tools, skills, and batch steps alike.
- **Doc-sync.** This changes how the turnkey brain is documented to the model.
  Per `superpowers-doc-sync`, the canonical doc (README turnkey section and/or
  the R12 turnkey spec) must note that the turnkey brain now forwards server
  tool descriptions, in the same unit of work.
- **Verification.** Re-run the frozen 12-case turnkey suite after the change to
  confirm no regression in the `codex-cli` green path before claiming it works;
  this is a code change, so the "verify, don't claim" rule applies.

### Native-session (API) note

In the default persistent session (entry #2, `TurnDecision` JSON return), deliver
this metadata as a **cached text block in the session prefix** — rendered once
from each whitelisted tool's MCP `description` + `inputSchema` and never rebuilt,
so it stays in the cached prefix for the whole run at zero per-turn cost. The
re-serialization / CLI one-shot mode includes the same rendered catalog in its
rebuilt prompt. Only if entry #4 (native tool-use) is adopted does this metadata
move into the provider's native `tools` parameter (OpenAI Responses `tools`,
Anthropic Messages `tools`) instead of prose.

### Status

Proposal only. Not yet specced, not yet implemented.

---

## 18. Replace fixed max-iters defaults with model-estimated iteration budgets

### Problem / current behavior

The turnkey loop currently uses a fixed CLI default for `max_iters`: `12` for
freeform `run` and `18` for `benchmark`, with `--max-iters` as the only override.
That is a blunt control for an agentic loop. Some tasks need only a few turns; real
bug-fix/debug tasks may need many board observations, build/flash cycles, targeted
instrumentation, verification retries, and rejected finalization attempts. A fixed
default either cuts off legitimate work or wastes time by giving simple tasks too
large a budget.

### What the change is

Ask the model to produce a structured iteration-budget estimate from the task
prompt before or at the start of the run. The brain then adds a fixed safety margin
and clamps the result to a hard product/user cap.

The model estimates; the brain owns authority:

```text
effective_max_iters = min(
    brain_hard_cap,
    model_total_estimated_iters + brain_fixed_safety_margin
)
```

The hard cap stays deterministic and brain-owned. The model can request enough
space to finish the task, but it cannot grant itself unbounded turns.

### User permission for long estimated runs

Add a separate brain-owned **unattended-duration cap**. If the model's estimated
runtime for the automated run exceeds that cap, the brain must not start the full
run silently. It should return a `needs_intervention` / permission request that
tells the user:

- the estimated duration;
- the main contributors to that estimate, such as builds, flashes, UART reads,
  recover attempts, long client actions, or verification retries;
- what will run unattended if approved;
- the hard maximum the brain will enforce even after approval.

This cap is not the same as `max_iters`. It is a wall-clock/operator-permission
guardrail. A task might have few iterations but still include a long flash/recover
or build sequence, and a task might have many short iterations that stay below the
wall-clock permission threshold.

After approval, the brain may run with the estimated budget plus its normal fixed
safety margin, still clamped by hard product/user caps. If the estimate later grows
past the approved duration class, the brain must ask again rather than silently
expanding the unattended run.

### Required model estimate shape

The prompt/schema should require a broken-down estimate, not just one loose number:

```json
{
  "iteration_budget_estimate": {
    "board_tool_turns": 4,
    "code_edit_turns": 3,
    "build_and_flash_turns": 3,
    "debug_observation_turns": 4,
    "verification_turns": 2,
    "failed_finalization_retries": 2,
    "total_estimated_turns": 18,
    "reason": "Need connect, observe failure, instrument, patch, rebuild, flash, verify."
  }
}
```

Use "failed finalization retries" rather than "false terminations": the model should
not be encouraged to terminate falsely, but the brain should budget for rejected
finalize attempts where scoped success gates, verification, or deterministic policy
correctly force the loop to continue.

### Brain validation and enforcement

- Validate every field as a non-negative integer.
- Validate that `total_estimated_turns` roughly matches the category sum; if it does
  not, use the safer larger validated value or reject the budget estimate.
- Clamp each category to a category-specific maximum so one field cannot dominate
  the budget.
- Add a fixed brain-owned safety margin for normal uncertainty.
- Clamp the final value to a hard cap from product policy / CLI / future config.
- Estimate wall-clock duration from the model's breakdown plus known per-action
  budgets, compare it to the unattended-duration cap, and force `needs_intervention`
  before starting if it is too long for unapproved automation.
- Keep existing early exits, convergence checks, timeout handling, and scoped success
  gates active; the iteration budget is only an outer allowance, not permission to
  thrash.
- Allow extensions only through a separate, explicit mechanism that requires
  evidence of progress, such as new observations, a passing build after a failed
  build, a narrowed hypothesis, or a successful verification step.

### Where it belongs

1. **Prompt/schema** - add the `iteration_budget_estimate` object to the model's
   required planning output.
2. **`src/pyocd_debug_mcp/brain/actions.py` / decision schema** - represent the
   estimate as structured data with validation.
3. **`src/pyocd_debug_mcp/brain/loop.py`** - compute `effective_max_iters` from the
   model estimate plus the fixed margin and hard cap, then use that value for the
   loop limit. Also compute the estimated wall-clock duration and block with
   `needs_intervention` when it exceeds the unattended-duration cap.
4. **`src/pyocd_debug_mcp/brain/cli.py`** - keep `--max-iters` as an absolute cap or
   rename it to an explicit hard-cap flag; do not treat the CLI default as the
   normal task budget. Add a separate CLI/config value for the unattended-duration
   cap.
5. **Action ledger / run artifacts** - record the model estimate, the brain margin,
   the hard cap, the unattended-duration cap, any user approval, and the final
   effective budget so budget decisions are auditable.

### What it is supposed to do

- Let simple tasks finish with small budgets.
- Let complex debugging tasks run to completion when they have a plausible plan.
- Keep the loop agentic without making `max_iters` an arbitrary magic number.
- Preserve safety: the model proposes, the brain validates/adds slack/clamps, and
  deterministic early exits still stop the run when the task is done or not making
  progress.

### Constraints / watch-outs

- **The model never owns the hard cap.** It only estimates.
- **Do not reward inflated estimates.** Category caps and audit logging should make
  obviously padded budgets visible and clampable.
- **Early exits still win.** A large budget must not prevent immediate completion,
  refusal, infeasible/needs-intervention verdicts, or convergence blocking.
- **Long unattended runs need permission.** The model cannot silently start an
  automated run whose estimated wall-clock duration exceeds the brain-owned
  unattended-duration cap.
- **Progress is required for extensions.** More iterations after budget exhaustion
  should require evidence, not a generic "need more time."

### Status

Proposal only. Not yet specced, not yet implemented. Replaces the fixed default
`max_iters` behavior with a model-estimated, brain-clamped iteration budget.

---

## 17. Prompt the model to instrument unexpected failures with targeted prints

### Problem / current behavior

When the model sees a bug, timeout, unexpected UART output, wrong register value, or
surprising test result, it can jump straight to a speculative fix. That is risky in
firmware because the failure might be earlier in the path than the symptom: init may
not run, a branch may never execute, a peripheral may fail before the printed output,
or the board may be stuck before the expected observation point. Without targeted
instrumentation, the loop can waste turns trying code changes without knowing where
execution diverged.

### What the change is

In the base prototype, inject a prompt rule on every turn that **incentivizes the
model to add targeted print/log instrumentation when debugging bugs or unexpected
outputs**. Once skills are active, move this rule into the bug-fix skill so it is
loaded when the task is actually a debugging task rather than carried forever in the
base prompt.

The rule should tell the model:

- If an observation is unexpected, first ask "where did execution diverge?" before
  guessing at a fix.
- Prefer a few targeted prints/logs at decision points, function entry/exit,
  parsed values, error branches, and hardware-state checkpoints over broad noisy
  logging.
- Use instrumentation to distinguish "code path never ran" from "code path ran but
  produced the wrong value" from "hardware/tool observation failed."
- Rebuild/flash/read after instrumentation, then remove or gate the instrumentation
  once the failure location is known.
- If adding prints could perturb timing, memory, UART bandwidth, or firmware size,
  say so and choose the least invasive observable signal available.

### Where it belongs

1. **Base prototype prompt injection** - add the instruction to the always-injected
   prompt while the product does not yet have task-specific bug-fix skills.
2. **Future bug-fix skill** - once skills are active, move the instruction into the
   bug-fix skill and inject it only for bug-fix / unexpected-output tasks.
3. **Action ledger / final summary** - when the model adds instrumentation, record
   what it was trying to distinguish and whether it removed/gated the instrumentation
   after diagnosis.

### What it is supposed to do

- Make the model localize failures instead of guessing fixes from symptoms.
- Shorten debugging loops by proving which code path, value, or hardware state is
  wrong.
- Pair cleanly with the timeout work: after a short read/timeout or unexpected
  output, the model should instrument to diagnose the failure point rather than
  repeatedly waiting longer or trying unrelated changes.

### Constraints / watch-outs

- **Instrumentation is diagnostic, not the fix.** Do not leave debug prints in final
  firmware unless the task explicitly wants persistent logging.
- **Firmware perturbation matters.** UART prints can change timing, code size, power,
  and scheduling. Use minimal, scoped prints or alternative observable signals when
  timing-sensitive behavior is suspected.
- **Do not spam output.** The model should add just enough instrumentation to split
  the hypothesis space.
- **Respect safety gates.** Instrumentation still goes through the same edit, build,
  flash, and hardware-operation guardrails as any other code change.

### Status

Proposal only. Not yet specced, not yet implemented. Prototype behavior belongs in
the base prompt first; mature behavior belongs in the bug-fix skill once the skill
layer is active.

---

## 8. Gated early-exit verdicts: infeasible, needs_intervention, ambiguous

### Problem / current behavior

The terminal vocabulary is `fixed`, `healthy_confirmed`, `diagnosed_only`,
`unresolved`, `blocked` ([actions.py:25](../src/pyocd_debug_mcp/brain/actions.py#L25)).
There is no clean way for the model to say either of two distinct things:

1. **"This task cannot be completed in the current physical setup"** — the board
   is miswired, a component is missing, a rail is dead. Today this only
   approximates as `diagnosed_only` / `unresolved` + `classification=physical_fault`,
   which does not signal *human bench action required* and is muddled with "the
   agent gave up."
2. **"I could continue, but a human should decide first"** — e.g. the next test
   would take 14 hours, or the next action is destructive/irreversible, or the
   task is genuinely ambiguous. Today the model either barrels on, grinds to
   `max_iters`, or is brain-`blocked` — none of which is "pause and ask the
   human."

Both differ from `blocked`, which is **brain-imposed** (convergence / refusal /
max-iters), not a model-reached judgment.

### What the change is

Add three model-judged terminal verdicts to `FinalStatus`. Crucially they are **not
hard-verified by the brain** — the brain cannot pre-enumerate every way a task can be
infeasible or need intervention ("board dead", "X disconnected", and the infinite
tail), so there is no fixed brain test for each case. Instead the gate is **forced
externalization**: the model must turn its claim into a **runnable artifact the brain
executes and judges**, not a bare assertion.

- **`infeasible`** — a *verdict*: task not achievable in the current physical
  configuration; human hardware action required. Typically
  `classification=physical_fault`.
- **`needs_intervention`** — a *pause-and-ask*: the model wants a human decision
  (permission or redirection) before proceeding — the next op is too long/costly,
  destructive/irreversible, or any other reason it judges warrants a human. Not a
  failure.
- **`ambiguous`** (= entry #12 `needs_clarification`) — the task itself is
  underspecified; the model needs the human to disambiguate.

**`infeasible` and `needs_intervention` are model-made-script tested, with
auditable, explicit reasoning; `ambiguous` is a soft specificity floor** (no test is
possible). All three are members of entry #12's terminal/communication decision union
(alongside the ungated `respond_to_user` and `done`); a turn ending in one does not
touch the board.

### The gate: forced externalization, not brain verification

The brain is **not** a hard guardrail here — it does not (cannot) ship a check for
every mode. What it does is **force the model to prove its claim with a runnable
test, then run that test itself** (challenge-response, structured like the green-check
gate [loop.py:888](../src/pyocd_debug_mcp/brain/loop.py#L888)):

1. **Model declares** the verdict.
2. **Brain challenges:** "prove it — write ground-truth test script(s) (using the
   gated server-tool hardware API, entry #9) into the tool folder and give me their
   names." (Plus, for `needs_intervention`, the specific human question / estimate.)
3. **Model authors** the scripts (native, entry #9) and supplies the names.
4. **Brain runs them** against real ground truth and **judges the observations** —
   the model never sets the flag, and the brain reads the *facts the scripts
   produced* (applying its own sanity checks), not the model's pass/fail label.
5. **Terminate, or bounce:** if the observations support the verdict, terminate with
   an actionable human message; if the model's *own* test shows otherwise, the brain
   returns "you said `infeasible` but your ground-truth test said otherwise" and the
   loop continues.

**Why this works (the real guardrail):** it is easy to hallucinate the *word*
"infeasible"; it is very hard to hallucinate an entire **test that passes while the
task is actually feasible** — because the test runs against the real board, and a
working board is a hostile witness to a false test. The brain isn't verifying the
claim's *logic*; it is **raising the cost of a false verdict from ~0 (a bare
assertion) to high (a rigged-but-passing hardware test)**, in proportion to how much
real ground truth backs the claim.

### Strength is fabrication difficulty (the measurability ladder)

| Verdict | What the script runs against | How hard to fake a passing test |
| --- | --- | --- |
| `infeasible` | real hardware (reads/probes) | Very hard — a working board contradicts a false test; you'd have to actively rig the logic |
| `needs_intervention` | estimates / computed numbers | Easier — no ground truth to contradict a self-serving estimate |
| `ambiguous` | nothing (no test possible) | n/a — only a specificity floor |

- **`infeasible` — strongest.** The script *measures* real hardware (a register read
  succeeds or it doesn't), so the self-falsification catch fully bites. Example
  reasoning it externalizes: silicon responds over SWD (alive) **and** the targeted
  I/O is dead across retries **and** the software path was exercised and ruled out.
- **`needs_intervention` — a soft guardrail.** Its reasons are open-ended and mostly
  *estimated*, not measurable — e.g. a script that *"sums the per-unit costs, compares
  to the brain-owned cap, returns yes if over"* (the long-duration case is **only one
  example**; the model writes whatever script fits the reason, since the brain can't
  enumerate them all). The brain can't verify the estimate against ground truth, so
  the script's value is **forcing explicit, auditable reasoning** — a strong deterrent
  against hallucinated BS, but *not* verification. The self-falsification catch only
  partially bites (the brain can sanity-check the formula/inputs for obvious nonsense,
  not measure them).
- **`ambiguous` — a soft specificity floor.** No ground truth exists to test ("is the
  task unclear?" can't be probed), so the gate is only: the model must supply a
  **concrete, specific** question, not a vague "I'm unsure." No script, no
  self-falsification catch — specificity plus cooperative trust.

### The thin brain-owned hard floor

A small core *is* deterministic and brain-owned (not the verdict logic): a **minimum
real-attempts floor**, the **brain-owned cap** for any duration comparison, and
recognizing **known-destructive op classes**. So the full picture is **a thin hard
floor + a forced-externalization layer whose deterrent scales with ground-truth
backing.**

### What happens after (resume semantics)

All three terminate the loop and surface an **actionable** message to the human in
the final result (`root_cause` / `summary`): for `infeasible`, what is physically
wrong and what bench action is needed; for `needs_intervention`, the exact
decision/permission required and the cost that triggered it; for `ambiguous`, the
specific question the human must answer.

True pause/resume (continue the *same* session after the human answers) is a
larger feature — the current human interaction is bookended (task in, result
out). For v1 these statuses terminate and the human re-invokes with permission /
redirection (updated task input or a flag). Note in-session resume as a future
enhancement.

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/actions.py`** — extend `FinalStatus` with
   `infeasible`, `needs_intervention`, and `ambiguous`. `FinalizeAction` carries
   the **names of the ground-truth test scripts** (for `infeasible` /
   `needs_intervention`), plus the human question / estimate
   (`needs_intervention`) or the specific concrete question (`ambiguous`).
2. **`src/pyocd_debug_mcp/brain/loop.py`** — the **challenge-response gate** in
   `_final_result_from_action` ([loop.py:883](../src/pyocd_debug_mcp/brain/loop.py#L883)):
   refuse the finalize (a `TurnkeyRefusal`) unless the model has supplied
   test scripts; **run them** (via the entry #9 / entry #11 `run_script` path) and
   **judge the observations** (not the model's label); for `ambiguous`, require a
   concrete specific question; enforce the **thin hard floor** (min real attempts,
   the brain-owned cap, known-destructive op classes). On a self-contradicting
   test, bounce back "your own test says otherwise."
3. **Test mechanism = entry #9** — the scripts are model-authored, gated
   server-tool scripts run by the brain (entry #11 governs that hardware-touching
   scripts go through `run_script`). No separate predicate engine.
4. **`src/pyocd_debug_mcp/brain/cli.py`** — print the human-facing ask / verdict
   clearly in the final result.

### What it is supposed to do

- Let the model end a run with a precise, actionable verdict — "the bench is
  miswired, fix X", "approve/redirect before I spend 14 hours", or "which bank?" —
  instead of silently grinding or returning a vague `unresolved`.
- Keep the verdicts honest by **forced externalization**: the model must back a
  script-testable claim with a runnable test the brain runs and judges, so a false
  verdict is expensive to fabricate (not merely asserted) — strongest for
  `infeasible`, a soft guardrail for `needs_intervention`, a specificity floor for
  `ambiguous`.

### Constraints / watch-outs

- **Not a hard guardrail — a fabrication-difficulty deterrent.** The brain does not
  (cannot) pre-enumerate the modes; it **runs the model's own test and judges the
  observations.** The guardrail is that a *passing* test which contradicts reality is
  hard to fabricate — not that the brain verifies the claim's logic.
- **Strength scales with ground truth.** Strong for `infeasible` (measured
  hardware), a soft guardrail for `needs_intervention` (estimated — forced explicit
  reasoning, not verification), specificity-floor-only for `ambiguous`.
- **Self-falsification catch only fully bites on measurable claims** (`infeasible`).
  For estimates the brain can only sanity-check the formula/inputs, not measure them.
- **Judge the facts, not the label.** The brain reads what the scripts actually
  observed and applies its own sanity checks; it does not trust the model's pass/fail
  interpretation.
- **Thin hard floor is real** — min real attempts, the brain-owned cap, known
  destructive op classes are deterministic and enforced.
- **Distinct from `blocked`** (brain-imposed convergence/refusal/max-iters).
  **`needs_intervention` cost case depends on entry #7** for the budget/cap.
- **Soft-guardrails ceiling.** A *deliberately* rigged test that looks like it probes
  hardware but short-circuits is the accepted residual (we defend against a sloppy
  cooperative model, not a malicious one); the catch handles the sloppy case.
- **Doc-sync + verify.** Update the README / R12 turnkey spec, and exercise each
  verdict — including a refused/contradicted attempt ("your own test says
  otherwise") — before claiming it works.

### Status

Proposal only. Not yet specced, not yet implemented.

---

## 14. Bound every blocking call (timeout and hang audit)

### Problem / current behavior

Current repo note (2026-06): this entry contains the original audit findings, but
the code has since landed several first-pass bounds: shared timeout constants in
`src/pyocd_debug_mcp/timeouts.py`, `subprocess.run(timeout=...)` for the known
external-command sites, provider timeouts, MCP startup timeout, UART
`write_timeout`, and pyOCD session-option ceilings. Those are necessary but not
the full guarantee. The remaining target is to make timeout values dynamic and
synced between the brain and server, and to make uncancellable hardware calls
enforceable through worker isolation / cleanup so a client timeout cannot leave
the server wedged behind `_lock`.

The findings below should therefore be read as historical plus remaining-work
items: some now have constant bounds, but they still need dynamic config, alignment
with client read-timeouts, or killable enforcement where the underlying call cannot
be cancelled in-process.

### Required timeout configuration model

Timeouts must be configurable at runtime without letting the model or client disable
the safety bound.

- **Brain owns the source config.** Add a brain-side timeout config, populated from
  invocation / CLI / env / defaults, and use it for per-tool MCP read-timeouts,
  provider calls, per-batch budgets, and local build/workspace timeouts where
  applicable.
- **Server owns a clamped mirror.** Add a server-side `_timeouts` config seeded from
  `timeouts.py` defaults. Server-side blocking calls read from that mirror instead
  of directly reading constants.
- **Sync through MCP.** Add a `set_timeouts(updates)` MCP tool. The brain calls it at
  session start and whenever its timeout config changes. No server restart is
  required.
- **Partial in-memory updates, not file rewrites.** `set_timeouts` accepts only the
  timeout keys the client wants to change, merges them into the server's current
  in-memory `_timeouts` config, clamps the changed values, and returns the effective
  config. It must not rewrite `timeouts.py` or any config file. Persistent timeout
  profiles, if needed later, should be a separate feature/tool from runtime
  retuning.
- **Model-proposed scoped budgets.** The decision prompt/schema must ask the model
  to propose timeout hints for each significant action or batch, not only an action
  list. The brain treats those hints as scoped to the current action/batch unless an
  explicit persistent runtime-config change is requested. For server-backed calls,
  the brain either passes the hint as a per-call timeout where the API supports it
  or pushes a partial `set_timeouts` update immediately before the call and restores
  the prior effective config after the scoped operation if needed.
- **Use a separate config lock.** `set_timeouts` must not take the hardware `_lock`,
  or a stuck hardware op would prevent changing the bounds that should apply to the
  next op.
- **Subsequent-op semantics.** A running operation reads its timeout when it starts.
  Runtime changes apply to later operations, not in-flight ones.
- **Clamp twice.** The brain clamps model/user-supplied values to brain caps, then
  the server clamps again to server-owned min/max constants. The hard min/max clamps
  remain server-owned constants; they are the integrity boundary.
- **Keep server bounds below client bounds.** Server-side effective timeouts must be
  smaller than the corresponding MCP read-timeout so the server returns a clean
  error before the client gives up and leaves a late response / lock cascade.

The brain has per-tool *client-side* give-up timeouts (entry #7 context), but several
blocking calls on the **server** and across the **brain↔server seam** have **no
timeout at all.** When one of those outlasts the client's give-up timeout, the client
reports an error to the model while the **server stays stuck holding `_lock`** — so
the next call queues behind it and *also* times out, cascading into an effectively
wedged server while the model waits for responses that never come. An audit of the
server/seam code found the specific gaps below.

### Findings — unbounded blocking calls (each needs a timeout)

1. **UART port `open()`** — `serial.Serial(device, baudrate, timeout=...)`
   ([uart_pyserial.py:17](../src/pyocd_debug_mcp/adapters/uart_pyserial.py#L17)). The
   `timeout` is the **read** timeout; the **open is unbounded**, and no `write_timeout`
   is set. A contended/vanished USB-CDC port hangs the open, exceeding `read_seconds`
   *and* the client's `read_seconds + 12` ceiling — the exact server-outlasts-client
   case. **(The originally-requested fix.)**
2. **External-CLI probe discovery** — `_run_cmd`: `subprocess.run(cmd, capture_output=
   True, text=True)` with **no `timeout=`**, in both
   [server.py:213](../src/pyocd_debug_mcp/server.py#L213) and
   [swd_pyocd.py:37](../src/pyocd_debug_mcp/adapters/swd_pyocd.py#L37). `nrfjprog` /
   `STM32_Programmer_CLI` / `pyocd list` can hang during connect/discovery and block
   the server indefinitely.
3. **pyOCD session/probe open** — `session.open()`
   ([swd_pyocd.py:200,209](../src/pyocd_debug_mcp/adapters/swd_pyocd.py#L200)): no
   timeout; USB enumeration / probe attach can hang (and pyOCD open is not cleanly
   cancellable — see constraints).
4. **Model provider call** — `subprocess.run(...)` with no `timeout=` in
   [provider_codex_cli.py:36](../src/pyocd_debug_mcp/brain/provider_codex_cli.py#L36)
   and [provider_claude_cli.py:33](../src/pyocd_debug_mcp/brain/provider_claude_cli.py#L33).
   A wedged model hangs the whole run. (Also called out in entry #7.)
5. **Brain↔server MCP startup** — `session.initialize()` / `list_tools()` in the
   client's `__aenter__` / `start` ([mcp_client.py](../src/pyocd_debug_mcp/brain/mcp_client.py))
   have no timeout; if the server hangs on startup the brain blocks *before* any
   per-tool timeout can apply.

### Findings — hardware ops with no configured op-level ceiling

SWD ops (`read_memory`, …) rely on pyOCD/USB transfer timeouts that **are not
configured in this repo**; `flash` (`FileProgrammer.program`) and `recover`
(`FlashEraser` mass-erase) have **no pyOCD session-option timeout** set. Set pyOCD's
built-in timeouts (flash especially) where available — the self-cleaning in-library
bound from the entry #7 layering.

Current repo note (2026-06): the code now sets pyOCD session-option ceilings for
step/reset/recover/flash through `build_session_options`, but those values are
created when the pyOCD `Session` is opened. Treat them as configurable per-connect,
not live-mutable on an already-open session.

### Dynamic vs. hardcoded audit

**Should become dynamic/synced through the brain/server timeout config:**

- Brain MCP read-timeouts in `brain/loop.py`: default, connect, flash, recover, and
  read-serial derived bounds.
- Server external-command bounds in `server.py` and `adapters/swd_pyocd.py`.
- UART read/write/open budgets at the server boundary, with open enforced through a
  worker/open strategy.
- Future killable-worker wall-clock budgets and cleanup/restart budgets.
- Provider request timeout and per-batch wall-clock budget on the brain side
  (client-owned; no server sync needed except for matching tool budgets).

**Configurable, but not live-syncable:**

- pyOCD session-option timeouts (`PYOCD_*` values): the brain can push them before
  connect and the server can apply them when creating the next `Session`, but an
  already-open session should be treated as using the old values.
- MCP startup timeout: can come from client config before launch, but cannot be
  updated through MCP because MCP is not running yet.
- Local build/workspace timeouts: client-side / local-runner config, not server
  state.

**Should stay hardcoded or server-owned:**

- Server clamp min/max values for timeout updates. These are the safety boundary and
  must not be client-controlled.
- Internal poll cadences and retry backoffs that are deliberately small and bounded.
  These are small loop pacing values used *inside* an already-bounded operation, not
  the top-level operation budget. Examples: `uart_capture` briefly opens/polls in
  0.05-0.2s chunks while the caller's `read_seconds` deadline remains the real
  bound; `reopen_delay` is the short pause before retrying a transient UART reopen;
  Stage 0 sleeps are short retry pacing; pack-index retry backoff is the short pause
  between bounded HTTP attempts. They should stay hardcoded by choice because
  exposing them would create tuning surface without changing the safety guarantee.
- Third-party/native lower-layer timeouts not exposed by pyOCD/libusb/vendor DLLs.
  The repo can wrap them with a worker budget, but it cannot make those internal
  transfer timeouts dynamically client-settable.
- Setup/provisioning script defaults (`host_bootstrap`, `stage0_check`,
  `pack_index_repair`, `pack_provision`, `zephyr_build`, harness defaults) when those
  tools run standalone without the brain/server pair. They may have CLI/env options,
  but they are outside runtime MCP syncing.

### Findings — error handling (graceful vs. masking)

Positives to keep (already aligned):

- `workspace` build subprocess has `timeout=` + `TimeoutExpired -> WorkspaceError`
  ([workspace.py:178](../src/pyocd_debug_mcp/brain/workspace.py#L178)).
- SWD ops map backend exceptions to **typed** domain errors
  (`_typed_backend_error -> LockedTargetError / TargetConnectionError`) and propagate
  cleanly ([swd_pyocd.py:85](../src/pyocd_debug_mcp/adapters/swd_pyocd.py#L85)).
- The J-Link retry-without-uid is a **single bounded** retry, not a loop
  ([swd_pyocd.py:203](../src/pyocd_debug_mcp/adapters/swd_pyocd.py#L203)); the
  `zephyr_build` subprocess has a timeout.

Watch (potential masking):

- `flash` **swallows `TransferError` on the final reset** when `halt_after_reset` is
  false ([swd_pyocd.py:335](../src/pyocd_debug_mcp/adapters/swd_pyocd.py#L335)) —
  intentional (`pyocd load` tolerates a transient drop), but keep the swallow narrow
  so it can't mask a real flash failure.

### The systemic misalignment to fix

Client per-call timeouts assume the server completes within budget — but the
unbounded server sections above can **outlast** the client timeout. The fix is to
**bound every blocking call so the server can never outlast its client budget**, and
**align** them (each server op's effective bound < its client timeout) so a timeout
is always a **clean error**, never a silent wedge or a cascade.

### What to do

1. **Bound the UART open** — wrap `serial.Serial(...)` open in a timeout (thread+join
   or platform open-with-timeout / fail-fast) and set `write_timeout`; cap so
   server-side `read_serial` can never exceed `read_seconds`.
2. **Bound `_run_cmd`** — add `timeout=` to the external-CLI `subprocess.run` (both
   sites) and map `TimeoutExpired` to a typed error.
3. **Bound `session.open()`** — a connect-timeout via a worker (kill, since pyOCD open
   isn't cancellable — ties to the killable-worker idea); at minimum a thread-join
   that reports a clean error even if the worker lingers.
4. **Bound the provider call** — add `timeout=` to the codex/claude `subprocess.run`
   (entry #7).
5. **Bound MCP startup** — timeout `initialize()` / `list_tools()` so a hung server
   start fails fast.
6. **Set pyOCD session-option timeouts** (flash etc.) where available.
7. **Align server bound < client timeout** everywhere, and make a timeout a
   **structured outcome** (entry #7), not a raw exception, so no layer waits on a
   response that will never come.
8. **Keep the flash final-reset swallow narrow.**

### Constraints / watch-outs

- **Opens aren't cleanly cancellable** (pyOCD/serial): a thread-join timeout reports a
  clean error but the worker may linger — true cancellation needs process isolation
  (the killable-worker; ties to entry #7 and the timeout-cleanup discussion).
- **Align bounds** (server < client) to prevent orphan/cascade and the wedged-`_lock`
  state.
- **Don't over-tighten** — legitimately slow flash / slow enumeration must still
  succeed; set generous-but-finite ceilings.
- **Doc-sync + verify on real hardware**, including a forced open-hang (unplug the
  device mid-op) to confirm the bound fires and the session recovers.

### Status

Partially implemented. The first-pass constant bounds have landed for subprocesses,
providers, MCP startup, UART write timeout, and pyOCD session options. Still open:
dynamic/synced timeout config, structured timeout outcomes, true UART/pyOCD open
enforceability, killable hardware worker cleanup, and forced-hang hardware proof.

---

## 15. Full timeout and hang audit (whole repo)

### Problem / current behavior

Entries #7 (the enforcement-layer design) and #14 (a *partial* server/seam
blocking-call audit) cover the spots found so far. But a complete, **repo-wide**
audit has not been done — hang / stuck-wait / stuck-cycle risks may exist anywhere
in the system (brain, server, services, adapters, providers, CLI, build, packs, the
MCP seam). This entry tracks doing that full audit properly.

### What the change is (the request, verbatim)

> Do a full timeout error audit:
>
> read my current codebase, and find out what's going on between the server and
> client. im concerned about hang or timeout errors; audit the codebase and
> determine where errors or null responses will genuinely cause hangs or unwanted
> waiting and cycling, and which calls are supposed to be like that vs which calls
> actually cause unwanted behavior? Also, as I am concerned about hang or timeout
> errors, I'd like a detailed audit on the ENTIRE system and ENTIRE code repository.
> I want proper error handling on any call that can hang, so it doesn't stay waiting
> for something that will never come, or stays listening after an error is thrown.
> Basically, I NEVER want a situation where the client or model stays listening and
> is stuck forever - the client should ALWAYS return to the user after some period of
> time or throw some output at the user, and there should NEVER be long processes
> that persist even when nothing needs its output anymore, and there should NEVER be
> long waiting or stuck cycling when things should have already terminated because an
> error was thrown.

### Acceptance criteria (hard requirements)

- **No infinite listening.** The client/model must **never** stay stuck forever.
- **Always return.** The client must **always** return to the user within a bounded
  time, or surface an output/error to the user.
- **No orphaned work.** No long-running process persists once nothing needs its
  output (no leaked workers/threads/subprocesses after the waiter gave up).
- **No post-error cycling.** No long wait or stuck cycle continues after an error has
  already determined the operation should terminate.
- **Proper error handling on every call that can hang**, so it never waits on a
  response that will never come, nor keeps listening after an error is thrown.
- **Classify, don't blanket-fix.** For each blocking/cycling call, decide whether the
  wait/cycle is **intended** (bounded, expected — e.g. the `read_serial` deadline
  loop) or **unwanted** (unbounded / hang). Don't "fix" intentional bounded waits.

### Scope — the ENTIRE repo, not just the hot path

- **Brain:** `loop`, `mcp_client`, the providers, `workspace`, `benchmark`, `cli`,
  `session_runtime`, `convergence_watcher`.
- **Server:** `server.py`, services (`target_control`, `uart_capture`, `symbols`,
  `session_runtime`), adapters (`swd_pyocd`, `uart_pyserial`).
- **Support / setup:** `probe_inventory`, `pack_provision`, `pack_index_repair`,
  `zephyr_build`, `reference_artifacts`, `serial_resolver`, `local_env`,
  `host_bootstrap`, `stage0_check`.
- **The seam:** stdio transport, MCP `initialize` / `list_tools` / `call_tool`, and
  **request/response matching** — what happens to a *late/unmatched* response after a
  client read-timeout (does it leave a dangling waiter, or get dropped cleanly?).

### Method — enumerate and classify every blocking point

For every blocking primitive in the repo — `subprocess.run`/`Popen`, USB/serial
`open`+`read`+`write`, pyOCD ops, MCP requests, `time.sleep`, `while`/retry loops,
lock acquisitions, queue/stream waits — record a matrix:

`call -> layer -> bounded? -> on-timeout behavior -> on-error behavior -> intended vs
unwanted -> fix`.

Then feed the **unwanted** rows into concrete fixes (entries #7 and #14 are the
landing zone for those).

### Relationship to #7 and #14

This is the **comprehensive** pass. Entry #14 is its partial down-payment (the
already-found server/seam gaps); entry #7 is the design the fixes should follow
(per-layer bounds primary, killable worker for enforceability, timeout as a
structured outcome). #15 should find everything #14 missed and route it into #7/#14.

### Current repo-wide audit result

The current repository is no longer at "no timeout coverage": most obvious
`subprocess.run` and provider hangs are bounded, and the MCP startup path is bounded.
The remaining risks fall into three buckets:

- **Uncancellable hardware/native calls:** pyserial `open()`, pyOCD `session.open()`,
  and native USB/vendor-library work can still block in-process. A dynamic timeout
  value helps choose the budget, but the enforcement mechanism is worker isolation
  and kill/restart.
- **Client/server alignment:** several values are now centralized constants, but not
  yet one live config. Until the brain pushes a synced config and the server derives
  its mirror from it, drift between server budgets and client read-timeouts remains
  possible.
- **Standalone tools:** setup, pack, Zephyr, and harness scripts are bounded or have
  CLI-level knobs, but they are outside the runtime MCP sync model by design.

### Constraints / watch-outs

- **Intended vs unwanted** — preserve deliberate bounded waits (e.g. the
  `read_serial` `read_seconds` loop, the single bounded J-Link retry); only fix
  unbounded ones.
- **Late/unmatched MCP responses** — after a client timeout, ensure the eventual
  server response is dropped cleanly and never leaves a dangling waiter.
- **Cross-platform** — USB/serial open and timeout behavior differ on Windows vs.
  macOS; verify both.
- **Audit + fix + verify** — produce the matrix, land the fixes via #7/#14, and
  verify on real hardware including **forced-hang** scenarios (unplug mid-op, wedged
  probe, killed external CLI, hung provider).

### Status

Initial repo-wide audit pass recorded here and in entry #14. Remaining verification
requires forced-hang hardware scenarios on Windows and macOS plus the implementation
work routed through entries #7 and #14.

---

## 7. Timeouts, hang-prevention, and a wait action

### Problem / current behavior

Per-tool timeouts already exist for hardware calls: `_tool_timeout_seconds`
([loop.py:501](../src/pyocd_debug_mcp/brain/loop.py#L501)) sets `connect=60s`,
`flash=240s`, `recover=180s`, `read_serial=window+12s`, default `30s`, threaded
into the MCP client's `read_timeout_seconds`
([mcp_client.py:165](../src/pyocd_debug_mcp/brain/mcp_client.py#L165)). So a
single hung hardware call will not hang the brain forever. But three gaps remain,
and they get worse once entry #5 lets the model send a sequence per turn:

1. **Timeouts are not a first-class outcome.** A timed-out call surfaces as a
   caught exception turned into an error string
   ([loop.py:1064](../src/pyocd_debug_mcp/brain/loop.py#L1064)), not a clean
   "null / timed-out" result. In a batch, early-abort (entry #5) needs a
   deterministic timeout outcome to key on.
2. **No per-batch wall-clock budget.** Even if every step is within its own
   timeout, a long sequence can run a long time. A batch needs an overall cap.
3. **The provider call itself can hang with no timeout.** Both CLI providers call
   `subprocess.run(...)` with **no `timeout=`**
   ([provider_codex_cli.py:36](../src/pyocd_debug_mcp/brain/provider_codex_cli.py#L36),
   [provider_claude_cli.py:33](../src/pyocd_debug_mcp/brain/provider_claude_cli.py#L33)).
   A wedged `codex`/`claude` process hangs the entire run indefinitely — the worst
   hang case, currently unguarded.

There is also **no `wait` action**: the model cannot insert a deliberate delay
(e.g. write input, wait for the device to react, then read), which is exactly the
sequencing entries #5 and #6 invite.

### What the change is

Make every unit of execution bounded, treat exceeding the bound as a clean failed
result, and give the model an explicit, bounded delay primitive.

- **Timeout = deterministic failed/null outcome.** Convert a per-call timeout into
  a structured result (e.g. a `timeout` code on the tool result, analogous to
  `refusal_code` / `blocked_code` in `ToolTextResult`
  [mcp_client.py:66](../src/pyocd_debug_mcp/brain/mcp_client.py#L66)) so the loop,
  the action ledger (entry #2), and batch early-abort (entry #5) all see "this
  step timed out" rather than a raw exception string.
- **Per-batch wall-clock budget.** Add an overall budget for a batch turn; if the
  cumulative time crosses it, abort the remaining steps and report which step the
  budget ran out on.
- **Provider-call timeout.** Add `timeout=` to the provider subprocess calls (and
  an equivalent guard on the API providers), so a stuck model call fails the turn
  cleanly instead of hanging the run.
- **`wait` action.** Add a `WaitAction` (`{"kind": "wait", "seconds": <float>}`)
  to `ActionUnion` ([actions.py:74](../src/pyocd_debug_mcp/brain/actions.py#L74)),
  executed by the brain as a bounded sleep. Most useful as a batch step
  (write -> wait -> read), but valid standalone. It is brain-local (not an MCP
  tool), like `run_build`; it is not a reason to re-gate inert host reads.

### Making timeouts *enforceable* — the layer model (corrected priority)

The client read-timeout above only makes the **brain** give up; it does **not** stop
the **server**, which keeps running the op holding the global `_lock`, so the next
call queues behind it and the server wedges (the cascade documented in entry #14).
Making a timeout *enforceable* — actually ending the work and freeing the probe —
needs the right layering, and the priority is **not** what an earlier draft assumed
(pyOCD options primary, worker as last resort). The entry #14 audit shows the real
hang sites are spread across pyserial `open()`, external-CLI subprocess, connect, the
provider, and MCP startup — **mostly not pyOCD-option-coverable, all non-cancellable,
all `_lock`-holding.** So the corrected layering, strongest-effort first:

1. **Per-layer bounds on every blocking call (entry #14) — the primary fix, do
   first.** Open-timeout, `subprocess timeout=`, connect-timeout, MCP-init timeout.
   Cheap, low-risk, and it covers the layers that actually hang. *This* is the main
   defense — not pyOCD options.
2. **Killable hardware worker — the enforceability mechanism (structural).** Because
   the dangerous ops are non-cancellable *and* hold `_lock`, a timeout is only
   *truly* enforceable if the server can **kill and restart the worker that owns the
   probe.** Double duty: it makes timeouts enforceable for the uncancellable cases,
   *and* it dissolves the lock-wedge cascade (kill -> OS releases the probe ->
   reconnect/reset/recover -> server stays alive). Promoted from "last-resort
   backstop" to **the thing that makes the guarantee real.** (True cancellation of a
   pyOCD call is not possible — blocking, non-cancellable USB calls — so kill +
   re-init is the only enforceable stop.)
3. **pyOCD session-option timeouts — a graceful optimization, not primary.** Let
   `flash`/connect fail cleanly in-library where pyOCD supports it, so the common
   slow-flash case need not trigger a worker-kill. Useful, but covers only a slice
   (flash) and even that can wedge if its status-polling reads stall.
4. **Client read-timeout — the outer backstop**, now backed by a server that can
   actually *act* on a timeout (kill its worker) instead of staying stuck.

Root cause being addressed: **one global `_lock` + inline blocking ops +
non-cancellable calls.** Per-layer bounds patch the symptoms cheaply; the killable
worker fixes the structure. Sequence: (a) per-layer bounds now (entry #14),
(b) pyOCD flash option, (c) worker isolation as the structural endgame.

### Model-specifiable durations (within brain caps)

Timeouts also let the model express intent: how long to listen after an input, or
how long to wait. Let the model pass a per-action duration / timeout override
(e.g. `read_serial` read window, a `wait` duration, an optional per-step timeout),
but **clamp every value to a brain-enforced maximum** so the model can shorten or
modestly extend a bound, never remove it. The cap is deterministic and owned by
the brain, not the model.

### Model-proposed timeout budget per decision

Do not only let the model choose *what action* to run. Prompt it to also choose the
smallest reasonable timeout budget for each significant action or batch, then pass
those proposed budgets into the brain as part of the decision JSON. The default
large timeout is a **maximum safety cap**, not the value the model should casually
spend on every call.

The prompt/schema should require the model to provide timeout hints for slow or
hang-prone work, especially hardware work:

- **Batch budget:** an overall wall-clock budget for the whole action batch.
- **MCP tool call budget:** the per-tool client read-timeout the brain should use
  for each server action, within the brain cap.
- **Server-side hardware budgets:** per-action hints that the brain can sync to the
  server before the call, such as connect/open, external probe command, UART
  read/write/open, flash, recover, and future worker wall-clock budgets.
- **UART observation windows:** short `read_serial` windows when the model is only
  checking for an immediate prompt/error line, longer windows only when it has a
  concrete reason to expect delayed firmware output.
- **External command budgets:** short budgets for quick discovery/probe-list checks,
  longer budgets only for known slow setup or programming operations.

The model should explicitly judge whether an operation needs the full cap. For
example, a quick UART "did the prompt appear?" check should request a short read,
not the default max; a probe-list command should not get a flash-sized budget; and
a suspected missing board should fail quickly enough to diagnose the physical/setup
problem instead of waiting through repeated long defaults. After a short timeout,
the model should diagnose from the timeout result, decide whether the wait was too
short or the operation is actually stuck/misconfigured, and only then try a longer
budget with a stated reason. This prevents the loop from repeatedly trying a
different action and waiting forever again.

These model-proposed values are still only **requests**. The brain clamps them,
records them in the action ledger, and either applies them directly to client-local
timeouts or syncs the relevant server-side values through `set_timeouts` before the
operation. The server clamps again. The model cannot disable a bound, set an
unbounded/infinite value, or enlarge a timeout beyond the product cap.

Provider-call timeouts are the one timing value the same model response cannot set
for itself, because the provider timeout must already be in force while that
response is being generated. Provider timeout can still be configured by the brain
before inference, or proposed for later turns/profiles, but not by the response that
is currently pending.

### Dynamic, synced timeout config (and what cannot be dynamic)

Most timeouts now live as constants in `src/pyocd_debug_mcp/timeouts.py` (plus the
brain's `loop.py` per-tool constants). The target is to make them **dynamic and
synced** — runtime-mutable, with the brain as the single source of truth and the
server mirroring changes, rather than set-once at launch.

**Mechanism:**

- **Server holds a mutable `_timeouts` config** (seeded from `timeouts.py` defaults),
  and every server-side bound reads from it — sitting next to the existing `_lock`
  module global ([server.py:81](../src/pyocd_debug_mcp/server.py#L81)), which already
  proves the server keeps mutable module state.
- **A `set_timeouts(updates)` MCP tool** lets the client update that config at
  runtime — idiomatic MCP (just another tool call over the same stdio link), no
  restart.
- **Partial in-memory updates, not file rewrites.** `set_timeouts` accepts only the
  timeout keys the client wants to change, merges them into the server's current
  in-memory `_timeouts` config, clamps the changed values, and returns the effective
  config. It must not rewrite `timeouts.py` or any config file. Persistent timeout
  profiles, if needed later, should be a separate feature/tool from runtime
  retuning.
- **The brain is the single source** (invocation-derived) and pushes via
  `set_timeouts` at session start and on any change. Client keeps a var, server
  mirrors it.
- **Semantics:** changes apply to *subsequent* ops, not in-flight ones (an op reads
  its bound when it starts); `set_timeouts` uses a **separate lightweight lock** (not
  the hardware `_lock`), so it can retune even while a long op runs.
- **Integrity — the server clamps.** Every update is clamped to server-owned
  min/max, so a timeout can be tuned within a safe window but never set to `0`
  (breaks everything) or huge/∞ (disables the bound). Composes with the
  model-specifiable durations above: model proposes → brain clamps to caps → pushes
  via `set_timeouts` → **server clamps again** (defense in depth).

**Covered (the bulk — flows through `_timeouts` + `set_timeouts`):** the brain
per-tool timeouts (`loop.py`), the MCP read-timeout, the provider request timeout
(`PROVIDER_REQUEST_TIMEOUT_SECONDS`), the external-command timeout
(`DEFAULT_EXTERNAL_COMMAND_TIMEOUT_SECONDS`, both `_run_cmd` sites), the UART read
window, and the future killable-worker / per-batch budgets — all client-owned or
our-server-code.

**Cannot be (fully) dynamic — audit of what stays hardcoded / per-connect:**

1. **pyOCD session-option timeouts** (`flash.timeout.*`, `reset.*`, `cpu.step.*` —
   the `PYOCD_*` consts applied in `build_session_options`,
   [swd_pyocd.py:163](../src/pyocd_debug_mcp/adapters/swd_pyocd.py#L163)). The client
   *can* pass these **at connect**, but pyOCD **bakes them into the `Session` at
   open**, so they are **not live-mutable without a reconnect**. → *configurable
   per-connect, not runtime-syncable.*
2. **Deep pyOCD / libusb USB-transfer timeouts** (the per-transaction bound *below*
   the session-options): third-party, **not exposed** by pyOCD's API; effectively
   fixed in libusb / the probe driver. → *not client-settable at all.*
3. **`MCP_STARTUP_TIMEOUT_SECONDS`** ([mcp_client.py:215](../src/pyocd_debug_mcp/brain/mcp_client.py#L215)):
   it bounds the server *coming up*, so it runs **before the server exists** —
   there is nothing to sync to. → *client-side only; can be a client config, never
   server-synced (chicken-and-egg).*
4. **Setup / operator / pack timeouts** — `SETUP_COMMAND_TIMEOUT_SECONDS` (host
   setup / `uv sync`), `pack_index_repair` httpx timeout + retries + backoff,
   `zephyr_build` subprocess timeouts: these run in **operator/setup/build tools, not
   the live MCP loop**, so they sit outside the client↔server sync — configurable via
   their own CLI args, not `set_timeouts`.
5. **Internal polling cadences** — these are small loop pacing values used *inside*
   an already-bounded operation, not the top-level operation budget. Examples:
   `uart_capture` briefly opens/polls in 0.05-0.2s chunks while the caller's
   `read_seconds` deadline remains the real bound; `reopen_delay` is the short pause
   before retrying a transient UART reopen; Stage 0 sleeps are short retry pacing;
   pack-index retry backoff is the short pause between bounded HTTP attempts. These
   values should stay hardcoded by choice because exposing them would create tuning
   surface without changing the safety guarantee.

So dynamic+synced covers the brain-side and our-server-code bounds (the bulk); the
genuine exclusions are pyOCD session-options (per-connect, baked into the session),
libusb internals (third-party), MCP startup (pre-server), the setup/pack/build tool
timeouts (out of the live loop), and internal cadences (by choice).

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/mcp_client.py`** — represent a timeout as a
   structured result with a `timeout` code rather than only raising.
2. **`src/pyocd_debug_mcp/brain/loop.py`** — treat a timed-out step as a failed
   step (feeds entry #5 early-abort and the entry #2 ledger); add the per-batch
   wall-clock budget; clamp model-supplied durations to caps.
3. **`src/pyocd_debug_mcp/brain/actions.py`** — add `WaitAction` to `ActionUnion`
   and the JSON schema, with a max-seconds bound.
4. **`provider_codex_cli.py` / `provider_claude_cli.py` (+ API providers)** — add
   a hard timeout to the model call so a stuck provider cannot hang the run.
5. **Server side (entry #14 + the layer model above)** — bound every blocking call
   at its own layer (open, `_run_cmd`, `session.open()`, MCP init); run hardware ops
   in a **killable worker** that owns the probe, so a timeout can kill + restart it
   and re-establish the session via the existing connect/recover services; set pyOCD
   session-option timeouts (flash) where available. This is what makes a timeout
   actually end the work and free the probe, not just make the brain give up.

### What it is supposed to do

- Guarantee forward progress: every tool call, batch, and model call is bounded,
  and exceeding a bound is a clean failure the loop can react to — no silent
  hangs, in addition to the existing anti-thrash protection.
- Give the model controlled timing — bounded `wait` and capped durations — so it
  can drive realistic stimulus/observe sequences (entries #5/#6) without being
  able to remove the safety bounds.

### Constraints / watch-outs

- **Caps are brain-owned.** The model may shorten or modestly extend a duration
  within a hard maximum; it can never disable a timeout. Same curated-control
  discipline as the whitelist entries.
- **Distinguish timeout from refusal/block.** A timeout is "no result in time,"
  not a policy refusal; keep the codes separate so convergence accounting and the
  ledger read them correctly.
- **Respect slow hardware.** Hardware ops are legitimately long
  (`flash=240s`, `recover=180s`); per-batch budgets and any new caps must not be
  tighter than the existing per-call timeouts for those operations.
- **Brain timeout ≠ enforcement.** The client read-timeout only stops the *brain*;
  without the server-side per-layer bounds + killable worker (entry #14), the
  *server* still wedges on `_lock`. Per-layer bounds are the cheap primary; the
  killable worker is what makes a timeout actually end the work. pyOCD session-options
  are a graceful optimization, not the primary bound — corrected from an earlier
  draft that had these priorities reversed.
- **Doc-sync + verify.** Update the README / R12 turnkey spec, and exercise a
  timeout path and a `wait` step before claiming it works.

### Status

Proposal only. Not yet specced, not yet implemented.

---

## 5. Model-composed batches: a sequence of tool calls per turn

### Problem / current behavior

A `TurnDecision` carries exactly **one** `action`
([actions.py:85](../src/pyocd_debug_mcp/brain/actions.py#L85)), and a
`server_tool` action calls exactly one tool
([actions.py:40](../src/pyocd_debug_mcp/brain/actions.py#L40)). The loop runs one
tool per turn ([loop.py:1010](../src/pyocd_debug_mcp/brain/loop.py#L1010)). So a
natural operator sequence — flash, read UART for 10s, send input, read UART again
— is four full model round-trips instead of one fluent sequence.

There is already a precedent for one action fanning out into several tool calls,
but the brain owns it: `run_green_check` is a fixed Python macro that chains
flash -> `read_core_register` -> `read_memory` -> `read_serial`
([loop.py:712](../src/pyocd_debug_mcp/brain/loop.py#L712)). The model cannot
compose its own sequence.

### What the change is

Let the model emit an ordered **batch** of actions in a single turn, executed in
order by the brain, so it can drive a full sequence "as if it were manning the MCP
server itself."

This is a current-bridge convenience for governed actions, not a replacement for
the free-host-work design. Once entries #9, #11, and #12 land, batches must not be
used to keep inert local work (`read_file`, directory listing, scratch computation,
pure-local scripts) inside the brain decision loop. Use batches only for governed
server-native/client-action/terminal steps that genuinely need the brain boundary.

Lower-risk schema: add a `BatchAction` to `ActionUnion`
([actions.py:74](../src/pyocd_debug_mcp/brain/actions.py#L74)):

```text
{ "kind": "batch", "steps": [ <action>, <action>, ... ] }
```

where each step is an existing governed single action (`server_tool`, `run_script`,
`run_build`, firmware-deliverable edits, terminal/finalize actions, ...). The
current bridge may still carry legacy local actions for compatibility, but the
north star is that model-native host work is not batched through the brain.
Single-action turns keep working unchanged; batching is opt-in. (Alternative: make
the top-level `action` a list and rename to `actions` — cleaner semantically but a
breaking change to every existing decision.)

### Execution semantics (the important part)

The batch is **not** a guardrail bypass — it is sequential single-tool execution
with the same gates, just without a model round-trip between steps:

- **Per-step gating.** Every step runs through the same brain dispatch/gate it
  would use alone: server tools through `_execute_server_tool`
  ([loop.py:513](../src/pyocd_debug_mcp/brain/loop.py#L513)), client actions
  through `run_script`, and terminal decisions through their terminal validators.
  Argument normalization, `TurnkeyRefusal` checks, the flash gate, the whitelist,
  and convergence accounting still apply. A batch step has no more power than the
  same call made alone. (Same curated-allowlist discipline as entries #1 and #3.)
- **Early-abort.** Stop the batch at the first step that refuses, is blocked,
  errors, **or times out** (a timeout is a failed step — see entry #7). Return the
  results of completed steps plus which step aborted and why, so the model reacts
  on the next turn instead of barreling on after a failure (e.g. do not read UART
  if the flash refused).
- **Per-step accounting.** Each executed step still updates `BrainState`
  individually (`flash_count`, verification snapshot, the action ledger from entry
  #2, the convergence signatures). The watcher sees every call; a batch is just a
  turn that happened to contain N of them.
- **Terminal steps.** `finalize` may only be the last step; `run_green_check` and
  `finalize` should not be followed by further steps. Reject malformed orderings
  deterministically.

### Relationship to the other entries

- **Entry #4 (native tool-use) gets this for free.** Provider-native tool calling
  already supports multiple / sequential `tool_use` blocks per assistant turn, so
  if #4 is adopted, model-composed batching is the native behavior and this entry
  is just the `TurnDecision`-JSON equivalent of it. Keep the two consistent: same
  per-step gating and early-abort whichever format is used.
- **Entry #2 (session).** All step results are appended to the session in order,
  preserving the append-only shape.
- **Does not add tools.** Batching only sequences existing whitelisted tools. The
  earlier "send input to UART" example still needs a UART-*write* tool, which is
  not in `AllowedServerToolName` today — out of scope here.

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/actions.py`** — add `BatchAction` to
   `ActionUnion` and to the JSON schema (`turn_decision_output_schema`), with
   `steps` as a list of the existing action variants.
2. **`src/pyocd_debug_mcp/brain/loop.py`** — execute a `BatchAction` by iterating
   its steps through the existing per-action dispatch, applying early-abort and
   recording each step into the ledger/state.
3. **Instructions** (`_build_instructions`,
   [loop.py:168](../src/pyocd_debug_mcp/brain/loop.py#L168)) — document batching,
   the early-abort contract, and the terminal-step rules so the model composes
   sensible sequences.

### What it is supposed to do

- Let the model drive a fluent multi-step operator sequence in one turn (flash ->
  read -> ... ) instead of one tool per round-trip, cutting model calls and
  latency for routine sequences.
- Preserve every safety guarantee: per-step gating, early-abort on failure, and
  full per-step convergence/ledger accounting — the batch is a convenience over
  the same gated calls, not a new privilege.

### Constraints / watch-outs

- **No bypass.** A step inside a batch must be exactly as gated as the same call
  made alone; the batch executor calls the same `_execute_server_tool`.
- **Abort, don't barrel.** First refusal/block/error ends the batch and reports
  back; never continue a sequence whose precondition just failed.
- **Reasoning trade-off.** Within a batch the model cannot react between steps —
  that is the point (it is committing to a sequence), but it means batches should
  be used for routine sequences, not for steps whose next move depends on the
  prior step's value.
- **Deterministic CI mode.** The replayable mode must execute batches in the same
  fixed order for reproducibility.
- **Doc-sync + verify.** Update the README turnkey section / R12 turnkey spec, and
  re-run the suite before claiming it works.

### Status

Proposal only. Not yet specced, not yet implemented.

---

## 6. Device input tools: UART write (and future I2C/SPI stimulus)

### Problem / current behavior

The agent can **observe** firmware output but cannot **stimulate** it. The UART
adapter is read-only — `open` / `close` / `reset_input_buffer` / `read`, with no
`write` ([uart_interface.py:20](../src/pyocd_debug_mcp/adapters/uart_interface.py#L20))
— and the only serial tool, `read_serial`, just reads/matches
([mcp_client.py:295](../src/pyocd_debug_mcp/brain/mcp_client.py#L295)). There is
no serial-write tool anywhere in the MCP surface, and nothing in
`AllowedServerToolName` ([actions.py:10](../src/pyocd_debug_mcp/brain/actions.py#L10)).

So an entire class of operation/interaction testing is impossible today: driving
a firmware CLI prompt, sending a command and checking the response, feeding test
input to exercise a code path. This is exactly the gap entry #5 flagged ("send
input to UART" needs a UART-*write* tool that does not exist). For real
bring-up/debug, passive observation is not enough — you need stimulus.

### What the change is

Add a device-input (stimulus) capability, starting with **UART write**, surfaced
as a new MCP tool and a new brain action. Unlike entries #1/#3/#5, this is **not**
a brain-only change — the capability is absent at every layer, so it spans the
full stack (and must follow the repo's "shared services, not wrapper-only" and
"data-driven boards" rules):

1. **Adapter contract** — add `write(handle, data: bytes)` to `UARTInterface`
   ([uart_interface.py:20](../src/pyocd_debug_mcp/adapters/uart_interface.py#L20))
   and implement it in `uart_pyserial`.
2. **Shared service** — a send/IO service (extend `services/uart_capture.py` or a
   new `uart_io` service) so the same logic is callable by the MCP tool, Stage 0
   flows, and the turnkey brain — not reimplemented per caller.
3. **MCP server tool** — a `write_serial` tool in `server.py` (an action with side
   effects -> "tool", not a read-only "resource", per the architecture doc).
   Optionally a `send_and_read` convenience that writes then captures, though the
   composable path is `write_serial` then `read_serial` sequenced via an entry #5
   batch.
4. **Brain** — add the tool to `AllowedServerToolName` plus a corresponding
   action, and handle port/baud/line-ending resolution in `_execute_server_tool`
   the same data-driven way `read_serial` resolves them
   ([loop.py:559](../src/pyocd_debug_mcp/brain/loop.py#L559)).

### Forward-looking: I2C / SPI stimulus

Generalize "device input" beyond UART later. I2C/SPI master operations
(addressing, register writes) are more involved and bus-specific, so they are a
**future** generalization, not this entry's deliverable. When added they follow
the same pattern: a backend-neutral adapter contract, a shared service, a
side-effecting MCP tool, a brain whitelist entry, and per-board capability
declared data-driven in `boards/<board>.yaml` (never hardcoded branches). This
entry delivers UART write; it just leaves the door shaped for I2C/SPI.

### What it is supposed to do

- Close the loop from passive observation to active stimulus: drive firmware with
  input and verify its response, enabling real operation/interaction testing.
- Pair naturally with entry #5 — `write_serial` then `read_serial` in one batch is
  the "send a command, read the reply" primitive — and resolve the UART-write gap
  that entry #5 explicitly deferred.

### Constraints / watch-outs

- **Shared service, not wrapper-only.** Write logic must live in a reusable
  service callable by MCP tools and local/Stage 0 flows alike, per the
  architecture's board-control rule.
- **Data-driven, no hardcoding.** Port, baud, and line-ending/encoding resolve
  from board config / session input exactly like `read_serial`; no baked-in
  ports or newline assumptions. Encoding (text vs raw bytes) and line ending are
  explicit tool arguments.
- **Still gated.** A side-effecting tool: normalized, refusable, logged, and
  ledgered like any other (lower-risk than flash, but not ungoverned), and only
  the whitelisted tool is exposed (same curated-allowlist discipline as #1/#3/#5).
- **I2C/SPI are explicitly out of scope here** — future work, same layering.
- **Hardware honesty.** This adds a real hardware I/O path; do not claim it works
  until it is exercised on a real board this session. Doc-sync the README tool
  surface and the tool docstring in the same unit of work.

### Status

Proposal only. Not yet specced, not yet implemented.

---

## 9. Model-authored scripts (code mode) over the gated server-tool API

### Problem / current behavior

Standalone, codex/claude are agents that **write and run scripts**. But the turnkey
integration reduces the provider to a **one-`TurnDecision`-per-turn decision
function** (`provider_codex_cli` pipes a prompt, reads one JSON object back),
*discarding the model's native scripting/agentic capability*. The model is throttled
to one declarative action per turn and cannot, for example, loop a read across 100
addresses, branch on the result, and act — it must round-trip the brain for each
step. The real limitation to remove is this throttle, not the absence of a gadget.

### What the change is

Let the model **author scripts natively** (the way codex/claude write files with
`apply_patch` standalone) into the **named client-side tool store**, and **execute a
hardware-touching (server-native) script only through a gated `run_script`
decision.** (A script that calls no server-native tool is model-native and runs
free — entry #11; this entry's gating concerns the server-native ones.) The split is
the whole design:

- **Authoring is native and inert.** Writing a script touches no hardware, so it is
  *not* a gated decision — the model writes (and edits/redrafts) the file directly,
  in its native flow, with no format tax and no per-edit round-trip. The script
  never goes inline into a `TurnDecision` (decisions can only name existing
  actions/tools; raw script text is not a valid decision).
- **Execution of a server-native script is a gated decision.** To run one the model
  emits a
  `run_script(name)` action; the brain reads the named file, gates it, runs it, and
  returns the aggregated result. This is where control matters and where it stays.
- **The brain captures what ran, at run time.** It did not witness the authoring, so
  on `run_script` it **snapshots + hashes the file** — that hash is the identity and
  version that actually executed. Identity, versioning, reuse counting, promotion
  (entry #10), and audit are all keyed on *what ran*, captured at execution, not on
  the model's drafting keystrokes (which are its private scratch).

Why this shape (Design 2) rather than making the *write* a formal decision too:
authoring is inert, so gating it buys nothing and only adds round-trips; native
writing is the model's fluent, untaxed format; and the dangerous part — execution —
is still a formal gated decision. It is also consistent with the
[accepted stance](#accepted-design-stance-direct-hardware-access-is-not-sandboxed):
inert native file-writing is fine to leave native; control is reasserted at the
gated run.

**This keeps native scripting power without giving up brain control — the
difference from free code mode is *granularity*, not capability:**

- *Within* a `run_script` execution: the script loops, branches, and makes many
  gated tool calls (`for addr in ...: client.read_memory(addr)` → analyze →
  `client.flash(...)`) in **one** model round-trip — the efficiency win of code
  mode is fully preserved.
- *At* the turn boundary: the model still emits the `run_script` decision, and the
  brain appends the script result as the next user message. The brain keeps parsing
  each turn-closing `TurnDecision`, updating `BrainState`, running convergence, and
  applying caps. The brain is never a bystander where it matters — execution.

Whether a script survives the run depends on context (ephemeral without a project, a
retained candidate inside a project — see entry #10). The named file in the tool
store, snapshotted at run, is what gives a script the **stable identity** the rest of
this entry and entry #10 depend on (versioning, reuse counting, promotion).

**Optional formal-write checkpoint (Design 1, only where authoring must be
reviewed).** For *guardrail-class* scripts (entry #9's model-authored guardrails),
where you may want the brain to inspect/approve a script **before** it can exist or
be installed, add a formal write/install decision as a validation checkpoint. This
is the exception, not the default — ordinary computation/orchestration scripts do
not need it, because gating execution is sufficient.

**The critical integrity rule:** the script does **not** get a raw probe handle. It
calls the server tools only through the **gated client API**, where every method
routes through the *same* gates as a `server_tool` action — flash gate, refusals,
convergence watcher, entry #7 timeouts, and the `AllowedServerToolName` whitelist.
Scripting freedom for the model; per-call gating unchanged for the brain. Each call
the script makes is still logged, counted, and convergence-checked.

Two flavors fall out, and they land in **different tool classes** (entry #11):

- **Computation scripts** — process ground truth without calling any server-native
  tool ("is this field non-zero across the last 10 reads?", "diff two register
  dumps"). These call **no** gated API, so they are **model-native** (entry #11):
  the model runs them **free** in its sandbox, no `run_script` decision needed. This
  is the entry #8 custom-predicate case.
- **Orchestration scripts** — drive a sequence of *gated* server-tool calls
  (flash → wait → read → check), i.e. a model-authored macro like `run_green_check`
  or a named, reusable test sequence. Because they reach server-native tools they are
  **server-native** and run **only via a gated `run_script` decision**. The
  declarative batch (entry #5) is the no-control-flow subset of this.

(The dividing line is entry #11's: a script that calls a server-native tool is
server-native and goes through `run_script`; one that calls none is model-native and
runs free. Enforced by the gated client API being in scope only during `run_script`.)

**Naming note: call these "client actions" when contrasting them with model
actions and server tools.** A client action is a model-authored, client-side script
or macro that lives in the client/session tool store and can be executed by name.
It is not a raw server tool, because it runs on the client side and may compose
many tool calls. It is not a model action body either, because the model never
embeds the script inline in a `TurnDecision`; the decision only names an existing
client action through `run_script(name, inputs)`. Client actions persist for one
client session by default; in a project, they may be retained as project tool
candidates under entry #10, but they are never silently promoted or auto-loaded.

Defining properties:

- **Stable identity, versioned content (captured at run).** A script has a **stable
  identity** = its filename in the tool store (the model names the file when it
  writes it). On each `run_script` the brain **snapshots and hashes the file** — that
  hash is the version that ran. Editing the file natively produces a new hash (new
  version) under the same filename/identity; reuse and history accrue to the
  identity; re-validation runs the latest file. The brain never has to witness the
  authoring — it captures identity + version from the file at execution.
- **Editable / iterative (native).** The model edits the file directly in its native
  flow. When a `run_script` errors or times out, the brain returns the failure
  (stderr / exit / timeout); the model edits the file and re-runs. Native edits are
  free (no per-edit decision round-trip); only the *runs* are decisions. Broken
  drafts are *iteration states of one file*, not separate artifacts. The run/edit
  loop is **bounded** by the convergence watcher + entry #7 timeouts: after N failed
  run cycles the script is abandoned.
- **Lifecycle is context-dependent.** Project-less ad-hoc run: ephemeral —
  discarded at run end (nowhere to persist). Inside a project: **retained as a
  candidate** (entry #10), never silently auto-loaded, promoted to active only by
  the brain-computed signals in #10.
- **CLI-providers only.** Requires the provider to execute code; the no-code-exec
  API providers cannot author session tools, so any feature that depends on them
  (e.g. entry #8 custom predicates) must have a brain-shipped fallback.
- **Hardware only through the gated API.** A script may call the whitelisted server
  tools via the brain-provided client API (each call gated as above) and may read
  brain-provided ground truth (observations, the ledger). It may **not** take
  model-supplied values as authoritative input or reach the probe / serial port
  directly — hardware goes through the gated API, never around it.
- **The brain consumes the return / still owns the gates.** When a script's output
  feeds a brain mechanism (e.g. an entry #8 flag), the brain decides what it means;
  the script never sets brain state or flags itself. And the brain — not the script
  — owns every guardrail on the calls the script makes.
- **Model sees the existing tool index.** So it *edits/reuses* an existing tool
  rather than blindly re-authoring a near-duplicate, the brain shows the model the
  index of tools already available (the shipped vocabulary plus, in a project, the
  project's tools) — same index pattern as skills (entry #3).
- **Deterministic, logged, re-runnable.** The script source (per version), its
  inputs, and its output are recorded under `runs/<session_id>/` so a run is
  auditable and the brain can re-execute it against the same evidence.

### Relationship to the accepted stance

Per the [Accepted design stance](#accepted-design-stance-direct-hardware-access-is-not-sandboxed),
the model on CLI providers *already* has full code execution, so this entry does
not grant a new raw capability — it gives that capability a **structured, audited
shape** pointed at the gated server-tool API: gated calls, brain-consumed outputs,
identity/versioning, lifecycle, and logging.

It also **reduces** bypass incentive rather than adding risk. The #1 reason a
code-capable model would go *around* the brain is that the one-action-per-turn
interface is more limiting than its native scripting. Code mode makes the
sanctioned path as expressive as the raw path (minus the hardware danger), so the
motivation to bypass largely disappears — strengthening, not weakening, the
mitigation in the accepted stance. The honest framing is unchanged: this organizes
a cooperative model's scripting; it is not a sandbox against a model that
deliberately bypasses the brain.

### Model-authored guardrails (a third flavor)

The same machinery lets the model install a **guardrail**: a brain-enforced
precondition on a specific dangerous action (e.g. "block the UART command that
wipes the bootloader unless explicitly confirmed"). Honest framing — who it binds:

- **Against the model's own future error: hard.** The lucid model at T0 installs
  the guard; the brain enforces it; a thrashing/confused model at T5 is blocked by
  it. A self-binding commitment device for the long-tail dangers the shipped
  guardrails did not anticipate.
- **Against a deliberately adversarial model: soft.** The model that authored it
  could author a permissive one or remove it — the accepted-stance ceiling.

Design rules: (1) **known-critical ops get *shipped* guardrails**, not
model-authored ones — model-authored guards are for the situation-specific long
tail; (2) **the brain enforces it** as a real precondition for every actor
including the model, or it is not "hard"; (3) **removal is gated/logged** (ideally
human-approved) so a thrashing model cannot strip its own interlock; (4) guards
that recur are **promoted to shipped guardrails** (same promotion path as tools).

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/`** — a script runner that, on `run_script`, reads
   the named file from the tool store, **snapshots + hashes it** (identity/version),
   exposes the **gated server-tool client API** (whitelisted tools, each routing
   through the existing `_execute_server_tool` gates) plus brain-provided ground
   truth, runs it, captures its return, and bounds it (entry #7 per-call + per-script
   budgets). Returns failures to the model for the native edit/re-run loop, capped by
   the convergence watcher, which still sees every gated call the script makes. Pairs
   with the entry #2 session model.
2. **Action surface** (`actions.py`) — the formal action is **`run_script(name,
   inputs)`** (authoring is native, not an action). The `TurnDecision` format is
   never bypassed: decisions still only name actions/tools, and the script body is
   never inline in a decision. Surface the tool index so the model edits/reuses an
   existing file rather than re-authoring. *(Optional, guardrail-class only: a formal
   write/install action as a pre-existence review checkpoint — see Design 1 above.)*
3. **Tool-store location** — run the provider with its working dir pointed at (or
   synced to) the tool store so native file writes land where `run_script` reads:
   the session run dir, or the project `tools/` folder (entry #10).
4. **Persistence** — snapshot per-run source/inputs/output to `runs/<session_id>/`
   for audit; in a project, retain the script file as a candidate (entry #10).

### What it is supposed to do

- Restore the model's native scripting (code mode) — loops/branches/data
  processing — pointed at the gated server-tool API, so it is no longer throttled
  to one action per turn for computation, orchestration, or guardrail authoring.
- Keep that scripting honest and auditable: every hardware call gated as a normal
  action, brain consumes outputs, brain owns the guardrails, all logged per
  version — without bloating the permanent tool surface or persisting throwaway
  scripts.

### Format tax: native authoring dissolves it (and is why Design 2 beats Design 1)

The model is pretrained/RLHF'd to write scripts in its **native** flow (codex via
`apply_patch`/file-write tools, claude similarly). The format tax appears only if you
force the script body through a *foreign serialization* — e.g. capturing it as a
structured "define-script" action, worst of all as an escaped JSON string in a
`TurnDecision`. That is off-distribution: truncation/escaping errors, shorter and
less dynamic scripts, suppressed "write-and-run" reflex.

**Design 2 sidesteps the tax by construction.** Because authoring is *native file-
writing* (the model writes the file the exact way it does standalone) and is **not**
captured into any structured action at all, the script body is never serialized into
a foreign format — there is nothing to tax. This is a primary reason Design 2 (native
write, gated run) is preferred over Design 1 (formal write decision): Design 1, if
its write step embedded the script in a structured action, would reintroduce the
tax; Design 2 does not.

So the only requirement is that the model's **native file-writing is active** in how
the brain invokes the provider (it is, on the CLI providers — `codex exec` can still
`apply_patch`), and that its working dir is pointed at the tool store so the file
lands where `run_script` reads it. Entry #4 (native tool-calling) is then **not**
needed to avoid a script-body tax — it reverts to a general reliability option for
the *decisions* (`run_script` etc.), which carry only short names, no script body.

**Verify empirically (don't assume).** If Design 1 is ever considered for guardrail-
class scripts, compare native-file authoring (Design 2) vs. capturing the body in a
structured action, on the same task — script length / quality / success — per
verify-don't-claim, rather than guessing the tax.

**Residual ceiling (honest):** the absolute highest scripting fidelity is full native
agentic mode (BYO-agent, model drives), which we deliberately traded away for brain
control. Design 2 (native authoring + gated run) gets *most* of the way — the
authoring is already fully native; what stays under brain control is execution. If
some residual gap remains, the lever to reconsider is a more BYO-leaning hybrid for
the scripting portion.

### Constraints / watch-outs

- **Not auto-promoted.** A session tool never silently becomes a persistent
  auto-loaded tool; activation happens only via the brain-computed signals in
  entry #10, or by deliberate promotion into the shipped vocabulary (e.g. an entry
  #8 predicate).
- **No fabricated inputs; hardware only through the gated API.** Ground truth comes
  from the brain; every hardware call goes through the gated client API (same gates
  as a `server_tool` action), never around it — the convergence watcher and entry
  #7 budgets see every call.
- **Bounded iteration.** The edit/re-run loop runs under the convergence watcher +
  entry #7 timeouts; a tool that cannot be made to work after N edits is abandoned
  and cannot promote.
- **CLI-only; always have a brain-shipped fallback** for features that must also
  work on the API providers.
- **Author natively; never serialize the script body into a decision.** Design 2
  writes the script as a native file (no format tax); the script body must never be
  embedded in a `TurnDecision`. Only `run_script` (a short name) is a decision.
- **Logged** for audit (per version).
- **Doc-sync + verify.** Document the script contract (native authoring + gated
  `run_script` + snapshot-at-run); before claiming it works, exercise a native
  author → run → fail → edit → re-run → pass cycle on real hardware.

### Status

Proposal only. Not yet specced, not yet implemented.

---

## 19. Live provider progress with separate authoritative decisions

### Problem / current behavior

The turnkey CLI currently waits silently while the brain loop runs. The operator
gets the final `_print_execution(...)` summary only after `run_turnkey_with_provider`
returns. Per-turn model decisions, brain actions, and results are captured in
`model_turns` / `brain_trace`, but they are not streamed to the terminal while the
task is running.

This creates a bad operator experience and a real diagnosability gap. A task can
spend many minutes inside a provider call, build, flash, UART read, green check, or
retry loop. Even if entry #7/#14 timeouts eventually fire, the user cannot tell
whether the agent is productively working, waiting on a long hardware operation,
stuck inside the model provider, or going off course until the whole run returns.

### What the change is

Add live progress streaming to the brain CLI, but keep machine control separate
from human-visible text.

The rule is:

```text
visible provider/brain stream = operator visibility only
structured decision artifact = authoritative brain input
```

Do not make the brain scrape arbitrary streamed prose for control decisions. The
model may emit visible progress text while it works, and the CLI should show it,
but the brain should still read the final turn decision from a strict structured
channel.

For CLI providers, prefer a separate JSON/artifact file for the authoritative
decision:

```text
turn_decision.json
```

The provider subprocess should stream stdout/stderr live to the operator and copy
the same bytes into run logs. When the provider exits, the brain reads and validates
`turn_decision.json` as the only authoritative turn decision. Human-facing text is
never parsed for board access, timeout settings, script names, or tool parameters.

If a CLI provider cannot produce a separate output file, use the provider's most
reliable structured-output mechanism as a fallback, such as a final isolated JSON
message, but keep that path explicitly less preferred than an artifact file because
mixed prose + JSON delimiter parsing is brittle.

### CLI-provider behavior

For `codex-cli` / `claude-cli` style providers:

- Replace one-shot `subprocess.run(..., capture_output=True)` with a streaming
  process runner.
- Print model-visible stdout/stderr to the CLI as it arrives.
- Tee the same stream into `runs/<session_id>/logs/provider_stream.log` or a
  pre-session temp log later copied into the run root.
- Keep the provider hard timeout from entry #7/#14.
- Continue using a strict final decision object. For Codex, this should be the
  `-o <output_path>` file when available. For any CLI that lacks native file output,
  prompt it to write a known decision artifact in its working directory when the
  CLI's tool mode supports file writes; otherwise fall back to a final structured
  stdout block with clear tests around delimiter collisions.
- On Ctrl-C / cancellation, terminate the provider subprocess, stop any in-flight
  server operation if possible, disconnect the MCP session, and return a clear
  cancelled result instead of leaving long-running children behind.

The model's visible stream should be useful but not secret-dependent. Prompt it to
emit concise progress like "checking UART path", "editing app main", "running
build", or "waiting for flash result". Do not require hidden chain-of-thought or
private reasoning to be streamed.

### API-provider behavior

API providers do not run as local interactive subprocesses, so the implementation
is different:

- Use the provider's streaming API when available to display assistant-visible text
  deltas in the CLI.
- Still request the authoritative turn decision through provider-native structured
  output/tool calling where possible, not by parsing the visible stream.
- If the provider API supports separate event types for text deltas and structured
  output/tool calls, route text deltas to the operator stream and route only the
  final structured object/tool call to the brain parser.
- If the provider API cannot stream structured output reliably, keep the current
  non-streaming structured request for correctness and add a brain-owned heartbeat
  while waiting.
- Never expose or depend on hidden reasoning. The live stream is for operator
  progress summaries and visible assistant text only.

API-provider fallback behavior should still make hangs obvious:

```text
[brain] waiting for model: 90s elapsed / 600s timeout
[brain] waiting for model: 120s elapsed / 600s timeout
```

That heartbeat is brain-owned, so it works even when the model/provider emits no
tokens.

### Brain and tool progress events

Provider streaming alone is not enough. The brain should emit its own structured
progress events before and after every long wait:

- run started, board id, provider, model, effective iteration budget
- iteration `N/M`
- waiting for model, with elapsed time and provider timeout
- model produced action kind and short action summary
- running server tool / build / green check / read file / replace file
- action completed, failed, refused, timed out, or was cancelled
- disconnect / cleanup started and completed
- final result

These events should be written both to the terminal and the run artifacts. A future
GUI can consume the same event stream instead of scraping terminal text.

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/provider_types.py`** - add an optional progress/event
   callback interface that providers can call with visible text chunks and status
   events.
2. **CLI providers** - replace captured subprocess execution with a streaming
   process runner, tee output to terminal + logs, and parse only the final decision
   artifact.
3. **API providers** - use streaming API responses for visible text when available,
   while preserving structured output/tool-call parsing for the final decision.
   Add heartbeat fallback when streaming is unavailable.
4. **`src/pyocd_debug_mcp/brain/loop.py`** - emit brain-owned progress events around
   provider waits, action dispatch, tool timeouts, build/flash/read operations,
   refusals, convergence blocks, finalization, and cleanup.
5. **`src/pyocd_debug_mcp/brain/cli.py`** - render progress events live by default,
   with a quiet/JSON mode for tests and automation.
6. **Run artifacts** - persist provider stream, brain progress events, final decision
   JSON, and parsed decision/result separately so audit can distinguish "what the
   user saw" from "what the brain trusted".

### What it is supposed to do

- Prevent the operator from staring at a silent CLI for 10-20 minutes with no clue
  whether the model or hardware operation is still alive.
- Let the user interrupt when the visible model stream shows it is going off course.
- Preserve brain control: only strict structured decisions can trigger board tools,
  scripts, timeout changes, or file edits.
- Make provider hangs diagnosable before the hard timeout fires by showing elapsed
  time and heartbeat status.
- Make long hardware/build operations visible even when the model itself is quiet.

### Constraints / watch-outs

- **Visible text is never authoritative.** Do not parse streamed prose for tool
  parameters, timeout budgets, or final status.
- **Prefer artifacts/tool calls over delimiters.** Delimited JSON in a mixed prose
  stream is a fallback, not the primary contract.
- **Do not stream hidden reasoning.** Progress summaries are enough; the product
  must not depend on private chain-of-thought.
- **Cancellation must clean up.** Ctrl-C or timeout should kill child provider
  processes and attempt MCP disconnect so no unwanted long process keeps running.
- **Keep automation usable.** Provide quiet/JSON progress modes so benchmark and CI
  output stays parseable.

### Status

Proposal only. Not yet specced, not yet implemented. Complements entries #7/#14:
timeouts make waits bounded; live progress makes bounded waits understandable and
interruptible.

---

## 20. Developer turn inspector for live brain/provider/server traffic

### Problem / current behavior

Entry #19 makes the normal CLI less silent, but it intentionally keeps operator
output compact. That is the right product-facing behavior, but it is not enough
while building and debugging the brain itself.

During development, we need to see the full live conversation between the brain and
the provider: the exact prompt sent to Codex/Claude/API, the model-visible provider
stream, the parsed decision, the brain's response/result returned into the next
turn, the evolving `BrainState`, and the server-tool/build responses. Without that,
it is hard to tell whether failures come from the prompt, model behavior, provider
wrapper, action schema, brain policy, MCP/server call, or hardware.

### What the change is

Add a developer-only inspector mode: a separate terminal/window or tailing viewer
that shows live turn traffic while the main agent CLI runs.

This is not the normal product UI. It is a temporary developer debugging surface
that can be removed, hidden, or replaced before shipping. Its job is to expose the
brain/provider/server boundary clearly enough to debug prompt and loop behavior.

The inspector should be read-only. It observes and renders what the brain is doing;
it does not send commands, approve gates, alter prompts, or mutate state.

### What it should show

The inspector should render separate streams/panes or clearly labeled sections for:

- **Prompt to provider** - system/instructions, selected skills, board facts,
  workspace summary, current `BrainState`, last observation/result, available
  action schema, and the exact user/turn prompt sent this turn.
- **Provider visible stream** - the model-visible text from Codex/Claude/API as in
  entry #19.
- **Structured decision** - the final `TurnDecision` / native tool call /
  `turn_decision.json` object that the brain actually trusted.
- **Brain action dispatch** - which action the brain executed, which gates/refusals
  applied, timeout budget used, and any dynamic timeout or iteration-budget updates.
- **Server/tool traffic** - server tool name, sanitized arguments, result summary,
  typed error, timeout, cancellation, or refusal.
- **Brain response into next turn** - the summarized observation/result that will
  be fed back to the model on the following turn.
- **State/convergence** - session id, iteration, flash/build/recover counts,
  verification snapshot, no-progress streak, blocked/refused action families, and
  finalization gate status.
- **Artifacts** - links/paths to prompt snapshots, provider stream logs, parsed
  decision JSON, brain events, tool-call JSONL, build output, diffs, and final
  result.

The normal CLI should not dump all of this by default. The inspector exists because
full prompts and raw tool traces are too noisy for normal use.

### Suggested file/event model

Write the inspector data as append-only files under the run root, then have the
inspector tail them:

```text
runs/<session_id>/logs/
  brain_events.jsonl
  prompt_turns.jsonl
  provider_stream.log
  parsed_decisions.jsonl
  tool_calls.jsonl
  state_snapshots.jsonl
  build_output.log
```

Before a session id exists, write to a pre-session temp run directory and move or
link it into the final run root once `session_id` is known.

The first implementation can be simple: launch a second terminal that tails a
human-readable inspector log, or print the inspector command/path for the developer
to run manually. A richer TUI can come later.

Example CLI surface:

```text
pyocd-debug-brain run ... --inspect
pyocd-debug-brain run ... --inspect-log-only
pyocd-debug-brain inspect --run-root runs/<session_id>
```

`--inspect` may try to open a second terminal window on supported developer OSes.
If terminal spawning is unreliable, fall back to `--inspect-log-only` behavior and
print the exact `pyocd-debug-brain inspect --run-root ...` command.

### Relationship to entry #19

Entry #19 is product/operator visibility: concise live progress, visible provider
text, heartbeats, and cancellation.

This entry is developer/debug visibility: full prompt snapshots, full brain
feedback into the next turn, state snapshots, structured decisions, and tool/server
traffic. Both should be backed by the same event/log infrastructure where possible,
but they render different views of it.

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/loop.py`** - emit prompt snapshots, state snapshots,
   parsed decisions, brain responses, action dispatches, and convergence decisions
   as structured events while the loop runs.
2. **Provider wrappers** - stream provider-visible text into the shared log/event
   sink from entry #19.
3. **MCP/client action dispatch** - log sanitized server-tool requests/responses,
   typed errors, timeout budgets, cancellation, and refusals.
4. **`src/pyocd_debug_mcp/brain/cli.py`** - add `--inspect` and `--inspect-log-only`
   flags for `run` and benchmark case execution.
5. **New inspector command/module** - add `pyocd-debug-brain inspect --run-root ...`
   or an internal helper that tails the JSONL/log files and formats them for a
   developer terminal.
6. **Run artifacts** - keep the inspector files separate from product summaries so
   they can be retained for debugging without changing normal output.

### What it is supposed to do

- Let a developer see exactly what the brain sent to Codex/Claude/API each turn.
- Let a developer see exactly what the brain returned to the model after each
  action, not only what the model said.
- Make prompt, provider, parser, action-schema, server-tool, timeout, and
  convergence bugs easy to localize.
- Provide a practical "debug window" during prototype development without making
  the production CLI noisy.

### Constraints / watch-outs

- **Read-only.** The inspector observes only; it must not become a second control
  path around the brain.
- **Dev-only by default.** Keep it behind an explicit flag and do not make normal
  users read full prompts/tool traces.
- **Redact where needed.** If future prompts include secrets, API keys, customer
  source snippets, or private paths, the inspector/logging layer needs redaction or
  an explicit unsafe-dev mode.
- **Do not rely on terminal spawning.** Cross-platform terminal windows are useful
  but brittle; log-only tailing must always work.
- **Keep structured logs canonical.** The inspector display can be human-friendly,
  but the source should be JSONL/events so failures can be replayed or attached to
  reviews.

### Status

Proposal only. Not yet specced, not yet implemented. This is a prototype/developer
debugging aid that complements, but should not replace, the product-facing live
progress stream in entry #19.

---

## 21. Model-cancellable checkpoints for chunked UART/build/client-action streams

### Problem / current behavior

Some operations are naturally stream-like but are exposed to the brain as one
blocking action. UART reads wait for the configured `read_seconds`, builds wait for
the subprocess to finish, and future model-authored client actions may run a long
sequence before returning. Even with hard timeouts, the model may not see partial
evidence until the whole action finishes, and the brain cannot ask the model whether
the stream is clearly garbage before waiting out the full duration.

This is different from flash/connect/recover cancellation. Those pyOCD operations
are not naturally streamy in the current architecture and should not be pulled into
this change. Avoid the worker/job layer for now.

### What the change is

For the stream-like operations only, run the operation as short chunks and allow the
model to request early termination through a structured checkpoint decision.

The control shape is:

```text
long operation -> chunk/progress events -> brain records them
brain deterministically continues/cancels on obvious conditions
brain occasionally asks the model for a checkpoint decision
model may request termination through a structured response
brain owns/applies the cancel flag and stops between chunks
```

The model should not write a raw shared-memory flag. The model emits a structured
checkpoint response; the brain validates it and updates brain-owned cancellation
state.

Example checkpoint response:

```json
{
  "kind": "stream_checkpoint_decision",
  "stream_id": "uart-123",
  "terminate": true,
  "reason": "UART bytes are repeated framing garbage and do not match expected boot text."
}
```

The cancel flag is internal to the brain/runner. It is protected by normal brain
state ownership, not exposed as a mutable model-owned primitive. The stream loop
checks it between short chunks and stops cleanly if set.

### Scope

Implement only for:

- **UART reads** - read in short windows, accumulate chunks, stream them to the CLI
  and logs, stop early on expected text, clear silence/stall conditions, or
  model-requested termination.
- **Builds / external commands** - stream stdout/stderr, track last-output time,
  checkpoint recent output, and allow the model to request subprocess termination
  when output clearly shows the build is doomed or off course.
- **Long model-authored client actions** - let client actions emit structured
  progress events; checkpoint those events and allow the model to request early
  stop of the client action runner.

Do **not** include pyOCD flash, connect, recover, halt/resume, or memory/register
operations in this change. Those remain bounded by timeouts and can be revisited
later if a cancellable worker/job layer is added.

### Checkpoint semantics

Checkpoints are occasional and bounded, not every byte or every line:

- ask after a time interval, byte/line threshold, suspicious pattern, long silence,
  or explicit client-action progress checkpoint;
- send a compact summary plus a tail of recent output, not the entire stream every
  time;
- apply a short checkpoint-provider timeout;
- if the model does not answer in time or returns invalid output, the brain ignores
  that checkpoint response and continues/cancels using deterministic policy;
- if the model requests termination, the brain records the reason, stops the stream
  at the next chunk boundary, and returns a normal action result explaining that the
  stream was model-cancelled after partial evidence.

When the brain asks for a checkpoint decision, the prompt should be explicit:

```text
This operation is still running and data is streaming. Do not propose a new board
action or final answer. Only decide whether this stream should continue or terminate.
```

Any non-checkpoint content from the model is ignored for control purposes, though it
may still be visible in the live provider stream from entry #19 and visible in the
developer inspector from entry #20.

### Brain-owned deterministic rules

The brain should not rely on the model for obvious stream control:

- UART expected text found -> stop success.
- UART no bytes after configured silence threshold -> stop with no-output/stall.
- UART bytes arriving but no match -> continue until budget or checkpoint decision.
- Build process exits -> stop with exit code and captured tail.
- Build no output for stall timeout -> terminate or fail by deterministic policy.
- Client action reports done/error -> stop.
- Total operation wall-clock budget exceeded -> cancel/fail by timeout.

The model checkpoint is for semantic interpretation of ambiguous streams, such as
"this UART is clearly the wrong baud/framing" or "this build is repeatedly failing
on the same missing include and continuing will not help."

### Where it belongs

1. **Action/schema layer** - add a separate `StreamCheckpointDecision` schema. Do
   not overload the normal `TurnDecision`; checkpoint decisions cannot run tools,
   edit files, finalize, or change global state.
2. **Provider layer** - add a lightweight checkpoint call path with a short timeout
   and strict parser. It should be cheaper and narrower than a full turn.
3. **UART service / brain read path** - expose chunked read progress to the brain,
   or add a brain-side loop that performs short `read_serial` calls rather than one
   long read. Prefer the design that avoids long in-flight reads.
4. **Workspace/build runner** - replace captured subprocess execution with
   streaming stdout/stderr, progress events, stall detection, and termination.
5. **Client-action runner** - provide a `client.progress(...)` API and support
   early stop when the brain sets the stream cancel state.
6. **Progress/inspector integration** - send chunks/checkpoints/cancel reasons to
   the entry #19 live progress stream and entry #20 inspector logs.
7. **Run artifacts** - record checkpoint prompts, checkpoint decisions, partial
   stream tails, cancellation reasons, and final operation results.

### What it is supposed to do

- Avoid waiting a full long read/build/client-action duration when partial evidence
  already shows the operation is wrong or useless.
- Let the model semantically identify bad streams without giving it direct control
  over hardware or subprocesses.
- Preserve deterministic brain authority: the model requests cancellation, the brain
  validates and applies it, and the stream stops only at safe chunk boundaries.
- Keep the implementation scoped to stream-friendly operations and avoid the larger
  pyOCD worker/job architecture.

### Constraints / watch-outs

- **No raw model-writable mutex flag.** The model emits structured cancellation
  requests; the brain owns the mutable state.
- **No full model turn inside every chunk.** Checkpoint asks must be coarse,
  bounded, and optional.
- **Checkpoint responses cannot perform actions.** They can only request
  continue/terminate for the active stream.
- **Short chunk boundaries matter.** UART/backend reads and subprocess polling must
  use short enough intervals that termination feels responsive.
- **Do not include non-stream pyOCD ops.** Keep flash/connect/recover on the
  timeout/worker backlog, not this scoped feature.

### Status

Proposal only. Not yet specced, not yet implemented. Scoped companion to entries
#7, #14, #19, and #20: bounded waits, visible stream progress, developer inspection,
and model-requested early termination for stream-friendly operations only.

---

## 22. Proof escalation ladder for expensive live validation

### Problem / current behavior

The roadmap already has the right runtime efficiency shape: free host work
(entries #11/#12), model-authored scripts (entry #9), compact result ledgers
(entry #2), progress streams (entry #19), and stream checkpoints (entry #21). The
remaining waste is mostly in **validation policy**: when a change needs proof, it is
too easy to jump straight to full live-provider + hardware matrices, burning Claude
usage and board time to rediscover implementation bugs that static/unit/replay
checks would have caught.

This is **not** a budget governor. Do not add arbitrary model-token or turn limits
that make the product feel cramped. The issue is proof ordering: spend cheap,
deterministic checks first, then escalate to live providers and real hardware when
the evidence actually requires them.

### What is already covered elsewhere

- Free local work before a governed board decision: entries #9, #11, and #12.
- Salient result compression and compaction-proof memory: entry #2 and the
  canonical memory spec.
- Provider-visible progress and separate authoritative decisions: entry #19.
- Chunked waits/checkpoints for long streams: entry #21.
- Branch-specific live proof ladders: the Branch A live-provider hardware suite
  spec. This entry generalizes that discipline into the product/process backlog.

### What the change is

Add a reusable proof escalation policy for specs, reviews, and test-suite runs:

1. **Static/local first:** formatting, typing, unit tests, schema validation, and
   deterministic replay/probe-free checks.
2. **Cheap behavioral canary:** one deterministic benchmark or mock-provider path
   that exercises the changed surface.
3. **One live-provider canary:** use the provider most likely to expose the changed
   adapter/prompt behavior, not every provider by default.
4. **One hardware canary:** use the board most likely to expose the changed
   hardware/build path, not every board by default.
5. **Full live matrix:** run only when the changed surface touches provider
   continuity, board abstractions, final verification semantics, release closure,
   or when a cheaper rung fails in a way that requires broader proof.

Each rung produces artifacts that say whether the next rung is required, skipped as
not relevant, or still pending. "Skipped as not relevant" is allowed only when the
touched code/docs do not affect that surface; it is not a substitute for hardware
proof when hardware behavior is the claim.

### Where it belongs

1. **Spec/review/test-suite skills** - include the ladder in Firmware-CLI process
   instructions so agents choose the cheapest sufficient proof first.
2. **Run metadata / reports** - record the proof rung reached, why escalation did
   or did not continue, and which expensive proof remains pending.
3. **README / R12 docs** - document that deployment closure still requires the full
   relevant matrix, but ordinary iteration should use the ladder.

### What it is supposed to do

- Avoid spending Claude/hardware time on bugs that deterministic checks can catch.
- Make "not run" honest: skipped because irrelevant, pending because unavailable,
  or required because the claim touches that surface.
- Keep the product non-frustrating: no arbitrary caps, just a cheaper path to the
  same evidence.

### Constraints / watch-outs

- **No budget governor.** Do not block useful work because a token/turn counter
  tripped. Escalation is evidence-driven, not quota-driven.
- **No fake green.** Cached or skipped lower-rung proof cannot replace live hardware
  proof when the acceptance claim is hardware behavior.
- **Touched-surface mapping must be conservative.** If a change touches provider
  adapters, hardware actions, workspace build behavior, final verification, or
  recovery, escalate to the relevant live rung.
- **Artifacts must explain the choice.** A future reviewer should know why a full
  matrix was or was not run.

### Status

Proposal only. Not yet specced, not yet implemented. Complements the existing
Branch A suite ladder; it is the reusable process rule for future changes.

---

## 23. Cache-assisted artifact/result reuse for setup and repeated non-final checks

### Problem / current behavior

The roadmap already stores rich artifacts and memory, but it does not yet define a
small, content-addressed reuse layer. Repeated runs can rebuild identical firmware,
re-render unchanged tool/skill prompt blocks, re-identify the same attached board,
or rerun setup checks whose inputs have not changed. That wastes wall time and
provider patience, even when the final acceptance proof still needs to be live.

This is different from the canonical memory layer: memory tells the model what
happened; cache-assisted reuse lets the runner avoid repeating deterministic setup
work when inputs are identical.

### What is already covered elsewhere

- Artifact indexes and code/workspace maps: canonical memory layer.
- Project-level reusable custom tools/skills: entry #10.
- Build/test/live proof artifacts: R12 and Branch A suite specs.
- Salient result excerpts: entry #2.

### What the change is

Add a bounded, auditable cache for deterministic or setup-oriented facts:

- source/workspace hash + build command + toolchain fingerprint -> build result and
  artifact paths;
- firmware artifact hash + board id + probe/target identity -> prior flash/check
  metadata, usable only as setup context unless a live final proof is not required;
- MCP tool schema hash -> rendered prompt catalog;
- selected skill ids + skill file hashes -> rendered skill index/safety block;
- board discovery fingerprint -> recently observed board identity and serial/probe
  mapping, revalidated cheaply before use;
- benchmark case id + fixture hash -> prepared workspace path or seed metadata.

The cache is advisory unless the cached artifact is itself the thing being reused
(for example, an unchanged rendered prompt catalog). It may skip redundant setup or
let the provider inspect prior facts, but it must not silently replace a required
live final verifier.

### Where it belongs

1. **Run artifact layer** - write cache records with content hashes, environment
   fingerprints, timestamps, and provenance links to the original run artifacts.
2. **Workspace/build runner** - reuse build outputs only when source, command,
   board target, toolchain fingerprint, and relevant environment keys match.
3. **Prompt assembly** - reuse rendered tool/skill blocks by hash so static context
   is stable and cache-friendly.
4. **Hardware setup** - reuse board discovery only as a hint; still revalidate the
   attached probe/serial before any hardware operation.
5. **Reports** - state when a result was reused, what hash justified it, and whether
   a live final proof was still run.

### What it is supposed to do

- Reduce repeated setup work and provider-visible noise.
- Make reruns faster without weakening final acceptance proof.
- Give the model useful prior artifacts by reference instead of reprinting or
  recomputing them.

### Constraints / watch-outs

- **Never replace required final hardware proof.** If the claim is "this board
  works now," run the live verifier now.
- **Invalidate conservatively.** Source, command, board id, probe identity,
  toolchain version, package lockfiles, environment-sensitive config, and runner
  version must be part of cache keys where relevant.
- **No stale board assumptions.** Board/probe/serial mappings are hints until
  revalidated in the current run.
- **Portable paths.** Cache records should prefer repo-relative artifact references
  and tolerate workspace relocation.
- **Transparent reuse.** Every reused result must be visible in events/artifacts.

### Status

Proposal only. Not yet specced, not yet implemented.

## 16. Scoped success gates (replace the whole-board green check)

### Problem / current behavior

The current success early-exit is the **green check**: `run_green_check` re-flashes
the **reference** artifact and checks **one** expected symbol + **one** UART
substring against the **whole board** ([loop.py:712](../src/pyocd_debug_mcp/brain/loop.py#L712)),
and `finalize(healthy_confirmed | fixed)` is gated on `green_check_ok`
([loop.py:888](../src/pyocd_debug_mcp/brain/loop.py#L888)). That is a *restore-to-
known-good* validation — correct for the benchmark, **wrong for real development**,
where success is **scoped** to a specific function/feature and there can be many
diverse checkpoints. Forcing every success through one monolithic whole-board
re-flash + final-UART + one-symbol check doesn't fit. **Replace it with scoped
success gates.**

### Why success can't just copy the entry #8 infeasible gate (the asymmetry)

- **`infeasible` (a "broken" claim):** an honest test of a working board *contradicts*
  a false claim — reality is a hostile witness, so a false "broken" is hard to fake.
- **Success (a "works" claim):** a weak/trivial test *passes* without exercising the
  feature — reality only pushes back if the test genuinely exercises it, and the
  model controls the test.

So a self-authored **success** test is far more gameable than a self-authored
**failure** test. Success therefore needs *more* than entry #8's mechanism: the
criteria must be **anchored** (human / manifest) or the discrimination must be
**enforced** — never just "the model wrote a passing test."

### What the change is

Replace the monolithic green check with **scoped success gates** — verify success for
the specific function/feature in question, not the whole board. **Two arms**, chosen
by assurance need; in both, the success criteria are **anchored, never model-invented**.

### Arm A — Automated (synchronized skill + brain-enforced flip)

1. **Trigger.** The model declares a scoped success ("function X works").
2. **Skill injection (entry #13, at done-time).** Inject the success-test rubric skill,
   which tells the model to:
   - design the test so that **flipping ONE critical element makes it fail** (a
     discriminating test);
   - pick a critical element that is **relevant** to the goal;
   - **declare that critical element to the brain as a specific, FLIPPABLE value** — a
     symbol/memory/register read or a UART substring the brain can corrupt, *not* a
     vague "correctness";
   - read the *actual* feature's real output (not a proxy), include a negative control.
3. **Model authors the test** as a gated, model-authored script (entry #9 over the
   server-tool API; entry #11 `run_script` path) and **declares the flippable critical
   element**.
4. **Brain gate (hard enforcement):**
   - run the test on the current state → must **PASS**;
   - re-run it while **flipping the declared element** — the brain mediates the read
     and returns a corrupted value — → must **FAIL**.
   Both must hold → accept the scoped success. The model **can't fake the flip** (the
   brain runs it), and the brain **knows what to flip** (the model declared it). This
   is the synchronization: the skill makes the model build a flippable test and name
   the element; the brain enforces the flip.
5. **Hard vs soft:**
   - **Hard-enforced:** the test *genuinely discriminates on the declared element* —
     not a constant, not ignoring its reads, not lying about the flip outcome (the
     brain observed both runs).
   - **Soft (skill + cooperative model):** that the declared element is the *relevant*
     one. The brain proves the test depends on `X`; it does **not** prove `X` means the
     feature works.
   - **Residual ceiling (accepted):** a relevant-*looking* but actually-irrelevant
     declared element passes the flip yet doesn't verify the real feature. Soft-
     guardrails line — defended by the skill + cooperative model, not enforced.
6. **Requirement:** the skill must force a **flippable** declaration (a concrete
   corruptible value), or the brain has nothing to flip. The declaration also doubles
   as the auditable "here is exactly what I claim."

### Arm B — Manual (human-anchored test)

1. **Model authors the success test, summarizes what it does,** and asks the human to:
   - **(a)** manually sign off on the test,
   - **(b)** confirm the values of any UART/register reads the model deems important,
   - **(c)** with the option to request additional checks via the chat box.
2. **Only when the whole test is manually approved does the run continue.**
3. **Timing:**
   - **Upfront** (before the relevant work) for **specified** tasks — locking the test
     *before* the work **kills post-hoc rigging** (the model can't tailor a weak test
     to whatever it ends up producing);
   - **mid-run** (once the goal crystallizes) for **exploratory** tasks where the
     success criteria aren't knowable at turn 0.
4. **The human is the external anchor.** Confirming the important values pins **both**
   non-triviality **and relevance** (the human verifies the test checks the *right*
   thing) — so Arm B is the **high-assurance** option with **no soft relevance
   ceiling.**

### Anchor sources (so criteria are never model-invented)

Success criteria are always anchored to one of:

- **human** (Arm B),
- **manifest / spec / reference** (the benchmark and specified tasks — this is where
  the old green check's manifest-supplied expected symbol/UART values move),
- **model-declared element + brain-enforced flip** (Arm A — discrimination-anchored,
  relevance soft).

The model authors the **test**; it never invents the **criteria** unilaterally.

### Remove the old green check (explicit)

- **Delete `run_green_check`** (the fixed whole-board macro,
  [loop.py:712](../src/pyocd_debug_mcp/brain/loop.py#L712)) and the
  **`green_check_ok` finalize gate** ([loop.py:888](../src/pyocd_debug_mcp/brain/loop.py#L888)).
- Gate `finalize(healthy_confirmed | fixed)` on a **scoped success gate** (Arm A or B)
  instead.
- **Benchmark continuity:** the benchmark's manifest-supplied criteria (expected
  symbol/UART) become an **anchored scoped success test** — the manifest is the
  anchor, exactly like the human in Arm B — so removing the green check does **not**
  lose benchmark trustworthiness; it generalizes it. The whole-board check becomes one
  *anchored instance*, not the only mechanism.
- **Do not leave two success paths.** The green check is fully replaced.

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/loop.py`** — remove `_execute_green_check` + the
   `green_check_ok` gate; add the scoped success gate: run the model's test, enforce
   the declared-element flip (Arm A) or require human approval (Arm B).
2. **`src/pyocd_debug_mcp/brain/actions.py`** — replace the `run_green_check` action
   with a scoped-success action carrying the test + the **declared flippable element**
   (Arm A) or the human-approval handshake (Arm B); gate `fixed` / `healthy_confirmed`
   on it.
3. **Entry #13** — deliver the success-test rubric skill at done-time.
4. **Entries #9 / #11** — the model-authored gated test, plus the brain's
   mediated-read flip (re-run with the declared value corrupted).
5. **`src/pyocd_debug_mcp/brain/benchmark.py`** — migrate the manifest criteria to an
   anchored success test.
6. **`src/pyocd_debug_mcp/brain/cli.py`** — Arm B's human handshake (summarize test,
   confirm values, chat for extra checks).

### What it is supposed to do

- Verify **scoped** success (the function/feature) instead of the monolithic
  whole-board green check.
- Keep success honest **without preloading every test**: anchor the criteria (human /
  manifest / enforced-flip), and for the automated arm **hard-enforce discrimination**
  via the brain-run flip while **goading relevance** via the skill.

### Constraints / watch-outs

- **The asymmetry is the reason for all of this** — never let the model both define
  success *and* author the only passing test unanchored.
- **Arm A hard-enforces discrimination, soft on relevance; Arm B hard-anchors both.**
  Pick by assurance need.
- **Flippable declaration required (Arm A)** — a concrete corruptible value, or the
  brain can't enforce.
- **Upfront-lock for specified tasks (Arm B)** to kill post-hoc rigging; mid-run for
  exploratory.
- **Benchmark:** migrate manifest criteria to an anchored success test; don't lose the
  existing trust.
- **Remove the old green check entirely** — no dual success paths.
- **Doc-sync + verify on real hardware** — including a *rejected* non-discriminating
  test (the flip doesn't make it fail) and a *rejected* constant test.

### Status

Proposal only. Not yet specced, not yet implemented. Replaces the green-check success
mechanism; composes with entries #8 (failure verdicts), #9/#11 (gated model-authored
tests), and #13 (the done-time skill).

---

## 3. Inject skills as a cached index + on-demand bodies, not a full per-turn block

### Problem / current behavior

Skills are selected **once** at run start (`load_skills_for_context`,
[skills.py:131](../src/pyocd_debug_mcp/brain/skills.py#L131)) and rendered **once**
to text (`render_skills`, [skills.py:155](../src/pyocd_debug_mcp/brain/skills.py#L155)),
but that same full `skills_text` is spliced into **every** turn's prompt
([loop.py:1001](../src/pyocd_debug_mcp/brain/loop.py#L1001)). The entire payload —
`facts` / `diagnostic_hints` / `verification_checks` / `forbidden_actions` for
every matched skill — is re-paid on every iteration. In the re-serialization
loop that is wasted tokens and compute each turn; in a native session it is worse,
because re-injecting the same block mutates the conversation tail and **busts the
KV cache** the session was meant to preserve.

### What the change is

Split skill rendering by cost and criticality, and make the expensive part
on-demand:

- **Always-on, cheap (cached prefix):** a one-line skill **index**
  (`skill_id: title` per matched skill) plus the **safety-critical
  `forbidden_actions`** (`avoid:` lines,
  [skills.py:167](../src/pyocd_debug_mcp/brain/skills.py#L167)). Small, stable,
  lives in the cached prefix.
- **On-demand, expensive (model-pull):** the full `facts` / `diagnostic_hints` /
  `verification_checks` body, fetched via a new `load_skill(skill_id)` action
  (a brain tool / MCP-resource-style read). In native tool-use mode it is just
  another tool call whose result persists in the session afterward.
- **Per-turn nudge (cheap):** one line in the instructions telling the model
  which skills exist and that it can `load_skill` to pull detail when it judges
  it needs a reminder.

**Reject fixed-cadence reinjection** ("re-inject all skills every X turns"). It
pays the full skill cost on a timer regardless of need, and in a native session
each reinjection invalidates the cached prefix and re-bills the tokens. On-demand
pull strictly dominates it: the model pulls a body exactly when it wants one, and
the index keeps it aware that the option exists.

### Where it belongs

1. **`src/pyocd_debug_mcp/brain/skills.py`** — add `render_skill_index()`
   (id + title only) and `render_skill_safety()` (`forbidden_actions` only),
   distinct from the full `render_skills` (kept for the on-demand body and the
   deterministic mode). Add a `render_skill_body(skill_id)` for single-skill
   pulls.
2. **`src/pyocd_debug_mcp/brain/actions.py`** — add a `LoadSkillAction`
   (`kind="load_skill"`, `skill_id`) to `ActionUnion`, or expose the same as a
   native tool in session mode.
3. **`src/pyocd_debug_mcp/brain/loop.py`** — inject index + safety lines once
   (native session) or compactly per turn (deterministic mode); handle the
   `load_skill` action by returning the requested body; add the nudge in
   `_build_instructions` ([loop.py:168](../src/pyocd_debug_mcp/brain/loop.py#L168)).

### Native-session (API) note

Inject the skill index + safety lines once into the cached system/prefix (OpenAI:
part of the initial Responses input retained via `previous_response_id`;
Anthropic: a `cache_control`-marked block in the resent prefix). A pulled skill
body returns as a `tool_result` and then persists in the session context, so it
is never re-injected. This is exactly why fixed-cadence reinjection is doubly
wrong on API credits: it would both re-bill tokens and invalidate the cached
prefix that holds the index, safety lines, and tool definitions from entry #1.

### What it is supposed to do

- Stop re-billing the full skill corpus every turn; keep only a cheap index +
  safety lines always present.
- Let the model pull diagnostic detail exactly when it decides it needs it, while
  staying aware (via index + nudge) that skills are available.
- Preserve the KV cache (stable prefix for index/safety/tool-defs; bodies arrive
  as persistent tool results), and never gate safety guidance behind a retrieval
  the model might skip.

### Constraints / watch-outs

- **Safety lines are never on-demand-only.** `forbidden_actions` must always be
  in context; only the diagnostic/verification detail is pullable.
- **Selection stays deterministic.** `load_skills_for_context` is unchanged; only
  the rendering/injection cadence changes. `load_skill` must validate `skill_id`
  against the already-selected set so the model cannot pull arbitrary or
  out-of-scope skills. This is the same *curated-allowlist* discipline as entry
  #1's tool whitelist filtering — the model selects from a brain-curated set and
  may never name something outside it.
- **Doc-sync + verify.** Update the README turnkey section / R12 turnkey spec in
  the same unit of work, and re-run the suite before claiming it works.

### Status

Proposal only. Not yet specced, not yet implemented.

---

## 13. Skill-guided self-directed host work (A/B/C experiment)

### Problem / current behavior

The model's *board* interaction is skill-guided (entry #3), but its self-directed
*host* work (the entries #11/#12 free-reign) is **unguided** — it runs complex local
workflows (bug triage, test suites, writing a process) on its own with no structured
process knowledge. We already ship these process skills (the repo's
`fix-bug` / `test-suite` / `write-process` commands), so the gap is that the turnkey
model can't draw on them while working freely on the host.

### What the change is

Equip the model with skills for its self-directed host work — extend the entry #3
skill layer from board-decisions to host-workflows, **reusing the existing process
skills** (read-bug ≈ `fix-bug`, feature-test ≈ `test-suite`, write-process). Complex
actions (read bug, feature test, write process, …) are defined as skills; simple
actions (`cd`, `mkdir`, read file, write a line) need none.

This is an **experiment**: build the three delivery mechanisms below behind a switch
and measure before committing. **Always-on in every arm:** a skill **index** (id +
one-line description of each available process-skill) so the model is aware of what
exists — cheap recognition without round-trips.

### The three arms (how skills reach the model for complex workflows)

- **Arm A — model-pull (model-side recognition).** The model self-discerns it is in a
  complex workflow and pulls the skill (entry #3 `load_skill`); simple actions it just
  does. Lowest friction. Fails if the model doesn't recognize the workflow, or
  recognizes but doesn't pull. Simple actions free.
- **Arm B — brain-push on declared complex action (model-side recognition, guaranteed
  push).** The model recognizes a complex action and declares it to the brain; the
  brain pushes that action's skill subset; the model proceeds with it as context.
  Removes "recognized but didn't pull"; still fails if the model doesn't recognize.
  Simple actions free.
- **Arm C — brain-oracle on every action (brain-side recognition).** The user's
  explicit design:

  > We want the model to have larger, more complex actions; however, the model is
  > soft gated via the brain in ANY actions; if it recognizes an action, it is asked
  > to feed the action into the brain first; brain responds with the skill subset for
  > that action, then model continues using those skills as context. Forcing the model
  > to ask the brain before doing an action 1) forces it to recognize all available
  > actions, making it difficult to bypass, 2) force injects the skills into the
  > prompt for any complex action, rather than the model implementing that action end
  > to end without actually calling the model.

  The model surfaces **every** action to the brain; the brain classifies (returns the
  skill subset for complex actions, "Continue" for simple). **Recognition moves from
  the model to the brain.** Highest coverage, highest overhead.

### Why C is the distinct arm (not redundant)

A and B both depend on the **model** recognizing complex actions — they differ only
*pull vs push* after recognition. **C is the only arm that moves recognition to the
brain**, so it tests a different variable. Failure-mode ladder:

- **A** fails on (didn't-recognize) **or** (recognized-but-didn't-pull);
- **B** fixes the second; still fails on (didn't-recognize);
- **C** fixes both (recognition is brain-side) — fails only if the brain's
  action→skill mapping is wrong, or the model deliberately doesn't surface.

So C is strongest on **coverage** (the whole point of the feature). The redundant
pair is **A vs B**; **C is the one to keep.** The cleanest two-arm cut is A (model-
side, low overhead) vs C (brain-side, high coverage), with B as an optional middle.

### Honest notes on C's framing

- **"Difficult to bypass" is *soft*, not hard.** Per the
  [accepted stance](#accepted-design-stance-direct-hardware-access-is-not-sandboxed)
  the model has full sandbox access and could skip surfacing. C's real value is
  brain-side **recognition** (catching complex workflows the model wouldn't
  self-classify), not enforcement.
- **C re-involves the brain in host actions**, in tension with the #11/#12 north
  star. Acceptable **only** if implemented as a **fast in-context oracle** (the model
  calls a brain tool mid-turn; the brain returns "Continue"/skill immediately), **not**
  as a turn boundary (a full model inference per ask = prohibitive). Pin the cheap
  implementation.

### Cost control for C

- **Cheap oracle, not turn boundary** — the brain-side check is a dict lookup; the
  only cost is the model generating the ask + consuming the response, appended to
  context.
- **Tight loops go in scripts** — entry #9 model-native scripts run without per-line
  asks, so only top-level actions surface; this bounds the ask count.
- **(Optional) coarser-grain surfacing** — declare intent at the *workflow* grain
  ("about to start on this bug") rather than every atomic `cd`/`mkdir` — most of C's
  recognition benefit for a fraction of the asks.

### Measurement plan (it's an experiment — verify, don't assume)

Measure each arm on:

- **Coverage** — for each complex workflow, did the right skill get loaded? (C should
  win.)
- **Overhead** — added latency / tokens (C pays most; bounded as above).
- **Outcome quality** — did skill-guidance actually improve the host work vs.
  unguided?

Decide by coverage-vs-overhead: if C's coverage gain beats its overhead, C wins; if
B's model-side recognition is "good enough" at lower cost, B wins.

### Where it belongs

1. **`skills.py` / brain** — reuse the existing process skills
   (`fix-bug`/`test-suite`/`write-process`) as host-workflow skills; render an
   always-on index; implement the three delivery mechanisms behind a config/flag so
   the arms are switchable for the experiment.
2. **Arm C** — a fast in-context "consult" oracle the model calls before actions
   (returns skill subset or "Continue"); ensure it is not a turn boundary.
3. **Arms A/B** — `load_skill` (pull) and a declare-action push.

### Constraints / watch-outs

- **Reuse existing process skills, don't reinvent** (build-on-libraries rule).
- **Always-on index in all arms** (recognition without round-trips).
- **Simple actions stay free in A/B**; C surfaces everything but only complex actions
  get skills.
- **C's anti-bypass is soft** (accepted); its value is brain-side recognition.
- **Pin C's cheap-oracle implementation**; bound asks via scripts.
- **This is an A/B/C experiment** — measure coverage AND overhead before committing.
- **Doc-sync + verify.**

### Status

Proposal (experiment). Not yet specced, not yet implemented. Extends entry #3's skill
layer to the entries #11/#12 host-free-reign.

---

## 10. Projects: persistent client-side custom skills and tools

### Problem / current behavior

Everything the model learns or builds during a run is thrown away. Shipped skills
and the shipped vocabulary are global and fixed; entry #9 session tools are
ephemeral. There is no place for custom skills/tools that should **persist across
runs** for a recurring target (a specific board + firmware + bug-family the user
debugs repeatedly). Every session re-derives the same context from scratch.

### What the change is

Add a **project**: a persistent, client-stored context for a recurring target,
holding custom skills and custom (promoted) tools, that the CLI can reopen in a
later session. This completes a three-tier model:

- **Shipped (global):** built-in skills and predicate/tool vocabulary, audited,
  ships with FirmCLI.
- **Project (persistent, target-scoped):** custom skills and tools accumulated for
  one target, stored client-side on the user's device, reusable across runs.
  Project tools have two states — **candidate** (retained, available, not
  auto-loaded) and **active** (promoted, auto-loaded into future sessions).
- **Session (ephemeral only without a project):** entry #9 tools authored during a
  run. In a project they are **retained as candidates**, not discarded; only a
  project-less ad-hoc run discards them.

A project is like a session except it is stored in the client app's storage on the
user's device, so a later session can reopen it and see its accumulated skills and
tools.

Nothing useful is thrown away (every session tool in a project is kept as a
candidate), but not everything auto-loads (only promoted/active tools do) — this
is the reconciliation of "don't waste reusable work" with "don't auto-run
accumulating junk."

### Where the data lives (source of truth)

A **client-managed project store** — e.g. `~/.firmcli/projects/<project>/` with
`skills/` and `tools/` — is the source of truth, loaded and gated by the brain
exactly as shipped skills are. Explicitly **not** `.codex` / `.claude`:

- Skills here are **brain-injected, not model-discovered** (loaded and rendered by
  `load_skills_for_context`, [skills.py:131](../src/pyocd_debug_mcp/brain/skills.py#L131)),
  so the "model is trained on `.codex`" advantage does not apply.
- The turnkey providers use brain-owned runtime working directories and provider
  resume handles. Those directories are implementation detail, not the user's
  project customization store, so a `.codex`/`.claude` in a human repo is not
  the source of truth for turnkey skills or session tools.

If a provider-style view ever helps native tool-authoring, the brain may *generate*
a `.codex`/`AGENTS.md`-shaped mirror at runtime — a generated view, never the
store of record.

### Skills vs tools persist differently

- **Project skills** (knowledge) — hazard is staleness/conflict (see the repo's
  consistency/doc-sync rules). Require **precedence** (define whether shipped or
  project wins) and **validation against board facts** at load, so a stale project
  skill cannot silently contradict a shipped skill or the board config.
- **Project tools** (model-authored code that can persist and auto-load) — hazard
  is sharper: a script written in run 1 auto-executes in run 50. Resolved by the
  candidate/active split below: every session tool is **retained as a candidate**,
  but a tool **auto-loads only once it is promoted to active**, and promotion is
  **brain-computed from deterministic signals** — not a model-set flag and not (by
  default) a human review.

### Promotion: candidate -> active

A candidate tool auto-loads in future sessions only when it clears two hard
preconditions and then the usefulness threshold.

**Hard preconditions (deterministic, always required, brain-observed):**

- **Clean-run** — its latest version ran without error/timeout (the brain executes
  it, so it has this directly). Never auto-load a tool that errors.
- **Re-validates** — the brain re-runs the latest version against *current* ground
  truth and it still behaves. This guards the hardcoded-transient case, so a tool
  being **specific is not disqualifying** — if a specific tool keeps re-validating
  it can auto-load. (No separate "generalizes" check; re-validation subsumes it.)

**Usefulness threshold — latching useful-count >= 1.** Each invocation, the model
reports whether *that* use was useful via a typed `tool_feedback` field on its
`TurnDecision` (see below); the brain aggregates a `useful_count` per stable tool
identity. Promote when `useful_count >= 1`. This single metric:

- **handles the one-shot case** — a tool written once, useful that once, then the
  session ends → `useful_count = 1` → promote;
- **handles the high-volume / low-rate case** — useful 10% of 100 invocations is
  10 useful uses → promote (a **rate** would wrongly reject this, and a high
  **>= M count** would wrongly reject the one-shot — so it is neither);
- **is also the veto** — a tool the model *never* marked useful (`useful_count = 0`)
  does not promote, however clean or often-run. This is the "passed the proxies but
  was actually junk" filter, falling out of the same metric.

Usefulness is therefore **latching/monotonic**: once genuinely useful even once, a
tool is promotable; more useful uses only raise confidence/ranking and delay
pruning, they are not required.

**Durable vs provisional (bounding the softening).** Letting `tool_feedback` reach
the threshold means a model-asserted "useful" can promote — a mild softening of the
earlier *veto-only* framing. The blast radius is bounded because the hard
preconditions still hold (it at least runs and re-validates), so the worst case is
harmless clutter, not danger. To self-correct it, split promotion:

- **durable** — backed by behavioral evidence the brain observes directly: *reused*
  (invoked >= N times, counted by stable identity so the count survives edits) or
  *consumed* (output flowed into a brain-mediated mechanism — an entry #8 gate
  predicate, green-check/finalize inputs, or a dependent batch step; note "the
  model used it in its reasoning" is **not** brain-observable and does not count).
- **provisional** — promoted on `useful_count >= 1` alone, no behavioral evidence
  yet. Auto-loads but on a **short leash**: if not actually reused within K later
  sessions, it is demoted/pruned. A genuinely useful one-shot gets reused and
  graduates to durable; a falsely-claimed one evaporates.

So *reused* / *consumed* shift from hard gates to **durability / confidence /
ranking** signals; `useful_count >= 1` (over the two hard preconditions) is the
promotion threshold.

**The `tool_feedback` field.** The model does not attach a loose variable for the
brain to scrape from prose — it fills an optional typed field on the already-parsed
`TurnDecision` (entry #2), e.g. `tool_feedback: { tool_id, useful: bool, note }`,
on the turn after it used a tool. The model may also supply **metadata**
(description, intended scope, ground truth needed) as helpful input. The model
**proposes/reports**; the brain still computes the promotion verdict and owns the
preconditions — consistent with the entry #8 rule that the model never sets the
gate flag directly.

**Storage stays bounded:** durable tools persist; provisional and unused candidates
are prunable (LRU/TTL — drop candidates never reused after N sessions, demote
provisional tools not reused within K sessions). Good capability accumulates
without unbounded junk.

### CLI surface

Projects are first-class in the CLI, with visible storage and explicit deletion:

- `pyocd-debug-brain project list` — list projects **with their memory/storage
  usage** (disk size of each project's `skills/` + `tools/`).
- `pyocd-debug-brain project show <name>` — what skills/tools the project holds,
  including each tool's state (**candidate** vs **active**) and reuse count.
- `pyocd-debug-brain run --project <name> ...` — run inside a project (its skills
  and tools load on top of shipped).
- `pyocd-debug-brain project delete <name>` — **delete that client's project
  folder** (its skills + tools) to free up space. Destructive and irreversible
  for that project's custom artifacts; confirm before deleting.

### Where it belongs

1. **Client store** — a project-store module that creates/lists/loads/deletes
   `~/.firmcli/projects/<project>/{skills,tools}/` and reports sizes.
2. **`src/pyocd_debug_mcp/brain/cli.py`** — a `project` subcommand group
   (`list` / `show` / `delete`) and a `--project` option on `run`, alongside the
   existing `run` / `benchmark` subcommands.
3. **`src/pyocd_debug_mcp/brain/skills.py`** — load project skills with the
   shipped ones, applying precedence + validation.
4. **Promotion path** — retain entry #9 session tools as project **candidates**;
   compute candidate -> active promotion (preconditions clean-run + re-validates,
   then latching `useful_count >= 1` from `tool_feedback`), tag durable vs
   provisional, and prune (LRU/TTL for candidates, short leash for provisional).

### What it is supposed to do

- Give the turnkey CLI a stateful, per-target memory: custom skills and promoted
  tools that persist and reload across runs, so recurring debugging gets faster
  over time instead of restarting cold.
- Keep that persistence honest and manageable: brain-loaded and gated like shipped
  skills, with precedence/validation for skills and candidate -> active promotion
  (clean-run + re-validates preconditions, then latching `useful_count >= 1`, with
  durable vs provisional tiers) for tools.
- Let the user see and reclaim storage: list projects with their footprint and
  delete a project's folder to free space.

### Constraints / watch-outs

- **Brain owns preconditions + verdict; model only reports usefulness.** Clean-run
  and re-validates are hard, brain-observed preconditions. The model reports
  per-use usefulness via the typed `tool_feedback` field, but the brain computes
  the verdict and aggregates `useful_count` — the model never sets the promotion
  flag, consistent with the entry #8 rule.
- **Latching useful-count, not a rate or a high count.** Promote at
  `useful_count >= 1` (honors both the one-shot and high-volume/low-rate cases);
  `useful_count = 0` is the veto.
- **Durable vs provisional.** Behavioral evidence (reused/consumed) = durable;
  model-asserted one-shot = provisional, demoted/pruned if not reused within K
  sessions. Bounds the mild self-certification of letting `tool_feedback` promote.
- **Retain candidates, prune by use.** Session tools in a project are kept as
  candidates (nothing useful discarded); unused candidates are pruned by LRU/TTL so
  storage stays bounded.
- **Precedence + validation for skills** so persisted knowledge can't silently
  override shipped skills or board facts.
- **`.codex`/`.claude` is not the store of record** — client project store is;
  any provider-folder view is a generated mirror.
- **Delete is destructive.** `project delete` removes custom skills/tools for that
  project permanently; confirm, and never touch shipped/global assets.
- **Doc-sync + verify.** Document the project model and exercise create → run →
  promote → list (with size) → delete before claiming it works.

### Status

Proposal only. Not yet specced, not yet implemented. Extends entry #3 (skills) and
entry #9 (session tools) as the persistence tier between shipped and session.

---

## 4. (Optional) Switch the output format to provider-native tool calls

### Problem / current behavior

The model closes a turn by returning a `TurnDecision` JSON object whose governed
`action` field is a discriminated union
([actions.py:74](../src/pyocd_debug_mcp/brain/actions.py#L74)), which the brain
parses (`parse_turn_decision_json`) and dispatches. This is **independent of the
session/memory work in entry #2** — entry #2 keeps this JSON return for the final
governed/terminal decision and only changes how turns are delivered (one
persistent session vs. cold re-prompts). This entry is the *separate* question of
whether to change the output **format** itself.

The current free-form-JSON contract works and is provider-agnostic, but the model
is emitting a schema by hand rather than using the function-calling mechanism the
providers are specifically trained on.

### What the change is

Replace the `TurnDecision` JSON return with the provider's **native tool/function
calls**: the whitelisted tools (`AllowedServerToolName`) are registered in the
provider's native `tools` parameter, the model emits real `tool_use` calls, and
the brain intercepts each call, runs it through the same `_execute_server_tool`
gate, and appends a native `tool_result`.

The logical governed action set is unchanged — `connect`, `flash_firmware`,
`run_script`, `run_build`, firmware-deliverable edits, `run_green_check`,
`finalize`, terminal decisions, etc. become provider-native calls. Model-native
host work stays outside this tool surface. The brain's guardrails, ledger, and
`BrainState` are untouched in spirit; only the wire format of "what the model said
to do at the governed boundary" changes.

### Why it is optional (and the trade-off)

- **For:** providers are heavily trained/RLHF'd on their native tool-call format,
  so well-formed calls can be more reliable than free-form JSON-schema adherence;
  tool definitions live in the native `tools` param and are cached there (pairs
  with entry #1's API delivery).
- **Against:** it gives up the clean, provider-agnostic `TurnDecision` contract —
  each provider's tool-call schema and surface differ, so the parsing/dispatch
  layer forks per provider. Acceptable only because we are not optimizing for
  provider symmetry; still a real cost in code surface.
- **Not a memory or caching win.** Those come entirely from entry #2's persistent
  session. This entry buys *call reliability/ergonomics*, nothing more, which is
  why it is sequenced last and marked optional.
- **Not needed for code-mode script bodies (entry #9 uses Design 2).** Entry #9
  authors scripts by *native file-writing* (no structured-action capture of the
  body), so there is no script-body format tax to fix and native tool-calling is
  **not** required for it. This entry stays a general reliability option for the
  *decisions* (`run_script` etc.), which carry only short names. See entry #9's
  "Format tax" section.

### Where it belongs

1. **The four providers** — add a native-tool-call path that surfaces the
   whitelisted tools via the provider `tools` parameter and parses `tool_use`
   responses, behind the same `DecisionProvider` boundary.
2. **`src/pyocd_debug_mcp/brain/loop.py`** — accept a native tool call as an
   alternative to a parsed `TurnDecision.action`, mapping it onto the same
   dispatch in `_execute_server_tool`. Keep the JSON-return path as the default /
   deterministic path.
3. **`src/pyocd_debug_mcp/brain/actions.py`** — the existing action models become
   the schema source for the native tool definitions, so there is one source of
   truth for both formats.

### What it is supposed to do

- Improve well-formed-call reliability by using the providers' first-class
  tool-calling, without changing the agent's logical capabilities or guardrails.

### Constraints / watch-outs

- **Sequence after #2.** Do not conflate with the session work; land #2 (JSON
  return + session) first, then evaluate whether the reliability gain justifies
  the per-provider fork.
- **Whitelist + scoping unchanged.** Native tools still expose only
  `AllowedServerToolName`, same discipline as entry #1's filtering and entry #3's
  `load_skill` scoping.
- **Keep a JSON-return mode.** The deterministic CI path stays on the
  provider-agnostic `TurnDecision` return for reproducibility.

### Status

Proposal only. Not yet specced, not yet implemented. Decoupled from entry #2,
which keeps the `TurnDecision` JSON return.

---
