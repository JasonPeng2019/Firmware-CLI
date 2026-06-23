# Tests Tree

This tree is the canonical home for repo-owned validation assets.

Current layout:

- `tests/fixtures/`: shared static data and captured samples
- `tests/cases/`: tracked benchmark definitions, suite metadata, and the
  `R11` structured result schema reused by the current benchmark layer
- `tests/harness/`: harness code and reusable test helpers

Tracked harnesses:

- `tests/harness/stage1_smoke.py`: the current canonical Stage 1 smoke-harness
  entrypoint over the shared SWD and UART services
- `tests/harness/r11_benchmark.py`: the `R11` benchmark runner over the current
  MCP server and scripted `codex exec`
- `tests/harness/r12_turnkey_benchmark.py`: the `R12` turnkey benchmark
  entrypoint over `pyocd-debug-brain`

Tracked benchmark metadata:

- `tests/cases/suites.yaml`: named benchmark suites and frozen execution order
- `tests/cases/r11_result_schema.json`: structured Codex result schema
- `tests/cases/<case_id>/case.yaml`: machine-readable case contract
- `tests/cases/<case_id>/prompt.md`: exact Codex prompt template for the case

Current benchmark split:

- `R11`: BYO-agent benchmark path through Codex CLI
- `R12`: turnkey benchmark path through the repo-owned native Python brain,
  with selectable decision backends:
  - `openai-api`
  - `anthropic-api`
  - `codex-cli`
  - `claude-cli`

Both paths currently reuse the same 12-case corpus:

- `pilot_v1_plus_b003_b004`

Current UX-layer relationship:

- `pyocd-debug-brain`
  - stable headless/automation CLI
  - benchmark path used by `tests/harness/r12_turnkey_benchmark.py`
- `pyocd-debug`
  - operator-facing CLI over the same turnkey brain
  - pretty/live rendering, history/show/rerun flows, and raw-output controls
  - does not replace the harnesses or change the benchmark corpus/schema

Current live status:

- the `R11` BYO-agent path is live-proven on the scoped pair
- the `R12` turnkey path is live-proven through the full 12-case suite with
  `codex-cli`
- the `R12` second-provider closure check is still open because the current
  `claude-cli --model sonnet` path fails before any board action on this host
- the Pass 1 `pyocd-debug` shell is implemented in code and covered by the
  local non-hardware test/lint/typecheck ladder; provider-token streaming is
  still the next UX follow-up

Keep bug-variant source trees under `firmware/<board>/bugs/`. Keep harness and
test definitions under `tests/`.
