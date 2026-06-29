# Branch C Test Plan — Event Spine + Timeout Policy

## Scope

Validates the `P-Wave-C` implementation against its written spec in
`markdowns/R12_P_SPLIT.md` ("Branch C - Event Spine + Timeout Policy",
lines 275-331). Branch C owns four things:

1. `brain/events.py` — the canonical `BrainEvent` taxonomy plus sink/fanout
   helpers.
2. `brain/timeout_policy.py` — parses model timeout/iteration proposals,
   applies brain-owned clamps, builds partial server timeout-sync requests.
3. `src/pyocd_debug_mcp/timeouts.py` — single source of truth for timeout
   defaults and clamp ranges, plus session/client-scoped effective timeout
   state.
4. The timeout-consumption hooks — providers consume `provider_seconds`,
   tool calls consume action timeouts, server sync applies partial updates
   only to *future* connects.

Branch C must **not** own: batch execution semantics, client-action
execution, checkpoint continue/cancel decisions, inspector UI, provider
adapter rewrites beyond the stable timeout-consumption hook, or a
model-facing timeout-admin tool.

## Harness

`tests/harness/branch_c_tests.py`. Run with:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk
```

Each check below prints `PASS` / `FAIL` / `SKIP` with a one-line reason.
The process exit code is non-zero iff at least one check is `FAIL`.
`SKIP` (missing hardware, missing/unauthenticated `codex`) does not fail
the run — those are environment preconditions, not Branch C defects.

## Preconditions

- The board under test (`nrf52840dk` by default — the retained alternate
  Nordic profile noted live-proven in `markdowns/current-progress.md`) is
  plugged in and idle (no other pyOCD/J-Link session holding it).
- `codex` CLI installed and authenticated (`codex login`) for the checks
  that drive a real model turn. If unauthenticated, those checks `SKIP`
  rather than `FAIL` — see the conversation history for the exact 401
  symptom and the `codex logout && codex login` fix.
- Repo's non-hardware ladder (`uv run pytest -q`, `uv run ruff check .`,
  `uv run mypy src`) is already green. This harness does not re-run that
  ladder; it is a Branch C-specific, hardware-aware supplement to it.

## Check matrix

| # | Name | Needs HW | Needs codex | Spec clause it proves |
|---|------|----------|--------------|------------------------|
| 1 | `probe_visible` | yes | no | precondition only — gates the rest |
| 2 | `timeout_defaults_and_clamp_ranges` | no | no | `timeouts.py` is the single source of truth for defaults/clamp ranges |
| 3 | `timeout_admin_not_model_facing` | no | no | "server timeout sync is brain-only/internal and must not appear in the model-facing tool schema bundle" |
| 4 | `no_overreach_into_other_branches` | no | no | "Should not own" list (batch/client-action/checkpoint/inspector) |
| 5 | `policy_clamps_and_partial_update` | no | no | `timeout_policy.py` clamps proposals, derives a *partial* server update, and never lets the model own the hard iteration cap |
| 6 | `stage0_bringup` | yes | no | precondition — board is real and alive before trusting any hardware-touching check below |
| 7 | `live_sync_does_not_mutate_open_session` | yes | no | "does not mutate an already-open pyOCD session" / "applies ... only forward", proven against a real live session |
| 8 | `codex_dry_run_prompt_render` | no | yes | the real rendered turn prompt (incl. the Branch C `effective_timeouts` line) is well-formed and codex returns a schema-valid `TurnDecision` from it |
| 9 | `codex_live_run_events_and_clamp` | yes | yes | end-to-end: a real codex-driven turnkey run against real hardware produces well-formed `BrainEvent` rows and an invocation-level timeout/iteration proposal is visibly clamped, not passed through raw |

## Per-check detail

**2 — timeout defaults and clamp ranges.** Pure Python: load
`default_turnkey_timeout_config()` and confirm `clamp_turnkey_timeout_value`
actually rejects/clips out-of-range values rather than passing them
through. No hardware, no model.

**3 — timeout-admin tool hidden from the model.** Confirms
`_brain_sync_timeouts` is absent from both `AllowedServerToolName` and
`decision_schema_text()` — the model never sees the timeout-sync tool name
or shape, even though it is registered as a real MCP tool the brain calls
directly.

**4 — no overreach.** Greps `brain/events.py`, `brain/timeout_policy.py`,
and `timeouts.py` for batch-execution / client-action / checkpoint /
inspector symbols. A hit means a later branch's ownership leaked into
Branch C's files.

**5 — clamp + partial update, two sub-cases:**
- *Not yet connected:* an out-of-range proposal (`connect_seconds=99999`,
  `flash_seconds=1`) gets clamped to the configured min/max, the derived
  server-sync update contains only the server-side fields tied to the
  *changed* turnkey fields (proving "partial," not a full rewrite), and
  `requested_max_iterations=999` against `operator_max_iters=12` still
  yields `effective_max_iters=12` — the model proposes, the brain's
  operator cap wins.
- *Already connected:* the same proposal must come back with
  `server_sync_apply_now=False` — the policy itself defers the sync rather
  than promising to touch a live session.

**7 — live non-mutation proof (the one claim that is meaningless without
hardware).** Opens a real `LocalMCPClient` session against the attached
board, reads a core register to prove the session is alive, calls
`_brain_sync_timeouts` with a new value, reads the same register again to
prove the *open* session kept working unaffected, then disconnects. This
only proves the server didn't disrupt the live session — it does **not**
prove the new value takes effect on the next connect's literal pyOCD
timeout behavior, since forcing a real timeout would require deliberately
hanging the board. That residual is explicitly accepted in the spec
("bounded outer waits are still not true cancellation ... a killable
worker/job layer remains out of scope for this branch").

**8 — codex dry run of the real prompt.** Builds the literal prompt text
`provider_codex_cli` would send (via the same internal
`_build_instructions` / `_build_turn_prompt` / `_compose_prompt` functions
the live loop uses — not a hand-written stand-in), pipes it to `codex exec`
for the real board config (no hardware touched, since this only loads the
board's YAML facts), and parses the response as a schema-valid
`TurnDecision`. Confirms the rendered `effective_timeouts=...` line is
present and matches `timeouts.py`'s real defaults.

**9 — full codex-driven live run.** Calls `run_freeform_task(...,
provider="codex-cli", board_id=<board>, timeout_proposal=..., 
iteration_estimate=...)` in-process (the same function the CLI's `run`
subcommand calls) with an out-of-range invocation-level proposal, a task
that tells the model to connect, read board info, and finalize
`unresolved`. After the run: every row in
`run_root/logs/brain_events.jsonl` has a valid `event_kind` from
`EVENT_KINDS`; at least one `connect`/`tool_complete`-shaped event proves
real hardware was touched; and `run-metadata/turnkey_state.json`'s
`effective_timeout_config` reflects the *clamped* value, never the raw
99999/1-second request.

## Known limitations (won't be fixed by this harness)

- No check forces a literal hardware hang to prove a timeout actually
  fires — accepted residual per the spec (killable-worker enforcement is
  explicitly out of scope for Branch C).
- Check 9 exercises the *invocation*-level proposal path
  (`proposal_source="invocation"`) deterministically; it does not force
  codex to emit its own mid-run `timeout_proposal` in a `TurnDecision`,
  since that is optional model behavior and not reliably reproducible.
