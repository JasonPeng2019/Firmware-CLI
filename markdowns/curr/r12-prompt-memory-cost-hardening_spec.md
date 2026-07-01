> STATUS: IMPLEMENTED HARD BAR - Wave 1 prompt/memory cost hardening is now part of R12 product validation.
>
> TIER 2 UPDATE: the current implementation now includes the distinct
> deterministic Tier 2 mid-history lane described below. Tier 1 overflow moves
> into Tier 2 first; provider/model-backed summary mode is reserved for Tier 2
> overflow into the hard-limited Tier 3 rolling summary.

# R12 Prompt And Memory Cost Hardening Spec

## Goal In Plain English

Firmware-CLI must stop treating every provider turn as if it is another bootstrap turn. The product should keep the provider informed enough to make safe firmware-debugging decisions, but ordinary later turns must be compact, bounded, auditable, and predictable in cost.

The hard bar is:

- Bootstrap turns may be large because they establish the task contract, tool surface, and workflow rules.
- Ordinary later turns must carry a compact canonical run state, latest evidence, and any newly needed details, not the full original prompt, full JSON schema, full tool schemas, and growing memory every time.
- Memory may be retained, but it must be tiered, bounded, mode-aware, and validated. It must not silently become an unbounded hidden second prompt.
- Model-authored summary is useful only as a bounded memory tier. It is not authoritative state.
- Cross-invocation provider session persistence is not part of this feature. Do not add it as a future feature here.

Roadmap anchor: R12 turnkey brain and Wave 1 product deployment hardening, with Wave 2 Module G static-context efficiency and prompt/cache hardening as the nearest roadmap continuation.

## Scope And Non-Scope

In scope:

- Replace the current bulky later-turn context shape with a compact state digest for normal provider turns.
- Define explicit prompt render modes and the exact sections each mode may include.
- Bound provider memory with a tiered design:
  - Tier 0: brain-authored canonical state digest, always rendered.
  - Tier 1: recent detailed turn window, brain-authored, last 1 to 2 committed turns.
  - Tier 2: mid-history brain-authored compact turn summaries.
  - Tier 3: model-authored rolling summary, hard-length-bounded and brain-validated.
- Add summary mode as a separate provider mode, then return to decision mode.
- Define how unexecuted or deferred provider decisions behave across compaction.
- Stop injecting the full `TurnDecision` schema on normal successful remote-delta turns.
- Cache or hash static context so unchanged static bodies are not resent unless the provider mode requires them.
- Preload common governed-action details that repeatedly cause avoidable `details_required` turns.
- Add rendered-prompt telemetry, not just available-bundle telemetry.
- Add unit, integration, fake-provider, and hardware acceptance checks for the new prompt behavior.
- Preserve API and CLI provider parity for Claude, Codex, Anthropic, and OpenAI provider paths as far as credentials allow.

Out of scope:

- Cross-invocation provider session persistence.
- Reusing a Claude/Codex native session across separate top-level FirmCLI invocations as a product feature.
- Depending on a provider's private cache behavior for correctness.
- Changing board identity, probe selection, pyOCD target rules, or hardware facts.
- Hiding critical safety facts from the provider to hit an arbitrary tiny prompt size.
- Replacing governed MCP actions or model-native host work semantics.

## Reconciliation Summary

- Build plan:
  - The build plan requires a turnkey brain that can reason across provider turns, use governed MCP actions, and handle real hardware safely.
  - The plan also expects portability, customer-facing deployability, no hardcoded bench facts, and a provider surface that can support multiple provider backends.
  - R12/Wave 2 calls for static-context efficiency, cached-prefix behavior, on-demand details, and compact memory so the product is not wasteful or fragile.

- Current code:
  - `src/pyocd_debug_mcp/brain/loop.py` builds a `ProviderPromptBundle` in `_build_prompt_bundle`.
  - `_build_turn_prompt` currently includes task text, board facts, artifacts, workspace context, current state, loaded details, model-native skill context, client action context, and action inventory in one large rendered string.
  - The bundle currently contains `tool_schema_text`, `provider_memory_text`, `turn_context_text`, and `turn_decision_schema_text` regardless of whether a provider render mode actually injects each body.
  - `src/pyocd_debug_mcp/brain/provider_types.py` already has bootstrap, remote-delta, remote-sync, retry, provider-memory rendering, deterministic compaction, and model-summary compaction primitives.
  - Provider implementations already distinguish remote-delta from full/sync/retry modes, but telemetry mostly records available bundle lengths and can make memory/schema cost look ambiguous.
  - Provider memory entries already compact some fields, but entries still include repeated artifact paths, workspace summaries, action payloads, constraints, changed files, and failed hypotheses. This can grow quickly and can create expensive sync turns.

