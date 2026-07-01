# R12 P-Split Parallel Work Plan

Read `markdowns/things-to-change.md` for scope of the modules. Its Prototype
Priority list is the hard acceptance bar; this file only schedules that work.

## Purpose

This file defines the parallel branch schedule for the `R12` prototype.

Status correction, 2026-06-30: the old D/E/F/G/H git branches have been deleted
locally and remotely. Their requirement content remains prototype-required, but
the branch objects are gone and must not be referenced as active work. Branch B's
strict free-host-work phase and final governed board/terminal decision boundary
has a new hard-bar correction: the old governed host-action compatibility layer
must be removed, not merely schema-hidden or refused. `read_file`,
`replace_file`, and `run_build` are no longer valid `TurnDecision` actions in
any branch/module. The model-native `load_skills` context-expansion decision is
now part of the current prototype scope, and the R12 scaffold hardening has
landed so compact indexes are discovery-only until details are loaded. Full
closure still requires live API-provider proof, exact official `nrf52833dk`
proof, fresh-machine proof, and the remaining Wave 2 modules.
Credentials-free OpenAI/Anthropic API-path simulation is now part of the Wave 1
hard bar and is green through the real provider factory/turnkey-loop code
paths. Claude CLI is now attached-board proven again on the current
`nucleo_l476rg + nrf52840dk` rig, but that retained-Nordic proof does not
replace exact official-pair proof on `nrf52833dk + nucleo_l476rg`.

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
- broad edits to `src/pyocd_debug_mcp/brain/loop.py`,
  `src/pyocd_debug_mcp/brain/actions.py`,
  `src/pyocd_debug_mcp/brain/cli.py`, and `src/pyocd_debug_mcp/server.py` are
  serialized integration work
- no branch, wave, or validation report is complete unless every relevant
  `things-to-change.md` prototype-priority item is mapped to code, tests, and
  run evidence

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
  Branch A: provider session + compact tool-index prompt
  Branch B: action boundary + batches + client actions
  Branch C: event spine + timeout policy

SERIAL:
  merge A + B + C back into Wave 0

WAVE 2 HARD-BAR WORK, NOT CURRENT GIT BRANCHES:
  Module D: progress UI + inspector
  Module E: stream checkpoints
  Module F: scoped green approval
  Module G: static context efficiency + cache-assisted reuse + codebase map
  Module H: process-tree + board-session cleanup guard

SERIAL:
  merge the rebuilt Wave 2 hard-bar work back into Wave 0

SERIAL:
  Final integration + acceptance cleanup
