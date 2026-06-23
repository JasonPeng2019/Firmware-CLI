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
5. If the review requests changes or the build/review loop exposes a real bug, route that iteration through `firmcli-fix-bug`, then run `firmcli-build` and `firmcli-review` again against the updated spec.
6. When the scoped change affects a feature chain, setup path, acceptance surface, or regression-prone workflow, run `firmcli-test-suite` after the review reaches clean.
7. If the suite exposes a real bug or repairable coverage gap, route it through `firmcli-fix-bug`, then return to build, review, and suite until the suite is green or the remaining boundary is hardware-only or requires a human decision.
8. Stop when any of these is true:
   - the review is clean, the required suite pass is green, and only hardware hand-off items remain
   - three full build-review iterations completed without reaching clean before the suite stage
   - a finding requires a real hardware result or a human decision you cannot supply
9. Keep the final report in the three verification buckets and include the exact hardware hand-off commands.

## Closeout

Report the spec path, review path, iteration count, whether a suite pass was required and run, final verdict, synced docs, surfaced conflicts, and hardware hand-off block.
