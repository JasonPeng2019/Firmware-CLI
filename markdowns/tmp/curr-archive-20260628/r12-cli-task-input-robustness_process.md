# R12 CLI Task Input Robustness Process

Status: COMPLETE PROCESS.

## Goal And Roadmap Anchor

Deliver the prompt-ingestion robustness fix for `R12` turnkey deployment runs.
This process exists because a real Windows PowerShell smoke exposed that complex
inline `--task` prompts can be split by the shell before the CLI receives them.

## Done

- Spec opened at `markdowns/curr/r12-cli-task-input-robustness_spec.md`.
- Root cause classified as shell argument transport, not model/brain behavior.
- Design chosen: add `--task-file` and `--task-stdin` alongside existing
  `--task`.
- Shared task-source helper implemented for `pyocd-debug-brain run` and
  `pyocd-debug run`.
- Unit coverage added for file/stdin parsing and task-file handoff.
- README guidance updated for long prompts.
- Targeted tests passed:
  `uv run pytest -q tests/test_p0_foundation.py tests/test_ux_cli.py`.
- Full suite ladder passed:
  - `uv run pytest -q`: 289 passed;
  - `uv run ruff check .`: passed;
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`: passed;
  - `uv run pytest -q tests/test_r11_benchmark.py`: 34 passed;
  - `uv run python -m tests.harness.r11_benchmark --help`: passed;
  - targeted Branch B/CLI tests: 45 passed.
- Real `--task-file` deployment smokes passed on both attached boards:
  - `nucleo_l476rg`: run root `20260628T211451Z-f2bc0136`;
  - `nrf52840dk`: run root `20260628T211628Z-3d17f3d8`.

## In Progress

None.

## TODO

None for the attached-board prompt-ingestion fix.

## Limitations / Known Gaps

- This does not make arbitrary shell quoting safe. It gives users a shell-safe
  alternative for complex prompts.
- This does not change provider-session behavior.

## Hardware Hand-Off

No hardware is required to prove the CLI parsing fix. Hardware smoke was still
run as an end-to-end deployment confidence check:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task-file <prompt-file> --client-action uart_write=tests/fixtures/client_actions/uart_write.py
```

Result: passed on `nucleo_l476rg` and on the attached Nordic `nrf52840dk`.
Exact official `nrf52833dk` task-file proof remains pending until that board is
physically attached.

## Open Decisions / Surfaced Issues

None.

## Verified / Pending verification

Verified:

- Spec created.
- Implementation and tests added.
- Targeted tests passed.
- Full suite passed.
- Real task-file deployment smoke passed on the attached
  `nucleo_l476rg + nrf52840dk` pair.

Pending verification:

- Exact `nrf52833dk` task-file smoke remains pending until that board is
  physically attached.
