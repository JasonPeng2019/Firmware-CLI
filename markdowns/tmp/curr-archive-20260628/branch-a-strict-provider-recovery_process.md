# Process ledger for branch-a-strict-provider-recovery

## Goal and roadmap anchor

Task: Finish Branch A strict provider-session recovery and deployment validation.
Roadmap anchor: `R12` turnkey brain, Wave 1 Branch A (`provider session + tool schema prompt`).

## Done

- Loaded the named Codex skills:
  - `firmcli-specs`
  - `firmcli-spec-loop`
  - `firmcli-write-process`
  - `firmcli-test-suite`
  - `firmcli-fix-bug`
- Loaded supporting build/review skills and the original `.claude/commands/*`
  workflow docs required by those skills.
- Re-read the authority docs and Branch A handoff/status docs.
- Confirmed the active branch is `P-Wave-A`.
- Confirmed the remaining Branch A implementation gap is strict provider
  resume failure handling and explicit recovery from saved brain memory.
- Created this process ledger and
  `markdowns/curr/branch-a-strict-provider-recovery_spec.md`.
- Implemented typed `ProviderResumeFailure` / `ProviderResumeFailureRecord`
  routing with provider, expected handle, turn index, failure text, local memory
  availability, and `replacement_provider_session_started=false`.
- Replaced silent real-session fallback for:
  - `openai-api` with `previous_response_id`
  - `codex-cli` with `thread_id`
  - `claude-cli` with `session_id`
- Added explicit recovery metadata for `new-session-from-memory` so a fresh
  provider session is labeled as recovery-created rather than continuation.
- Added loop-level recovery handling:
  - headless fail-closed default
  - interactive retry
  - interactive new session from saved memory
  - interactive abort
- Added `pyocd-debug` recovery prompt wiring for freeform and rerun paths.
- Enriched provider memory entries with visible rationale, structured action
  payload, result status, artifact paths, changed files, codebase/workspace
  summary, failed hypotheses, refused/blocked paths, and acceptance constraints.
- Updated README/current-progress/R12 spec wording so local-memory recovery is
  not described as normal continuation for real-session providers.
- Replaced old fallback assertions and added strict failure/recovery/artifact
  tests.
- Ran the default non-hardware ladder green:
  - `uv run pytest -q`: 296 passed
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
- Ran the suite non-hardware ladder green:
  - `uv run pytest -q`: 296 passed
  - `uv run ruff check .`: passed
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`: passed
  - `uv run pytest -q tests/test_r11_benchmark.py`: 34 passed
  - `uv run python -m tests.harness.r11_benchmark --help`: passed
- Wrote deployment test spec:
  `markdowns/curr/branch-a-deployment-suite_spec.md`.
- Live substrate proof:
  - `nucleo_l476rg` host bootstrap passed.
  - `nucleo_l476rg` Stage 0 passed: probe, target, connect/read, flash, UART.
  - `nucleo_l476rg` Stage 1 smoke passed: flash, PC, symbol, UART.
  - Requested `nrf52833dk` Stage 0 was blocked by real silicon mismatch:
    attached Nordic probe `683377322` reported FICR `0x52840`, while the board
    config expects `0x52833`; the runner correctly skipped flash/UART after
    identity failure.
  - Supplemental attached-board proof for `nrf52840dk` passed host bootstrap,
    Stage 0, recover, and Stage 1 smoke.
- Live Codex/provider proof:
  - `pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg ...`
    passed healthy with run root `runs/20260629T010758Z-1b0e4509`.
    Six provider turns used one Codex `thread_id`
    `019f10eb-0e2f-72a3-aaa4-8f356a3f4d0f`; turns 2-6 resumed it; memory sync
    occurred on turn 5; final verification was flash/UART/symbol/green all
    true.
  - `pyocd-debug-brain benchmark --provider codex-cli --case-id
    nucleo_l476rg__b001_wrong_boot_text ...` passed full success, score 100,
    run root `runs/20260629T011204Z-41050715`. Eight provider turns used one
    Codex `thread_id` `019f10ee-d4fd-7671-9a17-050f0b6ca68c`; the run edited
    only `src/src/main.c`, built, flashed, and passed green check.
- Supplemental operator CLI proof:
  `pyocd-debug run --provider codex-cli --board-id nrf52840dk ...` passed
  healthy with run root `runs/20260629T011450Z-482561ab`. Seven provider
  turns used one Codex `thread_id`
  `019f10f1-5a3a-79a3-bac1-0ccff0695392`; final verification was
  flash/UART/symbol/green all true.
- Wrote final review artifact:
  `markdowns/curr/branch-a-strict-provider-recovery_review.md`.
- Recorded the official `nrf52833dk` live proof as externally blocked by
  attached `nrf52840` silicon.

## In progress

- None.

## TODO

- None for the implemented Branch A strict provider recovery surface.

## Limitations and known gaps

- Hidden model chain-of-thought will not be stored. The recovery ledger stores
  visible decision rationale, hypotheses, observations, action payloads,
  outcomes, and verification facts.
- Claude full official-pair proof may remain a user-run item if local Claude
  auth/model availability is not stable in this session.
- Real hardware claims will only be made for commands actually run here against
  attached boards.

## Hardware hand-off

Remaining official-pair hand-off when an actual nRF52833 DK is attached:

```bash
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

## Open decisions and surfaced issues

- None blocking. The user explicitly requested strict recovery plus new-session
  memory injection, and the build plan already supports that direction.

## Verified

- Spec/process scaffolding exists.
- `python -m compileall -q src tests`
- `uv run pytest -q tests/test_r12_turnkey_merge.py`
- `uv run pytest -q tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py tests/test_ux_cli.py`
  - Result: 100 passed.
- Default ladder green.
- Suite ladder green.
- Live STM32 Codex freeform healthy run green.
- Live STM32 Codex code-writing benchmark repair green.
- Live attached Nordic board proof green as `nrf52840dk`.

## Pending verification

- Official `nrf52833dk` live provider/hardware proof is pending until an actual
  nRF52833 DK is attached; the current attached Nordic board reports
  `FICR.INFO.PART=0x52840`.
