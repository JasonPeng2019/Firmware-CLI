---
name: firmcli-write-process
description: Deliver a whole Firmware-CLI process through repeated spec-build-review passes while keeping a live process ledger. Use when the user wants the Claude `/write-process` behavior for a multi-step feature, roadmap item, rollout, or long-running implementation tracked in a `markdowns/curr/slug_process.md` file.
---

# FirmCLI Write Process

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

Use this skill to mirror `.claude/commands/write-process.md`.

## Workflow

1. Read `.claude/commands/write-process.md`.
2. Run the spec phase first with `firmcli-specs`. Create or update the spec before the first build pass and again whenever the process scope, acceptance surface, or design constraints materially change.
3. Create or update the process ledger:
   - `python .codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py process process-slug --task "process summary"`
4. Keep the ledger current after every meaningful step. It must track:
   - goal and roadmap anchor
   - done
   - in progress
   - TODO
   - limitations and known gaps
   - hardware hand-off
   - open decisions and surfaced issues
   - verified and pending verification
5. Implement the process in small, reversible sub-steps. Each meaningful sub-step must run as its own mini loop:
   - confirm the spec and ledger still match the intended change
   - run `firmcli-build` for the scoped change
   - run `firmcli-review` against the same spec
   - if build, review, or smoke checks expose a real bug or must-fix finding, route that iteration through `firmcli-fix-bug` instead of making ad hoc follow-up edits
   - after the fix, rerun build and review for that same sub-step before moving on
6. After each meaningful sub-step, run the non-hardware ladder as an extra smoke gate when the targeted build/review loop did not already cover the needed checks:
   - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
   - add targeted `--command` entries as needed
7. Do not advance to the next sub-step until the current sub-step is review-clean or blocked only on explicit hardware proof or a human decision.
8. Before declaring the process complete, run `firmcli-test-suite` on the full intended chain.
9. If the suite exposes a real bug, missing coverage that can be implemented, or a regression introduced by an earlier sub-step, route it through `firmcli-fix-bug`, then rerun the affected build/review loop and the full suite. Repeat until the agent-verifiable surface is green or the remaining gap is an explicit hardware or decision boundary.
10. Stop and ask before changing a settled decision or building around an unautomatable setup dependency.
11. Leave board-only proof in the ledger and the final response as an explicit hardware runbook.

## Closeout

Report the ledger path, a concise Done/TODO/Limitations summary, docs synced, the last spec/build/review artifacts used for the final green pass, validation buckets, the hardware hand-off runbook, and any open decisions.
