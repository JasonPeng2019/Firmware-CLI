# Process ledger for post-bootstrap-portability-contract

## Goal and roadmap anchor

Task: Implement the post-bootstrap portability contract, align the portability
playbook to that contract, and validate the current repo/runtime surface on the
currently attached Windows bench pair.
Roadmap anchor: `R0`, `R2-R7`, `R9-R12`, plus the deferred portability-proof
boundary in `ROADMAP.md` and `current-progress.md`.

## Done

- Wrote the reconciled portability spec in
  `markdowns/curr/post-bootstrap-portability-contract_spec.md`.
- Reconciled the narrower post-bootstrap contract against:
  - the build plan
  - the current bootstrap/runtime code
  - `README.md`
  - `init.md`
  - `stage0_setup.md`
  - `markdowns/current-progress.md`
- Updated setup/runtime/docs to match that contract:
  - `setup_host.ps1` now treats Nordic `nrfjprog` as an optional helper rather
    than a hard success requirement
  - `setup_host.sh` now treats Nordic `nrfjprog` as an optional helper rather
    than failing the entire setup path
  - `host_bootstrap.py` now describes vendor helper CLIs as optional
    post-bootstrap helpers rather than core prerequisites
  - `stage0_check.py`, `recover_gate.py`, and `target_control.py` now treat
    `recover_mode=manual_only` as an intentional manual support boundary rather
    than "automate later"
  - `README.md`, `init.md`, `stage0_setup.md`, and
    `markdowns/current-progress.md` now describe the contract as
    supported-host/supported-board portability after a short documented
    developer bootstrap
- Rewrote `superpowers/agent_portability_playbook.md` so it matches the same
  accepted post-bootstrap contract instead of the older stricter
  self-installing absent-stranger framing.
- Non-hardware validation passed:
  - `uv run pytest -q tests/test_stage0_shared_errors.py tests/test_target_control.py tests/test_host_bootstrap.py`
  - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
  - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
- Real hardware validation passed on the attached Windows pair:
  - `uv run python host_bootstrap.py --board-id nucleo_l476rg`
  - `uv run python host_bootstrap.py --board-id nrf52840dk`
  - `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg`
  - `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --recover-test nrf52840dk --confirm-shared-usb nrf52840dk`
  - `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
  - `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`
  - live stdio MCP smoke on both boards via `LocalMCPClient`
  - `uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."`
  - `uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52840dk --task "Verify this reference firmware is healthy and explain why."`
- Recorded the updated review outcome in
  `markdowns/curr/post-bootstrap-portability-contract_review.md`.

## In progress

- none

## TODO

- Optionally improve `setup_host.sh` to detect or warn on missing SEGGER J-Link
  tooling for Nordic J-Link boards, then verify that on a macOS host.
- Re-prove the official scoped pair on the current branch state if the team
  wants the public portability claim tied back to `nrf52833dk +
  nucleo_l476rg`.
- Run the later macOS proof when a macOS host is available.

## Limitations and known gaps

- The current live hardware rerun is on the attached `nrf52840dk +
  nucleo_l476rg` pair, not the official scoped `nrf52833dk +
  nucleo_l476rg` pair.
- macOS-specific behavior remains pending because only a Windows host is
  available in this session.
- The public supported-board claim still points at `nrf52833dk +
  nucleo_l476rg`; the currently attached alternate Nordic proof hardware does
  not replace that scoped-pair claim.

## Hardware hand-off

- Official scoped Nordic re-proof when `nrf52833dk` is attached again:
  ```powershell
  uv run python host_bootstrap.py --board-id nrf52833dk
  uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
  uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
  uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
  ```

## Open decisions and surfaced issues

- No remaining code-side portability-contract conflict is open in this process
  step.
- The remaining open proof decision is scope only: whether the attached
  `nrf52840dk` proof is enough for the current purpose, or whether the exact
  public scoped-pair claim must be re-proved now on `nrf52833dk`.

## Verified

- portability contract spec written
- setup-helper semantics updated for optional Nordic `nrfjprog`
- manual-only recover messaging updated across Stage 0 / service / guardrail
  layers
- repo-level docs synced to the narrower post-bootstrap contract
- portability playbook synced to that same contract
- targeted non-hardware slice passed
- suite ladder passed
- real hardware rerun passed on:
  - `nucleo_l476rg`
  - `nrf52840dk`
- live stdio MCP smoke passed on both attached boards
- live turnkey healthy-run proof passed on both attached boards

## Pending verification

- macOS bootstrap and runtime proof
- official scoped-pair portability closure on `nrf52833dk + nucleo_l476rg`
