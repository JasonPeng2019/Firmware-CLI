> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Wave 2 Provider-Visible Stream And Interrupt

## Goal in plain English

Make long provider turns visible and interruptible before the provider returns
its final raw output or final structured decision. During a Codex CLI, Claude
CLI, or API-provider turn, the operator should see provider-visible status text
and brain-owned heartbeats as they happen, and the operator should be able to
cancel the in-flight provider turn before the brain trusts a final decision or
dispatches new board work.

This is not hidden chain-of-thought streaming. It is a product visibility and
safety feature: show public/provider-exposed direction text, status events,
brain progress, and workspace/tool activity; keep hidden reasoning private and
never reconstruct it. The authoritative control boundary remains the final
validated `TurnDecision`, provider-native tool call, or checkpoint verdict.

Task: Wave 2 provider-visible stream and user interrupt design.
Roadmap anchor: R12 Wave 2 Module D progress UI + inspector, with required
cancel/cleanup support from Module H and interaction points with Module E
stream checkpoints and Module G codebase-map/partial-edit review.

## Scope and non-scope

In scope:

- Live provider-visible text/status streaming during provider turns, before the
  final provider output is available.
- Brain-owned waiting heartbeats when a provider backend cannot emit live text.
- User-visible provider turn boundaries such as "Codex turn started" and
  "Claude evaluating result."
- A normal operator view that shows concise public direction trace:
  observation, hypothesis summary, strategy, risk/uncertainty, progress, and
  changed-file summary where available.
- A developer/inspector view that shows exact dispatch events, prompt metadata,
  provider-visible stream logs, raw final provider output, parsed decisions,
  checkpoint buffers, and state snapshots.
- Ctrl-C or equivalent operator cancellation while a provider turn is running.
- Provider subprocess/API request cancellation with real cleanup/audit state.
- Partial-work detection after interruption, especially provider-native file
  edits in the runtime/workspace.
- Run artifacts/events that distinguish visible provider text from the final
  decision object the brain trusted.

Out of scope:

- Exposing hidden chain-of-thought, reconstructing hidden reasoning, or making
  hidden reasoning a product contract.
- Parsing streamed prose for board actions, timeout changes, file changes, or
  final status.
- Treating provider-visible status text as proof that an action is safe.
- Letting the provider call raw server tools while a different action is
  running.
- Replacing the mid-tool checkpoint design in
  `wave2-midtool-checkpoints_spec.md`; this spec is about the provider turn
  itself, while checkpoints are about long server/client actions after a tool
  or client action has started.
- A full web UI.
- A broad provider SDK rewrite unless needed to satisfy streaming or
  cancellation through the provider's official supported surface.

## Reconciliation summary

- Build plan: Stage 5 requires normalized progress events, CLI streaming,
  developer inspector output, bounded provider paths, and checkpoint/cancel
  behavior for high-payoff streams. This spec makes the provider-turn part of
  that requirement precise: status text and cancellation must happen before the
  final provider output, while structured decisions remain authoritative.
- Current code: `src/pyocd_debug_mcp/brain/provider_codex_cli.py` and
  `src/pyocd_debug_mcp/brain/provider_claude_cli.py` use
  `subprocess.run(..., capture_output=True)` for CLI provider turns. That means
  the operator sees no provider text until the subprocess exits. The providers
  return coarse `ProviderProgressUpdate` records only after the turn completes.
  `src/pyocd_debug_mcp/brain/loop.py` emits `provider_turn_start`,
  `provider_progress`, and `provider_turn_complete` events, but it has no
  live provider chunk event. `src/pyocd_debug_mcp/ux/shell.py` catches
  `KeyboardInterrupt` at the prompt loop, not as an in-flight provider-turn
  cancellation contract.
- Other docs or notes: `things-to-change.md` entry #19 already says visible
  provider/brain stream is operator visibility only and the structured decision
  artifact is authoritative. Entry #20 requires a developer inspector. Entry
  #24 requires process/session cleanup after interrupts. `UXLayer.md` currently
  records Pass 1 as turn-level progress and raw output after completed turns,
  with token/provider streaming deferred.
- Disagreements resolved here: normal users should not be blind during provider
  turns, and developers should be able to inspect exact provider turn traffic.
  But neither user nor developer should be promised hidden chain-of-thought.
  The product must expose provider-visible text and public direction summaries,
  not private reasoning internals.

