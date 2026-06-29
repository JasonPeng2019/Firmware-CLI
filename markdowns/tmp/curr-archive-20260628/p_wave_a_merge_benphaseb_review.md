# Review: P-Wave-A + benPhaseB Integration

## Verdict

**CLEAN FOR NON-HARDWARE BRANCH-A MERGE REVIEW**

`P-Wave-A` now has the intended Branch A behavior: provider session state,
remote continuation for the providers that expose handles, canonical local
memory, prompt-delta rendering, live MCP tool-schema prompting, response
semantics in the tool-schema overlay, provider progress events, and the P0
timeout/planning hooks.

The prior `CHANGES REQUESTED` findings in this file are now resolved in code:

- OpenAI resumed turns use remote-delta rendering instead of re-sending the full
  static tool/decision schema block every turn.
- Disconnect teardown uses the invocation timeout config.
- Tool-schema prompting includes curated response/refusal semantics.
- The benchmark module CLI exposes the same timeout/planning flags as the main
  brain CLI.
- Provider progress updates are emitted by runtime providers and consumed by the
  loop as `provider_progress` events.

## Verified In This Review Pass

Non-hardware ladder rerun on `P-Wave-A`:

- `uv run pytest -q` -> `288 passed`
- `uv run ruff check .` -> pass
- `uv run mypy src` -> pass
- `uv build --wheel` -> pass
- `uv run pyocd-debug --help` -> pass
- `uv run pyocd-debug-brain --help` -> pass

## Not Proved Here

This review did not run hardware or live provider sessions. These remain proof
gaps, not known code failures:

- fresh official scoped-pair hardware rerun on `nrf52833dk + nucleo_l476rg`
- full second-provider official-pair closure
- fresh Windows/macOS user-computer deployment proof
- multi-prompt operator CLI proof where several top-level prompts run back to
  back, each with its own internal provider/tool loop and isolated artifacts
- real code-writing repair proof under each intended provider class

## Remaining Product Work

Branch A is clean enough for non-hardware merge review, but it is not the final
deployment product. The current subscription-backed Codex and Claude adapters
use CLI resume handles as the compatibility bridge:

- Codex: `codex exec resume <thread_id>`
- Claude: `claude --print --resume <session_id>`

Future hardening direction:

- move Codex to SDK/app-server style thread and turn APIs when ready;
- keep Claude subscription use as BYO local Claude Code CLI unless Anthropic
  approves subscription/rate-limit use through another product surface;
- use Anthropic API / future Claude Agent SDK only for API-key or approved use;
- harden Anthropic API memory into an outcome-bearing debugging ledger before
  claiming parity with Claude Code CLI or OpenAI Responses.

## Verified

- non-hardware Branch A ladder is green
- stale review findings are fixed in current code
- docs now distinguish current CLI resume bridge from final SDK/session adapter
  goals

## Pending Verification

- hardware/provider proof listed above
- deployment-readiness ladder in `markdowns/curr/r12_turnkey_spec.md`
