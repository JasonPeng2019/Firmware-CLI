# Wave 1 Post-A/B/C Add-Ons Inventory

> STATUS: CURRENT INVENTORY - audit aid, not an implementation spec.
> Created from a second pass through `markdowns/curr`, `markdowns/tmp`,
> `markdowns/current-progress.md`, `markdowns/R12_P_SPLIT.md`, and
> `markdowns/things-to-change.md`.

## Purpose

This file inventories the R12 / Wave 1 work that was layered on top of, or
adjacent to, the original Wave 1 Branch A/B/C split.

It exists because the active `curr` specs alone do not show every add-on:
`markdowns/tmp` contains archived implementation specs, process ledgers,
validation ledgers, and superseded plans that still explain how the product got
to the current state.

This is not a claim that every item below is complete. Items are classified as:

- `implemented add-on`: product/code behavior that was added or changed.
- `validation/proof add-on`: evidence, harness, or proof coverage added around
  existing behavior.
- `gap spec`: active proposed work for a known missing behavior.
- `superseded/partial`: old or incomplete work that was replaced or narrowed by
  later specs.

## Active Implemented R12 / Wave 1 Add-Ons

These are the eight active R12 add-ons that remain in `markdowns/curr` as hard
bar references or validation records.

| Item | Primary doc | Classification | What it added |
|---|---|---|---|
| R12 context scaffold hardening | `markdowns/curr/r12-context-scaffold-hardening_spec.md` | implemented add-on | Product/client-owned model-native skill root, runtime-copy-only recovery, structured skill-load failures, `load_tool_details`, invalid-call auto-details, strict loaded-detail guardrails before governed tool/script/compound-action execution, prompt ordering/dedupe, and provider failure classification. |
| R12 delta compact indexes | `markdowns/curr/r12-delta-compact-indexes_spec.md` | implemented add-on | Compact skill context and compact governed-tool indexes in ordinary `remote-delta` provider turns without reverting to full schema/context reinjection. |
| R12 prompt/memory cost hardening | `markdowns/curr/r12-prompt-memory-cost-hardening_spec.md` | implemented add-on | Bootstrap/full versus compact later-turn prompt modes, rendered-vs-available prompt accounting, focused detail rendering, common safe detail preload, bounded provider memory, and credentials-free OpenAI/Anthropic API-path simulation. |
| R12 Tier 2 memory bridge | `markdowns/curr/r12-tier2-memory-bridge_spec.md` | implemented add-on | Four-tier provider memory behavior for the current turnkey path: Tier 0 canonical state, Tier 1 recent facts, deterministic Tier 2 mid-history compact facts, and hard-limited Tier 3 rolling summary. Only Tier 3 may use model-backed summary mode. |
| R12 provider-native skill bridge | `markdowns/curr/r12-provider-native-skill-bridge_spec.md` | implemented add-on | Runtime projection of FirmCLI-owned skills into run-local `.codex/skills` and `.claude/skills` views for CLI providers, Claude `--allowedTools Skill(...)`, projection metadata, and deterministic `load_skills` fallback for API providers. |
| R12 provider-native skill invocation proof | `markdowns/curr/r12-provider-native-skill-invocation-proof_spec.md` | validation/proof add-on | Focused live Codex/Claude proof that CLI providers actually consume projected native skill bodies and return valid `TurnDecision` output without falling back to `load_skills`. |
| R12 provider-native UX CLI controls | `markdowns/curr/r12-provider-native-ux-cli-controls_spec.md` | implemented add-on | Public `pyocd-debug run/benchmark` controls for provider-native skill mode/root, saved request persistence, and rerun replay of provider-native settings. |
| R12 OpenAI native sync metadata | `markdowns/curr/r12-openai-native-sync-metadata_spec.md` | implemented add-on | Periodic native memory safety-sync for OpenAI remote-primary keeps truthful `remote-resume` metadata while using `previous_response_id`. |

## Additional Archived Add-Ons Found In `markdowns/tmp`

