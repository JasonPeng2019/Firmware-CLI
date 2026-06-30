> STATUS: REVIEW - current for the Windows attached-board Branch C evidence boundary.

# R12 Branch C Completion Review

## Result

WINDOWS ATTACHED-BOARD BRANCH C SURFACE CLEAN.

The implementation matches the intended Branch C repair scope:

- the harness no longer depends on brittle raw pyOCD console parsing for probe
  visibility;
- the live Codex task uses a schema-valid classification;
- acceptance mode can fail selected skipped checks;
- existing `host_bootstrap.py` callers can omit `port_overrides`;
- docs distinguish current Windows attached-board evidence from pending
  official `nrf52833dk` and macOS/fresh-host proof.

## Findings

No new blocking design finding is recorded in this review. The remaining gaps
are proof/deployment gaps:

- official `nrf52833dk` Branch C hardware proof is pending because the attached
  Nordic board reports nRF52840 silicon;
- live API-provider proof is not part of the completed local CLI evidence;
- forced physical timeout/hang cancellation is not proven by Branch C and still
  needs a future killable worker/job layer if the product requires it;
- macOS/fresh-host portability proof is pending.

## Checks run

These checks were rerun on June 29, 2026:

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
- after the live-sync halt fix, targeted Branch C tests:
  `10 passed`
- after the live-sync halt fix, targeted ruff for the touched harness/test
  files: passed
- after the live-sync halt fix, full non-hardware validation:
  `uv run pytest -q` returned `286 passed`, `uv run ruff check .` passed, and
  `uv run mypy src` passed
- `uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --fail-on-skip`:
  `9 passed, 0 failed, 0 skipped`, run root
  `runs/20260629T203611Z-88e44520`
- `uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk --fail-on-skip`:
  `9 passed, 0 failed, 0 skipped`, run root
  `runs/20260629T203830Z-1b95fee0`
- `uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --fail-on-skip`:
  blocked in Stage 0 because the attached Nordic board reported
  `FICR.INFO.PART actual=0x52840, expected=0x52833`
- provider-neutral Branch C follow-on validation:
  - `uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py`
    returned `13 passed`
  - `uv run pytest -q` returned `289 passed`
  - `uv run ruff check .` passed
  - `uv run mypy src` passed
  - non-hardware `codex-cli` + `claude-cli` matrix returned
    `6 passed, 0 failed, 0 skipped` on both `nucleo_l476rg` and retained
    `nrf52840dk`
  - hardware/provider matrix returned `11 passed, 0 failed, 0 skipped` on
    `nucleo_l476rg` and retained `nrf52840dk`
  - public deployed CLI smokes passed for both providers on both attached
    boards:
    `runs/20260630T011733Z-ae2eb3ee`,
    `runs/20260630T011814Z-4c33bc87`,
    `runs/20260630T011858Z-f269f813`,
    `runs/20260630T011944Z-7b9c4186`

## Verified

- Review doc restored.
- Current non-hardware, provider-neutral, STM32 hardware, and retained Nordic
  hardware command output is recorded above.

## Pending verification

- Official `nrf52833dk` hardware acceptance proof.
- macOS/fresh-host proof.
