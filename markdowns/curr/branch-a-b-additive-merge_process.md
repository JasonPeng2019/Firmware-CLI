# Process Ledger: Branch A/B Additive Merge

## Goal and roadmap anchor

Task: Merge `origin/P-Wave-B` into `P-Wave-A` while preserving Branch A
provider resume guarantees and carrying Branch B action/task additions.

Roadmap anchor: `R12` prototype Wave 1 merge-back.

## Done

- Loaded `merge-conflicting-repos`, `firmcli-spec-loop`, workflow core, and
  relevant superpowers.
- Confirmed previous failed merge was aborted and `P-Wave-A` is clean.
- Ran ref inventory and scratch merge probe.
- Classified the merge as additive with a shared integration seam:
  Branch A owns provider/session/recovery; Branch B owns action/task/UART
  additions.
- Wrote `markdowns/curr/branch-a-b-additive-merge_spec.md`.
- Resolved `origin/P-Wave-B` into `P-Wave-A` from a clean target spine.
- Integrated B action/task/client behavior into A's provider-bundle flow.
- Reconciled active docs.
- Ran targeted tests: 134 passed.
- Ran default validation ladder: 319 tests, ruff, and mypy passed.
- Ran suite validation ladder: 319 tests, ruff, expanded mypy, R11 benchmark
  tests, and R11 benchmark help passed.
- Wrote `markdowns/curr/branch-a-b-additive-merge_review.md`.

## In progress

- Commit and push `P-Wave-A`.

## TODO

- Push merge commit to `origin/P-Wave-A`.

## Limitations and known gaps

- No new hardware result can be claimed unless a real hardware command is run
  in this session.
- Branch B docs may include stale "Branch A pending" language; active docs must
  not preserve that as current truth.

## Hardware hand-off

- Pending unless explicitly run after the merge:
  `uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."`
- Official Nordic proof remains pending unless `nrf52833dk` is attached and
  rerun.

## Open decisions and surfaced issues

- No user-level ambiguity found so far. The objective merge rule is clear:
  keep A's provider/session contract and port B's additive action surface.

## Verified

- `git status --short --branch` reported a clean `P-Wave-A`.
- `merge_probe.py` reported the expected seven conflict files and no surprise
  product-layer conflict outside the integration seam.
- Targeted merge suite passed: 134 tests.
- Default ladder passed.
- Suite ladder passed.

## Pending verification

- Push to `origin/P-Wave-A`.
- New hardware/live-provider proof after the merge.
