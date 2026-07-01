# Wave 1.6-B Client Actions And Native Skill Sync Spec Gap

> Status: PROPOSAL - not authority until accepted and reconciled into the build
> plan / roadmap. This replaces the older provider-visible
> `create_script(name, content)` / `update_script(name, content)` gap framing.

## Goal

Close the Wave 1.6-B / Branch B gap for model-authored client actions and model-created skills
without forcing script or skill bodies through `TurnDecision` JSON.

The hard-bar product behavior is:

- providers author scripts and skills natively, using their normal file-writing
  behavior;
- repo-local `.codex/skills` and `.claude/skills` are first-class native
  authoring/import surfaces;
- the FirmCLI brain watches and imports those native folders into a
  client-owned canonical registry after deterministic validation;
- API providers use the same canonical registry through fallback
  `load_skills`, so native CLI skill behavior is not required for correctness;
- hardware-touching scripts still execute only through governed
  `run_script(name, inputs)`;
- `skill_ok` means "ready for brain validation", not "provider-certified valid".

Roadmap anchor: R12 Stage 5 Wave 1, Branch B module 5 / action boundary,
batches, client actions, and provider-native skill substrate.

## Scope

In scope:

- repo-local `.codex/skills` and `.claude/skills` monitoring;
- syncing all valid repo-local Codex/Claude skills into a FirmCLI client-owned
  registry;
- skill creator mode for provider repair/creation loops;
- provider-visible `sync_skills` and `skill_ok` decisions;
- deterministic brain validation of skill format, paths, manifests, and safety
  boundaries;
- validation/repair loops for invalid skill changes;
- session-scoped model-authored client-action scripts that are written
  natively, registered by name/hash, and run through governed `run_script`;
- artifacts recording native-folder changes, validation errors, accepted hashes,
  registry records, and projection/fallback availability.

Non-scope:

- global `~/.codex`, `~/.claude`, or other user-global skill folders by
  default. Global import/export requires explicit opt-in and a separate safety
  policy.
- embedding script or skill bodies in `TurnDecision`.
- trusting provider self-report as validation proof.
- letting skills or client-action scripts call board/probe APIs directly.
- making `.codex` or `.claude` the product store of record. They are native
  provider-facing surfaces and user-visible mirrors/import sources; the
  validated FirmCLI registry is the canonical product state.

## Reconciliation Summary

### Build plan

The build plan requires model-authored scripts to be saved in a
session-scoped client-action store and run by name with inputs. Host-only
scripts are model-native/free; scripts that call server-native tools are gated
client actions.

### R12 split

Branch B module 5 requires a client session-scoped script/tool store, a native
script authoring target, governed `run_script(name, inputs)`, and snapshots /
hashes of the script version that actually runs. It explicitly says script
bodies are not embedded in `TurnDecision`.

The split and later scaffold-hardening text also require product/client-owned
skill roots and must not reintroduce `.codex` / `.claude` as installed product
skill roots. That does not forbid repo-local native views. It means `.codex` /
`.claude` cannot be the only authority.

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

- provider-authored skill creation/update/import from repo-local `.codex` or
  `.claude`;
- a canonical client-owned registry populated from native provider folders;
- automatic per-turn skill-folder diffing;
- provider-triggered `sync_skills`;
- skill creator mode;
- provider-triggered `skill_ok`;
- deterministic validation/repair loops for provider-created skills;
- sync from native Codex/Claude skill views into API-provider fallback state;
- provider-authored client-action script registration during a run;
- artifact trails for native skill/client-action create/update/sync events;
- detecting or reviewing provider changes under `.codex`, `.claude`, or
  `.agents`, because workspace diff currently ignores those runtime context
  directories.

### Conflict resolved

The older proposed fix, `create_script(name, content)` and
`update_script(name, content)`, is rejected for this feature. It closes part of
the implementation gap but violates the native-authoring requirement by putting
large script bodies into structured decisions.

Correct direction: let the provider write files natively, then have the brain
sync, validate, snapshot, register, and expose the resulting assets.

## Product Design

### Three surfaces

FirmCLI must distinguish three surfaces:

1. Native provider surfaces:
   - repo-local `.codex/skills`;
   - repo-local `.claude/skills`.
2. Provider-authored client-action surface:
   - a session/project client-action authoring directory chosen by FirmCLI;
   - scripts are normal files, not JSON strings.
3. Canonical FirmCLI registry:
   - validated skill records;
   - validated client-action records;
   - content hashes, source paths, provider, session/run provenance, and
     validation status;
   - the source for API fallback context and future projection.

The native folders and registry should be semantically synced, not necessarily
byte-identical. Codex and Claude skill formats may diverge. The registry should
store canonical metadata and per-provider source/projection records.

### Sync behavior