- Other docs or notes:
  - `markdowns/current-progress.md` says ordinary remote-primary `remote-delta` turns include compact skill context and compact governed-tool index, while full MCP schemas, full `TurnDecision` schema, and provider memory remain out of ordinary remote-delta turns except bootstrap/sync/retry/detail-loading.
  - `markdowns/R12_P_SPLIT.md` and `markdowns/things-to-change.md` should treat prompt/memory cost hardening as a deployment-quality bar, but not as session persistence.
  - Prior test artifacts showed large later-turn prompt bundle sections and growing provider memory records even in short runs. The issue is not only provider tokens spent in one mode; it is that the internal prompt state is too close to a full resend shape and the artifacts do not clearly separate rendered cost from available material.

- Disagreements and resolution:
  - There is no settled build-plan conflict in excluding cross-invocation session persistence. It is a non-goal for this spec.
  - Model-authored memory can improve long runs, but it must not become authoritative. Resolution: Tier 0 brain state wins over every summary.
  - Tiny prompts are unsafe if they omit task contract or verification state. Resolution: target structured compaction, not a 500-character summary.
  - A provider decision emitted before compaction can become stale. Resolution: unexecuted decisions are never executed after summary mode unless the provider re-emits them in decision mode after seeing the canonical post-compaction state.

## Design

### 1. Prompt Render Modes

Add a single render-policy layer so providers do not each guess which prompt sections to inject.

Required modes:

- `bootstrap_full`
  - Used for the first provider turn in a top-level invocation, retry fallback from unknown state, or explicit debug/full mode.
  - May include full static instructions, compact skill context, governed action index, required tool schemas, full current task contract, canonical state digest, and full `TurnDecision` schema.
  - May include memory only if this invocation already has in-process committed memory.

- `remote_delta`
  - Used for ordinary later decision turns.
  - Must include compact skill context or a hash/reference plus any changed compact section.
  - Must include compact governed-action index or a hash/reference plus newly loaded details.
  - Must include Tier 0 canonical state digest.
  - Must include latest evidence and loaded-detail status.
  - Must not include full `TurnDecision` schema unless the previous provider response failed schema validation.
  - Must not include full provider memory unless a sync policy explicitly selects `remote_sync`.

- `remote_sync`
  - Used when the configured native-memory sync cadence requires memory reinjection, when provider continuation state is uncertain, or when a recovery path needs local memory rendered.
  - May include tiered memory, but must use the bounded tier renderer.
  - Must still avoid full static bodies if hashes and provider mode allow compact references.

- `retry_schema`
  - Used after invalid JSON, invalid `TurnDecision`, missing required action shape, or a provider response that needs correction.
  - Must include the correction note and full `TurnDecision` schema.
  - Should include only the compact state digest, not a full bootstrap prompt, unless the failure indicates missing static context.

- `summary_mode`
  - Used only to ask the provider to summarize memory.
  - Must not offer governed actions.
  - Must request one structured summary object.
  - Must include the prior rolling summary, evicted Tier 1/Tier 2 facts, hard length budget, and a compact list of non-droppable facts.

- `decision_after_compaction`
  - Used after summary mode completes.
  - Must return the provider to normal decision semantics.
  - Must include a short note: if a decision was proposed before compaction and was not executed, it was discarded as stale. The provider must re-evaluate against the canonical state and re-emit that decision only if still correct.

Implementation target:

- Add a render policy type in `provider_types.py`, for example `ProviderPromptRenderMode` plus `ProviderPromptRenderPolicy`.
- Prefer one centralized `ProviderPromptBundle.render_for_mode(policy)` over provider-specific render choices scattered through each provider.
- Keep provider-specific code responsible for transport/session mechanics only.

### 2. Compact State Digest

`_build_turn_prompt` should stop being the normal later-turn body. Split it into:

- bootstrap/full task context
- compact task contract
- compact run state digest
- latest evidence block
- loaded detail status
- action availability index

The normal later-turn digest should be structured and loss-aware. A representative shape:

```text
Run state:
- mode=benchmark case=nrf52840dk__b001_wrong_boot_text board=nrf52840dk iter=4/6
- session=20260630T234709Z-4557ac50 connected=true provider_session=claude:...
- workspace_root=<run workspace path>
- allowed_edit_roots=[src]
- build_command=uv run pyocd-zephyr-build ...
- loaded_details=[connect, run_green_check]
- blocked/refused=[details_required(connect), details_required(run_green_check)]

Task contract:
- expected_uart="boot ok"
- expected_symbol=stage1_known_value=0x1234ABCD
- expected_classification=code_bug
- policy: do not use unlock_recover; do not hardcode probe UID; do not use generic target
- policy: do not finalize fixed until run_green_check passes
- preserve: const uint32_t stage1_known_value = 0x1234ABCD; existing loop and live volatile read
- intended fault: UART print path only

Progress so far:
1. Provider inspected src/src/main.c and found success branch printed "boot nope".
2. Provider changed that one string to "boot ok"; changed_files=[src/src/main.c].
3. connect succeeded with session_id=...
4. run_green_check passed after build+flash.

Latest evidence:
- build exit_code=0 duration=53.83s
- pc=0x00000AF0
- UART excerpt includes "boot ok"
- symbol read stage1_known_value=0x1234ABCD
- verification={flash:true, uart:true, symbol:true, green:true}

Next required:
- If the evidence satisfies the task, return finalize(fixed, code_bug) with root cause and summary.
```

Target sizes:

- Bootstrap provider user prompt: normally 15k to 25k characters is acceptable for full setup.
- Normal later decision turn: normally 4k to 8k characters rendered.
- Finalization turn after green check: normally 2k to 4k characters rendered.
- Retry/schema turn: may exceed normal later-turn budget because it includes the full schema.
- These are product targets, not correctness limits. If safety-critical state exceeds the budget, the renderer must surface a budget-overrun warning rather than silently dropping facts.

### 3. Tiered Memory

Provider memory should be a bounded hierarchy, not one growing list.

Tier 0: canonical state digest

- Brain-authored.
- Always rendered in decision modes.
- Authoritative over every other memory source.
- Contains current task contract, safety policies, verification status, active blockers/refusals, loaded details, changed files, and next required action.
- Derived from `BrainState`, `TurnkeyInvocation`, `BoardConfig`, and workspace state.

Tier 1: recent detailed turn window

- Brain-authored.
- Last 1 to 2 committed provider turns by default.
- Includes the last useful observation/action/result with enough payload detail to understand immediate context.
- Must omit repeated full static context, full tool schema, and repeated long path lists.

Tier 2: mid-history compact summaries

- Brain-authored deterministic summaries of older committed turns.
- Default window: turns older than Tier 1 but newer than the Tier 3 coverage boundary, up to a configurable hard count such as 8 total recent/mid turns.
- Short bullets with turn number, action, result, and durable learning.
- No full action payloads unless the payload is itself the durable fact.

Tier 3: model-authored rolling summary

- Provider-authored through `summary_mode`.
- Hard maximum length, configured and enforced by the brain. Recommended default: 1500 to 2500 characters.
- Must be parsed as structured output, for example:

```json
{
  "summary_text": "...",
  "covered_through_turn": 8,
  "non_droppable_facts": ["..."]
}
```

- The brain must reject and re-ask if:
  - output is not valid structured data,
  - `summary_text` exceeds the configured hard limit,
  - coverage metadata is missing or impossible,
  - summary contradicts Tier 0 canonical state,
  - required non-droppable facts are absent.
- After one or two failed rewrite attempts, use deterministic fallback compaction and record the fallback.

Config defaults:

- `recent_turn_detail_limit=2`
- `mid_history_turn_limit=8`
- `memory_summary_trigger_turns=8`
- `memory_summary_trigger_chars=8000`
- `memory_summary_max_chars=2000`
- `native_sync_every=10` remains the default memory-injection cadence unless overridden.

### 4. Summary Mode And Stale Decisions

Compaction must have clear transactional semantics.

If the provider decision has already been executed:

- Commit the action result first.
- Add the resulting committed turn facts to memory.
- Run summary mode if thresholds require it.
- Resume decision mode with the compacted state.

If the provider decision has not been executed yet:

- Do not execute that decision after compaction.
- Store it only as an unexecuted candidate for audit metadata.
- Run summary mode.
- Return to decision mode with the post-compaction canonical state and this instruction:

```text
Before compaction, you proposed <short action label>. It was not executed and is no longer considered live. Re-evaluate against the canonical run state below. Re-emit that action only if it is still the correct next step; otherwise choose the correct next decision.
```

- Only a fresh post-compaction `TurnDecision` may be executed.

This prevents a stale action from crossing a context rewrite boundary.

### 5. Static Context Hashing

Static or mostly static sections should have stable hashes:

- system instructions
- compact skill context
- governed action index
- full MCP schemas
- full `TurnDecision` schema
- board facts that are unchanged for the run
- task contract if unchanged

The prompt bundle record should include both:

- available section length and hash
- rendered section length and hash for the actual prompt sent this turn

Normal later turns may say:

```text
Static context unchanged:
- skill_context_hash=...
- governed_action_index_hash=...
- turn_decision_schema_hash=... not rendered this turn
```

Do not rely on the provider caching this. The hash is for auditability, provider orientation, and future provider-specific optimization. Correctness must hold if the provider has no cache.

### 6. Schema Injection Policy

The full `TurnDecision` JSON schema must be rendered only when useful:

- render on bootstrap/full turn,
- render on retry after invalid provider output,
- render on explicit debug/full mode,
- render if provider capability discovery says the provider lacks prior schema context,
- otherwise omit on ordinary `remote_delta`.

Ordinary later turns should include a compact reminder such as:

```text
Return one valid TurnDecision JSON object using the schema established earlier. If unsure of an action schema, request load_tool_details for that action.
```

Provider metadata must record `decision_schema_injected=true|false`.

### 7. Common Detail Preloading

Avoid repeated `details_required` turns for common safe actions.

Add a preload policy that can load full details before the first provider decision when the task mode predicts the need:

- benchmark and Branch C real-world runs should preload `connect` and `run_green_check`;
- code-writing benchmark cases may also preload any required edit/build/run script detail that is part of the standard case harness;
- preloading must be based on action names and run mode, not board-specific hardcoding;
- preloaded details must still be shown in `loaded_details` so the provider knows what is available.

This is not a loophole around governed actions. It only prevents avoidable round trips where the brain already knows the action details will be required.

### 8. Provider Bundle And Telemetry Changes

Update the prompt bundle model so records answer two separate questions:

- What material existed and could have been rendered?
- What exact material was rendered to the provider this turn?

Required telemetry fields:

- `prompt_render_mode`
- `rendered_total_length`
- `available_total_length`
- per-section `available_length`, `available_hash`, `rendered_length`, `rendered_hash`, `rendered`
- `memory_available_length`
- `memory_rendered_length`
- `memory_injected`
- `decision_schema_available_length`
- `decision_schema_rendered_length`
- `decision_schema_injected`
- `static_tool_schema_available_length`
- `static_tool_schema_rendered_length`
- `static_tool_schema_injected`
- `summary_mode_invoked`
- `summary_rewrite_count`
- `summary_fallback_reason`

The audit artifact should make it impossible to confuse "provider memory exists in the bundle/state" with "provider memory was sent to Claude/Codex on this turn."

### 9. Files Expected To Change

Primary code files:

- `src/pyocd_debug_mcp/brain/provider_types.py`
  - Define prompt render modes/policies.
  - Add per-section prompt accounting.
  - Replace or wrap `render_provider_memory_text` with a tiered memory renderer.
  - Harden `render_memory_summary_request` and summary validation.

- `src/pyocd_debug_mcp/brain/loop.py`
  - Split full turn prompt construction from compact digest construction.
  - Build Tier 0 canonical state.
  - Build Tier 1/Tier 2 memory entries.
  - Trigger summary mode at safe boundaries.
  - Add stale-decision handling across compaction.
  - Add common detail preload before first provider decision where configured.

- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
  - Use centralized render policy.
  - Preserve provider-specific continuation behavior only within the current top-level invocation.
  - Record rendered prompt metadata consistently.
  - Exercise summary mode without offering governed actions.

- `src/pyocd_debug_mcp/brain/config.py`
  - Add config fields and env/CLI plumbing for memory tier limits, summary trigger thresholds, schema policy, static rendering policy, and common detail preloading.
  - Do not add cross-invocation provider session persistence settings.

