# Process ledger for wave1-current-adversarial-audit

## Goal and roadmap anchor

Task: Wave 1 current adversarial audit loop and deployment validation
Roadmap anchor: `R12` Stage 5 Wave 1, governed by
`markdowns/firmware_agent_build_plan_concrete (10).md`,
`markdowns/things-to-change.md`, `markdowns/R12_P_SPLIT.md`, and the active
R12 specs in `markdowns/curr/`.

This process independently re-checks the Wave 1 product surface described in
the co-archived
`markdowns/tmp/curr-archive-20260701-current-adversarial-audit/next-codex-handoff-20260701-wave1-final-audit.md`.
Valid findings must be reviewed for merit, fixed through the FirmCLI workflow,
and retested before the suite can be considered green.

## Adversarial audit plan

Important code files to inspect:

- `src/pyocd_debug_mcp/brain/actions.py` and `decision_types.py` for the valid
  `TurnDecision` surface; deleted host actions must remain structurally absent.
- `src/pyocd_debug_mcp/brain/loop.py` for orchestration, detail guardrails,
  prompt construction, provider-native projection wiring, finalization, and
  run artifacts.
- `src/pyocd_debug_mcp/brain/provider_types.py` for prompt render modes,
  rendered-vs-available accounting, bounded memory, and provider capabilities.
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`,
  `provider_claude_cli.py`, `provider_openai.py`, and
  `provider_anthropic.py` for provider session/resume, prompt rendering,
  retries, timeout behavior, API fallback, and metadata.
- `src/pyocd_debug_mcp/brain/provider_native_skills.py` for native skill
  manifest validation, projection root selection, overwrite protection,
  metadata, and no-global-provider-config behavior.
- `src/pyocd_debug_mcp/brain/config.py`, `cli.py`, `benchmark.py`, and
  `app.py` for public CLI/config threading and benchmark entrypoints.
- `src/pyocd_debug_mcp/brain/workspace.py` and
  `src/pyocd_debug_mcp/benchmark_support.py` for workspace isolation, diff
  filtering, and scoring behavior around runtime skill projections.
- `src/pyocd_debug_mcp/ux/` for operator shell multi-prompt/history/event
  behavior and non-interactive stdin handling.
- `tests/harness/branch_c_tests.py`,
  `tests/harness/provider_native_skill_usage.py`,
  `tests/harness/r12_turnkey_benchmark.py`, and focused R12/UX/provider-native
  tests for regression coverage.
- `skills/provider_native/`, `skills/model_native/`, and `skills/README.md` for
  shipped skill source boundaries.

Product features to audit:

- The provider performs host-side reading/editing/build reasoning freely, then
  returns one governed board/client/terminal/context-expansion decision.
- `read_file`, `replace_file`, and `run_build` are not valid governed
  decisions, executor branches, batch actions, prompt actions, or schema
  variants.
- Compact tool and skill indexes are discovery surfaces only; governed tools,
  governed scripts/client actions, and brain-owned compound actions require
  loaded details before execution.
- Prompt/memory hardening keeps bootstrap/full prompts separate from ordinary
  `remote-delta`, bounds in-run memory, avoids normal full-schema reinjection,
  preloads common details without board-specific hardcoding, and records
  rendered-vs-available telemetry.
- Provider-native skill projection is run-local, does not write global
  `.codex`, `.claude`, or `.agents`, refuses unmarked user-owned skill dirs,
  and keeps API providers on deterministic `load_skills` fallback.
- Real hardware/provider behavior proves build, flash, UART, symbol, final
  green state, and process/session cleanup on both connected boards.
- Operator-facing `pyocd-debug` can run multiple top-level prompts or command
  scripts without corrupting history, prompt, events, diff, or run roots.
- Docs do not overclaim live API, exact official `nrf52833dk`, or fresh-machine
  proof.

Markdown authorities and guidance:

- `README.md`
- `markdowns/firmware_agent_build_plan_concrete (10).md`
- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/ROADMAP.md`
- `markdowns/current-progress.md`
- `markdowns/curr/README.md`
- active R12 specs in `markdowns/curr/`
- archived proof ledgers named by the handoff under
  `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/` and
  `markdowns/tmp/curr-archive-20260701-wave1-final-doublecheck/`
- `superpowers/*.md` and repo-local `.codex/skills/firmcli-*` workflow docs

Planned checks:

