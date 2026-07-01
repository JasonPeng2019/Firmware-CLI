> STATUS: IMPLEMENTED AND VALIDATED - attached-board/API-simulated hard-bar pass complete.

# R12 Prompt And Memory Cost Hardening Process

## Goal And Roadmap Anchor

Implement `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md` as a hard bar for the R12 turnkey product. The roadmap anchor is R12 Wave 1 deployment hardening plus Wave 2 Module G static-context efficiency, without adding cross-invocation provider session persistence.

## Done

- Created the hard-bar spec at `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`.
- Loaded the FirmCLI write-process, test-suite, fix-bug, spec-loop, build, review, workflow-core, and Python-change workflows.
- Reconciled the spec against the R12 build-plan/current-progress direction: compact local memory and periodic sync remain in scope; cross-invocation provider session persistence is explicitly out of scope.
- Implemented split prompt bodies: bootstrap/full context remains available for setup, while ordinary later turns use a compact canonical state digest.
- Added rendered-vs-available prompt accounting with section hashes and explicit memory/schema/tool-schema injection booleans.
- Bounded in-run provider memory defaults to a two-turn detailed window plus a hard-limited rolling summary, and summary-mode output is validated instead of silently truncated.
- Added common `connect` and `run_green_check` detail preload, with CLI/env controls to disable or tune prompt-memory behavior.
- Follow-up audit fix: loaded detail bodies render only on the preload/detail-load/context-expansion turn that needs them, then later compact turns carry status plus hashes.
- Follow-up audit fix: selected turnkey skill facts render in full at bootstrap/sync, while ordinary remote-delta turns carry a compact skill digest with IDs/counts/hashes.
- Added focused regression coverage for prompt accounting, memory config/env controls, common detail preload, Branch C harness prompt imports, and UX parser controls.
- Synced docs in `README.md`, `markdowns/current-progress.md`, `markdowns/things-to-change.md`, and `markdowns/R12_P_SPLIT.md`.

## In Progress

- None.

## TODO

- None for the attached-board, credentials-free/API-simulated hard bar.

## Limitations And Known Gaps

- Exact official `nrf52833dk` proof depends on the connected Nordic board matching that target.
- API-provider live proof depends on `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`; without credentials, API paths must be simulated.
- The attached Nordic board for this run was `nrf52840dk`; exact official `nrf52833dk` hardware proof remains a separate hardware availability boundary.
- The process intentionally excludes cross-invocation provider session persistence.

## Hardware Hand-Off

No hand-off is pending for the two attached boards. Exact official `nrf52833dk` and live API-provider credential proof remain external boundaries.

## Open Decisions And Surfaced Issues

- None requiring user decision at process start. The spec's exclusion of cross-invocation session persistence is now treated as the governing hard bar for this process.

## Verified

- Process ledger exists and is aligned with the hard-bar spec.
- Focused prompt/memory/UX checks passed:
  - `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle_exposes_static_and_dynamic_render_modes or memory_config_defaults_and_env_overrides or preloads_common_details"` -> `3 passed`
  - `uv run pytest -q tests/test_ux_cli.py -k "memory_controls"` -> `1 passed`
- R12/UX regression set passed:
  - `uv run pytest -q tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py tests/test_branch_c_harness.py tests/test_ux_cli.py` -> `130 passed`
- Full pytest passed:
  - `uv run pytest -q` -> `360 passed`
- Ruff and Pyright are currently green:
  - `uv run ruff check .` -> passed
  - `uv run pyright --outputjson` -> `0` diagnostics
- Final Python-change gate passed after all Python edits:
  - `uv run ruff check --fix .` -> passed
  - `uv run ruff format .` -> passed
  - `uv run pyright --outputjson` -> `0` diagnostics
  - `uv run pytest -q` -> `361 passed`
- Final FirmCLI suite ladder passed:
  - `uv run python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\r12-prompt-memory-cost-hardening-final-suite-report.txt`
  - full pytest `361 passed`, ruff clean, mypy clean, R11 benchmark tests `34 passed`, R11 benchmark help rendered.
- Branch C provider/hardware matrix passed on both attached boards with both subscription CLI providers:
  - `uv run python tests\harness\branch_c_tests.py --board-id nucleo_l476rg --provider codex-cli --provider claude-cli --fail-on-skip` -> `11 passed`
    - live run roots: `runs/20260701T045813Z-d7318dfe` (`codex-cli`), `runs/20260701T045844Z-dee0e49a` (`claude-cli`)
  - `uv run python tests\harness\branch_c_tests.py --board-id nrf52840dk --provider codex-cli --provider claude-cli --fail-on-skip` -> `11 passed`
    - live run roots: `runs/20260701T050115Z-578504fc` (`codex-cli`), `runs/20260701T050148Z-337dcfd8` (`claude-cli`)
