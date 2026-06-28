> STATUS: REVIEW COMPLETE - Branch B implementation pass.

# R12 Branch B Action Boundary Review

## Scope

Reviewed the `P-Wave-B` implementation against
`markdowns/curr/r12-branch-b-action-boundary_spec.md` and the process ledger.

## Findings

- No blocking software findings remain after the final pass.
- Hardware inventory finding remains: the connected Nordic board is not an
  `nrf52833dk`. `stage0_check.py --board-id nrf52833dk` read
  `FICR.INFO.PART=0x52840`, so exact `nrf52833dk` proof is still pending until
  that physical board is connected.

## Verified

- `uv run pytest -q` -> 277 passed.
- `uv run ruff check .` -> passed.
- `uv run mypy src` -> passed.
- `host_bootstrap.py` passed for `nucleo_l476rg` and the connected Nordic
  probe/port inventory.
- `stage0_check.py` passed for `nucleo_l476rg`.
- `stage0_check.py` passed for the actual connected Nordic board as
  `nrf52840dk`, including recover validation.
- Stage 1 smoke passed for `nucleo_l476rg`.
- Stage 1 smoke passed for `nrf52840dk`.
- Real `LocalMCPClient` server-client smoke passed on both physical boards:
  `connect -> write_serial -> read_serial -> disconnect`.
- Real turnkey Branch B batch smoke passed on both physical boards:
  `action_batch(connect, write_serial, read_serial) -> finalize`.
- Real turnkey full Branch B feature smoke passed on both physical boards:
  `action_batch(connect, wait, run_script(write_serial), read_serial) ->
  finalize`.
- Script-owned server calls now route through the same brain gate as direct
  server-tool actions; the regression test proves `write_serial` appears in
  `mcp_tools_used` when called by a client action.
- Real `codex-cli` provider smoke passed on `nucleo_l476rg`. Codex emitted
  `action_batch(connect, wait, write_serial, read_serial)` on the first turn and
  finalized on the second turn. Run root:
  `runs/20260627T231235Z-edb7bf36`.

## Residual Risk

- `run_script` execution is intentionally narrow and session-scoped, but it is
  not a hardened sandbox. It receives only a gated server API and restricted
  builtins in this pass.
- The implementation preserves legacy single-action compatibility; future A/C
  merges should keep the same regression tests active while replacing or
  extending provider-facing prompt behavior.
- Public CLI client-action registration was added after this action-boundary
  review through repeatable `--client-action NAME=PATH`, then verified in the
  full deployment completion pass and the multi-loop deployment report.
  Persistent provider sessions remain separate Branch A scope, not a Branch B
  residual risk.
