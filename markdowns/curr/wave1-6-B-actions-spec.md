# Wave 1.6-B Client Actions And Native Skill Sync Spec Gap

> Status: PROPOSAL - not implemented. This replaces the older
> `create_script(name, content)` / `update_script(name, content)` framing and
> clarifies the skill-surface ownership vocabulary for Wave 1.6-B.

## Goal

Close the Branch B gap for model-authored client actions and model-created
skills without forcing script or skill bodies through `TurnDecision` JSON.

Providers should author files natively when the user asks for skill or script
creation. FirmCLI should then sync, validate, snapshot, register, and expose the
resulting assets through governed brain state.

Roadmap anchor: R12 Stage 5 Wave 1, Branch B action boundary, client actions,
provider-native skill bridge, and Prototype Priority item 14 in
`markdowns/things-to-change.md`.

Vocabulary authority:
`markdowns/curr/r12-skill-surface-ownership_spec.md`.

## Required Vocabulary

FirmCLI must distinguish these three surfaces.

### 1. Projected preloaded skills

Generated provider-visible runtime views of FirmCLI/client-owned actual skills.

Examples:

```text
<provider-runtime>/.codex/skills/<skill_id>/
<provider-runtime>/.claude/skills/<skill_id>/
```

Rules:

- The provider can see and use these through Codex/Claude native skill behavior.
- The provider must not treat these as the editable deliverable.
- They are disposable runtime scaffolding and can be regenerated.
- They should carry projection provenance such as
  `.firmcli-provider-native-projection.json`.
- Run diffs/scoring may hide only marker-proven projection subtrees, not every
  `.codex` or `.claude` path.

### 2. Actual skills to preload

FirmCLI/client-owned source packages or validated registry entries.

Examples:

```text
skills/model_native/<skill_id>/
skills/provider_native/common/<skill_id>/
skills/provider_native/codex/<skill_id>/
skills/provider_native/claude/<skill_id>/
<client-owned-skill-registry>/<skill_id>/
```

Rules:

- This is the store of record for packaged or validated skills.
- API providers use this through `load_skills` or a registry-backed equivalent.
- CLI providers receive generated projections from this surface.
- The provider does not directly see or natively edit this surface unless
  FirmCLI exposes a bounded runtime-copy repair flow.

### 3. User-owned skills

Target-workspace native skill folders that the user can see and own.

Examples:

```text
<target-workspace>/.codex/skills/<skill_id>/
<target-workspace>/.claude/skills/<skill_id>/
<target-workspace>/.agents/...
```

Rules:

- The provider can see these through normal workspace/native skill access.
- The provider may natively edit these only in a user-requested
  skill-authoring/sync flow.
- They are not trusted merely because they are native provider files.
- They must sync into the client-owned actual-skill registry before API fallback
  is considered successful.

## Provider Visibility And Edit Contract

| Surface | Provider can see? | Provider can natively edit? | Store of record? |
|---|---:|---:|---:|
| Projected preloaded skills | Yes | No | No |
| Actual skills to preload | No by default | No | Yes |
| User-owned skills | Yes | Yes, in skill-authoring/sync mode | No until validated/synced |

Therefore:

- The provider can see surfaces 1 and 3.
- The provider can only natively edit surface 3.
- Surface 2 is what makes fallback reliable for API providers.
- Surface 1 is only how CLI providers consume preloaded skills natively.

## Hard-Bar Product Behavior

- Providers author scripts and user-owned skills natively, using their normal
  file-writing behavior.
- User-owned `.codex/skills` and `.claude/skills` are native
  authoring/import surfaces, not FirmCLI's store of record.
- FirmCLI watches and imports valid user-owned skills into a client-owned
  registry after deterministic validation.
- API providers use the same validated registry through fallback `load_skills`
  or the registry-backed equivalent.
- Hardware-touching scripts still execute only through governed
  `run_script(name, inputs)`.
- `skill_ok` means "ready for brain validation", not "provider-certified valid".
- Projected preloaded skills are read/use surfaces and should not be imported as
  provider-authored edits.

## Scope

In scope:

- user-owned `.codex/skills` and `.claude/skills` monitoring;
- syncing valid user-owned Codex/Claude skills into a FirmCLI client-owned
  registry;
