# Next Codex Handoff - 2026-06-30

## Purpose

This is the current handoff after the Branch B follow-up hard bar:

- old governed host actions are removed structurally
- `load_skills` is implemented as model-native context expansion
- focused tests, full Python-change gate, and a no-hardware Codex CLI smoke are
  green
- the governed MCP tool prompt injection is now a compact tool index instead of
  repeated full JSON schema bodies
- a repeated adversarial audit found and fixed two valid Branch B loader gaps:
  init scripts now preflight-reject direct probe/serial bypasses, and skill
  manifests must match their requested folder skill IDs
- a Codex host-native workspace smoke proved the desired provider flow: Codex
  freely edited a host file, the brain observed the workspace diff at the
  governed boundary, and the turn closed with `finalize` without MCP/server
  tools
- Claude CLI proof is still blocked by quota and must be rerun after reset
- exact official `nrf52833dk` proof remains pending because the attached Nordic
  board in this session is `nrf52840dk`

Do not declare full product-suite closure until the remaining Claude/provider
and desired live-board proof is rerun green.

## Read These First

- `markdowns/curr/README.md`
- `markdowns/curr/next-codex-handoff-20260630.md`
- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/current-progress.md`
- `markdowns/curr/r12_turnkey_spec.md`
- `markdowns/curr/model-native-skill-loading-codex-smoke-task.txt`
- `markdowns/curr/compact-tool-schema-index-codex-smoke-task.txt`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/action_policy.py`
- `src/pyocd_debug_mcp/brain/model_native_skills.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/tool_schemas.py`
- `tests/test_model_native_skills.py`
- `tests/test_p0_foundation.py`
- `tests/test_r12_turnkey.py`

Older Branch B docs remain useful historical context:

- `markdowns/tmp/curr-archive-20260630-wave1-final/`
- `markdowns/tmp/curr-archive-20260630-hardbar-reset/`

## Current Repo State

Observed branch earlier in this session:

```text
P-Wave-0...origin/P-Wave-0 [ahead 1]
```

The worktree is intentionally dirty with prior Branch B changes plus this pass.
New/current files from this pass include:

- `src/pyocd_debug_mcp/brain/model_native_skills.py`
- `tests/test_model_native_skills.py`
- `markdowns/curr/model-native-skill-loading-codex-smoke-task.txt`
- `markdowns/curr/compact-tool-schema-index-codex-smoke-task.txt`
- `.codex/skills/*/skill.yaml` manifests for repo-local workflow skills

Completed process/spec/review ledgers from this pass were archived under
`markdowns/tmp/curr-archive-20260630-wave1-final/`. Do not move them back into
`curr/` unless they become active current-step truth again.

## Implemented

The old governed host actions are now structurally absent:

- deleted `ReadFileAction`, `ReplaceFileAction`, and `RunBuildAction`
- removed them from `ActionUnion`, schema variants, and `__all__`
- removed loop imports, batch conversion, executor branches, and the old
  `_raise_model_native_host_action_refusal`
- removed `MODEL_NATIVE_HOST_ACTIONS` / model-native-host action classification
- stale `read_file` in an `action_batch` now falls through to ordinary
  `brain/unsupported-batch-action`; it is not a known/refused model-native host
  action anymore
- prompt text tells the model to perform host file/edit/build work with
  provider-native host tools before returning a governed/terminal decision

`load_skills` is now implemented:

- action shape: `{"kind": "load_skills", "skill_ids": ["firmcli-fix-bug"]}`
- accepts one or more skill IDs
- resolves transitive dependencies with de-dupe
- detects cycles with the full cycle path
- runs init scripts dependency-first post-order
- rejects init scripts before execution if they directly import known
  probe/serial stacks or invoke known board/probe commands
- rejects manifests whose `skill_id` does not match the requested skill folder
- repeats are no-op for already-loaded skills
- exposes usable files under
  `runs/_provider-runtime/<run_id>/<provider>/skills/<skill_id>/`
- injects loaded markdown/context into the next provider prompt
- persists loaded skill state in `turnkey_state.json`

Compact governed MCP tool prompt injection is now implemented:

- `tool_schemas.py` still reads live MCP tool descriptions/input schemas and
  filters them to the curated `AllowedServerToolName` order
- the prompt-facing `rendered_text` is now a compact tool index, not pretty JSON
  schema bodies
- each live curated tool line includes a short description and an `args:` list
  with `!` for required arguments and `?` for optional arguments
- stable response/refusal semantics remain in the same prompt block
- full schema dicts are still retained in `ToolSchemaEntry` records for
  provenance and future use
- the prompt no longer contains `input_schema:` in the governed tool block

Adversarial audit result:

- valid finding fixed: model-native skill init scripts were bounded/recorded but
  not preflight-rejected for direct hardware/probe bypasses
- valid finding fixed: a manifest could declare a different `skill_id` than the
  requested folder
