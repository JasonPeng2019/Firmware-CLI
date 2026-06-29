# Branch A strict provider recovery review

## Verdict

Code review result: clean for merge from the agent-verifiable and available
hardware/provider evidence.

Remaining live gap: official `nrf52833dk` proof is blocked by the attached
Nordic hardware reporting `FICR.INFO.PART=0x52840`, not `0x52833`.

## Findings

No code-blocking findings remain.

## Implemented Surface Reviewed

- Typed `ProviderResumeFailure` and `ProviderResumeFailureRecord` now capture:
  provider, remote strategy, continuation mode/path, handle kind, expected
  handle, turn index, failure text, local-memory availability, and
  `replacement_provider_session_started=false`.
- Real-session providers fail closed by default when a committed provider handle
  cannot resume:
  - `openai-api` with `previous_response_id`
  - `codex-cli` with `thread_id`
  - `claude-cli` with `session_id`
- Explicit recovery starts a new provider session only through
  `new-session-from-memory` and labels the event/metadata as a new session.
- Headless `pyocd-debug-brain` defaults to fail-closed.
- Interactive `pyocd-debug` offers retry, new session from saved memory, or
  abort.
- Provider memory entries now preserve visible rationale, structured action
  payload, result status, artifact paths, changed files, codebase/workspace
  summary, failed hypotheses, refused/blocked paths, acceptance constraints,
  and verification snapshot.

## Verification

Agent-verifiable non-hardware:

- `uv run pytest -q`
  - 296 passed.
- `uv run ruff check .`
  - passed.
- `uv run mypy src`
  - passed.
- `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`
  - passed.
- `uv run pytest -q tests/test_r11_benchmark.py`
  - 34 passed.
- `uv run python -m tests.harness.r11_benchmark --help`
  - passed.
- Targeted suite:
  - `uv run pytest -q tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py tests/test_ux_cli.py`
  - 100 passed.

Live hardware/provider:

- `nucleo_l476rg`
  - host bootstrap passed.
  - Stage 0 passed.
  - Stage 1 smoke passed.
  - Real Codex freeform run passed:
    `runs/20260629T010758Z-1b0e4509`.
    Six provider turns used one Codex `thread_id`; final verification
    flash/UART/symbol/green all true.
  - Real Codex code-writing benchmark passed:
    `nucleo_l476rg__b001_wrong_boot_text`,
    `runs/20260629T011204Z-41050715`, score 100.
    Eight provider turns used one Codex `thread_id`; changed only
    `src/src/main.c`; build/flash/green check passed.
- Requested `nrf52833dk`
  - host bootstrap saw the Nordic probe and COM port.
  - Stage 0 failed silicon identity: actual `0x52840`, expected `0x52833`.
  - Flash/UART for `nrf52833dk` were correctly skipped after the identity
    failure.
- Supplemental attached Nordic proof:
  - `nrf52840dk` host bootstrap passed.
  - `nrf52840dk` Stage 0 passed including recover.
  - `nrf52840dk` Stage 1 smoke passed.
  - Operator CLI Codex run passed:
    `runs/20260629T011450Z-482561ab`.
    Seven provider turns used one Codex `thread_id`; final verification
    flash/UART/symbol/green all true.

## Residual Risk

- Live invalid-handle failure injection is covered by deterministic tests, not
  by a live provider invalidation command. No stable, non-destructive live
  Codex handle invalidation path was used.
- Full official-pair hardware proof needs an actual attached nRF52833 DK.
- Claude live official-pair proof remains pending user-run work, as requested.
