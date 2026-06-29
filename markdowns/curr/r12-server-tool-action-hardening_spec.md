> STATUS: PROPOSAL - implementation pass may proceed after local reconciliation in this document.

# r12 server tool action hardening

## Goal in plain English

Harden the Branch A/B provider action boundary so server tool names have one
source of truth and provider-emitted `server_tool:<name>` calls cannot leak a
redundant or conflicting `arguments.tool_name` into the MCP tool arguments.

Roadmap anchor: R12 / Branch A+B live-provider hardening.

## Scope and non-scope

In scope:

- Centralize the server-native action-name list used by action policy and
  batched action parsing.
- Treat `server_tool:<name>` as authoritative for the tool name.
- Strip redundant `arguments.tool_name` from namespaced server-tool calls before
  invoking the MCP server.
- Refuse conflicting namespaced calls such as
  `action_type=server_tool:connect` with `arguments.tool_name=read_serial`.
- Normalize the live-provider legacy shape
  `action_type=server_tool` with nested `arguments.arguments={...}` so real MCP
  tools receive only their own argument object.
- Refuse duplicated outer/nested server-tool arguments when the two values
  conflict.
- Add focused smoke/regression tests for the above behavior.
- Run no-credit validation: unit/regression tests, lint/type checks, the
  non-hardware ladder, and a Codex-compatible/local smoke where feasible.
- Document Claude/API validation that is blocked until Claude usage and paid API
  credits are available again.

Out of scope:

- No real Claude CLI run in this pass, because Claude session usage is exhausted.
- No Anthropic/OpenAI API provider run in this pass, because there are no actual
  API credits available for this validation.
- No hardware flashing requirement for this narrow parser/policy hardening pass.
- No redesign of provider decision schema, memory, recovery, or benchmark cases.

## Reconciliation summary

- Build plan: R12 requires live-provider action boundaries to be deterministic
  and auditable. Provider shape drift should be handled by small normalization
  layers, not by permissive downstream leakage.
- Current code: `action_policy.py` defines `SERVER_NATIVE_ACTIONS`, while
  `loop.py` repeats the same literal set in `_action_from_call`. The namespaced
  parser forwards `arguments` unchanged, so a redundant `tool_name` can reach
  the selected MCP tool as an unexpected input field.
- Existing tests: coverage proves `server_tool:connect` is accepted, but does
  not prove redundant `tool_name` stripping or conflicting `tool_name` refusal.
- Disagreements: none. The stricter behavior is additive for valid provider
  output and fail-closed for ambiguous provider output.

## Design

- Keep `SERVER_NATIVE_ACTIONS` in `brain.action_policy` as the canonical
  immutable set.
- Add a small helper such as `namespaced_server_tool_name(action_type)` that
  parses `server_tool:<name>` and returns the allowed tool name or `None`.
- Make `classify_action` use that helper instead of local string parsing.
- Make `_action_from_call` import and use `SERVER_NATIVE_ACTIONS` and the helper
  instead of repeating the tool list.
- For namespaced calls:
  - copy `call.arguments` before mutation;
  - pop `tool_name` from the copied arguments;
  - accept no embedded name or the same embedded name;
  - raise `TurnkeyRefusal` when the embedded name is a different string;
  - return `ServerToolAction(tool_name=<namespace name>, arguments=<stripped args>)`.
- Keep legacy `action_type=server_tool` behavior unchanged: it still requires
  `arguments.tool_name` and strips that field before invoking the MCP tool.
- If a real provider wraps MCP inputs as `arguments.arguments`, unwrap that
  nested object before invocation. Same-value duplicated outer arguments are
  tolerated; conflicting duplicates fail closed before any MCP tool call.

## Board-facts-as-data and origin tags

This change is provider/action-boundary logic only. It does not add, remove, or
reinterpret board facts. Any later hardware proof must keep board IDs, probe
IDs, serial ports, and silicon IDs in run artifacts, not as assumptions in this
spec.

## Documentation plan

- Keep this spec in `markdowns/curr/` while the hardening pass is active.
- Track implementation/test status in
  `markdowns/curr/r12-server-tool-action-hardening_process.md`.
- Record review verdict in
  `markdowns/curr/r12-server-tool-action-hardening_review.md`.
