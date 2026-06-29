> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.
>
> FUTURE IMPLEMENTATION NOTE: This spec is intentionally not implemented in the
> current Branch A work. Implement it later when the project is ready to improve
> recovery reliability and the `anthropic-api` / Claude API facet. The current
> code has a useful recovery ledger, but this spec defines the stronger memory
> layer needed before claiming long-running Claude API continuity parity.

# Canonical Memory Layer Spec

## Goal

Build one canonical structured memory layer for turnkey provider continuity,
crash recovery, and stateless API-provider work.

Roadmap anchor: R12 turnkey brain, prototype foundation item "Persistent session
and model memory", and the `things-to-change.md` entry "Separate deterministic
safety-state from model reasoning-context".

Plain English goal: stop treating recovery memory and Claude API continuity as
separate partial mechanisms. The brain should persist one structured working
memory model, then render that model differently for:

- real provider-session sync (`openai-api`, `codex-cli`, `claude-cli`);
- stateless/local-primary continuous work (`anthropic-api`);
- explicit crash recovery / new provider session from saved memory;
- deterministic test replay.

This is not a hidden chain-of-thought store. It stores facts, decisions,
evidence, visible rationale, tool arguments/results, code/workspace state,
artifacts, and next-step state.

## Scope

This spec covers:

- a canonical structured memory schema;
- persistence under `runs/<session_id>/...`;
- prompt render profiles for normal sync, Claude API continuity, and recovery;
- exact recent turn memory plus compact older history;
- a current working-state snapshot;
- artifact and codebase indexes;
- migration from the current `ProviderMemoryEntry` / `ProviderMemorySummary`
  shape;
- tests proving important facts survive compaction and recovery.

## Non-Scope

This spec does not implement:

- Codex SDK/app-server thread APIs;
- Claude Agent SDK sessions;
- provider-native tool-call output format;
- broad product UI polish;
- new board-control capabilities;
- hidden model chain-of-thought capture;
- any claim that Claude API parity is already achieved.

Those can build on this memory layer, but they are separate build specs.

## Reconciliation Summary

Build plan:

- The build plan names R12 as the turnkey brain and includes four provider
  surfaces: `openai-api`, `anthropic-api`, `codex-cli`, and `claude-cli`.
- It says `anthropic-api` uses the official Anthropic SDK and Messages API.
- It says future Claude hardening should use approved/API-key-backed SDK paths,
  while local Claude subscription users remain a BYO Claude CLI adapter.
- It already requires strict provider-session recovery: a failed real-session
  resume must fail closed or explicitly start a labeled new provider session
  from saved local memory.

Current code:

- `ProviderMemoryEntry` stores an outcome-bearing turn ledger with visible
  rationale, action payload, result status, artifact paths, changed files,
  workspace summary, failed hypotheses, refused/blocked paths, acceptance
  constraints, and verification snapshot.
- `render_provider_memory_text(...)` renders compact text from recent memory
  entries plus a compact older summary.
- The JSON artifacts are richer than the prompt-injected memory text.
- `anthropic-api` continuity is local-primary and depends on the rendered memory
  block, not a provider-owned session handle.

Other docs:

- `markdowns/curr/things-to-change.md` already identifies this as prototype
  foundation work under persistent session and model memory.
- `markdowns/curr/r12_turnkey_spec.md` says Anthropic API memory is functional
  but weaker than Claude CLI session resume, and that parity requires ledger
  hardening and live proof.
- `markdowns/current-progress.md` lists Anthropic API memory-ledger hardening as
  missing before claiming parity with Claude Code CLI or OpenAI Responses.

Conflict list:

- No conflict. The stronger memory layer is an implementation refinement of the
  existing plan and docs.

Ambiguity list:

- AMBIGUITY: The exact token budget for each render profile is not specified in
  the build plan. Provisional choice: make budgets provider/runtime configurable
  with conservative defaults and hard caps, because hardware turns can be slow
  and provider context/cache behavior varies.
- AMBIGUITY: The exact codebase-map depth is not specified. Provisional choice:
  start with files touched/read, build command, allowed edit roots, changed
  files, and short semantic excerpts; do not index the whole repo by default.

