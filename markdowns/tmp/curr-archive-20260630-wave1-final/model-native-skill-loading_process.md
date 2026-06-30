# Process ledger for model-native-skill-loading

## Goal and roadmap anchor

Task: Remove brain-governed host actions and add model-native skill loading.
Roadmap anchor: `R12` turnkey brain prototype, Branch B action-boundary
correction plus Module G-style model-native context expansion.

Spec hard bar: `markdowns/curr/model-native-skill-loading_spec.md`.

## Done

- Created the active hard-bar spec for complete removal of governed host actions
  and addition of model-native `load_skills`.
- Synced active roadmap/build/progress docs before code changes.
- Removed `ReadFileAction`, `ReplaceFileAction`, `RunBuildAction`, the old
  model-native host action policy class, stale-action refusal path, and
  governed executor branches.
- Added `LoadSkillsAction`, batch conversion for `load_skills`, and prompt
  language that keeps host file/edit/build work provider-native.
- Added `brain/model_native_skills.py` with folder manifest loading,
  dependency closure, cycle detection, dependency-first init order, repeat-load
  no-op behavior, context rendering, and per-skill provider-runtime exposure.
- Added explicit manifests for the repo-local `.codex/skills/*` workflow skills.
- Added model-native skill session state to turnkey state artifacts.
- Added focused tests and a Codex CLI no-hardware smoke task.
- Follow-up adversarial audit fixed two valid loader hardening gaps:
  init scripts now preflight-reject direct probe/serial imports and known
  board/probe subprocess commands before execution, and manifest `skill_id`
  must match the requested skill folder.

## In progress

- None.

## TODO

- Claude CLI morning rerun after quota reset.

## Limitations and known gaps

- Claude CLI is out of usage during this pass, so Claude live-provider proof
  must be handed off with exact commands and expected evidence.
- This feature is primarily schema/loop/context behavior. No live hardware
  command was run for this pass; the Codex smoke intentionally avoided board
  connection and verified no MCP tools were used.

## Hardware hand-off

- No hardware command ran for this specific process.
- Morning Claude handoff must cover at least one Claude CLI model-native
  host-work/code-writing path plus `load_skills` context-expansion prompt proof
  on the attached board pair.

## Open decisions and surfaced issues

- The existing `.codex/skills/*/SKILL.md` files are folder-based but did not all
  have separate manifests. This process added explicit manifests for the
  repo-local workflow skills and kept the existing Codex skill markdown intact.
- Post-validation process audit showed two long-lived `pyocd-debug-mcp` process
  trees parented to Codex app-server processes, not to the validation/smoke
  command. They were treated as app-owned and not killed.

## Verified

- Focused tests passed:
  `uv run pytest -q tests/test_p0_foundation.py::test_action_policy_classifies_branch_b_boundaries tests/test_p0_foundation.py::test_turn_decision_schema_excludes_model_native_host_actions tests/test_p0_foundation.py::test_turn_decision_rejects_removed_host_action_variants tests/test_p0_foundation.py::test_turn_decision_accepts_load_skills_action tests/test_model_native_skills.py tests/test_r12_turnkey.py::test_run_turnkey_treats_removed_host_action_batch_as_unsupported tests/test_r12_turnkey.py::test_run_turnkey_load_skills_injects_context_on_next_turn tests/test_r12_turnkey_merge.py::test_removed_host_action_executors_are_absent`
  -> `9 passed`.
- Python-change gate passed:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`
  -> Ruff check/fix passed, Ruff format passed, full Pyright passed with `0`
  diagnostics across `107` analyzed files, full pytest `347 passed`.
- Codex CLI no-hardware smoke passed:
  `uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 3 --serial-read-seconds 1 --task-file markdowns/curr/model-native-skill-loading-codex-smoke-task.txt`
  -> `[DIAGNOSED_ONLY]`, `session_id=(none)`, run root
  `runs/turnkey-20260630T084055Z-0a0377bc`.
- The Codex smoke artifact shows `mcp_tools_used=[]`, `actions_taken` contains
  only `load_skills:firmcli-fix-bug`, and loaded skill state resolved
  `firmcli-workflow-core`, `python-change`, then `firmcli-fix-bug`.
- Post-audit verification passed:
  `uv run pytest -q tests/test_model_native_skills.py` -> `5 passed`;
  Python-change gate -> Ruff/format/Pyright `0`/pytest `350 passed`; suite
  preset -> pass; Codex `load_skills` smoke ->
  `runs/turnkey-20260630T090914Z-044ef516`.

## Pending verification

- Claude CLI morning rerun after quota reset.
- Optional live hardware reproof if the team wants to re-run the broader Branch
  B board path after this schema/context change.
