> STATUS: COMPLETE PROCESS - implementation and available verification for `r12-branch-b-full-deployment-completion_spec.md`.

# R12 Branch B Full Deployment Completion Process

## Goal and roadmap anchor

Implement `R12` prototype Wave 1 Branch B deployment completion from
`markdowns/curr/r12-branch-b-full-deployment-completion_spec.md`.

Roadmap anchor: `R12` prototype Wave 1 / Branch B.

## Done

- Spec phase complete:
  `markdowns/curr/r12-branch-b-full-deployment-completion_spec.md` exists and
  defines the missing customer-facing `run_script` deployment path.
- Build pass complete:
  - added public `pyocd-debug-brain run --client-action NAME=PATH`;
  - loaded registered action files into the per-run `ClientActionStore`;
  - rendered registered action metadata in the provider prompt;
  - persisted client-action audit metadata in run artifacts;
  - added tests for the public CLI/app path;
  - added `tests/fixtures/client_actions/uart_write.py` as the real deployment
    smoke action.
- Test-suite pass complete:
  - `uv run pytest -q`: 284 passed;
  - `uv run ruff check .`: passed;
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`: passed;
  - `uv run pytest -q tests/test_r11_benchmark.py`: 34 passed;
  - `uv run python -m tests.harness.r11_benchmark --help`: passed;
  - targeted Branch B/P0 tests: passed.
- Real hardware and deployment proof complete for the attached pair:
  - `nucleo_l476rg` Stage 0 and Stage 1 passed;
  - attached Nordic identified as `nrf52840dk`; Stage 0 and Stage 1 passed after
    one transient post-recover attach retry;
  - real Codex + real MCP + public `--client-action` smoke passed on both;
  - full customer-like Codex workspace edit/build plus governed Branch B batch
    passed on both.

## TODO

None for the attached-board Branch B completion pass.

## Limitations and known gaps

- Provider persistent sessions remain Branch A scope and are not required for
  this pass.
- Exact `nrf52833dk` proof depends on matching hardware being attached. If the
  connected Nordic board still reports as `nrf52840dk`, exact `nrf52833dk`
  proof remains pending.

## Hardware hand-off

Exact official Nordic proof remains pending until an `nrf52833dk` is attached.
The attached Nordic board for this pass identified as `nrf52840dk`.

Commands already run successfully on the attached pair:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 5 --serial-read-seconds 2 --task "<run_script smoke>"
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52840dk --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 5 --serial-read-seconds 3 --task "<run_script smoke>"
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --workspace-root <temp-workspace> --build-command "python app.py" --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 8 --serial-read-seconds 2 --task "<workspace edit/build + run_script smoke>"
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52840dk --workspace-root <temp-workspace> --build-command "python app.py" --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 8 --serial-read-seconds 3 --task "<workspace edit/build + run_script smoke>"
```

Run roots:

- `20260628T210308Z-8b42e2ce` - focused STM32 run-script smoke
- `20260628T210353Z-79827461` - focused Nordic run-script smoke
- `20260628T211451Z-f2bc0136` - full STM32 coding/build/board smoke via `--task-file`
- `20260628T211628Z-3d17f3d8` - full Nordic coding/build/board smoke via `--task-file`

## Open decisions and surfaced issues

- No build-plan conflict surfaced.
- The attached Nordic hardware is `nrf52840dk`; exact official `nrf52833dk`
  proof is still pending.
- One immediate `nrf52840dk` Stage 1 run after recover failed with a pyOCD
  `TransferFaultError`; a direct retry passed. No product code change was made
  for that transient.

## Verified

- Public Branch B registration, prompt visibility, artifact audit, real Codex,
  real MCP, real coding/build, and real hardware proof are complete for the
  attached `nucleo_l476rg + nrf52840dk` pair.

## Pending verification

- Exact `nrf52833dk` proof remains pending until that board is physically
  attached.
- Fresh-machine portability proof remains outside this Branch B completion pass.
