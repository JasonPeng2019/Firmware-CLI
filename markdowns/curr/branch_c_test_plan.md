# Branch C Test Plan - Event Spine + Timeout Policy

## Scope

Validates the `P-Wave-C` implementation against its written spec in
`markdowns/R12_P_SPLIT.md` ("Branch C - Event Spine + Timeout Policy"). Branch C
owns four things:

1. `brain/events.py` - the canonical `BrainEvent` taxonomy plus sink/fanout
   helpers.
2. `brain/timeout_policy.py` - parses model timeout/iteration proposals,
   applies brain-owned clamps, builds partial server timeout-sync requests.
3. `src/pyocd_debug_mcp/timeouts.py` - single source of truth for timeout
   defaults and clamp ranges, plus session/client-scoped effective timeout
   state.
4. The timeout-consumption hooks - providers consume `provider_seconds`, tool
   calls consume action timeouts, server sync applies partial updates only to
   future connects.

Branch C must not own: batch execution semantics, client-action execution,
checkpoint continue/cancel decisions, inspector UI, provider adapter rewrites
beyond the stable timeout-consumption hook, or a model-facing timeout-admin
tool.

## Harness

`tests/harness/branch_c_tests.py`. Default development run:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk
```

Each check prints `PASS` / `FAIL` / `SKIP` with a one-line reason. The process
exit code is non-zero if any check fails. By default, `SKIP` is allowed for
missing hardware or unavailable/unauthenticated provider CLIs because those are
environment preconditions, not necessarily Branch C defects.

For acceptance, use `--fail-on-skip` so every selected check must run:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --fail-on-skip
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --fail-on-skip
```

