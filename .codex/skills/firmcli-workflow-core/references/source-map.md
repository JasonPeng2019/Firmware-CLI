# Source Map

This Codex skill suite is the self-contained workflow surface for Firmware-CLI.
Historical slash-command files may exist in the repository, but Codex skills
must not require reading them. If a legacy command contains an important rule,
copy that rule into the relevant Codex `SKILL.md`.

| Workflow phase | Codex skill | Canonical repo inputs |
| --- | --- | --- |
| Spec | `firmcli-specs` | `superpowers/agent_consistency_playbook.md`, `superpowers/spec_build_review_loop_playbook.md`, `markdowns/ROADMAP.md`, `markdowns/current-progress.md`, touched files |
| Build | `firmcli-build` | `superpowers/agent_coding_playbook.md`, `superpowers/agent_doc_sync_playbook.md`, `superpowers/agent_portability_playbook.md`, spec/review files, touched files |
| Review | `firmcli-review` | spec, changed code/docs, all relevant `superpowers` playbooks, build plan |
| Spec loop | `firmcli-spec-loop` | `firmcli-specs`, `firmcli-build`, `firmcli-review`, and `firmcli-fix-bug` as needed |
| Fix bug | `firmcli-fix-bug` | repro evidence, authority docs, implicated files, optional focused spec |
| Test suite | `firmcli-test-suite` | build plan, `README.md`, `markdowns/ROADMAP.md`, `markdowns/current-progress.md`, concrete suite checks |
| Write process | `firmcli-write-process` | `firmcli-spec-loop`, `firmcli-fix-bug`, `firmcli-test-suite`, and a live process ledger |

Shared helper scripts:

- `scripts/scaffold_workflow_doc.py` creates spec, review, and process ledgers
  with the repo's expected headings.
- `scripts/run_check_ladder.py` runs the non-hardware validation ladder and
  records real output.
- `scripts/self_test_skills.py` validates the local Codex skill suite and its
  required repo authority files.

When a workflow rule changes, update the relevant Codex `SKILL.md` directly and
rerun:

```powershell
python .codex/skills/firmcli-workflow-core/scripts/self_test_skills.py --skip-quick-validate
```
