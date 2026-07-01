# Wave 1 Final Adversarial Double-Check Process

## Goal and roadmap anchor

Task: Final Wave 1 adversarial audit loop, full product validation, and next-session handoff
Roadmap anchor: R12 Stage 5 Wave 1 in
`markdowns/firmware_agent_build_plan_concrete (10).md`,
`markdowns/things-to-change.md`, and `markdowns/R12_P_SPLIT.md`.

This process is the final adversarial double-check after the provider-native
skill invocation proof landed. It must audit the whole Wave 1 surface, review
criticisms for merit, fix valid gaps through the FirmCLI workflow, rerun the
practical full suite surface, update docs, and leave a handoff for an
independent next Codex session.

## Adversarial audit plan

Important code files to inspect:

- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_native_skills.py`
- `src/pyocd_debug_mcp/brain/skills.py`
- `src/pyocd_debug_mcp/brain/tool_schemas.py`
- `src/pyocd_debug_mcp/brain/config.py`
- `src/pyocd_debug_mcp/brain/cli.py`
- `src/pyocd_debug_mcp/brain/benchmark.py`
- `src/pyocd_debug_mcp/brain/app.py`
- `src/pyocd_debug_mcp/brain/workspace.py`
- `src/pyocd_debug_mcp/ux/`
- `tests/harness/provider_native_skill_usage.py`
- `tests/harness/branch_c_tests.py`
- `tests/harness/r12_turnkey_benchmark.py`
- `tests/test_provider_native_skills.py`
- `tests/test_provider_native_skill_usage_harness.py`
- `tests/test_r12_turnkey.py`
- `tests/test_r12_turnkey_merge.py`
- `tests/test_branch_c_harness.py`
- `tests/test_ux_cli.py`

Important product features to inspect:

- Deleted governed host actions remain structurally absent:
  `read_file`, `replace_file`, and `run_build` must not be valid
  `TurnDecision` actions.
- Free host work still ends in a governed board/client/terminal or
  context-expansion decision.
- Compact MCP tool and skill indexes are discovery-only until focused details
  are loaded.
- `load_tool_details` and detail-required guardrails block stale or
  under-detailed governed execution.
- Prompt/memory hardening uses bootstrap/full prompts only where appropriate,
  compact later-turn state, bounded in-run memory, schema cadence, common detail
  preload, and rendered-vs-available accounting.
- Provider-native skill projection writes only run-local generated views, never
  global provider folders, never overwrites unmarked user-owned native skill
  dirs, and records metadata/hashes.
- Codex CLI and Claude CLI can actually read projected native skills; API
  providers stay on deterministic `load_skills` fallback.
- Simulated OpenAI/Codex API and Anthropic/Claude API code paths exercise
  provider loops, retries, timeout/failure handling, fallback behavior, and
  compact-memory behavior without live credentials.
- Branch C timeout/event behavior remains session/client scoped and does not
  expose brain-only timeout sync as a model-facing tool.
- Real hardware/code-writing runs show self-directed provider host work and
  final governed decisions, not bypassed board actions.
- Operator shell multi-prompt behavior keeps run roots/history/events/diffs
  scoped to the correct prompt.
- Cleanup leaves no spawned provider, MCP, pyOCD, serial, or board-debug
  processes that can be attributed to this pass.

Markdowns to reference for spec, product, and codebase guidance:

- `README.md`
- `markdowns/firmware_agent_build_plan_concrete (10).md`
- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/ROADMAP.md`
- `markdowns/current-progress.md`
- `markdowns/repo_file_index.md`
- `markdowns/curr/README.md`
- `markdowns/curr/r12_turnkey_spec.md`
- `markdowns/curr/r12-context-scaffold-hardening_spec.md`
- `markdowns/curr/r12-delta-compact-indexes_spec.md`
- `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`
- `markdowns/curr/r12-provider-native-skill-bridge_spec.md`
- `markdowns/curr/r12-provider-native-skill-invocation-proof_spec.md`
- `markdowns/curr/wave2-codebase-map_spec.md` for future-scope boundaries
- archived evidence ledgers under
  `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/`

Planned checks:

- `git status --short --branch`
- probe inventory with `PYTHONIOENCODING=utf-8 uv run pyocd list --probes`
- focused provider/API simulation pytest selection from the handoff
- focused provider-native skill usage proof for both CLI providers
- full Python-change gate if Python is edited, otherwise suite ladder
- full FirmCLI suite ladder
- representative live hardware/provider rows only if boards/providers are
  available and quota/usage constraints permit; otherwise inspect latest run
  artifacts and state exact hand-off commands
- markdown-audit delta/full pass after any doc updates
- `git diff --check`

## Done

- Loaded `firmcli-spec-loop`, `firmcli-write-process`,
  `firmcli-test-suite`, `firmcli-fix-bug`, `firmcli-markdown-audit`, and
  `firmcli-workflow-core`.
- Confirmed the branch started clean at `P-Wave-0...origin/P-Wave-0`.
- Created this process ledger.
- Completed an adversarial audit across action schema boundaries, prompt/memory
  accounting, provider-native skill projection, API fallback behavior, Branch C
  timeout/event behavior, operator UX, documentation status, and recent run
  artifacts.
- Fixed the one valid product/code gap found in this pass: `pyocd-debug` could
  hang or crash in non-console/piped operator smoke mode because
  `patch_stdout()` failed outside a Win32 console even though `PromptSession`
  construction had a dummy-output fallback.

## Audit findings and merit review

