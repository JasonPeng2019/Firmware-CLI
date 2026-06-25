# R12 P-Split Parallel Work Plan

## Purpose

This file defines the parallel branch schedule for the `R12` prototype.

The goal is not to make the code unusual. Each branch should use normal,
concrete Python modules, dataclasses/Pydantic models only where they fit, and
plain helper functions. The point is to keep three parallel branches from all
rewriting the same orchestration files.

Rule of thumb:

- steps inside one branch are serial
- branches inside one wave are parallel
- the next wave starts only after the prior wave's required dependencies land
- broad edits to `brain/loop.py`, `brain/actions.py`, `brain/cli.py`, and
  `server.py` are serialized integration work

## Simple Schedule

```text
SERIAL:
  P0 foundation

PARALLEL WAVE 1:
  Branch A: provider session + tool schema prompt
  Branch B: action boundary + batches + client actions
  Branch C: event spine + timeout policy

PARALLEL WAVE 2:
  Branch D: progress UI + inspector
  Branch E: stream checkpoints
  Branch F: scoped green approval

SERIAL:
  G final integration + acceptance cleanup
```

## P0 Foundation - Serial First

`P0` lands before any long-lived parallel branch starts.

Purpose:
create the smallest concrete shared shapes and hook points so later branches do
not all edit `loop.py` and `actions.py` differently.

Modules:

1. `src/pyocd_debug_mcp/brain/decision_types.py`
   - final board decision shape
   - `ActionCall`
   - `ActionBatch`
   - early-exit verdicts
   - timeout proposal fields
   - iteration estimate fields
2. `src/pyocd_debug_mcp/brain/events.py`
   - `BrainEvent`
   - event kinds
   - simple event sink/callback shape
3. `src/pyocd_debug_mcp/brain/provider_types.py`
   - provider response shape
   - provider session state fields
4. `src/pyocd_debug_mcp/timeouts.py`
   - shared timeout config/update shape if the existing file does not already
     cover it
5. `src/pyocd_debug_mcp/brain/client_actions.py`
   - empty/minimal client-action store shape only
6. Tiny hook points in:
   - `brain/loop.py`
   - `brain/actions.py`
   - `brain/cli.py`

P0 should not implement the full features. It should preserve current behavior
and add tests for parsing/serialization and no-op hooks.

## Wave 1 - Three Parallel Branches

After `P0` lands, Branch A, Branch B, and Branch C can run in parallel.

### Branch A - Provider Session + Tool Schema Prompt

Serial order inside Branch A:

1. `provider_types.py`
   - finalize provider session fields from `P0`
2. Provider adapters:
   - `provider_openai.py`
   - `provider_anthropic.py`
   - `provider_codex_cli.py`
   - `provider_claude_cli.py`
   - `provider_factory.py`
3. `tool_schemas.py`
   - read real MCP tool descriptions/schemas
   - render the model-facing prompt bundle
4. Small integration hook:
   - `loop.py` consumes provider session state and schema bundle through the
     `P0` hook

Parallel with:

- Branch B module 1 through module 4
- Branch C module 1 through module 4

Should not own:

- action execution
- timeout clamp rules
- CLI progress rendering

### Branch B - Action Boundary + Batches + Client Actions

Serial order inside Branch B:

1. `action_policy.py`
   - classify model-native host actions vs governed server-native actions
2. `host_actions.py`
   - host-only command/file/script execution path
3. `action_batch.py`
   - ordered action batches
   - batch result aggregation
   - batch-level failure behavior
4. Basic action additions:
   - `wait`
   - UART write
   - small `server.py` wrappers only if needed
5. `client_actions.py`
   - session-scoped script create/update/run
   - route server-native calls back through the brain gate

Parallel with:

- Branch A module 1 through module 4
- Branch C module 1 through module 4

Cross-branch dependency:

- Branch B module 3 may consume Branch A's schema shape only after `P0`; it
  should not wait for Branch A's full implementation.
- Branch B module 5 is needed by Wave 2 Branch E and Branch F.

Should not own:

- provider sessions
- inspector rendering
- timeout default/clamp rules

### Branch C - Event Spine + Timeout Policy

Serial order inside Branch C:

1. `events.py`
   - finish event kinds from `P0`
   - event sink helpers
