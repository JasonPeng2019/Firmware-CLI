> STATUS: EXECUTED - current Wave 1 A/B/C merge-back validation ledger.

# P-Wave A/B/C Merge Validation Spec

## Goal in plain English

Task: Merge P-Wave-C into P-Wave-A and validate combined Branch A/B/C product surface
Roadmap anchor: `R12` prototype Wave 1 merge-back from
`markdowns/R12_P_SPLIT.md`.

Create the current Wave 1 integration state by preserving the `P-Wave-A`
spine, which already includes Branch A and Branch B, then merging in
`P-Wave-C` event-spine / timeout-policy work. The result should keep the
combined product behavior coherent: provider session and tool-schema prompting,
governed batches and client actions, normalized events, timeout proposals,
timeout clamps, timeout propagation, and brain-only server timeout sync must
all work together.

## Scope and non-scope

In scope:

- Inventory `P-Wave-A` versus `P-Wave-C` before merging.
- Keep `P-Wave-A` as the target/spine branch.
- Merge or selectively transplant Branch C implementation and docs:
  - `brain/events.py`
  - `brain/timeout_policy.py`
  - `brain/timeout_runtime.py`
  - `timeouts.py`
  - Branch C state and loop/server/client hooks
  - Branch C harness/tests/docs
- Preserve Branch A behavior:
  - provider session state / resume handles
  - compact local memory and provider progress events
  - model-facing tool schema bundle from live MCP metadata
  - strict labeling of recovery-created provider sessions
- Preserve Branch B behavior:
  - action policy boundary
  - ordered `action_batch`
  - bounded `wait`
  - UART `write_serial`
  - session-scoped client actions and governed `run_script`
- Run a combined A/B/C test suite with:
  - unit/lint/type checks
  - branch-specific focused tests
  - non-hardware harness checks
  - local deployed CLI/provider smokes with `codex-cli` and `claude-cli`
    where the installed/authenticated provider CLIs allow it
  - live hardware checks when the required board/provider environment is
    currently available
- Use `firmcli-fix-bug` style loops for every reproducible bug exposed by the
  merge or suite, then rerun the failing check and the suite from scratch.

Out of scope:

- Changing settled build-plan decisions.
- Implementing Wave 2 items: progress UI/inspector beyond existing event
  records, stream checkpoints, scoped green approval, cache-assisted reuse.
- Implementing a killable pyOCD/vendor worker layer; Branch C only stages and
  propagates bounded timeout policy.
- Claiming official `nrf52833dk`, API-provider, macOS, fresh-host, or full
  deployment closure unless those exact checks run successfully in this
  session.
- Replacing the CLI-provider bridge with future Codex/Claude SDK/app-server
  integrations.

## Reconciliation summary

- Build plan: `R12` Wave 1 requires Branch A, Branch B, and Branch C to merge
  back into Wave 0 before Wave 2 begins. The Stage 5 prototype target includes
  provider continuity, real tool schemas, batched actions, bounded waits,
  client actions, structured brain events, and model-refined timeout budgets
  inside hard caps.
- Current code on `P-Wave-A`: Branch A and Branch B are implemented together.
  The active docs still describe Branch C as unimplemented on this branch.
- Source code on `P-Wave-C`: Branch C is implemented and tested for event
  spine, timeout policy, hidden `_brain_sync_timeouts`, and provider-neutral
  Branch C harness coverage on the then-attached Windows boards.
- Other docs: `current-progress.md`, `r12-branch-a-live-provider-status.md`,
  and `r12-branch-b-status.md` define the A/B proof boundary. Branch C docs on
  `P-Wave-C` define the C proof boundary.
- Disagreements: active `P-Wave-A` docs say Branch C is still missing. After a
  successful merge, that statement becomes stale and must be updated. Existing
  historical run IDs are not automatically current proof unless the artifacts
  exist and are reinspected or the checks are rerun.

## Design

Use the normal git merge result where the two branches compose cleanly. For any
conflict, classify it by ownership:

- Branch A wins provider-session semantics and schema bundle behavior.
- Branch B wins action execution, batches, wait, UART write, and client action
  behavior.
- Branch C wins event taxonomy, timeout policy, effective timeout state, and
  hidden server-timeout sync behavior.
- Shared files such as `brain/loop.py`, `brain/actions.py`, `brain/cli.py`,
  `brain/state.py`, `brain/mcp_client.py`, `server.py`, and `timeouts.py` must
  preserve all three branches' hooks in one coherent path rather than carrying
  duplicate parallel implementations.

## Board-facts-as-data and origin tags

No new board facts should be introduced by this merge. Board selection remains
by `board_id`, board config, discovery, and optional `--port`. Timeout values
remain `PROJECT-DEFINED` policy values in `timeouts.py`.

## Documentation plan

- Update `markdowns/R12_P_SPLIT.md` so Branch C is no longer described as
  unimplemented after the merge.
- Keep `markdowns/current-progress.md` honest about exactly what was rerun in
  this combined branch versus historical proof from A/B/C source branches.
- Add or update a review document at
  `markdowns/curr/p-wave-abc-merge-validation_review.md`.
- Do not leave active docs with contradictory A/B/C status.

## Portability

The merge must preserve the repo's Windows/macOS post-bootstrap contract:
`pathlib`/Python APIs, list-style subprocess calls, UTF-8-with-replacement
capture where applicable, provider executable detection through public seams,
and no machine-local path/port/probe literals.

## Verification plan

Inventory before merge:

