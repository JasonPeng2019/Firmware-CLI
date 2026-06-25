> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# P0 foundation spec

## Goal and roadmap anchor

This step turns the R12 "P0 foundation" from a planning note into a real,
bounded deliverable on top of the now-clean Wave 0 trunk.

Roadmap anchor:

- primary: R12 turnkey prototype
- execution gate: serial `P0` foundation between Wave 0 and Wave 1

The goal is narrow: land the shared data shapes and hook points that every
later prototype branch depends on, without prematurely implementing the later
provider-session, action-policy, timeout-policy, checkpoint, or green-approval
behavior.

## Scope and non-scope

In scope:

- add a concrete `brain/decision_types.py` module for the future governed
  board-decision surface
- expand `brain/provider_types.py` with provider-session and provider-progress
  shapes while preserving current one-turn behavior
- extend `timeouts.py` with shared timeout-config/update models and move the
  turnkey loop's hardcoded timeout constants under that shared module
- add a minimal `brain/client_actions.py` store contract only
- thread tiny no-op-compatible hook points through `brain/actions.py`,
  `brain/loop.py`, and `brain/cli.py`
- add tests for parsing/serialization/default behavior of the new P0 shapes
- clean the markdown active set so `markdowns/curr/` reflects the real current
  step

Not in scope:

- persistent provider sessions
- host-vs-board action execution policy
- batches, `wait`, UART write, or client-action execution
- live progress streaming, inspector panes, or checkpoint cancellation
- model-proposed timeout/iteration enforcement
- green approval logic

## Reconciliation summary

Build plan:

- `markdowns/ROADMAP.md` and `markdowns/R12_P_SPLIT.md` already define a serial
  `P0` foundation whose purpose is to land shared shapes and tiny hooks before
  the parallel R12 branches start.

Current code:

- `brain/actions.py` contains the current turnkey decision/result contract, but
  it is tied to the existing single-action loop and does not expose the future
  board-decision envelope or timeout/iteration proposal shapes.
- `brain/provider_types.py` is still only `ProviderTurn(decision, output_text,
  response_id)`.
- `timeouts.py` contains timeout constants but no structured shared config or
  update shape.
- `brain/events.py` already exists and is serviceable, so P0 should extend it
  only where a shared shape is still missing.

Other docs:

- `markdowns/curr/things-to-change.md` describes P0 as the prototype
  foundation, but it is a backlog document rather than an implementation
  contract.
- `markdowns/current-progress.md` still emphasizes the closed Wave 0 proof
  boundary and does not yet identify a concrete active P0 deliverable.
- `markdowns/repo_file_index.md` still lists several older slice docs under
  `curr/` as though they were current-step sources of truth.

Disagreements:

- There is no conflict on the purpose of P0, but there is a documentation gap:
  the roadmap and split plan mention P0 while the active-step docs do not
  define it as a real deliverable.
- The current code already contains pieces that the split plan labels as P0
  substrate (`events.py`, parts of `actions.py`). P0 therefore needs to refine
  those modules rather than recreate them.

No user-blocking conflicts were found for this step.

## Design

P0 stays in the brain/orchestration layer. It does not change the server tool
surface or the hardware substrate.

The design rule is compatibility first:

- keep the existing `TurnDecision`, `TurnkeyRunResult`, and current turnkey
  action models stable for the live loop and existing tests
- add new P0 shapes alongside them, then re-export or reference them from the
  existing modules where helpful
- keep all new fields optional/defaulted so the current turnkey runtime remains
  behaviorally unchanged

The concrete deliverable is:

1. `brain/decision_types.py`
   - define shared prototype decision types for future work:
     - timeout proposals
     - iteration estimates
     - early-exit verdicts
     - a future board-decision envelope
     - batch/action-call containers
   - keep these as data shapes only; no execution logic lands here
2. `brain/provider_types.py`
   - add a provider-session state shape
   - add a provider progress payload shape
   - extend `ProviderTurn` to optionally carry them
3. `timeouts.py`
   - define shared timeout config/update models
   - expose one canonical place for turnkey default timeouts
4. `brain/client_actions.py`
   - define a tiny session-scoped store contract and in-memory implementation
   - no execution path yet
5. tiny integration hooks
   - `brain/cli.py` and invocation config can carry a future timeout/iteration
     planning field without changing current CLI semantics
   - `brain/loop.py` reads shared turnkey defaults from `timeouts.py`
   - `brain/actions.py` re-exports the current/future decision types cleanly

## Board facts as data and origin tags

This step should not introduce new board facts.

Changed values:

- turnkey timeout defaults move from loop-local constants to shared timeout
  constants and config models in `timeouts.py`
  - origin: `PROJECT-DEFINED`
- timeout clamp minima/maxima for the shared config model
  - origin: `PROJECT-DEFINED`
- default iteration-estimate safety buffer in the shared shape, if present
  - origin: `PROJECT-DEFINED`

No board-specific behavior may be added in this step.

## Documentation plan

- `markdowns/ROADMAP.md`
  - mark P0 as the active serial step after Wave 0 and define its concrete
    deliverable briefly
- `markdowns/R12_P_SPLIT.md`
  - refine the P0 section so it matches the concrete module/file changes that
    land in code
- `markdowns/current-progress.md`
  - update the "current position" so Wave 0 is treated as done and P0 is the
    active next build step
- `markdowns/repo_file_index.md`
  - update the `curr/` vs `tmp/` ownership after the doc cleanup
- `markdowns/curr/p0_foundation_process.md`
  - live execution ledger for this step

## Portability

This step is host-portable by construction:

- it is mostly data-shape work
- no new shell/provider/hardware behavior is required
- validation should remain on the existing cross-platform Python ladder

## Verification plan

Cheapest-first verification:

1. `uv run pytest -q`
2. `uv run ruff check .`
3. `uv run mypy src`
4. targeted tests for:
   - new P0 decision/provider/timeout/client-action models
   - existing turnkey tests to prove compatibility was preserved

Hardware verification:

- none required for the P0 foundation itself if no runtime behavior changes
  beyond shared constant sourcing are introduced
- if an integration change accidentally affects live turnkey runtime, the
  fallback hardware hand-off is the existing Wave 0 ladder in
  `markdowns/current-progress.md`

## Acceptance criteria

P0 is done when:

- the repo has a concrete `decision_types.py` module with the planned shared
  prototype shapes
- `provider_types.py` and `timeouts.py` expose shared future-safe shapes without
  breaking the current runtime
- a minimal `client_actions.py` store contract exists
- the turnkey loop uses shared timeout defaults instead of private loop-local
  constants
- tests cover the new shapes and the non-hardware ladder stays green
- `markdowns/curr/` contains only the current active-step docs for the R12
  prototype, and the indexes/roadmap/current-progress files agree on that

## Verified

- Wave 0 baseline already proven on the current merged trunk before this step
  starts

## Pending verification

- P0 non-hardware validation after implementation
- any doc-sync drift discovered during the build/review loop
