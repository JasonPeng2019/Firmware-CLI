> STATUS: ACTIVE PROCESS - tracks implementation of `r12-branch-b-action-boundary_spec.md`.

# R12 Branch B Action Boundary Process

## Goal and roadmap anchor

Implement `R12` prototype Wave 1 Branch B from
`markdowns/curr/r12-branch-b-action-boundary_spec.md`.

Roadmap anchor: `R12` prototype Wave 1 / Branch B.

## Done

- Spec phase complete:
  `markdowns/curr/r12-branch-b-action-boundary_spec.md` exists and reconciles
  Branch B against the build plan, current code, Branch B clarification docs,
  and MCP architecture.
- Build pass 1 complete:
  - added action-boundary classification in
    `src/pyocd_debug_mcp/brain/action_policy.py`;
  - added `TurnDecision.action_batch`, bounded `wait`, and `run_script`
    contracts while preserving single-action compatibility;
  - added ordered batch execution in the turnkey loop;
  - added session-scoped client-action snapshots, hashes, and gated server API;
  - added UART write through adapter, service, MCP server tool, MCP client
    wrapper, brain allowlist, and real turnkey execution;
  - added focused unit/integration coverage.
- Test-suite pass complete after fixes:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy src`
- Real MCP server-client proof complete on the two physically connected boards:
  - `nucleo_l476rg`
  - `nrf52840dk`
- Real turnkey full Branch B feature smoke complete on the two physically
  connected boards:
  - ordered `action_batch`
  - bounded `wait`
  - named `run_script`
  - script-owned `write_serial` through the brain gate
  - `read_serial` verification
  - one MCP session per board
- Real `codex-cli` provider smoke complete on `nucleo_l476rg`:
  - Codex emitted an actual `action_batch`;
  - the batch executed `connect -> wait -> write_serial -> read_serial`;
  - the second Codex turn finalized `diagnosed_only`;
  - run root:
    `runs/20260627T231235Z-edb7bf36`.

## TODO

1. Decide whether the Nordic hardware expected for this branch should be
   `nrf52833dk` or the currently connected `nrf52840dk`.
2. If `nrf52833dk` remains required, connect a real nRF52833 DK and rerun the
   same Stage 0 / Stage 1 / MCP / turnkey smoke ladder.

## Limitations and known gaps

- This process is scoped to Branch B. Provider sessions, timeout policy,
  progress UI, checkpoints, and scoped green approval remain owned by other
  branches.
- The second connected Nordic board is physically an nRF52840, not an
  nRF52833. `stage0_check.py --board-id nrf52833dk` failed silicon identity
  with actual `0x52840` vs expected `0x52833`. The same physical board passed
  as `nrf52840dk`.

## Hardware hand-off

Executed dependency order:

```powershell
uv run python host_bootstrap.py --board-id nucleo_l476rg --board-id nrf52833dk --install-packs
uv run python stage0_check.py --board-id nucleo_l476rg --board-id nrf52833dk --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.hex --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.hex --confirm-shared-usb nucleo_l476rg --recover-test nrf52833dk --serial-read-seconds 3
uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.hex --recover-test nrf52840dk --serial-read-seconds 3
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk
```

Results:

- `nucleo_l476rg` Stage 0 passed flash and UART, Stage 1 passed.
- `nrf52833dk` Stage 0 failed exact silicon identity because the connected
  board reports `0x52840`.
- `nrf52840dk` Stage 0 passed probe, silicon identity, flash, UART, and recover.
  Stage 1 passed.
- Real MCP direct smoke passed on `nucleo_l476rg` and `nrf52840dk`:
  `connect -> write_serial -> read_serial -> disconnect`.
- Real turnkey Branch B smoke passed on `nucleo_l476rg` and `nrf52840dk`:
  `action_batch(connect, write_serial, read_serial) -> finalize`, one MCP
  session per board.
- Real turnkey full Branch B feature smoke passed on `nucleo_l476rg` and
  `nrf52840dk`:
  `action_batch(connect, wait, run_script(write_serial), read_serial) ->
  finalize`, one MCP session per board.
- Real `codex-cli` provider smoke passed on `nucleo_l476rg`:
  `action_batch(connect, wait, write_serial, read_serial) -> finalize`.

## Open decisions and surfaced issues

- No build-plan conflict surfaced.
- Hardware inventory conflict surfaced: the connected Nordic board does not
  match the `nrf52833dk` board id from the original pending-proof wording.

## Verified

- Process ledger created as a documentation artifact.
- Focused Branch B tests passed:
  `uv run pytest -q tests/test_p0_foundation.py tests/test_uart_capture.py tests/test_server_runtime_tools.py tests/test_r12_turnkey.py::test_run_turnkey_executes_ordered_action_batch_with_wait_and_uart_write`
- Full non-hardware ladder passed:
  - `uv run pytest -q` -> 277 passed
  - `uv run ruff check .` -> passed
  - `uv run mypy src` -> passed
- Hardware and real MCP proof passed on the actual connected board pair:
  `nucleo_l476rg` and `nrf52840dk`.
- Regression fixed and verified: script-owned server calls now route through
  `_execute_server_tool`, so `write_serial` appears in `mcp_tools_used` when a
  client action calls it.
- Real provider proof added: `codex-cli` produced a valid Branch B
  `action_batch` and completed the run through real MCP/hardware on
  `nucleo_l476rg`.

## Pending verification

- Exact `nrf52833dk` hardware proof remains pending because the connected
  Nordic board is an nRF52840.
- Manual shared-USB confirmation remains pending for `nrf52840dk`; Stage 0
  explicitly reported that manual item even though automated checks passed.
- Public CLI deployment of `run_script` remains incomplete because
  `pyocd-debug-brain run` has no operator-facing way to preload/register
  session-scoped client actions. The underlying runtime path is tested through a
  harness with a seeded `ClientActionStore`.
