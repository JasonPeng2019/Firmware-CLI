> STATUS: IMPLEMENTED AND VALIDATED - narrow Wave 1 audit gap closed against
> the R12 remote-primary provider continuity contract.

# R12 OpenAI Native Sync Metadata Spec

## Goal in plain English

Fix OpenAI remote-primary native memory sync metadata so periodic safety sync is
recorded as remote resume, not local-memory fallback.

Roadmap anchor: R12 Stage 5 provider-session/memory hardening in
`markdowns/firmware_agent_build_plan_concrete (10).md`,
`markdowns/curr/r12_turnkey_spec.md`, and
`markdowns/curr/r12-prompt-memory-cost-hardening_spec.md`.

## Scope and non-scope

In scope:

- Fix `OpenAIDecisionProvider` metadata for the periodic native memory safety
  sync branch.
- Preserve request behavior: when a valid `previous_response_id` exists, the
  OpenAI provider must still pass that id to `responses.create`.
- Record the safety-sync branch as `continuation_path="remote-resume"`,
  `prompt_render_mode="remote-sync"`, `native_sync_used=true`, and
  `local_memory_fallback_used=false`.
- Add focused fake-OpenAI coverage proving the request and metadata together.
- Sync the repeat adversarial audit ledger and relevant docs if behavior or
  status changes.

Out of scope:

- Live OpenAI API proof. This run uses fake SDK clients and does not require API
  credits or credentials.
- Changing Anthropic local-primary behavior.
- Changing Codex/Claude CLI native sync metadata; both already use
  `remote-resume` for the resumed safety-sync branch.
- Hardware validation.

## Reconciliation summary

- Build plan: OpenAI Responses is a `remote-primary` provider using
  `previous_response_id`, with periodic compact-memory safety sync injected into
  the native session.
- Current code: `OpenAIDecisionProvider._next_decision_sync` keeps passing
  `previous_response_id` during native sync, but labels the branch as
  `local-memory-fallback`.
- Other docs or notes: README/current-progress/R12 specs describe OpenAI native
  continuation with periodic safety sync, not fallback, when a response id
  exists.
- Disagreement: product behavior is mostly correct, but artifact/progress
  metadata is wrong. That is a real Wave 1 auditability gap because prompt
  accounting and recovery logic depend on truthful continuation metadata.

## Design

Change only the OpenAI native-sync branch:

```text
elif should_inject_native_memory_sync(session_state):
    use_local_memory = True
    continuation_path = "remote-resume"
    native_sync_used = True
    prompt_render_mode = "remote-sync"
```

This matches Codex/Claude remote-primary behavior and the actual OpenAI request,
which still includes `previous_response_id`.

## Board-facts-as-data and origin tags

- No board facts are introduced.
- `remote-resume`, `remote-sync`, and native sync cadence are
  `PROJECT-DEFINED` provider metadata semantics.

## Documentation plan

- Record the issue/fix/validation in
  `markdowns/tmp/curr-archive-20260701-repeat-adversarial-audit/wave1-repeat-adversarial-audit_process.md`.
- This narrow spec is sufficient; no build-plan amendment is needed because the
  build plan already says OpenAI uses native continuation with periodic safety
  sync.

## Portability

- No OS-specific behavior changes.
- Fake-provider coverage must not require live credentials, network, or a
  particular shell.

## Verification plan

- Add a focused test in `tests/test_r12_turnkey_merge.py` that constructs an
  OpenAI provider session with:
  - existing `response_id`;
  - local memory available;
  - `turns_since_last_memory_sync >= native_sync_every`.
- Assert the fake SDK receives `previous_response_id`.
- Assert provider metadata records `continuation_path="remote-resume"`,
  `prompt_render_mode="remote-sync"`, `native_sync_used=true`, and
  `local_memory_fallback_used=false`.
- Run the focused test, Python-change gate, and FirmCLI suite ladder.

## Acceptance criteria

- OpenAI periodic native sync uses true remote-primary metadata when a native
  response chain exists.
- New-session-from-memory recovery remains labeled `local-memory-fallback`.
- Missing-handle bootstraps from memory remain labeled `local-memory-fallback`.
- Existing API simulation and prompt accounting tests stay green.

## Verified

- Gap reproduced by code inspection: `src/pyocd_debug_mcp/brain/provider_openai.py`
  passes `previous_response_id` but sets `continuation_path` to
  `local-memory-fallback` in the native-sync branch.
- Implemented in `src/pyocd_debug_mcp/brain/provider_openai.py`: the native
  memory safety-sync branch keeps `previous_response_id`, renders
  `remote-sync`, and records `continuation_path="remote-resume"`.
- Focused regression:
  `uv run pytest -q tests/test_r12_turnkey_merge.py -k "openai_provider_records_native_sync_as_remote_resume or openai_provider_uses_previous_response_id"`
  -> `2 passed`.
- Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`
  -> ruff check/format passed, pyright 0 diagnostics, full pytest
  `387 passed`.
- FirmCLI non-hardware suite:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> full pytest `387 passed`, ruff passed, mypy passed, benchmark harness
  tests `34 passed`, R11 help smoke passed.
- API simulation:
  `uv run pytest -q tests/test_r12_turnkey_merge.py -k "openai_provider or anthropic_provider or native_sync"`
  -> `6 passed`.

## Pending verification

- None for this narrow no-hardware gap.