For non-hardware-only validation while boards are busy, intentionally skip the
hardware checks while still running the selected provider dry-run checks:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip
```

## Preconditions

- The board under test is plugged in and idle for hardware runs. `nrf52840dk`
  is the harness default because it has retained alternate-board proof in
  `markdowns/current-progress.md`; official Branch C merge proof should still
  use the scoped pair `nrf52833dk + nucleo_l476rg` unless the user explicitly
  accepts retained-board proof instead.
- `codex` and `claude` CLIs must be installed and authenticated for checks that
  drive real model turns. In development mode those checks may `SKIP`; in
  acceptance mode `--fail-on-skip` makes that pending proof visible.
- The repo's non-hardware ladder (`uv run pytest -q`, `uv run ruff check .`,
  `uv run mypy src`) should be green before trusting the hardware-aware harness.

## Check matrix

| # | Name | Needs HW | Needs provider CLI | Spec clause it proves |
|---|------|----------|-------------|------------------------|
| 1 | `probe_visible` | yes | no | precondition only; gates the rest |
| 2 | `timeout_defaults_and_clamp_ranges` | no | no | `timeouts.py` is the single source of truth for defaults/clamp ranges |
| 3 | `timeout_admin_not_model_facing` | no | no | timeout sync remains brain-only/internal and absent from model-facing schema |
| 4 | `no_overreach_into_other_branches` | no | no | Branch C does not absorb batch/client-action/checkpoint/inspector ownership |
| 5 | `policy_clamps_and_partial_update` | no | no | policy clamps proposals, derives partial server updates, and preserves the operator iteration cap |
| 6 | `stage0_bringup` | yes | no | precondition; board is real and alive before hardware-touching checks |
| 7 | `live_sync_does_not_mutate_open_session` | yes | no | sync does not disrupt an already-open live session |
| 8 | `provider_dry_run_prompt_render[provider]` | no | yes | real rendered prompt includes `effective_timeouts` and the selected provider returns a schema-valid `TurnDecision` |
| 9 | `provider_live_run_events_and_clamp[provider]` | yes | yes | real selected provider + hardware run emits valid events and clamps invocation timeout/iteration proposals |

## Per-check detail

**2 - timeout defaults and clamp ranges.** Pure Python: load
`default_turnkey_timeout_config()` and confirm `clamp_turnkey_timeout_value`
clips out-of-range values rather than passing them through.

**3 - timeout-admin tool hidden from the model.** Confirms
`_brain_sync_timeouts` is absent from both `AllowedServerToolName` and
`decision_schema_text()`, even though it is registered as a real MCP tool the
brain can call directly.

**4 - no overreach.** Greps `brain/events.py`, `brain/timeout_policy.py`, and
`timeouts.py` for batch-execution, client-action, checkpoint, and inspector
symbols. A hit means a later branch's ownership leaked into Branch C's files.

**5 - clamp + partial update.** Uses an out-of-range proposal
(`connect_seconds=99999`, `flash_seconds=1`) and
`requested_max_iterations=999` against `operator_max_iters=12`. The expected
result is clamped timeout values, `effective_max_iters=12`, a partial server
update tied only to changed turnkey fields, and deferred sync while connected.

**7 - live non-mutation proof.** Opens a real `LocalMCPClient` session against
the attached board, halts the core, reads `pc`, calls `_brain_sync_timeouts`,
reads `pc` again, then disconnects. This proves the open halted session was not
disrupted. It does not prove literal timeout firing under a deliberately hung
board; killable worker enforcement is outside Branch C.

**8 - Provider dry run of the real prompt.** Builds the same prompt text the
live provider uses, sends it through the selected provider factory, and parses
the response as a schema-valid `TurnDecision`. This touches board config only,
not hardware.

**9 - full provider-driven live run.** Calls `run_freeform_task(...)`
in-process with an out-of-range invocation-level timeout proposal and iteration
estimate. The task asks the selected provider to connect, read board info, and
finalize with a schema-valid `tooling_failure` classification. After the run,
every `brain_events` row must use a valid `EVENT_KINDS` value, hardware must
have been touched through `connect` / `get_board_info`, and the final state
must contain clamped effective timeout values rather than raw out-of-range
requests.

## Known limitations

- No check forces a literal hardware hang to prove a timeout actually fires.
  That residual is accepted by the Branch C spec because true cancellation of
  in-process pyOCD/vendor calls needs a future killable worker/job layer.
- Check 9 exercises the invocation-level proposal path deterministically. It
  does not force Codex to emit its own mid-run `timeout_proposal`, since that is
  optional model behavior and not reliably reproducible.

## Verified

- Provider-neutral Branch C validation was rerun on Windows on June 29, 2026.
- The full non-hardware ladder returned green after provider-neutral harness
  changes: `uv run pytest -q` returned `289 passed`, `uv run ruff check .`
  passed, and `uv run mypy src` passed.
- Non-hardware provider matrix with `codex-cli` and `claude-cli` returned
  `6 passed, 0 failed, 0 skipped` for both:
  - `uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip`
  - `uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip`
- Full Branch C hardware/provider acceptance on `nucleo_l476rg` returned
  `11 passed, 0 failed, 0 skipped`, including Codex and Claude provider live
  runs. Run roots:
  `runs/20260629T214134Z-58c1405a` and
  `runs/20260629T214212Z-19199e0e`.
- Full Branch C hardware/provider acceptance on retained `nrf52840dk` returned
  `11 passed, 0 failed, 0 skipped`, including Codex and Claude provider live
  runs. Run roots:
  `runs/20260630T012135Z-8a5780dc` and
  `runs/20260630T012206Z-292bb340`.
- Public deployed CLI smoke passed for both providers on both attached boards:
  - `codex-cli` + `nucleo_l476rg`: `runs/20260630T011733Z-ae2eb3ee`
  - `claude-cli` + `nucleo_l476rg`: `runs/20260630T011814Z-4c33bc87`
  - `codex-cli` + `nrf52840dk`: `runs/20260630T011858Z-f269f813`
  - `claude-cli` + `nrf52840dk`: `runs/20260630T011944Z-7b9c4186`
- Non-hardware harness mode was run with:
  `uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --skip-hardware --skip-codex`
  and returned `4 passed, 0 failed, 0 skipped`.
- Targeted unit tests for the Branch C harness and timeout policy were rerun
  after the live-sync halt fix with:
  `uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py`
  and returned `10 passed`.
- Full non-hardware unit/lint/type checks were rerun after restoration on
  June 29, 2026:
  `uv run pytest -q` returned `285 passed`, `uv run ruff check .` passed, and
  `uv run mypy src` passed.
- Full non-hardware unit/lint/type checks were rerun again after the live-sync
  halt fix on June 29, 2026:
  `uv run pytest -q` returned `286 passed`, `uv run ruff check .` passed, and
  `uv run mypy src` passed.
- Both official-board Branch C skip-hardware/no-Codex harness commands were
  rerun and returned `4 passed, 0 failed, 0 skipped`.
- Codex dry-run prompt rendering was run without hardware for both official
  board IDs:
  - `uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --skip-hardware`
  - `uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --skip-hardware`
  Both returned `5 passed, 0 failed, 1 skipped`; the skipped check was the live
  Codex-plus-hardware run.
- Full Branch C hardware acceptance on the attached STM32 board was rerun with:
  `uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --fail-on-skip`
  and returned `9 passed, 0 failed, 0 skipped`; run root
  `runs/20260629T203611Z-88e44520`.
- Full Branch C hardware acceptance on the attached retained Nordic board was
  rerun with:
  `uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk --fail-on-skip`
  and returned `9 passed, 0 failed, 0 skipped`; run root
  `runs/20260629T203830Z-1b95fee0`.
- Official `nrf52833dk` proof was attempted with:
  `uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --fail-on-skip`
  and did not reach Branch C hardware checks because Stage 0 reported
  `FICR.INFO.PART actual=0x52840, expected=0x52833`. The attached Nordic board
  is therefore not the official `nrf52833dk` for this proof.

## Pending verification

- Full `--fail-on-skip` Branch C harness run on the official `nrf52833dk`.
  The attached Nordic board currently reports nRF52840 silicon, so this remains
  blocked until an actual `nrf52833dk` is attached or the proof boundary is
  explicitly changed to retained `nrf52840dk`.
- macOS/fresh-host provider matrix remains pending; this pass proves the
  Windows host only.