- Probe inventory: `PYTHONIOENCODING=utf-8 uv run pyocd list --probes`.
- Static/code audit using targeted `rg` and full reads of implicated files.
- Focused provider/API simulation pytest selection from the handoff.
- Focused live provider-native skill invocation proof for Codex CLI and Claude
  CLI.
- Full FirmCLI suite ladder.
- Branch C live provider/hardware rows for both connected boards and both CLI
  providers when provider auth/quota permits.
- Representative real code-writing repair benchmarks on both connected boards
  with `--provider-native-skills require`.
- Operator shell multi-command smoke.
- Cleanup/orphan process audit before and after provider/hardware checks.
- If Python changes are needed, run the full Python-change gate after the final
  edit.

## Done

- Loaded required FirmCLI skills and authority docs.
- Read the final handoff, active Wave 1 specs, `things-to-change`,
  `R12_P_SPLIT`, roadmap/current-progress, current-doc index, and named archived
  proof ledgers.
- Confirmed branch `P-Wave-0` at `b96141b Finalize Wave 1 double-check
  handoff` with a clean initial worktree.
- Created this process ledger and adversarial audit plan.
- Completed first static audit pass over the Wave 1 code surface:
  - `TurnDecision` still excludes deleted host actions (`read_file`,
    `replace_file`, `run_build`) and tests assert they remain unsupported.
  - `remote-delta` prompt rendering excludes ordinary memory/full decision
    schema reinjection and records rendered-vs-available prompt accounting.
  - Governed tools, governed client scripts, and `run_green_check` are blocked
    behind focused detail loading before execution.
  - Provider-native projection is run-local, metadata-marked, refuses unmarked
    user-owned skill dirs, and leaves API providers on fallback.
  - Workspace and benchmark diff/scoring filters exclude runtime `.codex`,
    `.claude`, and `.agents` projection directories.
  - The operator shell keeps the non-interactive stdin path and no-console
    `patch_stdout` fallback from the final double-check fix.
- Ran focused provider/API simulation selection:
  `uv run pytest -q tests/test_provider_native_skills.py tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py -k "..."`
  passed with `32 passed, 78 deselected`.
- Ran live provider-native skill proof:
  `uv run python tests\harness\provider_native_skill_usage.py --provider codex-cli --provider claude-cli --timeout-seconds 180 --report-root runs\provider-native-skill-usage`.
  Both providers passed, observed hidden proof tokens from native skill bodies,
  returned `finalize`, and did not use `load_skills` fallback.
- Ran suite ladder before fixes:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\wave1-current-adversarial-audit-suite-ladder.txt`.
  Passed: `378 passed`, Ruff green, mypy green, R11 benchmark tests green, R11
  harness help green.
- Ran Branch C live provider/hardware matrix on attached boards:
  - `nucleo_l476rg` + `codex-cli`: `9 passed, 0 failed, 0 skipped`.
  - `nucleo_l476rg` + `claude-cli`: `9 passed, 0 failed, 0 skipped`.
  - `nrf52840dk` + `codex-cli`: `9 passed, 0 failed, 0 skipped`.
  - `nrf52840dk` + `claude-cli`: `9 passed, 0 failed, 0 skipped`.
- Ran representative code-writing repair benchmarks with
  `--provider-native-skills require --max-iters 6`:
  - `nucleo_l476rg__b001_wrong_boot_text` + `codex-cli`:
    `FULL_SUCCESS`, score 100.
  - `nucleo_l476rg__b001_wrong_boot_text` + `claude-cli`:
    `FULL_SUCCESS`, score 100.
  - `nrf52840dk__b001_wrong_boot_text` + `codex-cli`:
    `FULL_SUCCESS`, score 100.
  - `nrf52840dk__b001_wrong_boot_text` + `claude-cli`:
    `FULL_SUCCESS`, score 100.
- Found and fixed a valid operator-shell gap: PowerShell-piped stdin can prefix
  the first line with decoded UTF-8 BOM bytes, so `/help` was treated as plain
  task text by the real `pyocd-debug` console script and failed with
  "Select a board first". Fixed parser normalization and added a regression
  test.
- Verified the operator shell fix with:
  - `uv run pytest -q tests/test_ux_cli.py -k "piped_commands or bom_prefixed"`
    -> `2 passed, 26 deselected`.
  - Real `"/help`n/quit`n" | uv run pyocd-debug` -> prints slash-command help.
  - Real multi-command pipe with `/board`, `/provider`, `/history`, `/prompt`,
    `/events`, `/quit` -> completed without crash or task misrouting.
- Ran Python-change gate after the fix:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`.
  Passed: Ruff check/fix, Ruff format, Pyright `0` diagnostics over 119 files,
  pytest `379 passed`.
