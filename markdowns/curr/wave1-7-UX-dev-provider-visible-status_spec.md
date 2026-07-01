> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Wave 1.7 UX Dev Provider-Visible Status Trace

## Goal in plain English

Task: Wave 1 dev-side provider-visible status and reasoning trace bridge.
Roadmap anchor: R12 Stage 5 turnkey brain, Prototype Priority item #8
visibility/debuggability, as a narrow Wave 1 bridge before the full Wave 2
Module D/H provider-stream and interrupt implementation.

Give developers a practical way to see provider-visible status/reasoning text
while a Codex CLI or Claude CLI provider turn is still running. This is a
debugging bridge, not the full product UX. It should help catch a provider going
off course, doing surprising host work, or silently waiting, without exposing
hidden chain-of-thought, raw prompt bundles, or messy JSON to normal users.

This spec deliberately does less than
`markdowns/curr/wave2-provider-stream-interrupt_spec.md`: no user interrupt
contract, no partial-work review, no full inspector panes, and no normal-user
default streaming requirement. It is a Wave 1 developer trace layer that should
be small, useful, and safe to land before Wave 2.

## Scope and non-scope

In scope:

- A developer-only opt-in mode for `pyocd-debug-brain run`,
  `pyocd-debug-brain benchmark`, and the interactive `pyocd-debug` shell.
- Live or near-live display of provider-visible stdout/stderr/status text from
  `codex-cli` and `claude-cli` provider turns when the provider backend emits
  such text before the final result.
- Brain-owned waiting heartbeats in dev trace mode when a provider backend does
  not emit live text.
- Provider-turn boundary messages with provider, model, continuation path,
  prompt render mode, and elapsed time.
- Append-only dev trace artifacts that preserve what the developer saw and
  separate that stream from the final structured `TurnDecision`.
- Strict non-authoritative treatment of streamed provider-visible text: it is
  displayed/logged only and never parsed for actions, timeout changes, success
  claims, or board access.
- A clear fallback for providers that cannot stream visible text yet: show
  heartbeats during the wait, then save captured final raw provider output in
  dev artifacts after the turn completes.
- Tests that prove the trace is live for simulated CLI providers, bounded for
  silent providers, and does not alter structured decision parsing.

Out of scope:

- Hidden chain-of-thought exposure or reconstruction.
- Making provider-visible text the source of truth for any brain decision.
- Normal operator mode streaming by default.
- User-interruptible provider turns, Ctrl-C cancellation, process-tree cleanup,
  and partial-work review. Those remain Wave 2 Module D/H work.
- Full developer inspector panes, prompt snapshots, state snapshots, server
  traffic panes, or a tailing `inspect` command. This spec may produce artifacts
  that the future inspector consumes, but it does not build the inspector.
- Mid-tool checkpoint buffers for UART/build/client-action streams. That remains
  Wave 2 Module E.
- Broad provider SDK rewrites. Use the current CLI-provider wrappers unless a
  tiny provider-specific streaming flag is necessary and verified.
- Hardware validation. This is a dev-side CLI/provider visibility feature and
  can be validated with fake providers and no-hardware provider smoke tests.

## Reconciliation summary

- Build plan: Stage 5 requires visible progress and developer inspector output
  as part of the turnkey brain product direction. It also says the brain remains
  the owner of prompts, parsed decisions, evidence, timeout policy, and run
  artifacts. The build plan allows Wave 2 to implement full provider-turn
  streaming/cancellation, but it does not forbid an earlier developer-only
  bridge.
- Current code: `provider_codex_cli.py` and `provider_claude_cli.py` call
  provider CLIs with `subprocess.run(..., capture_output=True)`, so any
  provider-visible text remains unavailable until the subprocess exits. The
  loop emits `provider_turn_start`, `provider_progress`, and
  `provider_turn_complete`, and the shell renderer displays coarse progress,
  but there is no live provider-visible chunk event. `ProviderProgressUpdate`
  exists but is returned with the completed `ProviderTurn`, so it is not live.
- Other docs or notes: `things-to-change.md` entry #19 calls for live provider
  progress with separate authoritative decisions. Entry #20 calls for a
  developer inspector. `UXLayer.md` says the UX should expose structured
  summaries and provider-visible text, not hidden chain-of-thought.
  `wave2-provider-stream-interrupt_spec.md` owns the full provider-visible
  stream, user interrupt, partial-work, and cleanup feature.
