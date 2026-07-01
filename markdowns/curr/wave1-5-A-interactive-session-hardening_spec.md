> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Wave 1.5-A Persistent Shell Provider Session

## Goal In Plain English

Make `pyocd-debug` interactive mode behave like Codex CLI: one shell session is
one continuing provider conversation.

Hard bar:

**One `pyocd-debug` shell = one persistent provider session.**

The user should be able to type prompt 1, then prompt 2, and the provider should
remember prompt 1 through the same Codex thread, Claude session, OpenAI response
chain, or Anthropic/FirmCLI compact-memory continuity. The user should not have
to restate context just because the first prompt finished.

This spec exists because Wave 1 implemented provider continuity inside one
bounded turnkey run, but the normal interactive shell still starts each user
prompt as a fresh top-level provider session. That is not the product behavior
the prototype needs.

Roadmap anchor: `R12` Stage 5, Branch A provider-session continuity, before
Wave 2 product modules build on the shell.

## Scope And Non-Scope

In scope:

- `pyocd-debug` interactive shell keeps one provider session in memory for the
  lifetime of that shell process.
- Every normal user prompt in that shell resumes the same provider session by
  default.
- Provider session state includes the provider handle and the FirmCLI compact
  memory needed to continue if native resume is unavailable.
- Board/tool work may still create separate run artifacts internally.
- Board cleanup must not erase the provider conversation.
- `/session` shows the current provider session status.
- `/new` starts a fresh provider conversation.
- `/forget` clears provider session state and compact memory.
- Provider resume failure is visible and never silently replaced by a fresh
  session.

Out of scope:

- A complex user-facing parent/child session product model.
- Durable cross-process session resume after closing the shell. That can be a
  later feature.
- Provider-visible streaming and Ctrl-C cancellation; that remains Wave 2
  Module D/H.
- Mid-tool checkpoint buffers; that remains Wave 2 Module E.
- Codebase-map maintenance; that remains Wave 2 Module G.
- Keeping board hardware sessions open forever. Provider continuity and board
  connection lifetime are separate.
- Exposing hidden chain-of-thought. Status/progress text and provider metadata
  are separate from private hidden reasoning.

## Reconciliation Summary

### Build plan

The build plan and prototype priority list require persistent session/model
memory because the product is supposed to feel like a continuing agentic
debugging session, not a sequence of cold one-shot calls.

### Current code

Current code already has the pieces needed inside one run:

- `ProviderSessionState` stores native handles, runtime context, memory tiers,
  and resume-failure metadata.
- Codex CLI provider can resume a remote thread.
- Claude CLI provider can resume a remote session.
- OpenAI API simulation uses response chaining.
- Anthropic API path uses client-owned local memory.
- The turnkey loop updates provider session state during one run.

Current shell gap:

- `pyocd-debug` interactive shell preserves some settings such as board,
  provider, model, workspace, and last run id.
- It does not preserve the actual provider session state and compact memory
  across user prompts.
- Each prompt calls the run path as a fresh top-level invocation, so prompt 2
  is not reliably in the same provider conversation as prompt 1.

### Conflict resolved

Earlier wording made this sound like a large parent/child session framework.
That is not the desired product requirement. The desired requirement is simpler:

**The interactive shell owns one provider session and passes it into every
prompt until the user resets it.**

Run roots, prompt ids, and artifact links are implementation details only. They
must not make the user feel like they are starting a new agent every prompt.

## Required Product Behavior

### Default interactive behavior

When the user starts `pyocd-debug`:

1. The shell creates an empty provider-session slot.
2. The first normal prompt starts a provider session.
3. The shell stores the returned provider session state.
4. Every later prompt passes that stored provider session state back into the
   provider path.
5. After every prompt, the shell stores the updated provider session state.

The user-facing model is one continuous agent conversation.

### One-shot commands

One-shot commands stay deterministic:

- `pyocd-debug-brain run ...`
- `pyocd-debug run ...`
- benchmark commands
- scripted/piped one-shot invocations

These start fresh by default unless a future explicit `--session` or
`--resume-session` flag is designed. Do not silently reuse old sessions in
automation.

### Provider semantics

Provider-specific hard bar:

- Codex CLI: later shell prompts resume the same Codex thread when possible.
- Claude CLI: later shell prompts resume the same Claude session when possible.
- OpenAI API: later shell prompts continue through the stored response id /
  continuation state when available.
- Anthropic API or local-memory-only providers: later shell prompts receive the
  stored FirmCLI compact memory explicitly.

If native provider resume fails, the shell must not hide it. It must tell the
user and either:

- retry;
- start a new provider session from saved compact memory;
- start completely fresh after explicit user confirmation;
- abort the prompt and keep the shell in a recoverable state.

Silent fallback to a fresh provider session is a product bug.

### Memory semantics

The provider session carries compact memory across prompts:

- Tier 1 recent facts from the latest committed provider turns.
- Tier 2 deterministic mid-history facts.
- Tier 3 hard-limited rolling summary.

Existing caps still apply. This feature does not expand the memory budget; it
extends the same bounded memory across consecutive prompts in one shell.

### Board/session separation

Board cleanup is independent of provider continuity.

The product may disconnect, reset, or clean up board/MCP/pyOCD/serial resources
after a prompt. That must not erase the provider thread/session/memory unless
the user asks for a new provider session or forgets memory.

### User commands

Minimum required commands:

- `/session`: show provider, model, provider-session status, native handle kind
  and id if available, memory counts, selected board, workspace, and last run.
