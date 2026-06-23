# R12 Jason/Ben Merge Notes

## Purpose

This document captures how to merge the strongest parts of the current `R12`
implementation on `benPhaseA` with the strongest internal design ideas from
`JasonPhaseA`.

The key conclusion is:

- keep the current `benPhaseA` `R12` as the outer product architecture
- selectively borrow cleaner internal boundaries and deterministic helpers from
  `JasonPhaseA`

This is not a recommendation to replace the current `R12` brain with the
`JasonPhaseA` runner. It is a recommendation to preserve the current product
shape while tightening the implementation with a few specific Jason-originated
ideas.

## Executive Summary

The current `benPhaseA` implementation is the better foundation for the actual
project goals because it is:

- provider-flexible
- turnkey/product-facing
- benchmark-comparable against `R11`
- structured around a real `run --board-id --task ...` workflow

`JasonPhaseA` has several strong internal ideas that are worth borrowing:

- a cleaner `ToolClientProtocol` / `ServerCommand` split
- host-aware local command execution for Windows vs POSIX
- stronger typed reasoning/evidence dataclasses
- deterministic workflow specs that can serve as internal playbooks or
  regression helpers

The correct merge strategy is:

- preserve the current outer `R12` brain
- adopt Jason’s internal abstractions under it
- do not replace the current product CLI or provider-driven loop with Jason’s
  narrower deterministic runner

## What Should Stay From The Current R12

The current branch should remain the outer architecture because it already
matches the intended `R12` product shape.

### 1. Keep the current turnkey brain as the top-level product

The current branch implements a real turnkey product path:

- freeform mode:
  - `pyocd-debug-brain run --board-id <id> --task "<text>"`
- benchmark mode:
  - `pyocd-debug-brain benchmark --case-id ...`
  - `pyocd-debug-brain benchmark --suite ...`

This is the right product abstraction because the user supplies a task, not an
internal skill ID.

Relevant files:

- [src/pyocd_debug_mcp/brain/cli.py](../src/pyocd_debug_mcp/brain/cli.py)
- [src/pyocd_debug_mcp/brain/config.py](../src/pyocd_debug_mcp/brain/config.py)
- [src/pyocd_debug_mcp/brain/loop.py](../src/pyocd_debug_mcp/brain/loop.py)
- [src/pyocd_debug_mcp/brain/benchmark.py](../src/pyocd_debug_mcp/brain/benchmark.py)
- [markdowns/curr/r12_turnkey_spec.md](../markdowns/curr/r12_turnkey_spec.md)

### 2. Keep the provider-flexible architecture

The current branch already supports the provider model the project is now moving
toward:

- `openai-api`
- `anthropic-api`
- `codex-cli`
- `claude-cli`

That is a major architectural advantage because it supports both:

- API-credit usage
- subscription-backed CLI usage

Relevant files:

- [src/pyocd_debug_mcp/brain/config.py](../src/pyocd_debug_mcp/brain/config.py)
- [src/pyocd_debug_mcp/brain/provider_factory.py](../src/pyocd_debug_mcp/brain/provider_factory.py)
- [src/pyocd_debug_mcp/brain/provider_openai.py](../src/pyocd_debug_mcp/brain/provider_openai.py)
- [src/pyocd_debug_mcp/brain/provider_anthropic.py](../src/pyocd_debug_mcp/brain/provider_anthropic.py)
- [src/pyocd_debug_mcp/brain/provider_codex_cli.py](../src/pyocd_debug_mcp/brain/provider_codex_cli.py)
- [src/pyocd_debug_mcp/brain/provider_claude_cli.py](../src/pyocd_debug_mcp/brain/provider_claude_cli.py)

### 3. Keep the current benchmark-comparable R12 path

The current `R12` benchmark layer is intentionally tied to the frozen `R11`
corpus and scoring story. That is important because `R12` is supposed to prove
turnkey value against the same task surface, not against a different benchmark.

Relevant file:

- [src/pyocd_debug_mcp/brain/benchmark.py](../src/pyocd_debug_mcp/brain/benchmark.py)

### 4. Keep the current model-driven outer loop

The current loop is genuinely a turnkey brain:

- provider asks the model for a structured next action
- the client executes that action
- the loop updates verification and convergence state
- the loop can inspect files, replace files, rebuild, and green-check

That better matches the intended product than a purely deterministic skill
runner.

Relevant files:

