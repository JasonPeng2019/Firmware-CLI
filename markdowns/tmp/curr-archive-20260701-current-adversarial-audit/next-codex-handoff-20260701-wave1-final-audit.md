# Next Codex Handoff - Wave 1 Final Double-Check

Status: HANDOFF FOR INDEPENDENT AUDIT.

Use this document to double-check the latest `P-Wave-0` work one last time.
Do not treat this handoff as proof. Treat it as a map of what to read, what to
audit, and which tests to rerun or spot-check.

Latest pushed branch at handoff time: `P-Wave-0`. Verify the exact tip with
`git log -1 --oneline` after pulling; this handoff is intended to live on the
pushed branch tip rather than name a stale pre-amend hash.

## Mission

Audit the whole Wave 1 product surface after the provider-native skill bridge,
prompt/memory cost hardening, and final adversarial audit loop. Confirm that
the features work together, not just in isolation:

- real MCP server path;
- real connected hardware boards;
- real Codex CLI and Claude CLI provider turns;
- multi-turn provider loops inside each user prompt;
- multiple top-level user prompts in one operator session;
- code-writing repair workflows on hardware;
- simulated Claude/Codex API-provider paths without live API credentials;
- product behavior against the Wave 1 customer-facing hard bar.

If you find a valid issue, fix it through the FirmCLI workflow, rerun the
relevant tests, then rerun the final suite surface needed to regain confidence.

## Required Skills And Workflow

Use the repo-local skills when available:

- `.codex/skills/firmcli-workflow-core/SKILL.md`
- `.codex/skills/firmcli-test-suite/SKILL.md`
- `.codex/skills/firmcli-fix-bug/SKILL.md`
- `.codex/skills/firmcli-write-process/SKILL.md`
- `.codex/skills/firmcli-markdown-audit/SKILL.md`
- `.codex/skills/python-change/SKILL.md` for Python edits

Before running provider, MCP, pyOCD, serial, or hardware checks:

- prefer task files or JSON files over fragile inline PowerShell quoting;
- set explicit timeouts;
- record run roots;
- snapshot relevant processes before and after;
- clean up only processes clearly spawned by the suite.

## Authority Order

Read these first, in this order:

1. `README.md`
2. `markdowns/firmware_agent_build_plan_concrete (10).md`
3. `markdowns/things-to-change.md`
4. `markdowns/R12_P_SPLIT.md`
5. `markdowns/ROADMAP.md`
6. `markdowns/current-progress.md`
7. `markdowns/curr/README.md`

Then read the active Wave 1 specs:

1. `markdowns/curr/r12_turnkey_spec.md`
2. `markdowns/curr/r12-context-scaffold-hardening_spec.md`
3. `markdowns/curr/r12-delta-compact-indexes_spec.md`
4. `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`
5. `markdowns/curr/r12-provider-native-skill-bridge_spec.md`
6. `markdowns/curr/r12-provider-native-skill-invocation-proof_spec.md`
7. `markdowns/curr/wave2-codebase-map_spec.md` for future-scope boundaries.

Then read these archived evidence ledgers if you need the prior proof trail:

1. `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/r12-prompt-memory-cost-hardening_process.md`
2. `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/r12-provider-native-skill-bridge_process.md`
3. `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/r12-provider-native-skill-bridge_probe_notes.md`
4. `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/wave1-full-product-suite-provider-native_spec.md`
5. `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/wave1-adversarial-audit-loop_process.md`
6. `markdowns/tmp/curr-archive-20260701-wave1-final-doublecheck/wave1-final-adversarial-doublecheck_process.md`

Read `superpowers/*.md` for repo workflow guidance if you need to understand
the intended engineering discipline or doc-sync rules.

## Product Features To Verify Together

Wave 1 is the current `R12` turnkey product layer over the existing scoped
hardware-control substrate. The expected shape is:

- A native Python turnkey brain, not a thin wrapper around one provider CLI.
- A stable headless CLI: `pyocd-debug-brain`.
- An operator-facing CLI: `pyocd-debug`.
- Real MCP server control for board actions.
- Provider backends:
  - `codex-cli`
  - `claude-cli`
  - `openai-api`
  - `anthropic-api`
- Compact tool and skill discovery in provider prompts.
- Loaded-detail guardrails before governed tool/script/compound-action
  execution.
- Prompt/memory cost hardening:
  - bootstrap turns can carry full context;
  - later turns should use compact `remote-delta` prompts;
  - later turns should not repeat the full decision schema unnecessarily;
  - provider memory should be bounded and cadence-controlled;
  - rendered-vs-available prompt accounting should be observable.
