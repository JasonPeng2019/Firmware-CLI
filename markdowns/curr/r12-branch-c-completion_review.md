> STATUS: REVIEW - restored after accidental cleanup; rerun validation required.

# R12 Branch C Completion Review

## Result

CHANGES RESTORED, NON-HARDWARE CLEAN.

The restored implementation matches the intended Branch C repair scope:

- the harness no longer depends on brittle raw pyOCD console parsing for probe
  visibility;
- the live Codex task uses a schema-valid classification;
- acceptance mode can fail selected skipped checks;
- existing `host_bootstrap.py` callers can omit `port_overrides`;
- docs distinguish non-hardware evidence from pending hardware/provider proof.

## Findings

No new blocking design finding is recorded in this review. The remaining gaps
are proof gaps:

- real hardware Branch C harness runs on both official boards are pending;
- live Codex-plus-hardware check 9 is pending;
- Claude CLI/provider-neutral Branch C coverage is pending;
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

## Verified

- Review doc restored.
- Current non-hardware command output is recorded above.
- Current STM32 and retained Nordic hardware command output is recorded above.

## Pending verification

- Official `nrf52833dk` hardware acceptance proof.
- Provider-neutral / Claude Branch C acceptance proof.
