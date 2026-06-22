---
name: firmcli-write-process
description: Deliver a whole Firmware-CLI process through repeated spec-build-review passes while keeping a live process ledger. Use when the user wants the Claude `/write-process` behavior for a multi-step feature, roadmap item, rollout, or long-running implementation tracked in a `markdowns/curr/slug_process.md` file.
---

# FirmCLI Write Process

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

Use this skill to mirror `.claude/commands/write-process.md`.

## Workflow

1. Read `.claude/commands/write-process.md`.
2. Run the spec phase first. Create or update the spec if it does not exist.
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
5. Implement the process in small, reversible sub-steps.
6. After each meaningful sub-step, run the non-hardware ladder:
   - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
   - add targeted `--command` entries as needed
7. Self-review each sub-step against the same gates as `firmcli-review`. Fix must-fix findings before moving on.
8. Stop and ask before changing a settled decision or building around an unautomatable setup dependency.
9. Leave board-only proof in the ledger and the final response as an explicit hardware runbook.

## Closeout

Report the ledger path, a concise Done/TODO/Limitations summary, docs synced, validation buckets, the hardware hand-off runbook, and any open decisions.
