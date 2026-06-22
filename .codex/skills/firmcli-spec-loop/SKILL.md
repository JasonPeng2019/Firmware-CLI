---
name: firmcli-spec-loop
description: Run the full Firmware-CLI spec-build-review loop end to end, feeding review findings back into new build passes until the agent-verifiable surface is clean. Use when the user wants the Claude `/spec-loop` behavior replicated in Codex for a feature, bug, roadmap item, or validation task.
---

# FirmCLI Spec Loop

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

Use this skill to mirror `.claude/commands/spec-loop.md`.

## Workflow

1. If the input is already a `*_spec.md` path, use it. Otherwise, run `firmcli-specs` first.
2. If the spec surfaces a conflict or a settled-decision change that needs user approval, stop and ask before building.
3. Run `firmcli-build` against the spec.
4. Run `firmcli-review` against the same spec.
5. If the review requests changes, run `firmcli-build` again with the spec and review findings, then review again.
6. Stop when any of these is true:
   - the review is clean and only hardware hand-off items remain
   - three build-review iterations completed without reaching clean
   - a finding requires a real hardware result or a human decision you cannot supply
7. Keep the final report in the three verification buckets and include the exact hardware hand-off commands.

## Closeout

Report the spec path, review path, iteration count, final verdict, synced docs, surfaced conflicts, and hardware hand-off block.
