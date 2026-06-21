# Source Map

This skill suite mirrors the Claude command set under `.claude/commands/` and the repo rules under `superpowers/`.

| Claude command | Codex skill | Primary source files |
| --- | --- | --- |
| `/specs` | `firmcli-specs` | `.claude/commands/specs.md`, `superpowers/agent_consistency_playbook.md`, `superpowers/spec_build_review_loop_playbook.md` |
| `/build` | `firmcli-build` | `.claude/commands/build.md`, `superpowers/agent_coding_playbook.md`, `superpowers/agent_doc_sync_playbook.md` |
| `/review` | `firmcli-review` | `.claude/commands/review.md`, `superpowers/agent_script_doc_playbook.md`, `superpowers/agent_portability_playbook.md` |
| `/spec-loop` | `firmcli-spec-loop` | `.claude/commands/spec-loop.md`, `superpowers/spec_build_review_loop_playbook.md` |
| `/fix-bug` | `firmcli-fix-bug` | `.claude/commands/fix-bug.md`, `.claude/commands/build.md`, `.claude/commands/review.md` |
| `/test-suite` | `firmcli-test-suite` | `.claude/commands/test-suite.md`, `markdowns/current-progress.md` |
| `/write-process` | `firmcli-write-process` | `.claude/commands/write-process.md`, `.claude/commands/spec-loop.md` |

Shared helper scripts:

- `scripts/scaffold_workflow_doc.py` creates spec, review, and process ledgers with the repo's expected headings.
- `scripts/run_check_ladder.py` runs the non-hardware validation ladder and records the real output.
- `scripts/self_test_skills.py` validates the local skill suite and checks the mirrored source files still exist.

When the Claude command files or `superpowers` playbooks change, update the matching Codex skill and rerun `python .codex/skills/firmcli-workflow-core/scripts/self_test_skills.py`.
