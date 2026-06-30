---
name: firmcli-fix-bug
description: Fix a Firmware-CLI bug end to end by reproducing it, finding the root cause, implementing the smallest correct fix, validating the result, and syncing documentation. Use when the user gives a bug description, failing command, error text, or case id and expects the FirmCLI fix-bug workflow in Codex.
---

# FirmCLI Fix Bug

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

This skill is self-contained. Do not read legacy slash-command files; any
legacy workflow behavior needed by Codex belongs in this `SKILL.md`.

## Workflow

1. Read the authority docs from the core skill.
2. Reproduce the bug before editing anything. Prefer a failing test or a minimal repro. If the bug only appears on hardware, write the exact hardware repro command and then capture the strongest non-hardware signal you can build.
   - For provider-backed, hardware-backed, MCP-backed, pyOCD-backed, serial, or long-running repros, follow the process and board-session hygiene rules from `firmcli-workflow-core`: prefer task/JSON files over fragile inline PowerShell quoting, set explicit timeouts, snapshot spawned-process provenance, and record the run root.
3. State the root cause in one or two sentences.
4. For anything beyond a trivial one-file fix, create or update `markdowns/curr/slug_spec.md`. Use the helper if needed:
   - `python .codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py spec bug-slug --task "bug summary"`
5. If the fix changes Python code or Python-facing project config, read and use `.codex/skills/python-change/SKILL.md` before editing. Its validation gate is required in addition to the FirmCLI ladder.
   Once repo-wide Pyright is green, the Python-change gate requires full
   `uv run pyright --outputjson` success; any Pyright failure is part of the bug
   loop and must be fixed before reporting success.
6. Implement the smallest change in the correct layer.
7. Add or extend a regression guard so the bug cannot silently return.
8. Sync every doc the fix touched in the same unit of work.
9. Run the validation ladder and any targeted repro checks:
   - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
   - add targeted commands with `--command`
10. After every provider/hardware/MCP/pyOCD/serial/long-running repro or validation command, attempt normal product cleanup first, then audit for leftover spawned provider, MCP, pyOCD, serial, validation, or board-debug processes. Clean up only processes this fix pass spawned or can identify by precise provenance. If a spawned process, locked probe, open serial port, or connected debug session remains, treat that as part of the bug unless proven to be an unrelated user process.
11. For Python changes, also run the Python-change script unless already run after the final edit:
   - `python .codex/skills/python-change/scripts/run_python_change_checks.py`
12. Self-review against the same gates as `firmcli-review`. If you still have must-fix findings, loop until clean or until you hit a hardware or decision boundary.
13. For hardware-only proof, stop at the hand-off and do not claim the live result.

## Closeout

Report the root cause, the fix, the regression guard, docs synced, the three verification buckets, the hardware hand-off, and any surfaced conflicts or ambiguities.
