# P-Wave A Chat Handoff - 2026-06-28

This note summarizes the current Codex chat so a new Codex session can resume
without rereading the whole thread.

## Current Branch

- Repo: `C:\Users\Jason\Documents\Jason\FirmCLI\ParallelBranch\Firmware-CLI`
- Branch: `P-Wave-A`
- Current worktree includes docs edits in:
  - `README.md`
  - `markdowns/R12_P_SPLIT.md`
  - `markdowns/UXLayer.md`
  - `markdowns/current-progress.md`
  - `markdowns/firmware_agent_build_plan_concrete (10).md`
  - `markdowns/curr/r12_turnkey_spec.md`
  - `markdowns/curr/things-to-change.md`
  - `markdowns/curr/p_wave_a_merge_benphaseb_review.md`

## Phase A Status

Phase A is mostly there for the current prototype boundary. The docs now state
that the branch has a working brain-owned provider adapter model with:

- `openai-api`: remote-primary continuation through Responses
  `previous_response_id`
- `codex-cli`: remote-primary continuation through `codex exec resume
  <thread_id>`
- `claude-cli`: remote-primary continuation through `claude --print --resume
  <session_id>`
- `anthropic-api`: local-primary continuation, because the current Anthropic
  Messages API path is stateless and does not expose a Claude Code-style
  resumable session handle

The main remaining Phase A implementation gap is strict provider-session
recovery behavior.

## Session Policy Decision

For real-session providers, once a top-level run has a provider-owned resume
handle, the system should not silently start a fresh provider session if resume
fails.

Real-session providers:

- `openai-api` with `previous_response_id`
- `codex-cli` with `thread_id`
- `claude-cli` with `session_id`

Expected behavior:

- interactive `pyocd-debug`: notify the operator that resume failed and ask
  whether to retry resume, start a new provider session from saved local memory,
  or abort
- headless `pyocd-debug-brain`: fail closed by default
- recovery-created sessions must be labeled as new sessions in events/artifacts
- `anthropic-api` is excluded from this rule because continuity is brain-owned
  memory, not provider-owned session resume

This is the practical answer to the user's question: "is Phase A mostly done
except changing the fallback mechanism?" Yes, mostly. The code change is to
replace silent fallback with explicit recovery/fail-closed behavior, then prove
it with tests and artifacts.

## What Complete Phase A Still Needs

Implementation:

- remove or gate silent fresh-session fallback for `codex-cli` and `claude-cli`
  when a resume handle already exists
- apply equivalent strict handling to `openai-api` if `previous_response_id`
  resume fails
- add interactive recovery prompt/state for retry/new-from-memory/abort
- make headless behavior fail closed by default
- record expected handle, failure reason, selected recovery path, and new-session
  label in artifacts/events

Proof:

- unit tests for Codex CLI resume failure: no silent fallback
- unit tests for Claude CLI resume failure: no silent fallback
- tests for interactive choices: retry, new session from memory, abort
- tests for headless fail-closed behavior
- artifact assertions for resume failure and recovery/new-session labeling
- one end-to-end multi-prompt run proving each top-level prompt gets its own
  provider loop/session/artifacts and does not leak state across prompts

## Provider Integration Direction

Long-term direction documented in the repo:

- keep this repo's `DecisionProvider`/brain-owned adapter contract
- Codex final hardening should move toward SDK/app-server/thread APIs for
  stronger streaming, structured events, session lifecycle, approvals, and fewer
  subprocess/output-parsing failure points
- Claude subscription-backed use should stay as BYO local Claude Code CLI unless
  Anthropic approves a different product/auth arrangement
- Claude API-key/approved-partner use can move toward Claude Agent SDK
- do not claim Claude subscription/rate-limit support through SDKs unless the
  product arrangement is approved by Anthropic

## Claude API Memory Layer

Current `anthropic-api` behavior is not a native Claude Code session. It relies
on the brain's compact memory. The current memory entries preserve items like:

- turn index
- classification
- observation summary
- optional hypothesis
- action kind
- compact action summary
- compact result summary
- verification snapshot

Future hardening should preserve more exact operational state:

- exact tool arguments and important observed values
- artifact paths
- edits made
- failed hypotheses and ruled-out paths
- refusals/block reasons
- acceptance constraints
- board/session identity facts that must survive compaction

## Skill Install Done In This Chat

The user asked to install the skills currently in the repo's `.codex` so VS Code
could see them, but explicitly said not to install into `C:\Users\Jason\.codex`.

Installed from:

`C:\Users\Jason\Documents\Jason\FirmCLI\ParallelBranch\Firmware-CLI\.codex\skills`

Installed to workspace-local:

`C:\Users\Jason\Documents\Jason\FirmCLI\ParallelBranch\.codex\skills`

Installed skill folders:

- `firmcli-build`
- `firmcli-fix-bug`
- `firmcli-review`
- `firmcli-spec-loop`
- `firmcli-specs`
- `firmcli-test-suite`
- `firmcli-workflow-core`
- `firmcli-write-process`
- `merge-conflicting-repos`

Verified each installed folder has a `SKILL.md`. Also verified
`C:\Users\Jason\.codex\skills` still only contains `.system`.

## Verification Already Run

Before this handoff file, docs-only checks included:

- stale-claim scans for contradictions around session fallback/resume behavior
- `git diff --check`, which reported only Git LF-to-CRLF warnings and no
  whitespace errors

Earlier in the same branch discussion, the following full checks had passed
before later docs-only edits:

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run mypy src`
- `uv build --wheel`
- `uv run pyocd-debug --help`
- `uv run pyocd-debug-brain --help`
