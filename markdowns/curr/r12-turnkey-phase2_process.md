# Process ledger for r12-turnkey-phase2

## Goal and roadmap anchor

Task: Implement `R12` phase 2 turnkey repair skills, richer brain state, and
an acceptance benchmark with live `nrf52840dk` proof
Roadmap anchor: `R12`

## Done

- loaded the named workflow skills and the required command/authority docs
- reconciled the phase-2 request against the build plan, roadmap, and current
  phase-1 turnkey implementation
- confirmed the live-proof boundary for this session:
  scoped-pair support in code and benchmark definitions, attached
  `nrf52840dk` as the live proof board
- created the phase-2 spec, process ledger, and review target docs
- froze the phase-2 contract:
  - richer hypotheses/experiments/state
  - repair-oriented premium skills
  - `R12` acceptance benchmark harness
  - scoped-pair suite definitions plus an alternate live `nrf52840dk` suite
- implemented the richer brain-state model:
  - observations
  - hypotheses
  - experiments
  - strategy evaluations
- added the first repair-oriented turnkey skills:
  - `reference-contract-diagnose`
  - `reference-contract-repair`
- implemented the `R12` acceptance benchmark harness and suite definitions
- fixed the live verification boundary in the repair path by resetting on UART
  open when the post-flash target state is running
- fixed turnkey result persistence so saved run JSON includes its own
  `result_path`
- fixed the final static-gate boundary by replacing untyped diagnosis dicts
  with a typed `ReferenceContractDiagnosis`
- reran the repo suite ladder and the live alternate-board `R12` suite to green

## In progress

- documenting the validated phase-2 state and the remaining scoped-pair and
  fresh-machine proof work

## TODO

- roll the phase-2 turnkey slice onto the official scoped pair:
  `nrf52833dk` and `nucleo_l476rg`
- rerun the official scoped Nordic `R11` chain in the current post-fix state
- validate true fresh-machine Windows and macOS managed-Zephyr / no-`NCS`
  bring-up before claiming broad customer-machine portability

## Limitations and known gaps

- this pass still does not claim an unrestricted open-ended repair loop for
  arbitrary user projects
- the current repair workflow remains fixture-scoped to tracked repo-owned bug
  workspaces
- official scoped-pair `R12` hardware closure is still pending because this
  session proved the slice on attached `nrf52840dk`, not on both scoped boards

## Hardware hand-off

- live proof board for this session: attached `nrf52840dk`
- live proof completed:
  - host bootstrap
  - Stage 0
  - Stage 1 smoke
  - `turnkey_alt_nrf52840_v1` acceptance suite
- latest live benchmark summary:
  `runs/_turnkey_benchmark/turnkey_alt_nrf52840_v1__20260622T073914Z.json`
- later scoped-pair hardware hand-off will remain explicit until
  `nrf52833dk` and `nucleo_l476rg` both complete the same phase-2 acceptance
  proof

## Open decisions and surfaced issues

- use `nrf52840dk` as the live proof board while preserving the official
  scoped-pair claim as pending hardware, not silently redefined
- keep hardware-touching actions behind MCP even when the premium client edits
  source and rebuilds locally
- treat abnormally long single-step tool calls as hangs, but allow long-running
  builds, flashes, and full benchmark cases when they are still making progress

## Verified

- phase-1 turnkey baseline exists and is green
- tracked mirrored `nrf52840dk` bug fixtures already exist for:
  `b001`, `b002`, `b003`, `b004`
- `uv run pytest -q tests/test_turnkey.py tests/test_r12_turnkey_benchmark.py`
  passed
- `uv run ruff check .` passed
- `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`
  passed
- `uv run python -m tests.harness.r12_turnkey_benchmark --suite turnkey_alt_nrf52840_v1`
  passed with `full_success=6`, `partial_success=0`, `fail=0`,
  `average_score=100.0`
- `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --command "uv run pytest -q tests/test_turnkey.py tests/test_r12_turnkey_benchmark.py" --command "uv run python -m tests.harness.r12_turnkey_benchmark --suite turnkey_alt_nrf52840_v1"`
  passed end to end

## Pending verification

- scoped-pair hardware closure
- fresh-machine Windows managed-Zephyr / no-`NCS` validation
- fresh-machine macOS managed-Zephyr / no-`NCS` validation
