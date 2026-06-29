> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Branch A Strict Provider Recovery

## Goal in plain English

Task: Finish Branch A strict provider-session recovery and crash-context memory injection.
Roadmap anchor: `R12` turnkey brain, Wave 1 Branch A (`provider session + tool schema prompt`).

Branch A is mostly implemented, but it is not fully merge-clean while
real-session provider resume failures can silently start a fresh provider
session. This spec finishes the Branch A recovery contract: when a provider
handle exists and resume fails, the default behavior is fail-closed; recovery is
explicit, labeled, and driven from the brain's saved local memory.

The saved memory must be strong enough for a new provider session to continue
usefully after a crash. It should preserve the durable context an engineer
would need: session facts, turn decisions and rationale, observations, actions,
tool arguments, results, successful versus failed outcomes, codebase/workspace
summary, artifact paths, edits made, failed hypotheses, ruled-out paths,
refusals, blocks, and acceptance constraints. It must not depend on hidden model
chain-of-thought; it stores visible decision rationale and evidence.

## Scope and non-scope

In scope:

- replace silent fresh-session fallback for real-session providers:
  `openai-api` with `previous_response_id`, `codex-cli` with `thread_id`, and
  `claude-cli` with `session_id`
- add a typed provider resume failure with provider, handle kind, expected
  handle, turn index, failure text, and an explicit
  `replacement_provider_session_started=false` field
- keep new-session-from-memory as an explicit recovery path only
- label any recovery-created provider session as a new provider session in
  provider metadata, brain events, model-turn artifacts, and turnkey state
- add interactive recovery handling for `pyocd-debug`: retry resume, start new
  provider session from saved local memory, or abort
- keep `pyocd-debug-brain` headless behavior fail-closed by default
- strengthen the brain-owned memory record enough to support crash recovery:
  decision rationale, action/tool arguments, results, success/failure flags,
  codebase/workspace summary, artifact paths, edited files, failed hypotheses,
  refused/blocked paths, and verification snapshots
- update tests that currently expect permissive fallback
- add artifact assertions for strict failure and labeled recovery
- write a deployment test spec covering multiple top-level prompts, real Codex
  provider use where available, long provider loops, and simple code-writing
  repair behavior
- run the non-hardware ladder and then run the real-hardware/provider suite as
  far as this host and the attached boards allow

Out of scope:

- replacing Codex CLI with SDK/app-server thread APIs
- replacing Claude CLI with Claude Agent SDK sessions
- claiming Anthropic Messages API is a real provider-session backend
- exposing hidden model chain-of-thought or relying on it for recovery
- changing the server/MCP hardware tool surface
- adding Branch B batch/client-action behavior or Branch C timeout-policy
  behavior beyond the recovery hooks needed here

## Reconciliation summary

Build plan:

- `R12` requires persistent provider sessions where available.
- For real-session providers, failed resume is not normal continuation:
  headless runs fail closed by default, interactive runs ask before retrying or
  starting a new provider session from saved local memory, and any
  recovery-created provider session is labeled as new.
- The provider/session contract remains brain-owned and provider-specific:
  OpenAI uses Responses chaining, Codex/Claude CLI use current resume-handle
  bridges, Anthropic API stays local-primary.

Current code:

- `provider_codex_cli.py` resumes `codex exec resume <thread_id>`, but on
  resume command failure it falls back to a fresh local-memory-backed thread.
- `provider_claude_cli.py` resumes `claude --print --resume <session_id>`, but
  on resume command failure it falls back to a fresh local-memory-backed
  session.
- `provider_openai.py` passes `previous_response_id`, but provider request
  failures are not routed through a typed strict-resume failure record.
- `loop.py` catches provider failures generically and writes saved artifacts,
  but does not distinguish resume failure, recovery choice, or new-session
  labeling.
- `provider_types.py` already has provider session state and compact memory
  entries, but the memory entry is still too small for robust crash recovery.
- `ux/shell.py` runs one top-level prompt at a time but has no resume-failure
  recovery prompt.

Other docs or notes:

- `markdowns/curr/p_wave_a_chat_handoff_2026_06_28.md`,
  `markdowns/curr/r12_turnkey_spec.md`, `markdowns/R12_P_SPLIT.md`,
  `markdowns/UXLayer.md`, and `markdowns/curr/things-to-change.md` all point to
  strict provider-session recovery as the remaining Branch A gap.
- `markdowns/curr/p_wave_a_merge_benphaseb_review.md` says Branch A is clean
  for the earlier non-hardware review, but it also lists multi-prompt and live
  provider proof as unproved.

Disagreements:

- The code and older tests still encode permissive fallback. The build plan and
  active Branch A docs now require strict default behavior. Per authority
  order, the plan wins and the code/tests must change.
- No settled-decision conflict blocks this work. The stricter policy is already
  in the build plan and current R12 spec.

## Design

The change lives in the brain/provider and UX layers. It does not touch board
adapters or the MCP server tool surface.

Provider layer:

- Add a typed `ProviderResumeFailure` error in `provider_types.py`.
- Real-session providers raise that error when they have an expected provider
  handle and the provider refuses, loses, expires, or cannot resume it.
- The error record includes provider, handle kind, expected handle id, turn
  index, continuation mode/path, failure text, whether local memory is
  available, and `replacement_provider_session_started=false`.
- Providers honor an explicit recovery request stored on
  `ProviderSessionState.metadata`: `resume_recovery_action =
  "new-session-from-memory"`. In that mode they start a fresh provider session
  from the brain-rendered local memory and label the result as recovery-created.
- A retry recovery choice leaves the existing provider handle in place and
  calls the provider again.