- skill creator mode for provider repair/creation loops;
- provider-visible `sync_skills` and `skill_ok` decisions;
- deterministic brain validation of skill format, paths, manifests, projection
  provenance, and safety boundaries;
- validation/repair loops for invalid user-owned skill changes;
- session-scoped model-authored client-action scripts written natively,
  registered by name/hash, and run through governed `run_script`;
- artifacts recording user-owned native-folder changes, validation errors,
  accepted hashes, registry records, projection records, and fallback
  availability;
- narrowing workspace-diff filtering so it ignores marker-proven projected
  preloads while preserving user-owned skill edits.

Non-scope:

- global `~/.codex`, `~/.claude`, or other user-global skill folders by default;
- embedding script or skill bodies in `TurnDecision`;
- trusting provider self-report as validation proof;
- letting skills or client-action scripts call board/probe APIs directly;
- making `.codex` or `.claude` the product store of record;
- treating projected preloaded skills as provider-authored user-owned skills.

## Reconciliation Summary

### Build plan and things-to-change

The build plan and `things-to-change.md` require model-authored scripts and
skill/context loading without reintroducing governed host file/edit actions.
Item 14's skill-index/on-demand-skill-body direction now resolves into two
different flows:

1. preload existing FirmCLI skills for provider use; and
2. let providers natively author user-owned skills, then sync them into a
   client-owned actual-skill registry.

Those flows share validation and fallback semantics, but not ownership.

### R12 provider-native skill bridge

`r12-provider-native-skill-bridge_spec.md` implements projected preloaded skills:
FirmCLI-owned packages are copied into run-local provider-native folders for
CLI providers. That implementation is not the same as user-owned skill creation.

### R12 context scaffold hardening

`r12-context-scaffold-hardening_spec.md` requires actual skills to preload to
come from product/client-owned roots, not from `.codex/skills` as the installed
source root. This spec preserves that: user-owned `.codex` / `.claude` folders
can be import surfaces only after validation, never the sole authority.

### Current code

Current implementation supports:

- CLI pre-registration with `--client-action NAME=PATH`;
- `InMemoryClientActionStore.put_action(...)`;
- prompt rendering of registered client actions;
- `run_script(name, inputs)` as the only client-action decision;
- gated `server.call_tool(...)` injection only during `run_script`;
- run metadata for registered/executed client actions;
- provider-native projection from FirmCLI-owned packages into run-local
  `.codex/skills` / `.claude/skills`;
- API fallback through deterministic `load_skills`.

Current implementation does not support:

- provider-authored skill creation/update/import from user-owned `.codex` or
  `.claude`;
- a canonical client-owned registry populated from user-owned native folders;
- automatic per-turn skill-folder diffing;
- provider-triggered `sync_skills`;
- skill creator mode;
- provider-triggered `skill_ok`;
- deterministic validation/repair loops for provider-created skills;
- sync from user-owned native skill folders into API-provider fallback state;
- provider-authored client-action script registration during a run;
- artifact trails for native skill/client-action create/update/sync events;
- marker/provenance-based narrowing of the current broad workspace diff filter.

## Product Design

### Sync behavior

On startup and after every provider turn in skill-sync mode, the brain must scan
user-owned native skill roots for new, changed, or deleted skill files:

```text
<target-workspace>/.codex/skills
<target-workspace>/.claude/skills
```

The provider may also explicitly request:

```json
{"kind": "sync_skills"}
```

`sync_skills` means "scan user-owned native skill surfaces now and enter or
continue the skill validation workflow if needed." It does not mean "trust all
changes."

Every detected changed skill enters an import/validation queue. The queue
records:

- provider surface: `codex`, `claude`, or both;
- path;
- content hashes;
- previous accepted hash, if any;
- owning session/run, if known;
- whether the change was brain-detected or provider-requested;
- whether the path was user-owned or a marker-proven projection;
- validation state.

All valid user-owned skills should sync into the client-owned actual-skill
registry. Invalid skills remain unsynced/quarantined with user-visible
validation errors.

### Skill creator mode

When sync detects invalid or incomplete user-owned skill changes, or when the
user asks the provider to create/update a skill, the brain may enter skill
creator mode.

