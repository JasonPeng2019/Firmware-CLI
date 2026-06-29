# Branch A deployment suite spec

## Goal

Prove Branch A strict provider-session recovery in deployment-shaped runs, not
only unit tests.

The suite must cover:

- multiple top-level user prompts;
- each top-level prompt running its own bounded provider/tool loop;
- real `codex-cli` provider continuity across multiple provider turns;
- explicit strict failure when a real provider resume handle cannot be reused;
- explicit, labeled recovery when the operator chooses a new provider session
  from saved memory;
- simple code-writing repair against scoped firmware workspaces;
- hardware proof on both connected official boards:
  - `nucleo_l476rg`
  - `nrf52833dk`

## Non-Hardware Contract Tests

These are the mandatory agent-verifiable tests before live hardware:

1. Full unit suite.
   - Command: `uv run pytest -q`
   - Required result: all tests pass.
2. Lint/type suite.
   - Command: `uv run ruff check .`
   - Command: `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`
   - Required result: no issues.
3. R11 harness sanity.
   - Command: `uv run pytest -q tests/test_r11_benchmark.py`
   - Command: `uv run python -m tests.harness.r11_benchmark --help`
   - Required result: pass/help exits 0.
4. Strict provider-resume contract.
   - Covered by `tests/test_r12_turnkey_merge.py`,
     `tests/test_r12_turnkey.py`, and `tests/test_ux_cli.py`.
   - Required assertions:
     - OpenAI `previous_response_id` SDK failure raises typed
       `ProviderResumeFailure`.
     - Codex `thread_id` resume failure raises typed `ProviderResumeFailure`.
     - Claude `session_id` resume failure raises typed `ProviderResumeFailure`.
     - Headless loop records `provider_resume_failed` and fails closed.
     - Interactive loop records retry/new-session/abort choices.
     - New-session recovery labels `recovery_created_new_session=true` and
       `replaced_remote_handle_id=<old handle>`.
     - UX prompt exposes retry/new/abort and says no new provider session has
       been started.
5. Crash memory ledger contract.
   - Recent memory entries must preserve visible rationale, action payload,
     result status, artifact paths, changed files when present, workspace
     summary, failed hypotheses, refused/blocked paths, acceptance constraints,
     and verification snapshot.
   - Hidden chain-of-thought must not be stored.

## Live Provider And Hardware Suite

Run these only when both boards and provider auth are present.

### 1. Board Substrate Proof

For `nucleo_l476rg`:

```bash
uv run python host_bootstrap.py --board-id nucleo_l476rg --install-packs
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
```

For `nrf52833dk`:

```bash
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

### 2. Multi-Prompt Codex Operator Scenario

Use one `pyocd-debug` shell process with `--provider codex-cli` selected. Run
these top-level prompts back to back:

1. Verify prompt:
   - Board: `nucleo_l476rg`
   - Prompt: `Verify the current reference firmware and explain the evidence.`
   - Required result: a run root is created, board evidence is collected, and
     the final result is healthy or diagnosed-only with no source edits.
2. Diagnose prompt:
   - Board: `nrf52833dk`
   - Prompt: `Diagnose the current firmware behavior without editing source.`
   - Required result: a separate run root is created, no provider/session state
     leaks from the first prompt, and no source edits occur.
3. Repair prompt:
   - Board: one scoped board with a bug workspace.
   - Prompt: `Repair the wrong boot text, rebuild, flash, and verify boot ok.`
   - Required result: the model reads workspace source, changes only allowed
     files, builds, flashes, runs green check, and writes a diff artifact.

After each prompt, inspect:

- `runs/<session_id>/run-metadata/turnkey_state.json`
- `runs/<session_id>/logs/model_turns.jsonl`
- `runs/<session_id>/logs/brain_events.jsonl`
- `runs/<session_id>/applied-patches/turnkey.diff` when code was changed

Required continuity assertions:

- all provider turns inside a top-level prompt use the same intended Codex
  `thread_id` unless explicit recovery is selected;
- no later prompt reuses a previous prompt's provider handle as if it were the
  same top-level prompt;
- if recovery starts a new provider session, artifacts label it as a new
  provider session.

### 3. Headless Codex Code-Writing Suite

Run representative bug cases with `codex-cli`:

```bash
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b001_wrong_boot_text
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b002_wrong_symbol_value
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b003_silent_uart
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b004_stuck_hardfault
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52833dk__b001_wrong_boot_text
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52833dk__b002_wrong_symbol_value
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52833dk__b003_silent_uart
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52833dk__b004_stuck_hardfault
```

Required result:

- each case reaches `fixed` or a documented legitimate block;
- build, flash, UART, symbol, and green-check evidence are present where
  relevant;
- no case silently starts a fresh provider session after resume failure.

### 4. Strict Failure Injection

Use the automated contract tests for deterministic failure injection. Live
provider failure injection is optional unless the provider CLI exposes a stable,
non-destructive way to invalidate a handle.

Required live claim boundary:

- If no stable live invalidation exists, report strict failure injection as
  agent-verified only and do not claim live-provider invalid-handle proof.

## Pass Criteria

Branch A is mergeable when:

- non-hardware suite is green;
- docs match strict provider behavior;
- live hardware/provider proof is green for the boards physically attached in
  the session, or hardware/provider work is explicitly marked pending with the
  exact commands and missing external prerequisite;
- any failure is fixed and rerun, unless it is a legitimate external blocker
  such as missing board, missing provider auth, or unavailable provider CLI.