- Disagreements: there is no conflict with the build plan. The only ambiguity
  is scheduling: current docs place the full feature in Wave 2, but the user now
  wants a smaller Wave 1 dev-only bridge. This spec resolves that by keeping
  the Wave 2 product contract intact and adding only an opt-in dev trace that
  does not promise cancellation, normal-user UX, or hidden reasoning exposure.

## Design

### Product contract

The Wave 1 quick fix must add a developer trace mode, not a new control path.
The trace may show:

- provider dispatch/resume status;
- provider-visible stdout/stderr/status text;
- provider-visible reasoning summaries if the provider itself emits them;
- brain-owned wait heartbeats;
- retry/schema-repair notices;
- final raw provider output only in dev/raw artifacts or explicit dev trace
  output, never as the normal user default.

The trace must not show or claim:

- hidden chain-of-thought;
- reconstructed private reasoning;
- raw prompts by default;
- raw JSON decision payloads in the normal operator view;
- streamed prose as authoritative action input.

The final validated `TurnDecision`, provider-native tool call, or structured
provider result remains the only input the brain trusts.

### CLI surface

Add one simple opt-in switch family:

- `pyocd-debug-brain run --dev-provider-trace ...`
- `pyocd-debug-brain benchmark --dev-provider-trace ...`
- interactive shell command: `/dev-provider-trace on|off`
- optional environment default:
  `PYOCD_TURNKEY_DEV_PROVIDER_TRACE=0|1`

Names may be shortened during implementation only if the docs, tests, and shell
help stay consistent. Do not overload `--raw-output`; raw output controls what
is printed after completion, while dev provider trace controls live provider
visibility during the turn.

Automation defaults stay quiet. The flag should be off by default for
`pyocd-debug-brain` command-line automation and benchmark runs.

### Event model

Use the existing brain event sink instead of inventing a second console path.
Add either new event kinds or a clearly typed `provider_progress` subtype. The
preferred event names are:

- `provider_visible_text`
- `provider_wait_heartbeat`
- `provider_dev_trace_artifact`

Each record should carry stable fields where available:

- provider
- model
- iteration
- continuation path
- prompt render mode
- provider runtime working directory
- stream name: stdout, stderr, status, or heartbeat
- elapsed milliseconds
- chunk index
- text or artifact reference
- whether the text is provider-visible, brain-owned, or captured-final

If implementation reuses `provider_progress`, the `details.stage` field must be
specific enough to distinguish `provider_visible_text` from ordinary lifecycle
progress. Tests must assert this distinction.

### Provider adapter behavior

For `codex-cli` and `claude-cli`, trace-enabled execution must stop treating
the provider subprocess as an opaque captured wait:

1. Spawn the provider subprocess with stdin, stdout, and stderr pipes.
2. Feed the prompt through stdin without fragile shell quoting.
3. Read stdout/stderr incrementally with UTF-8 replacement decoding.
4. Emit dev trace events as chunks arrive.
5. Tee the same bytes into dev trace artifacts.
6. Continue to parse the final authoritative decision exactly as before:
   - Codex prefers the `-o <turn_decision.json>` output artifact.
   - Claude keeps its strict final JSON/result extraction path unless a safer
     provider-supported artifact path is introduced and verified.
7. Preserve existing retry behavior for invalid final structured output.
8. Preserve existing resume-failure behavior and metadata labels.

Non-trace mode may initially keep the current `subprocess.run` code path to
reduce Wave 1 risk, but trace mode must exercise the streaming runner. If the
implementation unifies both paths, it must prove no regression in return code,
timeout, retry, resume, output parsing, and provider-native skill projection.

### API-provider behavior

API providers do not have to implement full token streaming in this Wave 1
bridge. In dev trace mode they must at least emit brain-owned heartbeats while
waiting and record final raw provider metadata/output in dev artifacts where
the existing adapter already has it.

OpenAI/Anthropic live streaming can remain Wave 2 unless the implementation can
add it without weakening structured-output parsing. Credentials-free simulated
API tests should still cover the heartbeat fallback.

### Artifacts

Write append-only trace artifacts under the current run root when one exists.
Before a board session creates a final run root, write to the provider runtime
or provisional run directory and record the path in a brain event.

Preferred artifact names:

```text
logs/provider_dev_trace.log
logs/provider_dev_trace.jsonl
logs/provider_dev_trace_artifacts.json
```

The artifact contract must separate:

