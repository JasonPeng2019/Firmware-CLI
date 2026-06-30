# Review for r12-delta-compact-indexes

Task: Review compact skill/tool indexes in remote-delta provider turns

## Verdict

CLEAN

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |
| none | spec conformance | n/a | No must-fix findings. | n/a |

## Hardware hand-off status

- Codex CLI provider + live hardware smoke passed on both attached boards:
  - `nucleo_l476rg`: `runs/20260630T200822Z-b69e332f`
  - `nrf52840dk`: `runs/20260630T201005Z-f2c1d62b`
- The live run artifacts show `remote-delta` turns with
  `static_tool_schema_injected=true`, `memory_injected=false`, and
  `decision_schema_injected=false`.
- Claude CLI live proof was not rerun for this change; prior session state had
  Claude CLI blocked by local login.

## What's genuinely good

- The change is localized to prompt rendering and provider metadata.
- Memory cadence remains controlled by `native_sync_every`; no provider memory
  is injected into normal `remote-delta` turns.
- Full MCP schemas and full decision schemas remain out of normal deltas.
- Focused tests cover the shared prompt bundle plus OpenAI, Claude CLI, and
  Codex CLI remote-primary adapter paths.

## Verification

- Focused prompt/provider test:
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle" tests/test_r12_turnkey_merge.py -k "previous_response_id or resumes_remote_session or resumes_remote_thread or retry_updates_prompt_metadata"`
  -> `5 passed, 90 deselected`.
- Python-change gate:
  `uv run python .codex/skills/python-change/scripts/run_python_change_checks.py`
  -> Ruff check/format, Pyright JSON, and full pytest passed with `359 passed`.
- FirmCLI suite ladder:
  `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/r12-delta-compact-indexes-suite-report.txt`
  -> pytest, Ruff, mypy, R11 benchmark tests, and R11 benchmark help all passed.
- Live provider/hardware checks:
  - `uv run python -m tests.harness.branch_c_tests --board-id nucleo_l476rg --provider codex-cli --provider-timeout-seconds 240`
    -> `9 passed, 0 failed, 0 skipped`.
  - `uv run python -m tests.harness.branch_c_tests --board-id nrf52840dk --provider codex-cli --provider-timeout-seconds 240`
    -> `9 passed, 0 failed, 0 skipped`.
