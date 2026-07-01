# Wave 1 Adversarial Audit Loop Process

Status: COMPLETE for the agent-verifiable Wave 1 surface on this host.

## Goal and roadmap anchor

Run the requested adversarial audit loop over the whole Wave 1 product surface, not just the most recent provider-native skill bridge feature. Valid findings must be reviewed for merit, fixed through the FirmCLI workflow, retested through the full suite surface available on this host, audited again, reflected in markdowns, and pushed to `P-Wave-0`.

Roadmap/product anchors:

- `R12` / Stage 5 turnkey product.
- `markdowns/things-to-change.md` Prototype Priority items 1-14 plus Wave 1 validation requirements for prompt/memory cost hardening and provider-native skill projection.
- Wave 2 items such as codebase map and process-tree cleanup remain prototype-required future work unless explicitly promoted into the current Wave 1 closure bar.

## Adversarial audit plan

### Files important to inspect

Runtime/brain:

- `src/pyocd_debug_mcp/brain/loop.py` - turn orchestration, detail guardrails, compact prompt rendering, finalization, memory commit, runtime artifact persistence.
- `src/pyocd_debug_mcp/brain/actions.py` - valid decision/action surface; must not retain deleted host actions.
- `src/pyocd_debug_mcp/brain/provider_types.py` - provider session/memory/prompt bundle accounting and compaction contracts.
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py` - Codex remote resume, prompt delivery, retry and metadata behavior.
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py` - Claude remote resume, `Skill(...)` allowlisting, fork retry, memory-summary calls.
- `src/pyocd_debug_mcp/brain/provider_openai.py` and `provider_anthropic.py` - API request/response, continuation, retry, timeout, and fallback behavior.
- `src/pyocd_debug_mcp/brain/provider_native_skills.py` - native skill package loading, projection, hash metadata, source/runtime separation.
- `src/pyocd_debug_mcp/brain/config.py`, `cli.py`, `benchmark.py`, `app.py` - public CLI/config threading and benchmark paths.
- `src/pyocd_debug_mcp/brain/workspace.py` and `benchmark_support.py` - workspace isolation, diff/scoring, runtime artifact filtering.
- `src/pyocd_debug_mcp/runtime_resources.py` - packaged resource lookup for skills/cases/playbooks.
- `src/pyocd_debug_mcp/ux/` - operator shell multi-prompt behavior and visibility.
- `tests/harness/branch_c_tests.py` - real provider/hardware branch validation surface.
- `tests/test_provider_native_skills.py`, `tests/test_r12_turnkey.py`, `tests/test_r12_turnkey_merge.py`, `tests/test_r11_benchmark.py` - regression coverage.
- `skills/provider_native/`, `skills/model_native/`, `skills/README.md` - shipped skill packages and product/source-of-truth boundary.

Markdown/spec guidance:

- `markdowns/firmware_agent_build_plan_concrete (10).md` - highest authority for architecture and Stage 5 bar.
- `markdowns/things-to-change.md` - prototype priority hard bar and Wave 1 requirements.
- `markdowns/R12_P_SPLIT.md` - schedule/branch split guidance, not scope authority.
- `markdowns/ROADMAP.md`, `markdowns/current-progress.md`, `README.md` - public status and product guidance.
- `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`
- `markdowns/curr/r12-prompt-memory-cost-hardening_process.md`
- `markdowns/curr/r12-provider-native-skill-bridge_spec.md`
- `markdowns/curr/r12-provider-native-skill-bridge_process.md`
- `markdowns/curr/wave1-full-product-suite-provider-native_spec.md`
- `superpowers/*.md` and `.codex/skills/firmcli-*` for workflow/codebase guidance.

### Features important to inspect

- Provider-native skill bridge: native CLI projection, no global `.codex`/`.claude` writes, fallback `load_skills`, Claude `Skill(...)` allowlist, API fallback behavior.
- Prompt/memory cost hardening: bootstrap vs `remote-delta`, compact state shape, loaded-detail rendering, provider memory cadence, model-summary mode, accounting.
- Model-native/free host work boundary: no deleted `read_file`/`replace_file`/`run_build` decisions, host work observed only at governed boundaries.
- Loaded-detail guardrails: compact indexes must not execute governed tools/scripts/compound actions before details are loaded.
- Multi-provider loop behavior: Codex CLI, Claude CLI, OpenAI API simulation, Anthropic API simulation.
- Hardware behavior: both connected boards, real MCP server, real provider turns, build/flash/UART/symbol verification.
- Operator-facing behavior: multi-prompt CLI/session behavior, run artifacts, raw provider output visibility.
- Cleanup: no spawned provider/MCP/pyOCD/serial/debug workers left behind beyond pre-existing user-owned processes.
- Docs/product truth: status must not overclaim exact `nrf52833dk`, live API, or fresh-machine proof; it must include attached-board provider-native proof.

## Done

- Loaded requested FirmCLI workflow skills: `firmcli-write-process`, `firmcli-test-suite`, `firmcli-fix-bug`, `firmcli-spec-loop`, and `firmcli-markdown-audit`.
- Loaded workflow core, Python-change guidance, and relevant superpowers playbooks.
- Created this process ledger and audit plan.
- Executed first adversarial audit pass across provider-native projection, prompt/memory accounting, action schema, loaded-detail guardrails, tests, docs, and recent run artifacts.
- Reviewed first-pass criticisms for merit:
  - VALID: provider-native projection could overwrite a pre-existing user-owned `.codex/skills/<skill>` or `.claude/skills/<skill>` folder in a real workspace if the skill ID collided. The benchmark path used run-local copied workspaces, but the product path can use a user workspace for Claude stable-working-directory resume. Fixed by adding a FirmCLI projection marker and refusing to replace unmarked directories.
  - VALID: status docs still said attached-board projected-skill proof was pending after the full Wave 1 provider-native validation passed on `nucleo_l476rg + nrf52840dk`. Fixed the build plan, current progress, things-to-change, and provider-native process ledger wording while preserving live-API, exact-`nrf52833dk`, and fresh-machine non-claims.
  - NO MERIT: `read_file`, `replace_file`, and `run_build` string hits in code indicate workspace helper methods and historical/regression tests, not valid governed `TurnDecision` actions. The action schema and policy keep those actions removed.
  - NO MERIT: withheld advanced MCP tools such as `write_memory`, breakpoints, and memory-block reads are intentionally excluded from `AllowedServerToolName` for the current turnkey allowlist, per `r12_turnkey_spec.md` and `things-to-change.md`.
