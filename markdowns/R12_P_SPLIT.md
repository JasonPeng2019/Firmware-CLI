# R12 P-Split Parallel Work Plan

Read things-to-change for scope of the modules.

## Purpose

This file defines the parallel branch schedule for the `R12` prototype.

The goal is not to make the code unusual. Each branch should use normal,
concrete Python modules, dataclasses/Pydantic models only where they fit, and
plain helper functions. The point is to keep three parallel branches from all
rewriting the same orchestration files.

Rule of thumb:

- Wave 0 is the clean integration trunk for this prototype
- steps inside one branch are serial
- branches inside one wave are parallel
- every branch starts from the current Wave 0 branch
- every finished wave merges back into Wave 0 before the next wave starts
- the next wave starts only after the prior wave's required dependencies land
- broad edits to `brain/loop.py`, `brain/actions.py`, `brain/cli.py`, and
  `server.py` are serialized integration work

## Simple Schedule

```text
SERIAL:
  Wave 0 clean slate / P0.0 validation:
    fix current dirty repo issues
    self-diagnose current repo with extensive tests
    prove on real STM32 + Nordic boards

SERIAL:
  P0 foundation

PARALLEL WAVE 1:
  Branch A: provider session + tool schema prompt
  Branch B: action boundary + batches + client actions
  Branch C: event spine + timeout policy

SERIAL:
  merge A + B + C back into Wave 0

PARALLEL WAVE 2:
  Branch D: progress UI + inspector
  Branch E: stream checkpoints
  Branch F: scoped green approval
  Branch G: static context efficiency + cache-assisted reuse

SERIAL:
  merge D + E + F + G back into Wave 0

SERIAL:
  Final integration + acceptance cleanup
```

## Wave 0 Clean Slate / P0.0 Validation - Serial First

Wave 0 is the integration trunk for this prototype. It must be made clean before
`P0` starts.

Purpose:
do not build the new prototype on top of unknown dirty-state failures. First fix
the issues currently present in the repo, then self-diagnose the resulting state
with extensive non-hardware and hardware testing.

For this prototype, Wave 0 uses a narrower proof boundary:

- required now: current validated host + Codex-backed turnkey baseline on the
  scoped pair;
- deferred accepted risk: second-provider full reproof and true fresh-machine
  portability proof.

Wave 0 owns:

0. `P0.0` layered validation
   - use `markdowns/curr/p0_0_layered_validation_plan.md` as the execution
     checklist for Wave 0 cleanup and proof
   - write the resulting pass/fail matrix to
     `markdowns/curr/p0_0_validation_report.md`
1. Current dirty-code cleanup
   - reconcile existing uncommitted/code changes against the build plan and docs
   - fix known broken tests or runtime regressions before adding new prototype
     features
   - remove or finish half-landed changes so the next branches start from a
     coherent baseline
2. Non-hardware self-diagnosis
   - run the unit/type/lint/benchmark checks appropriate for the current repo
     state
   - investigate failures until they are understood, fixed, or explicitly
     documented as pending hardware
3. Real-board validation
   - validate the clean baseline against the scoped STM32 board
     (`nucleo_l476rg`)
   - validate the clean baseline against the scoped Nordic board
     (`nrf52833dk`)
   - record exact commands, outputs, and remaining hardware caveats
4. Deferred-proof bookkeeping
   - explicitly record second-provider and fresh-machine portability as
     unverified accepted prototype risk
   - do not block `P0` on those deferred items unless the team later chooses to
     restore them as hard gates

Wave 0 exit criteria:

- the worktree baseline for prototype work is intentionally clean or has only
  documented, non-blocking changes
- `markdowns/curr/p0_0_validation_report.md` exists and records the executed
  layers, elapsed times, artifacts, and remaining risks
- non-hardware checks have been run and recorded
- real STM32 and Nordic board checks have been run by a human/operator and
  recorded, or the missing hardware proof is explicitly marked as blocking
- the team agrees this is the branch all later prototype branches start from
- deferred second-provider and fresh-machine portability items are recorded as
  unverified accepted prototype risk, not silently assumed working

Wave 0 is not a feature branch. It is the baseline that later branches merge
back into.

## P0 Foundation - Serial First

`P0` starts from the clean Wave 0 branch and lands back into Wave 0 before any
long-lived parallel branch starts.

Purpose:
create the smallest concrete shared shapes and hook points so later branches do
not all edit `loop.py` and `actions.py` differently.