- [src/pyocd_debug_mcp/brain/actions.py](../src/pyocd_debug_mcp/brain/actions.py)
- [src/pyocd_debug_mcp/brain/loop.py](../src/pyocd_debug_mcp/brain/loop.py)
- [src/pyocd_debug_mcp/brain/state.py](../src/pyocd_debug_mcp/brain/state.py)

## What Should Be Borrowed From JasonPhaseA

These are the Jason-originated ideas that are worth incorporating.

## 1. Borrow the transport boundary

This is the cleanest and safest improvement.

### Current problem

The current MCP client in
[src/pyocd_debug_mcp/brain/mcp_client.py](../src/pyocd_debug_mcp/brain/mcp_client.py)
is doing too many jobs at once:

- default server spawn configuration
- stdio MCP lifecycle
- tool invocation
- tool-result flattening
- text parsing for `session_id`, `probe_uid`, `route_used`, refusal codes, and
  block codes
- higher-level convenience wrappers like `connect()`, `flash_firmware()`, and
  `read_serial()`

That makes the transport layer too coupled to the product layer.

### Jason idea worth adopting

Jason’s `mcp_client.py` separates:

- `ServerCommand`
- `ToolClientProtocol`
- one concrete stdio client implementation
- a typed flattened tool response

Relevant reference:

- `origin/JasonPhaseA:src/pyocd_debug_mcp/brain/mcp_client.py`

### Recommended merge approach

Do not replace the entire current file with Jason’s file. Instead:

1. Keep the current `ToolTextResult` because it already captures useful parsed
   metadata:
   - `session_id`
   - `probe_uid`
   - `route_used`
   - refusal/block codes
2. Introduce Jason-style `ServerCommand`
3. Introduce Jason-style `ToolClientProtocol`
4. Split the client into two layers:
   - a low-level `StdioToolClient` or equivalent transport-only client
   - a higher-level brain-facing wrapper that adds the current parsed
     convenience behavior

### Why this is better

This gives the current branch:

- cleaner testing seams
- cleaner server startup injection
- clearer separation of transport vs product logic
- easier future changes to server launch behavior

without giving up the richer current parsed response behavior.

### Concrete target

Refactor:

- [src/pyocd_debug_mcp/brain/mcp_client.py](../src/pyocd_debug_mcp/brain/mcp_client.py)

Likely introduce:

- `ServerCommand`
- `ToolClientProtocol`
- a lower-level stdio tool client
- a higher-level parsed wrapper used by the loop

## 2. Borrow Jason’s host-aware local command execution

This is the most clear-cut technical improvement.

### Current problem

The current workspace build path always shells through `bash`:

- [src/pyocd_debug_mcp/brain/workspace.py](../src/pyocd_debug_mcp/brain/workspace.py)

Specifically, `WorkspaceSession.run_build()` runs:

- `["bash", "-lc", build_command]`

That is a portability weakness on Windows.

### Jason idea worth adopting

Jason’s runner uses host-aware shell dispatch:

- `cmd.exe /d /s /c ...` on Windows
- `bash -lc ...` on POSIX

Relevant reference:

- `origin/JasonPhaseA:src/pyocd_debug_mcp/brain/runner.py`

### Recommended merge approach

Keep the current workspace abstraction, but add a tiny host-aware shell helper:

- `_shell_command_for_host(command: str) -> list[str]`
- `_run_local_command(command: str, cwd: Path, timeout_seconds: float = ...)`

Then make `WorkspaceSession.run_build()` use that helper instead of hardcoding
`bash`.

### Why this is better

This strengthens:

- Windows support
- predictable cross-platform build execution
- the repair path in freeform mode
- the benchmark rebuild path

without changing the user-facing product behavior.

### Concrete target

Refactor:

- [src/pyocd_debug_mcp/brain/workspace.py](../src/pyocd_debug_mcp/brain/workspace.py)

Do not change:

- path containment
- diff capture
- edit-root enforcement

Only improve:

- host-aware process spawning

## 3. Borrow Jason’s typed reasoning/evidence dataclasses

This should be adopted, but under the current loop rather than instead of it.

### Current problem

The current branch has:

- good action/result typing in
  [src/pyocd_debug_mcp/brain/actions.py](../src/pyocd_debug_mcp/brain/actions.py)
- a mutable runtime state in
  [src/pyocd_debug_mcp/brain/state.py](../src/pyocd_debug_mcp/brain/state.py)
- raw `model_turns` and `brain_trace` in
  [src/pyocd_debug_mcp/brain/loop.py](../src/pyocd_debug_mcp/brain/loop.py)