- `/new`: start a new provider conversation and clear carried provider memory.
- `/forget`: clear provider session state and compact memory.

Optional later commands:

- `/reset-board`: forget board runtime state without forgetting provider
  memory.
- `/reset-provider`: drop native provider handle but keep compact memory for
  explicit recovery.
- `/fork`: branch a conversation if the provider supports it.

Do not add optional commands before the minimum behavior is correct.

### User-visible output

Normal users should see short status lines such as:

- `starting Codex session`
- `continuing Codex thread <short-id>`
- `continuing Claude session <short-id>`
- `continuing from FirmCLI memory`
- `provider resume failed; choose retry/new-from-memory/fresh`

Normal users should not see raw JSON decisions, raw prompt bundles, or raw final
provider output by default. Developer/raw modes may expose provider metadata and
artifacts.

## Implementation Direction

Keep the implementation small.

1. Add shell-owned provider session state.
   - Store `ProviderSessionState | None` on the interactive shell object.
   - Store the compact memory state with it.
   - Store enough provider/runtime context to resume correctly on the next
     prompt.

2. Allow the turnkey/freeform run path to accept initial provider session state.
   - If session state is provided, use it before the first provider turn.
   - If no session state is provided, behave exactly as today.

3. Return updated provider session state from each prompt run.
   - The shell writes it back to its current provider-session slot.
   - Failed runs must report whether the previous provider state is still safe
     to reuse.

4. Keep run artifacts per prompt.
   - Existing `runs/<session_id>/...` artifacts can stay.
   - Add a field linking the run to the current shell provider session if
     practical.
   - Do not block the feature on a complex artifact tree.

5. Add minimal shell commands.
   - `/session`
   - `/new`
   - `/forget`

6. Add resume-failure handling.
   - Interactive shell asks or exposes choices.
   - Headless mode fails closed unless explicit recovery policy exists.

## Board Facts As Data And Origin Tags

- Provider handles, shell session ids, memory counters, and run ids are
  `PROJECT-DEFINED` runtime provenance.
- Board identity remains the existing `board_id` from board config.
- Do not add provider-session fields, prompt counters, runtime paths, serial
  ports, or probe ids to tracked board YAML.
- Do not claim a provider session, subprocess, serial port, or board resource
  was cleaned up unless the current run proved it.

## Documentation Plan

If implemented, update:

- `README.md`: explain that `pyocd-debug` interactive mode is one persistent
  provider session, while one-shot commands are fresh by default.
- `markdowns/things-to-change.md`: clarify item #1 as same-shell provider
  persistence, not only in-run persistence.
- `markdowns/R12_P_SPLIT.md`: record Wave 1.5-A as Branch A provider-session
  hardening before Wave 2.
- `markdowns/ROADMAP.md`: record the active R12 gap.
- `markdowns/current-progress.md`: record implementation and validation status.
- `markdowns/curr/README.md`: keep this spec discoverable.
- `markdowns/curr/r12_turnkey_spec.md`: distinguish one bounded run from one
  interactive shell provider session.

## Portability

- Use `pathlib` for any artifact/session paths.
- The shell behavior must work on Windows and macOS.
- The shell must still work in TTY mode and piped stdin mode.
- No global `.codex`, `.claude`, or `.agents` writes are required for this
  feature.
- Durable session resume after process exit is not required for this spec.

## Verification Plan

Software tests:

- Unit test provider-session state injection into a new prompt run.
- Unit test updated provider-session state is returned after a prompt run.
- Shell test with fake provider:
  - prompt 1 returns provider handle `H1` and memory fact `F1`;
  - prompt 2 receives `H1` and `F1` without the user restating them.
- Negative test proving one-shot commands still start fresh by default.
- `/session` test showing provider status and memory counts.
- `/new` test proving prompt after `/new` starts fresh.
- `/forget` test proving memory/provider state is cleared.
- Resume-failure test proving the shell does not silently create a fresh
  session.
- Artifact test proving per-prompt run artifacts still exist.

Provider behavior tests:

- No-hardware Codex CLI smoke, if available: prompt 2 resumes prompt 1's Codex
  thread or reports explicit recovery.
- No-hardware Claude CLI smoke, if available: prompt 2 resumes prompt 1's Claude
  session or reports explicit recovery.
- Credentials-free OpenAI/Anthropic simulation through the real provider paths
  proving continuation state or compact memory crosses prompts.

Hardware validation is not required unless implementation changes board cleanup
or board session lifetime.

## Acceptance Criteria

This spec is complete only when:

1. One `pyocd-debug` interactive shell keeps one provider session by default.
2. Prompt 2 resumes prompt 1's provider conversation when the provider supports
   native resume.
3. Prompt 2 receives bounded FirmCLI compact memory when native resume is not
   available.
4. The user does not have to restate facts from prompt 1 in prompt 2.
5. `/session` shows the current provider-session status.
6. `/new` starts a fresh provider conversation.
7. `/forget` clears provider session state and compact memory.
8. One-shot commands remain fresh by default.
9. Board cleanup does not erase provider conversation state.
10. Resume failure is visible and never silently replaced by a fresh session.
11. Tests prove the shell behaves like one persistent provider session.
12. Docs stop implying that in-run provider continuity is enough for the
    interactive product.

## Verified

- Current provider adapters and `ProviderSessionState` support in-run provider
  continuity.
- Current shell preserves configuration settings across prompts.
- Current shell does not preserve provider session state and compact memory
  across prompts.

## Pending Verification

- This spec is not implemented.
- Exact code shape and helper names are pending implementation.
- Live Codex/Claude/API provider proof is pending implementation.