## Design

### Visibility contract

The product has three visibility tiers:

1. Headless automation (`pyocd-debug-brain`):
   - remains final-output oriented and scriptable;
   - writes stream/interrupt artifacts when enabled or when an interruption
     occurs;
   - handles process interrupt safely and exits with a typed cancellation or
     failure result instead of leaving children behind.
2. Normal operator CLI (`pyocd-debug`):
   - shows provider turn start/finish, elapsed time, and brain heartbeats;
   - shows provider-visible status/reasoning text if the backend emits it;
   - shows concise public direction trace: observation, classification,
     hypothesis summary, strategy, risks/uncertainties, current action, and
     changed-file summary where available;
   - shows tool/build/board/client-action progress and final results;
   - hides raw prompt bundles, raw JSON decisions, raw checkpoint buffers,
     raw provider final output, and messy internal state unless the operator
     enables raw/verbose output.
3. Developer/inspector:
   - shows exact provider dispatch events, prompt snapshots or prompt hashes
     according to redaction policy, provider-visible stream chunks, raw final
     provider output, parsed decision objects, checkpoint buffers, tool/server
     observations, brain state snapshots, cleanup records, and artifact paths.

Normal users should be able to understand what the product is doing and stop it
if it is going off course. Developers should be able to debug prompt/provider
traffic. Neither mode should expose hidden chain-of-thought.

### Authoritative decision boundary

Provider-visible stream text is not control input. The brain may display and log
it, but it must not parse it for:

- server/native tool names or arguments;
- timeout or iteration updates;
- client-action names or inputs;
- final classifications or success claims;
- board access decisions;
- checkpoint verdicts.

The brain trusts only the final structured object for the relevant boundary:

- `TurnDecision` JSON or provider-native tool/function call for normal turns;
- typed checkpoint verdict for Module E checkpoint turns;
- typed cancellation result from the runtime when the user interrupts.

If a provider turn is cancelled before a final structured decision is accepted,
the brain must not parse partial output as a decision and must not dispatch a
new governed board/client action from that partial output.

### Provider streaming runner

CLI providers must stop using opaque `subprocess.run(..., capture_output=True)`
for long provider turns. The Wave 2 implementation must introduce a reusable
streaming provider runner with:

- asynchronous or nonblocking stdout/stderr consumption;
- UTF-8-with-replacement decoding;
- tee to live events and `provider_stream.log`;
- timeout handling that records elapsed time and whether output was still
  advancing;
- process-tree provenance for Module H cleanup;
- support for provider output artifacts such as Codex `-o <output_path>`;
- safe final parsing from an authoritative artifact or final structured output,
  not from arbitrary streamed prose.

API providers should use provider streaming APIs where available. If a provider
API cannot stream text reliably without weakening structured-output parsing, the
adapter may keep the current non-streaming structured request but must emit
brain-owned waiting heartbeats such as elapsed time, provider name, model, and
timeout budget.

### User interrupt and cancellation

While a provider turn is running, Ctrl-C or an equivalent shell command should
mean "cancel the in-flight turn," not "wait until the provider call finishes."

Required behavior:

1. Emit `provider_turn_cancel_requested` with provider, model, turn index,
   elapsed time, and run root if known.
2. Stop accepting new governed actions from the current provider turn.
3. Terminate the provider subprocess/process tree where possible, or cancel the
   API request task where the SDK/runtime supports cancellation.
4. If a board/server/client action is already active, coordinate with the
   action's owner:
   - Module E owns checkpoint job cancellation for UART/build/client-action
     streams.
   - Module H owns process-tree, MCP, pyOCD, serial, and board-session cleanup.
5. Record `provider_turn_cancelled` or `provider_turn_cancel_cleanup_uncertain`
   with exact cleanup outcome.
6. Return a typed run result such as `cancelled_by_user` or a structured
   tooling/cancelled result. The result must not look like a provider refusal
   or successful finalization.

Headless mode should also handle process interrupt with the same cleanup path.
It may print a minimal cancellation summary, but it must still preserve the
artifact/audit trail.

### Partial provider-native work after interruption

Provider-native CLIs may edit files in the runtime or workspace before the
brain receives a final decision. After cancellation or provider failure, the
brain must detect and surface partial work before any later governed action is
trusted.

