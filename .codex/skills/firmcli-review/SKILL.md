---
name: firmcli-review
description: Review a Firmware-CLI build against its spec and the `superpowers` playbooks. Use when the user wants an independent review pass that reruns checks, writes a `markdowns/curr/slug_review.md` file, and determines whether the build is clean or needs changes.
---

# FirmCLI Review

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

Use this skill to mirror `.claude/commands/review.md`.

## Workflow

1. Read `.claude/commands/review.md`.
2. Read the spec, the changed code, and the changed docs in full.
3. Reload the authority docs you are judging against:
   - `superpowers/agent_consistency_playbook.md`
   - `superpowers/agent_coding_playbook.md`
   - `superpowers/agent_doc_sync_playbook.md`
   - `superpowers/agent_portability_playbook.md`
   - `superpowers/agent_script_doc_playbook.md`
   - `markdowns/firmware_agent_build_plan_concrete (10).md`
4. Review as an independent judge, not as the builder.
5. Check spec conformance, honesty boundary, hardcoding, origin tags, layering, doc-sync, portability, and the executed smoke checks.
6. Rerun the checks yourself from the repo root:
   - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
   - add targeted commands with `--command` when the spec or change set needs more coverage
7. Write the review to `markdowns/curr/slug_review.md`. Use the helper to create the shell when needed:
   - `python .codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py review my-task --task "task summary"`
8. Structure the review with:
   - verdict
   - findings table with severity, violated gate, file:line, issue, and concrete fix
   - hardware hand-off status
   - what is genuinely good and should not regress
9. If the review is not clean, direct the next pass to `firmcli-build`.

## Closeout

End with the review path and either "review clean" or "review requests changes", plus the exact next action.
