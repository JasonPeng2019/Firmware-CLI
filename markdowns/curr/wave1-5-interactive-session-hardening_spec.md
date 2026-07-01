> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Wave 1.5 Interactive Product Session Hardening

## Goal in plain English

Make the product behave like a real interactive firmware-debugging agent, not
like a sequence of unrelated one-shot jobs. The operator shell must keep one
explicit parent agent session across consecutive user prompts, while each prompt
still runs as a bounded child task with its own artifacts and board/tool
evidence. Provider-native handles, compact provider memory, selected board,
workspace/build context, loaded details, client actions, and visible session
state must carry forward by default until the operator explicitly resets,
forks, or starts a new session.

This spec exists because Wave 1 implemented provider continuity inside one
top-level turnkey run, but the normal terminal product still starts a new
provider session for each consecutive prompt in the interactive shell. That is
not the user-facing product model described by the prototype priority list.

Task: Wave 1.5 interactive product session hardening.
Roadmap anchor: `R12` Stage 5 turnkey brain/product shell, before Wave 2 Module
D/E/F/G/H implementation. This is an entry gate for Wave 2, not a replacement
for the already specified Wave 2 provider-stream, checkpoint, codebase-map,
green-approval, or cleanup modules.

## Scope and non-scope

In scope:

- A parent `AgentSessionState` or equivalent product-session model for the
  `pyocd-debug` operator shell.
- Consecutive shell prompts sharing one provider handle/thread/session by
  default where the provider supports it:
  - Codex CLI thread resume;
  - Claude CLI session resume/fork behavior;
  - OpenAI Responses `previous_response_id`;
  - Anthropic local-memory continuation.
- Consecutive shell prompts sharing compact brain-owned memory:
  - Tier 0 canonical state for the active prompt;
  - Tier 1 recent committed facts;
  - deterministic Tier 2 mid-history facts;
  - hard-limited Tier 3 rolling summary.
- Prompt-scoped child runs so each user prompt still has its own run root,
  child prompt id, final result, prompt/decision artifacts, event records, and
  board evidence.
- Explicit shell controls:
  - `/session` to show the parent session, provider handle, prompt count,
    current board/workspace, memory counts, and child runs;
  - `/new` to start a fresh parent agent session;
  - `/reset-provider` to drop the provider handle and start a new provider
    conversation from explicit local memory or from a cold state;
  - `/reset-memory` or `/forget` to clear compact agent memory;
  - `/reset-board` to disconnect/forget board session context without throwing
    away provider/session memory;
  - `/fork` to branch the current parent session when supported, or create a
    labeled local-memory fork when native provider fork is unavailable.
- Strict resume-failure behavior across user prompts: do not silently start a
  fresh provider session when a promised handle cannot resume.
- Clear user-facing output that makes provider continuity visible without
  exposing raw JSON or hidden reasoning by default.
- Headless/one-shot commands preserving their current fresh-run behavior unless
  the user explicitly opts into a named persistent session.
- Documentation corrections wherever "persistent session" currently conflates
  in-run provider continuity with cross-prompt interactive continuity.

Out of scope:

- Implementing Wave 2 provider-visible streaming or Ctrl-C cancellation during
  an in-flight provider turn. That remains
  `wave2-provider-stream-interrupt_spec.md`.
- Implementing Wave 2 mid-tool checkpoint buffers. That remains
  `wave2-midtool-checkpoints_spec.md`.
- Implementing Wave 2 codebase-map creation/maintenance. That remains
  `wave2-codebase-map_spec.md`.
- Implementing project-level persistent custom tools/skills across unrelated
  product sessions. That later MVP feature is `things-to-change.md` entry #10.
- Exposing hidden chain-of-thought. Provider-visible status text and public
  direction summaries are separate from private hidden reasoning.
- Making board sessions live forever. Provider/agent continuity and board
  hardware connection lifetime are separate contracts.
