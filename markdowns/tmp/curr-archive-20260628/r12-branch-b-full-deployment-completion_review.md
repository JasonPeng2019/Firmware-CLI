> STATUS: CLEAN REVIEW for the agent-verifiable surface and attached-board hardware proof.

# R12 Branch B Full Deployment Completion Review

## Verdict

CLEAN.

The implementation matches the spec scope: it exposes public session-scoped
client-action registration, threads it through the app and turnkey loop, shows
registered actions to the provider, records audit metadata, and proves the path
with real Codex, real MCP, real workspace edits/builds, and real attached
hardware.

## Findings

| severity | gate | file | finding | resolution |
|---|---|---|---|---|
| none | spec conformance | n/a | No must-fix findings. | n/a |

## Evidence

Non-hardware suite:

- `uv run pytest -q`: 284 passed.
- `uv run ruff check .`: passed.
- `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`: passed.
- `uv run pytest -q tests/test_r11_benchmark.py`: 34 passed.
- `uv run python -m tests.harness.r11_benchmark --help`: passed.
- Targeted Branch B/P0 tests: passed.

Hardware and deployment:

- `nucleo_l476rg`:
  - `host_bootstrap.py --board-id nucleo_l476rg --install-packs`: passed.
  - Stage 0 with reference firmware and shared USB confirmation: passed.
  - Stage 1 smoke: passed.
  - focused real Codex/MCP/client-action run:
    `20260628T210308Z-8b42e2ce`.
  - full customer-like real Codex workspace edit/build plus board run:
    `20260628T211451Z-f2bc0136`.
- `nrf52840dk`:
  - `host_bootstrap.py --board-id nrf52840dk`: passed.
  - Stage 0 silicon identity, flash, UART, recover, and post-recover read:
    passed.
  - Stage 1 smoke: first immediate post-recover run hit a transient pyOCD
    transfer fault; direct retry passed.
  - focused real Codex/MCP/client-action run:
    `20260628T210353Z-79827461`.
  - full customer-like real Codex workspace edit/build plus board run:
    `20260628T211628Z-3d17f3d8`.

Artifact checks:

- `client_actions.json` exists for the focused and full deployment runs and
  records `uart_write` as executed with SHA-256
  `d1cdee58c07b47cadb3d91af03ab9c4b242c7adb18962f3c0b534e3a300fa661`.
- Full customer-like runs recorded five model turns each.
- Full customer-like results include `read_file`, `replace_file`, `run_build`,
  `connect`, `wait`, `run_script:uart_write`, and `read_serial`.
- `mcp_tools_used` includes `connect`, `write_serial`, and `read_serial`.
- `applied-patches/turnkey.diff` records the workspace edit in both full runs.

## Hardware Hand-Off Status

Attached-board proof is complete for `nucleo_l476rg + nrf52840dk`.

Exact official `nrf52833dk` proof remains pending because the connected Nordic
board in this session identified as `NRF52840_xxAA_REV2`.

When `nrf52833dk` is attached, rerun:

```powershell
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 5 --serial-read-seconds 3 --task "<run_script smoke>"
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --workspace-root <temp-workspace> --build-command "python app.py" --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 8 --serial-read-seconds 3 --task "<workspace edit/build + run_script smoke>"
```

## Verified

- The agent-verifiable suite is green.
- The real deployed Branch B path is green on the physically attached
  `nucleo_l476rg + nrf52840dk` pair.

## Pending Verification

- Exact `nrf52833dk` Branch B deployment proof.
- Fresh-machine Windows/macOS portability proof, which remains outside this
  Branch B completion pass.
