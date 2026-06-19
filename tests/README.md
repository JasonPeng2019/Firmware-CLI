# Tests Tree

This tree is the canonical home for repo-owned validation assets.

Current layout:

- `tests/fixtures/`: shared static data and captured samples
- `tests/cases/`: tracked `R11` benchmark definitions, suite metadata, and the
  Codex result schema
- `tests/harness/`: harness code and reusable test helpers

Tracked harnesses:

- `tests/harness/stage1_smoke.py`: the current canonical Stage 1 smoke-harness
  entrypoint over the shared SWD and UART services
- `tests/harness/r11_benchmark.py`: the `R11` benchmark runner over the current
  MCP server and scripted `codex exec`

Tracked benchmark metadata:

- `tests/cases/suites.yaml`: named benchmark suites and frozen execution order
- `tests/cases/r11_result_schema.json`: structured Codex result schema
- `tests/cases/<case_id>/case.yaml`: machine-readable case contract
- `tests/cases/<case_id>/prompt.md`: exact Codex prompt template for the case

Keep bug-variant source trees under `firmware/<board>/bugs/`. Keep harness and
test definitions under `tests/`.