These were not all in the earlier shortlist. Some predate the final A/B/C
merge-back, but they are part of the Wave 1 substrate or the immediate
post-merge correction/audit history.

| Item | Primary archived docs | Classification | What it added or corrected |
|---|---|---|---|
| Branch A strict provider recovery | `markdowns/tmp/curr-archive-20260628/branch-a-strict-provider-recovery_spec.md` | superseded/partial | Specified fail-closed provider resume handling, typed resume failures, explicit recovery-from-memory, and stronger brain-owned crash memory. Current active docs still show the same user-facing gap as Wave 1.5-A: one interactive shell does not yet preserve provider handles/memory across separate prompts. |
| Branch A deployment/live-provider proof suite | `markdowns/tmp/curr-archive-20260628/branch-a-deployment-suite_spec.md`; `markdowns/tmp/markdown-audit-20260630/branch-a-live-provider-hardware-suite_spec.md` | validation/proof add-on | Added live-provider and attached-board proof expectations around Branch A provider/session behavior. These are proof ledgers, not separate product features. |
| Branch A/B additive merge | `markdowns/tmp/curr-archive-20260628/branch-a-b-additive-merge_spec.md` | integration add-on | Merged Branch A provider/session/schema behavior with Branch B action/batch/client-action behavior without intentionally dropping either side. |
| Branch B action boundary | `markdowns/tmp/curr-archive-20260628/r12-branch-b-action-boundary_spec.md` | implemented add-on | Classified model-native, brain-local, server-native, batch, and client-action actions; added batch/wait/UART/client-action boundary behavior in the Branch B line. Later specs corrected the host-action subset. |
| Branch B public deployment completion | `markdowns/tmp/curr-archive-20260628/r12-branch-b-full-deployment-completion_spec.md`; `markdowns/tmp/curr-archive-20260628/r12-branch-b-multi-loop-real-deployment_test_report.md` | implemented add-on | Added public `--client-action NAME=PATH` registration through the brain CLI/app path, provider prompt visibility for registered actions, `client_actions.json` metadata, and real Codex/MCP/hardware proof for preregistered `run_script`. This did not implement dynamic provider-authored scripts during a run. |
| R12 CLI task input robustness | `markdowns/tmp/curr-archive-20260628/r12-cli-task-input-robustness_spec.md` | implemented add-on | Hardened customer prompt ingestion for deployment runs, including robust task-file/task-text handling and validation around mutually exclusive task sources. |
| R12 server-tool action hardening | `markdowns/tmp/markdown-audit-20260630/r12-server-tool-action-hardening_spec.md` | implemented add-on | Centralized server-native action names, normalized `server_tool:<name>` and legacy nested `arguments.arguments` provider output, stripped redundant tool names, and failed closed on conflicting duplicated arguments. |
| Branch C completion | `markdowns/tmp/markdown-audit-20260630-abc-cleanup/r12-branch-c-completion_spec.md`; `markdowns/tmp/curr-archive-20260630-hardbar-reset/branch_c_test_plan.md` | implemented add-on | Completed the event spine and timeout-policy slice: normalized brain events, effective timeout state, model timeout/iteration proposals with brain clamps, hidden server timeout sync, and Branch C harness hardening. |
| Branch C provider/portability coverage | `markdowns/tmp/markdown-audit-20260630-abc-cleanup/r12-branch-c-provider-portability-coverage_spec.md` | validation/proof add-on | Made Branch C acceptance provider-aware rather than Codex-only, with skip/auth/parse/schema/hardware distinctions and CLI-provider coverage expectations. Live API proof remains external. |
| A/B/C merge validation | `markdowns/tmp/curr-archive-20260630-hardbar-reset/p-wave-abc-merge-validation_spec.md` | validation/proof add-on | Validated the merged Branch A/B/C state and recorded that Branch B still needed a hard-bar correction for provider-native host work. |
| Branch C harness acceptance fixes | `markdowns/tmp/curr-archive-20260630-hardbar-reset/wave1-abc-adversarial-audit_process.md` | implemented/test add-on | Fixed acceptance false negatives by accepting schema-valid `action_batch` decisions and `TurnkeyRunResult.mcp_tools_used` evidence where appropriate. |
| Pyright baseline cleanup | `markdowns/tmp/curr-archive-20260630-hardbar-reset/pyright-baseline-cleanup_process.md` | quality-gate add-on | Burned down the repo-wide Pyright baseline to zero diagnostics and made full Pyright a hard Python-change gate rather than a filtered/chosen-file check. |
| Final disconnect cleanup failure handling | `markdowns/tmp/curr-archive-20260630-hardbar-reset/wave1-turnkey-cleanup-failure_spec.md` | implemented add-on | Stopped swallowing final `run_turnkey` disconnect cleanup failures. Such failures now surface as `unexpected_failure` / blocked tooling results with active session state preserved. |
| Branch B hard-bar prototype correction | `markdowns/tmp/curr-archive-20260630-wave1-final/branch-b-hardbar-prototype_spec.md` | implemented add-on | Removed `read_file`, `replace_file`, and `run_build` from model-facing governed decisions, refused stale host-action decisions, observed provider-native workspace changes at governed boundaries, and kept board verification governed. |
| Model-native skill loading | `markdowns/tmp/curr-archive-20260630-wave1-final/model-native-skill-loading_spec.md` | implemented add-on | Removed remaining governed host-action compatibility models/branches, added `load_skills` as a context-expansion decision, loaded skill dependencies/init scripts, injected loaded skill context, and exposed per-skill runtime folders. |
| Compact tool schema index | `markdowns/tmp/curr-archive-20260630-wave1-final/compact-tool-schema-index_spec.md` | implemented add-on | Added compact prompt metadata from live MCP/governed tool metadata so providers see names, short descriptions, required/optional argument hints, and stable semantics without full schema dumps every turn. The later `r12-delta-compact-indexes_spec.md` extended this into ordinary `remote-delta` turns. |
| Prompt/detail audit fixes | `markdowns/tmp/curr-archive-20260630-delta-index-final/wave1-audit-prompt-detail-fixes_spec.md` | implemented add-on | Fixed prompt ordering, removed duplicated compact skill context, preserved focused tool details after invalid MCP argument validation, and made `action_batch` schema exclude `finalize`. |
| R12 scaffold adversarial rerun | `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/wave1-r12-adversarial-audit-rerun_spec.md`; `markdowns/tmp/curr-archive-20260630-r12-scaffold-final/r12-context-scaffold-hardening_process.md` | validation/proof add-on | Rechecked the scaffold hardening implementation and archived the process evidence. The active contract is the current scaffold-hardening spec. |
| Claude-restored full suite | `markdowns/tmp/curr-archive-20260701-provider-native-doc-sync/wave1-full-suite-claude-restored_spec.md` | validation/proof add-on | Re-ran attached-board CLI proof and credentials-free API simulation after Claude auth/quota was restored. Exact `nrf52833dk`, live API, and fresh-machine proof remained external. |
| Provider-native full product suite | `markdowns/tmp/curr-archive-20260701-wave1-final-audit-handoff/wave1-full-product-suite-provider-native_spec.md` | validation/proof add-on | Recorded full-product validation around provider-native skill projection and fallback behavior. |
| Operator shell non-interactive behavior | `markdowns/tmp/curr-archive-20260701-wave1-final-doublecheck/wave1-final-adversarial-doublecheck_process.md`; `markdowns/current-progress.md` | implemented add-on | Fixed piped/non-console `pyocd-debug` command scripts so slash commands such as `/history`, `/prompt`, `/events`, and `/quit` work without hanging or crashing. |
| Operator shell BOM slash-command parsing | `markdowns/tmp/curr-archive-20260701-current-adversarial-audit/wave1-current-adversarial-audit_process.md`; `markdowns/current-progress.md` | implemented add-on | Fixed PowerShell BOM-prefixed stdin so slash commands such as `/help` are not misread as task text. |
| Repeat adversarial audit ledgers | `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/wave1-repeat-adversarial-audit_process.md`; `markdowns/tmp/curr-archive-20260701-second-repeat-adversarial-audit/wave1-second-repeat-adversarial-audit_process.md` | validation/proof add-on | Rechecked stale governed action removal, four-tier memory, provider continuation metadata, provider-native skill projection, public controls, operator shell behavior, and no-hardware Codex/Claude hidden-token native-skill proof. |

