# Process ledger for compact-tool-schema-index

## Goal and roadmap anchor

Task: Compact turnkey MCP tool prompt injections to a small schema index
Roadmap anchor: R12 / Stage 5 Wave 1 Branch A and Branch B prompt boundary.

## Done

- 2026-06-30: Loaded `firmcli-write-process`, `firmcli-test-suite`,
  `firmcli-fix-bug`, `firmcli-workflow-core`, and `python-change`.
- 2026-06-30: Re-read authority docs and localized the current full-schema
  renderer to `src/pyocd_debug_mcp/brain/tool_schemas.py`.
- 2026-06-30: Created the hard-bar spec at
  `markdowns/curr/compact-tool-schema-index_spec.md`.
- 2026-06-30: Replaced full JSON input-schema prompt rendering with a compact
  curated MCP tool index: short description, required/optional arg hints, and
  response/refusal semantics.
- 2026-06-30: Added focused regression checks in
  `tests/test_r12_turnkey.py::test_tool_schema_bundle_filters_and_orders_curated_tools`.
- 2026-06-30: Synced `README.md`, build plan, R12 split/spec docs,
  `things-to-change.md`, `current-progress.md`, `repo_file_index.md`, and this
  current-doc index/handoff set.
- 2026-06-30: Focused pytest passed:
  `uv run pytest -q tests/test_r12_turnkey.py::test_tool_schema_bundle_filters_and_orders_curated_tools tests/test_p0_foundation.py::test_turn_decision_schema_excludes_model_native_host_actions tests/test_model_native_skills.py`
  -> `4 passed`.
- 2026-06-30: Full Python-change gate passed: Ruff check/fix, Ruff format,
  Pyright `0` diagnostics across `111` files, full pytest `347 passed`.
- 2026-06-30: Codex no-hardware public-entrypoint smoke passed:
  `uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 2 --serial-read-seconds 1 --task-file markdowns/curr/compact-tool-schema-index-codex-smoke-task.txt`
  -> `[DIAGNOSED_ONLY]`, run root
  `runs/turnkey-20260630T085305Z-63e99e37`, no session IDs, no MCP tool calls.
  Artifact inspection showed compact index present, `input_schema:` absent from
  `logs/prompt.txt`, `tool_schema_length=3663`, and `entry_count=13`.
- 2026-06-30: Suite preset passed:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> full pytest `347 passed`, Ruff pass, mypy pass, R11 benchmark tests
  `34 passed`, R11 harness help pass.

## In progress

- Final closeout and handoff.

## TODO

- Rerun Claude CLI compact-index smoke after quota reset.
- Rerun live hardware/product-suite proof for the official pair when
  `nrf52833dk + nucleo_l476rg` are attached and Claude/provider quota is
  available.

## Limitations and known gaps

- Claude CLI validation is expected to be blocked by provider quota in this
  session; do not claim Claude green without a fresh run.
- Live hardware proof depends on attached boards and should be reported only
  from commands run in this session.

## Hardware hand-off

- After quota reset and with both boards attached, rerun the R12 turnkey smoke
  and product suite rows listed in `next-codex-handoff-20260630.md`.

## Open decisions and surfaced issues

- No settled-decision conflict found. The build plan already calls for cheap
  static context; this pass narrows the prompt representation of already
  curated MCP metadata.

## Verified

- Compact tool-index rendering is covered by focused pytest.
- Full Python-change gate is green.
- Broad non-hardware suite preset is green.
- Codex CLI no-hardware smoke through the public turnkey entrypoint is green
  and inspected in run artifacts.
- Process audit after validation found the same app-owned Codex/MCP process
  trees that existed before validation; no new pytest/pyright/mypy children
  remained.

## Pending verification

- Claude provider smoke after quota reset.
- Live official-pair hardware proof.