- VALID: operator shell no-console handling was incomplete. Root cause:
  `OperatorShell.run()` wrapped the whole input loop in `patch_stdout()`.
  On Windows non-console launchers and piped smoke tests, `patch_stdout()`
  can fail or hang before the shell reads `/history`, `/prompt`, `/events`, or
  `/quit`. Fix: split prompt-toolkit interactive mode from line-based stdin
  mode, add prompt-time no-console fallback, and add regression tests in
  `tests/test_ux_cli.py`.
- REVIEWED / NON-BLOCKING: provider-native proof does not expose a vendor
  machine-readable "native skill loader invoked" telemetry event. The product
  proof is behavioral: FirmCLI projects a temporary run-local skill, the CLI
  provider returns the hidden token from that skill body through a valid
  `TurnDecision`, `fallback_used=false`, and Claude includes
  `Skill(firmcli-native-usage-proof)` in the allowlist. Docs must continue to
  avoid claiming live API native-skill execution.
- REVIEWED / NON-BLOCKING: exact official `nrf52833dk`, live OpenAI/Anthropic
  credentials, and fresh-machine proof remain external boundaries. This pass
  tested the attached `nucleo_l476rg` and retained `nrf52840dk` rig.

## Fixes implemented

- `src/pyocd_debug_mcp/ux/shell.py`
  - added explicit stdin-line mode for piped/non-interactive operator command
    scripts;
  - added prompt-time no-console fallback after `patch_stdout()` failures;
  - kept prompt-toolkit behavior for real interactive TTY sessions.
- `tests/test_ux_cli.py`
  - added regression coverage for prompt-time no-console fallback;
  - added regression coverage proving piped commands bypass prompt-toolkit and
    execute `/help` then `/quit`.

## Repeated audit after fix

- Rechecked the changed code path and scoped diff. The final code change is
  limited to operator-shell input handling plus tests; no brain/provider/hardware
  path was changed by the fix.
- Re-ran the practical suite surfaces after the fix, including local quality
  gates, API/provider simulations, live native-skill proof, and compact
  attached-board provider/hardware checks.
- No second-round valid code or product gaps were found. Remaining criticisms
  are external-boundary non-claims listed below.

## Limitations and known gaps

- Live OpenAI/Anthropic API credential proof is not available without
  credentials/credits; use simulated provider paths and do not overclaim.
- Exact official `nrf52833dk` proof can only be claimed if that exact board is
  attached and tested in this pass.
- Fresh-machine proof requires a fresh machine or clean VM and is not implied by
  this checkout.

## Hardware hand-off

- If both attached boards are available, run the Branch C matrix and
  representative code-writing repair benchmarks listed in the handoff.
- If `nrf52833dk` is not attached, preserve the exact official-board gap and use
  `nrf52840dk` only as retained alternate Nordic evidence.

## Open decisions and surfaced issues

- None blocking. External-boundary non-claims remain explicit: no live
  OpenAI/Anthropic API credential proof, no exact official `nrf52833dk` proof
  on this rig, and no fresh-machine/VM proof.

## Verified

- Probe inventory before the pass showed both attached boards:
  `nucleo_l476rg` through ST-Link UID `066FFF514988525067233337` and
  `nrf52840dk` through J-Link UID `683377322`.
- Pre-fix full Branch C provider/hardware matrix was green on both attached
  boards and both CLI providers:
  - `20260701T094215Z-a7c60ba2` (`nucleo_l476rg + codex-cli`)
  - `20260701T094359Z-c0698acd` (`nucleo_l476rg + claude-cli`)
  - `20260701T094620Z-777b35ef` (`nrf52840dk + codex-cli`)
  - `20260701T094836Z-11a0994e` (`nrf52840dk + claude-cli`)
- Pre-fix real code-writing repair benchmarks with
  `--provider-native-skills require` were green:
  - `20260701T095114Z-0e7c5c9a` (`nucleo_l476rg + codex-cli`)
  - `20260701T095526Z-e74ecc95` (`nucleo_l476rg + claude-cli`)
  - `20260701T095859Z-56a8a95a` (`nrf52840dk + codex-cli`)
  - `20260701T100506Z-78df81c0` (`nrf52840dk + claude-cli`)
- Post-fix Python-change gate:
  - `uv run ruff check --fix .` green
  - `uv run ruff format .` green
  - `uv run pyright --outputjson` green, 0 diagnostics
  - `uv run pytest -q` green, `378 passed`
- Post-fix suite ladder:
  `runs/wave1-final-doublecheck-suite-ladder-after-ux-fix.txt`, all green.
- Post-fix focused simulated API/provider path test:
  `32 passed, 78 deselected`.
- Post-fix operator shell smoke:
  `"/history`n/prompt`n/events`n/quit`n" | uv run pyocd-debug`
  completed and saved output to
  `runs/wave1-final-doublecheck-operator-pipe-smoke.txt`.
- Post-fix live provider-native skill invocation proof:
  - Codex token `FIRMCLI_NATIVE_SKILL_USAGE_CODEX_CLI_cb3d90b2`
  - Claude token `FIRMCLI_NATIVE_SKILL_USAGE_CLAUDE_CLI_d96026c2`
  - reports under `runs/provider-native-skill-usage/`
  - both providers passed with `fallback_used=false`.
- Post-fix compact attached-board provider/hardware checks:
  - `nucleo_l476rg + codex-cli`, Branch C `9 passed`, run root
    `20260701T101703Z-9013fd9e`
  - `nrf52840dk + claude-cli`, Branch C `9 passed`, run root
    `20260701T101646Z-b1a06423`

## Pending verification

- Markdown audit/doc cleanup and final handoff update.
- Commit and push to `P-Wave-0`.
