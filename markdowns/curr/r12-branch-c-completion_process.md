> STATUS: PROCESS LEDGER - not authority.

# R12 Branch C Completion Process

## Objective

Restore and complete the `P-Wave-C` event-spine / timeout-policy completion
work in this checkout, keeping the branch boundary narrow and preserving the
portable Windows/macOS post-bootstrap contract.

## Completed steps

- Restored the Branch C completion spec at
  `markdowns/curr/r12-branch-c-completion_spec.md`.
- Restored the Branch C test plan at `markdowns/curr/branch_c_test_plan.md`.
- Restored `tests/harness/branch_c_tests.py` fixes:
  - shared probe inventory for probe visibility checks;
  - UTF-8-with-replacement subprocess capture for Windows-safe output handling;
  - schema-valid `tooling_failure` classification in the live Codex task;
  - stable skipped-check names;
  - `--fail-on-skip` acceptance mode.
- Restored `tests/test_branch_c_harness.py` regression coverage.
- Restored the `host_bootstrap.py` optional `port_overrides` behavior required
  by existing callers.
- Synced `markdowns/R12_P_SPLIT.md` and `markdowns/current-progress.md` with the
  restored Branch C status.

## Current limits

- This process ledger does not claim hardware proof.
- This process ledger does not claim Claude CLI coverage.
- This process ledger does not claim macOS/fresh-host portability proof.
- The provider/portability gap is tracked separately in
  `markdowns/curr/r12-branch-c-provider-portability-coverage_spec.md`.

## Validation run after restoration

These commands were rerun on June 29, 2026:

```bash
uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --skip-hardware --skip-codex
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --skip-hardware --skip-codex
```

Results:

- targeted Branch C tests: `9 passed`
- full pytest: `285 passed`
- ruff: passed
- mypy: passed
- both official-board skip-hardware/no-Codex harness runs:
  `4 passed, 0 failed, 0 skipped`

Then, when boards/providers are available:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --fail-on-skip
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --fail-on-skip
```

## Verified

- The files above were restored in this checkout after an accidental cleanup.
- The non-hardware validation listed above passed after restoration.

## Pending verification

- Current hardware Branch C harness on both official boards.
- Claude/provider-neutral Branch C harness work.