Hard requirements:

- snapshot relevant workspace/runtime file state before provider turn start
  using git status, hashes, a file watcher, or a conservative inventory;
- after cancellation, record changed files and a diff summary;
- preserve the provider runtime directory and stream logs long enough for
  review;
- normal UX shows a concise partial-work summary and asks for explicit next
  intent before continuing in an interactive session;
- inspector/dev output can show full diffs and exact changed paths;
- no silently committed/applied provider changes;
- no governed board action after an interrupted provider-native edit until the
  partial work is reviewed, discarded, or incorporated by a fresh provider turn.

This coordinates with Wave 2 Module G. If provider-native file changes remain,
the codebase-map maintenance/replay rule applies before the next governed
action is trusted.

### Event and artifact schema

The implementation should extend the event stream with first-class event kinds
or equivalent records:

- `provider_visible_stream_chunk`
- `provider_visible_stream_closed`
- `provider_wait_heartbeat`
- `provider_turn_cancel_requested`
- `provider_turn_cancelled`
- `provider_turn_cancel_cleanup_uncertain`
- `workspace_change_detected`
- `partial_diff_available`
- `partial_work_review_required`
- `inspector_provider_record`

Each event should carry stable fields where applicable:

- `session_id`
- `provider`
- `model`
- `turn_index`
- `provider_handle_kind`
- `provider_handle_id`
- `continuation_path`
- `prompt_render_mode`
- `elapsed_ms`
- `stream_name` (`stdout`, `stderr`, API text delta, provider status)
- `chunk_text` or `chunk_ref`
- `chunk_index`
- `run_root`
- `cleanup_status`
- `changed_files`
- `diff_ref`

Artifacts should separate public/operator, inspector, and authoritative data:

- `runs/<session_id>/logs/provider_stream.log`
- `runs/<session_id>/logs/provider_stream.jsonl`
- `runs/<session_id>/logs/provider_visible_status.jsonl`
- `runs/<session_id>/logs/provider_interrupts.jsonl`
- `runs/<session_id>/logs/partial_work.diff`
- existing `model_turns.jsonl`, `brain_events.jsonl`, and prompt/decision
  artifacts

If no board session exists yet, the provisional run root must still capture
these artifacts and later move/link them into the final run root if a real
session is created.

### UX policy

Normal default output should show enough to supervise the agent:

- provider turn started/completed/cancelled;
- elapsed waiting status;
- provider-visible status text when present;
- concise public evidence/direction summaries;
- action/tool/build progress;
- changed-file and partial-work summaries;
- final status and artifact pointers.

Normal default output should not show:

- hidden chain-of-thought;
- raw prompt bundles;
- raw JSON `TurnDecision` objects;
- raw provider final output unless `/raw on`, `/raw last`, or an explicit
  `--raw-output` policy is active;
- raw checkpoint buffers;
- internal next-action JSON dumps in the Evidence Summary panel.

The current Evidence Summary panel should be tightened during implementation:
keep observation, classification, hypothesis, strategy, risk/uncertainty, and a
human-readable next-step label; move full action payloads and raw JSON to
inspector/raw output.

### Relationship to Wave 2 modules

Primary ownership:

- Module D owns provider-visible stream rendering, normal/verbose/inspector UX,
  event display, and public direction trace policy.
- Module H owns cancellation cleanup, provider subprocess/process-tree reaping,
  MCP/serial/pyOCD/board-session cleanup, and orphan audits.

Required integrations:

- Module E consumes the same event/log foundation but owns mid-tool checkpoint
  buffers after a server/client action has started.
- Module G owns codebase-map maintenance and decision replay after
  provider-native file changes.
- Final integration wires cancellation from shell/headless entrypoints through
  the provider runner, loop, and cleanup guard.

This should not become a new top-level Wave 2 module unless implementation
conflicts prove D/H cannot own it cleanly.

## Board facts as data and origin tags

- Provider stream/cancel records must use existing board/session identity
  fields; no probe UID, port, PID, or local path becomes tracked board config.
- Process IDs, provider handles, runtime directories, and local absolute paths
  are session-local provenance.
- Provider/model names come from `TurnkeyInvocation`/provider config and are
  `PROJECT-DEFINED` runtime metadata, not board facts.
