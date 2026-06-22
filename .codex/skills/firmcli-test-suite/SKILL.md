---
name: firmcli-test-suite
description: Validate a whole Firmware-CLI feature chain, close missing coverage when possible, and return a trustworthy pass-fail matrix. Use when the user wants the Claude `/test-suite` behavior for a cross-feature suite, runtime surface, regression ladder, or acceptance run in this repo.
---

# FirmCLI Test Suite

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

Use this skill to mirror `.claude/commands/test-suite.md`.

## Workflow

1. Read `.claude/commands/test-suite.md`.
2. Read the build plan, `README.md`, `markdowns/ROADMAP.md`, and `markdowns/current-progress.md`.
3. Map the requested chain to concrete checks and note any missing validation surface.
4. For larger efforts, create or update a spec with the helper:
   - `python .codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py spec suite-slug --task "suite summary"`
5. Run the suite ladder from the repo root:
   - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
   - add `--command` entries for chain-specific tests, harnesses, or dry-runs
6. If the ladder exposes a real bug or a coverage gap that can be fixed without user input, fix it and rerun the relevant checks before reporting back.
7. If a finding requires a settled-decision change or real hardware proof, surface it and stop at the hand-off.
8. Produce a matrix with `feature | check run | result | evidence`.
9. Keep the outcome honest: a suite can be green only up to the hardware boundary, never past it.

## Closeout

Report the matrix, the real command output, the ordered hardware hand-off, and the top-line verdict for the agent-verifiable surface.
