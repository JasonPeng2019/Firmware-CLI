# Wave 1 Tmp Cleaned Inventory

> STATUS: CURRENT CLEANED INVENTORY - product-behavior aggregate from archived tmp Wave 1 feature specs and process ledgers.
>
> This document keeps only information from `markdowns/tmp/` that still describes current codebase behavior or intended product behavior. It excludes superseded branch mechanics, stale proof claims, and wording overwritten by current code or active specs.

## Authority And Method

Authority order used for this cleanup:

1. Current code on branch `P-Wave-0`.
2. `README.md`, `markdowns/current-progress.md`, `markdowns/things-to-change.md`, `markdowns/firmware_agent_build_plan_concrete (10).md`, and `markdowns/curr/r12_turnkey_spec.md`.
3. Active specs in `markdowns/curr/`.
4. Archived tmp feature specs and process ledgers.

Code inspected while producing this inventory:

- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/action_policy.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_native_skills.py`
- `src/pyocd_debug_mcp/brain/model_native_skills.py`
- `src/pyocd_debug_mcp/brain/tool_schemas.py`
- `src/pyocd_debug_mcp/brain/client_actions.py`
- `src/pyocd_debug_mcp/brain/config.py`
- `src/pyocd_debug_mcp/brain/task_input.py`
- `src/pyocd_debug_mcp/brain/timeout_policy.py`
- `src/pyocd_debug_mcp/brain/workspace.py`
- `src/pyocd_debug_mcp/ux/cli.py`
- `src/pyocd_debug_mcp/ux/commands.py`
- `src/pyocd_debug_mcp/ux/shell.py`

## Current Product Behaviors Aggregated From Tmp

### 1. Free Host Work, Brain-Governed Board Boundary

Current behavior:

- The provider/model may inspect, edit, and build host-side workspace content during its provider turn.
- The brain governs board access, client-action calls, context expansion, waits, green checks, and finalization.
- Every provider turn closes with exactly one FirmCLI `TurnDecision`: a governed board/client/context/wait/green-check action, an ordered non-final batch, or `finalize`.
- Host-local work is not represented as `read_file`, `replace_file`, or `run_build` actions in the provider-facing schema.

Code evidence:

- `actions.py` exposes only `server_tool`, `load_skills`, `load_tool_details`, `wait`, `run_script`, `run_green_check`, and `finalize` as action variants.
- `action_policy.py` classifies context-expansion, brain-local, client-action, and server-native actions; stale host actions are absent.
- `workspace.py` contains internal helper methods named `read_file`, `replace_file`, and `run_build`, but those are not provider-facing decisions.

Do not carry forward from tmp:

- Reintroducing governed `read_file`, `replace_file`, or `run_build` decisions.
- Prompt language that asks the provider to call those as brain-governed actions.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260630-wave1-final/branch-b-hardbar-prototype_spec.md`
- `markdowns/tmp/curr-archive-20260630-wave1-final/model-native-skill-loading_spec.md`
- `markdowns/tmp/curr-archive-20260701-current-adversarial-audit/wave1-current-adversarial-audit_process.md`
- `markdowns/tmp/curr-archive-20260701-second-repeat-adversarial-audit/wave1-second-repeat-adversarial-audit_process.md`

### 2. TurnDecision And Batch Boundary

Current behavior:

- A provider returns exactly one `action` or one non-empty `action_batch`.
- Ordered batches stop at the first refusal, block, relevant failure, or serial mismatch.
- `finalize` is intentionally excluded from `action_batch`; finalization must be a single action.
- `server_tool:<name>` is the preferred explicit namespaced batch form.
- Legacy `server_tool` batch calls can still be normalized when unambiguous, but conflicting duplicated tool names or arguments fail closed.

Code evidence:

- `TurnDecision._require_single_action_or_batch()` enforces exactly one action surface.
- `actions.py` builds `action_batch.calls[].action_type` from the action policy sets and excludes `finalize`.
- `loop.py::_action_from_call()` normalizes namespaced and legacy server-tool calls and refuses unsupported action kinds.
- `loop.py::_execute_batched_actions()` refuses batch finalization and records per-action events.