Loop layer:

- Add a provider-resume recovery callback hook to `run_turnkey(...)`.
- If a `ProviderResumeFailure` occurs and no callback exists, fail closed with a
  tooling-failure result and persist artifacts.
- If the callback returns `retry`, re-enter the same provider turn with the same
  expected handle.
- If it returns `new-session-from-memory`, mark the session state with explicit
  recovery metadata and call the provider again. The resulting provider metadata
  and events must say this is a new provider session from saved memory, not a
  continuation of the old handle.
- If it returns `abort`, stop with a provider-session failure result.

Memory layer:

- Preserve the current compact memory model, but strengthen each entry with
  durable context fields:
  - visible decision rationale from `strategy_evaluation`
  - exact action payload / tool arguments
  - result status: success, failure, refusal, block, or unknown
  - artifact/session/workspace context
  - changed files and codebase/workspace summary where available
  - failed hypotheses and blocked/refused action families
- Keep the prompt-rendered memory compact and bounded. Exact records are
  persisted in `turnkey_state.json` / model-turn artifacts; the provider prompt
  gets concise rendered summaries.

UX layer:

- `pyocd-debug` supplies a recovery callback to the shared app/loop.
- The shell prompt is blocking and offers exactly:
  `retry resume`, `new session from saved memory`, or `abort`.
- The headless `pyocd-debug-brain` CLI does not supply the callback and
  therefore fails closed by default.

## Board-facts-as-data and origin tags

No board facts are introduced or changed.

New project-defined values:

- recovery choices: `retry`, `new-session-from-memory`, `abort`
  - `PROJECT-DEFINED`
- provider metadata keys such as `resume_recovery_action`,
  `recovery_created_new_session`, and
  `replacement_provider_session_started`
  - `PROJECT-DEFINED`
- provider resume-failure event kind / block code:
  `provider_resume_failed` / `turnkey/provider-resume-failed`
  - `PROJECT-DEFINED`

No serial ports, probe ids, pyOCD targets, baud rates, or OS-specific paths may
be added.

## Documentation plan

- Update `markdowns/curr/r12_turnkey_spec.md` in place because this is the
  current R12 contract.
- Update `markdowns/R12_P_SPLIT.md` only if the Branch A status needs sharper
  merge criteria.
- Update `markdowns/current-progress.md` after implementation and validation so
  it no longer says permissive fallback is the current behavior.
- Update `README.md` provider-continuity text if the user-facing command
  contract changes.
- Update `markdowns/curr/branch-a-strict-provider-recovery_process.md`
  throughout the process.
- No MCP tool docstrings are expected to change because no server tool contract
  changes.

## Portability

This work must remain portable across supported Windows and macOS hosts:

- no shell-specific recovery behavior in product code
- interactive prompting uses the existing `prompt_toolkit` shell path and must
  keep the no-console fallback behavior intact
- headless recovery remains deterministic and automation-friendly through
  non-zero final status / exit code
- provider CLI dependencies remain the existing BYO local CLI prerequisites
  documented for `codex-cli` and `claude-cli`

## Verification plan

Cheapest-first checks:

1. Targeted tests for provider resume failure and recovery:
   - Codex resume failure fails closed by default
   - Claude resume failure fails closed by default
   - OpenAI `previous_response_id` request failure is typed as resume failure
   - explicit new-session-from-memory recovery creates labeled new provider
     metadata
   - retry recovery reuses the expected handle
   - abort recovery produces a provider-session failure result
   - artifacts contain expected handle, failure text, and
     `replacement_provider_session_started=false`
2. Targeted tests for memory entry enrichment.
3. Targeted UX tests for the interactive recovery callback/prompt behavior.
4. `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
5. `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
6. Deployment scenario tests:
   - multiple top-level `pyocd-debug` prompts in one shell process
   - each top-level prompt owns its own run root and provider state
   - long provider loops under real `codex-cli` where available
   - simple code-writing repair with workspace/build context
   - real hardware runs on `nrf52833dk` and `nucleo_l476rg` if both are
     attached and the local provider auth is available

Hardware/provider proof:

- Run real Codex-backed multi-prompt and repair flows on the attached scoped
  pair if this host has both boards and Codex auth.
- If Claude proof is not available now, leave Claude as an explicit later
  provider proof item for the user to run.

## Acceptance criteria

Branch A is merge-clean when:

- real-session providers no longer silently fall back to fresh provider
  sessions after a resume failure
- `pyocd-debug-brain` fails closed by default on provider resume failure
- `pyocd-debug` exposes retry/new-session-from-memory/abort recovery and routes
  the selected choice through the same shared loop
- recovery-created sessions are labeled as new in events/artifacts/provider
  metadata
- the brain persists a richer crash-recovery memory ledger and uses it for
  explicit new-session recovery
- all stale tests expecting silent fallback are replaced with strict/recovery
  assertions
- docs match code at the R12 contract level
- non-hardware default and suite ladders are green
- real hardware/provider deployment tests are green on this host or have a
  precise blocking reason that is not a code ambiguity

## Verified

- The build plan and active R12 docs already require strict provider-session
  recovery.
- The current code paths that still implement silent fallback were identified:
  `provider_codex_cli.py`, `provider_claude_cli.py`, and the generic provider
  failure handling in `loop.py`.

## Pending verification

- Implementation of strict failure and explicit recovery.
- Updated regression tests.
- Non-hardware ladder.
- Real Codex provider multi-prompt/code-writing deployment proof.
- Real hardware proof on attached `nrf52833dk` and `nucleo_l476rg`.
- Later Claude provider proof by the user if Claude auth/model availability is
  not available in this session.