Modules:

1. `src/pyocd_debug_mcp/brain/decision_types.py`
   - final board decision shape
   - `ActionCall`
   - `ActionBatch`
   - early-exit verdicts
   - timeout proposal fields
   - iteration estimate fields
2. `src/pyocd_debug_mcp/brain/events.py`
   - `BrainEvent`
   - event kinds
   - simple event sink/callback shape
3. `src/pyocd_debug_mcp/brain/provider_types.py`
   - provider response shape
   - provider session state fields
4. `src/pyocd_debug_mcp/timeouts.py`
   - shared timeout config/update shape if the existing file does not already
     cover it
5. `src/pyocd_debug_mcp/brain/client_actions.py`
   - empty/minimal client-action store shape only
6. Tiny hook points in:
   - `brain/loop.py`
   - `brain/actions.py`
   - `brain/cli.py`

P0 should not implement the full features. It should preserve current behavior
and add tests for parsing/serialization and no-op hooks.

Active implementation docs for this step:

- `markdowns/curr/p0_foundation_spec.md`
- `markdowns/curr/p0_foundation_process.md`

## Wave 1 - Three Parallel Branches

After `P0` lands back into Wave 0, Branch A, Branch B, and Branch C branch from
Wave 0 and run in parallel.

### Branch A - Provider Session + Tool Schema Prompt

Branch A owns provider session continuity where the provider surface makes that
possible, plus the model-facing tool schema prompt. It should not overclaim
"one native provider session" for every provider:

- API-backed providers should use native/session-capable continuation where
  available, such as OpenAI Responses `previous_response_id`;
- Anthropic API-style continuity may be client-owned history that is resent each
  turn, because that is the provider's session model;
- CLI providers may use persisted CLI resume handles as the current bridge;
- the final robust Codex/Claude integrations should use provider-specific
  programmable session APIs behind the same brain-owned provider adapter
  protocol;
- do not call a CLI transcript/local-memory fallback a true native persistent
  provider session unless the provider CLI actually resumes the same session.

Tool schema forwarding in this branch means a curated model-facing schema bundle
for the allowed server-native tools. It does not expose raw MCP handles, internal
brain/admin tools, or every MCP server function. Branch A keeps the current
`TurnDecision` JSON contract; provider-native tool calls remain a later optional
change, not part of this branch.

Serial order inside Branch A:

1. `provider_types.py`
   - finalize provider session fields from `P0`
2. Provider adapters:
   - `provider_openai.py`
   - `provider_anthropic.py`
   - `provider_codex_cli.py`
   - `provider_claude_cli.py`
   - `provider_factory.py`
3. `tool_schemas.py`
   - read real MCP tool descriptions/schemas
   - render the model-facing prompt bundle
4. Small integration hook:
   - `loop.py` consumes provider session state and schema bundle through the
     `P0` hook

Parallel with:

- Branch B module 1 through module 4
- Branch C module 1 through module 4

Should not own:

- action execution
- timeout clamp rules
- raw MCP server tool exposure
- provider-native tool-call output format
- event spine or progress UI ownership
- CLI progress rendering

### Branch B - Action Boundary + Batches + Client Actions

Branch B is a turnkey brain/client branch, not a general MCP-server expansion.
It must preserve the closed-server boundary:

- the MCP server remains the board-control surface with deterministic
  guardrails;
- host-only model work stays model-native and is not converted into governed
  brain actions;
- every board/server-native action still routes through the brain gate, whether
  it is direct, batched, or called by a client action.

Serial order inside Branch B:

1. `action_policy.py`
   - classify model-native host actions vs governed server-native actions
2. `host_actions.py`
   - support and audit model-native host work at the decision boundary
   - do not make ordinary host file/shell/script authoring a governed action
   - do not add general host command/file execution to the MCP server
3. `action_batch.py`
   - ordered action batches
   - batch result aggregation
   - batch-level failure behavior
4. Basic action additions:
   - `wait` as a bounded brain-local delay
   - UART write as real hardware I/O
   - for UART write, update the adapter/service/MCP tool/brain allowlist stack;
     do not treat it as only a small `server.py` wrapper
5. `client_actions.py`
   - client (NOT codex session) session-scoped script/tool store
   - native script authoring target; script bodies are not embedded in
     `TurnDecision`
   - governed `run_script(name, inputs)` execution for scripts that touch
     server-native tools
   - snapshot/hash the script version that actually runs
   - inject the gated server-tool API only during governed `run_script`
     execution
   - route every server-native call back through the same brain gate used by
     direct server-tool actions

