> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# p0 0 doc sync superpowers audit

## Goal in plain English

Task: Clean stale markdown/superpowers state after Wave 0 merge validation and fix superpowers-compliance drift in code
Roadmap anchor: `R12` Wave 0 / `P0.0`

## Scope and non-scope

In scope:
- clean stale `markdowns/` status after the `main` into `P-Wave-0` merge and
  the executed `P0.0` validation pass
- move clearly completed or non-active Wave 0 docs out of `markdowns/curr/`
- update authoritative docs that still describe pre-validation or pre-fix
  state
- audit the code for superpowers-compliance drift introduced by the merge,
  especially one-source-of-truth violations in runtime configuration
- add the smallest regression guard and rerun targeted validation, including a
  real-board smoke check for any code fix

Out of scope:
- implementing deferred prototype features from `things-to-change.md`
- changing the product closure bar for second-provider parity or fresh-machine
  portability
- re-scoping the official board pair away from `nrf52833dk + nucleo_l476rg`

## Reconciliation summary

- Build plan:
  - the build plan and roadmap treat Wave 0 as a clean-slate validation gate,
    with `current-progress.md` carrying the live state
  - `timeouts.py` is the intended shared runtime timeout home
- Current code:
  - the merged branch is green and has an executed Wave 0 validation report
  - `brain/loop.py` still carried duplicate turnkey timeout constants instead
    of consuming `timeouts.py`
- Other docs or notes:
  - `README.md`, `current-progress.md`, `ROADMAP.md`, `R12_P_SPLIT.md`, and
    `repo_file_index.md` still contained some pre-validation or pre-fix text
- Disagreements:
  - docs still described `P0.0` as pending even after the validation report was
    created
  - `README.md` still described `claude-cli` as blocked on this host even
    though `current-progress.md` already contained later STM32 Claude proof
  - code and docs implied `timeouts.py` was the shared timeout source while the
    turnkey loop still duplicated its own timeout constants

## Design

- Keep the authoritative live-state docs truthful instead of appending
  contradictory notes.
- Keep `markdowns/curr/` limited to active step docs and move completed or
  parked items to `markdowns/tmp/`.
- Centralize turnkey timeout constants in `src/pyocd_debug_mcp/timeouts.py` and
  make `brain/loop.py` consume them, so the runtime has one timeout source.

## Board-facts-as-data and origin tags

- No board-fact schema changes are needed in this pass.
- New timeout constants remain `PROJECT-DEFINED` in the shared timeout module.

## Documentation plan

- Update `README.md`, `current-progress.md`, `repo_file_index.md`,
  `ROADMAP.md`, and `R12_P_SPLIT.md`.
- Do not change the build-plan authority; only sync subordinate docs to the
  already-proven Wave 0 state.

## Portability

- No new portability mechanism is added here.
- The code fix must not reintroduce per-host timeout literals in multiple
  modules.

## Verification plan

- targeted non-hardware regression:
  - `uv run pytest -q tests/test_r12_turnkey.py`
- strict non-hardware sanity:
  - `uv run ruff check .`
  - `uv run mypy src`
- hardware smoke after the code fix:
  - one real `pyocd-debug-brain run --provider codex-cli ...` health run on the
    attached STM32 board
  - one real `pyocd-debug-brain run --provider codex-cli ...` health run on the
    attached Nordic board

## Acceptance criteria

- stale pre-validation/pre-fix statements are removed from the active docs
- `markdowns/curr/` contains only active docs for the current Wave 0 /
  prototype step
- `brain/loop.py` no longer owns a second copy of the turnkey timeout
  constants
- a regression test covers the shared turnkey timeout source
- the non-hardware checks pass and the hardware smoke still runs green

## Verified

- The merge validation report already exists at
  `markdowns/curr/p0_0_validation_report.md`.
- `README.md` and `current-progress.md` currently disagree about the live
  `claude-cli` host status.
- `repo_file_index.md` and `ROADMAP.md` still describe `P0.0` as not yet
  executed.
- `brain/loop.py` currently duplicates turnkey timeout constants instead of
  importing them from `src/pyocd_debug_mcp/timeouts.py`.

## Pending verification

- The code/doc fixes in this spec still need the targeted non-hardware reruns
  and the post-fix hardware smoke.