## Design

The canonical memory layer lives in the brain layer. It is derived from observed
results and brain state, not from provider self-report alone.

The memory model has five tiers.

### 1. Working State Snapshot

Always render this first for local-primary and recovery profiles.

It should include:

- task goal and current phase;
- board id, session id, provider kind, provider handle summary;
- run mode, case id/kind when present;
- completed steps;
- pending/next recommended action;
- active blockers;
- active hypotheses with status and supporting/refuting evidence ids;
- verification flags and last green-check status;
- current workspace root, allowed edit roots, build command, changed files;
- acceptance constraints;
- recovery context if recovering from a failed provider resume.

This snapshot is the most important part for resuming after a crash. It answers:
"Where was I, what is true, what should I do next, and what must I not redo?"

### 2. Exact Recent Turn Ledger

Keep the last N committed turns as structured JSON and render them faithfully.

Each recent turn should include:

- turn index;
- visible observation summary;
- hypothesis;
- visible strategy/rationale;
- exact action kind and exact action payload;
- exact normalized tool call arguments when applicable;
- result status;
- salient result record;
- capped result excerpt;
- verification snapshot after the turn;
- artifacts produced or consulted;
- changed files after the turn;
- provider metadata relevant to continuity.

This should replace lossy action summaries as the main recent-memory surface.

### 3. Compact Older History

Older turns should compact into a structured summary, not plain prose only.

The compacted form should preserve:

- action -> outcome + key values;
- hypotheses supported/refuted;
- irreversible operations such as recover/flash;
- build/test/green-check status transitions;
- important observed values, such as PC, symbol value, UART excerpts, silicon
  identity, build errors, and refusal/block codes.

Never compact an old turn to only "success" or "failed"; keep the value that
made it useful.

### 4. Artifact Index

The memory should carry a short index of durable artifacts and what each is for:

- prompt;
- model turns;
- brain events;
- brain trace;
- turnkey state/result/score;
- build logs;
- serial excerpts;
- diffs;
- flashed artifacts and ELF/symbol artifacts.

The prompt should include paths and short descriptions, not full raw logs by
default. The provider can request or read details when a profile allows it.

### 5. Codebase / Workspace Map

For code-writing tasks, memory should include a bounded workspace map:

- allowed edit roots;
- files read;
- files changed;
- short before/after summaries for changed files;
- build command and last build status;
- test/green-check status;
- unresolved code questions.

This is not a full repo index. It is a task-local code map that helps the model
avoid losing the repair context after a provider failure.

## Render Profiles

### Remote-Primary Sync Profile

Used for `openai-api`, `codex-cli`, and `claude-cli` when provider-native
continuity exists and only periodic safety sync is needed.

Render:

- compact working state;
- exact recent turn ledger only when native sync is due;
- compact older summary;
- artifact index.

Goal: reinforce ground truth without wasting tokens every turn.

### Local-Primary Continuous Profile

Used for `anthropic-api` because the Messages API surface is stateless at the
provider session layer in this implementation.

Render:

- full working-state snapshot every turn;
- exact recent turn ledger every turn;
- compact older history;
- artifact index;
- codebase/workspace map for code tasks.

Goal: make brain-owned memory strong enough for long-running Claude API work.

### Recovery Profile

Used when a real provider session cannot resume and the operator explicitly
chooses "new session from saved memory".

Render:

- recovery banner with provider, expected handle, failure text, turn index, and
  confirmation that the new session is not the old session;
- full working-state snapshot;
- exact recent turn ledger;
- compact older history;
- artifact index;
- codebase/workspace map;
- next recommended action and anti-repeat instructions.

Goal: let a new provider session continue from facts without pretending it has
the old provider's hidden context.

### Deterministic Replay Profile

Used for tests and CI.

Render:

- stable ordering;
- no provider-specific prose that changes across runs;
- capped deterministic excerpts;
- no live-provider-only assumptions.

Goal: keep tests reliable.

## Persistence Plan

The canonical memory should be persisted in:

