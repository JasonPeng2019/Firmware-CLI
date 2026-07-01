# Process ledger for r12-tier2-memory-bridge

## Goal and roadmap anchor

Task: Implement the R12 Tier 2 memory bridge spec as the hard bar, with software-only validation and no hardware tests.
Roadmap anchor: R12 Stage 5 Wave 1 prompt/memory cost hardening; prototype `things-to-change` item 1 / item 14.

## Done

- Reconciled the active Tier 2 spec against the build plan, R12 prompt/memory spec, current code, and operator CLI surfaces.
- Added the Tier 2 mid-history lane to provider session state, serialization, summary records, memory rendering, compaction planning, deterministic compaction, and model-summary compaction.
- Changed the compaction path so Tier 1 overflow deterministically becomes Tier 2 first; provider-backed/model compression is only invoked when Tier 2 overflows into Tier 3.
- Threaded Tier 2 limits through `TurnkeyInvocation`, env config, headless brain CLI, module benchmark CLI, operator CLI, operator shell context, saved request artifacts, and rerun behavior.
- Added focused tests for Tier 2 state retention, Tier 2 overflow into Tier 3, model-summary invocation timing, config/env controls, CLI/parser controls, and shell memory controls.
- Ran focused regression tests for provider memory and UX memory controls.
- Ran the full Python-change gate: Ruff check/fix, Ruff format, Pyright, and full pytest.
- Ran the FirmCLI suite ladder preset.
- Ran no-hardware real-provider behavior checks for both Codex CLI and Claude CLI, including Branch C skip-hardware prompt rows and direct provider summary smokes.
- Inspected provider outputs: Codex CLI returned a valid `TurnDecision` with `load_tool_details`, Claude CLI returned a valid `TurnDecision` with `finalize`, and both provider summary smokes returned bounded Tier 3 summary text.
- Ran the markdown-audit workflow and synced current status docs.

## In progress

- None.

## TODO

- None for this Tier 2 memory bridge implementation.

## Limitations and known gaps

- Hardware validation is intentionally out of scope for this feature per user instruction; no board flashing, attached-board validation, or two-board hardware proof will be run.
- Live provider proof may be limited by provider CLI availability, credentials, or quota; fake-provider tests still exercise the same brain memory compaction loop.

## Hardware hand-off

- None required for this CLI-interaction memory feature.

## Open decisions and surfaced issues

- Tier 2 is deterministic brain-authored compaction from Tier 1. Only Tier 3 may use provider/model-backed summary mode.
- The public env var for the Tier 2 render cap is `PYOCD_TURNKEY_MID_HISTORY_RENDER_CHAR_LIMIT`, matching the spec.

## Verified

- Spec and implementation reconciliation completed.
- Focused provider-memory tests:
  - `uv run pytest -q tests/test_r12_turnkey.py -k "provider_session_state_serialization_and_deterministic_compaction or tier2_overflow or model_summary_waits_for_tier2_overflow or memory_config_defaults_and_env_overrides or memory_compaction_triggers_on_recent_memory_char_limit or module_benchmark_cli"`
  - Result: `7 passed, 66 deselected`.
- Focused UX memory-control tests:
  - `uv run pytest -q tests/test_ux_cli.py -k "memory_controls or guided_verify_ignores_workspace_context_but_keeps_artifact_context or shell_memory_commands"`
  - Result: `3 passed, 25 deselected`.
- Python-change gate:
  - `python .codex\skills\python-change\scripts\run_python_change_checks.py`
  - Result: Ruff, Ruff format, Pyright `0` diagnostics, and full pytest `381 passed`.
- FirmCLI suite ladder:
  - `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  - Result: full pytest `381 passed`, Ruff pass, mypy pass, R11 benchmark tests `34 passed`, and benchmark help smoke pass.
- Real-provider no-hardware Branch C check:
  - `uv run python -m tests.harness.branch_c_tests --board-id nrf52833dk --skip-hardware --provider codex-cli --provider claude-cli --provider-timeout-seconds 120`
  - Result: `6 passed, 0 failed, 0 skipped`.
- Direct real-provider summary smoke:
  - Codex CLI returned a bounded summary of 429 chars.
  - Claude CLI returned a bounded summary of 362 chars.
- Process cleanup:
  - Audited provider/process cleanup after the no-hardware provider checks.
  - No spawned Branch C, inline provider-summary, or provider child processes remained; only pre-existing IDE/Codex/MCP processes and the audit PowerShell itself matched the broad process search.

## Pending verification

- Live `openai-api` / `anthropic-api` proof still depends on credentials and credits and is not required for this feature.
- Hardware proof is intentionally out of scope for this CLI-interaction memory feature.
