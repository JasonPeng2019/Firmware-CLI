# Process ledger for r12-turnkey-phase1

## Goal and roadmap anchor

Task: Freeze and implement the first turnkey brain/CLI slice as an MCP client
with live Nordic proof
Roadmap anchor: `R12`

## Done

- loaded the named workflow skills and their required command/authority docs
- reconciled the active roadmap/build-plan description of `R12` against the
  real codebase
- confirmed `R12` is still greenfield in product code:
  - no `src/pyocd_debug_mcp/brain/` package exists yet
  - no turnkey CLI exists yet
  - no root `skills/` tree exists yet
- confirmed the already-proven substrate boundary this phase is allowed to build
  on:
  - Stage 0
  - Stage 1 smoke
  - MCP server/runtime safety layer
  - `R11` benchmark harness and live Nordic alternate-board proof
- froze the phase-1 design direction in the paired spec:
  - real stdio MCP client
  - turnkey CLI
  - tracked skill files
  - deterministic bounded loop
  - live `nrf52840dk` acceptance slice
- implemented the first turnkey package under `src/pyocd_debug_mcp/brain/`
- added the `pyocd-turnkey` CLI entrypoint and tracked skills under
  `skills/turnkey/`
- added targeted unit coverage for the new slice
- fixed the repo-wide `ruff` failure in
  `.codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py` so the
  broader suite can go green again
- completed the live Nordic acceptance slice on attached `nrf52840dk`:
  - host bootstrap
  - Stage 0
  - Stage 1 smoke
  - turnkey `reference-health-check`
  - turnkey `nordic-recover-cycle`

## In progress

- syncing final docs and remaining-work notes after the green phase-1 result

## TODO

- roll the phase-1 slice onto the official scoped pair
- expand the skill set into repair-oriented premium workflows
- define the next brain-state/self-evaluation layer
- freeze and run the full product-#2 acceptance benchmark

## Limitations and known gaps

- this pass is intentionally phase 1 of `R12`, not the whole premium bug-fixing
  brain
- no claim is being made yet about general LLM-driven repair, code editing, or
  premium benchmark superiority over `R11`
- the final live-suite proof in this pass is on the attached `nrf52840dk`, not
  yet the full scoped-pair `R12` rollout

## Hardware hand-off

- active live target for the end-of-pass suite: attached `nrf52840dk`

## Open decisions and surfaced issues

- keep the first skill set deterministic and trustworthy rather than widening
  immediately into open-ended repair
- use the existing server as the hardware boundary even when the brain can reuse
  local shared helpers for read-only artifact facts such as symbol resolution
- do not treat same-probe parallel turnkey runs as supported for phase 1; one
  run owns the board/probe at a time

## Verified

- local `mcp` SDK is installed and exposes:
  - `mcp.client.stdio.stdio_client`
  - `mcp.client.stdio.StdioServerParameters`
  - `mcp.ClientSession`
- `ClientSession` supports the needed phase-1 calls:
  - `initialize()`
  - `list_tools()`
  - `call_tool(...)`
- targeted validation passed:
  - `uv run pytest -q tests/test_turnkey.py`
  - `uv run ruff check src/pyocd_debug_mcp/brain tests/test_turnkey.py`
  - `uv run mypy src`
- broader repo validation passed:
  - `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
- live Nordic phase-1 proof passed:
  - `uv run python host_bootstrap.py --board-id nrf52840dk`
  - `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --recover-test nrf52840dk --confirm-shared-usb nrf52840dk`
  - `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`
  - `uv run pyocd-turnkey run --board-id nrf52840dk --skill-id reference-health-check --json`
  - `uv run pyocd-turnkey run --board-id nrf52840dk --skill-id nordic-recover-cycle --json`

## Pending verification

- scoped-pair rollout and the later premium-brain slices
