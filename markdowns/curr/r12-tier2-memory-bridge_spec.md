> STATUS: IMPLEMENTED SOFTWARE-VALIDATED - active implementation record for the
> R12 Tier 2 memory bridge.

# R12 Tier 2 Memory Bridge Spec

## Goal in plain English

Bridge the R12 prompt/memory hardening gap by adding the formerly missing Tier 2
mid-history memory lane between recent Tier 1 committed facts and the
hard-limited Tier 3 rolling summary.

Roadmap anchor: R12 Stage 5 Wave 1 prompt/memory cost hardening and Prototype
Priority item 1 / item 14 in `markdowns/things-to-change.md`.

The pre-implementation code had useful bounded memory behavior, but it did not
fully match the four-tier design in
`markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`. It kept Tier 0
canonical state separately, retained Tier 1 recent detailed entries, and folded
evicted entries directly into the rolling summary. This spec closed that gap by
adding the formerly missing Tier 2 lane without changing provider-session persistence,
board behavior, or the governed host-vs-board action boundary.

## Scope and non-scope

In scope:

- Add an explicit brain-authored Tier 2 mid-history compact summary lane to the
  provider session state.
- Move entries from Tier 1 into Tier 2 before they are eligible for Tier 3
  rolling-summary compaction.
- Keep Tier 2 deterministic, compact, auditable, and non-authoritative over
  Tier 0.
- Update memory rendering so a memory sync can show Tier 3, Tier 2, and Tier 1
  distinctly.
- Update run metadata and prompt telemetry so artifacts distinguish Tier 1,
  Tier 2, and Tier 3 counts, coverage, rendered lengths, and compaction causes.
- Add focused tests proving Tier 2 retention, Tier 2 overflow into Tier 3,
  model-summary fallback, and rendered memory labels.
- Update status docs so the four-tier memory design is not called fully
  implemented until the Tier 2 lane is present and verified.

Out of scope:

- Cross-invocation provider session persistence.
- Reusing a Codex or Claude provider session across separate top-level FirmCLI
  invocations.
- Changing the governed board-action decision schema.
- Changing board ids, target names, probe discovery, serial behavior, or any
  hardware facts.
- Making Tier 2 model-authored. Tier 2 is brain-authored deterministic memory;
  only Tier 3 may use provider-backed summary mode.
- Reintroducing full memory into ordinary `remote-delta` turns.

## Reconciliation summary

- Build plan:
  - The build plan requires R12 to maintain provider context through provider
    sessions plus brain-owned compact memory and periodic native safety sync.
  - The build plan does not require cross-invocation persistence for this item.
  - The plan's direction is compatible with adding a deterministic Tier 2 lane
    because it keeps memory brain-owned, compact, and auditable.

- Pre-implementation code inspected for this spec:
  - `src/pyocd_debug_mcp/brain/provider_types.py` defines
    `ProviderSessionState.recent_memory_entries` and `memory_summary`.
  - `render_provider_memory_text()` renders Tier 3 rolling summary and Tier 1
    recent committed facts. It does not render a Tier 2 section.
  - `plan_memory_compaction()` evicts old Tier 1 entries when the recent window
    exceeds `recent_turn_limit` or the recent render cap.
  - `apply_deterministic_compaction()` and `apply_summary_compaction()` fold the
    evicted entries directly into `memory_summary`.
  - `src/pyocd_debug_mcp/brain/loop.py` calls that compaction path inside
    `_commit_provider_memory()`, records summary metadata, and optionally calls
    provider-backed summary mode for `memory_mode=model-summary`.

- Implemented code:
  - `ProviderSessionState` now stores `mid_memory_entries` plus Tier 2 limits.
  - Tier 1 overflow deterministically converts detailed entries into Tier 2
    mid-history entries before Tier 3 compaction can occur.
  - Tier 2 overflow is the only path that feeds Tier 3 deterministic or
    provider-backed summary compaction.
  - Memory rendering labels Tier 3 rolling summary, Tier 2 mid-history compact
    facts, and Tier 1 recent committed facts separately.
  - CLI, env, shell, request artifacts, summary records, and prompt telemetry
    expose the Tier 2 limits, counts, rendered lengths, and compaction turns.

