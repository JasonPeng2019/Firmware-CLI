# Review for p0-foundation

Task: Final independent review of the P0 foundation baseline before Wave 1 branch fan-out

## Verdict

CLEAN

## Resolved findings

| severity | file | resolution |
| --- | --- | --- |
| MAJOR | `src/pyocd_debug_mcp/timeouts.py`, `src/pyocd_debug_mcp/brain/decision_types.py` | The shared timeout substrate now covers the full P0 planning surface: tool defaults, UART read/grace, build, batch, external-command, provider, and MCP-startup budgets all live in `TurnkeyTimeoutConfig` / `TurnkeyTimeoutUpdate`. |
| MAJOR | `src/pyocd_debug_mcp/brain/cli.py`, `src/pyocd_debug_mcp/brain/app.py`, `src/pyocd_debug_mcp/brain/benchmark.py` | The promised CLI/app hook seam is now real. `pyocd-debug-brain` accepts `--timeout-config-json`, `--timeout-proposal-json`, and `--iteration-estimate-json`, validates them, and threads them into the invocation/runtime path. |
| MAJOR | `README.md` | Public README links now point to the active P0 docs and the historical `R10` / `R11` docs in `markdowns/tmp/`, so the repo entrypoint no longer sends readers to dead paths. |
| MINOR | `src/pyocd_debug_mcp/timeouts.py` | The UART grace window is now a named `PROJECT-DEFINED` constant instead of an inline literal. |
| MINOR | `src/pyocd_debug_mcp/brain/mcp_client.py` | MCP startup timeout injection remains configurable while preserving the existing test/monkeypatch surface by resolving the default at runtime, not at function-definition time. |

## Verification rerun

Passed after the fixes:

- `uv run pytest -q tests/test_p0_foundation.py tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py tests/test_ux_cli.py`
- `uv run pytest -q`
- `uv run ruff check .`
- `uv run mypy src`

Results:

- targeted regression subset: `72 passed`
- full repo pytest: `246 passed`
- ruff: clean
- mypy: clean

## Residual risk

No new P0-specific code-quality or doc-sync issues remain in the reviewed surface.
Open project work is now back to the already-known next-step items, not unresolved P0 baseline defects.