Do not carry forward from tmp:

- `finalize` inside `action_batch`.
- Host actions inside `action_batch`.
- Provider-specific parsing outside the shared `TurnDecision` contract.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260628/r12-branch-b-action-boundary_spec.md`
- `markdowns/tmp/markdown-audit-20260630/r12-server-tool-action-hardening_spec.md`
- `markdowns/tmp/curr-archive-20260630-delta-index-final/wave1-audit-prompt-detail-fixes_spec.md`

### 3. Server-Native Board Tools And Green Check

Current behavior:

- Board/SWD/UART/recover/flash/symbol work routes through governed MCP/server tools or brain-owned compound actions.
- `connect` defaults to the selected board id, and benchmark mode forbids explicit probe UID or target override.
- `read_serial` receives expected text and board/port context from invocation/board config rather than fixed local assumptions.
- `flash_firmware` paths are normalized relative to the workspace where appropriate.
- `unlock_recover` is refused unless the invocation allows recovery.
- `run_green_check` can internally build, flash, read PC, read a symbol, read UART, update verification state, and decide final evidence.
- A successful `fixed` or `healthy_confirmed` finalization requires `run_green_check` success.

Code evidence:

- `loop.py::_execute_server_tool()` normalizes `connect`, `flash_firmware`, `read_serial`, and `unlock_recover` behavior.
- `loop.py::_execute_green_check()` performs build/flash/PC/symbol/UART verification.
- `loop.py::_final_result_from_action()` refuses healthy/fixed finalization without `green_check_ok`.

Do not carry forward from tmp:

- Final healthy/fixed claims based only on provider text.
- Direct raw board access as a sanctioned product route.
- Treating retained `nrf52840dk` proof as exact `nrf52833dk` proof.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260628/branch-a-deployment-suite_spec.md`
- `markdowns/tmp/markdown-audit-20260630/branch-a-live-provider-hardware-suite_spec.md`
- `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/wave1-full-product-suite-provider-native_spec.md`

### 4. Client Actions / `run_script`

Current behavior:

- Client actions are session-scoped and pre-registered through `--client-action NAME=PATH`.
- A client action must be a Python file defining `run(inputs, server)`.
- Registered actions are snapshotted by content hash.
- Provider prompt text exposes action name, path, hash, and description.
- `run_script` executes the snapshotted action through a narrow injected server API.
- Client-action server calls are allowed only for known governed server tools.
- Inner server calls from client actions still require focused loaded tool details before execution.
- `client_actions.json` records registered actions and execution status in run artifacts.

Code evidence:

- `client_actions.py` validates `NAME=PATH`, Python syntax, `run()`, content hashes, and prompt rendering.
- `GatedClientActionServer.call_tool()` refuses tools outside its allowlist.
- `loop.py::_execute_run_script()` injects the gated server and blocks inner server tool calls when details are missing.
- `loop.py::_persist_turnkey_artifacts()` writes `run-metadata/client_actions.json` when actions exist.

Future / not current:

- Dynamic provider-authored client-action registration inside an already-running provider turn remains future work.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260628/r12-branch-b-full-deployment-completion_spec.md`
- `markdowns/tmp/curr-archive-20260628/r12-branch-b-multi-loop-real-deployment_test_report.md`
- `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/wave1-r12-adversarial-audit-rerun_spec.md`

### 5. Task Input Robustness

Current behavior:

- Run-mode task text comes from exactly one of `--task`, `--task-file`, or `--task-stdin`.
- Empty task text is rejected.
- `--task-file` reads UTF-8.
- `--task-stdin` supports redirected or piped prompt text.
- Operator-facing and headless CLIs share the task-input helper.

Code evidence:

- `task_input.py` defines the mutually exclusive task source parser and `resolve_task_input()`.
- `ux/cli.py` uses those shared helpers for `pyocd-debug run`.

Primary tmp source:

- `markdowns/tmp/curr-archive-20260628/r12-cli-task-input-robustness_spec.md`

### 6. Compact Governed Tool Index And Loaded Details

Current behavior:

- Ordinary provider turns receive a compact governed MCP tool index, not repeated full JSON schema bodies.
- The compact index includes names, descriptions, required/optional argument hints, and stable response/refusal semantics.
- Full schemas remain available internally and can be loaded through `load_tool_details`.
- Governed tools, client-action inner server tools, and `run_green_check` require loaded details before execution.
- Invalid governed tool arguments can auto-load focused details for the next decision.
- Non-argument MCP failures remain tooling failures.
- `load_tool_details(["run_green_check"])` loads the brain-owned compound action contract.

Code evidence:

- `tool_schemas.py` builds compact `ToolSchemaBundle` output from live MCP descriptors.
- `tool_schemas.py::render_tool_detail_entries()` renders focused full details.
- `loop.py::_execute_load_tool_details()` loads MCP details and the `run_green_check` contract.
- `loop.py::_execute_batched_actions()` enforces details-required blocks.
- `loop.py::_preload_common_details()` preloads `connect` and `run_green_check` when enabled.

Do not carry forward from tmp:

- Full MCP JSON schemas in every ordinary turn.
- Executing governed tools based only on compact index discovery.
- Treating `run_green_check` detail requests as unknown.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260630-wave1-final/compact-tool-schema-index_spec.md`
- `markdowns/tmp/curr-archive-20260630-delta-index-final/wave1-audit-prompt-detail-fixes_spec.md`
- `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/r12-context-scaffold-hardening_process.md`
- `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/wave1-r12-adversarial-audit-rerun_spec.md`

### 7. Model-Native Workflow Skill Loading

Current behavior:

- `load_skills(skill_ids=[...])` is a context-expansion decision.
- It loads FirmCLI-owned model-native workflow skills between provider turns.
- Dependencies resolve recursively with de-duping and cycle detection.
- Init scripts run from runtime copies, dependency-first, with timeout and result capture.
- Init scripts are preflighted before subprocess execution; known raw probe/serial stacks and board/probe commands are blocked.
- Manifest `skill_id` must match the requested/folder skill id.
- Loaded skill state, runtime paths, init results, context file hashes, and failures are persisted.
- Structured failures include provider-visible recovery choices.

Code evidence:

- `actions.py` defines `LoadSkillsAction`.
- `model_native_skills.py` implements dependency closure, runtime-copy loading, manifest validation, init preflight constants, failure records, and context rendering.
- `loop.py::_execute_load_skills()` records structured failure/result text.

Do not carry forward from tmp:

- Treating `.codex/skills` as the product-owned model-native source root.
- Allowing skill init scripts to bypass governed server tools.
- Treating `load_skills` as arbitrary host execution.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260630-wave1-final/model-native-skill-loading_spec.md`
- `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/r12-context-scaffold-hardening_process.md`
- `markdowns/tmp/curr-archive-20260701-current-adversarial-audit/wave1-current-adversarial-audit_process.md`

### 8. Provider-Native Skill Projection

Current behavior:

- Provider-native skills are available for proven CLI providers only:
  - Codex CLI receives run-local `.codex/skills/<skill_id>`.
  - Claude CLI receives run-local `.claude/skills/<skill_id>` plus `Skill(<skill-id>)` allowlisting.
- API providers are fallback-only and use `load_skills`.
- Mode is configurable as `off`, `auto`, or `require`.
- Source root is configurable.
- Projection is run-local and writes no global user `.codex`, `.claude`, or `.agents` folders.
- Projection metadata is written to `firmcli-native-skills.json`.
- Projected directories carry `.firmcli-provider-native-projection.json`.
- Existing unmarked user-owned native skill dirs are not overwritten.
- Native skills guide provider-side host reasoning only; every turn still ends with a FirmCLI `TurnDecision`.

Code evidence:

- `provider_native_skills.py` defines provider layouts, projection metadata, marker files, API fallback, mode handling, and overwrite refusal.
- `provider_codex_cli.py` advertises Codex native skill support for `.codex/skills`.
- `provider_claude_cli.py` advertises Claude native skill support for `.claude/skills` and `Skill(...)`.
- `config.py` and `ux/cli.py` expose provider-native mode/root controls.
- `loop.py` prepares and records the runtime projection.

Do not carry forward from tmp:

- Global provider config writes.
- Overwriting user-owned provider skill folders without FirmCLI markers.
- Claiming live API provider-native skill execution from fake-client simulation.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/wave1-full-product-suite-provider-native_spec.md`
- `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/r12-provider-native-ux-cli-controls_process.md`
- `markdowns/tmp/curr-archive-20260701-current-adversarial-audit/wave1-current-adversarial-audit_process.md`
- `markdowns/tmp/curr-archive-20260701-second-repeat-adversarial-audit/wave1-second-repeat-adversarial-audit_process.md`

