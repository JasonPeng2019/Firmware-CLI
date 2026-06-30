> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Wave 1 Turnkey Cleanup Failure Spec

## Goal in plain English

Treat final turnkey disconnect cleanup failure as a recorded tooling failure
instead of silently swallowing it. A run that leaves a known active board session
behind is not green, even if the model already produced a final answer.

Roadmap anchor: Wave 1 / R12 turnkey brain hardening, specifically Branch C's
bounded runtime and process/session hygiene requirements.

## Scope and non-scope

In scope:

- `run_turnkey` final cleanup after the decision loop.
- Recording a concrete brain event when final `disconnect` fails or times out.
- Converting the execution result to `blocked` / `tooling_failure` when cleanup
  fails while a session is known active.
- Regression coverage that proves the failure is visible in result, state, and
  artifacts.

Out of scope:

- Introducing killable pyOCD/vendor worker processes.
- Killing arbitrary provider or MCP process trees.
- Changing successful cleanup behavior.
- Changing explicit model-requested `disconnect` tool behavior inside the normal
  action loop.

## Reconciliation summary

- Build plan: Stage 5 Branch C says all provider, MCP startup, server helper,
  subprocess, UART, and hardware-adjacent paths need bounded failure modes; it
  also identifies killable workers as future work, not part of this narrow fix.
- Current code: `run_turnkey` attempts a final `disconnect` when
  `state.session_id` is present, but catches `MCPClientError` and does nothing.
  That can hide a failed cleanup from the final result.
- Other docs or notes: the workflow skills now require process and board-session
  hygiene after provider/hardware/MCP checks, and treat leftover spawned process
  or board sessions as a suite failure or deployment ambiguity.
- Disagreements: no settled-decision change is required. This aligns the code
  with the build plan and skill gates without implementing the larger killable
  worker feature.

## Design

After the decision loop has produced `result`, final cleanup still runs if
`state.session_id` is present. On successful disconnect, existing behavior stays
the same. On `MCPClientError`, the brain records an `unexpected_failure` event
with phase `final_disconnect`, keeps the session id in state, and replaces the
result with a tooling-failure blocked result whose root cause states that final
cleanup failed. This makes the persisted execution artifacts and CLI outcome
honest.

## Board-facts-as-data and origin tags

No board facts or origin-tagged constants change.

## Documentation plan

Add this scoped spec and update the deep audit process ledger. Governing docs
already say process/session cleanup failures are not green.

## Portability

The fix uses existing MCP/tooling error paths and does not add OS-specific
commands or assumptions.

## Verification plan

- Add a unit regression around final disconnect failure.
- Run the targeted R12 turnkey test file.
- Run the Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`.
- Run the full FirmCLI suite ladder and live provider/hardware rows after all
  audit fixes are complete.

## Acceptance criteria

- A final `disconnect` timeout/error cannot be silently ignored.
- The final `TurnkeyExecution.result` is blocked/tooling_failure when cleanup
  fails.
- The active `session_id` remains visible in state so the operator can see what
  needs cleanup.
- Artifacts contain an `unexpected_failure` event for final disconnect cleanup.

## Verified

- Targeted regression:
  `uv run pytest -q tests/test_r12_turnkey.py -k "disconnect_cleanup_fails or invocation_default_timeout_for_disconnect"`
  -> `2 passed, 54 deselected`.
- `uv run pyright --outputjson` -> 105 files analyzed, 0 diagnostics.
- `python .codex\skills\python-change\scripts\run_python_change_checks.py`
  -> ruff check/fix passed, ruff format passed, full Pyright passed, full
  pytest -> `340 passed`.
- `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> `340` pytest tests, ruff, mypy, `34` R11 benchmark tests, and R11
  benchmark help all passed.
- Live Branch C provider/hardware harness passed on both attached boards with
  both `codex-cli` and `claude-cli`.
- Public deployed CLI two-turn smoke passed by artifact semantics on both
  attached boards with both providers. Each saved run used
  `action_batch(connect,get_board_info)` then `finalize`.

## Pending verification

- Official `nrf52833dk` current-branch proof remains pending because the
  attached Nordic board is `nrf52840dk`.
- Full Wave 2 process-tree cleanup guard remains pending as Branch H work.
