# Current Working Docs

`markdowns/curr/` is intentionally small. It is only for docs that are still
active current-step truth, not historical process ledgers or branch proof notes.

## Active Docs

- `r12_turnkey_spec.md` - current R12 turnkey contract. It remains useful, but
  it is subordinate to `markdowns/firmware_agent_build_plan_concrete (10).md`
  and the hard prototype bar in `markdowns/things-to-change.md`.
- `r12-context-scaffold-hardening_spec.md` - active R12 scaffold-hardening spec
  and verification record for product/client-owned model-native skills,
  runtime-copy-only recovery, structured skill-load failures,
  `load_tool_details`, invalid-call auto-details, strict loaded-detail
  guardrails before governed tool/script or brain-owned compound-action
  execution, prompt ordering/dedupe, and future bug-reporting docs.
- `r12-delta-compact-indexes_spec.md` - active task spec for including compact
  skill and governed-tool indexes in ordinary `remote-delta` provider turns
  without changing memory cadence or full-schema cadence.
- `r12-prompt-memory-cost-hardening_spec.md` - implemented Wave 1 hard-bar spec
  for compact later-turn prompts, bounded tiered in-run provider memory,
  rendered-vs-available prompt accounting, focused detail rendering, and
  credentials-free API-provider simulation coverage.
- `r12-prompt-memory-cost-hardening_process.md` - active implementation and
  validation ledger for the prompt/memory cost hardening pass.
- `wave1-full-suite-claude-restored_spec.md` - implemented validation record for
  the auth-restored Claude CLI attached-board checks and credentials-free
  OpenAI/Anthropic API-path simulation checks.
- `next-codex-handoff-20260630.md` - current final-audit handoff for a fresh
  Codex session to independently review the pushed R12 scaffold hardening,
  delta-index prompt work, Wave 1 scope, important code/docs/tests, and live
  validation plan.
- `wave1-final-deployment-adversarial-audit_process.md` - active process
  ledger for the current Wave 1 product-deployment adversarial audit loop.

## Active Future Specs

- `wave2-codebase-map_spec.md` - active Wave 2 Module G spec for first-boot
  `codebase_map.md`, workflow-skill map injection, and map-maintenance turns.
- `r12-provider-native-skill-bridge_spec.md` - proposal spec for projecting
  FirmCLI-owned provider-native skills into Claude/Codex runtime skill layouts,
  prompting native skill invocation first, and falling back to FirmCLI
  `load_skills` when native provider behavior is unavailable or unproven. This
  is intentionally still in `curr` and is not implemented.

Canonical current status now lives in:

- `markdowns/things-to-change.md` - hard prototype acceptance bar.
- `markdowns/R12_P_SPLIT.md` - corrected schedule/status note: Branch B's
  free-host/governed-decision code boundary and the R12 scaffold-hardening
  follow-up are implemented. Prompt/memory cost hardening and credentials-free
  API simulation are now part of the Wave 1 hard bar. Live API credentials,
  exact official-board proof, fresh-machine proof, and Wave 2 modules remain
  pending.
- `markdowns/current-progress.md` - current implementation/proof status.

## Archive

Completed Wave 1 hard-bar specs, process ledgers, reviews, and ladder snippets
from the final June 30 pass were moved to:

```text
markdowns/tmp/curr-archive-20260630-wave1-final/
```

Completed R12 scaffold-hardening process/audit ledgers and the consumed June 30
handoff were moved to:

```text
markdowns/tmp/curr-archive-20260630-r12-scaffold-final/
```

Completed delta-index process/review ledgers and Wave 1 audit evidence from the
latest June 30 pass were moved to:

```text
markdowns/tmp/curr-archive-20260630-delta-index-final/
```

The previous Branch A/B/C status, merge-validation, audit, pyright, cleanup, and
Branch C proof docs were moved to:

```text
markdowns/tmp/curr-archive-20260630-hardbar-reset/
```

The superseded June 30 handoff and old Branch B no-hardware smoke prompt files
were moved to:

```text
markdowns/tmp/curr-archive-20260630-wave2-spec-cleanup/
```

Older completed or superseded current-work docs remain in:

```text
markdowns/tmp/curr-archive-20260628/
markdowns/tmp/markdown-audit-20260630/
markdowns/tmp/markdown-audit-20260630-abc-cleanup/
```

## Verified

- `markdowns/curr/` now contains this index, active/implemented R12 Wave 1
  specs and process ledgers, the active Wave 2 codebase-map spec, the active
  provider-native skill bridge proposal, the current final-audit handoff, and
  the active Wave 1 final-deployment audit process ledger.
- Completed process/review/spec ledgers are historical evidence only; they no
  longer compete with `current-progress.md`, `things-to-change.md`, or this
  index as current-step truth.
- R12 scaffold hardening and prompt/memory cost hardening are implemented and
  validated by Python-change gates, suite ladders, focused fake-provider/API
  simulation tests, Codex/Claude CLI live smokes, and attached-board hardware
  runs recorded in the current or archived process ledgers.

## Pending Verification

- Branch B's free-host-work / governed-decision boundary, R12 scaffold
  hardening, and R12 prompt/memory cost hardening are implemented and
  attached-board/API-simulated.
- Remaining proof gaps are external: live API credentials, exact official-board
  proof, and fresh-machine deployment.
- Exact official `nrf52833dk` proof remains pending.
- Wave 2 progress/inspector, checkpoints, scoped green approval, static
  context/cache reuse, codebase-map scaffolding, and cleanup guard work remains
  hard prototype scope.
