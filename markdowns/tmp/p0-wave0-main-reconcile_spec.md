# P0 Wave 0 Main Reconcile Spec

## Task

Reconcile `main` into the clean pre-merge `P-Wave-0` baseline, keeping the best
of both branches:

- keep the validated runtime-safety and timeout hardening already proven on
  `P-Wave-0`
- bring in the additive UX/operator-shell work and useful P0 foundation
  scaffolding from `main`
- resolve any integration regressions caused by combining the two code paths
- re-run the full non-hardware ladder plus real-board validation on the
  currently attached Nordic and STM32 boards

## Reconciliation Summary

### Build plan / current docs

The current plan and repo docs already allow and describe:

- the Codex-backed turnkey path as the currently proven baseline
- an additive operator-facing shell over the same turnkey runtime
- P0/Wave-0 cleanup before further prototype branching

So bringing in the operator UX from `main` is consistent with the governing
docs, as long as it does not roll back proven runtime safety.

### `main`

`main` contributes:

- additive UX modules under `src/pyocd_debug_mcp/ux/`
- event/app scaffolding under `src/pyocd_debug_mcp/brain/events.py` and
  `src/pyocd_debug_mcp/brain/app.py`
- packaging/runtime-data updates
- host bootstrap improvements
- associated tests and doc updates

### Clean `P-Wave-0`

The clean pre-merge `P-Wave-0` baseline contributes the latest proven Wave 0
cleanup and hardening, including:

- MCP timeout normalization and safer transport teardown
- startup/runtime timeout fixes
- invalid UART/memory argument refusal handling
- mixed-board probe-resolution fix proven against the attached boards
- updated audit and validation docs

## Conflicts To Resolve

1. `main` removes or weakens several proven runtime-safety checks in
   `brain/mcp_client.py`, `server.py`, `services/uart_capture.py`, and
   `brain/config.py`. These must stay on the `P-Wave-0` side.
2. `main` adds useful event/UX integration in `brain/loop.py`, `brain/cli.py`,
   `host_bootstrap.py`, `pyproject.toml`, and new `ux/*` modules. Those should
   be preserved unless they introduce a concrete regression.
3. Repo-facing docs now conflict because `P-Wave-0` documents the Wave-0 proof
   boundary while `main` documents the new UX shell and broader turnkey state.
   The merged docs must say both things cleanly.

## Acceptance Criteria

1. The merge result keeps the validated runtime-safety/hardening behavior from
   `P-Wave-0`.
2. The merge result includes the operator-facing UX shell and its supporting
   event/app/package wiring from `main`.
3. The merged repo is free of merge markers and obvious integration regressions.
4. Non-hardware validation is green:
   - targeted regression tests
   - full `pytest`
   - `ruff`
   - `mypy`
5. Real MCP/client and board validation is green on the attached
   `nrf52840dk` and `nucleo_l476rg`, including the current layered validation
   boundary and the paths touched by the merge.
6. The relevant docs are updated to reflect the merged baseline and to note that
   the imported P0 foundation/event shell should still be cleaned up before
   further prototype expansion.

## Verification Status

Verified:

- pre-merge diff inspection shows the desired merge is feasible and low-conflict
  in code, with explicit doc conflicts and a few overlapping runtime files
- the current merge state in `P-Wave-0` already contains the main UX additions
  and the validated hardening in the most critical runtime files

Pending verification:

- full non-hardware validation after the final merge resolution
- live MCP/client + dual-board rerun after the final merge resolution
