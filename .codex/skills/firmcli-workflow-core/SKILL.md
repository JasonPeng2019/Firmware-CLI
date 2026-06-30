---
name: firmcli-workflow-core
description: Load the Firmware-CLI repo's authority order, repo-specific safety rules, and helper scripts for the Codex FirmCLI workflow. Use when Codex needs to work under the `superpowers` playbooks, scaffold spec/review/process artifacts, run the non-hardware validation ladder, or self-test the local `.codex` skill suite.
---

# FirmCLI Workflow Core

Read this skill before using the other `firmcli-*` workflow skills or when you need the repo's shared operating rules.

Resolve the project repo root before reading or running anything. Use the directory that contains both `.codex/skills` and `superpowers`. In this workspace, if the skills are copied into the outer `FirmCLI` folder, the project root is usually `FirmCLI/Firmware-CLI`.

## Load Order

Read these repo documents in this order before writing:

1. `superpowers/agent_index_START_HERE.md`
2. `superpowers/agent_consistency_playbook.md`
3. `markdowns/firmware_agent_build_plan_concrete (10).md`
4. Task-specific playbooks:
   - `superpowers/agent_coding_playbook.md` for code or implementation-doc changes
   - `superpowers/agent_doc_sync_playbook.md` whenever code or governing docs move
   - `superpowers/agent_portability_playbook.md` for setup, config, install, dependency, or first-run work
   - `superpowers/agent_script_doc_playbook.md` for MCP docstrings or shell/operator scripts
   - `superpowers/spec_build_review_loop_playbook.md` when running the spec/build/review loop
5. The current state of every file you will touch or depend on, in full

Respect the repo's authority order:

- The build plan wins over everything else.
- The coding playbook is binding under the build plan.
- The committed `main` state is reality, but it is subordinate to the plan.
- Other docs, branches, and notes are proposals until reconciled.

Surface conflicts instead of silently resolving them. Never claim a hardware result that was not produced by a real board in the current session.

## Process and Board-Session Hygiene

Provider, MCP, pyOCD, serial, hardware, and long validation commands must not
leave child processes, debug sessions, serial ports, or boards alive after the
check that spawned them.

Before running any provider-backed, hardware-backed, MCP-backed, or long-running
subprocess check:

- prefer task files, JSON files, or generated argument files over fragile inline
  PowerShell quoting for prompts and JSON payloads
- set an explicit timeout appropriate to the proof being run
- record enough context to identify the spawned command, run root, and child
  process tree when possible
- snapshot relevant pre-existing processes so cleanup does not broad-kill user
  work

After each such check, including failures and interrupts:

- attempt normal product cleanup first, especially MCP `disconnect`, serial-port
  close, provider session close where available, and run-artifact finalization
- audit for leftover `uv`, `python`, `pyright`, `pytest`, `node`, `codex`,
  `claude`, `pyocd`, and repo MCP server processes
- clean up only processes that this workflow spawned or can identify by run root,
  command line, parent process, or other precise provenance
- never broad-kill unrelated user processes just because their names match
- treat an identified leftover spawned process, locked probe, open serial port,
  or still-connected debug session as a test failure or deployment ambiguity
  until it is cleaned up or handed off explicitly

If the agent cannot prove cleanup because the environment hides child processes
or the user interrupted the command, state that uncertainty in the closeout and
give the exact process/session audit command to run next.

## Shared Helpers

Use these scripts from the folder that contains this `.codex` tree. They auto-resolve the real Firmware-CLI repo root:

- `.codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py`
  - Create `markdowns/curr/slug_spec.md`, `slug_review.md`, or `slug_process.md` with repo-aligned section templates.
- `.codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py`
  - Run the non-hardware validation ladder and capture real command output.
- `.codex/skills/firmcli-workflow-core/scripts/self_test_skills.py`
  - Validate the local skill suite, required source files, and skill metadata.

Read [references/source-map.md](references/source-map.md) when you need the mapping from FirmCLI workflow phases to Codex skills. That reference is historical/contextual; Codex skills must remain self-contained and must not require reading legacy slash-command files.

## Python Code Changes

For any Python code change under this repo, use
`.codex/skills/python-change/SKILL.md` in addition to this core skill. That
skill owns the Python-specific edit discipline and validation gate:

- identify the smallest relevant files
- run Ruff autofix and format
- run `uv run pyright --outputjson`
- run `uv run pytest -q`
- report files changed, verification commands, and remaining risks

Repo-wide Pyright is the desired hard gate. If full Pyright is temporarily
blocked by known pre-existing debt, the Python-change closeout must classify
changed-file/new diagnostics separately from baseline diagnostics and must not
call Pyright green. Once the baseline is zero, every full-Pyright failure is a
blocking bug for the current workflow.

## Reporting Contract

Every workflow closeout must separate:

- `verified here`
- `non-hardware verified`
- `pending hardware`

Also report:

- files changed
- docs synced and their sections
- surfaced conflicts or ambiguities
- exact hardware hand-off commands when board proof is still required