- Cleanup uncertainty must be explicit; do not claim a board or process is clean
  unless the run actually proved it.

## Documentation plan

Update these docs when this spec is accepted and again when implemented:

- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/UXLayer.md`
- `markdowns/ROADMAP.md`
- `markdowns/firmware_agent_build_plan_concrete (10).md`
- `markdowns/current-progress.md`
- `markdowns/curr/README.md`
- `markdowns/curr/r12_turnkey_spec.md`
- `markdowns/curr/wave2-midtool-checkpoints_spec.md`
- `markdowns/firmware_agent_mcp_architecture.md`
- `README.md`

The implementation should also update `markdowns/repo_file_index.md` if it
adds new modules such as a provider stream runner, inspector module, or process
hygiene module.

## Portability

- Streaming subprocess execution must work on Windows and macOS.
- Do not rely on shell-only process group behavior as the only cleanup path.
- Prefer argv arrays, task files, JSON files, and provider output files over
  fragile shell quoting.
- Decode provider output as UTF-8 with replacement.
- Treat terminal spawning for inspector output as optional; log-only/tail mode
  must work everywhere.
- If a platform/provider cannot cancel a request cleanly, record
  `cleanup_uncertain` and fail/stop safely instead of pretending cancellation
  was complete.

## Verification plan

Software-side tests:

- Unit tests for provider stream chunk events and artifact writing.
- Fake CLI-provider tests that emit stdout/stderr slowly, then return a final
  valid decision artifact.
- Fake CLI-provider tests where the operator cancels before the final decision;
  assert no decision is parsed and no governed action is dispatched.
- Fake CLI-provider tests where cancellation leaves changed files; assert diff
  summary and partial-work review are required before later governed actions.
- Fake timeout tests where output continues and where output stalls.
- API-provider tests with simulated streaming text deltas and non-streaming
  heartbeat fallback.
- UX renderer tests for normal vs raw/inspector behavior, including no raw JSON
  action payload in the default Evidence Summary.
- Process-hygiene tests that simulate a hung provider child and prove
  provenance-based cleanup records are emitted.

Product-behavior tests:

- Simulated Codex and Claude CLI turns that stream public direction text, then
  return a valid `TurnDecision`.
- Simulated long provider turn cancelled by the user before final output.
- Multi-prompt `pyocd-debug` shell smoke where each prompt has its own run root,
  stream log, and no leaked cancellation state.
- Inspector smoke showing provider stream text, prompt metadata, parsed
  decision, and cleanup records.
- No-hardware full product suite rows for software behavior. Hardware tests are
  required only when implementation changes board/session cleanup in a way that
  needs real probe/serial proof.

## Acceptance criteria

- `codex-cli` and `claude-cli` provider turns no longer remain opaque until the
  subprocess exits.
- Normal operator mode shows provider-visible status/progress text or a
  brain-owned heartbeat before final provider output.
- Normal operator mode does not expose hidden chain-of-thought, raw prompt
  bundles, raw JSON decisions, or raw final provider output by default.
- Developer/inspector mode can show the exact provider-visible stream, raw final
  provider output, prompt metadata, parsed decisions, server/tool observations,
  state snapshots, and cleanup records.
- User interrupt during a provider turn stops the current turn, prevents partial
  output from becoming an action, and records cancellation/cleanup state.
- Provider subprocess/API cancellation is best-effort real cleanup, with
  `cleanup_uncertain` explicitly recorded when the product cannot prove cleanup.
- Provider-native partial file changes after interruption are detected and
  surfaced before any later governed action is trusted.
- The final structured decision/checkpoint object remains the only
  authoritative input to the brain.

## Verified

- Current code has a structured event spine and operator shell rendering for
  coarse provider/tool progress.
- Current CLI provider adapters still use captured subprocess execution, so
  provider-visible text is not streamed before the turn completes.
- Current shell handles `KeyboardInterrupt` at the prompt loop, but there is no
  provider-turn cancellation contract.

## Pending verification

- No implementation has been written for this spec.
- Exact event class names, CLI flags, provider-stream artifact filenames, and
  cancellation result status names must be finalized during Wave 2 Module D/H
  implementation.
- Real provider streaming behavior must be proven separately for each provider
  surface because Codex CLI, Claude CLI, OpenAI Responses, and Anthropic
  Messages expose different streaming/structured-output mechanics.
