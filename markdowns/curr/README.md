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
  for compact later-turn prompts, bounded in-run provider memory,
  deterministic Tier 2 mid-history memory, rendered-vs-available prompt
  accounting, focused detail rendering, and credentials-free API-provider
  simulation coverage.
- `r12-tier2-memory-bridge_spec.md` - implemented bridge spec and validation
  record for the brain-authored Tier 2 mid-history lane between recent Tier 1
  facts and the hard-limited Tier 3 rolling summary.
- `r12-provider-native-skill-bridge_spec.md` - implemented Wave 1 hard-bar spec
  for projecting FirmCLI-owned actual skills into provider-visible projected
  preloaded `.codex/skills` and `.claude/skills` runtime views for CLI
  providers, with deterministic `load_skills` fallback for API providers and
  uncertain native-skill handling.
- `r12-skill-surface-ownership_spec.md` - active vocabulary cleanup doc for
  distinguishing projected preloaded skills, actual skills to preload, and
  user-owned skills. This doc is the terminology bridge for
  `things-to-change.md` entry 14, the build-plan R12 skill amendments, the
  provider-native bridge, and Wave 1.6-B native skill sync.
- `r12-provider-native-skill-invocation-proof_spec.md` - active proof spec and
  validation record for the focused live Codex/Claude CLI native-skill
  invocation test that closes the remaining provider-native skill evidence gap.
- `r12-provider-native-ux-cli-controls_spec.md` - implemented narrow gap spec
  and validation record for exposing provider-native skill mode/root controls
  through the public `pyocd-debug` UX CLI and rerun path.
- `r12-openai-native-sync-metadata_spec.md` - implemented narrow audit-gap spec
  and validation record for truthful OpenAI remote-primary metadata during
  periodic native memory safety sync.
- `wave1-post-abc-addons-inventory.md` - current audit inventory of the R12 /
  Wave 1 add-ons, archived fixes, validation/proof additions, and active
  Wave 1 gap specs discovered across `curr/` and `markdowns/tmp/`.
- `wave1-tmp-cleaned-inventory.md` - cleaned aggregation of non-superseded
  archived tmp feature/spec behavior that still describes current product/code
  behavior or intended behavior.

## Active Future Specs

- `wave1-5-A-interactive-session-hardening_spec.md` - active proposal spec for
  making one `pyocd-debug` interactive shell behave like one persistent
  provider session, with provider handle/memory carryover across prompts,
  `/session`, `/new`, `/forget`, and no silent fresh-session fallback.
- `wave1-6-B-actions-spec.md` - active proposal spec for the Branch B
  client-action/native-skill-sync implementation gap. It now uses the
  `r12-skill-surface-ownership_spec.md` vocabulary: providers can see
  projected preloaded skills and user-owned skills, can natively edit only
  user-owned skills in skill-authoring/sync mode, and must sync validated
  user-owned skills into a client-owned registry so API fallback succeeds.
- `wave1-7-UX-dev-provider-visible-status_spec.md` - active proposal spec for a
  narrow Wave 1 developer-only bridge that exposes provider-visible
  status/reasoning text and brain heartbeats during provider turns, while
  leaving normal-user streaming, interrupt cleanup, partial-work review, and
  full inspector UX to Wave 2 Module D/H.
- `wave2-codebase-map_spec.md` - active Wave 2 Module G spec for first-boot
  `codebase_map.md`, workflow-skill map injection, and map-maintenance turns.
- `wave2-midtool-checkpoints_spec.md` - active Wave 2 Module E spec for a
  brain-mediated mid-tool checkpoint observation buffer over
  UART/build/client-action streams.
- `wave2-provider-stream-interrupt_spec.md` - active Wave 2 Module D/H spec for
  provider-visible stream text, brain heartbeats, developer inspector records,
  user interruption during provider turns, partial-work review, and
  process-cleanup coordination.

Canonical current status now lives in:

- `markdowns/things-to-change.md` - hard prototype acceptance bar. Entry 14's
  skill-index / on-demand skill body language is refined by
  `r12-skill-surface-ownership_spec.md` and `wave1-6-B-actions-spec.md` until
  the large backlog file is directly reconciled.
- `markdowns/R12_P_SPLIT.md` - corrected schedule/status note: Branch B's
  free-host/governed-decision code boundary and the R12 scaffold-hardening
  follow-up are implemented. Prompt/memory cost hardening and credentials-free
  API simulation are now part of the Wave 1 hard bar. Provider-native
  projection and focused live Codex/Claude CLI native-skill invocation proof
  are also Wave 1 validation requirements. Live API credentials, exact
  official-board proof, fresh-machine proof, and Wave 2 modules remain pending.
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

The superseded June 30 Wave 1 handoff, final-deployment adversarial-audit
ledger, and Claude-restored full-suite validation record were moved to:

```text
markdowns/tmp/curr-archive-20260701-provider-native-doc-sync/
```

The completed July 1 prompt/memory hardening process ledger, provider-native
skill bridge process/probe notes, Wave 1 adversarial-audit process ledger, and
provider-native full-suite validation record were moved to:

```text
markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/
```

The completed final Wave 1 adversarial double-check process ledger was moved to:

```text
markdowns/tmp/curr-archive-20260701-wave1-final-doublecheck/
```

