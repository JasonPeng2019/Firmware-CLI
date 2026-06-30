# Branch B Hardbar Prototype Spec

## Goal in plain English

Make Branch B satisfy the prototype contract in `markdowns/things-to-change.md`:
the model may do free host work during its provider turn, but every turn must
close with one governed board/client/terminal decision. File reads, source
edits, and local builds must not be model-facing brain actions.

Roadmap anchor: `things-to-change.md` Prototype Priority item 2 and entries
#11/#12; `R12_P_SPLIT.md` Branch B.

## Scope

In scope:

- remove `read_file`, `replace_file`, and `run_build` from the TurnDecision
  schema and prompt action list
- refuse stale `read_file`, `replace_file`, and `run_build` actions if a
  provider returns them anyway
- keep `run_green_check` as a governed final verifier because it drives the
  board/hardware path
- record provider-native workspace changes at the next governed boundary
- update regression tests so they prove provider-native host work plus
  brain-governed flash/green-check behavior

Out of scope for this pass:

- replacing CLI providers with SDK-backed Codex/Claude session APIs
- Wave 2 progress UI, stream checkpoints, cache reuse, scoped green approval,
  and process-tree cleanup implementation
- broad provider-native tool-call output format

## Reconciliation Summary

- Build plan: Branch B is the action-boundary branch. It must not re-gate inert
  host work through the brain.
- Current code before this pass: Branch B had additive action/batch/client-action
  behavior, but still exposed `read_file`, `replace_file`, and `run_build` as
  TurnDecision actions.
- User requirement: the prototype target is the user's desired final-product
  prototype, not a smaller agent-selected subset.
- Decision: preserve private compatibility models/helpers where useful, but make
  the model-facing schema, prompt, batch parser, and runtime executor reject
  host actions as governed decisions.

## Design

Provider-native host work:

- the provider process receives the workspace root and uses its own host tools to
  inspect, edit, and build
- host edits must stay inside the configured edit roots
- the brain observes `WorkspaceSession.changed_files()` at the next governed
  decision boundary and records a `model_native_host_work_observed` event

Governed decisions:

- server-native board actions remain routed through the MCP client
- `run_script` remains a gated client action over the server API
- `wait` remains a bounded brain-local action
- `run_green_check` remains governed because it flashes/reads/verifies board
  state
- `finalize` remains the terminal decision, with healthy/fixed gated by a prior
  successful `run_green_check`

## Verification Plan

- focused unit/regression tests for action policy and schema
- focused turnkey tests for stale host-action refusal
- focused turnkey test proving provider-native workspace mutation followed by
  governed flash and green check
- Python-change gate: Ruff autofix, Ruff format, Pyright JSON, pytest
- full product test suite including live provider/hardware checks where the
  environment permits

## Acceptance Criteria

- `read_file`, `replace_file`, and `run_build` do not appear as TurnDecision
  schema action variants
- prompt action list tells the model to use provider-native host tools for host
  work and not emit host actions
- stale direct or batched host actions are refused with a deterministic code
- provider-native host edits are visible in brain events and provider memory
- the A/B/C combined suite remains green, including real-board checks on the two
  connected boards before declaring full success

## Verified

- Focused local tests for the new Branch B boundary passed on 2026-06-30:
  `uv run pytest -q tests/test_p0_foundation.py::test_action_policy_classifies_branch_b_boundaries tests/test_p0_foundation.py::test_turn_decision_schema_excludes_model_native_host_actions tests/test_r12_turnkey.py::test_run_turnkey_refuses_model_native_read_file_action tests/test_r12_turnkey.py::test_run_turnkey_allows_green_check_after_first_failed_fix_verification`
- Full non-hardware suite ladder passed after the final code changes on
  2026-06-30: full pytest `342 passed`, ruff clean, mypy clean, R11 benchmark
  tests `34 passed`, and R11 benchmark help rendered.
- Python-change gate passed on 2026-06-30: ruff check/fix, ruff format, full
  Pyright `0` diagnostics, and full pytest `342 passed`.
- Attached-board substrate proof passed on 2026-06-30 for
  `nucleo_l476rg + nrf52840dk`: host bootstrap, Stage 0, and Stage 1 smoke.
- Codex CLI live provider proof passed on both attached boards through the
  Branch C harness and `b001_wrong_boot_text` code-writing benchmark.

## Pending Verification

- Claude CLI code-writing benchmark after provider quota resets.
- Exact official `nrf52833dk` proof; the attached Nordic board in this session
  is `nrf52840dk`.
- API-provider parity, fresh-machine portability, and Wave 2 prototype modules.
