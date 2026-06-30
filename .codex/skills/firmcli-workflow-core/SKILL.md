---
name: firmcli-workflow-core
description: Load the Firmware-CLI repo's authority order, repo-specific safety rules, and helper scripts for the Claude-style workflow. Use when Codex needs to work under the `superpowers` playbooks, scaffold spec/review/process artifacts, run the non-hardware validation ladder, or self-test the local `.codex` skill suite.
---

# FirmCLI Workflow Core

Read this skill before using the other `firmcli-*` workflow skills or when you need the repo's shared operating rules.

Resolve the project repo root before reading or running anything. Use the directory that contains both `.claude/commands` and `superpowers`. In this workspace, if the skills are mirrored into the outer `FirmCLI` folder, the project root is usually `FirmCLI/Firmware-CLI`.

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
   - `superpowers/spec_build_review_loop_playbook.md` when mirroring the Claude workflow
5. The current state of every file you will touch or depend on, in full

Respect the repo's authority order:

- The build plan wins over everything else.
- The coding playbook is binding under the build plan.
- The committed `main` state is reality, but it is subordinate to the plan.
- Other docs, branches, and notes are proposals until reconciled.

Surface conflicts instead of silently resolving them. Never claim a hardware result that was not produced by a real board in the current session.

## Shared Helpers

Use these scripts from the folder that contains this mirrored `.codex` tree. They auto-resolve the real Firmware-CLI repo root:

- `.codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py`
  - Create `markdowns/curr/slug_spec.md`, `slug_review.md`, or `slug_process.md` with repo-aligned section templates.
- `.codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py`
  - Run the non-hardware validation ladder and capture real command output.
- `.codex/skills/firmcli-workflow-core/scripts/self_test_skills.py`
  - Validate the local skill suite, required source files, and skill metadata.

Read [references/source-map.md](references/source-map.md) when you need the mapping from the original Claude commands to the Codex skills.

## Python Code Changes

For any Python code change under this repo, use
`.codex/skills/python-change/SKILL.md` in addition to this core skill. That
skill owns the Python-specific edit discipline and validation gate:

- identify the smallest relevant files
- run Ruff autofix and format
- run `uv run pyright --outputjson`
- run `uv run pytest -q`
- report files changed, verification commands, and remaining risks

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