- Replacing the provider adapters with new SDK integrations. The first
  implementation should work through the existing adapter protocol and can
  leave SDK/app-server replacement as later hardening.

## Reconciliation summary

- Build plan: Stage 5 requires a turnkey brain + CLI product that can carry
  provider reasoning context, compact memory, skills, progress, and governed
  board decisions. The build plan and prototype priority list make persistent
  session/model memory item #1 because the model is supposed to debug over a
  continuing context, not cold-start every operator prompt.
- Current code:
  - `src/pyocd_debug_mcp/brain/provider_types.py` has a real
    `ProviderSessionState` with native handle, runtime context, Tier 1/Tier 2/
    Tier 3 memory, sync cadence, and resume-failure metadata.
  - `src/pyocd_debug_mcp/brain/provider_codex_cli.py` resumes one Codex remote
    thread inside a run with `codex exec resume <thread_id>`.
  - `src/pyocd_debug_mcp/brain/provider_claude_cli.py` resumes one Claude
    remote session inside a run with `claude --print --resume <session_id>`.
  - `src/pyocd_debug_mcp/brain/loop.py` creates and updates provider session
    state inside `run_turnkey`, records provider progress, and fails closed on
    resume failure unless interactive recovery is provided.
  - `src/pyocd_debug_mcp/brain/app.py` creates a fresh provider and fresh
    invocation for each `run_freeform_task(...)`.
  - `src/pyocd_debug_mcp/ux/shell.py` stores shell settings such as board,
    provider, model, workspace, memory knobs, and `last_session_id`, but it
    does not retain provider session state or compact memory across `_run_task`
    calls. Each prompt in the interactive shell therefore starts a new
    top-level provider session today.
- Other docs or notes:
  - `things-to-change.md` item #1 says persistent session and model memory is
    the first prototype priority, but the July 1 status text explicitly says
    current prompt/memory hardening does not add cross-invocation provider
    session persistence.
  - `R12_P_SPLIT.md` says Branch A covers provider sessions where available and
    also says the current Wave 1 memory hardening does not include
    cross-invocation provider-session persistence.
  - `current-progress.md` states the same limitation: the feature does not add
    cross-invocation provider-session persistence.
  - `wave2-provider-stream-interrupt_spec.md` and
    `wave2-midtool-checkpoints_spec.md` both assume multi-prompt shell behavior
    will be tested, but they do not define the parent product-session model.
- Disagreements:
  - The docs can make Wave 1 sound complete because in-run provider continuity
    is implemented and well-tested. From a product perspective, the normal
    interactive shell is still missing the more important continuity: prompt 2
    should know what prompt 1 established without the operator restating it.
  - This spec resolves that by naming the current behavior honestly:
    in-run provider continuity is implemented; cross-prompt interactive
    provider continuity is not implemented and must be treated as a Wave 1.5
    hard gate before Wave 2 product work builds on the shell.

## Design

### Product-session model

Add a parent agent-session object owned by the operator shell and reusable by
non-shell entrypoints that explicitly opt into session persistence. Suggested
fields:

- `agent_session_id`;
- provider kind/model and provider capabilities;
- `ProviderSessionState | None`;
- compact memory policy and current memory state;
- selected board id and board-facing context;
- workspace/build/flash/symbol context;
- loaded governed tool details, loaded client-action details, loaded
  compound-action details, and loaded model-native skill state where safe to
  carry across prompts;
- session-scoped client actions and their hashes;
- prompt counter and child run ids;
- current recovery state after provider resume failure;
- creation/update timestamps and artifact root.

The parent session is the user-facing conversation. A child run is one user
prompt's bounded firmware-debugging task.

### Prompt boundary

In `pyocd-debug`, entering plain text or `/run <task>` should create a child
prompt/run under the current parent agent session by default.

For each child prompt:

1. Build a normal `TurnkeyInvocation` for the new task.
2. Inject the parent provider state, memory, loaded details, and client-action
   state into the child `BrainState` before the first provider turn.
