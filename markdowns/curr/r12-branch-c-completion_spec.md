> STATUS: IMPLEMENTED FOR CURRENT WINDOWS ATTACHED-BOARD SCOPE. Official `nrf52833dk` and macOS/fresh-host proof remain pending.

# R12 Branch C Completion Spec

## Goal in plain English

Complete `P-Wave-C`, the R12 prototype Wave 1 branch for the event spine and
timeout policy, so it is ready to merge back into Wave 0.

Branch C is done when the turnkey brain can prove, in the real deployed shape,
that one brain/client run owns its own effective timeout state, emits normalized
brain events, lets the model propose timeout and iteration budgets, clamps those
budgets in the brain, and applies only hidden partial server timeout sync for
future operations.

Roadmap anchor: `R12` / Stage 5 product #2 prototype increment, specifically
Wave 1 Branch C from `markdowns/R12_P_SPLIT.md`. The broader gate is `G7`, but
this spec closes only Branch C. It does not close full R12.

## Scope and non-scope

In scope:

- Finish and verify the Branch C-owned event contract in
  `src/pyocd_debug_mcp/brain/events.py`.
- Finish and verify the Branch C-owned timeout policy in
  `src/pyocd_debug_mcp/brain/timeout_policy.py`.
- Keep timeout defaults, clamp ranges, server timeout updates, and timeout
  serialization centralized in `src/pyocd_debug_mcp/timeouts.py`.
- Keep effective timeout state, effective iteration budget, pending server sync,
  and last policy result scoped to the current turnkey brain/client run through
  `BrainState`, not persistent global product state.
- Parse invocation-level and turn-level `timeout_proposal` and
  `iteration_estimate` values, clamp them inside brain-owned hard caps, and
  record the requested and applied values.
- Consume effective timeout values at the provider, MCP startup, server-tool,
  build/external command, and UART-read call sites that already exist in the
  Branch C integration surface.
- Keep `_brain_sync_timeouts` brain-only/internal. It may exist as a local MCP
  tool callable by the brain client, but it must not appear in
  `AllowedServerToolName`, `decision_schema_text()`, or any curated
  model-facing tool schema bundle.
- Ensure server timeout sync is a partial update for subsequent operations only.
  It must not mutate config files and must not promise to interrupt in-flight
  pyOCD or vendor calls.
- Harden the Branch C harness so it can be used as real acceptance evidence
  rather than only as a loose smoke script.

Out of scope:

- Branch A provider-session continuity and real tool schema prompt forwarding.
- Branch B action boundary work: batches, `wait`, UART write, client actions,
  and model-native host work.
- Branch D progress rendering and developer inspector UI.
- Branch E stream checkpoint continue/cancel decisions.
- Branch F scoped green approval.
- Provider-native tool-call conversion.
- A killable worker/job layer for pyOCD or vendor calls.
- A model-facing timeout administration tool.
- Fresh-machine Windows/macOS portability closure or full second-provider R12
  parity. Those are broader R12 proof items, not this narrow Branch C completion
  gate.

## Reconciliation summary

- Build plan: `firmware_agent_build_plan_concrete (10).md` says the current R12
  prototype must harden blocking paths, let the model refine timeout and
  iteration budgets inside brain caps, and sync allowed timeout changes to the
  server as partial updates for later operations.
- Current code: Branch C implementation is present in `brain/events.py`,
  `brain/timeout_policy.py`, `brain/timeout_runtime.py`, `timeouts.py`,
  `BrainState` timeout fields, provider/tool timeout consumption hooks in
  `brain/loop.py`, hidden `_brain_sync_timeouts` in `server.py`, and
  `LocalMCPClient.sync_timeouts(...)`.
- Other docs: `markdowns/R12_P_SPLIT.md` defines Branch C ownership and
  non-ownership. `markdowns/curr/branch_c_test_plan.md` defines a Branch C
  harness. `markdowns/current-progress.md` must be kept honest about what was
  verified on the current checkout.
- DEFECT FIXED BY THIS PASS: `tests/harness/branch_c_tests.py` previously asked
  the live Codex run to finalize with `classification=other`, which is not a
  schema-valid classification. The harness must use a schema-valid value such
  as `tooling_failure`.
- DEFECT FIXED BY THIS PASS: `check_probe_visible` previously treated any
  nonzero `pyocd list` return code as no probe. On Windows, pyOCD can print a
  usable probe table while returning nonzero because of console encoding. The
  harness must use the shared probe inventory path.
- DEFECT FIXED BY THIS PASS: hardware acceptance must not count `SKIP` as
  success. `SKIP` is acceptable for local development when hardware or Codex
  auth is absent, but Branch C completion must use `--fail-on-skip` or remain
  explicitly pending.
- RESOLUTION: local CLI provider coverage for `codex-cli` and `claude-cli` was
  closed by the follow-on provider-portability pass for the current Windows
  host and attached `nucleo_l476rg` + retained `nrf52840dk` boards. macOS,
  fresh-host, live API-provider, and official `nrf52833dk` proof remain outside
  the completed evidence boundary.

## Design

The implementation should be a finishing pass over existing Branch C modules,
not a broad orchestration rewrite.

`BrainEvent` stays the canonical normalized event record. Event kinds must be
JSONL-safe and stable enough for later Branch D progress/inspector work.

`TimeoutProposal` and `IterationEstimate` remain model-proposed inputs. The
brain applies clamp ranges from `timeouts.py`, records what changed, records
what was clamped, enforces the operator `--max-iters` cap, and keeps the
absolute iteration ceiling in policy code as a project-defined cap.