Skill creator mode is a bounded provider sub-loop:

- provider may create/edit the relevant user-owned `.codex/skills` and/or
  `.claude/skills` files using native file tools;
- provider may request another `sync_skills`;
- provider may return:

```json
{"kind": "skill_ok", "skill_ids": ["..."]}
```

`skill_ok` is only valid in skill creator mode. It means "I believe these skills
are ready; run deterministic validation now." It is not proof that the skill is
valid.

If `skill_ok` appears outside skill creator mode, the brain must refuse it and
explain that it is only available during skill validation/repair.

### Deterministic validation

After `skill_ok`, or after an auto-sync reaches a candidate-ready state, the
brain validates deterministically before importing the skill.

Validation must check at least:

- supported provider skill layout;
- required files for Codex and/or Claude;
- valid frontmatter/manifest fields;
- stable skill id and title;
- context file references stay within the skill root;
- dependencies are present and acyclic;
- no path escape through symlinks, `..`, absolute paths, or provider-specific
  config tricks;
- init scripts, if allowed, pass the existing raw probe/serial/board command
  preflight;
- skill text does not instruct bypassing FirmCLI `TurnDecision`, governed server
  tools, loaded-detail flags, or `run_script` gates;
- skill text does not claim direct hardware access;
- no hidden binaries or generated caches unless explicitly allowed;
- API fallback renderability through FirmCLI `load_skills`;
- projected-preload provenance is not being imported as user-authored source.

If validation fails, the brain returns structured validation errors to the
provider and allows another skill creator mode repair turn until validation
passes or the repair turn budget is exhausted.

### Import and registry behavior

On validation pass, the brain imports the skill into the FirmCLI registry and
records:

- skill id;
- provider-specific user-owned source path(s);
- canonical registry path;
- source hashes;
- accepted hash;
- provider/session/run provenance;
- validation result;
- validation timestamp/turn index;
- API fallback availability;
- native projection availability.

The provider then receives a concise status update such as:

```text
Skill synced: firmcli-my-skill, sha256=<hash>, available to codex-cli,
claude-cli, and API fallback load_skills.
```

Successful sync must update the skill index used by `load_skills` or the new
registry-backed equivalent. Without that, API fallback is not successful.

### Client-action scripts

Client-action scripts follow the same native-authoring principle:

- provider writes or updates a normal script file in a FirmCLI/user-visible
  authoring area;
- provider does not embed the script body in `TurnDecision`;
- brain syncs/registers the script by name/path/hash;
- `run_script(name, inputs)` is the only governed execution decision;
- brain snapshots and hashes the exact script content that runs;
- hardware/server access is available only through the gated `server` object
  injected during `run_script`;
- imports remain disallowed unless the implementation explicitly designs a
  bounded import policy.

Provider-visible mutation vocabulary:

- `sync_skills` for user-owned native skill folder sync;
- `skill_ok` for validation trigger inside skill creator mode;
- `sync_client_actions` or `sync_client_assets` for native script registration,
  if separate from `sync_skills`;
- existing `run_script(name, inputs)` for governed execution.

Do not add `create_script(content)` or `update_script(content)` unless a later
decision explicitly reverses the native-authoring requirement.

## Workspace Diff And Artifacts

The current workspace diff exclusion for `.codex`, `.claude`, and `.agents`
must be narrowed.

Correct behavior:

- Ignore marker-proven projected preloaded skill subtrees.
- Do not hide user-owned native skill edits merely because they live under
  `.codex`, `.claude`, or `.agents`.
- Record projection artifacts separately from user-authored skill changes.
- If provenance is ambiguous, show the path in artifacts rather than hiding it.

Run artifacts must include:

- user-owned native skill folder diff records;
- projected-preload provenance/hash records;
- skill validation attempts and errors;
- accepted skill hashes;
- registry records;
- client-action create/update/sync events;
- exact script hash used for every `run_script`;
- provider-facing status returned after sync.

## UX Expectations

Users should see concise sync status, not raw JSON. For example:

- "Detected new Codex skill `firmcli-uart-check`."
- "Validating skill..."
- "Validation failed: missing SKILL.md frontmatter title."
- "Provider repairing skill, attempt 2/4."
- "Skill synced and available to Codex, Claude, and API fallback."