- Model-native/free host-work boundary:
  - providers may inspect/edit files in their host workspace;
  - board actions remain behind governed FirmCLI/MCP decisions;
  - removed governed host actions such as `read_file`, `replace_file`, and
    `run_build` must not reappear as valid `TurnDecision` actions.
- Provider-native skill bridge:
  - FirmCLI-owned skills project into `.codex/skills` for Codex CLI;
  - FirmCLI-owned skills project into `.claude/skills` for Claude CLI;
  - projection must be runtime-local and must not write global provider config;
  - projection must not overwrite unmarked user-owned native skill dirs;
  - API providers must use deterministic `load_skills` fallback because native
    provider skill execution is not proven through live API credentials.

## Important Code Files

Brain/runtime:

- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_native_skills.py`
- `src/pyocd_debug_mcp/brain/config.py`
- `src/pyocd_debug_mcp/brain/cli.py`
- `src/pyocd_debug_mcp/brain/benchmark.py`
- `src/pyocd_debug_mcp/brain/app.py`
- `src/pyocd_debug_mcp/brain/workspace.py`
- `src/pyocd_debug_mcp/benchmark_support.py`
- `src/pyocd_debug_mcp/runtime_resources.py`

UX and harness:

- `src/pyocd_debug_mcp/ux/`
- `tests/harness/branch_c_tests.py`
- `tests/harness/r12_turnkey_benchmark.py`

Skills:

- `skills/README.md`
- `skills/model_native/firmcli-firmware-debug/`
- `skills/provider_native/common/firmcli-firmware-debug/`
- `.codex/skills/firmcli-*`

Tests:

- `tests/test_provider_native_skills.py`
- `tests/test_r12_turnkey.py`
- `tests/test_r12_turnkey_merge.py`
- `tests/test_r11_benchmark.py`
- `tests/test_ux_cli.py`
- `tests/test_branch_c_harness.py`

## Less Important Or Historical Files

Do not use these as current authority unless you are investigating history or
reading the specific archived evidence ledgers listed above:

- `markdowns/tmp/curr-archive-*`
- `markdowns/tmp/markdown-audit-*`
- old completed process/review ledgers under `markdowns/tmp/`
- `runs/` artifacts except the specific run IDs cited below
- generated benchmark workspaces under `runs/_r11_workspaces/`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- provider-runtime projected dirs inside run workspaces such as `.codex/skills`
  and `.claude/skills`

The active future spec `markdowns/curr/wave2-codebase-map_spec.md` is relevant
for future scope, but it is not part of the current Wave 1 green claim.

## Known Validation Evidence To Re-Inspect

Recent green run roots from the final double-check pass:

- Full Branch C matrix before the operator-shell fix:
  - `nucleo_l476rg + codex-cli`: `20260701T094215Z-a7c60ba2`
  - `nucleo_l476rg + claude-cli`: `20260701T094359Z-c0698acd`
  - `nrf52840dk + codex-cli`: `20260701T094620Z-777b35ef`
  - `nrf52840dk + claude-cli`: `20260701T094836Z-11a0994e`
- Real code-writing repair benchmarks before the operator-shell fix:
  - `nucleo_l476rg + codex-cli`: `20260701T095114Z-0e7c5c9a`
  - `nucleo_l476rg + claude-cli`: `20260701T095526Z-e74ecc95`
  - `nrf52840dk + codex-cli`: `20260701T095859Z-56a8a95a`
  - `nrf52840dk + claude-cli`: `20260701T100506Z-78df81c0`
- Compact post-fix hardware/provider rechecks, after the only code change:
  - `nucleo_l476rg + codex-cli`: `20260701T101703Z-9013fd9e`
  - `nrf52840dk + claude-cli`: `20260701T101646Z-b1a06423`

Focused live-provider native-skill invocation proof:

- Codex CLI report:
  `runs/provider-native-skill-usage/codex-cli-provider-native-skill-usage.json`
  with latest token `FIRMCLI_NATIVE_SKILL_USAGE_CODEX_CLI_cb3d90b2`.
- Claude CLI report:
  `runs/provider-native-skill-usage/claude-cli-provider-native-skill-usage.json`
  with latest token `FIRMCLI_NATIVE_SKILL_USAGE_CLAUDE_CLI_d96026c2`.

Expected native-skill invocation proof behavior:

- projection status is `available`;
- Codex layout is `.codex/skills`;
- Claude layout is `.claude/skills`;
- Claude allowlist includes `Skill(firmcli-native-usage-proof)`;
- provider returns a valid `finalize` `TurnDecision`;
- `fallback_used=false`;
- the hidden proof token appears in the decision even though it was present only
  in the proof skill body.

Latest focused native-skill proof closure:

- `uv run pytest -q tests/test_provider_native_skill_usage_harness.py tests/test_provider_native_skills.py`
  -> `11 passed`.
- `uv run ruff check tests/harness/provider_native_skill_usage.py tests/test_provider_native_skill_usage_harness.py`
  -> green.
- `uv run python tests\harness\provider_native_skill_usage.py --provider codex-cli --provider claude-cli --timeout-seconds 180 --report-root runs\provider-native-skill-usage`
  -> both providers passed with `fallback_used=false`.
- `python .codex\skills\python-change\scripts\run_python_change_checks.py --continue-on-error`
  -> Ruff, format, Pyright `0`, and `376 passed`.
- `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\r12-provider-native-skill-invocation-proof-suite.txt`
  -> suite ladder green.

Latest final double-check evidence after the operator-shell fix:

- `python .codex\skills\python-change\scripts\run_python_change_checks.py --continue-on-error`
  -> Ruff, format, Pyright `0`, and `378 passed`.
- `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\wave1-final-doublecheck-suite-ladder-after-ux-fix.txt`
  -> suite ladder green.
- Focused simulated API/provider pytest selection -> `32 passed, 78 deselected`.
- `"/history`n/prompt`n/events`n/quit`n" | uv run pyocd-debug`
  -> completed without a no-console crash/hang; captured in
  `runs/wave1-final-doublecheck-operator-pipe-smoke.txt`.
- `uv run python tests\harness\provider_native_skill_usage.py --provider codex-cli --provider claude-cli --timeout-seconds 180 --report-root runs\provider-native-skill-usage`
  -> both providers passed with `fallback_used=false`.
- `uv run python tests\harness\branch_c_tests.py --board-id nucleo_l476rg --provider codex-cli --provider-timeout-seconds 300 --fail-on-skip`
  -> `9 passed`, run root `20260701T101703Z-9013fd9e`.
- `uv run python tests\harness\branch_c_tests.py --board-id nrf52840dk --provider claude-cli --provider-timeout-seconds 300 --fail-on-skip`
  -> `9 passed`, run root `20260701T101646Z-b1a06423`.

Final adversarial finding from this pass:

- VALID and fixed: `pyocd-debug` could crash or hang in piped/non-console mode
  because `patch_stdout()` failed before reading operator commands. The shell
  now uses line-based stdin when launched non-interactively and keeps
  prompt-toolkit for real TTY sessions. Regression tests live in
  `tests/test_ux_cli.py`.
- Non-blocking boundary: provider-native skill proof is behavioral, not vendor
  telemetry that exposes an internal loader event. Do not overclaim live API
  native-skill execution.

For each code-writing run, inspect these files under that run root:

- run-metadata benchmark result JSON
- run-metadata score JSON
- run-metadata turnkey state JSON
- model turns JSONL log
- brain events JSONL log
- applied turnkey diff
- projected skill folders in the run workspace

Expected behavior:

- final status `fixed`;
- classification `code_bug`;
- hardware verification true for flash/UART/symbol/green check;
- provider performs self-directed host-side source inspection/editing;
- final decision is a governed return/action, not an ungoverned board action;
- later turns use `remote-delta` and do not repeatedly inject full schema;
- changed files are only the benchmark workspace firmware file.

## Full Validation Commands

Run from repo root.

Probe inventory:

```powershell
PYTHONIOENCODING=utf-8 uv run pyocd list --probes
```

Expected attached boards in the previous run:

- `nucleo_l476rg` through ST-Link UID `066FFF514988525067233337`
- `nrf52840dk` through J-Link UID `683377322`

`nrf52833dk` was not attached. Do not claim exact `nrf52833dk` proof unless it
is actually attached and tested.

Local quality gate:

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py --continue-on-error
```