- Other docs or notes:
  - `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md` explicitly
    describes four tiers: Tier 0 canonical state, Tier 1 recent detailed turns,
    Tier 2 deterministic mid-history summaries, and Tier 3 hard-limited rolling
    summary.
  - Before this implementation,
    `markdowns/things-to-change.md`, `markdowns/R12_P_SPLIT.md`, and
    `markdowns/current-progress.md` mostly described the implemented
    last-two-turns-plus-rolling-summary behavior. They now state that the
    four-tier Tier 2 lane is implemented.

- Disagreements:
  - Pre-implementation, the detailed prompt/memory spec said Tier 2 existed in
    the target design, but the code had no separate Tier 2 state or render path.
  - Lower-level status docs could be read as calling prompt/memory hardening
    complete, which was too broad while the four-tier design was the closure
    bar.
  - Resolution: the current bounded memory implementation now includes Tier 2 as
    the missing Wave 1 prompt/memory hardening closure item.

## Design

### Tier Model

Keep the existing authority rule:

- Tier 0 canonical state is always authoritative.
- Tier 1 and Tier 2 are brain-authored factual memory.
- Tier 3 is a hard-limited rolling summary and may be provider-authored only
  through summary mode, then brain-validated.

The implemented state should become:

- Tier 0: compact canonical run state, rendered separately in decision turns.
- Tier 1: recent detailed committed entries, default `2`.
- Tier 2: deterministic compact mid-history entries, default `6`, so the
  combined detailed/mid window is `8` committed turns by default.
- Tier 3: rolling summary, default hard cap `2000` chars.

### Data Model

Add a compact Tier 2 entry type in `provider_types.py`, for example:

```python
@dataclass(frozen=True)
class ProviderMidHistoryEntry:
    turn_index: int
    classification: str | None
    action_kind: str
    action_summary: str
    result_status: ProviderMemoryResultStatus
    durable_learning: str
    verification_snapshot: str
    changed_files: tuple[str, ...] = ()
    refused_or_blocked_paths: tuple[str, ...] = ()
```

Add to `ProviderSessionState`:

```python
mid_memory_entries: tuple[ProviderMidHistoryEntry, ...] = ()
mid_history_turn_limit: int = DEFAULT_MID_HISTORY_TURN_LIMIT
mid_history_render_char_limit: int = DEFAULT_MID_HISTORY_RENDER_CHAR_LIMIT
```

Defaults are `PROJECT-DEFINED`:

- `DEFAULT_RECENT_TURN_LIMIT = 2` remains unchanged.
- `DEFAULT_MID_HISTORY_TURN_LIMIT = 6` gives `8` total Tier 1 + Tier 2 entries.
- `DEFAULT_MID_HISTORY_RENDER_CHAR_LIMIT` should be small enough to keep memory
  sync turns bounded; start at `4_000` unless implementation evidence supports
  a different project-defined value.
- `DEFAULT_SUMMARY_CHAR_LIMIT = 2_000` remains unchanged.

### Compaction Flow

After each committed provider decision:

1. Append the detailed `ProviderMemoryEntry` to Tier 1.
2. If Tier 1 exceeds count or render-char limits, convert the oldest Tier 1
   entries into deterministic Tier 2 entries.
3. If Tier 2 exceeds count or render-char limits, evict oldest Tier 2 entries
   into the Tier 3 compaction plan.
4. If Tier 3 compaction is required:
   - use provider-backed summary mode when `memory_mode=model-summary`;
   - otherwise use deterministic summary merge;
   - fall back to deterministic summary if provider-backed summary fails or
     violates validation.
5. Record the whole plan in run metadata.