The completed July 1 current-audit handoff and adversarial-audit process ledger
were moved to:

```text
markdowns/tmp/curr-archive-20260701-current-adversarial-audit/
```

The completed July 1 Tier 2 bridge process ledger, provider-native UX controls
process ledger, and repeat Wave 1 adversarial audit process ledger were moved
to:

```text
markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/
```

The completed July 1 second repeat Wave 1 adversarial audit process ledger was
moved to:

```text
markdowns/tmp/curr-archive-20260701-second-repeat-adversarial-audit/
```

Older completed or superseded current-work docs remain in:

```text
markdowns/tmp/curr-archive-20260628/
markdowns/tmp/markdown-audit-20260630/
markdowns/tmp/markdown-audit-20260630-abc-cleanup/
```

## Verified

- `markdowns/curr/` now contains this index, active/implemented R12 Wave 1
  specs, and active Wave 2 specs for codebase-map scaffolding and mid-tool
  checkpoint buffers.
- Completed process/review/spec ledgers are historical evidence only; they no
  longer compete with `current-progress.md`, `things-to-change.md`, or this
  index as current-step truth.
- The R12 skill surface vocabulary now distinguishes projected preloaded skills,
  actual skills to preload, and user-owned skills. That distinction prevents the
  provider-native bridge from confusing generated runtime projections with
  user-owned native skill folders that Wave 1.6-B will sync into the
  client-owned fallback registry.
- R12 scaffold hardening, prompt/memory cost hardening, and provider-native
  skill projection are implemented and validated by Python-change gates, suite
  ladders, focused fake-provider/API simulation tests, Codex/Claude CLI live
  smokes, Branch C attached-board runs, and representative code-writing repair
  benchmarks recorded in the current or archived process ledgers. A focused
  live-provider native-skill invocation proof is also green for both Codex CLI
  and Claude CLI. The final double-check and later current audit added and
  validated non-interactive operator shell smoke coverage for piped command
  scripts, including PowerShell BOM-prefixed slash commands such as `/help`,
  `/history`, `/prompt`, and `/events`.
- The current bounded memory implementation has Tier 0 canonical state, Tier 1
  recent committed facts, deterministic Tier 2 mid-history compact facts, and a
  hard-limited Tier 3 rolling summary. Tier 2 is compacted from Tier 1 by the
  brain; only Tier 3 may use provider/model-backed summary mode.
- A July 1 spec-to-code audit found and closed one public-entrypoint gap:
  `pyocd-debug run/benchmark` now mirror the headless provider-native
  `--provider-native-skills` and `--provider-native-skill-root` controls,
  saved requests record explicit provider-native mode/root fields, and rerun
  replays those fields.
- A July 1 repeat adversarial audit found and closed one metadata gap: OpenAI
  periodic native memory safety-sync turns now keep remote-primary
  `remote-resume` metadata while still passing `previous_response_id`.
- A July 1 second repeat adversarial audit after that metadata fix found no new
  valid spec or product gaps. The full non-hardware suite ladder, focused
  Wave 1 tests, provider-native projection tests, operator shell smoke, and
  live no-hardware Codex/Claude hidden-token native-skill proof were green.
- Completed Wave 1 specs remain in `curr/` as regression contracts until the
  team intentionally archives them behind a canonical Wave 1 closure/index
  record. They are no longer process ledgers, but they are still useful hard-bar
  references while Wave 2 branches build on the Wave 1 substrate.

## Pending Verification

- Branch B's free-host-work / governed-decision boundary, R12 scaffold
  hardening, R12 prompt/memory cost hardening including the Tier 2 memory lane,
  and the provider-native skill bridge are implemented and validated on the
  attached `nucleo_l476rg` and `nrf52840dk` deployment surface available on this
  host where hardware proof was required. The Tier 2 memory bridge itself is a
  software-only feature and was validated without hardware by user instruction.
- Remaining proof gaps are external: live API credentials, exact official-board
  proof beyond the attached board set, and fresh-machine deployment.
- Exact official `nrf52833dk` proof remains pending.
- Cross-prompt interactive provider continuity remains planning-only: the
  current shell preserves settings/history, but not provider handles or compact
  memory across separate user prompts. The proposed Wave 1.5-A fix is
  `wave1-5-A-interactive-session-hardening_spec.md`.
- `wave1-6-B-actions-spec.md` records the Branch B implementation gap where
  pre-registered `run_script` works but native provider-created user-owned
  skills/scripts are not yet synced, validated, registered, and exposed through
  API fallback.
- `wave1-7-UX-dev-provider-visible-status_spec.md` records the proposed Wave 1.7
  developer trace bridge for provider-visible status/reasoning text; it is not
  implemented and does not replace the broader Wave 2 Module D/H stream,
  interrupt, cleanup, and inspector work.
- Wave 2 progress/inspector, mid-tool checkpoint buffers, scoped green approval,
  static context/cache reuse, codebase-map scaffolding, and cleanup guard work
  remains hard prototype scope.
- Wave 2 provider-visible stream and user-interrupt support is planning-only:
  provider turns still expose coarse progress today, not live provider text
  before final output, and in-flight provider cancellation still depends on the
  future Module D/H implementation.