### 9. Provider Session Continuity And Recovery

Current behavior:

- The brain always persists canonical compact local memory for provider continuity and audit.
- OpenAI API is remote-primary through Responses `previous_response_id`.
- Codex CLI is remote-primary through Codex thread resume.
- Claude CLI is remote-primary through Claude session resume and fork retry.
- Anthropic Messages API is local-primary because the current Messages API is stateless.
- Remote-primary resume failure is typed and must fail closed unless an explicit recovery starts a newly labeled session from saved memory.
- A recovery-created provider session is not the same as continuation of the old handle.
- Headless behavior defaults to fail closed.

Code evidence:

- `provider_types.py` defines continuation modes, continuation paths, resume recovery metadata, provider handles, and resume failure records.
- `provider_openai.py` uses `previous_response_id` and raises `ProviderResumeFailure` on failed prior-response continuation.
- `provider_codex_cli.py` models Codex remote thread resume and native memory sync.
- `provider_claude_cli.py` models Claude session resume and fork retry support.
- `provider_anthropic.py` declares `continuation_mode="local-primary"` and `remote_strategy="none"`.
- `loop.py` accepts a provider resume recovery handler, commits memory, emits progress events, and persists artifacts.

Do not carry forward from tmp:

- Silent fresh-session fallback after a real remote handle exists.
- Treating Anthropic Messages as a resumable Claude Code-style session backend.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260628/branch-a-strict-provider-recovery_spec.md`
- `markdowns/tmp/curr-archive-20260628/branch-a-deployment-suite_spec.md`
- `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/wave1-repeat-adversarial-audit_process.md`
- `markdowns/tmp/curr-archive-20260701-second-repeat-adversarial-audit/wave1-second-repeat-adversarial-audit_process.md`

### 10. Provider Memory, Prompt Cost, And Native Sync

Current behavior:

- Provider memory is tiered:
  - Tier 0: canonical compact brain-owned run state.
  - Tier 1: detailed recent committed provider turns.
  - Tier 2: deterministic mid-history compact entries from Tier 1 overflow.
  - Tier 3: hard-limited rolling summary.
- Deterministic memory mode is default.
- Model/provider-backed summary mode is only for Tier 2 overflow into Tier 3.
- Ordinary remote-primary later turns use `remote-delta` prompt rendering.
- Full decision schema and full bootstrap task context are not re-injected into ordinary `remote-delta` turns.
- Prompt artifacts record rendered-vs-available accounting.
- Native memory safety sync defaults to every 10 provider turns and is configurable.
- OpenAI native sync remains labeled as remote resume/native sync when it carries `previous_response_id`.

Code evidence:

- `provider_types.py` defines memory defaults, entries, mid-history entries, prompt render modes, and native sync cadence.
- `loop.py::_commit_provider_memory()` appends memory, plans compaction, moves Tier 1 overflow into Tier 2, and invokes summaries only when Tier 3 is required.
- `config.py`, `ux/cli.py`, and `ux/commands.py` expose memory controls.

Do not carry forward from tmp:

- Summarizing Tier 1 directly before Tier 2.
- Treating state existing as equivalent to state being sent to the provider.
- Reinjecting full schema/memory bundles every ordinary turn.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/r12-tier2-memory-bridge_process.md`
- `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/wave1-repeat-adversarial-audit_process.md`
- `markdowns/tmp/curr-archive-20260701-second-repeat-adversarial-audit/wave1-second-repeat-adversarial-audit_process.md`

