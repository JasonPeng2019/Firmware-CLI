# Review for Branch A/B Additive Merge

Task: Review merge of `origin/P-Wave-B` into `P-Wave-A` preserving Branch A
provider resume and Branch B action/task additions.

## Verdict

CLEAN for the agent-verifiable, non-hardware merge surface.

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |
| none | spec conformance | n/a | No blocking findings after targeted and suite validation. | n/a |

## Review notes

- Branch A remains the provider/session spine: provider prompt bundles,
  provider session state, real-session resume failure records, fail-closed
  headless behavior, and explicit recovery labeling are preserved.
- Branch B additions are integrated as additive behavior: task-file/task-stdin
  ingestion, repeatable `--client-action`, ordered action batches, bounded
  `wait`, UART `write_serial`, and gated `run_script` client actions.
- B tests were ported to A's provider interface by inspecting
  `ProviderPromptBundle.turn_context_text`; the older
  `next_decision(instructions, turn_prompt)` provider shape was not restored.
- Active docs no longer claim Branch B is unimplemented on this merged branch.
  The official `nrf52833dk` Branch B proof gap remains documented as pending.

## Validation

- `uv run pytest -q tests/test_r12_turnkey.py tests/test_ux_cli.py tests/test_server_runtime_tools.py tests/test_uart_capture.py tests/test_p0_foundation.py`
  - PASS: 134 tests.
- `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
  - PASS: `uv run pytest -q` with 319 tests.
  - PASS: `uv run ruff check .`.
  - PASS: `uv run mypy src`.
- `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
  - PASS: `uv run pytest -q` with 319 tests.
  - PASS: `uv run ruff check .`.
  - PASS: `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`.
  - PASS: `uv run pytest -q tests/test_r11_benchmark.py` with 34 tests.
  - PASS: `uv run python -m tests.harness.r11_benchmark --help`.

## Hardware hand-off status

Pending. No new board/live-provider proof was run in this merge review.

Suggested follow-up proof, when the official pair is attached:

```bash
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
```

## What's genuinely good

- The merged action layer is covered by direct loop tests, app/CLI threading
  tests, UX task-file tests, server UART write tests, and the full default/suite
  ladders.
- Provider resume strictness did not regress under the full `test_r12_turnkey`
  suite.