- provider-visible text seen during the turn;
- brain-owned heartbeat/status messages;
- captured final raw provider output;
- final trusted structured decision.

Do not replace `model_turns.jsonl`, `brain_events.jsonl`, or
`turn_decision.json`; this feature adds debug visibility beside those records.

### Renderer behavior

When dev provider trace is enabled, the terminal should render concise live
lines such as:

```text
[provider:codex-cli] checking available files
[provider:codex-cli] editing runtime copy
[brain] waiting for provider: 60s / 300s
```

The renderer should avoid dumping raw JSON lines by default. If the provider
emits JSON event envelopes, the dev trace renderer should either:

- extract a provider-visible text/status field when one is known and safe; or
- show a compact event label and write the raw line to the artifact.

Raw JSON remains available through raw/dev artifacts, not as the normal trace
line. If extraction rules are provider-specific, tests must cover them.

### Prompt guidance

When dev provider trace is enabled, the prompt may include a short instruction
asking the provider to emit concise provider-visible progress/status text during
long work. The instruction must be clear that:

- progress text is for the operator only;
- the final structured decision is still required;
- hidden/private reasoning should not be exposed or relied on;
- concise summaries such as "reading context", "checking build", or "preparing
  final decision" are preferred over verbose deliberation.

Do not add this prompt text to normal non-trace turns unless a later product
spec asks for it.

### Implementation files

Expected implementation touch points:

- `src/pyocd_debug_mcp/brain/provider_types.py`
  - add a minimal provider trace event/callback type, or extend provider call
    context so adapters can emit events before returning a `ProviderTurn`;
  - keep the `DecisionProvider` contract explicit and testable.
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
  - add trace-enabled streaming subprocess execution while preserving output
    artifact parsing and thread resume.
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
  - add trace-enabled streaming subprocess execution while preserving final JSON
    extraction, session resume, and fork retry.
- `src/pyocd_debug_mcp/brain/loop.py`
  - wire dev trace settings into provider turns and event/artifact recording;
  - do not parse streamed provider-visible text as decisions.
- `src/pyocd_debug_mcp/brain/config.py`, `brain/app.py`, `brain/cli.py`,
  `brain/benchmark.py`
  - carry the setting through freeform and benchmark paths.
- `src/pyocd_debug_mcp/ux/shell.py`, `ux/commands.py`, `ux/renderer.py`
  - expose `/dev-provider-trace on|off`, render trace events, and keep shell
    help accurate.
- Tests under `tests/`
  - add fake streaming provider/subprocess coverage, CLI parser coverage,
    renderer coverage, and no-regression provider parsing tests.

## Board-facts-as-data and origin tags

- No board facts are introduced by this feature.
- Provider trace settings are `PROJECT-DEFINED` runtime/CLI behavior.
- Provider subprocess PIDs, runtime directories, output paths, and chunk indexes
  are session-local provenance, not tracked board config.
- Do not add board-specific branches, probe IDs, serial ports, or hardware
  constants to implement this feature.
- If a provider cannot emit live text on a platform, record that as provider
  capability/evidence, not as a board fact.

## Documentation plan

When this spec is accepted and implemented, update:

- `markdowns/things-to-change.md`
  - mark a Wave 1 dev-trace bridge as implemented separately from the full
    Wave 2 provider stream/interrupt item.
- `markdowns/current-progress.md`
  - record what is implemented, what was tested, and what remains Wave 2.
- `markdowns/R12_P_SPLIT.md`
  - add this as a Wave 1 addendum consumed by Wave 2 Module D/H, not a new
    replacement for Module D/H.
- `markdowns/ROADMAP.md`
  - clarify that full normal-user streaming/cancel remains Wave 2, while
    dev-only provider-visible trace is a Wave 1 bridge if implemented.
- `markdowns/UXLayer.md`
  - document the developer-visible behavior and the no-hidden-CoT line.
- `markdowns/curr/wave2-provider-stream-interrupt_spec.md`
  - mention that Wave 1 may provide a dev trace substrate, while Wave 2 still
    owns normal UX, interrupt, cleanup, and partial-work review.
- `markdowns/curr/README.md`
  - list this current spec and its status.
- CLI help and shell help for the new flag/command.

## Portability

- Streaming subprocess execution must work on Windows and macOS.
- Avoid shell-specific process control. Use argv arrays and Python subprocess
  primitives.
