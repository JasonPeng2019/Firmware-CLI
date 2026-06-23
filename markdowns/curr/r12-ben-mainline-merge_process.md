# Process ledger for r12-ben-mainline-merge

## Goal and roadmap anchor

Task: R12 Ben mainline merge and portability hardening
Roadmap anchor:
- primary: R12 turnkey brain
- secondary: portability closure and retained-board hardening below full R12 closure

## Done

- Reconciled the merge task against the build plan, current R12 contract, and
  the Ben-vs-Jason merge spec.
- Activated the merge spec under `markdowns/curr/r12_ben_mainline_merge_spec.md`
  and kept this process ledger live during the build loop.
- Ported the Jason-style transport seam into Ben's turnkey client:
  - `ServerCommand`
  - `ToolClientProtocol`
  - transport-only stdio client
  - parsed local client wrapper
- Replaced the Windows-unsafe `bash`-only local rebuild path with host-aware
  shell dispatch in the turnkey workspace helper.
- Added typed turnkey evidence records:
  - observations
  - hypotheses
  - experiments
  - strategy evaluations
- Added the separate deterministic helper layer under `playbooks/turnkey/`
  without changing the outer Ben product interface.
- Added per-tool timeout discipline in the turnkey loop.
- Fixed the live alternate-board failure boundary where `read_file(...)`
  returned only a char-count summary instead of file contents.
- Generalized alternate-suite acceptance so retained-board turnkey suites no
  longer assume the official scoped pair.
- Hardened Windows subprocess capture for local rebuilds and CLI-provider calls
  to use UTF-8-with-replacement decoding.
- Cleared the non-hardware ladder after every meaningful change:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy src`
- Re-ran the non-hardware ladder again in the final merged state on June 23,
  2026 and it still passed cleanly.
- Re-proved the attached `nrf52840dk` substrate on this Windows host:
  - `uv run pyocd-zephyr-build --app-dir firmware/nrf52840dk/reference/src --build-dir firmware/nrf52840dk/reference/build --board nrf52840dk/nrf52840`
  - `uv run python host_bootstrap.py --board-id nrf52840dk`
  - `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --recover-test nrf52840dk --confirm-shared-usb nrf52840dk`
  - `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`
- Re-proved the freeform Codex-backed healthy-turnkey path on the attached
  `nrf52840dk`:
  - `uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52840dk --task "Verify this reference firmware is healthy and explain why."`
  - session root: `20260623T034813Z-4301eb52`
- Re-proved the Codex-backed alternate-board R12 ladder on this attached
  `nrf52840dk` through all six implemented retained-board cases:
  - `nrf52840dk__k001_reference_green`
  - `nrf52840dk__b001_wrong_boot_text`
  - `nrf52840dk__b002_wrong_known_value`
  - `nrf52840dk__f001_halted_target_silent_uart`
  - `nrf52840dk__b003_silent_uart`
  - `nrf52840dk__b004_dual_signal_regression`
  - aggregate rerun command:
    `uv run pyocd-debug-brain benchmark --provider codex-cli --suite nrf52840dk_v1_plus_b003_b004`
  - aggregate rerun result: `full_success=6`, `partial_success=0`, `fail=0`,
    `average_score=100.0`
  - aggregate rerun session roots:
    - `20260623T035021Z-e60b20c3`
    - `20260623T035301Z-18bc10da`
    - `20260623T035705Z-892b585d`
    - `20260623T040041Z-47861540`
    - `20260623T040253Z-7b5f1e56`
    - `20260623T040728Z-ff4cf87c`
  - observed runtime: about 20 minutes 43 seconds with continuous case
    progress; no abnormal hang boundary appeared during the one-command rerun

## In progress

- None.

## TODO

- Re-run the official scoped-pair R12 ladder on `nrf52833dk + nucleo_l476rg`
  after these mainline hardening changes, so the official pair is re-proven in
  the latest post-merge state rather than only historically proven.
- Clear the required second-provider closure ladder on the official scoped pair
  once the chosen provider/model path is usable on this host.
- Run true fresh-machine Windows and macOS no-`NCS` portability proof for the
  managed Zephyr path.

## Limitations and known gaps

- The official scoped product truth is still the pair `nrf52833dk +
  nucleo_l476rg`; the `nrf52840dk` proof here is retained-board parity, not a
  replacement scoped product claim.
- The required second-provider R12 closure pass is still open.
- Fresh-machine no-`NCS` proof is still open on both Windows and macOS.

## Hardware hand-off

- Official scoped-pair reproof after this merge:
  - `uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."`
  - `uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --suite pilot_v1_plus_b003_b004`
- Second-provider closure once the provider path is fixed:
  - rerun the same freeform + suite ladder on the official pair with the
    approved second provider/model path
- Fresh-machine proof:
  - rerun `pyocd-zephyr-build --ensure-only`, one reference rebuild, Stage 0,
    Stage 1, and at least one benchmark repair case on a clean Windows host and
    a clean macOS host without preinstalled `NCS`

## Open decisions and surfaced issues

- None for the retained-board `nrf52840dk` surface. The remaining boundaries
  are official-pair, second-provider, and fresh-machine proof work.

## Verified

- Non-hardware:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy src`
- Live attached-board proof on June 23, 2026:
  - the retained-board reference rebuild passed for `nrf52840dk`
  - `host_bootstrap.py`, `stage0_check.py`, and `stage1_smoke` all passed on
    the connected `nrf52840dk`
  - the freeform healthy-turnkey run passed with session root
    `20260623T034813Z-4301eb52`
  - the one-command retained-board suite
    `nrf52840dk_v1_plus_b003_b004` passed with:
    `full_success=6`, `partial_success=0`, `fail=0`, `average_score=100.0`

## Pending verification

- Official scoped-pair reproof in the latest merged state
- Second-provider closure on the official pair
- Fresh-machine Windows no-`NCS` proof
- Fresh-machine macOS no-`NCS` proof