This avoids calling provider-backed summary mode every time the third committed
turn arrives. The third turn should normally move turn 1 from Tier 1 to Tier 2,
not directly to Tier 3.

### Rendering

`render_provider_memory_text()` should render sections in stable order:

1. Tier 3 rolling summary, if present.
2. Tier 2 mid-history compact facts, if present.
3. Tier 1 recent committed turn facts, if present.

The header must keep the existing safety stance:

```text
Provider session memory (bounded; Tier 0 canonical run state is rendered separately and wins on conflict):
```

Tier 2 should have its own label:

```text
Tier 2 mid-history compact facts (brain-authored):
```

Ordinary `remote-delta` behavior must not change. Memory is still injected only
when the existing render policy chooses a memory-bearing mode such as
`remote-sync`, bootstrap with memory, or explicit recovery/new-session-from-memory
path.

### Telemetry And Artifacts

Update provider/session records and memory compaction metadata to include:

- `mid_memory_entries`
- `mid_memory_entry_count`
- `mid_history_turn_limit`
- `mid_history_render_char_limit`
- `mid_history_render_char_count`
- `tier1_evicted_turns`
- `tier2_added_turns`
- `tier2_evicted_turns`
- `tier3_summary_source`
- `tier3_summary_covered_through_turn`
- `tier3_summary_char_count`

Existing fields such as `recent_memory_entry_count`, `summary_mode_invoked`,
`summary_source`, and `summary_char_count` should remain for compatibility, but
tests should assert the new Tier 2 fields so the gap cannot silently reappear.

### Config And CLI

Add config/env plumbing only if needed for the new project-defined values:

- `PYOCD_TURNKEY_MID_HISTORY_TURN_LIMIT`
- `PYOCD_TURNKEY_MID_HISTORY_RENDER_CHAR_LIMIT`

If these are added, mirror them through the operator CLI and headless brain CLI
only where the existing memory controls already appear. Do not add broad new
configuration surfaces if tests can use direct invocation fields instead.

### Files Expected To Change

Primary code files:

- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/config.py` if config/env plumbing is added
- `src/pyocd_debug_mcp/brain/cli.py` if CLI flags are added
- `src/pyocd_debug_mcp/ux/cli.py` or related UX parser files if operator memory
  flags need to mirror new controls

Likely tests:

- `tests/test_r12_turnkey.py`
- `tests/test_r12_turnkey_merge.py`
- `tests/test_ux_cli.py` only if new CLI flags are added

Docs after implementation:

- `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`
- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/current-progress.md`
- `markdowns/curr/README.md`

## Board-facts-as-data and origin tags

- This feature introduces no board facts.
- Memory limits and render caps are `PROJECT-DEFINED` defaults.
- Provider memory records must continue to derive board facts from
  `BoardConfig`, run artifacts, benchmark case definitions, or `BrainState`.
- Do not add board-specific branches or board-id-specific memory behavior.
- No hardware claim is made by this spec.

## Documentation plan

- Keep this spec active in `markdowns/curr/` as the current Tier 2
  implementation record until the broader Wave 1 current-doc set is archived.
- `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`,
  `markdowns/things-to-change.md`, `markdowns/R12_P_SPLIT.md`,
  `markdowns/current-progress.md`, and `markdowns/curr/README.md` now state that
  the full four-tier memory design is implemented for the current turnkey path.
- Do not archive this spec until the current markdown audit is complete and its
  process ledger records the final validation state.

## Portability

- No absolute paths.
- No provider credentials are required for non-hardware tests.
- Provider-backed summary mode must be testable with fake providers.
- Deterministic compaction must work identically on Windows, macOS, and Linux.
- New config defaults must be loadable from environment variables without
  shell-specific quoting assumptions.

## Verification plan

Focused tests:

- New session with one or two committed turns keeps all entries in Tier 1.
- Third committed turn moves turn 1 into Tier 2 while keeping turns 2 and 3 in
  Tier 1; Tier 3 remains empty.
- More than `recent_turn_limit + mid_history_turn_limit` committed turns moves
  the oldest Tier 2 entries into Tier 3.