- Decode output as UTF-8 with replacement.
- Do not require terminal spawning.
- Non-TTY/piped shell operation must remain stable and parseable.
- Dev trace logs must use `pathlib` paths and portable newline handling.
- If a provider emits CR-only progress, ANSI control sequences, or partial JSON
  lines, the artifact must preserve enough raw text for debugging while the
  live renderer stays readable.

## Verification plan

Software tests:

- Unit test a fake CLI process/runner that emits stdout/stderr chunks before a
  final valid decision artifact; assert trace events arrive before final parse.
- Unit test a silent fake provider; assert dev heartbeats appear and timeout
  behavior remains bounded.
- Unit test invalid final structured output with streamed provider text; assert
  retry behavior remains unchanged and streamed text is not parsed as the
  decision.
- Unit test Codex JSON-line output extraction: known provider-visible/status
  fields render cleanly, raw JSON stays in artifacts.
- Unit test Claude JSON/final-result extraction remains compatible with current
  output parsing.
- CLI parser tests for `--dev-provider-trace` on run and benchmark.
- Shell parser/help tests for `/dev-provider-trace on|off`.
- Renderer tests proving dev trace mode prints provider-visible lines and
  normal mode remains unchanged.
- Artifact tests proving provider dev trace logs are written and referenced.

Product behavior checks:

- No-hardware fake-provider run through `run_freeform_task` with dev trace on:
  observe live trace events and a valid final `TurnDecision`.
- No-hardware CLI smoke for `pyocd-debug-brain run --dev-provider-trace` using a
  fake or monkeypatched provider path.
- No-hardware interactive shell smoke that toggles `/dev-provider-trace on`,
  runs a simulated provider task, and shows trace output.
- Credentials-free API-provider simulation proving heartbeat fallback.
- Optional local Codex CLI and Claude CLI live no-hardware smoke if auth is
  available; absence of auth is not a hardware or implementation blocker but
  must be reported honestly.

Full validation after implementation:

- Ruff/format for changed Python.
- Pyright full gate or changed-file diagnostic classification if a pre-existing
  baseline blocks full green.
- Focused pytest for provider adapters, loop events, CLI/shell controls, and
  UX renderer.
- Relevant no-hardware suite ladder.
- No hardware-specific tests are required unless implementation touches
  board/session cleanup or server-side hardware behavior.

## Acceptance criteria

- Developers can opt into dev provider trace from headless run, benchmark, and
  interactive shell paths.
- With trace enabled, Codex CLI and Claude CLI provider turns are not completely
  opaque: provider-visible stdout/stderr/status text is displayed/logged as it
  arrives when the provider emits it.
- With trace enabled and no provider-visible text available, the brain emits
  waiting heartbeats with elapsed time and provider timeout.
- Normal/default output remains unchanged enough for automation and does not
  dump provider JSON or raw prompts.
- Hidden chain-of-thought is not exposed, reconstructed, or required.
- Streamed provider-visible text is never parsed for actions, arguments,
  timeout changes, final status, or board decisions.
- Final structured decision parsing remains strict and uses the same
  authoritative channels as before.
- Existing provider resume, retry, memory sync, provider-native skill
  projection, and prompt accounting metadata continue to work.
- Trace artifacts are written and discoverable from events/run artifacts.
- The implementation leaves Wave 2 Module D/H scope intact: user interrupt,
  cleanup, partial-work review, normal-user streaming policy, and full
  inspector remain separate future work.

## Verified

- Current Wave 2 provider stream/interrupt spec exists at
  `markdowns/curr/wave2-provider-stream-interrupt_spec.md` and owns the full
  product feature.
- Current `codex-cli` and `claude-cli` adapters use captured subprocess calls,
  so provider-visible text is not available until provider completion.
- Current shell renderer already receives brain events and can display provider
  progress events, but current provider progress updates are returned only after
  the provider turn completes.
- No hardware validation is needed to specify this dev-side feature.

## Pending verification

- No implementation has been written for this spec.
- Exact CLI flag names can still be adjusted during implementation if all docs
  and tests agree.
- Provider-specific live output shapes must be verified against the installed
  Codex CLI and Claude CLI versions on the implementation host.
- It remains unverified whether Claude CLI can provide meaningful incremental
  provider-visible text in the current `--print --output-format json` mode; if
  not, the accepted Wave 1 behavior is heartbeat plus captured-final dev
  artifact, with full provider streaming left to Wave 2.
