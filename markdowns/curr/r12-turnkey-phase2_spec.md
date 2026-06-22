> STATUS: ACTIVE WORKING SPEC FOR `R12` PHASE 2. This is the tracked contract
> for the current expansion pass, not a claim that all of Stage 5 is already
> complete.

# `R12` Turnkey Phase 2

## Goal in plain English

Task: Implement `R12` phase 2 turnkey repair skills, richer brain state, and
an acceptance benchmark with live `nrf52840dk` proof
Roadmap anchor: `R12`

This phase widens the turnkey client from a deterministic health-check shell
into the first real premium workflow layer:

- repair-oriented turnkey skills
- richer run state with hypotheses and experiments
- a tracked turnkey acceptance benchmark

It does **not** claim the full final `R12` product is done.

## Scope and non-scope

In scope:

- extend the turnkey models from simple step logging into richer run-state
  capture:
  - observations
  - hypotheses
  - experiments
  - strategy evaluations
- add local non-hardware step kinds to the turnkey runner where needed for
  premium workflows:
  - source inspection
  - deterministic source repair
  - local rebuild
  - result evaluation
- add the first repair-oriented turnkey skill family for the tracked
  reference-contract bug fixtures:
  - wrong UART signature
  - wrong known-value symbol
  - missing application UART output
  - combined UART + symbol regression
- keep hardware-touching actions behind the MCP server boundary even when local
  source edits and rebuilds happen in the turnkey client
- define the first turnkey acceptance benchmark surface for product #2
- implement a runnable turnkey benchmark harness and suite definitions
- support official scoped-pair benchmark definitions in code:
  - `nrf52833dk`
  - `nucleo_l476rg`
- use attached `nrf52840dk` as the live proof board for the phase-2 suite in
  this session
- update docs and progress tracking to distinguish:
  - scoped-pair support in code
  - live proof produced here on `nrf52840dk`

Out of scope:

- a general LLM-driven patch authoring loop
- arbitrary user-project repair outside the tracked repo-owned bug fixtures
- claiming final scoped-pair hardware closure for `R12` in this session
- hosted deployment, remote transport, or multi-board coordination
- changing settled substrate/server architecture decisions

## Reconciliation summary

- Build plan:
  - `R12` requires the turnkey brain as an MCP client, skills loading, CLI,
    brain-level convergence/self-evaluation logic, and an acceptance benchmark.
  - the plan says the turnkey CLI should drive the full loop on either board and
    demonstrate a meaningful premium advantage.
  - board facts must stay data-driven and the shared services remain below both
    frontends.
- Current code:
  - phase 1 already landed the stdio MCP client, the CLI, tracked skills, and a
    deterministic health/recover run path
  - the current runner state is still a simple ordered step log with no richer
    hypothesis/experiment model
  - no repair-oriented skill, no local source-repair engine, and no `R12`
    benchmark harness exists yet
- Other docs or notes:
  - `current-progress.md` already lists the exact next tasks as richer skills,
    richer state, and the product-#2 benchmark
  - the repo already contains mirrored `nrf52840dk` `R11` bug fixtures, which
    are suitable tracked inputs for the first deterministic premium repairs
- Disagreements / surfaced boundary:
  - the roadmap and `current-progress.md` name the official scoped pair, but the
    only attached board in this session is `nrf52840dk`
  - per the authority order and the verify-don't-claim rule, phase-2 code can
    support the scoped pair while live proof in this session is produced on the
    attached alternate Nordic board only

## Design

### 1. Phase-2 product shape

Keep the same top-level product boundary:

- local turnkey CLI
- child stdio MCP server
- hardware-touching steps through MCP
- local source/build logic in the turnkey client

Widen the turnkey client with three new subsystems:

- richer run-state tracking
- deterministic fixture-repair strategies
- a turnkey benchmark harness

### 2. Richer run state

Add explicit typed state objects for:

- observation
  - source: `mcp_tool`, `source_scan`, `build_output`, `verification`
  - summary
  - raw evidence excerpt
- hypothesis
  - id
  - summary
  - status: `active`, `confirmed`, `rejected`
  - supporting observation ids
- experiment
  - id
  - purpose
  - action summary
  - result
- strategy evaluation
  - strategy id
  - outcome
  - next action

The run result must record these separately from raw step results so later
benchmark scoring can judge premium reasoning quality without pretending the
client is open-ended.

### 3. Repair-oriented skills

Phase 2 introduces repair-oriented turnkey skills over the tracked repo-owned
bug fixtures.

The first premium repair family is a deterministic
`reference-contract-repair` flow:

1. connect to the board
2. inspect current runtime evidence:
   - board info
   - flash current bug artifact
   - read symbol
   - read UART
3. inspect the tracked source workspace
4. form hypotheses about which reference contract is broken:
   - wrong UART signature
   - wrong `stage1_known_value`
   - missing UART output entirely
   - multiple simultaneous contract regressions
5. apply the smallest deterministic repair to `src/src/main.c`
6. rebuild through the tracked build command
7. flash the rebuilt artifact
8. re-verify symbol + UART + green-state
9. summarize the reasoning/evidence

