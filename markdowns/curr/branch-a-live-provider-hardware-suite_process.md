# Process ledger for Branch A live provider hardware suite

## Goal and roadmap anchor

Validate merged `P-Wave-A` after the additive Branch A/B merge against the live
`R12` turnkey proof boundary: both real local CLI providers, both attached
boards, multiple top-level provider loops, code-writing repairs, rebuilds,
flashes, final green verification, and artifact inspection.

Roadmap anchor: `R12` / `G7`.

## Done

- Loaded the `firmcli-spec-loop`, `firmcli-test-suite`, `firmcli-fix-bug`,
  `firmcli-specs`, and `firmcli-workflow-core` rules.
- Reconciled the request against the build plan, README, ROADMAP,
  `current-progress.md`, current CLI code, benchmark runner, and suite manifest.
- Created `markdowns/curr/branch-a-live-provider-hardware-suite_spec.md`.
- Archived completed/stale `markdowns/curr/` artifacts into
  `markdowns/tmp/curr-archive-20260628/`, including the stale Branch A
  deployment spec with outdated case IDs.
- Updated `markdowns/curr/README.md` to list the active docs for this pass.
- Confirmed provider CLIs are installed:
  - `codex --version`: `codex-cli 0.142.2`
  - `claude --version`: `2.1.76 (Claude Code)`
- Non-hardware suite ladder passed:
  - `uv run pytest -q`: 319 passed
  - `uv run ruff check .`: passed
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`: passed
  - `uv run pytest -q tests/test_r11_benchmark.py`: 34 passed
  - `uv run python -m tests.harness.r11_benchmark --help`: passed
- Attached pair discovered through `host_bootstrap.py`:
  - `nucleo_l476rg`: ST-Link `066FFF514988525067233337`, serial `COM12`
- `nrf52833dk` attachment readiness matched the Nordic probe/serial metadata,
  but Stage 0 silicon identity check failed: FICR part was `0x52840`, expected
  `0x52833`. This proves the attached Nordic board is not the official scoped
  `nrf52833dk`.
- The attached Nordic board will be tested as retained alternate
  `nrf52840dk`; official `nrf52833dk` closure remains pending.
- `nucleo_l476rg` Stage 0 passed: reference ELF flashed and UART matched
  `boot ok` on COM12.
- `nucleo_l476rg` Stage 1 passed: flashed `firmware.hex`, read
  `stage1_known_value=0x1234ABCD`, and UART matched `boot ok`.
- `nrf52840dk` host bootstrap passed: J-Link `683377322`, serial `COM11`.
- `nrf52840dk` Stage 0 passed: silicon identity `0x52840`, reference ELF
  flashed, UART matched `boot ok`, and recover/unlock cycle completed.
- `nrf52840dk` Stage 1 passed: flashed `firmware.hex`, read
  `stage1_known_value=0x1234ABCD`, and UART matched `boot ok`.
- Freeform healthy provider runs passed:
  - `codex-cli` + `nucleo_l476rg`: `20260629T035106Z-4a223380`,
    `HEALTHY_CONFIRMED`, flash/UART/symbol/green all true.
  - `codex-cli` + `nrf52840dk`: `20260629T035219Z-0a1876b7`,
    `HEALTHY_CONFIRMED`, flash/UART/symbol/green all true.
  - `claude-cli` + `nucleo_l476rg`: `20260629T035340Z-f4903419`,
    `HEALTHY_CONFIRMED`, flash/UART/symbol/green all true.
  - `claude-cli` + `nrf52840dk`: `20260629T035532Z-ada74c86`,
    `HEALTHY_CONFIRMED`, flash/UART/symbol/green all true.
- Public client-action smoke passed:
  - `codex-cli` + `nucleo_l476rg`, with
    `--client-action uart_write=tests/fixtures/client_actions/uart_write.py`:
    `20260629T035801Z-d42178a3`, `HEALTHY_CONFIRMED`.
- Code-writing benchmark cases passed for `codex-cli`:
  - `nucleo_l476rg__b001_wrong_boot_text`: `FULL_SUCCESS`, score 100,
    session `20260629T040142Z-f304ef93`.
  - `nucleo_l476rg__b002_wrong_known_value`: `FULL_SUCCESS`, score 100,
    session `20260629T040414Z-abe5aa61`.
  - `nrf52840dk__b001_wrong_boot_text`: `FULL_SUCCESS`, score 100,
    session `20260629T040848Z-c7e6a8be`.
  - `nrf52840dk__b002_wrong_known_value`: `FULL_SUCCESS`, score 100,
    session `20260629T041145Z-a4533224`.
- Fix-bug loop: Claude CLI failed `nucleo_l476rg__b002_wrong_known_value`
  before the fix with `WinError 206` because the Claude adapter passed a long
  prompt as a positional command-line argument. The model had repaired the code
  and runner-owned final verification was green, but the later provider turn
  could not start on Windows.
- Fix applied: `provider_claude_cli.py` now sends Claude prompt content over
  stdin, matching the CLI pipe contract and avoiding Windows command-line length
  limits. Regression guard added in `tests/test_r12_turnkey.py`.
- Fix validation:
  - `uv run pytest -q tests/test_r12_turnkey.py`: 51 passed.
  - `uv run ruff check src/pyocd_debug_mcp/brain/provider_claude_cli.py tests/test_r12_turnkey.py`: passed.
  - `uv run mypy src/pyocd_debug_mcp/brain/provider_claude_cli.py`: passed.
  - Repro rerun `claude-cli` + `nucleo_l476rg__b002_wrong_known_value`:
    `FULL_SUCCESS`, score 100, session `20260629T042202Z-c0d13cb9`.
- Post-fix non-hardware suite ladder rerun passed:
  - `uv run pytest -q`: 319 passed.
  - `uv run ruff check .`: passed.
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`: passed.
  - `uv run pytest -q tests/test_r11_benchmark.py`: 34 passed.
  - `uv run python -m tests.harness.r11_benchmark --help`: passed.
