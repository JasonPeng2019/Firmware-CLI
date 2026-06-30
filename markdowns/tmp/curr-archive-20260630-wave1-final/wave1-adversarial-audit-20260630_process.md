# Process ledger for wave1-adversarial-audit-20260630

## Goal and roadmap anchor

Task: Adversarial audit and validation pass for Wave 1 A/B/C plus Branch B
model-native skills and compact tool index.
Roadmap anchor: R12 Wave 1 A/B/C.

## Done

- Read the active write-process, fix-bug, spec-loop, test-suite, and workflow
  core instructions.
- Reconciled current code against:
  - `markdowns/curr/model-native-skill-loading_spec.md`;
  - `markdowns/curr/compact-tool-schema-index_spec.md`;
  - `markdowns/current-progress.md`;
  - `markdowns/things-to-change.md`;
  - `markdowns/R12_P_SPLIT.md`;
  - `markdowns/curr/r12_turnkey_spec.md`.
- Found and reproduced one valid Branch B product-boundary bug:
  model-native skill init scripts were not preflight-rejected when they directly
  imported probe/serial modules or invoked direct probe commands.
- Found and reproduced one valid namespace bug:
  a skill manifest could declare a `skill_id` different from its requested
  folder.
- Added focused failing tests in `tests/test_model_native_skills.py`:
  - manifest ID must match folder/request;
  - direct hardware/probe imports are rejected before init execution;
  - direct hardware/probe subprocess commands are rejected before init
    execution.
- Verified the reproducer failed before the fix:
  `uv run pytest -q tests/test_model_native_skills.py` -> `3 failed, 2 passed`.
- Implemented the fix in `model_native_skills.py`:
  - manifest ID consistency check;
  - Python AST preflight for forbidden hardware/probe imports;
  - subprocess-call preflight for forbidden hardware/probe commands;
  - UTF-8 validation for init scripts before execution.
- Updated `things-to-change.md` entry #11/#12 to match the corrected Branch B
  hard bar.
- Reran the focused regression:
  `uv run pytest -q tests/test_model_native_skills.py` -> `5 passed`.
- Reran the full Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py` ->
  Ruff check/fix passed, Ruff format passed, Pyright `0` diagnostics across
  `111` files, full pytest `350 passed`.
- Reran the suite preset:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> full pytest `350 passed`, Ruff passed, mypy passed across `69` source
  files, R11 benchmark tests `34 passed`, R11 harness help passed.
- Ran a Codex host-native workspace smoke with a disposable workspace:
  - command: `uv run pyocd-debug-brain run --provider codex-cli --board-id
    nucleo_l476rg --max-iters 1 --serial-read-seconds 1 --workspace-root
    <temp> --build-command "python --version" --task <host edit prompt>`;
  - run root: `runs/turnkey-20260630T090753Z-02dee333`;
  - result: `[DIAGNOSED_ONLY]`;
  - artifact file content: `codex host native smoke ok`;
  - `actions_taken=[]`, `mcp_tools_used=[]`;
  - event log contains `model_native_host_work_observed` with
    `changed_files=["host_native_probe.txt"]`.
- Reran the Codex `load_skills` no-hardware smoke:
  - command: `uv run pyocd-debug-brain run --provider codex-cli --board-id
    nucleo_l476rg --max-iters 3 --serial-read-seconds 1 --task-file
    markdowns/curr/model-native-skill-loading-codex-smoke-task.txt`;
  - run root: `runs/turnkey-20260630T090914Z-044ef516`;
  - result: `[DIAGNOSED_ONLY]`;
  - loaded closure:
    `firmcli-workflow-core -> python-change -> firmcli-fix-bug`;
  - `mcp_tools_used=[]`.
- Reran the Codex compact tool-index no-hardware smoke:
  - command: `uv run pyocd-debug-brain run --provider codex-cli --board-id
    nucleo_l476rg --max-iters 2 --serial-read-seconds 1 --task-file
    markdowns/curr/compact-tool-schema-index-codex-smoke-task.txt`;
  - run root: `runs/turnkey-20260630T090947Z-703de0e5`;
  - result: `[DIAGNOSED_ONLY]`;
  - prompt contains `Curated MCP tool index (compact`;
  - `rg "input_schema:" runs/.../logs/prompt.txt` found no matches;
  - `mcp_tools_used=[]`.
- Repeated the adversarial audit after fixes:
  - no removed action models/executor branches/refusal paths were reintroduced;
  - compact tool-index prompt stayed compact;
  - remaining `run_build` mentions in `things-to-change.md` were either hard-bar
    removal statements or inert-host-work examples after the doc patch;
  - remaining blockers are Claude quota and exact-board proof only.
- Audited leftover processes after validation. No pytest/Pyright validation
  children remained. Existing `pyocd-debug-mcp` processes were launched as
  `uv run pyocd-debug-mcp` under Codex app-server/plugin parent processes, so
  they were treated as app-owned and left running.

## In progress

- None.

## TODO

- None for the agent-verifiable audit scope.

## Limitations and known gaps

- Claude CLI cannot be tested in this session because the user reported quota is
  exhausted. Do not infer Claude success from Codex results.
- Exact official `nrf52833dk` proof is still pending if that specific hardware
  is required; the existing attached Nordic proof is for `nrf52840dk`.
- The turnkey brain still does not sandbox the provider's own host tools. That
  is the accepted product stance; this pass only governs brain-mediated skill
  initialization.

## Hardware hand-off

- Morning rerun should start with the no-hardware Claude `load_skills` and
  compact tool-index smokes from `next-codex-handoff-20260630.md`.
- Then rerun Claude live code-writing benchmark on STM32 and the selected Nordic
  board.
- If the exact official board is required, attach `nrf52833dk` and rerun the
  official Nordic proof rather than treating `nrf52840dk` as equivalent.

## Open decisions and surfaced issues

- Whether to broaden the init-script preflight denylist later is a product
  policy decision. The current list covers the obvious sanctioned-boundary
  bypasses without blocking normal pure-host setup scripts.
- `respond_to_user` / `done` richer terminal decisions remain later product
  work; current prototype terminal closure still uses `finalize`.

## Verified

- `uv run pytest -q tests/test_model_native_skills.py` -> `5 passed`.
- `python .codex\skills\python-change\scripts\run_python_change_checks.py` ->
  pass; Pyright `0`; pytest `350 passed`.
- `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> pass.
- Codex host-native smoke -> pass at
  `runs/turnkey-20260630T090753Z-02dee333`.
- Codex `load_skills` smoke -> pass at
  `runs/turnkey-20260630T090914Z-044ef516`.
- Codex compact tool-index smoke -> pass at
  `runs/turnkey-20260630T090947Z-703de0e5`.

## Pending verification

- Claude quota-reset reruns.
- Exact official-board proof.