On startup and after every provider turn, the brain must scan repo-local
`.codex/skills` and `.claude/skills` for new, changed, or deleted skill files.

The provider may also explicitly request:

```json
{"kind": "sync_skills"}
```

`sync_skills` means "scan native skill surfaces now and enter/continue the
skill validation workflow if needed." It does not mean "trust all changes."

Every detected changed skill enters an import/validation queue. The queue
records:

- provider surface: `codex`, `claude`, or both;
- path;
- content hashes;
- previous accepted hash, if any;
- owning session/run, if known;
- whether the change was brain-detected or provider-requested;
- validation state.

All valid repo-local skills should be synced into the client-owned registry.
Invalid skills remain unsynced/quarantined with user-visible validation errors.

### Skill creator mode

When a sync detects invalid or incomplete skill changes, or when the user asks
the provider to create/update a skill, the brain may enter skill creator mode.

Skill creator mode is a bounded provider sub-loop with a narrower purpose:

- provider may create/edit the relevant repo-local `.codex/skills` and/or
  `.claude/skills` files using native file tools;
- provider may request another `sync_skills`;
- provider may return:

```json
{"kind": "skill_ok", "skill_ids": ["..."]}
```

`skill_ok` is only valid in skill creator mode. It means "I believe these
skills are ready; run deterministic validation now." It is not proof that the
skill is valid.

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
- skill text does not instruct bypassing FirmCLI `TurnDecision`, governed
  server tools, loaded-detail flags, or `run_script` gates;
- skill text does not claim direct hardware access;
- no hidden binaries or generated caches unless explicitly allowed;
- API fallback renderability through FirmCLI `load_skills`.

If validation fails, the brain returns structured validation errors to the
provider and allows another skill creator mode repair turn until either:

- validation passes; or
- the skill repair turn budget is exhausted.

On budget exhaustion, the brain reports the failed skill(s), errors, and paths
to the user. The invalid skill is not imported into the canonical registry.

### Import and registry behavior

On validation pass, the brain imports the skill into the FirmCLI registry and
records:

- skill id;
- provider-specific native source path(s);
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

The provider can then either continue normal actions or finalize/return.

### Client-action scripts

Client-action scripts follow the same native-authoring principle:

- the provider writes or updates a normal script file in the FirmCLI
  client-action authoring area;
- the provider does not embed the script body in `TurnDecision`;
- the brain syncs/registers the script by name/path/hash;
- `run_script(name, inputs)` is the only governed execution decision;
- on execution, the brain snapshots and hashes the exact script content that
  runs;
- hardware/server access is available only through the gated `server` object
  injected during `run_script`;
- imports remain disallowed unless the implementation explicitly designs a
  bounded import policy.

The provider-visible mutation vocabulary should therefore be:

- `sync_skills` for native skill folder sync;
- `skill_ok` for validation trigger inside skill creator mode;
- `sync_client_actions` or a broader `sync_client_assets` for native script
  registration, if separate from `sync_skills`;
- existing `run_script(name, inputs)` for governed execution.

Do not add `create_script(content)` or `update_script(content)` unless a later
decision explicitly reverses the native-authoring requirement.

## Implementation Requirements

### 1. Native skill watcher

Add a deterministic scanner for repo-local native skill roots:

- `.codex/skills`;
- `.claude/skills`.

The scanner must run:

- at run/session start;
- after every provider turn;
- after any provider-visible `sync_skills`;
- before any governed action that depends on newly edited skills.

The scanner should produce a diff record rather than directly mutating the
registry.

### 2. Skill validation and repair loop

Add skill creator mode state to the brain. It must track:

- active skill ids;
- changed paths;
- validation attempts;
- remaining repair turns;
- last validation errors;
- whether `skill_ok` is currently allowed.

Add strict action models for:

- `sync_skills`;
- `skill_ok`.

Both must appear in the output schema and action policy only with the correct
mode/guardrails.

### 3. Canonical registry

Add a client-owned registry for validated model-created/imported skills. The
registry can start session-local, but the data model must support later project
persistence.

The registry must not treat `.codex` or `.claude` as the store of record. It
imports validated content and tracks provider-native source/projection paths.

### 4. API fallback integration

After import, API providers must be able to use the same skill through
FirmCLI-managed context expansion, not provider-native folder discovery.

This means successful sync must update the skill index used by `load_skills` or
the new registry-backed equivalent.

### 5. Client-action script sync

Extend the current `ClientActionStore` flow so provider-authored scripts can be
registered from native file writes.

Requirements:

- name validation uses the existing client-action name policy;
- script content parses as Python;
- script defines `run(inputs, server)`;
- script body never appears inside `TurnDecision`;
- create/update/import events are recorded;
- loaded client-action details are refreshed or invalidated when the script hash
  changes;
- `run_script` refuses unsynced/invalid scripts.