## Active Gap Specs Added After These Audits

These are not implemented add-ons. They are active proposed Wave 1 gap closures
created after the later audits exposed missing behavior or UX needs.

| Item | Primary doc | Classification | Gap recorded |
|---|---|---|---|
| Wave 1.5-A interactive session hardening | `markdowns/curr/wave1-5-A-interactive-session-hardening_spec.md` | gap spec | A single `pyocd-debug` interactive shell should behave like one persistent provider session across consecutive user prompts. Current shell settings/history are not enough. |
| Wave 1.6-B actions/native skill sync | `markdowns/curr/wave1-6-B-actions-spec.md` | gap spec | Branch B has preregistered `--client-action` plus `run_script`, but not full provider-authored `.codex`/`.claude` skill sync, validation, repair, canonical registry, and API fallback. |
| Wave 1.7 dev provider-visible status | `markdowns/curr/wave1-7-UX-dev-provider-visible-status_spec.md` | gap spec | Developers need opt-in provider-visible status/reasoning text and brain heartbeats during long provider turns. Current CLI providers wait on captured subprocess output and do not show live provider-visible text before final output. |

## Future Wave 2 Specs Seen During The Pass

These are real active specs, but they are not counted as completed Wave 1
add-ons.

| Item | Primary doc | Status |
|---|---|---|
| Provider-visible stream and interrupt | `markdowns/curr/wave2-provider-stream-interrupt_spec.md` | planning-only Wave 2 Module D/H work |
| Mid-tool checkpoint buffers | `markdowns/curr/wave2-midtool-checkpoints_spec.md` | planning-only Wave 2 Module E work |
| Client-side codebase map | `markdowns/curr/wave2-codebase-map_spec.md` | planning-only Wave 2 Module G work |
| UX Layer Pass 2 | `markdowns/UXLayer.md` | broader UX design note for provider streaming, interrupt, inspector, and checkpoint follow-up |