3. Run the existing bounded provider/tool loop with the usual max-iteration and
   timeout caps.
4. On completion, commit the updated provider state, compact memory, loaded
   details, child run id, and relevant durable facts back to the parent agent
   session.
5. Render the child result normally and keep its artifacts isolated under the
   child run root.

The child prompt must not erase the parent provider handle after board cleanup.
The current final `disconnect` behavior can still close board sessions; that is
separate from provider/agent continuity.

### One-shot vs interactive modes

Preserve two clear product modes:

- `pyocd-debug-brain run ...` and `pyocd-debug run ...` one-shot commands start
  a fresh top-level run by default and exit after one task. This keeps
  automation deterministic.
- `pyocd-debug` interactive shell starts or resumes a parent agent session and
  treats consecutive user prompts as one continuing conversation by default.

If headless persistence is added, it must be explicit, for example
`--agent-session <id>` or `--resume-agent-session <id>`. Do not make scripts
silently reuse stale sessions.

### Session controls

The shell needs explicit controls because provider continuity is powerful and
must be inspectable:

- `/session`: print agent session id, provider/model, remote handle kind/id
  summary, continuation path, prompt count, memory tier counts, current board,
  workspace/build context, loaded details summary, and recent child runs.
- `/new`: create a fresh parent agent session and clear provider handle,
  compact memory, loaded details, client actions, and prompt count.
- `/reset-provider`: drop only the provider handle/runtime context. The user
  chooses or the command states whether local compact memory is retained and
  injected into the next provider turn.
- `/reset-memory` or `/forget`: clear compact memory and summary state without
  changing board/workspace settings.
- `/reset-board`: disconnect or forget board session metadata and selected
  board runtime state without changing provider memory.
- `/fork`: create a named child parent session. If the provider supports native
  fork, preserve the native fork handle. Otherwise create a local-memory fork
  clearly labeled as not a true provider-native fork.

No command should hide whether it kept or discarded provider state.

### Resume failure policy

If the parent session has a native provider handle and a later prompt cannot
resume it, the product must stop and ask in interactive mode. Valid choices:

- retry the same handle;
- start a new provider session from saved compact memory, visibly replacing the
  old handle;
- abort the child prompt and keep the parent session marked as needing
  recovery.

Headless mode must fail closed unless it was given an explicit recovery policy.
Starting a fresh provider session silently is a product bug.

### Memory semantics

Memory tiers must span prompts in one parent agent session:

- Tier 0 remains the current child prompt's canonical brain state and wins on
  conflict.
- Tier 1 keeps recent committed facts from the latest provider turns across
  child prompts.
- Tier 2 is deterministically compacted from Tier 1.
- Tier 3 is hard-limited rolling summary; model/provider compression is only
  allowed when Tier 2 overflows into Tier 3.

The default remains two Tier 1 recent turns, six Tier 2 mid-history entries,
and native memory safety sync every ten provider turns unless the existing
configuration says otherwise. Prompt count and provider turn count are both
shown in `/session`.

### Artifact model

Use a parent session artifact root that links to child run roots. The exact path
can be finalized during implementation, but it must not collide with existing
board run roots. A first acceptable shape:

```text
runs/agent-sessions/<agent_session_id>/
  agent-session.json
  prompts.jsonl
  memory.json
  child-runs.jsonl
  logs/events.jsonl
```

Child run roots continue to use existing `runs/<session_id>/...` semantics. A
child run record should include its parent `agent_session_id` and child
`prompt_index`.

Artifacts must distinguish:

- provider handle/session metadata;
- brain-owned compact memory;
- board session/run artifacts;
- user-visible prompt/result history;
- raw/inspector data where enabled.

### UX policy

Normal users should see:

- the current board, provider, model, parent agent session, and last child run
  in the prompt or `/session`;
- provider continuity status such as "continuing Codex thread ..." or "new
  provider session from saved memory" at prompt boundaries;
- concise evidence/direction summaries from completed turns;
- final result and artifact pointers.

