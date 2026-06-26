# Process ledger for p0-wave0-main-reconcile

## Goal and roadmap anchor

Task: Close the useful main-to-P-Wave-0 runtime gap and revalidate against real MCP clients and attached boards
Roadmap anchor: `R12` prototype Wave 0 / `P0`

## Done

- loaded the workflow-core, write-process, and test-suite instructions
- reconciled the current repo state against the build plan, roadmap, README,
  and current-progress ledger
- diffed `main` against `P-Wave-0` and identified the useful remaining
  runtime-only gap:
  - Windows implicit J-Link UID bypass in `server.py`
  - prompt-toolkit no-console fallback in `ux/shell.py`
- identified an important negative constraint:
  `main` also carries weaker server argument validation in the same area, so
  the reconcile pass must be selective rather than a blind merge
- scaffolded this process ledger and the matching spec
- ported the useful `main` runtime behavior into `P-Wave-0`:
  - Windows implicit J-Link UID bypass in `server.py`
  - prompt-toolkit no-console fallback in `ux/shell.py`
- preserved the stronger `P-Wave-0` server argument validation that `main`
  would have weakened
- updated regression coverage for:
  - Windows/non-Windows J-Link probe-resolution behavior
  - Windows connect path passing `unique_id=None` through to the backend
  - prompt-toolkit no-console fallback
- reproduced a real attached-Nordic live failure through the MCP client/server
  path:
  - `connect(board_id=\"nrf52840dk\")` failed with opaque `KeyError: 1`
- fixed that repo bug in `adapters/swd_pyocd.py` by mapping the pyOCD
  `KeyError(1)` failure to a concrete target-connect diagnostic
- added a regression guard for that error mapping in `tests/test_target_control.py`
- ran targeted regression tests:
  - `uv run pytest -q tests/test_server_board_config.py tests/test_server_runtime_tools.py tests/test_ux_cli.py tests/test_target_control.py`
  - result: PASS
- reran the full non-hardware suite ladder:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`
  - `uv run pytest -q tests/test_r11_benchmark.py`
  - `uv run python -m tests.harness.r11_benchmark --help`
  - result: PASS
- ran live stdio MCP client/server validation on attached hardware:
  - `nucleo_l476rg`: connect -> get_board_info -> read_memory -> disconnect = PASS
  - `nucleo_l476rg`: connect -> read_serial(expected='boot ok') -> disconnect = PASS
  - attached Nordic probe identified via `nrfjprog --deviceversion` as `NRF52840_xxAA_REV2`
  - `nrf52840dk`: connect now fails fast with the improved actionable
    diagnostic instead of opaque `KeyError: 1`

## In progress

- none

## TODO

- decide whether to treat the attached Nordic board's current probe/programmer
  failure as a separate bench-state incident or a follow-up repo bug once the
  board is physically rechecked

## Limitations and known gaps

- this pass only closes the useful runtime gap from `main`; it does not claim
  broad doc parity between branches
- the attached Nordic board is currently not green through live MCP attach on
  this Windows host:
  - `nrfjprog --deviceversion` identifies it as `NRF52840_xxAA_REV2`
  - `nrfjprog --recover` and MCP `connect(board_id=\"nrf52840dk\")` both fail at
    the probe/target-access boundary in the current session
  - this looks like a live bench/probe-state problem rather than a regression
    from the reconcile patch, because the repo now fails quickly with a typed
    diagnostic and the vendor CLI is failing too

## Hardware hand-off

- after physically rechecking or power-cycling the attached Nordic board/probe,
  rerun:
  - `nrfjprog --deviceversion`
  - `nrfjprog --recover`
  - `uv run python - <<PY ... LocalMCPClient().connect(board_id=\"nrf52840dk\") ... PY`
- if that succeeds, add one live MCP `read_memory(0x10000100)` and one bounded
  `read_serial(expected_text=\"boot ok\")` proof for `nrf52840dk`

## Open decisions and surfaced issues

- surfaced issue: `current-progress.md` already claims the Windows implicit
  J-Link bypass exists, but the current `P-Wave-0` code did not yet implement
  it before this pass
- no settled build-plan decision change is required for this reconcile pass
- surfaced live hardware issue: the attached Nordic board/probe path is not
  currently healthy enough for full live MCP validation, and the vendor CLI is
  failing at the same boundary

## Verified

- useful gap analysis is complete
- spec/process artifacts exist and are aligned with the task
- selective code import, regression guards, non-hardware suite, and live STM32
  MCP validation are complete

## Pending verification

- live Nordic MCP validation after the current board/probe failure is cleared