- Tier 2 render output is compact, deterministic, labeled as Tier 2, and does
  not contain full action payloads or repeated static context.
- `memory_mode=model-summary` invokes provider-backed summary only when Tier 2
  entries overflow into Tier 3, not merely when Tier 1 rolls into Tier 2.
- Invalid or too-long provider summary still falls back to deterministic
  compaction.
- `ProviderSessionState.to_record()` and `summary_record()` include Tier 2
  state and limits.
- Prompt metadata distinguishes Tier 1, Tier 2, and Tier 3 rendered lengths.

Non-hardware checks:

- `python .codex\skills\python-change\scripts\run_python_change_checks.py`
- `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
- Focused pytest for provider memory compaction and render behavior.

Hardware/live checks after implementation:

- Hardware checks are intentionally not required for this feature. The user
  explicitly scoped this task to software and product behavior and instructed
  not to run board flashing, connected-board tests, firmware deployment, or
  two-board validation unless this spec required hardware.
- Live provider checks are still useful because the implementation touches the
  provider loop. The completed validation used no-hardware real Codex CLI and
  Claude CLI runs to inspect valid provider decisions and bounded Tier 3 summary
  responses.

## Acceptance criteria

- Tier 2 exists as a distinct provider-session state lane.
- Tier 1 overflow moves entries into Tier 2 before Tier 3.
- Tier 2 overflow moves entries into Tier 3 through the existing summary-mode /
  deterministic fallback policy.
- Rendered memory clearly labels Tier 3, Tier 2, and Tier 1.
- Tier 0 remains separate and authoritative.
- Ordinary `remote-delta` turns do not start injecting full memory because of
  this change.
- Run artifacts expose enough Tier 2 metadata to audit coverage and prompt cost.
- Existing prompt/memory controls keep their current behavior unless explicitly
  extended by this spec.
- No cross-invocation provider-session persistence is introduced.
- Docs no longer call the full four-tier system complete until this spec is
  implemented and verified.

## Verified

- Tier 2 data model, compaction, rendering, telemetry, CLI/env controls, shell
  controls, and compatibility metadata are implemented.
- Current implementation was inspected and changed at:
  - `src/pyocd_debug_mcp/brain/provider_types.py`
  - `src/pyocd_debug_mcp/brain/loop.py`
  - `src/pyocd_debug_mcp/brain/config.py`
- Related CLI/provider/test files were updated for the same Tier 2 contract:
  `src/pyocd_debug_mcp/brain/cli.py`,
  `src/pyocd_debug_mcp/brain/benchmark.py`,
  `src/pyocd_debug_mcp/ux/cli.py`,
  `src/pyocd_debug_mcp/ux/shell.py`,
  `src/pyocd_debug_mcp/ux/commands.py`, provider adapters, and focused tests.
- Current docs were reconciled against:
  - `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`
  - `markdowns/things-to-change.md`
  - `markdowns/R12_P_SPLIT.md`
  - `markdowns/current-progress.md`
  - `markdowns/ROADMAP.md`
  - `markdowns/firmware_agent_build_plan_concrete (10).md`
- Focused Tier 1 -> Tier 2 -> Tier 3 tests passed.
- Python-change gate passed with Ruff, Ruff format, Pyright `0` diagnostics,
  and full pytest `381 passed`.
- FirmCLI suite ladder passed with full pytest, Ruff, mypy, R11 benchmark tests,
  and benchmark help smoke.
- No-hardware real-provider checks passed for `codex-cli` and `claude-cli`:
  Branch C skip-hardware rows returned valid `TurnDecision` outputs, and direct
  provider summary smokes returned bounded Tier 3 summaries.

## Pending verification

- Live `openai-api` / `anthropic-api` proof remains dependent on credentials and
  credits and is not a Tier 2 implementation blocker.
- Hardware proof is not required for this CLI-interaction memory feature and was
  intentionally skipped per user instruction.