- Record blocked future Claude/API validation in
  `markdowns/curr/r12-claude-refresh-hardening-test-plan_spec.md`.

## Portability

The fix must stay platform-neutral Python. It should not depend on shell
quoting, hardware availability, provider credentials, or Windows-specific
behavior.

## Verification plan

- Targeted pytest for action policy and R12 turnkey action parsing.
- Lint/type checks on touched files.
- Repository non-hardware ladder through the FirmCLI check script.
- Codex-compatible smoke that exercises provider-shaped decisions without
  spending Claude usage or paid API credits.
- Explicitly pending: real Claude CLI multi-turn provider run and paid
  Anthropic/OpenAI API provider runs.

## Acceptance criteria

- There is only one canonical server-native action set.
- `classify_action("server_tool:connect")` still returns `server_native`.
- Unknown namespaced server tools still fail closed.
- `server_tool:connect` with redundant `arguments.tool_name="connect"` invokes
  `connect` without forwarding `tool_name`.
- `server_tool:connect` with conflicting `arguments.tool_name` is refused before
  any MCP tool call.
- Legacy `server_tool` calls with nested `arguments.arguments` are unwrapped
  before MCP invocation.
- Conflicting outer/nested legacy server-tool arguments are refused before MCP
  invocation.
- All no-credit tests run in this pass are green.
- Pending live-provider/API checks are documented with exact run intent.

## Verified

- Implemented canonical namespaced server-tool parsing in
  `src/pyocd_debug_mcp/brain/action_policy.py`.
- Updated `src/pyocd_debug_mcp/brain/loop.py` to use the canonical server-tool
  set and helper.
- Updated the provider prompt's server-tool list to render from the same
  canonical set.
- Added regression coverage in `tests/test_p0_foundation.py` and
  `tests/test_r12_turnkey.py`.
- Targeted focused tests passed:
  - `uv run pytest -q tests/test_p0_foundation.py::test_action_policy_accepts_namespaced_server_tool_action tests/test_r12_turnkey.py::test_run_turnkey_strips_redundant_tool_name_from_namespaced_server_tool tests/test_r12_turnkey.py::test_run_turnkey_refuses_conflicting_tool_name_on_namespaced_server_tool`
  - Result: 3 passed.
- Final post-prompt-hardening target set passed:
  - `uv run pytest -q tests/test_r12_turnkey.py::test_provider_prompt_bundle_exposes_static_and_dynamic_render_modes tests/test_p0_foundation.py::test_action_policy_accepts_namespaced_server_tool_action tests/test_r12_turnkey.py::test_run_turnkey_strips_redundant_tool_name_from_namespaced_server_tool tests/test_r12_turnkey.py::test_run_turnkey_refuses_conflicting_tool_name_on_namespaced_server_tool`
  - Result: 4 passed.
- Broader touched tests passed:
  - `uv run pytest -q tests/test_p0_foundation.py tests/test_r12_turnkey.py`
  - Result: 76 passed.
- Full no-credit ladder passed:
  - `uv run pytest -q`: 322 passed.
  - `uv run ruff check .`: passed.
  - `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`:
    passed.
  - `uv run pytest -q tests/test_r11_benchmark.py`: 34 passed.
  - `uv run python -m tests.harness.r11_benchmark --help`: passed.
- Real Codex CLI adapter smoke passed:
  - Parsed a hardware-free `FinalizeAction`.
  - Parsed a provider-emitted `server_tool:connect` batch with redundant
    `arguments.tool_name`, and local normalization produced
    `ServerToolAction(tool_name=connect, arguments={'board_id': 'nrf52833dk'})`.
- Follow-up live validation exposed and fixed a second provider-shape hardening
  gap: Codex emitted legacy `server_tool` calls with nested
  `arguments.arguments`. The loop now unwraps those nested arguments and refuses
  conflicting duplicates. Regression tests and the full suite passed after the
  fix.
- Real Claude CLI run after usage refresh is complete for the attached
  `nucleo_l476rg + nrf52840dk` pair, including multiple code-writing repair
  prompts on both boards. Official `nrf52833dk` closure remains pending because
  the attached Nordic board identifies as `0x52840`.

## Pending verification

- Anthropic/OpenAI API provider run after credits are available.
