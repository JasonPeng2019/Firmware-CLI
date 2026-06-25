# Process ledger for p0-foundation

## Goal and roadmap anchor

Task: deliver the serial P0 foundation step for the R12 prototype on top of the
clean Wave 0 trunk.

Roadmap anchor:

- primary: R12 turnkey prototype
- execution gate: serial `P0` between Wave 0 and the parallel Wave 1 branches

## Done

- Loaded the repo authority docs, workflow commands, and current roadmap/split
  planning before writing the step.
- Reconciled the current codebase against the roadmap, `R12_P_SPLIT.md`, the
  active backlog, and the current-proof docs.
- Confirmed the live repo trunk is `main` at `Wave 0 done`; the historical
  `P-Wave-0` branch exists only as a remote ref and is not the active local
  working branch anymore.
- Confirmed there was no stale live debug/provider process left running before
  starting this step.
- Opened the concrete P0 implementation spec at
  `markdowns/curr/p0_foundation_spec.md`.
- Reduced `markdowns/curr/` to the real active doc set for this step and moved
  older completed slice docs into `markdowns/tmp/`.
- Landed the P0 shared substrate in code:
  - `brain/decision_types.py`
  - `brain/client_actions.py`
  - expanded `brain/provider_types.py`
  - shared turnkey timeout config/update shapes in `timeouts.py`
  - compatibility-preserving hook points in `brain/actions.py`,
    `brain/config.py`, and `brain/loop.py`
- Fixed two Windows/headless UX shell defects exposed by the validation ladder:
  - `PromptSession()` now falls back cleanly when no Win32 console buffer is
    available
  - workspace/artifact slash commands now preserve Windows paths by using raw
    command text instead of backslash-stripped parsed args
- Added targeted P0 tests in `tests/test_p0_foundation.py`.
- Cleared the non-hardware validation ladder after the P0 implementation:
  - `uv run pytest -q` -> `246 passed`
  - `uv run ruff check .` -> clean
  - `uv run mypy src` -> clean
- Re-ran the suite-style proof after the final P0 cleanup and CLI timeout-hook
  fixups:
  - `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
    -> clean
  - `uv run pytest -q tests/test_r11_benchmark.py` -> `34 passed`
- Confirmed there is still no stale live debug/provider process running after
  the validation pass.

## In progress

- None.

## TODO

- Wave 1 prototype branch work:
  - Branch A: provider session + tool schema prompt
  - Branch B: action boundary + batches + client actions
  - Branch C: event spine + timeout policy

## Limitations / known gaps

- This step intentionally does not implement the later R12 behavior; it only
  lands the shared substrate.
- Hardware validation was not rerun for P0 because the landed behavior stayed in
  shared types, config, and UX-shell robustness; the existing Wave 0 hardware
  proof remains the relevant board boundary.

## Hardware hand-off

Only needed if P0 unexpectedly changes runtime behavior. If that happens, rerun
the Wave 0 ladder recorded in `markdowns/current-progress.md` for the current
attached board pair.

## Open decisions / surfaced

- None at the moment.

## Verified

- Authority/read-order reconciliation completed.
- Current branch/trunk state verified.
- No stale debug/provider process was running at process start.
- P0 code implementation landed.
- Active-doc cleanup landed.
- `pytest`, `ruff`, and `mypy` are green in the final P0 state.

## Pending verification

- None for the P0 non-hardware surface.
