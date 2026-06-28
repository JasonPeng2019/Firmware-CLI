# R12 CLI Task Input Robustness Review

## Verdict

CLEAN.

The implementation matches the spec scope. The run CLIs now accept exactly one
task source from inline text, UTF-8 file, or stdin, and both public run commands
share the same helper. This fixes the Windows PowerShell prompt-transport issue
without changing provider, model, MCP, or board-control behavior.

## Findings

| severity | gate | file | finding | resolution |
|---|---|---|---|---|
| none | spec conformance | n/a | No must-fix findings. | n/a |

## Evidence

Targeted tests:

- `uv run pytest -q tests/test_p0_foundation.py tests/test_ux_cli.py`: 43 passed.

Full suite:

- `uv run pytest -q`: 289 passed.
- `uv run ruff check .`: passed.
- `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`: passed.
- `uv run pytest -q tests/test_r11_benchmark.py`: 34 passed.
- `uv run python -m tests.harness.r11_benchmark --help`: passed.
- Targeted Branch B/CLI tests: 45 passed.

Real deployment smoke:

- `nucleo_l476rg` task-file run root:
  `runs/20260628T211451Z-f2bc0136`.
- `nrf52840dk` task-file run root:
  `runs/20260628T211628Z-3d17f3d8`.

Both deployment prompts included JSON-like quoted text and arrived intact in
`logs/prompt.txt`. Both runs registered and executed `uart_write` through
`--client-action`, edited a temporary workspace file, ran `python app.py`, used
an ordered action batch with `wait`, and verified UART `boot ok`.

## Hardware Hand-Off Status

Attached-board proof is complete for `nucleo_l476rg + nrf52840dk`.

Exact official `nrf52833dk` proof remains pending because the connected Nordic
board in this session identified as `NRF52840_xxAA_REV2`.

## Verified

- CLI task ingestion is covered by unit tests and full suite checks.
- Real `--task-file` deployment runs passed on the attached boards.

## Pending Verification

- Exact `nrf52833dk` task-file smoke when that board is attached.