Full suite ladder:

```powershell
python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\wave1-final-doublecheck-suite-ladder.txt
```

Focused API/provider simulation without live API credentials:

```powershell
uv run pytest -q tests/test_provider_native_skills.py tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py -k "provider_native or native_skill or openai or anthropic or api_provider_factory_turnkey_loop_smoke or resume_failure or provider_setup_failed or model_summary or retry_updates_prompt_metadata or previous_response_failure or timeout"
```

This must exercise the same provider-loop code paths as much as possible:

- simulated OpenAI/Codex API request/response handling;
- simulated Anthropic/Claude API request/response handling;
- retries and retry metadata;
- setup failure;
- resume failure;
- timeout behavior;
- fallback behavior;
- model-summary compaction behavior.

Focused native skill invocation proof:

```powershell
uv run python tests\harness\provider_native_skill_usage.py --provider codex-cli --provider claude-cli --timeout-seconds 180 --report-root runs\provider-native-skill-usage
```

Branch C provider/hardware matrix:

```powershell
uv run python tests\harness\branch_c_tests.py --board-id nucleo_l476rg --provider codex-cli --provider-timeout-seconds 300 --fail-on-skip
uv run python tests\harness\branch_c_tests.py --board-id nucleo_l476rg --provider claude-cli --provider-timeout-seconds 300 --fail-on-skip
uv run python tests\harness\branch_c_tests.py --board-id nrf52840dk --provider codex-cli --provider-timeout-seconds 300 --fail-on-skip
uv run python tests\harness\branch_c_tests.py --board-id nrf52840dk --provider claude-cli --provider-timeout-seconds 300 --fail-on-skip
```

