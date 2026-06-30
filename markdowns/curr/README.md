# Current Working Docs

`markdowns/curr/` is for active or still-useful current-step docs only.
Completed process ledgers, superseded specs, and review artifacts should move to
`markdowns/tmp/`.

## Active Docs

- `things-to-change.md` - broad prototype backlog.
- `r12_turnkey_spec.md` - current R12 turnkey contract.
- `r12-branch-a-live-provider-status.md` - compact Branch A / merged A+B
  live-provider handoff, replacing the completed spec/process/review cluster.
- `r12-branch-b-status.md` - compact Branch B implementation and proof handoff.
- `r12-branch-b-official-portability-closure_spec.md` - remaining stricter
  Branch B closure proof for official board/fresh-machine claims.
- `branch_c_test_plan.md` - current Branch C event/timeout harness and proof
  boundary.
- `p-wave-abc-merge-validation_spec.md` - executed Wave 1 A/B/C merge-back
  validation ledger.
- `p-wave-abc-merge-validation_review.md` - current independent review of the
  merged A/B/C candidate.

## Archive

Completed and redundant docs from previous loops were moved to:

```text
markdowns/tmp/curr-archive-20260628/
markdowns/tmp/markdown-audit-20260630/
markdowns/tmp/markdown-audit-20260630-abc-cleanup/
```

## Verified

- The active list reflects the intended reduced `curr` set after the
  2026-06-30 markdown audit cleanup.
- Completed Branch A strict-recovery, P0 foundation, and A/B additive merge
  artifacts were archived out of `curr`.
- Completed Branch A live-provider and server-tool hardening artifacts were
  replaced by compact status/current docs and archived out of `curr`.
- Completed Branch C process/spec/review fragments and the A/B-only readiness
  review were archived after the A/B/C merge ledger became the current source.

## Pending Verification

- Official `nrf52833dk` second-provider closure still needs an actual
  `nrf52833dk` attached; the current live suite is green for the attached
  `nucleo_l476rg + nrf52840dk` pair.
