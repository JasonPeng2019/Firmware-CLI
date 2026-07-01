---
name: firmcli-test-suite
description: Validate a whole Firmware-CLI feature chain, close missing coverage when possible, and return a trustworthy pass-fail matrix. Use when the user wants the FirmCLI test-suite workflow for a cross-feature suite, runtime surface, regression ladder, or acceptance run in this repo.
---

# FirmCLI Test Suite

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

This skill is self-contained. Do not read legacy slash-command files; any
legacy workflow behavior needed by Codex belongs in this `SKILL.md`.

## Workflow

1. Read the build plan, `README.md`, `markdowns/ROADMAP.md`, and `markdowns/current-progress.md`.
2. Map the requested chain to concrete checks and note any missing validation surface. Treat `firmcli-spec-loop` as the acceptance backbone for any feature behavior, deployment behavior, or regression-prone workflow that the suite is validating.
3. For larger efforts, create or update a spec with the helper:
   - `python .codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py spec suite-slug --task "suite summary"`
4. Before any provider-backed, hardware-backed, MCP-backed, or long-running check,
   apply the process and board-session hygiene rules from
   `firmcli-workflow-core`: prefer task/JSON files over fragile inline
   PowerShell quoting, set explicit timeouts, snapshot relevant processes, and
   record the run root or provenance needed to identify spawned children.
5. Run the suite ladder from the repo root:
   - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
   - add `--command` entries for chain-specific tests, harnesses, or dry-runs
6. After every provider/hardware/MCP/long-running check, attempt normal product
   cleanup first, then audit for leftover spawned `uv`, `python`, `node`,
   `codex`, `claude`, `pyocd`, MCP server, debug-session, and serial-port
   resources. Clean up only processes that this suite spawned or can identify by
   precise provenance. Treat any leftover spawned process, locked probe, open
   serial port, or still-connected board session as a failing suite row or an
   explicit deployment ambiguity.
7. If the ladder exposes a real bug or a coverage gap that can be fixed without user input, route that failure through `firmcli-fix-bug`. Do not patch suite failures ad hoc.
8. During each suite-driven repair pass, keep the workflow disciplined:
   - update or create the narrowest spec needed for the fix
   - run `firmcli-spec-loop` for that spec unless this suite was invoked from an already-active spec-loop for the exact same spec; in that parent-loop case, make the fix and return control so the parent can rerun its build/review/suite sequence
   - build the fix only through the spec-loop/build path, or through `firmcli-fix-bug` when the repair is a narrow reproduced defect
   - if the fix changes Python code, use `.codex/skills/python-change/SKILL.md` and run its validation gate after the final Python edit
   - after the Pyright baseline is green, a Python-changing repair is not suite-clean unless full `uv run pyright --outputjson` is green
   - review the fix
   - rerun the targeted failing checks
   - restart the full suite from the beginning before reporting green
9. If a finding requires a settled-decision change or real hardware proof, surface it and stop at the hand-off.
10. Produce a matrix with `feature | check run | result | evidence`, including cleanup/orphan-process evidence for rows that spawn providers, MCP, pyOCD, serial, or hardware sessions.
11. Keep the outcome honest: a suite can be green only up to the hardware boundary, never past it. The suite is not green after a targeted rerun alone; it is green only after every applicable row passes in one clean full-suite pass after the last repair, with full Pyright, pytest, smoke checks, docs, and cleanup checks green for the final tree.

## Closeout

Report the matrix, the real command output, the ordered hardware hand-off, the fix loops taken if any, and the top-line verdict for the agent-verifiable surface.
