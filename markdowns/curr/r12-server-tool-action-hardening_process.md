# Process ledger for r12 server tool action hardening

## Goal and roadmap anchor

Task: Centralize server tool action normalization and harden namespaced
`server_tool` argument handling without spending Claude/API credits.

Roadmap anchor: R12.

## Done

- Loaded and applied the requested FirmCLI workflow skills:
  `firmcli-write-process`, `firmcli-specs`, `firmcli-spec-loop`,
  `firmcli-test-suite`, and `firmcli-fix-bug`.
- Audited the current action policy and parser code.
- Confirmed the hardening gap:
  - `SERVER_NATIVE_ACTIONS` exists in `action_policy.py`;
  - `_action_from_call` repeats the same tool-name set in `loop.py`;
  - existing tests accept `server_tool:connect` but do not prove redundant
    `arguments.tool_name` is removed.
- Created this process ledger and
  `markdowns/curr/r12-server-tool-action-hardening_spec.md`.
- Implemented canonical namespaced server-tool parsing in
  `brain.action_policy`.
- Replaced the duplicated server-tool list in `brain.loop` with the canonical
  set and helper.
- Made the provider prompt's displayed server-tool list render from the same
  canonical set, preventing prompt drift from policy/parser behavior.
- Hardened namespaced action parsing:
  - redundant same-value `arguments.tool_name` is stripped;
  - conflicting embedded `arguments.tool_name` fails closed with
    `brain/conflicting-server-tool-name`.
- Added tests for policy parsing, redundant-name stripping, and conflicting-name
  refusal.
- Real Codex adapter smoke passed for both structured finalize output and the
  namespaced redundant `tool_name` provider-shape case.

## In progress

- None for the no-credit scope.

## TODO

- Run the scaled Claude CLI refresh test after usage refresh:
  - one board first;
  - at least two top-level user prompts in the same continued workflow;
  - short prompts;
  - target `max_iters=2` per user prompt, allowing `max_iters=3` only for the
    first prompt if setup needs it;
  - no exhaustive Claude matrix on a basic Claude Pro window;
  - optional third prompt with one tiny code-writing/workspace-change proof only
    if the two-prompt smoke leaves enough usage headroom.
- Run Anthropic/OpenAI API provider smoke after paid credits are available.

## Limitations and known gaps

- Claude CLI validation is intentionally not run in this pass because current
  Claude usage is exhausted.
- The deferred Claude validation is intentionally scaled down. The previous
  exhaustive Claude live pass consumed usage too quickly, so the next green bar
  should prove the real Claude adapter/action path across multiple top-level
  user prompts without trying to rerun the whole two-board, multi-case matrix.
- Anthropic/OpenAI API provider validation is intentionally not run because
  there are no paid API credits available for this validation.
- Hardware flashing is not required for this narrow parser/policy hardening
  pass. Prior hardware proof remains documented in the Branch A live-provider
  process ledger.

## Hardware hand-off

No new hardware hand-off is required for the code change itself. If a later
full live-provider proof is requested, run it under the existing R12 hardware
suite process and preserve board/probe/serial/silicon artifacts.

## Open decisions and surfaced issues

- Namespaced action type is authoritative. A same-value embedded
  `arguments.tool_name` is stripped; a different embedded value is refused.

## Verified

- `uv run pytest -q tests/test_p0_foundation.py::test_action_policy_accepts_namespaced_server_tool_action tests/test_r12_turnkey.py::test_run_turnkey_strips_redundant_tool_name_from_namespaced_server_tool tests/test_r12_turnkey.py::test_run_turnkey_refuses_conflicting_tool_name_on_namespaced_server_tool`
  - 3 passed.
- `uv run pytest -q tests/test_r12_turnkey.py::test_provider_prompt_bundle_exposes_static_and_dynamic_render_modes tests/test_p0_foundation.py::test_action_policy_accepts_namespaced_server_tool_action tests/test_r12_turnkey.py::test_run_turnkey_strips_redundant_tool_name_from_namespaced_server_tool tests/test_r12_turnkey.py::test_run_turnkey_refuses_conflicting_tool_name_on_namespaced_server_tool`
  - 4 passed after the prompt-list canonicalization patch.
- `uv run ruff check src\pyocd_debug_mcp\brain\action_policy.py src\pyocd_debug_mcp\brain\loop.py tests\test_p0_foundation.py tests\test_r12_turnkey.py`
  - passed.
- `uv run pytest -q tests/test_p0_foundation.py tests/test_r12_turnkey.py`
  - 76 passed.
- `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`
  - passed, no issues in 66 source files.
- `uv run python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  - passed:
    - 322 pytest tests passed;
    - ruff passed;
    - mypy passed;
    - 34 R11 benchmark tests passed;
    - R11 benchmark help passed.
- `codex --version`
  - `codex-cli 0.142.2`.
- Real Codex CLI adapter smoke:
  - `FinalizeAction` parsed with `classification=healthy`.
  - Namespaced redundant server-tool smoke parsed as a batch and normalized to
    `tool_name=connect`, `arguments={'board_id': 'nrf52833dk'}`.

## Pending verification

- Real Claude CLI short multi-user-prompt smoke after usage refresh, sized for
  a basic Claude Pro five-hour window.
- Anthropic/OpenAI API provider run after credits are available.
