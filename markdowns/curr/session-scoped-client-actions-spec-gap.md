# Session-Scoped Client Actions Spec Gap

## Status

`P-Wave-0` has a partial Branch B implementation for session-scoped client actions.

The current branch supports pre-registering a Python client-action script before a run and lets the provider call that registered script through `run_script(name, inputs)`. It does not yet let the provider create, update, or re-register session-scoped scripts during a run.

## Intended Branch B Behavior

Branch B was scoped to own the action boundary, batches, and client actions. For session-scoped scripts, the intended behavior is:

1. The provider can create a session-scoped script.
2. The provider can update an existing session-scoped script.
3. The provider can run a registered session-scoped script.
4. Script execution remains governed:
   - board/server actions still route through the brain gate;
   - scripts cannot bypass MCP/tool policy;
   - script details and hashes are inspectable in run artifacts;
   - script lifetime is limited to the current turnkey session/run.

## Current Implemented Behavior

Implemented today:

- `src/pyocd_debug_mcp/brain/client_actions.py` defines:
  - `ClientActionRecord`
  - `ClientActionSnapshot`
  - `ClientActionStore`
  - `InMemoryClientActionStore`
  - client-action loading from `NAME=PATH` specs
  - prompt rendering for registered client actions
  - gated script execution via `run_client_action(...)`
- `pyocd-debug-brain run` accepts repeatable `--client-action NAME=PATH` arguments.
- Freeform app setup loads those CLI-provided specs into a session-local store.
- The provider-visible action schema includes `run_script(name, inputs)`.
- The execution loop can run a registered script through `_execute_run_script(...)`.
- The injected script `server` object only exposes governed server-tool calls through the brain gate.
- Run metadata can persist `client_actions.json` with registered action names, hashes, and whether each action was executed.

## Current Gap

Missing today:

- no provider-visible `create_script` action;
- no provider-visible `update_script` action;
- no provider-visible `put_script` / `register_script` action;
- no loop path that converts provider-supplied script content into a `ClientActionRecord`;
- no policy checks for provider-created script content;
- no artifact trail for script creation/update events;
- no stale-snapshot rule for what happens if a script is updated after details were loaded;
- no tests proving provider create -> run or update -> run behavior.

The internal store has `put_action(record)`, but that method is not currently exposed through the provider action schema or execution loop.

## User-Visible Impact

A user can currently do this:

```bash
uv run pyocd-debug-brain run \
  --board-id nrf52833dk \
  --task "Use the registered helper script if needed." \
  --client-action helper=path/to/helper.py
```

Then the provider may call:

```json
{
  "action": {
    "kind": "run_script",
    "name": "helper",
    "inputs": {}
  }
}
```

But the provider cannot currently do this inside the session:

```json
{
  "action": {
    "kind": "create_script",
    "name": "helper",
    "content": "async def run(inputs, server):\n    return {'ok': True}\n"
  }
}
```

Nor can it revise that script with an `update_script` action and then run the updated version.

## Required Design Decision

Before implementation, choose the provider-facing action vocabulary. Recommended minimal vocabulary:

- `create_script(name, content, description?)`
- `update_script(name, content, description?)`
- `run_script(name, inputs)`

Alternative compact vocabulary:

- `put_script(name, content, description?, overwrite=true)`
- `run_script(name, inputs)`

The explicit `create_script` / `update_script` split is more inspectable and easier to test for accidental overwrite behavior.

## Implementation Requirements

### 1. Action schema

Add strict Pydantic action models in `brain/actions.py`:

- `CreateScriptAction`
- `UpdateScriptAction`

or a single `PutScriptAction` if that design is chosen.

Expose the chosen action kinds in:

- `ActionUnion`
- `turn_decision_output_schema()`
- batch action type values
- provider prompt action list

### 2. Store mutation API

Add a controlled mutation helper around `InMemoryClientActionStore.put_action(...)` that:

- validates the action name using the existing name rules;
- validates script content parses as Python;
- requires a `run(inputs, server)` function;
- rejects empty content;
- computes and returns a content hash;
- optionally rejects overwrite on `create_script` and requires existing record on `update_script`.

### 3. Runtime execution loop

Add execution branches in `_execute_batched_actions(...)` for the new script mutation actions.

Expected runtime behavior:

- create/update actions update the session-local store only;
- the result text includes script name, path/virtual path, description, and sha256;
- creation/update events are emitted into `brain_events.jsonl`;
- `state.last_action_summary` and `state.last_result_text` are updated;
- `state.loaded_client_action_details[name]` is either refreshed or invalidated after update.

### 4. Artifact persistence

Extend `client_actions.json` or add `client_action_events.jsonl` so run artifacts record:

- script name;
- creation/update timestamp or turn index;
- sha256 after each mutation;
- whether it was provider-created or CLI-registered;
- whether it was executed;
- final content hash.

Do not write provider-created executable content into arbitrary workspace paths unless explicitly designed as a separate export feature. The session-scoped store should remain session-local by default.

### 5. Safety and gating

Keep the current safety boundary:

- scripts receive only the gated `server` object;
- server calls still require loaded details before execution;
- server-native calls route through `_execute_server_tool(...)`;
- unsupported server tools are rejected;
- script content is session-scoped and not implicitly persisted to the repo/workspace.

Also decide whether imports are allowed. The current `run_client_action(...)` execution environment provides a small builtins set and no import function. If imports remain disallowed, document that as part of the script contract.

## Acceptance Criteria

The gap is closed when all of the following are true:

1. A provider can create a script during a turnkey run.
2. A provider can run the script it just created.
3. A provider can update that script during the same run.
4. Running the script after update uses the updated content/hash.
5. Script-created server calls still route through the governed brain/MCP path.
6. Script execution cannot call unallowed server tools.
7. Create refuses duplicate names unless overwrite semantics are explicitly chosen.
8. Update refuses missing names unless upsert semantics are explicitly chosen.
9. Script details in the prompt reflect the latest content hash after create/update.
10. Run artifacts record registered, created, updated, and executed scripts.
11. Tests cover create -> run, update -> run, missing script refusal, duplicate create refusal, invalid script refusal, and gated server-tool enforcement.

## Suggested Test Coverage

Add or extend tests around:

- `parse_client_action_spec(...)`
- provider-created script validation
- client-action store mutation semantics
- `turn_decision_output_schema()` includes the new action kinds
- `_actions_for_decision(...)` accepts the new action kinds
- `_execute_batched_actions(...)` can execute create -> run in one batch or across turns
- update invalidates or refreshes loaded details
- artifacts include final hashes and executed flags

## Summary

Current state: **pre-register and run works**.

Spec gap: **provider-created and provider-updated session-scoped scripts do not yet work**.

Closing this requires adding provider-visible script mutation actions, loop execution branches, store validation/mutation helpers, artifact tracking, and tests.