Users should be able to inspect user-owned native skills in workspace `.codex`
and `.claude` folders. Projected preloaded FirmCLI skills are generated runtime
views and do not need to be preserved after the run.

## Documentation Plan

If implemented, update:

- `markdowns/things-to-change.md` entry 14 and the current-status paragraph;
- `markdowns/firmware_agent_build_plan_concrete (10).md` R12 scaffold/provider
  native skill amendments;
- `markdowns/R12_P_SPLIT.md` Branch B module 5 and Wave 1 substrate addendum;
- `markdowns/ROADMAP.md` R12 current proof boundary and Branch B split;
- `markdowns/current-progress.md` with actual implementation and validation
  status;
- `repo_file_index.md` for registry/watcher/validator files;
- `skills/README.md` and `markdowns/curr/r12-skill-surface-ownership_spec.md`.

## Verification Plan

Non-hardware validation:

- unit tests for user-owned native skill root scanning and diffing;
- unit tests for deterministic skill validation failures and passes;
- unit tests proving `skill_ok` is refused outside skill creator mode;
- unit tests for validation repair loop budget exhaustion;
- tests for importing user-owned `.codex/skills` and `.claude/skills` into the
  FirmCLI registry;
- tests proving API fallback can render/use a synced skill without native
  provider folders;
- tests proving projected preloaded skill folders are ignored only when
  marker/provenance proves they are generated;
- tests proving user-owned native skill changes are not hidden by workspace diff;
- tests for client-action script native authoring/import without script bodies in
  `TurnDecision`;
- tests for `run_script` using the latest accepted hash;
- pyright, pytest, and the suite ladder through the relevant software surface.

Live provider validation, when credentials/local CLIs are available:

- Codex CLI creates or repairs a user-owned `.codex` skill, returns `skill_ok`,
  and FirmCLI imports it;
- Claude CLI creates or repairs a user-owned `.claude` skill, returns
  `skill_ok`, and FirmCLI imports it;
- a later API-provider turn can use the imported skill through fallback context.

Hardware validation is not required for the skill-sync feature itself. Hardware
proof is only required for any client-action script that calls server-native
board tools through `run_script`.

## Acceptance Criteria

This gap is closed when:

1. The provider can create/update a user-owned Codex skill natively.
2. The provider can create/update a user-owned Claude skill natively.
3. The brain detects those changes automatically after a provider turn.
4. The provider can explicitly request `sync_skills`.
5. The brain can enter skill creator mode and allow `skill_ok`.
6. `skill_ok` triggers deterministic validation and is not trusted as proof.
7. Invalid skills produce structured errors and a bounded provider repair loop.
8. Valid skills sync into the client-owned registry with hashes/provenance.
9. Synced skills are available to Codex/Claude native paths when supported.
10. Synced skills are available to API providers through FirmCLI fallback
    context.
11. Provider-authored client-action scripts are written natively and registered
    by sync/name/hash, not embedded in `TurnDecision`.
12. `run_script(name, inputs)` runs only validated/synced scripts and snapshots
    the exact content hash.
13. Scripts that touch server tools still route through the gated brain/MCP path.
14. Workspace diff/audit captures real user-owned skill/client-action file
    changes under `.codex`, `.claude`, and `.agents` instead of hiding them
    wholesale.
15. Run artifacts record every sync, validation, import, update, and run hash.
16. Tests cover Codex-native, Claude-native, API-fallback, invalid repair,
    budget exhaustion, and client-action execution paths.

## Verified

- Current code inspection shows only CLI pre-registration plus governed
  `run_script` is implemented for client actions.
- Current code inspection shows provider-native skill projection exists for
  FirmCLI-owned actual skill packages into run-local `.codex/skills` and
  `.claude/skills`.
- Current code inspection shows no `sync_skills`, `skill_ok`, skill creator
  mode, native folder import watcher, or registry-backed API fallback for
  provider-created skills.

## Pending Verification

- This spec has not been implemented.
- No tests have been added for user-owned `.codex` / `.claude` skill creation,
  validation, repair, import, or API fallback.
- No live provider run has proven this proposed skill-sync loop.
