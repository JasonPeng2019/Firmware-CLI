---
name: firmcli-specs
description: Write reconciled task specs for Firmware-CLI before any implementation work. Use when the user asks to spec or plan a feature, a bug fix, a roadmap item, or a validation effort in this repo and the output should be a `markdowns/curr/slug_spec.md` file.
---

# FirmCLI Specs

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

This skill is self-contained. Do not read legacy slash-command files; any
legacy workflow behavior needed by Codex belongs in this `SKILL.md`.

## Workflow

1. Read the authority docs in the load order from the core skill.
2. Read `superpowers/spec_build_review_loop_playbook.md` when you need the broader loop semantics or artifact conventions.
3. Read `markdowns/ROADMAP.md`, `markdowns/current-progress.md`, and every current file the task will touch or depend on.
4. Build a reconciliation list:
   - what the build plan says
   - what the current code does
   - what other docs or notes say
   - where they disagree
5. Surface every conflict or ambiguity in one place. If the task requires changing a settled decision in the build plan, stop and ask before proceeding.
6. Create or update the spec file in `markdowns/curr/`. Use the helper when a shell is faster than writing the skeleton by hand:
   - `python .codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py spec my-task --task "task summary"`
7. Ensure the spec contains:
   - the proposal status banner
   - plain-English goal and roadmap anchor
   - scope and non-scope
   - reconciliation summary
   - design
   - board-facts-as-data and origin tags
   - documentation plan
   - portability
   - verification plan
   - acceptance criteria
   - verified and pending verification
8. Do not edit product code or test files during this phase unless the user explicitly changes the request.

## Closeout

End with the spec path, roadmap anchor, the reconciliation summary, and the next step: implement with `firmcli-build`.
