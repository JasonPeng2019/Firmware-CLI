# P0.0 Validation Report

## Environment

- branch: `P-Wave-0`
- commit at validation start: `3c4cdc7f2343e8a66b547af6a42b11d3d8120ab4`
- host OS: Windows
- Python: `3.14.2`
- uv: `0.11.19`
- pyOCD: `0.44.1` via `uv run pyocd --version`
- boards attached:
  - `nucleo_l476rg`
  - `nrf52840dk`

## Scope Note

The original `P0.0` plan names `nrf52833dk + nucleo_l476rg` as the scoped
pair. This validation pass used the actually attached Nordic board,
`nrf52840dk`, plus `nucleo_l476rg`.

That means:

- the current merged branch is green on the real attached pair used in this
  pass;
- this report does **not** newly re-prove `nrf52833dk` in the merged state;
- the official scoped-pair Nordic rerun remains a follow-on proof item if Wave
  0 needs fresh `nrf52833dk` evidence specifically.

## Pass/Fail Matrix

| Layer | Command/Case | Result | Elapsed | Artifact/Log | Notes |
|---|---|---|---|---|---|
| L0 | `git status --short --branch` / `git diff --stat` / `git diff --check` | PASS | short | git output | Merge worktree is intentional; no whitespace errors from `git diff --check`. |
| L1 | `uv run pytest -q` | PASS | `10.65s` | console output | Full non-hardware suite green after merge fixes. |
| L1 | `uv run ruff check .` | PASS | short | console output | Green after removing obsolete server import and aligning tests. |
| L1 | `uv run mypy src` | PASS | short | console output | Source typing green in merged state. |
| L1 | `uv build --wheel` | PASS | short | `dist/pyocd_debug_mcp-0.1.0-py3-none-any.whl` | Packaged product still builds. |
| L2 | Live MCP timeout recovery on `nucleo_l476rg` | PASS | bounded | session ids in `runs/` | `read_serial` forced timeout returned `Tool 'read_serial' timed out after 0s.` and a fresh reconnect succeeded. |
| L2 | Live MCP timeout recovery on `nrf52840dk` | PASS | bounded | session ids in `runs/` | Same bounded timeout + reconnect success on Nordic board. |
| L2 | Invalid UART argument refusal on both boards | PASS | bounded | session ids in `runs/` | `read_seconds=-1.0` returned deterministic `Refused [uart/invalid-read-seconds] ...`. |
| L3 | `uv run python host_bootstrap.py --board-id nucleo_l476rg` | PASS | `36.1s` | console output | Matched probe `066FFF514988525067233337`, serial `COM12`. |
| L3 | `uv run python host_bootstrap.py --board-id nrf52840dk` | PASS | `35.4s` | console output | Matched probe `683377322`, serial `COM11`. |
| L4 | `uv run python stage0_check.py --board-id nucleo_l476rg ...` | PASS | `35.9s` | console output | Flash, UART `boot ok`, shared USB confirmation. |
| L4 | `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg` | PASS | `5.0s` | console output | Flash, PC read, symbol `0x1234ABCD`, UART `boot ok`. |
| L4 | `uv run python stage0_check.py --board-id nrf52840dk ... --recover-test ...` | PASS | `42.6s` | console output | Flash, UART `boot ok`, exact silicon identity, recover proof. |
| L4 | `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk` | PASS | `8.2s` | console output | Flash, PC read, symbol `0x1234ABCD`, UART `boot ok`. |
| L5/L6 | Real stdio MCP client/server smoke + 3-cycle repeatability on `nucleo_l476rg` | PASS | ~`48s` board-local portion | session ids `20260625T195030Z-eb3ebc66`, `...917d49fe`, `...ebbbf5c2`, `...9d15c1b7` | `connect/get_board_info/get_state/flash/halt/read_core_register/read_memory/resume/reset/read_serial/disconnect` repeated cleanly. |
| L5/L6 | Real stdio MCP client/server smoke + 3-cycle repeatability on `nrf52840dk` | PASS | ~`30s` board-local portion | session ids `20260625T195131Z-af484b57`, `...032770b3`, `...738c0a97`, `...39189183` | Same tool sequence repeated cleanly on Nordic board. |
| L7 | `uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."` | PASS | `127.3s` | run root `20260625T195246Z-0d6b5cc2` | Healthy confirmed, green check passed. |
| L7 | `uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52840dk --task "Verify this reference firmware is healthy and explain why."` | PASS | `101.0s` | run root `20260625T195447Z-7eeced46` | Healthy confirmed, green check passed. |
| L7 | `uv run pyocd-debug run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."` | PASS | `95.6s` | run root `20260625T195641Z-1bb62579` | Operator-facing UX shell path works against the real board. |
| L8 | `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__k001_reference_green` | PASS | `100.9s` | run root `20260625T195831Z-b63fb060` | `FULL_SUCCESS`, score `100`. |
| L8 | `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b001_wrong_boot_text` | PASS | `356.4s` | run root `20260625T200319Z-8e16fc5d` | `FULL_SUCCESS`, score `100`. |
| L8 | `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__k001_reference_green` | PASS | `110.9s` | run root `20260625T200614Z-906fa1a3` | `FULL_SUCCESS`, score `100`. |
| L8 | `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__b001_wrong_boot_text` | PASS | `310.8s` | run root `20260625T201030Z-150f14d1` | `FULL_SUCCESS`, score `100`. |

