# Process ledger for r12-branch-c-provider-portability-coverage

## Goal and roadmap anchor

Task: Close Branch C provider neutrality and deployment coverage
Roadmap anchor: R12

## Done

- Read the Branch C provider-portability spec and existing Branch C harness
  context.
- Reworked `tests/harness/branch_c_tests.py` from Codex-only checks to
  provider-selected checks for `codex-cli` and `claude-cli`.
- Kept deprecated `--skip-codex` compatibility while adding
  `--provider`, `--provider-model`, `--provider-timeout-seconds`, and
  `--skip-providers`.
- Reworked Branch C harness tests to prove default provider selection,
  provider matrix selection, skip semantics, and provider factory use.
- Ran targeted non-hardware tests for the changed harness files:
  `uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py`
  passed with 13 tests.
- Ran targeted lint for changed harness files after fixing an unused import:
  `uv run ruff check tests/harness/branch_c_tests.py tests/test_branch_c_harness.py`
  passed.
- Fixed the non-hardware acceptance semantics bug where `--skip-hardware` still
  selected live provider/hardware rows and therefore created artificial SKIPs
  under `--fail-on-skip`.
- Ran the non-hardware provider matrix for both accepted local board IDs with
  `codex-cli` and `claude-cli`; both returned `6 passed, 0 failed, 0 skipped`.
- Ran the full non-hardware regression ladder:
  `uv run pytest -q` returned `289 passed`, `uv run ruff check .` passed, and
  `uv run mypy src` passed.
- Ran the full hardware/provider matrix on `nucleo_l476rg`; it returned
  `11 passed, 0 failed, 0 skipped`.
- Ran the full hardware/provider matrix on retained `nrf52840dk`; it returned
  `11 passed, 0 failed, 0 skipped`.
- Ran direct public `pyocd-debug-brain run` deployment smokes for Codex and
  Claude on both attached boards. All four passed and exercised multiple
  provider turns through the real MCP client/server path.
- Updated Branch C docs with exact validation results and remaining portability
  limits.

## In progress

- None.

## TODO

- None for Branch C on the currently attached Windows host and boards.

## Limitations and known gaps

- This Windows host can prove Windows behavior only. macOS remains pending
  until the same matrix is run on a macOS host.
- The local Nordic board reports nRF52840 silicon, so this run can validate
  `nrf52840dk` rather than claiming official `nrf52833dk` hardware proof.

## Hardware hand-off

- Hardware is currently allowed by the user.
- Target connected boards for this pass: `nucleo_l476rg` and `nrf52840dk`.

## Open decisions and surfaced issues

- The first direct public CLI smoke used `final_status=unresolved`, which
  correctly exercised the deployed path but returned exit code 1 by CLI policy.
  The accepted smoke prompt now uses `final_status=diagnosed_only` for dry-run
  deployment proof without claiming `fixed` or `healthy_confirmed`.

## Verified

- Targeted Branch C harness/unit checks: passed.
- Targeted lint on changed files: passed.
- Non-hardware provider matrix:
  - `nucleo_l476rg`: `6 passed, 0 failed, 0 skipped`
  - `nrf52840dk`: `6 passed, 0 failed, 0 skipped`
- Full non-hardware ladder:
  - `uv run pytest -q`: `289 passed` before and after documentation updates
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
- Hardware/provider matrix:
  - `nucleo_l476rg`: `11 passed, 0 failed, 0 skipped`
  - `nrf52840dk`: `11 passed, 0 failed, 0 skipped`
- Public deployed CLI smoke:
  - `codex-cli` + `nucleo_l476rg`: `runs/20260630T011733Z-ae2eb3ee`
  - `claude-cli` + `nucleo_l476rg`: `runs/20260630T011814Z-4c33bc87`
  - `codex-cli` + `nrf52840dk`: `runs/20260630T011858Z-f269f813`
  - `claude-cli` + `nrf52840dk`: `runs/20260630T011944Z-7b9c4186`

## Pending verification

- Official `nrf52833dk` hardware proof, if that exact board is required.
- macOS/fresh-host proof.