Representative real code-writing repair benchmarks:

```powershell
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b001_wrong_boot_text --provider-native-skills require --max-iters 6
uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__b001_wrong_boot_text --provider-native-skills require --max-iters 6
uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__b001_wrong_boot_text --provider-native-skills require --max-iters 6
uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nrf52840dk__b001_wrong_boot_text --provider-native-skills require --max-iters 6
```

Multi-user-prompt / operator-session check:

```powershell
uv run pyocd-debug
```

In one real TTY shell process, run at least three top-level prompts or benchmark
commands. The exact prompts can be simple, but they must be real top-level
operator requests. Verify:

- each prompt creates a separate run root;
- each prompt has its own bounded provider/tool loop;
- provider session state does not leak incorrectly between prompts;
- `/history`, `/prompt`, `/events`, `/diff`, `/score`, or equivalent shell
  views point to the correct run;
- a provider-session failure path, if encountered, offers retry-new/abort
  recovery rather than silently corrupting state.

Smoke examples for headless product path:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider claude-cli --board-id nrf52840dk --task "Verify this reference firmware is healthy and explain why."
```

Use `--task-file` for longer prompts.

## What To Audit Adversarially

Check for bugs and product gaps, not just failing tests:

- Does provider-native projection ever write global `.codex` or `.claude`
  config? It should not.
- Can projection overwrite a user-owned `.codex/skills/<skill>` or
  `.claude/skills/<skill>` folder? It should refuse unless the FirmCLI marker
  is present.
- Are runtime projected skill dirs filtered from benchmark diffs and scoring?
- Do API providers incorrectly claim native `.codex` or `.claude` skill support?
  They should use deterministic `load_skills` fallback.
- Do later provider turns still carry bootstrap-size prompt bundles?
- Does memory grow unbounded or inject every turn despite the configured cadence?
- Can a provider execute a governed tool or compound action before details are
  loaded?
- Did deleted governed host actions reappear in schema, policy, or prompt text?
- Do provider responses show the desired behavior: self-directed host-side
  reading/editing, followed by a governed decision or skill call?
- Do hardware checks prove build, flash, UART, symbol, and final green state?
- Are process cleanup and board-session cleanup reliable after provider/hardware
  runs?
- Are docs overclaiming live API proof, exact `nrf52833dk` proof, or
  fresh-machine proof?

## Expected Non-Claims

Keep these boundaries explicit:

- No live OpenAI/Anthropic API credential proof unless credentials and credits
  are actually available and used.
- No exact `nrf52833dk` hardware proof unless that exact board is attached and
  tested.
- No fresh-machine install/deployment proof unless performed on a fresh machine
  or clean VM.

The previous green claim is limited to this checkout, the attached
`nucleo_l476rg` and `nrf52840dk`, real Codex/Claude CLI providers, and simulated
API paths through test doubles.

## If You Find A Valid Gap

1. Write down the criticism and why it is valid against code/product behavior.
2. Use the smallest correct fix.
3. For Python edits, follow `.codex/skills/python-change/SKILL.md`.
4. Rerun focused failing checks.
5. Rerun the suite surface needed to prove the fix did not break Wave 1.
6. Update docs if the implementation, validation state, or product bar changed.
7. Do not mark the audit green if the issue is only hidden by a skipped
   provider, skipped board, or missing credentials.

## Final Verdict Shape For The Next Session

Return a short matrix:

```text
feature/check | command/evidence | result | notes
```

Include:

- local suite result;
- API simulation result;
- hardware/provider matrix result;
- real code-writing benchmark result;
- operator multi-prompt result;
- cleanup/orphan-process result;
- audit findings and merit review;
- any remaining external boundaries.

If everything is still green, say that Wave 1 remains green for the
agent-verifiable attached deployment surface. If not, state the failing gap
precisely and whether it was fixed.