Likely tests:

- `tests/test_r12_turnkey.py`
- `tests/test_r12_turnkey_merge.py`
- focused prompt-memory coverage in `tests/test_r12_turnkey.py`
- provider-session and provider-surface coverage in `tests/test_r12_turnkey_merge.py`
- provider fake/stub tests for Claude/Codex/OpenAI/Anthropic request rendering and API-loop behavior
- benchmark case smoke checks for `b001` and `b002`

Docs expected after implementation:

- `markdowns/current-progress.md`
- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- relevant handoff doc when this work is accepted or implemented

## Board-Facts-As-Data And Origin Tags

- This spec introduces no new board facts.
- Board identifiers, targets, probe UIDs, serial ports, baud rates, and build commands must continue to come from existing board configuration, harness data, or run artifacts.
- Prompt budgets are `PROJECT-DEFINED` defaults and must be configurable.
- Memory turn-window defaults are `PROJECT-DEFINED`.
- Provider schema behavior is provider capability data, not board data.
- Any benchmark task contract facts, such as expected UART text or expected symbols, must originate from the benchmark case definition or run harness and be rendered as task contract data.

## Documentation Plan

Current status:

- Keep this file as the implemented hard-bar spec for Wave 1 prompt and memory
  cost hardening.
- Keep `markdowns/current-progress.md` synchronized with the actual behavior,
  test proof, and remaining hardware/API gaps.
- Keep `markdowns/things-to-change.md` free of future-feature framing around
  cross-invocation session persistence; bounded prompt/memory hardening is the
  active requirement.
- Keep `markdowns/R12_P_SPLIT.md` aligned so the Wave 1/Wave 2 split reflects:
  - no cross-invocation session persistence,
  - compact later-turn prompts,
  - tiered bounded memory,
  - rendered-vs-available prompt telemetry,
  - API/CLI provider parity.
- If provider docstrings or CLI help mention memory behavior, update those
  docstrings/help strings in the same change.

## Portability

- No absolute user paths in config, tests, or prompt text except run artifacts already produced by the local run.
- Defaults must work on Windows, macOS, and Linux.
- Do not require Claude or Codex paid API credentials to run non-live tests.
- API provider paths must be testable with fake provider responses.
- CLI provider paths must remain optional and degrade with clear messages if the CLI is unavailable or unauthenticated.
- Prompt-size budgets must be configurable through normal project config/CLI/env mechanisms.
- The implementation must not rely on a provider's undocumented cache, private session format, or local CLI persistence across top-level invocations.

## Verification Plan

Unit and focused tests:

- Prompt render policy tests:
  - bootstrap includes full schema and required static context;
  - ordinary remote-delta omits full schema and full memory;
  - retry includes correction note and full schema;
  - remote-sync includes bounded tiered memory;
  - summary-mode cannot emit governed actions.
- Compact state digest tests:
  - contains task contract, verification status, loaded details, blocked/refused families, changed files, and next required action;
  - does not repeat full original prompt or full tool schemas on normal later turns.
- Tiered memory tests:
  - Tier 1 retains only recent detailed turns;
  - Tier 2 summarizes mid-history deterministically;
  - Tier 3 is hard-length-enforced;
  - invalid or too-long model summary is rejected and retried or deterministically compacted.
- Stale decision tests:
  - unexecuted pre-summary action is not executed after summary;
  - provider must re-emit a fresh post-summary decision before execution.
- Telemetry tests:
  - records rendered and available lengths separately;
  - records section hashes;
  - records accurate `memory_injected` and `decision_schema_injected`.

Non-hardware checks:

- `uv run ruff check --fix` on touched Python files, then `uv run ruff format` as appropriate.
- `uv run pyright --outputjson`.
- Focused pytest modules covering prompt rendering and memory compaction.
- Existing R12 turnkey/provider regression tests.
- Simulated Claude/Codex API-path tests with fake responses:
  - request rendering,
  - response parsing,
  - retries,
  - timeout/fallback behavior,
  - summary-mode output validation.

Hardware/live checks after implementation:

- Representative benchmark `b001` and `b002` on both connected boards.
- Branch C live provider run with real MCP servers and real hardware.
- At least one run long enough to trigger summary mode or a controlled fake/live threshold lowered to trigger the same code path.
- Artifact inspection proving normal later turns stay in compact mode and that rendered prompt telemetry matches the actual provider mode.

