> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# r12 nucleo reproof

## Goal in plain English

Task: R12 official STM32 reproof on attached nucleo_l476rg in merged Ben mainline
Roadmap anchor:
- primary: `R12` turnkey brain
- secondary: scoped-pair reproof after the Ben mainline merge hardening

## Scope and non-scope

In scope:
- non-hardware suite validation for the current merged Ben mainline:
  - `pytest`
  - `ruff`
  - `mypy`
  - benchmark harness CLI surface
- attached-board live proof for the official scoped STM32 board:
  - reference rebuild
  - `host_bootstrap.py --board-id nucleo_l476rg`
  - `stage0_check.py --board-id nucleo_l476rg ...`
  - `tests.harness.stage1_smoke --board-id nucleo_l476rg`
  - freeform `pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg`
  - all six `nucleo_l476rg__...` Codex turnkey benchmark cases
- the second-provider path only as far as this host can really execute it on
  the attached Nucleo
- any real repo bug exposed by that ladder, fixed through the `fix-bug` loop

Out of scope:
- mixed-board `pilot_v1_plus_b003_b004` suite closure, because the official
  scoped Nordic board is not attached in this pass
- fresh-machine Windows or macOS no-`NCS` portability proof
- retained-board `nrf52840dk` parity proof, already done
- changing the `R12` contract or architecture

## Reconciliation summary

- Build plan:
  - `R12` closure requires the turnkey CLI to drive the full loop on the
    scoped pair and remain benchmark-comparable to the frozen `R11` corpus.
- Current code:
  - the Ben mainline already contains the merged Jason-originated transport,
    host-shell, evidence, and playbook hardening.
- Other docs or notes:
  - `current-progress.md` still lists official scoped-pair `R12` reproof after
    the merge as open.
  - the attached `nrf52840dk` retained-board path is already green and should
    not be retested as a substitute for the official STM32 half.
- Disagreements:
  - none in architecture.
  - practical proof boundary: with only the Nucleo attached, this pass can
    close the official STM32 half of the post-merge reproof but not the Nordic
    half or the mixed-board one-command suite.

## Design

Treat this as a `write-process` sub-step executed through a `test-suite`
ladder:

1. rerun the non-hardware suite preset
2. confirm the attached board is really `nucleo_l476rg`
3. rerun STM32 Stage 0 and Stage 1 in the merged state
4. rerun the Codex freeform healthy-turnkey path
5. rerun all six STM32 Codex benchmark cases individually
6. repro the `claude-cli` STM32 turnkey path
7. if any real repo defect appears, route it through the bug loop, then rerun
   the targeted failure and the full STM32 ladder above

The final verdict must distinguish:

- green here on the attached STM32
- blocked on missing Nordic hardware
- blocked on provider/account state
- red due to a real repo bug

## Board-facts-as-data and origin tags

- board identity remains `board_id=nucleo_l476rg`; no raw target or probe UID
  is hardcoded into the live commands
- provider names remain `PROJECT-DEFINED`
- CLI handles and model names remain `VENDOR-FIXED`

## Documentation plan

- if no repo bug appears, sync the active process ledger and current-progress
  to the new official STM32 reproof evidence
- if a repo bug is fixed, sync every touched governing doc in the same unit of
  work

## Portability

- use the host-aware rebuild path already merged into the brain
- do not rely on Windows `bash`
- treat provider/account failures as host/runtime boundaries unless the repo is
  constructing the wrong CLI invocation

## Verification plan

- `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
- `uv run python host_bootstrap.py --board-id nucleo_l476rg`
- `uv run pyocd-zephyr-build --app-dir firmware/nucleo_l476rg/reference/src --build-dir firmware/nucleo_l476rg/reference/build --board nucleo_l476rg`
- `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg`
- `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
- `uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."`
- six per-case `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__...`
- `uv run pyocd-debug-brain run --provider claude-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."`

## Acceptance criteria

1. The non-hardware suite ladder is green.
2. The attached board is confirmed as `nucleo_l476rg`.
3. STM32 Stage 0 and Stage 1 pass in the current merged state.
4. The Codex freeform `R12` run on `nucleo_l476rg` passes.
5. All six `nucleo_l476rg` Codex `R12` benchmark cases pass in the current
   merged state, or any real failure is fixed and rerun to green.
6. The `claude-cli` STM32 path is either:
   - green, or
   - reduced to a reproduced non-repo boundary with real evidence.
7. The final matrix clearly separates verified-here, non-hardware verified,
   and pending hardware/provider boundaries.

## Verified

- this spec is reconciled against the build plan, current merge spec, current
  process ledger, README, ROADMAP, and current-progress status

## Pending verification

- live STM32 suite execution
- any repo bug surfaced by that execution