`BrainState.effective_timeout_config`, `BrainState.effective_max_iters`,
`BrainState.pending_server_timeout_sync`, and `BrainState.last_timeout_policy`
are the run/session state that should appear in turnkey artifacts. They must
not be moved into process-global brain state.

`_brain_sync_timeouts` accepts only partial low-level server timeout updates.
It returns machine-readable status for the brain, but the model must not see it
as an allowed server-native action.

Verification must be deployment-shaped: unit tests, the Branch C harness, real
Codex CLI prompt rendering, a real local stdio MCP client/server, and real
attached boards. Pure unit tests are necessary but not sufficient for Branch C
completion.

## Board-facts-as-data and origin tags

No new board-specific facts should be added by Branch C. Timeout values and
iteration caps are product policy values, not board facts.

- Timeout defaults and clamp ranges in `timeouts.py` are `PROJECT-DEFINED`
  values.
- pyOCD option names in `ServerTimeoutConfig.pyocd_options()` are
  `VENDOR-FIXED` API/option names.
- Board identity, target names, serial ports, baud rates, probe family, and
  reference firmware paths must continue to come from board config, local
  overrides, discovery, or command-line flags.
- Harness commands must accept `--board-id` and optional `--port`; they must not
  hardcode `COMx`, `/dev/...`, probe UIDs, or machine-local paths.

## Documentation plan

- Keep `markdowns/R12_P_SPLIT.md` aligned with Branch C's verified/pending
  status.
- Keep `markdowns/curr/branch_c_test_plan.md` aligned with the harness behavior,
  especially `SKIP` handling.
- Keep `markdowns/current-progress.md` honest about exact commands, board IDs,
  providers, pass/fail/SKIP matrix, and pending proof.
- If `_brain_sync_timeouts` behavior or arguments change, update its MCP
  docstring in `src/pyocd_debug_mcp/server.py`.
- Do not update `firmware_agent_build_plan_concrete (10).md` unless completing
  Branch C requires changing a settled decision.

## Portability

Branch C must preserve the repo's post-bootstrap portability contract:

- Use `pathlib`, Python APIs, and repo scripts; do not add OS-specific shell
  syntax to product code.
- Prefer shared probe inventory over parsing pyOCD console tables directly.
- Subprocess capture must use UTF-8 with replacement or an equivalent robust
  decode path.
- Board and serial selection must be by `board_id`, config, discovery, optional
  `--port`, or local override.
- Real provider validation should distinguish missing CLI/auth from product
  defects, but acceptance must not turn skipped required checks into green.

## Verification plan

Non-hardware:

```bash
uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --skip-hardware --skip-codex
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --skip-hardware --skip-codex
```

CLI provider dry-run prompt checks, if provider CLIs are installed and
authenticated:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip
```

Full hardware acceptance:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --fail-on-skip
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --fail-on-skip
```

## Acceptance criteria

- Branch C behavior preserves current turnkey behavior when no timeout proposal
  or iteration estimate is provided.
- Invocation-level and turn-level proposals are clamped and recorded.
- Provider calls consume the current `provider_seconds` value.
- MCP startup and server-tool calls consume appropriate effective timeout
  values.
- `_brain_sync_timeouts` remains brain-only/internal and absent from
  model-facing actions/schema text.
- Server timeout sync applies only named low-level fields and does not rewrite
  config files.
- Completion proof treats required `SKIP` checks as pending, not success.
- Non-hardware checks pass.
- Real stdio MCP client/server checks pass on each board claimed.
- Real Codex CLI deployment-shaped checks pass on each board claimed, or remain
  explicitly pending.

## Verified

- This spec was restored after the accidental cleanup in this checkout.
- Non-hardware validation after restoration passed on June 29, 2026:
  targeted Branch C tests returned `9 passed`, full pytest returned
  `285 passed`, full ruff passed, full mypy passed, and both official-board
  skip-hardware/no-Codex harness runs returned `4 passed, 0 failed, 0 skipped`.
- Targeted validation after the live-sync halt fix returned `10 passed` for:
  `uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py`.
- Full non-hardware validation after the live-sync halt fix returned
  `286 passed` for `uv run pytest -q`; `uv run ruff check .` and
  `uv run mypy src` also passed.
- Full Branch C hardware acceptance passed on `nucleo_l476rg` with
  `9 passed, 0 failed, 0 skipped`; run root
  `runs/20260629T203611Z-88e44520`.
- Full Branch C hardware acceptance passed on retained `nrf52840dk` with
  `9 passed, 0 failed, 0 skipped`; run root
  `runs/20260629T203830Z-1b95fee0`.
- Provider-neutral Branch C acceptance later passed on this Windows host:
  - non-hardware provider matrix for `codex-cli` and `claude-cli` returned
    `6 passed, 0 failed, 0 skipped` on both `nucleo_l476rg` and retained
    `nrf52840dk`
  - hardware/provider matrix returned `11 passed, 0 failed, 0 skipped` on
    `nucleo_l476rg`
  - hardware/provider matrix returned `11 passed, 0 failed, 0 skipped` on
    retained `nrf52840dk`
  - public deployed `pyocd-debug-brain run` smokes passed for Codex and Claude
    on both attached boards
- Official `nrf52833dk` hardware acceptance was attempted, but Stage 0 reported
  `FICR.INFO.PART actual=0x52840, expected=0x52833`, so the attached Nordic
  board is not valid official `nrf52833dk` proof.

## Pending verification

- Full `--fail-on-skip` Branch C harness remains pending on official
  `nrf52833dk` until an actual nRF52833 DK is attached or the proof boundary is
  explicitly changed to retained `nrf52840dk`.
- macOS/fresh-host provider matrix remains pending; this pass proves the
  current Windows host only.
