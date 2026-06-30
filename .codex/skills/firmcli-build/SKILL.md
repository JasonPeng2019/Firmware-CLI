---
name: firmcli-build
description: Implement a reconciled Firmware-CLI spec or address a Firmware-CLI review file while keeping code and docs in sync. Use when the user wants the FirmCLI build workflow, including targeted implementation, smoke checks, and honest hardware hand-off.
---

# FirmCLI Build

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

This skill is self-contained. Do not read legacy slash-command files; any
legacy workflow behavior needed by Codex belongs in this `SKILL.md`.

## Workflow

1. Read `superpowers/agent_consistency_playbook.md`, `markdowns/firmware_agent_build_plan_concrete (10).md`, and `superpowers/agent_coding_playbook.md` on every build.
2. Read `superpowers/agent_doc_sync_playbook.md` and `superpowers/agent_portability_playbook.md` when the task touches docs, setup, config, dependencies, or first-run behavior.
3. Read the spec and any review file in full. If no spec path was given, use the latest `markdowns/curr/*_spec.md`.
4. Read the current state of every file you will touch before editing.
5. Re-check that the spec still matches the build plan and current code. If it is stale or contradicts a settled decision, stop and surface it.
6. Implement only the scoped change. Do not silently expand scope.
7. Enforce the repo rules while editing:
   - no hardware claims without a real run
   - no hardcoded ports, paths, targets, baud rates, probe types, or OS assumptions
   - add origin tags for non-obvious values
   - build on pyOCD, pyserial, and `mcp` instead of reimplementing them
   - keep changes inside the correct layer
8. Sync the one correct doc in the same unit of work. For MCP tool behavior, update the docstring in `server.py`. For shell/operator flow, update `stage0_setup.md`. For architecture or decisions, update the build plan.
9. Run the non-hardware check ladder from the repo root:
   - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
   - add extra commands with `--command` for targeted tests or harnesses
10. If a check fails, fix the root cause and rerun the relevant commands.
11. When this build is part of `firmcli-spec-loop`, `firmcli-write-process`, `firmcli-fix-bug`, or `firmcli-test-suite`, do not treat the code edit as done yet. Hand the result straight into `firmcli-review`, and if review or later validation exposes a real bug or must-fix finding, route that failure through `firmcli-fix-bug` rather than patching around it informally.
12. For hardware-only acceptance criteria, stop at an explicit hand-off with the exact command and expected output.

## Closeout

End with the three verification buckets, files changed, docs synced, surfaced conflicts, and the single next step: either review with `firmcli-review` or return to the caller's bug-fix or suite loop when that workflow is already in progress.