## Documents Scanned But Not Counted As Wave 1 Add-Ons

The second pass also found older or adjacent docs that should not be treated as
new Wave 1 add-ons unless a later task explicitly reopens them:

- P0/P0.0 foundation, static-audit, and Wave 0 reconcile docs.
- R10/R11 benchmark and STM32 bring-up docs.
- ThreadX demo/spec docs outside the active R12 prototype gate.
- General build-plan gap analysis and historical Ben/Jason merge rationale.
- `live-provider-suite-*.txt` prompt snippets, which are test inputs rather
  than product features.
- `r12-branch-b-official-portability-closure_spec.md`, which is a pending proof
  boundary for exact official-board/fresh-host portability rather than an
  implemented add-on.
- `r12-claude-refresh-hardening-test-plan_spec.md`, which was superseded by
  later Claude-restored validation records.

## Audit Conclusion

After the second pass through `markdowns/tmp`, the R12 / Wave 1 add-on set is
larger than the original eight active `curr` specs. The additional material is
mostly archived implementation fixes, validation/proof additions, and audit
corrections around Branch B action boundaries, Branch C harness/proof behavior,
prompt/detail rendering, provider-native skill proof, and operator-shell
non-interactive behavior.

The current known unimplemented Wave 1 gap specs are:

- `wave1-5-A-interactive-session-hardening_spec.md`
- `wave1-6-B-actions-spec.md`
- `wave1-7-UX-dev-provider-visible-status_spec.md`

The current known future Wave 2 specs are:

- `wave2-provider-stream-interrupt_spec.md`
- `wave2-midtool-checkpoints_spec.md`
- `wave2-codebase-map_spec.md`
