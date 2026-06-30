> STATUS: SUPERSEDED EXECUTION PLAN - Claude CLI refresh proof was later run
> under `markdowns/curr/branch-a-live-provider-hardware-suite_process.md`.
> The API-provider portion remains pending until paid OpenAI/Anthropic credits
> are available. The run IDs recorded in that process ledger are historical
> local runtime outputs; this checkout does not currently contain the
> `runs/20260629T03...` / `04...` / `17...` / `18...` artifact directories
> for reinspection.

# r12 claude refresh hardening test plan

## Goal in plain English

This file records the deferred test intent that existed before the later live
provider refresh. Claude CLI usage later refreshed and the attached-board
Claude/Codex validation moved to
`markdowns/curr/branch-a-live-provider-hardware-suite_process.md`. Keep this
file only as the API-provider and exact-test-intent record; do not read it as
the latest Claude CLI status.

Roadmap anchor: R12.

## Scope and non-scope

In scope:

- Real Claude CLI smoke after usage refresh.
- Real Codex CLI smoke if a fresh comparison run is useful.
- Paid Anthropic/OpenAI API provider smoke only when credits are explicitly
  available.
- Artifact inspection for action payloads and MCP tool arguments.
- A scaled Claude green bar that is strongly indicative of longer-session
  behavior without requiring long benchmark loops.
- Multiple top-level user prompts in the same continued Claude/CLI workflow,
  with shorter provider loops per prompt.

Out of scope:

- No schema redesign.
- No new benchmark case family unless the smoke exposes a real regression.
- No claim of official hardware closure unless the scoped boards are attached
  and verified by silicon/probe/serial facts.
- No exhaustive two-board, multi-case Claude matrix on a basic Claude Pro
  window. That matrix is useful but not the default refresh test.
- No single-prompt-only Claude closure. A one-prompt smoke is useful as a
  preflight, but it is not sufficient for the deferred Claude green bar.

## Reconciliation summary

- Historical fact: Claude CLI usage was exhausted during the live Branch A/B
  proof, which is why this plan was written.
- Follow-up fact: Claude quota refreshed on 2026-06-29, and the later
  Branch A live-provider suite records successful attached-board Claude CLI
  health and code-writing repair proof on `nucleo_l476rg + nrf52840dk`.
- Current blocked fact: Anthropic/OpenAI API provider runs require paid credits
  that are not currently available.
- This plan now exists so the remaining paid API-provider pass can start
  without rebuilding the test intent from memory.

## Design

Run a minimal but real multi-user-prompt provider sequence that is likely to
catch provider-shape and continuation regressions while staying cheap enough for
Claude Pro:

1. Start with one attached board only. Prefer the already proven board with the
   least setup friction.
2. Use two required top-level user prompts in the same continued workflow;
   prefer three if usage headroom is still comfortable after prompt two.
3. Keep each user prompt short and explicit. Avoid broad natural-language
   benchmark instructions and avoid asking for exploratory narration.
4. Cap each user prompt to a small provider loop. Target `max_iters=2` per user
   prompt, with `max_iters=3` allowed only for the first prompt if connection or
   board setup needs one extra step.
5. Required prompt shape:
   - User prompt 1: concise healthy-board proof. Connect, perform one short
     read/write or state check, finalize.
   - User prompt 2: concise follow-up that relies on the continued session or
     saved context. Re-check one signal or ask for a small additional
     observation, then finalize.
   - User prompt 3, preferred if budget allows: minimal code-writing or
     workspace-change proof. Use the simplest one-line repair or tiny file
     update case and stop after one successful verify. Skip this prompt if the
     first two prompts already consume too much Claude usage.
6. Prefer batched actions when possible: `connect`, optional short `wait`, one
   serial read/write or status read, then finalization.
7. Inspect run artifacts to confirm no selected MCP tool receives an unexpected
   `tool_name` argument.
8. Use local harness/unit tests for injected conflict cases. Do not spend Claude
   turns trying to coerce a live model into emitting malformed conflicting JSON
   unless a real artifact shows that shape.

The lower green bar is acceptable because the parser/policy behavior is already
covered by unit tests and Codex provider-shape smoke. The Claude run must prove
the real Claude CLI adapter can still produce parseable decisions across
multiple user prompts that travel through the same hardened action path.

## Board-facts-as-data and origin tags

Record board ID, probe ID, serial port, silicon identity, provider CLI version,
session ID, and run artifact directory for every live run.

## Documentation plan

- Update `markdowns/curr/r12-server-tool-action-hardening_process.md` with
  actual run IDs and verdicts.
- If a bug is found, create a focused fix-bug note or review finding before
  patching.

## Portability

Use repo commands and provider CLIs only. Do not encode provider-local paths or
board facts into source code.

## Verification plan

- First run after refresh, required:
  - Claude CLI, one attached board, two top-level user prompts in the same
    continued workflow.
  - Suggested cap: `max_iters=2` per user prompt; allow `max_iters=3` only for
    the first prompt if setup needs it.
  - Prompt 1 should be compact: identify the board, ask for one concise
    diagnosis/health proof, request batched actions where useful, and forbid
    exploratory narration.
  - Prompt 2 should be compact and continuation-sensitive: ask for one
    follow-up observation using the existing session/context, then finalize.
  - Inspect events/artifacts for action payloads, MCP tool arguments, and
    continuity across the two user prompts.
- Third prompt, preferred only if Claude usage is still comfortable:
  - One minimal code-writing or workspace-change proof on one board.
  - Use the simplest previously green case or a tiny one-line change, not the
    full benchmark suite.
  - Suggested cap: `max_iters=2`, stop after one successful verify.
- Optional comparison:
  - Codex CLI, same task and board, to verify provider-neutral behavior.
- Paid API checks when credits exist:
  - Anthropic API provider smoke.
  - OpenAI API provider smoke.

## Acceptance criteria

- Claude CLI completes at least two top-level user prompts in the same
  continued workflow, or fails only for an unrelated external provider/hardware
  reason documented with artifacts.
- Each required user prompt stays within the small-loop budget unless a real
  setup failure requires one additional provider turn.
- No `tool_name` field leaks into MCP arguments for namespaced server-tool
  calls.
- Conflicting namespaced/embedded tool names fail closed if observed or injected
  by a test harness.
- Run IDs and blocked/unblocked provider facts are recorded in the process
  ledger.
- The run does not attempt an exhaustive Claude matrix by default. Passing the
  two-prompt Claude smoke plus existing local/Codex coverage is sufficient
  green for this hardening feature under Claude Pro constraints.

## Verified

- Superseded for Claude CLI by
  `markdowns/curr/branch-a-live-provider-hardware-suite_process.md`.
- That process ledger records post-refresh Claude CLI health smokes and
  code-writing repair benchmark proof on the attached
  `nucleo_l476rg + nrf52840dk` pair.
- Current workspace audit: the historical Branch A `20260629T03...` /
  `04...` / `17...` / `18...` run IDs named by that process ledger are not
  present under local `runs/`, so this checkout cannot reinspect those specific
  artifacts without restoring the untracked run folders.

## Pending verification

- Anthropic/OpenAI API providers after paid credits are available.
- Exact official `nrf52833dk` proof for any claim that requires the official
  scoped Nordic board.