That is usable, but it is lighter and less structured than it should be if
later scoring and comparison need to reason about:

- what was observed
- what was hypothesized
- what intervention was attempted
- what strategy was chosen

### Jason idea worth adopting

Jason’s typed dataclasses are strong:

- `Observation`
- `Hypothesis`
- `Experiment`
- `StrategyEvaluation`

Relevant reference:

- `origin/JasonPhaseA:src/pyocd_debug_mcp/brain/models.py`

### Recommended merge approach

Do not replace the current `TurnDecision` and action schema.

Instead:

1. Keep [actions.py](../src/pyocd_debug_mcp/brain/actions.py) as the model
   action contract
2. Add a new typed evidence module:
   - `brain/evidence.py`
   - or expand into a new `brain/models.py`
3. Extend the loop to record evidence objects as the run progresses
4. Serialize that evidence into the run artifacts

### Why this is better

This improves:

- explainability of turnkey runs
- benchmark interpretation
- later scoring richness
- comparison between providers

without sacrificing the current provider-driven architecture.

### Concrete target

Add a new typed evidence layer under:

- `src/pyocd_debug_mcp/brain/`

Then thread that into:

- [src/pyocd_debug_mcp/brain/loop.py](../src/pyocd_debug_mcp/brain/loop.py)
- `turnkey_result.json`
- `turnkey_state.json`
- `brain_trace.jsonl`

## 4. Borrow deterministic workflow specs as internal playbooks

This is the highest-risk item conceptually, so it needs the most discipline.

### Current problem

The current branch only has one “skills” concept:

- prompt/context skills in `skills/common/` and `skills/mcu_families/`

Those are useful for model guidance, but they are not the same thing as fixed
executable workflows.

### Jason idea worth adopting

Jason’s `skills/turnkey/*.yaml` files are really deterministic workflows:

- static health-check flow
- deterministic diagnose flow
- deterministic repair flow
- recover cycle

Relevant references:

- `origin/JasonPhaseA:skills/turnkey/reference-health-check.yaml`
- `origin/JasonPhaseA:skills/turnkey/reference-contract-diagnose.yaml`
- `origin/JasonPhaseA:skills/turnkey/reference-contract-repair.yaml`
- `origin/JasonPhaseA:skills/turnkey/nordic-recover-cycle.yaml`

### Recommended merge approach

Do not overload the existing `skills/` concept.

Use two distinct concepts:

- **Prompt/context skills**
  - the current branch’s `skills/common/` and `skills/mcu_families/`
  - used to influence model reasoning
- **Deterministic playbooks/workflows**
  - Jason-style executable step sequences
  - used for fixed known procedures

### Important naming recommendation

Do not call both of these simply “skills”.

Use a separate name for the deterministic Jason-style layer, such as:

- `playbooks`
- `workflows`
- `macros`

### Where these playbooks fit well

Good uses:

- internal green-check helper
- internal known-good health-check helper
- internal recover/reflash/reverify helper
- benchmark preflight/prep flows
- regression testing helpers

Bad uses:

- replacing the freeform `--task` product CLI
- replacing the provider-driven loop as the core of `R12`
- requiring the operator to choose `--skill-id` as the main product path

### Why this is the right boundary

If you expose Jason’s deterministic workflow model as the primary user-facing
product, you lose too much of the intended turnkey value.

If you keep it as an internal helper layer, you gain:

- more predictable fixed procedures
- stronger regression coverage
- cleaner fallback logic
- reusable benchmark plumbing

without turning the whole product into an internal script engine.

## What Should Not Be Borrowed Wholesale

Several Jason design choices should not be copied directly.

### 1. Do not replace the current CLI shape

Jason’s CLI is workflow-driven:

- `run --board-id ... --skill-id ...`

That is useful internally, but it is the wrong top-level product interface for
the current `R12`.

The current product-facing shape is better:

- `run --board-id ... --task ...`
- `benchmark --case-id ...`
- `benchmark --suite ...`

### 2. Do not replace the provider layer with the deterministic runner

The current project direction now explicitly wants:

- API providers
- subscription-backed CLI providers
- multiple provider paths under one product layer

Jason’s implementation does not validate that architecture. Replacing the
current branch with that runner would move the project backward.

### 3. Do not reintroduce stale board-scope assumptions

Jason’s branch still centers too much of its `R12` story around `nrf52840dk`.

The current scoped pair is:

- `nrf52833dk`
- `nucleo_l476rg`

Do not reintroduce old board-truth or stale test assumptions while borrowing
internal design ideas.