2. `timeout_policy.py`
   - parse model timeout/iteration proposals
   - apply brain clamps
   - build server timeout-sync requests
3. `src/pyocd_debug_mcp/timeouts.py`
   - shared defaults and clamp ranges
   - no competing timeout source
4. Timeout consumption hooks:
   - providers consume provider timeout values
   - tool calls consume action timeout values
   - server timeout sync uses partial updates

Parallel with:

- Branch A module 1 through module 4
- Branch B module 1 through module 5

Cross-branch dependency:

- Branch C module 4 may touch provider adapters after Branch A's provider
  session fields are stable. If that would conflict, split it into a tiny
  integration patch after Branch A lands.
- Branch C module 1 and module 2 are required by Wave 2 Branch D and Branch E.

Should not own:

- batch semantics
- client-action execution
- inspector UI

## Wave 2 - Three Parallel Branches

Wave 2 starts after Wave 1 dependencies are available:

- Branch D needs Branch C module 1.
- Branch E needs Branch B module 5 and Branch C module 1/module 2.
- Branch F needs Branch B module 5 if green tests use client actions.

### Branch D - Progress UI + Inspector

Serial order inside Branch D:

1. `cli_progress.py`
   - render live progress from `BrainEvent`
2. `inspector.py`
   - write prompt turns, provider stream text, parsed decisions, tool calls,
     server observations, and state snapshots
3. CLI hook:
   - `cli.py` exposes progress/inspector flags through a small integration edit

Parallel with:

- Branch E module 1 through module 4
- Branch F module 1 through module 3

Should not own:

- event shape redesign
- timeout clamp rules
- action execution semantics

### Branch E - Stream Checkpoints

Serial order inside Branch E:

1. `stream_checkpoints.py`
   - checkpoint records
   - continue/cancel verdict
   - stall policy
2. Build/external-command chunking:
   - `workspace.py`
3. UART read chunking:
   - UART read path emits chunks and observes cancellation
4. Client-action chunking:
   - `client_actions.py` emits chunks and observes cancellation

Parallel with:

- Branch D module 1 through module 3
- Branch F module 1 through module 3

Cross-branch dependency:

- Branch E module 4 depends on Branch B module 5.
- Branch E uses Branch C timeout/event shapes, but does not own them.

Should not own:

- pyOCD flash/connect/recover worker design
- green approval logic

### Branch F - Scoped Green Approval

Serial order inside Branch F:

1. `green_approval.py`
   - manual/human-confirmed model-made test flow
2. Narrow flipped-value gate:
   - model supplies script, parameters, correct values, flipped values
   - brain accepts pass-correct/fail-flipped only
3. Evidence/result capture:
   - use existing state/evidence helpers

Parallel with:

- Branch D module 1 through module 3
- Branch E module 1 through module 4

Cross-branch dependency:

- If green tests run as client actions, Branch F module 1 waits for Branch B
  module 5.

Should not own:

- provider sessions
- server tools
- general benchmark scoring outside the narrow prototype gate

## G Final Integration - Serial Last

After Wave 2 lands, do one short serial integration branch.

Owns:

- final wiring in `brain/loop.py`
- final wiring in `brain/actions.py`
- final wiring in `brain/cli.py`
- final server wrapper cleanup in `server.py`
- acceptance tests/docs cleanup

Rules:

- no feature should first be implemented in this branch
- this branch wires already-owned modules together
- any broad rewrite here means a prior branch split was wrong

## Shared Files Rule

These files are shared integration points:

- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/cli.py`
- `src/pyocd_debug_mcp/server.py`

During Wave 1 and Wave 2, a branch may touch those files only for a small hook
to its owned module. Broad edits to these files happen in `P0` or `G`, not in
parallel branches.

## Conflict Escalation Rule

If a branch cannot proceed without broad edits to another branch's owned module
or to a shared integration file, stop and update this plan before coding
further. That means the dependency is serial and should be moved into `P0`,
into the other branch, or into final integration.

## Verified

- This file is a coordination plan only.
- It is aligned with the current `R12` prototype target in the build plan and
  roadmap.

## Pending Verification

- The exact module names should be checked against implementation reality when
  `P0` starts.
- No code behavior has been changed by this document.
