> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Wave 2 Mid-Tool Checkpoint Buffer

## Goal in plain English

Give the turnkey brain and provider a generic way to observe long-running work
before the final tool timeout. When a UART read, build/external command, or long
client action is still running, the server/client side should append compact
checkpoint observations to a job buffer. The brain periodically surfaces those
observations to the provider and asks for a bounded decision: continue, cancel,
or make a narrow checkpoint adjustment. This is not a special "is a board
connected" feature. It is the general final-product design for detecting bad
reads, null reads, stalls, partial output, and early failure evidence while a
long action is still in progress.

Task: Wave 2 provider-visible mid-tool checkpoint buffer.
Roadmap anchor: R12 Wave 2 Module E stream checkpoints, with UX Pass 2
inspector/progress support from Module D and cleanup dependencies from Module H.

## Scope and non-scope

In scope:

- A brain-mediated checkpoint model for long-running actions that currently
  behave as a single request/response wait.
- Checkpoint observation buffers for:
  - UART read/wait flows;
  - workspace builds and external commands launched by the product runtime;
  - governed client actions and model-authored scripts that can run long enough
    to need intermediate observations.
- Typed checkpoint records with elapsed time, latest chunks, no-data/stall
  markers, matched/error/null-read indicators, output counters, and cleanup
  state.
- A bounded provider checkpoint turn where the provider can inspect checkpoint
  context and return only a checkpoint verdict, not arbitrary new board work.
- Continue/cancel handling that is generic across the supported stream sources.
- Operator UX separation:
  - normal users see concise live progress and important checkpoint state;
  - developer/inspector mode can show the detailed observation buffer and
    provider checkpoint turns.
- Artifacts/events that make each checkpoint auditable after the run.

Out of scope:

- A one-off board-presence polling feature or a hard-coded connected-board
  checker.
- Letting the provider poll raw server tools directly while another server tool
  is running. The brain mediates checkpoint observation and verdicts.
- Token-by-token provider streaming. This spec covers server/client action
  checkpoints, not provider prose streaming.
- A broad killable pyOCD worker/job redesign for connect, flash, recover, or
  other in-process vendor calls. That belongs to Module H/process hygiene or a
  later worker isolation spec.
- Reintroducing model-governed host file/build actions. Build/external command
  checkpointing applies to product-owned runtime jobs, not stale
  `TurnDecision` host actions.
- Replacing final verification. Checkpoints improve early detection and
  cancellation; they do not substitute for the final observed result.

## Reconciliation summary

- Build plan: Stage 5 already requires chunked stream checkpoints for high-payoff
  flows and says not to broaden the prototype into the pyOCD worker/job layer.
  This spec makes that requirement concrete by adding a provider-visible
  observation buffer mediated by the brain.
- Current code: `src/pyocd_debug_mcp/brain/loop.py` calls server tools through
  a single awaited request/response path,
  `src/pyocd_debug_mcp/brain/mcp_client.py` waits for one final tool result,
  and `src/pyocd_debug_mcp/server.py` tools return final strings. UART capture
  polls internally but does not expose intermediate null-read/stall/bad-read
  observations to the provider. The operator shell renders `provider_progress`,
  tool starts, completions, evidence summaries, and raw output toggles, but it
  has no checkpoint buffer UI.
- Other docs or notes: `things-to-change.md` Prototype Priority item 9 and
  detailed entry #21 require stream checkpoints for UART/build/client-action
  flows. `R12_P_SPLIT.md` assigns this to Wave 2 Module E. `UXLayer.md` already
  names chunked checkpoints as Pass 2 follow-up work.
- Disagreements resolved here: the desired behavior is not a provider-specific
  "check if board connected" shortcut. It is a generic mid-tool observation
  design where the provider can notice bad or empty reads before a long timeout,
  while the brain keeps the board/action boundary authoritative.

## Design

### Checkpoint job model

Long-running actions should be represented internally as checkpoint-capable
jobs. The implementation may choose whether the first prototype exposes these as
separate MCP tools, internal server jobs, or brain/client-side task objects, but
the product behavior must preserve one logical action from the provider's point
of view.

Each job should have:

- `job_id`
- `action_id` or turn/action correlation id
- `tool_name` or action kind
- `session_id`
- `board_id` where applicable
- `started_at`, `last_update_at`, `elapsed_ms`
- requested timeout and effective brain/server timeout
- current status: `running`, `succeeded`, `failed`, `cancel_requested`,
  `cancelled`, `cleanup_uncertain`, or `timed_out`
- latest chunks from stdout, stderr, UART, or client-action observations
- counters for bytes/chunks read, empty polls, no-new-data duration, and stall
  intervals
- typed signals such as `matched_expected_text`, `unexpected_text`,
  `bad_read`, `null_read`, `no_data_yet`, `stall_detected`, and
  `early_error`
- cleanup state for cancelled jobs

Checkpoint records are telemetry and tool observations, not hidden
chain-of-thought. They may be shown to the provider and, in developer mode, to
the operator.

### Supported stream sources

UART reads:

- Emit a first checkpoint if no useful data appears before the configured early
  interval.
- Append compact serial chunks when data appears.
- Mark `null_read` or `no_data_yet` when polls return nothing.
- Mark `bad_read` or `unexpected_text` when output contradicts the expected
  pattern or known product semantics.
- Preserve the existing final UART result semantics after the job succeeds,
  fails, times out, or is cancelled.

Builds and external commands:

- Capture stdout/stderr chunks with byte and line counters.
- Emit progress when output advances, when the process stalls, and when a clear
  compiler/tool error appears before process exit.
- Support cancellation with process-tree cleanup where possible. Full
  process-hygiene guarantees coordinate with Module H.

Client actions:

- Emit checkpoints from long script/client-action execution.
- Route any server-native calls inside a client action through the existing
  governed brain gate.
- Do not let checkpoint turns start unrelated board work while the original
  client action is still active.

### Provider checkpoint turns

The provider should not poll the server directly. The brain decides when to
surface checkpoints based on configured cadence, meaningful new observations,
stall markers, and the action deadline. The provider receives a compact
checkpoint context and must return a typed checkpoint verdict.

Valid first-version verdicts:

- `continue`: keep waiting for the current job.
- `cancel`: stop the job and return the cancellation observation.
- `adjust`: apply a narrow allowed adjustment, such as a shorter remaining wait,
  a longer wait inside hard caps, or a revised expected text pattern if the
  original action type supports that safely.

Invalid checkpoint behavior:

- requesting a different board/server tool;
- performing a new governed action while the original job is active;
- treating ordinary provider prose as authoritative;
- bypassing the final `TurnDecision` boundary after the job completes.

The checkpoint turn should be bounded by a small provider timeout and a small
prompt. It should include only the task context needed to decide whether this
same job should continue or stop.

### Cadence and caps

The implementation must define project defaults and hard caps. Suggested first
prototype defaults:

- first checkpoint after roughly three seconds without useful data for
  UART/build/client-action jobs;
- subsequent checkpoints every five to ten seconds, or sooner on significant
  new output, early error, bad read, or stall transition;
- a maximum number of checkpoint turns per action to prevent provider spin;
- a final forced result when the action deadline is reached.

The brain owns these limits. Provider-suggested waits or timeout adjustments are
clamped by the existing timeout policy.

### Cancellation and cleanup

Cancellation must be product-real, not just a prompt label:

1. The brain records `cancel_requested`.
2. The server/client job stops reading or terminates the process/action where
   possible.
3. The job releases serial ports, subprocess handles, and client-action
   resources it owns.
4. The final observation records `cancelled` or `cleanup_uncertain`.
5. The next provider turn receives that final observation before any new
   governed action is accepted.

For pyOCD/vendor calls that cannot be safely interrupted in-process today, this
spec requires explicit non-support labeling rather than fake cancellation.

### Operator UX

Current behavior:

- `pyocd-debug-brain run` is the stable headless surface and prints final
  summary text.
- `pyocd-debug` is the operator shell. It currently renders live provider
  progress lines such as `provider [provider_request] ...`, tool start/finish
  lines, Evidence Summary panels after provider turns, and raw provider output
  when raw mode is enabled or final-output rendering applies.

Final-product target:

- Normal operator mode should show concise progress: what action is running,
  elapsed time, whether output is arriving, and important stall/error/checkpoint
  conclusions.
- Normal operator mode should not flood users with provider dispatch internals
  like `Dispatching Codex CLI turn` unless verbose/developer output is enabled.
- Evidence summaries are useful product output, but they should be concise and
  should avoid hidden chain-of-thought. They may remain visible by default if
  they describe observations, classification, hypothesis summary, strategy, and
  next action in product terms.
- Developer/inspector mode should expose detailed checkpoint buffers, raw
  provider checkpoint verdicts, prompt snippets, server observations, and event
  artifacts.

## Board facts as data and origin tags

Checkpoint records must include board identity and source tags without copying
machine-local facts into tracked config:

- `board_id` comes from the existing board selection/config flow.
- probe UID, serial port, process id, and runtime paths are session-local
  provenance only.
- UART semantics such as baud and expected text continue to come from
  board/runtime config, not ad hoc prompt text.
- Checkpoint artifacts should use repo-relative paths where possible and
  session-local absolute paths only as provenance.

## Documentation plan

Update these current docs with this spec as the Module E design anchor:

- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/UXLayer.md`
- `markdowns/current-progress.md`
- `markdowns/curr/README.md`
- `README.md`

The existing `markdowns/ROADMAP.md` and
`markdowns/firmware_agent_build_plan_concrete (10).md` already require
checkpoints, but they should point at the provider-visible observation-buffer
shape so future implementation does not collapse it into a generic timeout or a
board-presence special case.

## Portability

- Must work on Windows and macOS for product-owned subprocess/build jobs.
- Must avoid shell-specific quoting as the checkpoint/job control path.
- Must preserve UTF-8-with-replacement output capture for external commands.
- Must keep serial/resource cleanup explicit on cancellation.
- Must degrade clearly when a platform cannot interrupt a specific action.

## Verification plan

Software-side tests:

- Unit tests for checkpoint record serialization and truncation.
- Unit tests for cadence/cap decisions and timeout clamping.
- Fake UART stream tests for:
  - data arrives before first checkpoint;
  - repeated null reads trigger checkpoints;
  - unexpected text triggers a bad-read checkpoint;
  - provider `cancel` stops the job and records cleanup state.
- Fake build/external-command tests for stdout/stderr chunks, compiler-error
  early observation, stall checkpoint, and cancellation.
- Fake client-action tests for chunk emission and checkpoint verdict handling.
- Brain-loop tests proving checkpoint turns only accept checkpoint verdicts and
  cannot start unrelated governed actions.
- UX tests proving normal mode is concise and inspector/developer mode can show
  detailed buffers.

Product-behavior tests:

- Simulated Codex and Claude provider responses where the provider receives a
  checkpoint context, chooses continue on useful progress, cancels on repeated
  null reads, and returns a normal final `TurnDecision` after the job completes.
- Multi-prompt shell smoke where each user prompt is one loop and checkpoint
  artifacts do not leak between prompts.
- No-hardware full suite rows for all relevant software behavior. Hardware rows
  are only required when a later implementation touches real board I/O in a way
  that cannot be faithfully simulated.

## Acceptance criteria

- Long UART/build/client-action waits no longer remain opaque until final
  timeout.
- The provider can inspect a brain-surfaced checkpoint buffer and decide
  continue/cancel/adjust before final timeout.
- Checkpoint turns are bounded and cannot execute unrelated board work.
- Cancellation records real cleanup status.
- Normal user output is concise; detailed buffers and provider dispatch details
  are available through developer/inspector output.
- Final action results and the final `TurnDecision` boundary remain
  authoritative.

## Verified

- Current code has event/progress rendering, final tool-result handling, and
  internal UART polling, but it does not yet implement provider-visible
  mid-tool checkpoint buffers.
- The relevant planning anchors are Prototype Priority item 9, detailed entry
  #21, R12 Wave 2 Module E, and UX Pass 2.

## Pending verification

- No implementation has been written for this spec.
- Exact checkpoint schemas, event names, CLI flags, and provider-verdict models
  remain to be implemented and validated in the Wave 2 Module E branch.
