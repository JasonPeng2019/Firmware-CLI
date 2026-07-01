> STATUS: IMPLEMENTED VALIDATION RECORD - attached-board CLI proof and credentials-free API simulation complete; live API/exact nRF52833 proof remain pending.

# wave1 full suite claude restored

## Goal in plain English

Task: Full Wave 1 suite after Claude CLI auth restoration
Roadmap anchor: R12 / Wave 1 whole-product deployment validation.

## Scope and non-scope

In scope:

- Full Wave 1 verification across the integrated product surface: Branch A host skills, Branch B context scaffolding and telemetry, Branch C real-board task execution, R12 provider loop behavior, deployment smoke paths, audits, and portability/customer-facing expectations.
- Both attached boards available in this workspace: `nucleo_l476rg` and the retained Nordic board currently validated as `nrf52840dk`.
- Real CLI provider paths for Codex CLI and Claude CLI, including real provider turns and provider-directed host-side actions.
- Simulated OpenAI/Anthropic API paths without live credentials, using the repo's fake SDK/client tests to exercise request/response handling, retries, timeouts, resume state, fallback behavior, and strict failure handling as far as possible without paid API access.
- Real code-writing benchmark workflows on both boards with both CLI providers, using representative Wave 1 hardware repair cases.
- Full static/unit/smoke suite ladder, Pyright, and audit-oriented focused reruns.

Out of scope:

- Live OpenAI/Anthropic API calls requiring unavailable credentials or paid credits.
- Official `nrf52833dk` acceptance unless that exact board is attached and its destructive board proof preconditions are explicitly satisfied.
- Wave 2 fresh-machine/customer packaging work beyond Wave 1 portability checks and current smoke coverage.

## Reconciliation summary

- Build plan: Wave 1 must prove the host-side MCP/product loop works as a deployable product, not only as isolated unit tests.
- Current code: Previous final ladder and Branch C runs were green, but Claude CLI was blocked during part of the earlier suite; this run closes that gap with Claude restored.
- Other docs or notes: `things-to-change`, `R12_P_SPLIT`, `current-progress`, and the active handoff identify loader hardening as implemented and exact `nrf52833dk` acceptance as pending when hardware/preconditions are absent.
- Disagreements: None for current attached-board acceptance. API-path validation is explicitly simulated because live credentials are unavailable.

## Design

Run the suite as a layered matrix:

1. Baseline environment/process capture.
2. Full repo suite ladder with static checks, type checks, and pytest.
3. Focused Wave 1/R12 provider simulation tests for OpenAI, Anthropic, Codex CLI, and Claude CLI behaviors.
4. Branch C real-board matrix on both attached boards using Codex CLI and Claude CLI.
5. Representative code-writing hardware repair benchmarks on both attached boards with both CLI providers.
6. Deployment/multi-prompt smoke checks that exercise real CLI invocation, provider loops, context loading, and board interaction.
7. Audit pass over logs and generated artifacts for failures, messy code, product/spec drift, and customer-facing gaps.

If a meaningful failure appears, use the appropriate bug-fix/spec-loop workflow, rerun from the nearest affected layer, and do not claim full green until the failed layer and downstream impact are green.

## Board-facts-as-data and origin tags

- `nucleo_l476rg`: attached-board target used for Wave 1 acceptance.
- `nrf52840dk`: attached Nordic board used as the retained second-board acceptance target.
- `nrf52833dk`: exact official target remains pending when not physically attached or when destructive proof inputs are unavailable.
- Board identities and run roots must come from harness/run output, not hardcoded assumptions.

## Documentation plan

- Write this validation spec before running the suite.
- Preserve run logs under `runs/` with stable `wave1-full-suite-claude-restored-*` names.
- Update `current-progress`/handoff only if this run changes status, exposes a new limitation, or validates a previously pending gap.

## Portability

- Verify that non-hardware checks run from repo commands without relying on local-only absolute paths beyond the active workspace.
- Verify simulated API paths do not require live credentials.
- Treat real-board validation as environment-dependent and record attached-board identities.

## Verification plan

- Run process baseline capture.
- Run the workflow-core suite preset through the repo ladder script.
- Run focused pytest coverage for R12 provider loops, model-native skills, Branch C harness, P0 foundation, and turnkey merge behavior.
- Run Branch C harness for Codex CLI and Claude CLI against `nucleo_l476rg`.
- Run Branch C harness for Codex CLI and Claude CLI against `nrf52840dk`.
- Run representative hardware code-writing benchmarks for each board/provider pair.
- Run deployment/multi-prompt smokes where the provider can freely inspect context and return a final decision/action.
- Review all logs and generated reports for meaningful failures, retries that mask product issues, missing customer-facing behavior, and spec drift.

## Acceptance criteria

- Full suite ladder passes.
- Pyright/static checks pass through the repo's configured suite tooling.
- Focused simulated API-path tests pass without live API credentials.
- Branch C passes on both attached boards for Codex CLI and Claude CLI.
- Code-writing hardware benchmark smokes pass on both attached boards for Codex CLI and Claude CLI.
- Deployment/multi-prompt smoke behavior matches product goals: provider reads context/skills as needed, uses host-side tools where useful, and returns a final decision or skill/tool call rather than stalling.
- Audit is clean or only contains non-actionable/non-valid criticisms.

## Verified

- Full suite ladder passed after the API simulation additions:
  - `uv run python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\r12-api-sim-prompt-memory-suite-report.txt`
  - full pytest `363 passed`, Ruff clean, mypy clean, R11 benchmark tests `34 passed`, R11 benchmark help rendered.
- Focused credentials-free API-path tests passed:
  - `uv run pytest -q tests/test_r12_turnkey.py -k "api_provider_factory_turnkey_loop_smoke or openai or api or resume_failure or provider_setup_failed or model_summary or green_check or details"` -> `17 passed, 52 deselected`
  - `uv run pytest -q tests/test_r12_turnkey_merge.py -k "openai or anthropic or codex_cli_provider_surfaces_subprocess_timeout or claude_cli_provider_surfaces_subprocess_timeout or retry_updates_prompt_metadata or previous_response_failure"` -> `7 passed, 23 deselected`
- The API smoke coverage simulates OpenAI Responses and Anthropic Messages SDK clients while still entering through the real provider factory and `run_turnkey_with_provider` loop. It verifies request/response handling, continuation metadata, local-memory behavior, prompt render modes, and the no-live-credential failure boundary as far as possible without API keys.
- Claude CLI attached-board proof after auth/usage restoration passed:
  - `uv run python tests\harness\branch_c_tests.py --board-id nucleo_l476rg --provider claude-cli --fail-on-skip` -> `9 passed, 0 failed, 0 skipped`, run root `runs/20260701T054747Z-fa210e66`
  - `uv run python tests\harness\branch_c_tests.py --board-id nrf52840dk --provider claude-cli --fail-on-skip` -> `9 passed, 0 failed, 0 skipped`, run root `runs/20260701T054938Z-578b5878`
  - `uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__b001_wrong_boot_text` -> `FULL_SUCCESS`, run root `runs/20260701T055138Z-0be02f11`
- Earlier final matrix proof for the same prompt-memory implementation includes Claude CLI `nrf52840dk__b001_wrong_boot_text` at `runs/20260701T054004Z-1d30d2d3`; a later rerun of that one case was intentionally interrupted by the operator and left no benchmark subprocess running.

## Pending verification

- Live `openai-api` and `anthropic-api` provider calls when credentials/credits are available.
- Exact official `nrf52833dk` hardware proof when that board is attached.
- Fresh-machine Windows/macOS deployment proof remains outside this attached-board validation record.
