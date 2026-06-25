# Runtime Timeout Audit Spec

IMPLEMENTED - reconciled into the build plan Step 2.4 timeout wording.

## Task

Audit the server/client and whole repository for calls that can wait forever, then close the agent-verifiable gaps so the MCP server and turnkey brain return bounded errors instead of listening forever.

## Root Cause

Several runtime paths already had user-facing budgets at higher levels, but lower-level subprocess and startup calls did not carry timeouts. In particular, vendor CLI discovery, CLI model providers, MCP initialize/list-tools startup, and serial open/write behavior could block beneath the loop's per-tool timeouts.

## Reconciliation

The build plan's settled choice is blocking-v1, but Step 2.4 says blocking hardware calls must not freeze the server or transport. The current code partially implements that in the turnkey loop with per-tool budgets, but the lower subprocess/startup layers were not consistently bounded. The fix keeps the blocking API shape and adds explicit ceilings instead of changing the architecture to tickets/async tasks.

## Scope

- Add bounded subprocess timeouts for server/probe/serial helper command paths.
- Add bounded CLI-provider subprocess timeouts and API-provider client timeouts.
- Bound MCP startup initialize/list-tools calls.
- Set pyserial `write_timeout` to the same bounded serial window.
- Add pyOCD session flash/reset/step timeout options where this installed pyOCD exposes them.
- Add focused regression tests for timeout propagation and timeout error handling.
- Update docs that describe runtime readiness and operator timeout symptoms.

## Audit Classification

Genuinely can hang or wait too long:

- `server._run_cmd`, `swd_pyocd._run_cmd`, `stage0_check.run`, and `host_bootstrap.run` external CLI calls. These invoke pyOCD/vendor CLIs and previously had no `timeout=`.
- `CodexCLIDecisionProvider` and `ClaudeCLIDecisionProvider` subprocess calls. These were in worker threads but had no child-process ceiling.
- `LocalMCPClient.start()` startup (`initialize()` plus `list_tools()`). Tool calls had read timeouts; startup did not.
- `PySerialUARTInterface.open()`. The configured pyserial timeout bounded reads, not the OS open. Python cannot reliably interrupt a kernel/driver-level serial open in-process, but setting `write_timeout` closes the missing write-side gap and the caller's read window still bounds capture after open.
- API provider calls. SDKs have their own defaults, but relying on provider defaults is not this repo's timeout discipline.

Intentionally bounded / acceptable as-is:

- `capture_uart_output()` read loop is bounded by `read_seconds`, with a small bounded reopen delay.
- workspace builds use `DEFAULT_BUILD_TIMEOUT_SECONDS`.
- Zephyr setup/build/download helpers and pack downloads already pass explicit timeouts.
- convergence watcher loops are iteration/event bounded, not unbounded polling loops.

Known architectural limit:

- `pyOCD session.open()`, flash, recover, and target register operations run in-process. pyOCD exposes flash/reset/step timeout options but not a direct connect timeout in the installed version. If a vendor DLL blocks inside C, Python cannot safely kill just that call; a future hard guarantee requires isolating hardware operations in a killable child worker.

## Validation

- Targeted pytest coverage for timeout propagation and timeout errors.
- Non-hardware validation ladder after the patch.

## Verified

- `uv run pytest -q` passes: 205 tests.
- `uv run ruff check .` passes.
- `uv run mypy src` passes.
- The default `run_check_ladder.py --preset default` passes all three checks.

## Pending verification

- Hardware behavior for pyOCD/vendor timeout options on `nrf52833dk` and `nucleo_l476rg`.
- A true native pyOCD/vendor-DLL hang still requires a future killable worker-process boundary for a hard stop guarantee.
