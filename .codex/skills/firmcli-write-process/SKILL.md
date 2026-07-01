---
name: firmcli-write-process
description: Deliver a whole Firmware-CLI process through firmcli-spec-loop execution, iterative firmcli-fix-bug repair, and a deployment-grade firmcli-test-suite final gate while keeping a live process ledger. Use when the user wants the FirmCLI write-process workflow for a multi-step feature, roadmap item, rollout, or long-running implementation tracked in a `markdowns/curr/slug_process.md` file.
---

# FirmCLI Write Process

If you have not already loaded `.codex/skills/firmcli-workflow-core/SKILL.md`, read it first.

This skill is self-contained. Do not read legacy slash-command files; any
legacy workflow behavior needed by Codex belongs in this `SKILL.md`.

## Workflow

1. Treat `firmcli-spec-loop` as the execution backbone. For the whole process and for every meaningful sub-step, drive work through the same spec-build-review loop instead of hand-rolling build/review steps. `firmcli-write-process` is the top-level orchestrator: it uses `firmcli-spec-loop` for scoped implementation, `firmcli-fix-bug` for every real repair, and `firmcli-test-suite` as the final deployment gate.
2. Run the spec phase first with `firmcli-specs` or the spec phase inside `firmcli-spec-loop`. Create or update the spec before the first build pass and again whenever the process scope, acceptance surface, deployment scenario, or design constraints materially change.
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
5. Implement the process in small, reversible sub-steps. Each meaningful sub-step must run through `firmcli-spec-loop`:
   - confirm the spec and ledger still match the intended change
   - run `firmcli-spec-loop` for the scoped change or existing `*_spec.md`
   - if the sub-step changes Python code or Python-facing project config, use `.codex/skills/python-change/SKILL.md` and run its validation gate after the final Python edit for that sub-step
   - after the repo-wide Pyright baseline is green, any Python-changing
     sub-step must leave full `uv run pyright --outputjson` green; changed-file
     filtering is no longer a success condition
   - if the loop, review, or smoke checks expose a real bug or must-fix finding, route that issue through `firmcli-fix-bug` instead of making ad hoc follow-up edits
   - after the fix, rerun `firmcli-spec-loop` for that same sub-step before moving on
6. After each meaningful sub-step, run the non-hardware ladder as an extra smoke gate when the targeted spec loop did not already cover the needed checks:
   - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
   - add targeted `--command` entries as needed
7. Do not advance to the next sub-step until the current sub-step is spec-loop-clean or blocked only on explicit hardware proof or a human decision. A sub-step is not clean if Ruff, Pyright, pytest, the non-hardware ladder, targeted smoke checks, docs, or cleanup/process-hygiene checks are red for the touched surface.

## Final test gate

Before declaring the process complete, run `firmcli-test-suite` on the full intended chain. The suite must test the exact future product deployment scenario as closely as the current environment allows, not only isolated unit behavior.

The final suite must include, when applicable:

- the public product entrypoint the user will actually run, not only internal helpers
- the real MCP server/client path or closest available subprocess path
- the provider/auth mode expected in deployment
- multiple model decision turns inside a prompt
- multiple top-level prompts
- multiple user turns in the operator-facing flow, such as repeated `pyocd-debug` shell prompts, history/show/rerun behavior, or the closest current CLI equivalent
- realistic workspace setup, build, flash/verify, artifact capture, and cleanup boundaries
- fresh run roots, fresh provider/session state where the product promises isolation, and no hidden reuse of prior green state unless cache/reuse is itself the feature under test
- explicit process and board-session hygiene: no spawned provider, MCP, pyOCD,
  serial, validation, or board-debug process may remain alive after the run
  unless it is intentionally user-owned and documented as such

If the exact deployment scenario cannot be run by the agent, still test up to the highest possible confidence boundary:

- audit the code path from public entrypoint down through every service layer it depends on
- adversarially list plausible flaws, race conditions, stale-state leaks, portability traps, missing docstrings, bad prompts, unbounded waits, and unverifiable assumptions
- evaluate each suspected flaw against the code and tests; dismiss only with evidence
- fix every real flaw through `firmcli-fix-bug`
- add or strengthen smoke tests, harnesses, dry-runs, mock-provider runs, fake-MCP runs, CLI transcript tests, artifact inspections, and regression tests that emulate the real deployment scenario as closely as possible
- for provider/hardware/MCP tests, prefer task files and JSON files over inline
  PowerShell quoting, set explicit timeouts, snapshot spawned-process
  provenance, attempt normal product cleanup, and audit for orphaned provider,
  MCP, pyOCD, serial, or validation processes after every failure or interrupt
- state exactly what remains untested and why, with the precise hardware/provider/manual hand-off needed

## Failure loop

If the final suite exposes any real bug, missing coverage that can be implemented, deployment-scenario mismatch, portability issue, stale documentation, or regression from an earlier sub-step:

1. Create a concrete issue entry in the process ledger.
2. Route the issue through `firmcli-fix-bug`.
3. Rerun the affected `firmcli-spec-loop` if the fix changed feature behavior or acceptance criteria.
4. Restart the final `firmcli-test-suite` from the beginning, not just the failed row.
5. Repeat for every issue until the full suite runs green from one end to the other after the last fix, or until the only remaining boundary is explicit hardware proof, provider quota/credentials, or a human decision.

Leftover spawned processes, locked probes, open serial ports, or still-connected
debug sessions count as final-suite failures. Route reproducible cleanup bugs
through `firmcli-fix-bug`; if cleanup cannot be proven because of an interrupt or
environment limitation, stop with an explicit deployment ambiguity and a cleanup
runbook.

Do not report the process as complete after a partial rerun. A green final gate means the whole suite passed in one clean end-to-end pass after the last fix, with all applicable Python-change gates, full Pyright, pytest, smoke checks, docs, and cleanup checks green for the final tree.

## Stop conditions

Stop and ask before changing a settled decision or building around an unautomatable setup dependency. Stop at a hand-off when the remaining proof requires real hardware, provider credentials/quota unavailable in the current session, or a deployment environment the agent cannot access. Leave those gaps in the ledger and final response as explicit runbooks; do not claim them.

## Closeout

Report the ledger path, a concise Done/TODO/Limitations summary, docs synced, the spec-loop artifacts used for the last clean execution pass, the final test-suite matrix and evidence, every fix-bug loop taken, validation buckets, the exact deployment scenario tested or emulated, the hardware/provider hand-off runbook, and any open decisions.
