---
description: "Run the full spec → build → review loop end to end, feeding review findings back into build until CLEAN (or hardware hand-off remains)"
argument-hint: "<what to build — a sentence, a roadmap id like R12, or an existing *_spec.md path>"
---

# /spec-loop — the whole loop in one go

This is Karpathy's loop wired for this repo: **/specs → /build → /review**, then feed review findings
back into another **/build** pass until the review is `CLEAN` (or the only remaining items are
hardware hand-offs an agent cannot perform).

Target:

> $ARGUMENTS

## Drive the loop

1. **Spec.** If `$ARGUMENTS` is already a `*_spec.md` path, use it. Otherwise run the `/specs` workflow
   (`.claude/commands/specs.md`) to produce `markdowns/curr/<slug>_spec.md`. **If the spec surfaces a
   `⚠️ CONFLICT` or a settled-decision change that needs the user, STOP and ask before building** — do
   not loop over an unresolved contradiction.
2. **Build.** Run the `/build` workflow (`.claude/commands/build.md`) against the spec.
3. **Review.** Run the `/review` workflow (`.claude/commands/review.md`) against the spec.
4. **Iterate.** If the review is `CHANGES REQUESTED`, run `/build` again with both the spec and
   `markdowns/curr/<slug>_review.md` (fix highest severity first), then `/review` again. Repeat.
5. **Stop conditions** — stop and report when ANY of these is true:
   - the review is `CLEAN` and only hardware hand-off items remain;
   - you've completed **3 build↔review iterations** without reaching CLEAN (per coding playbook §7:
     detect non-progress, escalate rather than thrash);
   - a finding requires a settled-decision change or a real-hardware result you cannot get — surface it
     and hand off.

## Honesty rule for the whole loop

Because you cannot touch the boards, "the loop is done" never means "verified on hardware." It means
**everything an agent can verify is green and the hardware hand-off is written**. Report the final state
in three buckets — verified-here / non-hardware-verified / pending-hardware — and end with the exact
commands the human runs to close the hardware gap (from `markdowns/current-progress.md`).

## Final report

Give the user: the spec path, the review path, the number of iterations, the final verdict, the list of
synced docs, every surfaced `⚠️`, and the hardware hand-off block.