- Post-fix hardware substrate rerun passed:
  - `nucleo_l476rg` Stage 0 and Stage 1 passed.
  - `nrf52840dk` Stage 0 with recover and Stage 1 passed.
- Post-fix freeform healthy provider rerun passed:
  - `codex-cli` + `nucleo_l476rg`: `20260629T043122Z-111a3465`.
  - `codex-cli` + `nrf52840dk`: `20260629T043259Z-e86e7433`.
  - `claude-cli` + `nucleo_l476rg`: `20260629T043423Z-e68dcc66`.
  - `claude-cli` + `nrf52840dk`: `20260629T043548Z-98a1ad18`.
- Post-fix public client-action smoke passed:
  - `codex-cli` + `nucleo_l476rg`: `20260629T043927Z-62698a08`.
- Post-fix code-writing benchmark cases passed for `codex-cli`:
  - `nucleo_l476rg__b001_wrong_boot_text`: `FULL_SUCCESS`, score 100,
    session `20260629T044139Z-2ccda5da`.
  - `nucleo_l476rg__b002_wrong_known_value`: `FULL_SUCCESS`, score 100,
    session `20260629T044416Z-2157a0cb`.
  - `nrf52840dk__b001_wrong_boot_text`: `FULL_SUCCESS`, score 100,
    session `20260629T044650Z-f89de0e6`.
  - `nrf52840dk__b002_wrong_known_value`: `FULL_SUCCESS`, score 100,
    session `20260629T045049Z-583a08f9`.
- Second fix-bug loop: Claude emitted a batched action name
  `server_tool:connect`, which the prompt made understandable but the batch
  normalizer refused as `brain/unsupported-batch-action`. The memory/artifact
  ledger captured the read/edit/build/refusal sequence and the remote Claude
  session handle.
