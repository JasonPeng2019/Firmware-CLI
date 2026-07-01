# Wave 1 Full Product Suite Provider-Native Validation

Status: VALIDATION RECORD - green for the attached Wave 1 deployment surface on 2026-07-01.

## Goal

Validate the full Wave 1 product suite after the provider-native skill bridge and prompt/memory cost hardening work. The run must prove real hardware behavior where hardware is attached, real CLI-provider behavior for Codex and Claude, simulated API behavior where live API credentials are unavailable, and product behavior against the Wave 1 customer-facing bar.

## Attached Hardware

- `nucleo_l476rg`: connected through ST-Link UID `066FFF514988525067233337`.
- `nrf52840dk`: connected through J-Link UID `683377322`.
- `nrf52833dk`: not attached in this environment; no green claim is made for that physical board in this run.

## Validation Matrix

| Area | Command or evidence | Result |
| --- | --- | --- |
| Probe inventory | `PYTHONIOENCODING=utf-8 uv run pyocd list --probes` | PASS; Nucleo and nRF52840DK detected. |
| Python change gate | `python` plus `.codex/skills/python-change/scripts/run_python_change_checks.py` and the continue-on-error flag | PASS; Ruff fix, Ruff format, Pyright, and full pytest green. |
| Full suite ladder | `python` plus `.codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py` and the suite preset | PASS; pytest, Ruff, mypy, R11 benchmark tests, and harness help. |
| Focused API simulation | `uv run pytest -q tests/test_provider_native_skills.py tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py -k ...` | PASS; `30 passed`, covering simulated OpenAI/Codex and Anthropic/Claude provider paths, retries, timeouts, setup failure, resume failure, fallback, and model-summary behavior. |
| Post-audit focused API simulation | Same focused command after projection overwrite protection | PASS; `32 passed, 78 deselected`. |
| Branch C Nucleo/Codex | `uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --provider codex-cli --provider-timeout-seconds 300 --fail-on-skip` | PASS; `9 passed`, real provider turn, real MCP server, live board touch. |
| Branch C Nucleo/Claude | Same harness with `--provider claude-cli` | PASS; `9 passed`, real provider turn, real MCP server, live board touch. |
| Branch C nRF/Codex | Same harness with `--board-id nrf52840dk --provider codex-cli` | PASS; `9 passed`, real provider turn, real MCP server, live board touch. |
| Branch C nRF/Claude | Same harness with `--board-id nrf52840dk --provider claude-cli` | PASS; `9 passed`, real provider turn, real MCP server, live board touch. |
| Nucleo Codex code-writing benchmark | `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b001_wrong_boot_text --provider-native-skills require --max-iters 6` | FULL_SUCCESS, score 100, run `20260701T074737Z-99dd8d5c`. |
| Nucleo Claude code-writing benchmark | Same benchmark with `--provider claude-cli` | FULL_SUCCESS, score 100, run `20260701T075915Z-31ddee72`. |
| nRF Codex code-writing benchmark | Same benchmark with case `nrf52840dk__b001_wrong_boot_text` and `--provider codex-cli` | FULL_SUCCESS, score 100, run `20260701T080359Z-a02ea3ab`. |
| nRF Claude code-writing benchmark | Same benchmark with `--provider claude-cli` | FULL_SUCCESS, score 100, run `20260701T080937Z-8529049c`. |
| Post-audit Nucleo Codex code-writing benchmark | `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b001_wrong_boot_text --provider-native-skills require --max-iters 6` | FULL_SUCCESS, score 100, run `20260701T083254Z-987cf201`. |
| Post-audit Nucleo Claude code-writing benchmark | Same benchmark with `--provider claude-cli` | FULL_SUCCESS, score 100, run `20260701T083805Z-ad7caba6`. |
| Post-audit nRF Codex code-writing benchmark | Same benchmark with case `nrf52840dk__b001_wrong_boot_text` and `--provider codex-cli` | FULL_SUCCESS, score 100, run `20260701T084025Z-552f6748`. |
| Post-audit nRF Claude code-writing benchmark | Same benchmark with `--provider claude-cli` | FULL_SUCCESS, score 100, run `20260701T084536Z-120d39a4`. |
| Process cleanup audit | `Get-CimInstance Win32_Process` filtered for FirmCLI/provider/MCP processes | PASS; only existing Codex/Claude app processes and the pre-existing MCP worker tree were observed. |

## Behavioral Audit

The real provider runs matched the desired Wave 1 behavior:

- Providers performed self-directed host-side work in the run workspace, inspected and patched firmware source, then returned governed decisions/actions.
- Board actions stayed behind FirmCLI-governed MCP calls.
- `run_green_check` rebuilt, flashed, read UART, read the symbol, and required all verification flags before `fixed` finalization.
- Changed files for all four live code-writing runs were exactly the benchmark
  workspace firmware file src/src/main.c inside each run workspace.
- Provider-native skill projection was available in real runs:
  - Codex used `.codex/skills`.
  - Claude used `.claude/skills` with `Skill(firmcli-firmware-debug)` allowed.
- Prompt-cost hardening behaved as required:
  - Bootstrap turns carried full context and decision schema.
  - Later turns used `remote-delta`.
  - Later turns did not reinject the full decision schema.
  - Memory was not injected before the configured cadence.
  - Representative later-turn rendered prompt sizes stayed around 8k chars for the successful two-turn Claude runs.

## Issue Found And Fixed

During the Nucleo/Claude live benchmark, the firmware behavior was correct and hardware verification passed, but the score initially returned partial success because provider-native runtime projection files under `.claude/skills` were counted as changed files.

Fix:

- `src/pyocd_debug_mcp/brain/workspace.py` now ignores runtime context directories `.agents`, `.claude`, and `.codex` when reporting changed files or writing diffs.
- `src/pyocd_debug_mcp/benchmark_support.py` applies the same filter for benchmark scoring.
- Regression coverage was added to `tests/test_r11_benchmark.py` and `tests/test_r12_turnkey.py`.

The failed Nucleo/Claude row was rerun after the fix and passed FULL_SUCCESS with score 100.

## Follow-Up Adversarial Fix

A later adversarial audit found one more valid product-safety gap: provider-native projection could overwrite a pre-existing user-owned `.codex/skills/<skill>` or `.claude/skills/<skill>` folder in a real workspace if the skill ID collided with FirmCLI's generated projection.

Fix:

- Projected skill folders now carry `.firmcli-provider-native-projection.json`.
- FirmCLI refuses to replace an existing projected-skill directory unless that marker is present.
- Focused regression tests cover both refusing an unmarked user-owned directory and replacing a prior marked FirmCLI projection.
- Python-change, suite ladder, focused API simulation, Branch C real hardware rows, and representative code-writing repair rows were rerun after the fix and stayed green.

## API Path Limits

Live Codex API and Claude API calls were not run because live API credentials/credits are unavailable in this environment. The API paths were validated to the greatest extent possible through simulated provider clients that exercise the same FirmCLI provider-turn loop, request/response handling, retry metadata, timeout behavior, setup-failure handling, resume-failure handling, fallback behavior, and model-summary compaction behavior.

## Remaining Non-Claims

- This record does not claim live API-provider billing/transport success.
- This record does not claim real `nrf52833dk` hardware success because that board was not attached.
- This record does not claim a fresh-machine installer validation; it validates this repo checkout and the currently connected hardware deployment surface.