Normal users should not see raw JSON decisions, raw final provider output, raw
prompt bundles, or hidden chain-of-thought by default. Developer/raw modes
should expose provider metadata, raw final output, prompt hashes, and event
records.

The provider-turn streaming and interrupt spec will later add live
provider-visible text during a running provider turn. This spec only requires
the shell to make session continuity and prompt boundaries visible.

### Bad product behaviors this spec removes

- Calling a one-run provider resume implementation a complete persistent user
  session.
- Making `pyocd-debug` look conversational while each prompt is a cold provider
  conversation.
- Requiring the user to restate facts from the previous prompt to the same
  shell session.
- Silently losing compact memory or loaded provider context between prompts.
- Silently starting a new provider handle after resume failure.
- Mixing board session lifetime with provider conversation lifetime.
- Leaving Wave 2 modules to infer different meanings of "session" while they
  add streaming, checkpoints, codebase-map maintenance, cleanup, and inspector
  behavior.

## Board-facts-as-data and origin tags

- `agent_session_id`, child prompt ids, provider handles, runtime directories,
  process ids, and local artifact paths are session-local `PROJECT-DEFINED`
  runtime provenance. They are not board facts.
- Board identity still comes from the existing board config and shell
  selection. Do not add provider-session fields, prompt counters, serial ports,
  probe UIDs, or runtime paths to tracked `boards/<board>.yaml`.
- If a parent session carries a selected board across prompts, it carries only
  the logical `board_id` plus runtime provenance in session artifacts. Machine
  attachment facts remain local/discovered.
- Cleanup and resume status must be explicit. Do not claim a provider handle,
  board session, subprocess, serial port, or pyOCD session is clean unless the
  current run proved it.

## Documentation plan

If accepted, update these docs in the implementation unit:

- `README.md`: distinguish one-shot commands from the persistent interactive
  shell and document `/session`, `/new`, reset, and fork controls.
- `markdowns/things-to-change.md`: clarify item #1 so persistent session means
  both in-run provider continuity and cross-prompt interactive continuity.
- `markdowns/R12_P_SPLIT.md`: add Wave 1.5 as a serial entry gate before Wave 2
  modules, and state that D/E/F/G/H build on the parent agent-session model.
- `markdowns/ROADMAP.md`: record the Wave 1.5 gate under the active `R12`
  prototype frontier.
- `markdowns/firmware_agent_build_plan_concrete (10).md`: amend Stage 5 status
  only after user sign-off, because this changes the current interpretation of
  what "persistent session" requires for the product.
- `markdowns/current-progress.md`: record current code reality and, after
  implementation, validation evidence.
- `markdowns/curr/README.md`: keep this active spec discoverable.
- `markdowns/curr/r12_turnkey_spec.md`: tighten terminology around run,
  provider session, board session, and parent agent session.
- `markdowns/UXLayer.md`: document the interactive shell UX, `/session`, and
  the split between normal user output and raw/inspector output.
- `markdowns/repo_file_index.md`: update if new modules such as
  `agent_session.py` or shell-session artifact helpers are added.

## Portability

- The parent session store must work on Windows and macOS using `pathlib`.
- No shell-specific quoting, path separators, terminal APIs, or process-group
  assumptions should be required for session persistence.
- Session artifacts should use repo-relative paths where possible and reserve
  absolute paths for provenance.
- The shell must continue to work in real TTY mode and piped stdin mode.
- If durable resume across shell process restarts is implemented, it must be
  atomic enough to avoid corrupting `agent-session.json` on crash or Ctrl-C.
- The implementation must not write global user `.codex`, `.claude`, or
  `.agents` folders. Provider-native skill projections remain run/session-local
  generated views.

## Verification plan

Software-side tests:

- Unit tests for parent `AgentSessionState` serialization, prompt counter,
  child run links, and memory/provider-state carryover.
