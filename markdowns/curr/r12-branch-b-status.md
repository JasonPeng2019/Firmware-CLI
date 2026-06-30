# R12 Branch B Status

This is the current Branch B handoff. It replaces the overlapping Branch B
action-boundary, full-deployment-completion, and real-deployment report files
that were archived after their implementation/review loops completed.

## Current Status

Branch B is implemented and verified on the hardware available in the latest
Windows validation session:

- `nucleo_l476rg`
- `nrf52840dk`

The official scoped Nordic proof for `nrf52833dk` is still pending because the
attached Nordic board identified as `NRF52840_xxAA_REV2`.

## What Branch B Owns

Branch B owns the governed action boundary work for the `R12` prototype:

- model-native host work stays outside the MCP server;
- board/server-native work routes through the brain gate;
- ordered action batches execute in order and stop on failure/refusal;
- bounded brain-local `wait`;
- UART write through the server surface;
- session-scoped client actions registered by name and run through
  `run_script(name, inputs)`;
- public deployment registration with:

```powershell
uv run pyocd-debug-brain run --client-action NAME=PATH ...
```

## Implemented Surface

The current code supports:

- repeatable `pyocd-debug-brain run --client-action NAME=PATH`;
- deterministic client-action validation and loading;
- prompt rendering of registered action name, path, description, and SHA-256;
- per-run `ClientActionStore` threading through CLI -> app -> provider loop;
- `runs/<session_id>/run-metadata/client_actions.json` audit output;
- execution of script-owned server calls only through the gated server API.

This does not implement Branch A provider-session persistence, provider-native
tool-call conversion, dynamic model-authored action registration during an
already-running provider turn, or a general host execution MCP tool.

## Latest Verification

Non-hardware:

- `uv run pytest -q`: 284 passed.
- `uv run ruff check .`: passed.
- `uv run mypy src`: passed.
- Suite ladder also passed with R11 benchmark checks/help.
- Focused Branch B/P0 tests passed for loader validation, CLI/app threading,
  prompt visibility, `run_script`, and client-action audit metadata.

Real deployment on attached boards:

- focused Codex + MCP + public `--client-action` smoke:
  - `20260628T210308Z-8b42e2ce` on `nucleo_l476rg`;
  - `20260628T210353Z-79827461` on `nrf52840dk`.
- full customer-like Codex runs with multiple provider turns, workspace
  read/edit/build, and governed action batch:
  - `20260628T210541Z-8b5ecff9` on `nucleo_l476rg`;
  - `20260628T210710Z-b62737bb` on `nrf52840dk`.

The full customer-like runs recorded `read_file`, `replace_file`, `run_build`,
`connect`, `wait`, `run_script:uart_write`, and `read_serial` in the run
artifacts. `client_actions.json` recorded the executed `uart_write` action hash.

## Remaining Proof

Before claiming exact official scoped-pair closure for Branch B, rerun the same
deployment checks with `nrf52833dk` attached:

```powershell
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 5 --serial-read-seconds 3 --task "<run_script smoke>"
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --workspace-root <temp-workspace> --build-command "python app.py" --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 8 --serial-read-seconds 3 --task "<workspace edit/build + run_script smoke>"
```

Fresh-machine Windows/macOS portability proof remains outside Branch B's local
implementation proof and is tracked separately.

## Archived Source Docs

The detailed build-loop artifacts that produced this status were moved to:

```text
markdowns/tmp/curr-archive-20260628/
```

Relevant archived files include:

- `r12-branch-b-action-boundary_spec.md`
- `r12-branch-b-action-boundary_process.md`
- `r12-branch-b-action-boundary_review.md`
- `r12-branch-b-full-deployment-completion_spec.md`
- `r12-branch-b-full-deployment-completion_process.md`
- `r12-branch-b-full-deployment-completion_review.md`
- `r12-branch-b-multi-loop-real-deployment_test_report.md`

## Verified

- This file reflects the latest Branch B implementation and attached-board
  validation evidence from the current repo docs.

## Pending Verification

- Exact `nrf52833dk` Branch B deployment proof.
- Fresh-machine Windows/macOS portability proof.