```

Current integration note, 2026-06-30: Wave 1 A and C are acceptable for their
prototype slices, and Branch B's free-host/final-governed-decision code boundary
has now been corrected. Codex CLI proof on `nucleo_l476rg + nrf52840dk` is real
attached-board evidence, and a later auth-restored Claude CLI Branch C rerun is
also green on that attached pair. Those attached-board rows do not replace exact
official `nrf52833dk`, API-provider parity, or fresh-machine proof.
Wave 2 Module G now also includes the codebase-map specification in
`markdowns/curr/wave2-codebase-map_spec.md`; that feature is planning-only until
implemented and validated on a rebuilt Wave 2 branch/module pass. The
provider-visible mid-tool checkpoint-buffer design for Wave 2 Module E is now
specified in `markdowns/curr/wave2-midtool-checkpoints_spec.md`; it is also
planning-only until implemented. Module E must treat checkpointing as a generic
brain-mediated observation buffer for UART/build/client-action streams, not as a
special board-presence poller or raw provider access to server tools.
The prerequisite scaffold hardening at
`markdowns/curr/r12-context-scaffold-hardening_spec.md` has landed:
product/client-owned model-native skills rather than `.codex/skills`,
runtime-copy-only skill repair, structured skill-load failures,
`load_tool_details`, strict loaded-detail guardrails before governed
tool/script or brain-owned compound-action execution, invalid-tool-call
auto-details, canonical ordering/dedupe for existing prompt surfaces, failure
classification, and prompt bundle alias cleanup.
The loader-specific launch risk is not the current Wave 1 design; it is drift in
packaging/config. A deployable package must keep the product skill root
client-owned, never default it back to `.codex/skills` or `.claude/skills`, copy
skills into per-session runtime directories before init/context, keep installed
skill source read-only, and retain init-script preflight against raw
probe/serial imports or board/probe shell commands.
Prompt/memory cost hardening now belongs to the Wave 1 integration substrate,
not to a future cross-invocation persistence feature. The current implementation
keeps bootstrap turns large enough for setup, renders compact Tier 0 canonical
state on ordinary later turns, bounds provider memory with Tier 1 recent
details, deterministic Tier 2 mid-history compact facts, and a hard-limited
Tier 3 rolling summary, preloads common `connect` and `run_green_check` details,
and records rendered-vs-available prompt telemetry with section hashes. Tier 2
is deterministically compacted from Tier 1; only Tier 3 may use model-backed
summary mode. Wave 2 Module G should consume those prompt/accounting surfaces;
it should not reintroduce full per-turn schema/memory resends or add
cross-invocation provider-session persistence.
Provider-native skill projection is also now part of the Wave 1 integration
substrate. Codex CLI receives run-local `.codex/skills`, Claude CLI receives
run-local `.claude/skills` plus `--allowedTools Skill(...)`, and API providers
use deterministic `load_skills` fallback. Wave 2 Module G should consume this
native projection/fallback split instead of reimplementing provider skill
behavior inside the brain or reverting product skill source to global
`.codex`/`.claude` folders. Wave 1 validation must also run the focused
`tests/harness/provider_native_skill_usage.py` proof: each CLI provider must
consume a run-local projected proof skill, return the hidden token through a
valid `TurnDecision`, and avoid `load_skills` fallback. The final Wave 1
double-check also requires non-interactive operator shell smoke coverage:
piped command scripts must run through `pyocd-debug` without a Windows console
and still support history/artifact commands for multi-user-prompt validation.

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
- deferred accepted risk: exact official-pair second-provider reproof,
  API-provider parity, and true fresh-machine portability proof.

Wave 0 owns:

0. `P0.0` layered validation
   - use `markdowns/tmp/curr-archive-20260628/p0_0_layered_validation_plan.md`
     as the archived execution checklist for Wave 0 cleanup and proof
   - write the resulting pass/fail matrix to
     `markdowns/tmp/curr-archive-20260628/p0_0_validation_report.md`
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
   - explicitly record exact official-pair second-provider proof,
     API-provider parity, and fresh-machine portability as unverified accepted
     prototype risk
   - do not block `P0` on those deferred items unless the team later chooses to
     restore them as hard gates

Wave 0 exit criteria:

- the worktree baseline for prototype work is intentionally clean or has only
  documented, non-blocking changes
- `markdowns/tmp/curr-archive-20260628/p0_0_validation_report.md` records the
  executed layers, elapsed times, artifacts, and remaining risks
- non-hardware checks have been run and recorded
- real STM32 and Nordic board checks have been run by a human/operator and
  recorded, or the missing hardware proof is explicitly marked as blocking
- the team agrees this is the branch all later prototype branches start from
- deferred official-pair second-provider, API-provider, and fresh-machine
  portability items are recorded as unverified accepted prototype risk, not
  silently assumed working

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
   - `src/pyocd_debug_mcp/brain/loop.py`
   - `src/pyocd_debug_mcp/brain/actions.py`
   - `src/pyocd_debug_mcp/brain/cli.py`

P0 should not implement the full features. It should preserve current behavior
and add tests for parsing/serialization and no-op hooks.

Archived implementation docs for this step:

- `markdowns/tmp/curr-archive-20260628/p0_foundation_spec.md`
- `markdowns/tmp/curr-archive-20260628/p0_foundation_process.md`

## Wave 1 - Three Parallel Branches

After `P0` lands back into Wave 0, Branch A, Branch B, and Branch C branch from
Wave 0 and run in parallel.

### Branch A - Provider Session + Compact Tool-Index Prompt

Branch A owns provider session continuity where the provider surface makes that
possible, plus the model-facing compact tool-index prompt. It should not overclaim
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

Tool schema forwarding in this branch means a curated compact model-facing tool
index for the allowed server-native tools, sourced from live MCP descriptions and
input schemas but rendered as short descriptions plus required/optional argument
hints. It does not expose raw MCP handles, full repeated JSON schema bodies,
internal brain/admin tools, or every MCP server function. Branch A keeps the
current `TurnDecision` JSON contract; provider-native tool calls remain a later
optional change, not part of this branch.

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
   - render the compact model-facing prompt index
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
- Branch B module 5 and the corrected free-host/final-decision boundary are
  needed by Wave 2 Module E and Module F.
- The 2026-06-30 model-native skill-loading correction extends Branch B's
  boundary: host file/edit/build actions must be structurally absent, and
  `load_skills(skill_ids=[...])` is the only brain-mediated model-native
  context expansion action in this pass.
- The scaffold-hardening follow-up specified in
  `markdowns/curr/r12-context-scaffold-hardening_spec.md` is implemented and is
  the substrate Wave 2 Module G should consume. It fixes the product skill root,
  runtime-copy-only recovery, structured skill-load failures,
  `load_tool_details`, strict loaded-detail guardrails before governed
  tool/script or brain-owned compound-action execution, invalid-tool-call
  auto-details, current prompt ordering/dedupe, provider/adapter failure
  classification, and prompt bundle alias cleanup. It does not implement
  codebase-map generation, map maintenance, actual product skills, or global bug
  reporting. Wave 2 and launch packaging must consume this substrate as-is: do
  not reintroduce `.codex`/`.claude` as product skill roots, source-package
  mutation by providers, or init-script paths that can directly touch hardware.

Should not own:

- provider sessions
- inspector rendering
- timeout default/clamp rules
- broad MCP-server host execution
- raw hardware access from client scripts
- future codebase-map generation and maintenance turns
- global bug-report registry/backend telemetry

### Branch C - Event Spine + Timeout Policy

Branch C owns the normalized brain event spine and timeout policy. It must make
timeout state session/client scoped now, not process-global prototype state:

- timeout proposals, clamps, effective budgets, and pending server-sync values
  live with the current turnkey brain/client session;
- server timeout sync is brain-only/internal and must not appear in the
  model-facing compact tool index;
- server timeout updates are partial updates for subsequent operations, not
  mutation of config files and not a promise to interrupt already-running
  pyOCD/vendor calls;
- bounded outer waits are still not true cancellation for in-process vendor
  calls. A killable worker/job layer remains out of scope for this branch.

Branch C defines event kinds, sinks, timeout clamps, and timeout propagation
hooks. Module D renders those events, Module E owns checkpoint continue/cancel
decisions, and Branch B applies batch timeout behavior during batch execution.

Current implementation status, 2026-06-30: Branch C is implemented in the
current Wave 1 merge-back candidate and has been live-validated with the
Branch C harness on `nucleo_l476rg` and `nrf52840dk` using both local CLI
providers. The branch still intentionally does not implement killable
pyOCD/vendor worker cancellation; that remains Wave 2 Module H prototype
hardening.

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
- Branch C module 1 and module 2 are required by Wave 2 Module D and Module E.

Should not own:

- batch semantics
- client-action execution
- checkpoint continue/cancel decisions
- inspector UI
- provider adapter rewrites beyond the stable timeout-consumption hook
- model-facing timeout admin tools

## Wave 2 - Prototype Hard-Bar Work

Wave 2 starts only after Branch A, Branch B, and Branch C have each merged back
into Wave 0 and the merged Wave 0 branch has passed the agreed checks. Because
Branch B's code boundary is only Codex-validated so far, Wave 2 must not start
as if the full provider/hardware proof were complete.

The old D/E/F/G/H git branches have been deleted. The sections below are now
requirement modules, not active branch names. They may be rebuilt as new
branches after Branch B is corrected, but the requirements themselves remain
mandatory for the first prototype.

- Module D needs Branch C module 1.
- Module E needs Branch B module 5 and the corrected free-host/decision
  boundary, plus Branch C module 1/module 2.
- Module F needs Branch B module 5 if green tests use client actions.
- Module G needs Branch A prompt/session metadata and Branch C event shapes if
  cache-reuse events are emitted.
- Module H needs Branch A provider subprocess/session behavior, Branch C event
  shapes, and the current MCP/pyOCD/serial lifecycle paths.

### Module D - Progress UI + Inspector

Serial order inside Module D:

1. `cli_progress.py`
   - render live progress from `BrainEvent`
2. `inspector.py`
   - write prompt turns, provider stream text, parsed decisions, tool calls,
     server observations, and state snapshots
3. CLI hook:
   - `cli.py` exposes progress/inspector flags through a small integration edit

Should not own:

- event shape redesign
- timeout clamp rules
- action execution semantics
- proof escalation policy
- static-context rendering, skill body loading, or cache key/reuse semantics

### Module E - Stream Checkpoints

Serial order inside Module E:

1. `stream_checkpoints.py`
   - checkpoint job and record schema
   - provider checkpoint verdict: continue/cancel/narrow adjustment
   - stall, null-read, bad-read, partial-output, early-error, and no-new-data
     policy
   - bounded provider checkpoint turn that cannot start unrelated board work
2. Build/external-command chunking:
   - `workspace.py`
   - stdout/stderr chunks, stall markers, early compiler/tool errors, and
     process cleanup status on cancellation
3. UART read chunking:
   - UART read path emits chunks, null-read/no-data observations, expected-match
     or unexpected-output markers, and observes cancellation
4. Client-action chunking:
   - `client_actions.py` emits chunks/checkpoints, exposes progress to the
     brain, and observes cancellation
5. UX/artifact integration:
   - normal operator progress shows concise checkpoint state
   - developer/inspector output shows checkpoint buffers, provider verdicts,
     prompt snippets, and final cleanup state

Design anchor:

- `markdowns/curr/wave2-midtool-checkpoints_spec.md`

Cross-branch dependency:

- Module E module 4 depends on Branch B module 5 and the corrected free-host /
  final-governed-decision boundary.
- Module E uses Branch C timeout/event shapes, but does not own them.

Should not own:

- pyOCD flash/connect/recover worker design
- green approval logic
- static-context rendering, skill body loading, cache-assisted build/workspace
  reuse
- proof escalation policy

### Module F - Scoped Green Approval

Serial order inside Module F:

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

Cross-branch dependency:

- If green tests run as client actions, Module F module 1 waits for Branch B
  module 5.

Should not own:

- provider sessions
- server tools
- general benchmark scoring outside the narrow prototype gate
- static-context rendering, skill body loading, cache keys, or cache-assisted
  reuse

### Module G - Static Context Efficiency + Cache-Assisted Reuse

Module G owns skill-index rendering, on-demand skill bodies, model-native skill
loading, client-side codebase-map context, and cache-assisted setup reuse because
those all touch prompt/static-context assembly. It must not spread cache,
skill-rendering, or codebase-map policy into D/E/F-owned modules during Wave 2.
It consumes the scaffold hardened by
`markdowns/curr/r12-context-scaffold-hardening_spec.md`; it should not rediscover
the product skill root, runtime-copy recovery, tool-detail loading, or prompt
ordering rules. It also inherits the detail-required execution guardrail:
index-only governed tool calls, governed client scripts, and brain-owned
compound actions must block, auto-load focused details, and require a fresh
provider decision before execution.

Serial order inside Module G:

1. `skills.py` static-context split
   - render selected-skill index and always-on safety lines
   - render one selected skill body on demand
   - keep safety lines always present; only diagnostic bodies are pullable
   - validate requested skill IDs against the already-selected set
   - build on the already-hardened `load_skills(skill_ids=[...])` context
     expansion substrate; do not reintroduce `.codex` as the product skill
     root, source-skill mutation, opaque skill-load crashes, or broad prompt
     rewrites
   - preserve the loaded-detail guardrail; Module G may add codebase-map context
     but must not let map/skill/index text substitute for the specific detail
     flag required before governed execution
2. `codebase_map.py` client-side map scaffolding
   - create `codebase_map.md` on first workspace boot from a deterministic
     inventory skeleton plus provider-authored descriptions
   - each file entry lists purpose, definitions/functions/classes, code
     dependencies, logical/process dependencies, tags, hashes, and provenance
   - inject the skill index, available governed-tool index, codebase-map rule,
     map path/hash/summary, and memory-cadence status into provider turns
   - inject the full current `codebase_map.md` exactly once for any provider
     turn that receives model-native workflow skill context; multiple skill
     loads in the same turn do not duplicate the map body
   - prompt the model to read the map before new code files or significant code
     changes greater than about 100 lines
   - after provider-native file changes, run one bounded maintenance subturn that
     updates/skips the map and replays or validly changes the pending
     `TurnDecision` before any governed action is trusted
   - record events/artifacts for map creation, injection, skipped/applied
     updates, changed files, hashes, and decision replay/change status
3. `artifact_cache.py`
   - content-addressed cache record schema
   - source/workspace hash, build-command fingerprint, toolchain fingerprint
   - firmware artifact hash, board/probe identity fields
   - prompt/tool/skill render hash fields
   - provenance links back to original run artifacts
4. Cache artifact writer/reader tests:
   - deterministic JSON ordering
   - conservative invalidation keys
   - portable repo-relative artifact references where possible
5. Reuse event/report records:
   - cache hit/miss/skipped reason events
   - report fields stating whether final live proof still ran
6. Small prompt/CLI hooks:
   - expose `load_skill(skill_id)` or equivalent on-demand body retrieval through
     the turn-closing decision/native-tool path selected by the branch spec
   - keep hooks minimal; broad prompt assembly rewrites move to final wiring

Cross-branch dependency:

- Module G may consume Branch C event shapes, but it must not redesign them.
- Module G may read Branch A prompt/session metadata, but it must not change
  provider session semantics.
- Module G must not change provider-memory semantics; the prototype relies on
  the existing compact memory ledger plus configurable native sync.
- Module G's codebase-map maintenance may perform provider-native host reads and
  edits only; it must not create generic host execution in the brain or bypass
  governed board/server actions.

Should not own:

- workspace build chunking or cancellation, owned by Module E
- progress/inspector UI rendering, owned by Module D
- scoped green approval semantics, owned by Module F
- final hardware proof replacement; cache reuse can skip setup/non-final repeats
  but cannot replace required live final verification
- broad edits to `loop.py`, `workspace.py`, `cli.py`, or `actions.py`; only small
  hooks are allowed, and if they conflict with D/E/F they move to final wiring
- project-level persistent custom tools/skills, owned by later MVP entry #10
- skill-guided host-work A/B/C experiments, owned by later MVP entry #13
- provider-memory semantics, owned by Branch A and final integration if needed

### Module H - Process-Tree + Board-Session Cleanup Guard

Module H owns deployment hygiene for subprocess-backed and hardware-backed runs.
It ensures provider CLIs, local MCP server children, pyOCD sessions, serial ports,
validation commands, and board-debug sessions do not leak across failures,
timeouts, interrupts, or malformed command invocations.

Serial order inside Module H:

1. `process_hygiene.py`
   - baseline process snapshots
   - spawned command/run-root provenance
   - precise child-tree identification
   - post-run orphan audit records
2. Provider subprocess wrapping:
   - `provider_codex_cli.py`
   - `provider_claude_cli.py`
   - explicit wall-clock timeout handling and provenance-based cleanup
   - prefer task/JSON files over fragile inline PowerShell prompt/JSON quoting in
     harnesses and docs
3. MCP client/server lifecycle:
   - `mcp_client.py`
   - local MCP subprocess close/reap on provider failure, timeout, or interrupt
   - always attempt `disconnect` before child cleanup when a session exists
4. pyOCD/serial cleanup hooks:
   - target-control/session close paths
   - serial-port close proof
   - events/artifacts that state whether cleanup succeeded
5. Harness/workflow integration:
   - post-check orphan audit for provider/MCP/hardware smokes
   - fail rows for leaked spawned children, locked probes, open serial ports, or
     connected debug sessions
   - tests that simulate hung child providers, failed MCP startup, timeout during
     pyOCD/serial work, and interrupted validation

Cross-branch dependency:

- Module H may consume Branch C event shapes for cleanup events, but must not
  redesign the event spine.
- Module H may wrap Branch A provider subprocesses, but must not change provider
  memory/session semantics except to make cleanup explicit on failure.
- Module H may touch MCP/pyOCD/serial close paths, but it must not implement
  stream checkpoint continue/cancel policy; that remains Module E.

Should not own:

- progress/inspector UI rendering, owned by Module D
- stream checkpoint policy, owned by Module E
- scoped green approval semantics, owned by Module F
- static-context rendering or cache reuse, owned by Module G
- broad provider SDK rewrites; this module hardens lifecycle cleanup around the
  current adapters and leaves final provider API replacement to later
- direct-hardware sandboxing; accepted soft hardware stance remains unchanged

## Final Integration - Serial Last

After Branch B is corrected and the Wave 2 Module D/E/F/G/H hard-bar work is
rebuilt, merged back into Wave 0, and checked, do one short serial integration
branch.

Owns:

- final wiring in `src/pyocd_debug_mcp/brain/loop.py`
- final wiring in `src/pyocd_debug_mcp/brain/actions.py`
- final wiring in `src/pyocd_debug_mcp/brain/cli.py`
- final server wrapper cleanup in `src/pyocd_debug_mcp/server.py`
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

During Wave 1 and Wave 2, a branch or module branch may touch those files only
for a small hook to its owned module. Broad edits to these files happen in `P0`
or final integration, not in parallel branches.

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
6. Correct Branch B before any Wave 2 hard-bar work starts.
7. Create new Wave 2 module branches, if desired, from the corrected Wave 0.
8. Merge the rebuilt Module D, E, F, G, and H work back into Wave 0 one at a
   time, running checks after each merge.
9. Branch `Final` from Wave 0.
10. Merge `Final` back into Wave 0 after final acceptance cleanup.

The old D/E/F/G/H branch objects were deleted on 2026-06-30; do not carry stale
branch state forward.

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
- Branch A/Wave 1 integration now includes compact later-turn prompts, bounded
  in-run provider memory, common detail preload, and rendered-vs-available
  prompt telemetry. It still does not include cross-invocation provider-session
  persistence.
- Wave 2 Module E now has an active design spec at
  `markdowns/curr/wave2-midtool-checkpoints_spec.md`. The feature remains
  unimplemented; current code still has whole request/response waits for long
  server/client actions rather than provider-visible checkpoint buffers.
- Wave 1 validation must include the prompt/memory hardening tests and
  credentials-free OpenAI/Anthropic API-path simulation checks. Live API calls
  remain a separate credential/credit-dependent proof boundary.
- Wave 1 validation must also include provider-native skill bridge checks:
  projection to `.codex/skills` and `.claude/skills`, Claude
  `--allowedTools Skill(...)`, fallback `load_skills`, prompt accounting,
  projection metadata, no writes to global provider folders, and focused live
  Codex/Claude CLI invocation proof through
  `tests/harness/provider_native_skill_usage.py`.
- Branch B now explicitly preserves the closed-server boundary: model-native
  host work stays outside governed actions, board/server-native work stays
  gated, and UART write is treated as hardware-stack work.
- Branch C now explicitly requires session/client-scoped timeout state and keeps
  brain-only timeout sync out of the model-facing tool surface.

## Pending Verification

- Wave 0 now has an executed `P0.0` validation report archived at
  `markdowns/tmp/curr-archive-20260628/p0_0_validation_report.md`, including real proof on the
  attached `nrf52840dk + nucleo_l476rg` pair and the merged `P-Wave-0` branch.
- If the team wants the prototype gate tied back to the exact official scoped
  pair, a fresh `nrf52833dk + nucleo_l476rg` re-proof remains a separate
  follow-on evidence task.
- Exact official-pair second-provider, API-provider parity, and fresh-machine
  portability proof remain intentionally deferred outside the Wave 0 gate and
  must not be claimed as verified.
- The exact module names should be checked against implementation reality when
  `P0` starts.
- No code behavior has been changed by this document.
- Branch A is acceptable for the current prototype bridge through provider session state,
  CLI resume handles, OpenAI Responses continuation, tool-schema forwarding,
  and provider progress events. Remaining Branch A hardening is final-provider
  integration quality: Codex SDK/app-server thread APIs, Claude Agent SDK
  sessions, and strict no-silent-fresh-session policy for modes that promise one
  continuous provider session. Strict policy means resume failure stops headless
  runs by default, while the interactive shell must ask before retrying or
  starting a new provider session from saved local memory.
- Branch B's strict prototype boundary has been tightened and is now summarized
  in `markdowns/current-progress.md` and `markdowns/things-to-change.md`:
  host-only file/shell/script work stays model-native/free, `read_file`,
  `replace_file`, and `run_build` are structurally impossible as governed
  decisions, and each provider turn still closes with one governed
  board/client/terminal or context-expansion decision. The scaffold-hardening
  implementation now requires guarded tool/script and brain-owned compound
  actions to block until their detail flags are loaded. Codex CLI
  `b001_wrong_boot_text` proof is green on `nucleo_l476rg + nrf52840dk`, and a
  Codex CLI no-hardware `load_skills` smoke is green at
  `runs/turnkey-20260630T084055Z-0a0377bc`. Later scaffold-hardening Codex
  live smokes and attached-board checks are also green. Claude CLI Branch C
  attached-board rows are green after auth restoration on `nucleo_l476rg` and
  retained `nrf52840dk`. Prompt/memory cost hardening and credentials-free
  OpenAI/Anthropic API-path simulation are green through the real provider
  factory/turnkey-loop code paths. Live API proof, exact official
  `nrf52833dk` proof, and fresh-machine proof remain pending.
- Branch C behavior is acceptable for the Wave 1 C slice in the current
  merge-back
  candidate through session/client-scoped timeout state, brain-only server
  timeout sync, and event-spine hooks. The current proof is live on the attached
  `nucleo_l476rg + nrf52840dk` pair with both local CLI providers; exact
  official `nrf52833dk`, live API-provider parity, and fresh-machine proof
  remain pending/deferred. Credentials-free API simulation is green but is not
  a substitute for paid/live provider proof.
