> STATUS: PROPOSAL - not authority. This spec governs only the local merge
> pass of `origin/P-Wave-B` into `P-Wave-A`; it does not change the settled
> build-plan decisions.

# Branch A/B Additive Merge

## Goal in plain English

Task: Merge `origin/P-Wave-B` into `P-Wave-A` while preserving Branch A
provider resume guarantees and carrying Branch B action/task additions.

Roadmap anchor: `R12` prototype Wave 1 merge-back, specifically Branch A
provider session/tool schema work plus Branch B action boundary/client action
work from `markdowns/R12_P_SPLIT.md`.

## Scope and non-scope

In scope:

- Undo the previous partial/failed B-into-A merge and rebuild the merge from a
  clean `P-Wave-A` spine.
- Preserve Branch A's provider contract:
  `ProviderPromptBundle`, `ProviderSessionState`, native provider resume
  handles, typed resume failure records, fail-closed headless behavior, and
  labeled explicit recovery sessions.
- Port Branch B's additive behavior onto that provider contract:
  CLI task input helpers, model-visible client action registry, action policy,
  action batches, `wait`, `run_script`, and UART write support.
- Resolve overlapping docs so active docs do not claim Branch A is still
  unimplemented after Branch A has landed.
- Keep B's useful validation/docs about official-scope Branch B gaps and
  portability proof where they remain true.
- Update tests so Branch B coverage uses Branch A's provider-bundle API instead
  of the older `next_decision(instructions, turn_prompt)` shape.

Out of scope:

- Replacing Branch A's provider architecture with Branch B's older prompt-only
  provider call shape.
- Treating `anthropic-api` as a real provider-session resume path before an
  external resumable handle exists.
- Claiming new hardware/live-provider proof unless the commands are run against
  real boards/providers in this session.
- Closing Branch C/D/E/F/G prototype work.

## Reconciliation summary

- Build plan: `R12` now explicitly wants persistent provider sessions, real
  tool schemas, batched board decisions, `wait`, UART write, client actions,
  bounded paths, and visible/labeled recovery. Failed real-session resume must
  fail closed unless the operator explicitly chooses recovery.
- Current `P-Wave-A` code: owns the provider/session continuity contract,
  strict resume failure artifacts, recovery labeling, and the current
  `ProviderPromptBundle` provider interface.
- `origin/P-Wave-B` code: owns the action/client-action/task-input expansion
  and adds UART write capability through the adapter/service/server layers.
- Disagreements: B's overlapping brain files were written against the older
  provider call shape and some B docs still describe Branch A as pending. Per
  the authority order and build plan, Branch A's real-session contract wins;
  B's behavior is transplanted into that contract rather than replacing it.

## Design

- `src/pyocd_debug_mcp/brain/loop.py` remains Branch A's orchestration spine.
  B's additional action types and client-action prompt sections are integrated
  into the existing prompt bundle and turn execution path.
- `src/pyocd_debug_mcp/brain/app.py` and `brain/cli.py` route both Branch A
  provider recovery handling and Branch B client-action/task-input arguments.
- `src/pyocd_debug_mcp/server.py`, UART adapters/services, and MCP client
  additions from B are kept where they are additive and already sit in the
  correct lower layers.
- Tests that fake providers must implement the Branch A provider interface and
  inspect `prompt_bundle.turn_context_text` instead of a raw prompt string.
- Active docs must describe A+B as additive. Historical B process/review docs
  may be archived under `markdowns/tmp/` if they are useful but no longer
  active truth.

## Board-facts-as-data and origin tags

- No new board facts, ports, targets, baud rates, or probe identifiers are
  introduced by this merge.
- Existing B UART write support must keep board and serial details flowing
  through board config / local resolution, not hardcoded paths or ports.
- Timeout and action-policy constants are project-defined behavior; preserve
  existing origin-tag style where non-obvious constants are introduced.

## Documentation plan

- Update `README.md`, `markdowns/R12_P_SPLIT.md`,
  `markdowns/current-progress.md`, and `markdowns/repo_file_index.md` only as
  needed to remove contradictory active status and include the merged action
  surface.
- Keep B's current-status docs only if they are clearly labeled as status or
  archived history and do not override the build plan.
- Update MCP tool docstrings in `server.py` for any changed UART write tool
  behavior. Do not create a sidecar tool doc.

## Portability

- Preserve B's task-file/task-stdin path because it avoids Windows command-line
  length problems and keeps long prompts portable.
- Preserve subprocess and path handling through existing helpers and `pathlib`.
- Do not introduce machine-specific defaults. Real board/provider proofs remain
  pending unless rerun in this session.

## Verification plan

- Static/import sanity through the default ladder.
- Targeted non-hardware tests:
  - `tests/test_r12_turnkey.py`
  - `tests/test_ux_cli.py`
  - `tests/test_server_runtime_tools.py`
  - `tests/test_uart_capture.py`
  - `tests/test_p0_foundation.py`
  - Branch A provider resume tests, including artifact assertions.
- Full non-hardware ladder:
  `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
- Run broader suite/ladders as practical after targeted green. Hardware/live
  provider proof is not claimed unless executed on attached boards/providers.

## Acceptance criteria

- `git merge origin/P-Wave-B` is resolved with no conflict markers and a clean
  worktree after commit.
- Branch A provider resume/fail-closed semantics still pass their tests.
- Branch B action/task/client additions are present, wired through CLI/app/loop,
  and covered by tests.
- Active docs do not contradict the chosen merge ownership.
- The non-hardware validation surface is green.
- `P-Wave-A` is pushed after a successful merge commit.

## Verified

- `P-Wave-A` was clean before the merge pass.
- Scratch merge probe shows conflicts limited to README, R12 split docs,
  `brain/app.py`, `brain/cli.py`, `brain/loop.py`, and two tests.
- Ref comparison shows A-only provider/session files and B-only
  action/task/UART additions, with overlap in the integration seam.

## Pending verification

- Conflict resolution against the real merge worktree.
- Targeted tests and default validation ladder after resolution.
- Hardware/live-provider proof for any behavior that requires attached boards
  or real remote providers.