- Stage 1 smoke passed on both attached boards:
  - `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
  - `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`
- Post-fix real code-writing benchmark repair passed on both attached boards with both CLI providers:
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b001_wrong_boot_text` -> `FULL_SUCCESS`, run `runs/20260701T052759Z-1aa06762`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__b001_wrong_boot_text` -> `FULL_SUCCESS`, run `runs/20260701T053213Z-f96b93e0`
  - `uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__b001_wrong_boot_text` -> `FULL_SUCCESS`, run `runs/20260701T053722Z-bee29b32`
  - `uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nrf52840dk__b001_wrong_boot_text` -> `FULL_SUCCESS`, run `runs/20260701T054004Z-1d30d2d3`
- Artifact audit after the final b001 matrix:
  - all four final b001 runs ended `fixed/code_bug`, changed only the isolated benchmark workspace C source file, and had `flash_ok=true`, `uart_ok=true`, `symbol_ok=true`, `green_check_ok=true`.
  - ordinary post-detail `remote-delta` turns used compact skill digests and rendered about `7.3k-7.8k` chars with `memory_injected=false` and `decision_schema_injected=false`.
  - focused detail-load turns were allowed to exceed the ordinary delta target because they intentionally carried full focused tool bodies.
- API-provider paths were exercised through the credentials-free fake-provider/unit coverage in the full pytest suite, including OpenAI/Anthropic request/response handling, prompt accounting, retry behavior, resume handling, timeout/error surfaces, and summary-mode parsing. Live API calls were not run because API credentials/credits were unavailable.
- Follow-up credentials-free API deployment-path validation passed on 2026-07-01:
  - Added and ran `test_openai_api_provider_factory_turnkey_loop_smoke`, which monkeypatches the real OpenAI adapter factory path, drives `run_turnkey_with_provider`, verifies Responses-style `previous_response_id` chaining, and confirms the second provider turn renders as `remote-delta` without provider-memory or full decision-schema injection.
  - Added and ran `test_anthropic_api_provider_factory_turnkey_loop_smoke`, which monkeypatches the real Anthropic adapter factory path, drives `run_turnkey_with_provider`, verifies local-memory-only continuation for the stateless Messages API shape, and confirms later-turn provider memory injection behavior.
  - `uv run pytest -q tests/test_r12_turnkey.py -k "api_provider_factory_turnkey_loop_smoke or openai or api or resume_failure or provider_setup_failed or model_summary or green_check or details"` -> `17 passed, 52 deselected`
  - `uv run pytest -q tests/test_r12_turnkey_merge.py -k "openai or anthropic or codex_cli_provider_surfaces_subprocess_timeout or claude_cli_provider_surfaces_subprocess_timeout or retry_updates_prompt_metadata or previous_response_failure"` -> `7 passed, 23 deselected`
  - `uv run python .codex\skills\python-change\scripts\run_python_change_checks.py` -> Ruff clean, Pyright `0` diagnostics, full pytest `363 passed`
  - `uv run python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\r12-api-sim-prompt-memory-suite-report.txt` -> suite ladder passed: full pytest `363 passed`, Ruff clean, mypy clean, R11 benchmark tests `34 passed`, R11 benchmark help rendered.
- Follow-up Claude CLI attached-board proof after local usage/auth was available:
  - `uv run python tests\harness\branch_c_tests.py --board-id nucleo_l476rg --provider claude-cli --fail-on-skip` -> `9 passed, 0 failed, 0 skipped`, run root `runs/20260701T054747Z-fa210e66`
  - `uv run python tests\harness\branch_c_tests.py --board-id nrf52840dk --provider claude-cli --fail-on-skip` -> `9 passed, 0 failed, 0 skipped`, run root `runs/20260701T054938Z-578b5878`
  - `uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__b001_wrong_boot_text` -> `FULL_SUCCESS`, run root `runs/20260701T055138Z-0be02f11`
  - A later rerun of `nrf52840dk__b001_wrong_boot_text` was intentionally interrupted by the operator; no leftover benchmark subprocess remained. The completed Claude nRF52840 b001 proof for this implementation remains `runs/20260701T054004Z-1d30d2d3`.
- Cleanup audit after provider/hardware checks found no still-running test/benchmark/provider subprocesses from this suite. Remaining `codex.exe`, `claude.exe`, `node_repl.exe`, and `uv run pyocd-debug-mcp` processes matched pre-existing Codex app/VS Code extension app-server/MCP process trees.

## Pending Verification

- Live `openai-api` / `anthropic-api` provider proof when credentials are available.
- Exact official `nrf52833dk` hardware proof when that board is attached.