### 11. Branch C Event / Timeout Behavior

Current behavior:

- Brain events are first-class run artifacts and UX inputs.
- Timeout proposals and iteration estimates are provider-suggested but brain-clamped.
- Effective timeout state is scoped to the run/session.
- Server timeout sync is hidden and brain-owned, not a model-facing tool.
- Current progress events are coarse; provider-visible streaming and mid-tool checkpoint buffers are Wave 2, not current Wave 1 behavior.

Code evidence:

- `loop.py` emits structured events for run start, provider progress, action start/complete, details-required blocks, verification updates, final result, and unexpected failures.
- `timeout_policy.py` clamps timeout proposals, derives server timeout updates, and caps model-estimated iteration budgets.

Do not carry forward from tmp:

- Model-facing timeout-sync tools.
- Treating provider-visible stream text, user interrupt, or mid-tool checkpoints as already implemented.

Primary tmp sources:

- `markdowns/tmp/markdown-audit-20260630-abc-cleanup/r12-branch-c-completion_spec.md`
- `markdowns/tmp/curr-archive-20260630-hardbar-reset/branch_c_test_plan.md`
- `markdowns/tmp/markdown-audit-20260630-abc-cleanup/r12-branch-c-provider-portability-coverage_spec.md`
- `markdowns/tmp/curr-archive-20260630-hardbar-reset/wave1-abc-adversarial-audit_process.md`

### 12. Operator-Facing `pyocd-debug` UX

Current behavior:

- `pyocd-debug` is additive over the same turnkey brain/runtime as `pyocd-debug-brain`.
- It supports `run`, `benchmark`, `history`, `show`, and `rerun`.
- Invoking `pyocd-debug` with no subcommand opens the operator shell.
- Public `run` and `benchmark` expose memory and provider-native skill controls.
- Shell slash commands include board/provider/model, memory controls, workspace/build/artifact context, guided verify/diagnose/repair, history/show/rerun, artifact shortcuts, raw output, help, and quit.
- Slash parsing strips BOM prefixes so PowerShell-piped commands dispatch correctly.
- Non-interactive/piped mode reads stdin lines directly; real TTY mode keeps prompt-toolkit.

Code evidence:

- `ux/cli.py` exposes the one-shot commands and public flags.
- `ux/commands.py` strips BOM prefixes in `parse_shell_input()` and lists supported commands.
- `ux/shell.py` switches to line-based stdin for non-TTY input and keeps prompt-toolkit for interactive sessions.

Current limitation / future:

- Provider-visible streaming before final provider output and user-interruptible provider turns are Wave 2.
- Stronger one-shell provider-session persistence across consecutive prompts remains an open hardening target.

Primary tmp sources:

- `markdowns/tmp/curr-archive-20260701-wave1-final-doublecheck/wave1-final-adversarial-doublecheck_process.md`
- `markdowns/tmp/curr-archive-20260701-current-adversarial-audit/wave1-current-adversarial-audit_process.md`
- `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/r12-provider-native-ux-cli-controls_process.md`

### 13. Workspace Diff / Runtime Context Filtering

Current behavior:

- Runtime projection directories are excluded from changed-file and diff/scoring outputs.
- Excluded runtime context directories are `.agents`, `.claude`, and `.codex`.
- Build output and `.r12_*` files are also ignored.

Code evidence:

- `workspace.py` defines `_RUNTIME_CONTEXT_DIRS = {".agents", ".claude", ".codex"}`.
- `WorkspaceSession._relative_files()` skips build output, runtime context dirs, and `.r12_*` files.

Primary tmp source:

- `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/wave1-full-product-suite-provider-native_spec.md`

### 14. Final Cleanup Failure Visibility

Current behavior:

- A final disconnect cleanup failure is not considered green.
- The run records the failure as a tooling/blocking condition and leaves the session context visible for inspection.

Code evidence:

- `loop.py` includes tooling-failure result construction, `unexpected_failure` events, and persistent `brain_events.jsonl` / `turnkey_state.json` artifacts.

Future:

- Broader process-tree cleanup after user interruption or killable vendor-worker behavior remains future process/session hardening.

Primary tmp source:

- `markdowns/tmp/curr-archive-20260630-hardbar-reset/wave1-turnkey-cleanup-failure_spec.md`

## Still-Open Intended Behavior From Tmp

These still describe intended product behavior, but they are not fully closed by current code/proof:

1. Exact official board proof: `nrf52833dk + nucleo_l476rg` remains the official scoped pair; `nrf52840dk` is retained alternate evidence only.
2. Live API-provider parity: OpenAI/Anthropic have credentials-free simulation coverage, but live proof needs credentials/credits and explicit models.
3. Fresh-machine proof: current proof is tied to this checkout/current host unless a clean machine or VM run is explicitly recorded.
4. Provider-visible streaming and user interruption: specified for Wave 2, not implemented in Wave 1.
5. Mid-tool checkpoint buffers: specified for Wave 2, not implemented in Wave 1.
6. Codebase map/static context: specified for Wave 2, not implemented in Wave 1.
7. Dynamic provider-authored client actions: future work; current surface is pre-registered `--client-action`.
8. Broader process/session cleanup guard: final cleanup visibility exists, but full interruption/process-tree cleanup is future.

## Tmp Source Disposition

| Tmp file | Disposition |
|---|---|
| `markdowns/tmp/curr-archive-20260628/branch-a-strict-provider-recovery_spec.md` | Keep strict fail-closed provider resume/recovery behavior; discard old pending-status wording. |
| `markdowns/tmp/curr-archive-20260628/branch-a-deployment-suite_spec.md` | Keep deployment proof shape and strict provider-session expectations; validation suite, not current spec. |
| `markdowns/tmp/markdown-audit-20260630/branch-a-live-provider-hardware-suite_spec.md` | Keep attached-board vs official-board proof discipline, provider/live matrix, task-file portability, and client-action proof expectations. |
| `markdowns/tmp/curr-archive-20260628/branch-a-b-additive-merge_spec.md` | Keep integration ownership: A provider/session spine plus B action/task/client additions. |
| `markdowns/tmp/curr-archive-20260628/r12-branch-b-action-boundary_spec.md` | Keep action boundary, batches, wait, UART write, and client-action model. |
| `markdowns/tmp/curr-archive-20260628/r12-branch-b-full-deployment-completion_spec.md` | Keep public `--client-action` / `run_script`; dynamic provider-authored actions remain future. |
| `markdowns/tmp/curr-archive-20260628/r12-branch-b-multi-loop-real-deployment_test_report.md` | Evidence for sequential deployment-shaped runs, not design authority. |
| `markdowns/tmp/curr-archive-20260628/r12-cli-task-input-robustness_spec.md` | Keep task ingestion behavior. |
| `markdowns/tmp/markdown-audit-20260630/r12-server-tool-action-hardening_spec.md` | Keep server-tool normalization and fail-closed behavior. |
| `markdowns/tmp/markdown-audit-20260630-abc-cleanup/r12-branch-c-completion_spec.md` | Keep event/timeout behavior and non-claims. |
| `markdowns/tmp/curr-archive-20260630-hardbar-reset/branch_c_test_plan.md` | Provider-neutral harness/proof ledger. |
| `markdowns/tmp/markdown-audit-20260630-abc-cleanup/r12-branch-c-provider-portability-coverage_spec.md` | Keep provider-aware harness/skip/auth distinctions. |
| `markdowns/tmp/curr-archive-20260630-hardbar-reset/p-wave-abc-merge-validation_spec.md` | Keep A/B/C integration summary and proof boundaries. |
| `markdowns/tmp/curr-archive-20260630-hardbar-reset/wave1-abc-adversarial-audit_process.md` | Keep fixed harness acceptance behavior for `action_batch`. |
| `markdowns/tmp/curr-archive-20260630-hardbar-reset/pyright-baseline-cleanup_process.md` | Keep full Pyright as hard gate. |
| `markdowns/tmp/curr-archive-20260630-hardbar-reset/wave1-turnkey-cleanup-failure_spec.md` | Keep final disconnect cleanup failure visibility. |
| `markdowns/tmp/curr-archive-20260630-wave1-final/branch-b-hardbar-prototype_spec.md` | Keep product law that host work is provider-native; compatibility-refusal details are superseded by structural deletion. |
| `markdowns/tmp/curr-archive-20260630-wave1-final/model-native-skill-loading_spec.md` | Keep model-native skill loading behavior. |
| `markdowns/tmp/curr-archive-20260630-wave1-final/compact-tool-schema-index_spec.md` | Compact-index principle retained; active delta-index spec owns ordinary remote-delta behavior. |
| `markdowns/tmp/curr-archive-20260630-delta-index-final/wave1-audit-prompt-detail-fixes_spec.md` | Keep prompt ordering, invalid-argument detail loading, and batch finalize exclusion. |
| `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/wave1-r12-adversarial-audit-rerun_spec.md` | Keep client-action inner-tool guardrails, finalize memory fix, and `run_green_check` detail loading. |
| `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/r12-context-scaffold-hardening_process.md` | Implementation evidence; active scaffold spec owns contract. |
| `markdowns/tmp/curr-archive-20260701-provider-native-doc-sync/wave1-full-suite-claude-restored_spec.md` | Validation record; keep proof boundaries. |
| `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/wave1-full-product-suite-provider-native_spec.md` | Keep provider-native projection behavior, runtime diff filtering, marker overwrite fix, and proof boundaries. |
| `markdowns/tmp/curr-archive-20260701-wave1-final-doublecheck/wave1-final-adversarial-doublecheck_process.md` | Keep operator shell non-console/piped stdin behavior and no-merit classifications. |
| `markdowns/tmp/curr-archive-20260701-current-adversarial-audit/wave1-current-adversarial-audit_process.md` | Keep BOM slash-command fix, static audit conclusions, and proof boundaries. |
| `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/r12-provider-native-ux-cli-controls_process.md` | Keep public UX provider-native controls and rerun replay behavior. |
| `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/r12-tier2-memory-bridge_process.md` | Keep Tier 2 memory bridge behavior. |
| `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/wave1-repeat-adversarial-audit_process.md` | Keep OpenAI native-sync metadata correction and no-merit audit conclusions. |
| `markdowns/tmp/curr-archive-20260701-second-repeat-adversarial-audit/wave1-second-repeat-adversarial-audit_process.md` | Keep final no-new-gap audit conclusion and current non-claims. |