- `runs/<session_id>/run-metadata/turnkey_state.json`;
- a dedicated `runs/<session_id>/run-metadata/provider_memory.json`;
- `runs/<session_id>/logs/model_turns.jsonl`;
- `runs/<session_id>/logs/brain_events.jsonl`;
- existing artifact paths such as `applied-patches/turnkey.diff`.

`turnkey_state.json` remains the run-state artifact. The dedicated
`provider_memory.json` gives recovery and external inspection one stable memory
schema without requiring callers to understand the entire brain state record.

## Migration Plan

Phase 1:

- Keep existing `ProviderMemoryEntry`.
- Add canonical memory snapshot objects alongside it.
- Render current prompt memory from the canonical memory, not directly from the
  old entry renderer.

Phase 2:

- Make `ProviderMemoryEntry` either a compatibility projection or a child of the
  canonical memory schema.
- Add per-profile renderers.
- Add tests for compaction survival and recovery rendering.

Phase 3:

- Upgrade `anthropic-api` to use the local-primary continuous profile.
- Run Anthropic API repair/verify slices before claiming parity.

## Board-Facts-As-Data And Origin Tags

No new board facts should be introduced by this spec.

New project-defined values:

- memory profile names: `PROJECT-DEFINED`;
- render profile budgets and caps: `PROJECT-DEFINED`;
- recent-turn retention counts: `PROJECT-DEFINED`;
- salient result fields per tool: `PROJECT-DEFINED`;
- artifact index schema: `PROJECT-DEFINED`.

Hardware values remain sourced from board configs, MCP tool results, and run
artifacts. Do not add `if board == ...` memory behavior.

## Documentation Plan

Update:

- `markdowns/curr/r12_turnkey_spec.md` for the provider memory architecture and
  Claude API status.
- `markdowns/current-progress.md` when implementation is complete or partially
  verified.
- `README.md` provider-continuity section when user-facing behavior changes.
- `markdowns/curr/things-to-change.md` to keep the backlog pointing at this
  spec.

No MCP tool docstrings change unless the implementation adds or changes a tool.

## Portability

The memory schema must use repo-relative paths where possible and absolute paths
only where existing runtime artifacts already require them.

The implementation must work on Windows and macOS:

- no OS-specific path parsing;
- no shell-specific artifact readers;
- no reliance on symlinks;
- UTF-8 JSON artifacts;
- deterministic ordering for serialized memory records.

## Verification Plan

Non-hardware:

1. Unit tests for memory schema serialization.
2. Unit tests for all render profiles.
3. Tests that exact recent action payloads survive rendering.
4. Tests that compaction preserves key values, not just success/failure.
5. Tests that recovery profile includes provider failure details and labels the
   new session as recovery-created.
6. Tests that `anthropic-api` receives the local-primary continuous profile.
7. Existing ladder:
   - `uv run pytest -q`
   - `uv run ruff check .`
   - `uv run mypy src`

Provider/hardware:

1. Real Codex CLI freeform run on `nucleo_l476rg`.
2. Real Codex CLI code-writing repair run on a bug case.
3. Real Anthropic API run after memory profile upgrade.
4. Official-pair hardware proof on `nucleo_l476rg` and `nrf52833dk` when the
   correct boards are attached.

Do not claim Anthropic/Claude API parity until the Anthropic API live repair
slice passes with this memory layer.

## Acceptance Criteria

The feature is complete when:

- canonical provider memory has a documented JSON schema;
- `provider_memory.json` is written for each turnkey run;
- prompt rendering uses named render profiles;
- recovery profile contains enough state to continue after a provider failure
  without pretending the old provider session survived;
- `anthropic-api` uses the local-primary continuous memory profile;
- exact recent action payloads and salient result values are rendered;
- older compaction preserves key observed values;
- code-writing recovery includes changed files, diff summary, build status, and
  last verification status;
- all non-hardware tests pass;
- live Anthropic API and Codex CLI slices pass before parity is claimed.

## Verified

- This spec was written against the current Branch A state and current docs.
- Existing docs already identify Anthropic API memory-ledger hardening as future
  work before parity claims.

## Pending Verification

- No implementation has been done for this spec.
- No new tests have been added for this spec.
- Claude/Anthropic API parity remains pending.
- Hardware/provider proof remains pending for the eventual implementation.