This is intentionally limited to the tracked bug fixtures. It is still a real
premium workflow because it owns diagnosis, local edit, rebuild, flash, and
verification end to end.

Additional phase-2 skills:

- `reference-contract-diagnose`
  - diagnosis-only, no source edits
- `reference-contract-repair`
  - diagnosis + repair + rebuild + flash + verify

The phase-1 skills remain and are still part of the acceptance ladder.

### 4. Local repair engine

The first repair engine is deterministic and fixture-scoped, not model-based.

It operates only on tracked workspaces with known Stage-1 contracts and applies
small source edits to restore:

- `printk("boot ok\\n")`
- `const uint32_t stage1_known_value = 0x1234ABCD`

It must:

- reject unsupported layouts clearly
- record every proposed and applied repair in run state
- keep edits constrained to the allowed workspace roots from the case contract

### 5. CLI expansion

Add new turnkey CLI run inputs:

- `--case-id`
  - resolves a tracked benchmark case/workspace
- `--workspace-root`
  - optional explicit workspace override for repair skills

Add a benchmark entrypoint:

```bash
uv run python -m tests.harness.r12_turnkey_benchmark --suite turnkey_alt_nrf52840_v1
```

The CLI remains useful for single-run operator use; the harness owns aggregate
acceptance scoring.

### 6. Product-#2 acceptance benchmark

Define a new turnkey benchmark harness that reuses the existing tracked case
surface rather than inventing a second unrelated corpus.

Phase-2 benchmark families:

- reused from `R11`
  - `k001_reference_green`
  - `f001_halted_target_silent_uart`
  - `b001_wrong_boot_text`
  - `b002_wrong_known_value`
  - `b003_silent_uart`
  - `b004_dual_signal_regression`
- turnkey-only benchmark assertions
  - hypothesis list is present and non-empty for non-trivial cases
  - experiments are recorded
  - repair cases produce source diffs and successful rebuild/verify runs
  - observability-fault cases classify correctly without code edits

Scoped suite definitions to add:

- `turnkey_scoped_pair_v1`
  - official `nrf52833dk` + `nucleo_l476rg`
- `turnkey_alt_nrf52840_v1`
  - attached alternate Nordic live-proof suite for this session

### 7. Premium-advantage scoring

For phase 2, "premium advantage" is measured honestly as:

- no external Codex/Claude client required
- deterministic diagnosis and repair on tracked bug fixtures
- richer internal reasoning record than the BYO-agent harness captured

Score dimensions for the turnkey benchmark:

- classification correctness
- intervention correctness
- green verification
- reasoning/state quality

This is an initial premium acceptance benchmark, not yet the final
research-grade product comparison.

## Board-facts-as-data and origin tags

- supported boards remain board-config-driven through the existing loader
- no scoped-pair support may be hardcoded into the brain logic
- workspace/build facts for repair cases come from tracked benchmark case data
- skill ids, benchmark suite names, and scoring thresholds are
  `PROJECT-DEFINED`
- attached `nrf52840dk` live proof is a runtime fact, not a scope redefinition

## Documentation plan

Update in the same unit of work:

- `README.md`
  - turnkey CLI and benchmark entrypoints
- `current-progress.md`
  - phase-2 done vs next boundaries
- this phase-2 spec, process ledger, and review

## Portability

- local rebuild steps must keep using the repo-owned `pyocd-zephyr-build`
  surface rather than shell-specific scripts
- no repair logic may hardcode board-specific source paths beyond what the case
  contract or workspace input provides
- same-probe concurrency remains unsupported; timeouts and failure text must
  keep abnormal waits bounded and diagnosable

## Verification plan

Non-hardware:

- targeted turnkey tests and new benchmark tests
- full default and suite ladders
- CLI smoke for new repair skills

Live on the attached board in this session:

- host bootstrap
- Stage 0
- Stage 1 smoke
- single-skill repair runs on tracked `nrf52840dk` bug fixtures
- full `turnkey_alt_nrf52840_v1` suite

Scoped-pair hardware remains a pending hand-off for a later session with those
boards attached.

## Acceptance criteria

- richer turnkey run-state objects exist and are persisted in run results
- at least one diagnosis-only and one repair-oriented premium skill exist
- the repair engine can restore the tracked reference contract on the mirrored
  `nrf52840dk` bug fixtures
- a real `R12` benchmark harness exists with suite definitions for the scoped
  pair and the live alternate Nordic proof suite
- the full agent-verifiable surface is green
- the live `turnkey_alt_nrf52840_v1` suite is green on attached hardware
- docs state clearly what was live-proven here and what scoped-pair proof still
  remains pending

## Verified

- phase-1 turnkey client, CLI, and live `nrf52840dk` proof already exist
- the repo already has mirrored `nrf52840dk` bug fixtures matching the `R11`
  bug-family contract, so phase 2 has real tracked repair inputs

## Pending verification

- the phase-2 implementation itself
- the new benchmark harness and suite definitions
- live alternate-board phase-2 suite
- official scoped-pair hardware closure for `R12`