## Cleaned Product Rules

1. Host-local work is provider-native; board work is brain-governed.
2. `read_file`, `replace_file`, and `run_build` are not valid provider decisions.
3. Every provider turn closes through exactly one FirmCLI decision surface.
4. `finalize` is never batched.
5. `run_green_check` is required before fixed/healthy finalization.
6. Compact indexes are discovery surfaces; loaded details are required for governed execution.
7. `load_skills` and `load_tool_details` are context-expansion decisions.
8. Client actions are pre-registered, snapshotted, and server-gated.
9. Provider-native skills are run-local CLI-provider projections with API fallback.
10. Provider-native projection must not write global provider folders or overwrite unmarked user-owned skill dirs.
11. Provider memory is brain-owned, tiered, and audit-visible.
12. Remote-primary resume failures must not silently start fresh sessions.
13. Anthropic Messages remains local-primary.
14. Branch C is coarse structured events and brain-clamped timeouts, not Wave 2 streaming/checkpoints.
15. `pyocd-debug` must support both interactive TTY and non-interactive piped command modes.
16. Runtime `.codex`, `.claude`, and `.agents` dirs are not user source changes for scoring/diff.
17. Exact official-board proof, live API proof, fresh-machine proof, and Wave 2 modules remain separate claims.

## Maintenance Rule

When future work changes any behavior here:

1. update the active hard-bar spec in `markdowns/curr/`,
2. update this cleaned inventory only if an archived tmp behavior is reclassified,
3. do not move stale tmp language forward unless current code and active product docs support it,
4. keep attached-board proof, official-board proof, live API proof, and fresh-machine proof as separate claims.