- Added focused regression tests for provider-native projection overwrite protection.
- Python-change gate after fixes:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py --continue-on-error`
  -> Ruff pass, format pass, Pyright `0`, full pytest `374 passed`.
- Full suite ladder after fixes:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\wave1-adversarial-audit-loop-suite-ladder.txt`
  -> full pytest `374 passed`, Ruff pass, mypy pass, R11 benchmark tests `34 passed`, harness help pass.
- Focused API/provider simulation after fixes:
  `uv run pytest -q tests/test_provider_native_skills.py tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py -k "provider_native or native_skill or openai or anthropic or api_provider_factory_turnkey_loop_smoke or resume_failure or provider_setup_failed or model_summary or retry_updates_prompt_metadata or previous_response_failure or timeout"`
  -> `32 passed, 78 deselected`.
- Real attached-board Branch C matrix after fixes:
  - `nucleo_l476rg + codex-cli`: `9 passed`, run root `20260701T082515Z-50b0ca3d`.
  - `nucleo_l476rg + claude-cli`: `9 passed`, run root `20260701T082653Z-b8965681`.
  - `nrf52840dk + codex-cli`: `9 passed`, run root `20260701T082917Z-ecbbce11`.
  - `nrf52840dk + claude-cli`: `9 passed`, run root `20260701T083110Z-9d9836cf`.
- Real code-writing repair benchmarks after fixes, all with `--provider-native-skills require`:
  - `nucleo_l476rg__b001_wrong_boot_text + codex-cli`: `FULL_SUCCESS`, score `100`, run `20260701T083254Z-987cf201`.
  - `nucleo_l476rg__b001_wrong_boot_text + claude-cli`: `FULL_SUCCESS`, score `100`, run `20260701T083805Z-ad7caba6`.
  - `nrf52840dk__b001_wrong_boot_text + codex-cli`: `FULL_SUCCESS`, score `100`, run `20260701T084025Z-552f6748`.
  - `nrf52840dk__b001_wrong_boot_text + claude-cli`: `FULL_SUCCESS`, score `100`, run `20260701T084536Z-120d39a4`.
- Artifact audit after code-writing runs:
  - every benchmark result is `fixed` / `code_bug`;
  - every verification snapshot has `flash_ok`, `uart_ok`, `symbol_ok`, and `green_check_ok` true;
  - every run changed only the benchmark workspace firmware file
    src/src/main.c inside that run workspace;
  - native projection was available in `.codex/skills` or `.claude/skills`;
  - later provider turns used `remote-delta` with no memory or decision-schema reinjection.
- Process cleanup audit after provider/hardware checks found no new suite-owned leftover worker beyond pre-existing user-owned Codex/Claude app processes and a pre-existing app-owned MCP worker tree.
- Repeated adversarial audit after the green suite. Findings:
  - No new valid code/product gaps found.
  - Remaining criticisms were non-useful or no-merit: expected external boundaries for exact `nrf52833dk`, live API credentials, and fresh-machine proof; historical doc references to removed host actions; and intentionally withheld advanced MCP tools outside the current `AllowedServerToolName` whitelist.

## In progress

- Markdown audit/delta sync and push.

## TODO

- Run markdown audit/delta sync and clean `markdowns/curr/` without removing unimplemented feature folders/specs.
- Commit and push `P-Wave-0`.

## Limitations and known gaps

- Live Codex API / Claude API credentials and credits are unavailable; API paths must be simulated through the real provider-loop code paths.
- Official `nrf52833dk` hardware is not attached; attached Nordic proof uses the retained `nrf52840dk` profile.
- Fresh-machine Windows/macOS proof cannot be performed from this already-configured checkout.

## Hardware hand-off

- If official-pair proof is required later, attach `nrf52833dk + nucleo_l476rg` and rerun the full official-pair R12 suite.
- If live API parity is required later, provide `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` and explicit models, then rerun the API provider benchmark/smoke ladder.

## Open decisions and surfaced issues

- Exact official `nrf52833dk` proof is blocked on attached hardware, not on a known code failure.
- Live API proof is blocked on unavailable API credentials/credits; credentials-free simulation is green.
- Fresh-machine proof is outside this configured checkout; the current proof is this repo and connected hardware deployment surface.

## Verified

- Ledger created.
- Valid first-loop gaps fixed.
- Full local suite, focused API simulation, Branch C provider/hardware matrix,
  and representative code-writing hardware repair rows are green after fixes.
- Repeat audit found no remaining valid Wave 1 gap in the agent-verifiable surface.
- Markdown audit completed. Current-doc stale provider-native pending wording was
  fixed, new validation-doc reference noise was removed, and older missing run
  IDs/shorthand module paths were reviewed as historical/reference-checker noise
  rather than current Wave 1 acceptance claims.

## Pending verification

- Exact official `nrf52833dk`, live API credentials, and fresh-machine proof remain external boundaries.