## Fixes Made During P0.0

1. `src/pyocd_debug_mcp/ux/shell.py`
   - lazy-initialize `PromptSession()` only inside `run()`
   - fix `/workspace`, `/flash-artifact`, and `/elf` to consume raw command text
     so Windows paths with backslashes are not mangled by `shlex`
2. `tests/test_server_board_config.py`
   - replace the obsolete Windows J-Link bypass expectation with the current
     auto-resolution behavior
3. `tests/test_server_runtime_tools.py`
   - remove stale `server.sys.platform` assumptions from runtime tests
4. `src/pyocd_debug_mcp/server.py`
   - remove now-unused `sys` import after retiring the old J-Link bypass path
5. Repo docs
   - resolve the `main` vs `P-Wave-0` merge conflicts in repo-facing docs
   - preserve Wave-0 hardening status while carrying forward the imported UX
     shell/product-layer state

## Remaining Risks

- The merge is green on the attached `nrf52840dk + nucleo_l476rg`, but this
  report is not a fresh official scoped-pair rerun for `nrf52833dk`.
- The imported Pass 1 event/UX shell scaffold from `main` is functioning, but
  it still needs cleanup before broader P0 prototype expansion.
- `uv run pyocd list --probes` on this Windows host still returns a console
  encoding failure after printing the probe table; the repo’s actual host
  bootstrap path is green because it uses the shared discovery path instead of
  depending on that raw CLI surface.

## Pending Hardware

- Fresh merged-state rerun on the official scoped Nordic board `nrf52833dk`,
  if the Wave 0 exit decision requires the exact scoped pair rather than the
  currently attached Nordic board.

## Deferred Prototype Risk

- full official-pair second-provider reproof
- fresh-machine Windows portability proof
- fresh-machine macOS portability proof

## Exit Decision

- [x] Wave 0 is clean enough to branch P0.
- [ ] Wave 0 is blocked; reason:

## Verification Status

Verified:

- the merged codebase is green through the full non-hardware ladder
- the merged codebase is green on the real attached pair:
  `nucleo_l476rg + nrf52840dk`
- real stdio MCP client/server, headless turnkey brain, benchmark slice, and
  operator-facing `pyocd-debug` CLI all ran successfully in this pass

Pending verification:

- fresh merged-state rerun on `nrf52833dk` if exact scoped-pair proof is
  required for this branch gate
- full second-provider and fresh-machine portability proof remain deferred