- Second fix applied: namespaced `server_tool:<tool>` action names now
  normalize to server-native tool actions in both `loop.py` and the Branch B
  action policy. Regression guards were added to `tests/test_r12_turnkey.py`
  and `tests/test_p0_foundation.py`.
- Second fix validation:
  - targeted pytest for namespaced batch action and policy tests: 2 passed.
  - targeted ruff for touched files: passed.
  - targeted mypy for touched source files: passed.
- Retry of `claude-cli` + `nrf52840dk__b002_wrong_known_value` after the
  second fix is temporarily blocked by external Claude quota before any board
  session: `You're out of extra usage - resets 4:50am (America/New_York)`.
- Representative artifact inspection passed:
  - `runs/20260629T043927Z-62698a08/run-metadata/client_actions.json`
    records `uart_write`, SHA-256, relative path, and `executed=true`.
  - `runs/20260629T044139Z-2ccda5da/run-metadata/score.json` records Codex
    runner-owned flash/UART/symbol/green all true, score 100, and exactly one
    session id.
  - `runs/20260629T045740Z-e4bdc996/run-metadata/score.json` records Claude
    runner-owned flash/UART/symbol/green all true, score 100, and exactly one
    session id.
  - `runs/20260629T045740Z-e4bdc996/logs/model_turns.jsonl` records Claude
    `remote_handle_kind=session_id`, remote resume, and no recovery-created
    replacement session.
- Code-writing benchmark cases passed for `claude-cli` after/around the fix:
  - `nucleo_l476rg__b001_wrong_boot_text`: `FULL_SUCCESS`, score 100,
    session `20260629T041550Z-0632e95d`.
  - `nucleo_l476rg__b002_wrong_known_value`: `FULL_SUCCESS`, score 100,
    session `20260629T042202Z-c0d13cb9`.
  - `nrf52840dk__b001_wrong_boot_text`: `FULL_SUCCESS`, score 100,
    session `20260629T042514Z-de752672`.
  - `nrf52840dk__b002_wrong_known_value`: `FULL_SUCCESS`, score 100,
    session `20260629T042822Z-17b76990`.

## In progress

- Complete local validation/artifact inspection while waiting for Claude quota
  reset, then rerun the full live matrix on the final fixed branch state.

## TODO

- Inspect representative run artifacts.
- If failures are code defects, route through fix-bug, rerun targeted checks,
  then rerun this suite from the beginning.
- Update README/current-progress if the live status boundary changes.
- Create a review artifact and push `P-Wave-A` if the full matrix is green.

## Limitations and known gaps

- Sequential `pyocd-debug-brain run` and `benchmark` invocations are the current
  product-supported way to simulate multiple user prompts. A single interactive
  REPL transcript with several `/prompt` turns is not required unless the
  existing shell can be driven reliably without inventing a new feature.
- Official scoped-pair closure requires an attached `nrf52833dk`, not only the
  retained alternate `nrf52840dk`.
- Provider CLI auth/rate-limit failures are external deployment blockers unless
  the failure comes from this repo's adapter code.
- Claude CLI is temporarily quota-blocked until 4:50am America/New_York during
  the final rerun.

## Hardware hand-off

None yet. This session has access to the local workspace and will attempt the
hardware commands directly.

## Open decisions and surfaced issues

- No settled-decision conflict found before test execution.
- Official `nrf52833dk` proof cannot be completed with the currently attached
  Nordic hardware because the board identifies as `0x52840`.

## Verified

- Branch `P-Wave-A` was clean before this doc/spec work started.
- The verification spec is anchored to the actual `pyocd-debug-brain` CLI,
  benchmark runner, and configured suites in the current repo.

## Pending verification

- Final post-second-fix non-hardware suite ladder rerun.
- Final post-second-fix live provider matrix after Claude quota reset.
