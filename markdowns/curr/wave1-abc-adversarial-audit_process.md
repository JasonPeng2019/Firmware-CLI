# Process ledger for wave1-abc-adversarial-audit

## Goal and roadmap anchor

Task: Adversarial audit and cleanup for Wave 1 A/B/C merge candidate
Roadmap anchor: `R12` prototype Wave 1 A/B/C merge-back from
`markdowns/R12_P_SPLIT.md`.

## Done

- Audited the active Wave 1 docs and code paths against the build plan,
  `R12_P_SPLIT.md`, `current-progress.md`, and the prior merge validation
  ledger.
- Valid criticism: `tests/harness/branch_c_tests.py` treated a provider
  dry-run `action_batch` as a failure even though `TurnDecision` explicitly
  allows `action_batch` and the live deployed Wave 1 smoke path uses it.
  Fixed the harness to accept either a single action or a non-empty batch, and
  added a focused regression test.
- Valid criticism: the tail of `markdowns/R12_P_SPLIT.md` still said Branch C
  was unimplemented even though the current Wave 1 merge section and live proof
  ledger mark it implemented. Updated that stale line in place.
- Ran the focused regression tests, Python-change gate, combined non-hardware
  suite, live provider/hardware harness, and explicit public CLI smokes on both
  attached boards and both local CLI providers.
- Repeated the adversarial audit after validation. No additional Wave 1 A/B/C
  code defects or useful cleanup findings survived manual review.

## In progress

- None.

## TODO

- None for the current attached-board Wave 1 A/B/C scope.

## Limitations and known gaps

- Exact official `nrf52833dk` proof remains pending unless that board is
  physically attached; the current Nordic attachment has previously identified
  as retained alternate `nrf52840dk`.
- API-provider parity and fresh-machine proof remain deferred prototype risks,
  not Wave 1 A/B/C merge blockers.
- Branch C still intentionally does not implement killable pyOCD/vendor worker
  cancellation; that is Wave 2 Branch H/future hardening.

## Hardware hand-off

If exact official scoped-pair closure is required, attach an actual
`nrf52833dk` and run:

```powershell
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --provider codex-cli --provider claude-cli --provider-timeout-seconds 120 --fail-on-skip
```

## Open decisions and surfaced issues

- No settled-decision change surfaced by the adversarial passes.

## Verified

- `uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py`
  -> `15 passed`.
- `uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk --skip-hardware --skip-providers --fail-on-skip`
  -> `4 passed, 0 failed, 0 skipped`.
- `python .codex\skills\python-change\scripts\run_python_change_checks.py --continue-on-error`
  -> ruff check/fix passed, ruff format passed, Pyright remained at the known
  repo-wide `95` diagnostic baseline, full pytest -> `339 passed`.
- Changed-file Pyright filter for `tests/harness/branch_c_tests.py` and
  `tests/test_branch_c_harness.py` -> `0` diagnostics.
- Focused Wave 1 suite:
  `uv run pytest -q tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py tests/test_branch_c_harness.py tests/test_timeout_policy.py tests/test_p0_foundation.py`
  -> `123 passed`.
- `uv run mypy src` -> passed.
- `uv run pytest -q tests/test_r11_benchmark.py` -> `34 passed`.
- `uv run python -m tests.harness.r11_benchmark --help` -> passed.
- Full Branch C live provider/hardware harness on `nucleo_l476rg` with
  `codex-cli` and `claude-cli` -> `11 passed, 0 failed, 0 skipped`; run roots
  `runs/20260630T043201Z-9346a430` and
  `runs/20260630T043226Z-9b317d56`.
- Full Branch C live provider/hardware harness on `nrf52840dk` with
  `codex-cli` and `claude-cli` -> `11 passed, 0 failed, 0 skipped`; run roots
  `runs/20260630T043418Z-ef122410` and
  `runs/20260630T043448Z-a2f53ffd`.
- Public CLI two-turn smokes used a task file, turn 1
  `action_batch(connect, get_board_info)`, and turn 2 standalone `finalize`.
  Expected `blocked` status artifacts:
  - `runs/20260630T043529Z-6391fd28`
  - `runs/20260630T043559Z-83135d6d`
  - `runs/20260630T043636Z-e803899e`
  - `runs/20260630T043707Z-34dd6769`
- Process audit before and after live checks showed no new leftover spawned
  provider, MCP, pyOCD, serial, or validation children from this suite.
- Follow-up Pyright baseline cleanup on June 30, 2026:
  - `python .codex\skills\python-change\scripts\run_python_change_checks.py`
    -> ruff check/fix passed, ruff format passed, full Pyright passed with 105
    files analyzed and 0 diagnostics, full pytest -> `339 passed`
  - `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
    -> passed, including `339` pytest tests, ruff, mypy, `34` R11 benchmark
    tests, and R11 benchmark help
  - Branch C live provider/hardware harness reran green on
    `nucleo_l476rg` and `nrf52840dk` with both `codex-cli` and
    `claude-cli`; fresh run roots:
    `runs/20260630T050810Z-8a1abf43`,
    `runs/20260630T050841Z-1aaaf4a0`,
    `runs/20260630T050814Z-ac5c22c2`, and
    `runs/20260630T050845Z-c42644ee`
  - Public CLI two-turn smokes reran on both attached boards and both
    providers; artifact pass roots:
    `runs/20260630T050932Z-f84bc258`,
    `runs/20260630T051005Z-56326461`,
    `runs/20260630T051045Z-34e7d70e`, and
    `runs/20260630T051113Z-f12e5c29`
  - cleanup audit found no new leftover spawned provider/MCP/pyOCD or
    validation children beyond the pre-existing VS Code/Codex app-server-owned
    MCP process tree.

## Pending verification

- Exact official `nrf52833dk` closure, API-provider parity, and fresh-machine
  proof remain pending/deferred as documented in the Wave 1 specs.