- Re-ran suite ladder after the fix:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\wave1-current-adversarial-audit-suite-ladder-postfix.txt`.
  Passed: pytest `379 passed`, Ruff green, mypy green, R11 benchmark tests
  green, R11 harness help green.
- Re-ran live provider-native proof after the fix under
  `runs\provider-native-skill-usage-postfix`. Both Codex CLI and Claude CLI
  passed, observed hidden proof tokens, returned `finalize`, and did not use
  fallback.
- Re-ran Branch C live provider/hardware matrix after the fix:
  - `nucleo_l476rg` + `codex-cli`: `9 passed, 0 failed, 0 skipped`.
  - `nucleo_l476rg` + `claude-cli`: `9 passed, 0 failed, 0 skipped`.
  - `nrf52840dk` + `codex-cli`: `9 passed, 0 failed, 0 skipped`.
  - `nrf52840dk` + `claude-cli`: `9 passed, 0 failed, 0 skipped`.
- Re-ran representative code-writing repair benchmarks after the fix with
  `--provider-native-skills require --max-iters 6`:
  - `nucleo_l476rg__b001_wrong_boot_text` + `codex-cli`:
    `FULL_SUCCESS`, score 100.
  - `nucleo_l476rg__b001_wrong_boot_text` + `claude-cli`:
    `FULL_SUCCESS`, score 100.
  - `nrf52840dk__b001_wrong_boot_text` + `codex-cli`:
    `FULL_SUCCESS`, score 100.
  - `nrf52840dk__b001_wrong_boot_text` + `claude-cli`:
    `FULL_SUCCESS`, score 100.
- Completed repeat audit after the fix:
  - `git diff --check` passed.
  - Compact static search re-checked deleted-action boundary and the touched
    shell parser.
  - Process snapshots were saved before/after. Remaining `pyocd-debug-mcp`
    processes matched pre-existing Codex/node helper-owned MCP servers, so no
    audit-owned orphan process was identified.

## In progress

- None.

## TODO

- None for this audit loop.

## Limitations and known gaps

- Live OpenAI/Anthropic API proof requires credentials/credits.
- Exact official `nrf52833dk` proof can only be claimed if that exact board is
  detected and tested in this session.
- Fresh-machine proof requires a fresh machine or clean VM; this configured
  checkout can only validate the current host deployment surface.

## Hardware hand-off

- Pending live detection. The current pass will use only boards that
  `pyocd list --probes` actually reports.

## Open decisions and surfaced issues

- No valid static code defects found in the first pass.
- Valid issue fixed: `pyocd-debug` piped slash commands from PowerShell could be
  misrouted as task text when the first line was prefixed by decoded UTF-8 BOM
  bytes. This was a real product/UX gap in the non-interactive operator shell
  path. Fix files: `src/pyocd_debug_mcp/ux/commands.py`,
  `tests/test_ux_cli.py`.
- No-merit criticism: `WorkspaceSession` still has internal helper method names
  such as `read_file`, `replace_file`, and `run_build`. These are not provider
  action variants, are not exposed through the R12 `TurnDecision` schema, and
  are covered by tests that reject the deleted host actions.

## Verified

- Static audit pass 1 complete for provider-native projection, prompt/memory
  hardening, governed detail guardrails, deleted-action absence, diff/scoring
  filters, API fallback boundaries, public CLI/config threading, shipped native
  skill source, and operator shell non-interactive behavior.
- Probe inventory detected:
  - `066FFF514988525067233337` STM32 STLink `NUCLEO-L476RG`.
  - `683377322` Segger J-Link OB-SAM3U128-V2-NordicSem.
- Exact official `nrf52833dk` was not identified by `pyocd list --probes` in
  this run; attached Nordic validation used the repo's `nrf52840dk` profile.
- Post-fix full product deployment validation is green on the current host and
  attached boards for the Wave 1 scope validated here.

## Pending verification

- Live OpenAI/Anthropic API calls with real credentials/credits.
- Exact official `nrf52833dk` hardware proof, because that exact board was not
  detected by `pyocd list --probes`.
- Fresh-machine proof on a separate clean machine or VM.