```bash
git merge-base P-Wave-A P-Wave-C
git log --oneline <merge-base>..P-Wave-A
git log --oneline <merge-base>..P-Wave-C
git diff --name-only <merge-base>..P-Wave-A
git diff --name-only <merge-base>..P-Wave-C
```

After merge, run the combined non-hardware ladder:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run pytest -q tests/test_r11_benchmark.py
uv run python -m tests.harness.r11_benchmark --help
```

Run focused A/B/C checks as present in the merged tree:

```bash
uv run pytest -q tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py tests/test_p0_foundation.py
uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py
uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk --skip-hardware --skip-providers --fail-on-skip
```

Run lightweight provider/deployed-path smoke if CLIs are available and
authenticated:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 4 --task "Connect to the board by board_id, read board info, then finalize without flashing or editing files."
uv run pyocd-debug-brain run --provider claude-cli --board-id nucleo_l476rg --max-iters 4 --task "Connect to the board by board_id, read board info, then finalize without flashing or editing files."
```

Run hardware/provider checks only when the required board is attached and the
operator has authorized the board use. Do not claim them otherwise.

## Acceptance criteria

- `P-Wave-C` is merged into `P-Wave-A` without losing Branch A or Branch B
  behavior.
- The model-facing tool schema bundle still excludes internal brain/admin
  tools, including `_brain_sync_timeouts`.
- Ordered batches, `wait`, UART write, and governed `run_script` still parse,
  execute, and record results.
- Provider session/resume state and compact local memory still persist through
  provider turns.
- Branch C timeout proposals clamp inside hard caps, update effective timeout
  state, and emit event records.
- Hidden server timeout sync remains brain-only and partial.
- The combined suite is green up to the current hardware/provider boundary.
- Every reproducible bug found by the suite is fixed with a regression guard
  and the relevant tests are rerun from scratch.

## Verified

- Merge inventory ran with `merge-conflicting-repos` helper scripts:
  - `compare_refs.py --left P-Wave-A --right P-Wave-C`
  - `merge_probe.py --target P-Wave-A --other P-Wave-C`
- `P-Wave-C` was selectively merged onto the `P-Wave-A` spine. The merge keeps
  Branch A provider/session/schema behavior, Branch B batch/wait/UART/client
  action behavior, and Branch C event/timeout/server-sync behavior.
- Combined non-hardware checks passed:
  - `uv run pytest -q tests/test_r12_turnkey.py tests/test_r12_turnkey_merge.py tests/test_branch_c_harness.py tests/test_timeout_policy.py tests/test_p0_foundation.py`
    -> `121 passed`
  - `uv run python tests/harness/branch_c_tests.py --board-id nrf52840dk --skip-hardware --skip-providers --fail-on-skip`
    -> `4 passed, 0 failed, 0 skipped`
  - `uv run ruff check .` -> passed
  - `uv run pytest -q` -> `337 passed` before the harness regression and
    `338 passed` after it
  - `uv run mypy src` -> passed
  - `uv run pytest -q tests/test_r11_benchmark.py` -> `34 passed`
  - `uv run python -m tests.harness.r11_benchmark --help` -> passed
- Python-change gate after the harness fix:
  - `uv run ruff check --fix .` -> passed
  - `uv run ruff format .` -> passed
  - `uv run pyright --outputjson` -> repo-wide baseline failure with `95`
    diagnostics; changed-file filter for the merge/harness files reported `0`
  - `uv run pytest -q` -> `338 passed`
- Live hardware substrate checks passed:
  - `host_bootstrap.py`, `stage0_check.py`, and `tests.harness.stage1_smoke`
    on `nucleo_l476rg`
  - `host_bootstrap.py`, `stage0_check.py --recover-test`, and
    `tests.harness.stage1_smoke` on `nrf52840dk`
- Branch C live provider/hardware harness passed on both attached boards and
  both local CLI providers:
  - `nucleo_l476rg`: `codex-cli` run root
    `runs/20260630T035533Z-13eb8716`, `claude-cli` run root
    `runs/20260630T035604Z-1cab4775`
  - `nrf52840dk`: `codex-cli` run root
    `runs/20260630T035749Z-166e2f98`, `claude-cli` run root
    `runs/20260630T035823Z-4733fa03`
- Explicit two-turn deployed CLI smokes passed on both attached boards and
  both providers using turn 1 `action_batch(connect, get_board_info)` and turn
  2 standalone `finalize`:
  - `runs/20260630T035908Z-792e4e13`
  - `runs/20260630T035938Z-d595f811`
  - `runs/20260630T040008Z-8a79ddbf`
  - `runs/20260630T040034Z-b497ea08`
- A Branch C harness false negative was fixed after the first Nucleo Codex
  run. Codex did reach hardware after recovering from an unsupported batched
  `finalize`, but the harness only accepted per-tool `tool_complete` event
  evidence. It now also accepts `TurnkeyRunResult.mcp_tools_used`, with a
  focused regression test.
- Process/session audits after live provider and hardware smokes found no
  leftover spawned provider, MCP, pyOCD, serial, or Python child processes.

## Remaining gaps

- Exact official `nrf52833dk` proof was not run in this session because the
  attached Nordic board identifies as `nrf52840`.
- API-provider parity, fresh Windows/macOS host proof, and future
  SDK/app-server provider integrations remain deferred.
- Literal killable pyOCD/vendor-worker cancellation is not part of Branch C;
  Branch C provides bounded outer waits, timeout policy, and server timeout
  propagation only.