Parallel with:

- Branch A module 1 through module 4
- Branch C module 1 through module 4

Cross-branch dependency:

- Branch B module 3 may consume Branch A's schema shape only after `P0`; it
  should not wait for Branch A's full implementation.
- Branch B module 5 is needed by Wave 2 Branch E and Branch F.

Should not own:

- provider sessions
- inspector rendering
- timeout default/clamp rules
- broad MCP-server host execution
- raw hardware access from client scripts

### Branch C - Event Spine + Timeout Policy

Branch C owns the normalized brain event spine and timeout policy. It must make
timeout state session/client scoped now, not process-global prototype state:

- timeout proposals, clamps, effective budgets, and pending server-sync values
  live with the current turnkey brain/client session;
- server timeout sync is brain-only/internal and must not appear in the
  model-facing tool schema bundle;
- server timeout updates are partial updates for subsequent operations, not
  mutation of config files and not a promise to interrupt already-running
  pyOCD/vendor calls;
- bounded outer waits are still not true cancellation for in-process vendor
  calls. A killable worker/job layer remains out of scope for this branch.

Branch C defines event kinds, sinks, timeout clamps, and timeout propagation
hooks. Branch D renders those events, Branch E owns checkpoint continue/cancel
decisions, and Branch B applies batch timeout behavior during batch execution.

Serial order inside Branch C:

1. `events.py`
   - finish event kinds from `P0`
   - event sink helpers
2. `timeout_policy.py`
   - parse model timeout/iteration proposals
   - apply brain clamps
   - build server timeout-sync requests
3. `src/pyocd_debug_mcp/timeouts.py`
   - shared defaults and clamp ranges
   - no competing timeout source
   - session/client-scoped effective timeout state
4. Timeout consumption hooks:
   - providers consume provider timeout values
   - tool calls consume action timeout values
   - server timeout sync uses partial updates

Parallel with:

- Branch A module 1 through module 4
- Branch B module 1 through module 5

Cross-branch dependency:

- Branch C module 4 may touch provider adapters after Branch A's provider
  session fields are stable. If that would conflict, split it into a tiny
  integration patch after Branch A lands.
- Branch C module 1 and module 2 are required by Wave 2 Branch D and Branch E.

Should not own:

- batch semantics
- client-action execution
- checkpoint continue/cancel decisions
- inspector UI
- provider adapter rewrites beyond the stable timeout-consumption hook
- model-facing timeout admin tools

## Wave 2 - Parallel Branches

Wave 2 starts only after Branch A, Branch B, and Branch C have each merged back
into Wave 0 and the merged Wave 0 branch has passed the agreed checks.

Branch D, Branch E, Branch F, and Branch G then branch from the updated Wave 0
branch and run in parallel.

- Branch D needs Branch C module 1.
- Branch E needs Branch B module 5 and Branch C module 1/module 2.
- Branch F needs Branch B module 5 if green tests use client actions.
- Branch G needs Branch A prompt/session metadata and Branch C event shapes if
  cache-reuse events are emitted.

### Branch D - Progress UI + Inspector

Serial order inside Branch D:

1. `cli_progress.py`
   - render live progress from `BrainEvent`
2. `inspector.py`
   - write prompt turns, provider stream text, parsed decisions, tool calls,
     server observations, and state snapshots
3. CLI hook:
   - `cli.py` exposes progress/inspector flags through a small integration edit

Parallel with:

- Branch E module 1 through module 4
- Branch F module 1 through module 3
- Branch G module 1 through module 5

Should not own:

- event shape redesign
- timeout clamp rules
- action execution semantics
- proof escalation policy
- static-context rendering, skill body loading, or cache key/reuse semantics

### Branch E - Stream Checkpoints

Serial order inside Branch E:

1. `stream_checkpoints.py`
   - checkpoint records
   - continue/cancel verdict
   - stall policy
2. Build/external-command chunking:
   - `workspace.py`
3. UART read chunking:
   - UART read path emits chunks and observes cancellation
4. Client-action chunking:
   - `client_actions.py` emits chunks and observes cancellation

Parallel with:

- Branch D module 1 through module 3
- Branch F module 1 through module 3
- Branch G module 1 through module 5

Cross-branch dependency:

- Branch E module 4 depends on Branch B module 5.
- Branch E uses Branch C timeout/event shapes, but does not own them.