- valid doc finding fixed: `things-to-change.md` had older wording that still
  implied `run_build`/firmware edits were governed host decisions
- repeated audit after fixes found no remaining valid Codex-verifiable
  criticisms; remaining blockers are Claude quota and exact-board proof

Current repo skill dependency example:

```text
firmcli-fix-bug
  depends_on: firmcli-workflow-core, python-change
python-change
  depends_on: firmcli-workflow-core
```

Resolved order in the Codex smoke:

```text
firmcli-workflow-core -> python-change -> firmcli-fix-bug
```

## Validation Completed

Focused tests:

```powershell
uv run pytest -q tests/test_p0_foundation.py::test_action_policy_classifies_branch_b_boundaries tests/test_p0_foundation.py::test_turn_decision_schema_excludes_model_native_host_actions tests/test_p0_foundation.py::test_turn_decision_rejects_removed_host_action_variants tests/test_p0_foundation.py::test_turn_decision_accepts_load_skills_action tests/test_model_native_skills.py tests/test_r12_turnkey.py::test_run_turnkey_treats_removed_host_action_batch_as_unsupported tests/test_r12_turnkey.py::test_run_turnkey_load_skills_injects_context_on_next_turn tests/test_r12_turnkey_merge.py::test_removed_host_action_executors_are_absent
```

Result: `9 passed`.

Full Python-change gate:

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py
```

Result:

- Ruff check/fix passed
- Ruff format passed
- full Pyright passed with `0` diagnostics across `107` analyzed files
- full pytest passed with `347 passed`

Codex CLI no-hardware smoke:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 3 --serial-read-seconds 1 --task-file markdowns/curr/model-native-skill-loading-codex-smoke-task.txt
```

Result:

- `[DIAGNOSED_ONLY]`
- `session_id=(none)`
- run root: `runs/turnkey-20260630T084055Z-0a0377bc`
- `actions_taken=["load_skills:firmcli-fix-bug"]`
- `mcp_tools_used=[]`
- loaded skill closure: `firmcli-workflow-core`, `python-change`,
  `firmcli-fix-bug`
- second Codex turn observed the loaded skill context and finalized without
  board/server tool use

Compact tool-index focused and suite validation:

```powershell
uv run pytest -q tests/test_r12_turnkey.py::test_tool_schema_bundle_filters_and_orders_curated_tools tests/test_p0_foundation.py::test_turn_decision_schema_excludes_model_native_host_actions tests/test_model_native_skills.py
```

Result: `4 passed`.

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py
```

Result:

- Ruff check/fix passed
- Ruff format passed
- full Pyright passed with `0` diagnostics across `111` analyzed files
- full pytest passed with `347 passed`

```powershell
python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite
```

Result:

- full pytest `347 passed`
- Ruff check passed
- mypy passed across `69` source files
- R11 benchmark tests `34 passed`
- R11 harness help passed

Compact tool-index Codex CLI no-hardware smoke:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 2 --serial-read-seconds 1 --task-file markdowns/curr/compact-tool-schema-index-codex-smoke-task.txt
```

Result:

- `[DIAGNOSED_ONLY]`
- `session_id=(none)`
- run root: `runs/turnkey-20260630T085305Z-63e99e37`
- `actions_taken=[]`
- `mcp_tools_used=[]`
- `session_ids_seen=[]`
- `tool_schema_summary.entry_count=13`
- `prompt_bundle.tool_schema_length=3663`
- `runs/turnkey-20260630T085305Z-63e99e37/logs/prompt.txt` contains
  `Curated MCP tool index (compact`
- `runs/turnkey-20260630T085305Z-63e99e37/logs/prompt.txt` does not contain
  `input_schema:`

Post-adversarial-audit validation:

```powershell
uv run pytest -q tests/test_model_native_skills.py
```

Result: `5 passed`.

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py
```

Result:

- Ruff check/fix passed
- Ruff format passed
- full Pyright passed with `0` diagnostics across `111` analyzed files
- full pytest passed with `350 passed`

```powershell
python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite
```

Result:

- full pytest `350 passed`
- Ruff check passed
- mypy passed across `69` source files
- R11 benchmark tests `34 passed`
- R11 harness help passed

Codex host-native workspace smoke:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 1 --serial-read-seconds 1 --workspace-root <temp-host-native-smoke-workspace> --build-command "python --version" --task "<inspect and rewrite host_native_probe.txt, then finalize>"
```

Result:

- `[DIAGNOSED_ONLY]`
- run root: `runs/turnkey-20260630T090753Z-02dee333`
- temp file final content: `codex host native smoke ok`
- `actions_taken=[]`
- `mcp_tools_used=[]`
- `files_changed=["host_native_probe.txt"]`
- event log includes `model_native_host_work_observed`