- Fake-provider shell test:
  - prompt 1 returns a native handle and a durable fact;
  - prompt 2 receives the same provider handle and memory fact without the
    operator restating it.
- Fake-provider negative test proving `pyocd-debug-brain run ...` remains a
  fresh one-shot unless explicit session resume is requested.
- Resume-failure tests:
  - interactive retry;
  - interactive new session from saved memory;
  - interactive abort;
  - headless fail-closed.
- Shell command tests for `/session`, `/new`, `/reset-provider`,
  `/reset-memory`, `/reset-board`, and `/fork`.
- Memory tests proving Tier 1/Tier 2/Tier 3 state can span multiple child
  prompts and still respects the existing caps.
- Artifact tests proving parent session records link to child run roots without
  overwriting existing `runs/<session_id>/...` artifacts.
- UX renderer tests proving default output shows continuity state but not raw
  JSON or hidden reasoning.
- Regression tests for non-interactive/piped shell input, including
  BOM-prefixed slash commands.

Product-behavior tests:

- Two-prompt interactive shell smoke with a fake provider that explicitly
  asserts the second prompt is in the same provider conversation.
- No-hardware Codex CLI smoke, if credentials/local CLI availability permits:
  prompt 1 establishes a harmless fact; prompt 2 asks the provider to use the
  prior fact and artifacts must show the same Codex thread id or explicit
  recovery path.
- No-hardware Claude CLI smoke, if credentials/local CLI availability permits:
  same pattern with Claude session id or fork semantics.
- Credentials-free OpenAI/Anthropic API-path simulation through the real
  provider factory/turnkey loop, proving previous response id or local-memory
  continuity crosses user prompts inside one parent agent session.
- Multi-prompt shell run where each user prompt is one child loop, with isolated
  child artifacts and a shared parent memory/provider state record.

Hardware tests are not required for this feature unless implementation changes
board-session cleanup or persistent board connection behavior. The hard bar is
CLI/product/provider behavior.

## Acceptance criteria

- In the `pyocd-debug` interactive shell, consecutive user prompts continue the
  same parent agent session by default.
- Where the provider supports a remote handle, prompt 2 resumes the same
  provider conversation established by prompt 1. Where the provider is
  local-memory-only, prompt 2 receives the parent compact memory explicitly.
- The shell prompt or `/session` makes the parent agent session and provider
  continuity visible.
- Each user prompt still creates an isolated child task/run with its own
  artifacts, result, events, and board evidence.
- One-shot commands remain fresh by default.
- `/new`, `/reset-provider`, `/reset-memory`, `/reset-board`, and `/fork` work
  with clear user-facing state changes.
- Provider resume failure is never silently replaced by a fresh session.
- Compact memory tiers span prompts and remain bounded by the existing caps.
- Board session lifetime and provider conversation lifetime are separated.
- Docs no longer overstate Wave 1 by calling in-run provider continuity a
  complete persistent user session.
- Wave 2 D/E/F/G/H specs can refer to one parent agent-session model instead of
  inventing incompatible local meanings of "session."

## Verified

- Current code has a real provider-session state model, native handle metadata,
  compact memory tiers, resume-failure records, and in-run provider continuation
  for Codex CLI, Claude CLI, OpenAI API simulation, and Anthropic local-memory
  behavior.
- Current operator shell preserves board/provider/model/workspace settings and
  last child run id across prompts.
- Current operator shell does not preserve provider session state or compact
  memory across `_run_task(...)` calls; each prompt invokes
  `run_freeform_task(...)`, which creates a fresh provider/config/invocation
  path.
- Current docs already state that the prompt/memory cost hardening feature does
  not add cross-invocation provider-session persistence.

## Pending verification

- No implementation has been written for this spec.
- Exact module names, artifact path names, slash command names, and persistence
  format should be finalized during the build pass.
- User sign-off is needed before amending the build plan/source-of-truth wording
  to make Wave 1.5 an accepted hard gate.
- Live Codex/Claude/API provider proof remains pending until implementation.