### 4. Do not replace the current benchmark-comparison story

The current `R12` is deliberately tied to the frozen `R11` corpus for
comparability.

Jason’s turnkey benchmark layer introduces more turnkey-specific scoring logic.
That can be useful later, but it should not replace the current baseline
comparison story during `R12` closure.

## Recommended Integration Order

The order matters. The safe sequence is:

### Step 1. Refactor the transport boundary

First introduce:

- `ServerCommand`
- `ToolClientProtocol`
- split transport-only vs parsed brain-facing client behavior

Why first:

- low conceptual risk
- high code-health value
- improves testing and portability immediately

### Step 2. Fix host-aware workspace command execution

Next make local build/process execution host-aware.

Why second:

- clearly better
- low product risk
- improves Windows behavior immediately

### Step 3. Add typed evidence models

Next introduce:

- observations
- hypotheses
- experiments
- strategy evaluations

Why third:

- useful for analysis and later scoring
- improves trace quality
- still does not change the current product surface

### Step 4. Introduce deterministic playbooks as helpers

Only after the client boundary and evidence model are cleaned up should you add
Jason-style deterministic workflows as internal helpers.

Why fourth:

- this is the highest conceptual risk
- it is easy to accidentally blur playbooks with the main brain architecture
- adding it later makes the boundary easier to preserve

## Target Merged Architecture

The merged design should look like this:

### Outer layer: keep the current R12 product

- current provider-flexible turnkey brain
- current `run` and `benchmark` CLI
- current structured `TurnDecision` model
- current benchmark comparison story against `R11`

### Middle layer: cleaner Jason-inspired internal boundaries

- transport protocol and server-command abstraction
- host-aware local command execution
- typed evidence dataclasses
- cleaner internal artifact writing

### Inner helper layer: deterministic playbooks

- reusable fixed health-check flow
- reusable recover/reflash flow
- benchmark prep helpers
- regression and fallback helpers

This gives:

- the current branch’s correct product direction
- Jason’s cleaner implementation boundaries

without collapsing the current turnkey brain into a deterministic script engine.

## Concrete File-Level Plan

### 1. `brain/mcp_client.py`

Refactor:

- [src/pyocd_debug_mcp/brain/mcp_client.py](../src/pyocd_debug_mcp/brain/mcp_client.py)

Add:

- `ServerCommand`
- `ToolClientProtocol`
- lower-level stdio tool client
- higher-level parsed wrapper

Keep:

- `ToolTextResult`
- refusal/block/session/probe/route parsing
- product-facing convenience wrappers

### 2. `brain/workspace.py`

Refactor:

- [src/pyocd_debug_mcp/brain/workspace.py](../src/pyocd_debug_mcp/brain/workspace.py)

Add:

- host-aware shell command builder
- host-aware local command runner

Keep:

- path containment
- edit-root enforcement
- diff capture
- snapshot behavior

### 3. Evidence / model module

Add a new module such as:

- `src/pyocd_debug_mcp/brain/evidence.py`
  - or
- `src/pyocd_debug_mcp/brain/models.py`

Introduce:

- `Observation`
- `Hypothesis`
- `Experiment`
- `StrategyEvaluation`

Then thread those through:

- [src/pyocd_debug_mcp/brain/loop.py](../src/pyocd_debug_mcp/brain/loop.py)
- run metadata artifacts

### 4. Deterministic playbook layer

Add a distinct deterministic helper system under something like:

- `src/pyocd_debug_mcp/brain/playbooks.py`
- `playbooks/`
- or `skills/playbooks/`

Do **not** merge this into the existing prompt-skill loader without a separate
concept boundary.

Good first playbooks:

- reference health check
- recover -> reflash -> reverify
- fixed green-check regression helper

## Practical Merge Rule

The safest practical rule is:

> Adopt Jason’s cleaner internals. Keep Ben’s current product shape.

That means:

- do not replace the current outer loop
- do not replace the current CLI contract
- do not remove the multi-provider architecture
- do adopt the better transport seam
- do adopt the better host-aware command execution
- do adopt the stronger typed evidence model
- do adopt deterministic workflow specs only as internal playbooks or regression
  helpers

## Final Recommendation

If this merge is executed correctly, the result should be:

- more portable
- easier to test
- easier to analyze after a run
- more internally disciplined

while still remaining:

- provider-flexible
- benchmark-comparable
- product-facing
- genuinely turnkey

That is the correct merge target for the current `R12` direction.