### 6. Workspace diff and artifact changes

The current workspace diff exclusion for `.codex`, `.claude`, and `.agents`
must be narrowed. The product should ignore generated runtime projection files
only when they are known FirmCLI-generated artifacts, not all native skill
changes.

Run artifacts must include:

- native skill folder diff records;
- skill validation attempts and errors;
- accepted skill hashes;
- registry records;
- client-action create/update/sync events;
- exact script hash used for every `run_script`;
- provider-facing status returned after sync.

### 7. UX expectations

Users should see concise skill-sync status, not raw JSON. For example:

- "Detected new Codex skill `firmcli-uart-check`."
- "Validating skill..."
- "Validation failed: missing SKILL.md frontmatter title."
- "Provider repairing skill, attempt 2/4."
- "Skill synced and available to Codex, Claude, and API fallback."

The user should be able to inspect generated skills in repo-local `.codex` and
`.claude` folders. Preloaded/bundled FirmCLI skills do not need to be copied
into those folders unless native projection for the current run requires it.

## Portability And Origin Tags

All paths are `PROJECT-DEFINED` product policy and must use `pathlib`.

Repo-local `.codex/skills` and `.claude/skills` layouts are
`VENDOR-FIXED, UNVERIFIED ACROSS VERSIONS` except where current live provider
proof exists. The implementation must keep capability flags/probes so future
provider layout changes can fall back to FirmCLI `load_skills`.

No board facts are introduced by this spec. Any board/probe access remains
behind existing governed server tools.

## Documentation Plan

If implemented, update:

- `markdowns/firmware_agent_build_plan_concrete (10).md` R12 Wave 1 / Branch B
  client-action text;
- `markdowns/R12_P_SPLIT.md` Branch B module 5 and Wave 1 substrate addendum;
- `markdowns/ROADMAP.md` R12 current proof boundary and Branch B split;
- `markdowns/current-progress.md` with actual implementation and validation
  status;
- `markdowns/things-to-change.md` entries for model-authored scripts, project
  skills/tools, provider-native skills, and API fallback;
- `repo_file_index.md` for new registry/watcher/validator files;
- CLI/operator docs if new flags or visible commands are added.

## Verification Plan

Non-hardware validation:

- unit tests for native skill root scanning and diffing;
- unit tests for deterministic skill validation failures and passes;
- unit tests proving `skill_ok` is refused outside skill creator mode;
- unit tests for validation repair loop budget exhaustion;
- tests for importing repo-local `.codex/skills` and `.claude/skills` into the
  FirmCLI registry;
- tests proving API fallback can render/use a synced skill without native
  provider folders;
- tests for client-action script native authoring/import without script bodies
  in `TurnDecision`;
- tests for `run_script` using the latest accepted hash;
- tests proving invalid/unsynced scripts are refused;
- tests ensuring workspace diff no longer hides real provider-created skills;
- pyright, pytest, and the suite ladder through the relevant software surface;
- provider simulation for Codex CLI, Claude CLI, OpenAI API, and Anthropic API
  behavior without live credentials where needed.

Live provider validation, when credentials/local CLIs are available:

- Codex CLI creates or repairs a repo-local `.codex` skill, returns `skill_ok`,
  and FirmCLI imports it;
- Claude CLI creates or repairs a repo-local `.claude` skill, returns
  `skill_ok`, and FirmCLI imports it;
- a later API-provider turn can use the imported skill through fallback context.

Hardware validation is not required for the skill-sync feature itself. Hardware
proof is only required for any client-action script that actually calls
server-native board tools through `run_script`.

## Acceptance Criteria

This gap is closed when:

1. The provider can create/update a repo-local Codex skill natively.
2. The provider can create/update a repo-local Claude skill natively.
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
13. Scripts that touch server tools still route through the gated brain/MCP
    path.
14. Workspace diff/audit captures real skill/client-action file changes under
    `.codex`, `.claude`, and `.agents` instead of hiding them wholesale.
15. Run artifacts record every sync, validation, import, update, and run hash.
16. Tests cover Codex-native, Claude-native, API-fallback, invalid repair,
    budget exhaustion, and client-action execution paths.

## Verified

- Current code inspection shows only CLI pre-registration plus governed
  `run_script` is implemented for client actions.
- Current code inspection shows provider-native skill projection exists for
  FirmCLI-owned packages into run-local `.codex/skills` and `.claude/skills`.
- Current code inspection shows no `sync_skills`, `skill_ok`, skill creator
  mode, native folder import watcher, or registry-backed API fallback for
  provider-created skills.

## Pending Verification

- This spec has not been implemented.
- No tests have been added for native `.codex` / `.claude` skill creation,
  validation, repair, import, or API fallback.
- No live provider run has proven this proposed skill-sync loop.