## Acceptance Criteria

- Ordinary later decision turns no longer render full `TurnDecision` schema unless retry/schema policy requires it.
- Ordinary later decision turns no longer render full provider memory unless `remote_sync` or recovery policy requires it.
- Normal later-turn rendered prompt size is typically in the 4k to 8k character range for benchmark-style cases after bootstrap.
- Finalization turns after green check are typically in the 2k to 4k character range.
- If a prompt exceeds the configured budget, the run records a warning with the section that caused the excess.
- Tier 0 canonical state is always rendered in decision modes and contains all safety-critical task state.
- Tier 3 model summary is never authoritative over Tier 0.
- Summary-mode output is validated, length-bounded, and retried or replaced with deterministic fallback if invalid.
- An unexecuted decision from before summary mode is never executed after compaction unless re-emitted in decision mode.
- Common safe details such as `connect` and `run_green_check` can be preloaded for benchmark/Branch C runs without board-specific hardcoding.
- Prompt telemetry distinguishes rendered lengths from available bundle lengths.
- Claude CLI, Codex CLI, Anthropic API, and OpenAI/Codex API paths use the same prompt-render policy semantics.
- No cross-invocation provider session persistence is introduced.
- Docs reflect this as prompt/memory cost hardening, not as provider-session persistence.

## Verified

- Implemented in `src/pyocd_debug_mcp/brain/provider_types.py`,
  `src/pyocd_debug_mcp/brain/loop.py`,
  `src/pyocd_debug_mcp/brain/skills.py`, and the provider adapters.
- Bootstrap/full and ordinary later-turn `remote-delta` rendering are separated.
- Rendered-vs-available prompt accounting records section hashes plus
  `memory_injected`, `decision_schema_injected`, and
  `static_tool_schema_injected` booleans.
- Provider memory is bounded by Tier 1 recent details, deterministic Tier 2
  mid-history compact facts, and a hard-limited Tier 3 rolling summary;
  model-summary output is validated instead of silently truncated.
- The distinct Tier 2 mid-history compact-summary lane in the target design is
  implemented as separate state and rendering, with Tier 1 overflow moving into
  Tier 2 before Tier 3 compaction is eligible.
- Common `connect` and `run_green_check` details preload by default, loaded
  detail bodies are one-turn focused payloads, and later turns carry compact
  detail status/hashes.
- Selected turnkey skill facts render in full at bootstrap/sync while ordinary
  later turns carry compact skill digests.
- Focused API-path simulation now exercises the real `openai-api` and
  `anthropic-api` factory/turnkey-loop paths without live credentials:
  `test_openai_api_provider_factory_turnkey_loop_smoke` and
  `test_anthropic_api_provider_factory_turnkey_loop_smoke`.
- Validation recorded in
  `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/r12-prompt-memory-cost-hardening_process.md`:
  Python-change gate green with full pytest `363 passed`, Pyright `0`
  diagnostics, suite ladder green, attached-board Branch C Claude runs green,
  and representative CLI code-writing repair proof green on the attached boards.
- The later current adversarial audit archived at
  `markdowns/tmp/curr-archive-20260701-current-adversarial-audit/wave1-current-adversarial-audit_process.md`
  revalidated the Wave 1 deployment surface after the UX stdin BOM fix:
  Python-change gate green with full pytest `379 passed`, suite ladder green,
  focused provider-native hidden-token proof green for both `codex-cli` and
  `claude-cli`, Branch C attached-board rows green on `nucleo_l476rg +
  nrf52840dk`, and representative `b001_wrong_boot_text` repair benchmarks
  green on both attached boards with both local CLI providers.
- The Tier 2 memory bridge is implemented and validated in
  `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/r12-tier2-memory-bridge_process.md`:
  focused Tier 1 -> Tier 2
  -> Tier 3 tests are green, Python-change passed full pytest `381 passed` with
  Pyright `0` diagnostics, the suite ladder is green, and no-hardware real
  provider checks for Codex CLI and Claude CLI returned valid decisions and
  bounded Tier 3 summary outputs.

## Pending Verification

- Live `openai-api` / `anthropic-api` proof when API credentials and credits are
  available.
- Exact official `nrf52833dk` hardware proof when that board is attached.
- Fresh-machine Windows/macOS deployment proof remains a broader product
  boundary, not a prompt-memory implementation gap.