Should not own:

- pyOCD flash/connect/recover worker design
- green approval logic
- static-context rendering, skill body loading, cache-assisted build/workspace
  reuse
- proof escalation policy

### Branch F - Scoped Green Approval

Serial order inside Branch F:

1. `green_approval.py`
   - manual/human-confirmed model-made test flow
2. Narrow flipped-value gate:
   - model supplies script, parameters, correct values, flipped values
   - brain accepts pass-correct/fail-flipped only
3. Evidence/result capture:
   - use existing state/evidence helpers
4. Proof escalation policy:
   - `proof_ladder.py`
   - records the proof rung reached, why the next rung is required/skipped/pending,
     and which expensive live proof remains
   - integrates with spec/review/test-suite reports, not provider/session runtime

Parallel with:

- Branch D module 1 through module 3
- Branch E module 1 through module 4
- Branch G module 1 through module 5

Cross-branch dependency:

- If green tests run as client actions, Branch F module 1 waits for Branch B
  module 5.

Should not own:

- provider sessions
- server tools
- general benchmark scoring outside the narrow prototype gate
- static-context rendering, skill body loading, cache keys, or cache-assisted
  reuse

### Branch G - Static Context Efficiency + Cache-Assisted Reuse

Branch G exists only to keep static-context efficiency and cache/reuse additive
and parallelizable. It owns skill-index rendering, on-demand skill bodies, and
cache-assisted setup reuse because those all touch prompt/static-context assembly.
It must not spread cache or skill-rendering policy into D/E/F-owned modules
during the parallel wave.

Serial order inside Branch G:

1. `skills.py` static-context split
   - render selected-skill index and always-on safety lines
   - render one selected skill body on demand
   - keep safety lines always present; only diagnostic bodies are pullable
   - validate requested skill IDs against the already-selected set
2. `artifact_cache.py`
   - content-addressed cache record schema
   - source/workspace hash, build-command fingerprint, toolchain fingerprint
   - firmware artifact hash, board/probe identity fields
   - prompt/tool/skill render hash fields
   - provenance links back to original run artifacts
3. Cache artifact writer/reader tests:
   - deterministic JSON ordering
   - conservative invalidation keys
   - portable repo-relative artifact references where possible
4. Reuse event/report records:
   - cache hit/miss/skipped reason events
   - report fields stating whether final live proof still ran
5. Small prompt/CLI hooks:
   - expose `load_skill(skill_id)` or equivalent on-demand body retrieval through
     the turn-closing decision/native-tool path selected by the branch spec
   - keep hooks minimal; broad prompt assembly rewrites move to final wiring

Parallel with:

- Branch D module 1 through module 3
- Branch E module 1 through module 4
- Branch F module 1 through module 4

Cross-branch dependency:

- Branch G may consume Branch C event shapes, but it must not redesign them.
- Branch G may read Branch A prompt/session metadata, but it must not change
  provider session semantics.
- Branch G must not change provider-memory semantics; the prototype relies on
  the existing compact memory ledger plus configurable native sync.

Should not own:

- workspace build chunking or cancellation, owned by Branch E
- progress/inspector UI rendering, owned by Branch D
- scoped green approval semantics, owned by Branch F
- final hardware proof replacement; cache reuse can skip setup/non-final repeats
  but cannot replace required live final verification
- broad edits to `loop.py`, `workspace.py`, `cli.py`, or `actions.py`; only small
  hooks are allowed, and if they conflict with D/E/F they move to final wiring
- project-level persistent custom tools/skills, owned by later MVP entry #10
- skill-guided host-work A/B/C experiments, owned by later MVP entry #13
- provider-memory semantics, owned by Branch A and final integration if needed

## Final Integration - Serial Last

After Branch D, Branch E, Branch F, and Branch G have each merged back into Wave
0 and the merged Wave 0 branch has passed the agreed checks, do one short serial
integration branch.

Owns:

- final wiring in `brain/loop.py`
- final wiring in `brain/actions.py`
- final wiring in `brain/cli.py`
- final server wrapper cleanup in `server.py`
- wiring already-implemented proof-ladder and artifact-cache hooks where the
  shared integration files would otherwise create parallel-branch conflicts
- acceptance tests/docs cleanup

Rules:

- no feature should first be implemented in this branch
- this branch wires already-owned modules together
- any broad rewrite here means a prior branch split was wrong

## Shared Files Rule

These files are shared integration points:

- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/cli.py`
- `src/pyocd_debug_mcp/server.py`

During Wave 1 and Wave 2, a branch may touch those files only for a small hook
to its owned module. Broad edits to these files happen in `P0` or `G`, not in
parallel branches.

## Merge-Back Rule

Wave 0 is the only branch that continues across the whole prototype.

When Wave 0 changes during an active parallel wave, fan that change out to every
active branch in the wave before new feature work continues. Do this one target
branch at a time:

1. merge `P-Wave-0` into the target branch;
2. resolve any conflict on that target branch;
3. run the agreed checks for that branch;
4. push the target branch;
5. continue to the next target branch.

Do not auto-resolve conflicts across all targets. Conflict resolution and checks
stay serial even when the fan-out is scripted.

Merge sequence:

1. Clean/fix/test current repo state on Wave 0.
2. Branch `P0` from Wave 0.
3. Merge `P0` back into Wave 0.
4. Branch A, B, and C from Wave 0.
5. Merge A, B, and C back into Wave 0 one at a time, running checks after each
   merge.
6. Branch D, E, F, and G from the updated Wave 0.
7. Merge D, E, F, and G back into Wave 0 one at a time, running checks after
   each merge.
8. Branch `Final` from Wave 0.
9. Merge `Final` back into Wave 0 after final acceptance cleanup.

This lets the people or branch slots used for A/B/C be repurposed for D/E/F/G
without carrying stale branch state forward.

## Conflict Escalation Rule

If a branch cannot proceed without broad edits to another branch's owned module
or to a shared integration file, stop and update this plan before coding
further. That means the dependency is serial and should be moved into `P0`,
into the other branch, or into final integration.

## Verified

- This file is a coordination plan only.
- It is aligned with the current `R12` prototype target in the build plan and
  roadmap.
- Branch A now scopes persistent sessions to "where available": native/session
  continuation for providers that support it, client-owned history where that is
  the provider model, and explicitly labeled fallback behavior for CLI providers.
- Branch B now explicitly preserves the closed-server boundary: model-native
  host work stays outside governed actions, board/server-native work stays
  gated, and UART write is treated as hardware-stack work.
- Branch C now explicitly requires session/client-scoped timeout state and keeps
  brain-only timeout sync out of the model-facing tool surface.

## Pending Verification

- Wave 0 now has an executed `P0.0` validation report in
  `markdowns/curr/p0_0_validation_report.md`, including real proof on the
  attached `nrf52840dk + nucleo_l476rg` pair and the merged `P-Wave-0` branch.
- If the team wants the prototype gate tied back to the exact official scoped
  pair, a fresh `nrf52833dk + nucleo_l476rg` re-proof remains a separate
  follow-on evidence task.
- Second-provider and fresh-machine portability proof remain intentionally
  deferred outside the Wave 0 gate and must not be claimed as verified.
- The exact module names should be checked against implementation reality when
  `P0` starts.
- No code behavior has been changed by this document.
- Branch A is now implemented on `P-Wave-A` through provider session state,
  CLI resume handles, OpenAI Responses continuation, tool-schema forwarding,
  and provider progress events. Remaining Branch A hardening is final-provider
  integration quality: Codex SDK/app-server thread APIs, Claude Agent SDK
  sessions, and strict no-silent-fresh-session policy for modes that promise one
  continuous provider session. Strict policy means resume failure stops headless
  runs by default, while the interactive shell must ask before retrying or
  starting a new provider session from saved local memory.
- Branch B behavior has now been merged onto `P-Wave-A` as additive action
  surface: action-boundary behavior, ordered batches, bounded `wait`, UART
  write, and session-scoped client actions. It does not own provider-session
  continuity, timeout policy ownership, inspector/progress rendering, stream
  checkpoints, scoped green approval, or provider-native tool-call conversion.
- Branch B attached-board deployment proof exists on the Branch B side for
  `nucleo_l476rg + nrf52840dk`, including real Codex, the real MCP subprocess,
  public `--client-action` registration, workspace edit/build runs, and
  repeated user-prompt / multi-loop runs. Exact official `nrf52833dk` Branch B
  deployment proof remains pending because the Nordic board attached during the
  Branch B completion pass identified as `nrf52840dk` / `NRF52840_xxAA_REV2`,
  a retained alternate profile rather than the official scoped Nordic board.
- Branch C behavior remains unimplemented here; session/client-scoped timeout
  state and brain-only server timeout sync still need code and tests.