Post-fix Codex CLI `load_skills` smoke:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 3 --serial-read-seconds 1 --task-file markdowns/curr/model-native-skill-loading-codex-smoke-task.txt
```

Result:

- `[DIAGNOSED_ONLY]`
- run root: `runs/turnkey-20260630T090914Z-044ef516`
- `actions_taken=["load_skills:firmcli-fix-bug"]`
- `mcp_tools_used=[]`
- loaded closure: `firmcli-workflow-core`, `python-change`,
  `firmcli-fix-bug`

Post-fix compact tool-index smoke:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 2 --serial-read-seconds 1 --task-file markdowns/curr/compact-tool-schema-index-codex-smoke-task.txt
```

Result:

- `[DIAGNOSED_ONLY]`
- run root: `runs/turnkey-20260630T090947Z-703de0e5`
- `mcp_tools_used=[]`
- prompt contains `Curated MCP tool index (compact`
- prompt contains no `input_schema:` marker

Process audit note:

- no pytest/pyright children remained after validation
- post-audit `pyocd-debug-mcp` process trees were parented to Codex app-server
  processes as `uv run pyocd-debug-mcp`, not to the completed validation/smoke
  commands; they were treated as app-owned/plugin-owned and not killed

## Prior Hardware/Provider Evidence

Before this follow-up pass, Branch B/Codex proof was green on attached boards:

- attached boards: `nucleo_l476rg` and `nrf52840dk`
- Codex CLI Branch C harness:
  - `nucleo_l476rg`: `20260630T080831Z-b996d530`
  - `nrf52840dk`: `20260630T081021Z-31f3aaae`
- Codex CLI `b001_wrong_boot_text` benchmark:
  - `nucleo_l476rg`: `20260630T081152Z-0ed30757`
  - `nrf52840dk`: `20260630T081747Z-32904e64`

Claude CLI final code-writing rerun did not complete because quota was
exhausted before any MCP session was created:

```text
runs/turnkey-20260630T082157Z-25e30a91
You're out of extra usage - resets 7:30am (America/New_York)
```

## Morning Claude Runbook

1. Audit processes before live commands:

```powershell
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -match 'pyocd-debug-brain|pyocd-debug-mcp|pyocd|codex|claude|uv|pytest|pyright'
} | Select-Object ProcessId,ParentProcessId,Name,CommandLine
```

2. Run a no-hardware Claude compact tool-index smoke first:

```powershell
uv run pyocd-debug-brain run --provider claude-cli --board-id nucleo_l476rg --max-iters 2 --serial-read-seconds 1 --task-file markdowns/curr/compact-tool-schema-index-codex-smoke-task.txt
```

Expected:

- finalizes `diagnosed_only`
- `session_id=(none)`
- `mcp_tools_used=[]`
- run artifact prompt has compact tool index and no `input_schema:` in the tool
  section

3. Run a no-hardware Claude `load_skills` smoke:

```powershell
uv run pyocd-debug-brain run --provider claude-cli --board-id nucleo_l476rg --max-iters 3 --serial-read-seconds 1 --task-file markdowns/curr/model-native-skill-loading-codex-smoke-task.txt
```

Expected:

- first turn returns `load_skills` for `firmcli-fix-bug`
- second turn finalizes `diagnosed_only`
- `session_id=(none)`
- `mcp_tools_used=[]`
- state contains loaded skill closure and per-skill runtime paths

4. Rerun Claude code-writing proof on STM32:

```powershell
uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__b001_wrong_boot_text --max-iters 8 --serial-read-seconds 1.0
```

5. If STM32 passes, rerun on the attached Nordic board:

```powershell
uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nrf52840dk__b001_wrong_boot_text --max-iters 8 --serial-read-seconds 1.0
```

6. If exact official-board closure is required, attach `nrf52833dk` and rerun
the corresponding official Nordic ladder instead of treating `nrf52840dk` as a
substitute.

7. After every failed live run that requires a code fix, use
`firmcli-fix-bug`, rerun the Python-change gate, and restart the affected live
suite from the beginning.

8. Audit processes again after every live run and clean up only processes tied
to the current run by parent PID, command line, run root, or another precise
provenance signal.

## Final Success Bar

Do not call the product suite fully green until:

- old governed host actions remain structurally absent
- `load_skills` context expansion remains green
- model-native skill init scripts still reject direct probe/serial bypasses and
  manifest ID spoofing
- Ruff, full Pyright, and full pytest stay green after any new edits
- Codex/Claude provider behavior remains host-native for file/build/source work:
  the provider may freely inspect/edit locally, and the brain only sees the
  turn-closing governed/context/terminal decision
- Claude CLI no-hardware `load_skills` smoke passes after quota reset
- Claude CLI code-writing proof passes at the selected hardware scope
- exact official `nrf52833dk` proof is either run or explicitly deferred by the
  team
- Wave 2 prototype-priority modules are still tracked as required work
