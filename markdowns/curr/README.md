# Current Working Docs

`markdowns/curr/` is intentionally small. It is only for docs that are still
active current-step truth, not historical process ledgers or branch proof notes.

## Active Docs

- `r12_turnkey_spec.md` - current R12 turnkey contract. It remains useful, but
  it is subordinate to `markdowns/firmware_agent_build_plan_concrete (10).md`
  and the hard prototype bar in `markdowns/things-to-change.md`.
- `next-codex-handoff-20260630.md` - handoff for the next Codex/Claude session,
  including validation status, Claude quota blockers, exact-board proof gaps,
  and morning rerun commands.
- `model-native-skill-loading-codex-smoke-task.txt` - no-hardware Codex/Claude
  CLI smoke prompt used to verify `load_skills` without touching the board.
- `compact-tool-schema-index-codex-smoke-task.txt` - no-hardware Codex/Claude
  CLI smoke prompt used to verify compact tool-index injection without touching
  the board.

Canonical current status now lives in:

- `markdowns/things-to-change.md` - hard prototype acceptance bar.
- `markdowns/R12_P_SPLIT.md` - corrected schedule/status note: Branch B's
  free-host/governed-decision code boundary is implemented, but Claude
  live-provider proof and exact official-board proof remain pending.
- `markdowns/current-progress.md` - current implementation/proof status.

## Archive

Completed Wave 1 hard-bar specs, process ledgers, reviews, and ladder snippets
from the final June 30 pass were moved to:

```text
markdowns/tmp/curr-archive-20260630-wave1-final/
```

The previous Branch A/B/C status, merge-validation, audit, pyright, cleanup, and
Branch C proof docs were moved to:

```text
markdowns/tmp/curr-archive-20260630-hardbar-reset/
```

Older completed or superseded current-work docs remain in:

```text
markdowns/tmp/curr-archive-20260628/
markdowns/tmp/markdown-audit-20260630/
markdowns/tmp/markdown-audit-20260630-abc-cleanup/
```

## Verified

- `markdowns/curr/` now contains only the active R12 contract, the current
  handoff, and the two smoke prompts still used by the handoff runbook.
- Completed process/review/spec ledgers are historical evidence only; they no
  longer compete with `current-progress.md`, `things-to-change.md`, or this
  index as current-step truth.

## Pending Verification

- Branch B's free-host-work / governed-decision boundary is implemented and
  Codex-smoked, but Claude CLI code-writing proof is blocked by quota until the
  2026-06-30 morning reset.
- Exact official `nrf52833dk` proof remains pending.
- Wave 2 progress/inspector, checkpoints, scoped green approval, static
  context/cache reuse, and cleanup guard work remains hard prototype scope.
