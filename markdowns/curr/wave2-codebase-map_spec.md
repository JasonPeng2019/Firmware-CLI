> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Wave 2 Codebase Map And Skill Prompt Scaffolding

## Goal in plain English

Add a client-side codebase map for the turnkey brain's provider session. On
first boot for a workspace, the model creates a `codebase_map.md` that describes
each relevant file, its functions/classes, code dependencies, and logical
process dependencies. Wave 2 Module G then uses that map as part of static
context and model-native skill scaffolding: workflow skill turns receive the
full map once per provider turn, normal turns receive a clear rule and map
provenance, and any provider-native file changes trigger a bounded map
maintenance turn before the next governed action is trusted.

Task: Wave 2 client codebase map and skill prompt scaffolding.
Roadmap anchor: R12 Wave 2 Module G static context efficiency and
cache-assisted reuse.

## Scope and non-scope

In scope:

- A workspace-local `codebase_map.md` artifact generated on first boot/run for
  the selected workspace.
- A deterministic file inventory/skeleton to help the model author the first map
  and to make map completeness testable.
- Per-file map entries with repo-relative path, short description, functions,
  classes, public symbols, commands, or data shapes defined there.
- Per-file code dependencies such as imports, local module references, config
  includes, scripts, generated artifacts, or tests.
- Per-file logical/process dependencies such as docs, build plans, specs,
  workflow skills, runbooks, harnesses, tests, board configs, or review files
  that affect how the file should be changed even when they are not code
  imports.
- Ownership/layer tags, content hash/provenance, and last update metadata.
- Prompt injection of these per-provider-turn items: skill index, available
  governed-tool index, compact memory every 10 provider turns by default through
  the existing `native_sync_every` policy, codebase-map guidance every turn, and
  the full `codebase_map.md` once per provider turn when model-native workflow
  skill context is loaded or injected.
- The hard prompt rule that the model must consult the map before creating new
  code files or making significant code changes greater than about 100 lines.
- De-duping map injection when multiple workflow skills are loaded in one
  provider turn.
- A bounded codebase-map maintenance phase after provider-native file changes:
  the model updates `codebase_map.md` or explicitly skips because no file change
  occurred, then re-emits the prior `TurnDecision` or a better decision if the
  newly updated map changes the correct next step.
- Events/artifacts for map creation, map injection, skipped updates, applied
  updates, map hashes, changed files, and replayed/changed decisions.
- Tests that this scaffolding works even before project-level user skills exist.
  Branch B already added `load_skills`; Wave 2 uses the hardened scaffold from
  `r12-context-scaffold-hardening_spec.md` without requiring shipped custom
  workflow skills.

Out of scope:

- Implementing a broad project-level custom skills UI or marketplace.
- Reintroducing governed host actions for reading files, writing files, or
  running builds. Map creation and map maintenance are provider-native host
  work; the brain only orchestrates context and decision boundaries.
- Letting map maintenance execute board/server actions or bypass the governed
  server API.
- Replacing provider memory with the map. The map is a code/workspace artifact;
  compact provider memory remains the durable turn-history summary.
- Replacing final live hardware proof with cached map/cache artifacts.

## Reconciliation summary

- Build plan: Stage 5 already requires cheap static context, a compact governed
  tool index, selected-skill index, provider-native host work, governed board
  decisions, and compact memory sync every 10 provider turns. This spec extends
  that Module G static-context work with a codebase map and map-maintenance
  turn.
- Current code: Branch B already removed governed host file/build actions and
  added model-native `load_skills(skill_ids=[...])`, per-skill runtime folders,
  compact governed-tool index rendering, and provider memory sync plumbing.
  The follow-up scaffold-hardening spec now requires product/client-owned skill
  roots, runtime-copy-only recovery, structured skill failures, tool-detail
  loading, loaded-detail guardrails before governed execution, invalid-call
  auto-details, and prompt ordering/dedupe before Wave 2 codebase-map work
  depends on that substrate.
  `ProviderPromptBundle` already separates tool schema text, provider memory,
  turn context, and the decision schema. `ProviderMemoryEntry` already has
  `changed_files` and `codebase_summary` fields that can be used by the new map
  maintenance artifacts.
- Other docs or notes: `things-to-change.md` entry #3 covers skill index and
  on-demand bodies, entry #23 covers cache-assisted static prompt reuse, and
  `R12_P_SPLIT.md` Module G owns static-context efficiency plus skill loading.
- Disagreements resolved here: the user requested full map injection whenever a
  skill is called. That is a hard prototype requirement for workflow skill
  turns. To preserve cache efficiency on non-skill turns, ordinary turns inject
  the map rule, path, hash, and compact summary rather than reprinting the full
  map unless the provider enters a workflow skill turn.

## Design

### Artifact shape

`codebase_map.md` is a workspace-local markdown artifact. The implementation may
choose the final path, but the first Wave 2 prototype should prefer a stable
repo-relative path under client/runtime metadata, for example:

```text
<workspace>/.firmcli/codebase_map.md
```

The provider prompt must expose the exact path and current SHA-256 hash. The map
must be portable across workspaces: paths inside the map are repo-relative where
possible, and absolute paths are provenance-only.

The first map must be model-authored because the product goal is to give the
provider a reasoning map, not just an import graph. A deterministic scanner may
prepare an inventory skeleton with paths, file hashes, function/class names, and
obvious import dependencies so the model has ground truth to build from and the
brain can test for omissions.

Each file entry should use a stable shape:

```text
## path/to/file.py

- purpose: ...
- defines: ClassName, function_name, CLI command, data schema, ...
- code dependencies: path/to/other.py, pyproject.toml, tests/test_x.py, ...
- logical/process dependencies: markdowns/R12_P_SPLIT.md, skills/model_native/..., ...
- layer/tags: brain-loop, provider-adapter, board-gate, docs, tests, ...
- provenance: sha256=..., last_map_update_turn=..., source=model|scanner
```

Logical/process dependencies are first-class. They include build plans,
roadmaps, tests, runbooks, workflow skills, generated artifacts, board config
files, prompt specs, and review docs that should influence edits even when no
language-level import exists.

### First boot

When a workspace is first used by the turnkey client:

1. If no `codebase_map.md` exists, create a deterministic inventory skeleton.
2. Prompt the provider to author the initial codebase map from that inventory
   using provider-native host reads as needed.
3. Record a `codebase_map_created` event with path, hash, covered file count,
   skipped file count, provider turn id, and any omissions.
4. Continue into the normal governed loop only after the map exists or the run
   fails clearly with an initialization error.

Generated/build/vendor folders should be excluded by policy unless they are
part of the source of truth for the requested workspace.

### Prompt injection rules

Every provider turn must include:

- the skill index;
- the compact available governed-tool index;
- the standing codebase-map rule:
  "Before creating new code files or making significant code changes greater
  than about 100 lines, read the current `codebase_map.md` and follow the listed
  code and logical/process dependencies.";
- map path, current map hash, freshness status, and a compact map summary;
- provider memory according to the existing cadence, defaulting to every 10
  provider turns for remote-primary providers through `native_sync_every`.

When any model-native workflow skill context is loaded or injected in a provider
turn, the prompt must also include the full current `codebase_map.md` exactly
once for that provider turn. Multiple skill loads or multiple skill bodies in
one turn do not multiply the map body.

The map body is static context for the provider, not a governed action result.
It must not make `read_file`, `replace_file`, or `run_build` valid
`TurnDecision` actions again.

### Map maintenance turn

After a provider turn performs provider-native host edits, the brain must make
the codebase map current before dispatching or trusting the next governed
board/client action.

The first Wave 2 design is a bounded maintenance subturn:

1. The brain detects changed workspace files from provider/runtime artifacts,
   git status, file hashes, or an explicit provider change report.
2. If no source/doc/test/config file changed, record `codebase_map_update_skipped`
   and continue.
3. If files changed, the next provider interaction is a codebase-map maintenance
   prompt. It asks the model to update `codebase_map.md` for those changes or
   explicitly skip with a reason if the map is still correct.
4. The maintenance prompt includes the previous pending `TurnDecision` and asks
   the model to re-emit that same decision unless the map update or new
   information makes a better decision available.
5. The provider response closes with either the replayed decision or an updated
   valid `TurnDecision`.
6. The brain records changed files, map hash before/after, whether the decision
   was replayed or changed, and the reason.

The maintenance phase is capped at one subturn per provider turn to prevent
infinite loops. It may perform provider-native host reads/edits of
`codebase_map.md`; it may not call board tools, server tools, or generic host
execution through the brain.

### Skill integration

Until workflow skill manifests grow finer tags, every model-native workflow skill
is treated as a read/write-significant skill for map purposes. That means:

- `load_skills(skill_ids=[...])` still only loads model-native workflow context;
- on the next provider turn, loaded skill markdown plus the full map are injected
  once;
- the skill index remains always available as cheap context;
- future manifests may add `requires_codebase_map: true|false`, but the prototype
  default is `true` for workflow skills.

### Cache and token policy

The hard prototype behavior is full map injection once per workflow-skill turn.
Cache-assisted reuse may avoid re-rendering unchanged map text internally, but it
must not omit the full map body from a skill turn unless a later accepted spec
changes this requirement.

For ordinary non-skill turns, the prompt should prefer a compact map summary plus
path/hash/freshness to avoid reprinting a large map every iteration.

### Failure behavior

Failures must be clear and artifact-backed:

- missing map on first boot is a setup failure;
- stale map after detected file changes blocks the next governed action until a
  maintenance turn succeeds or fails clearly;
- a malformed maintenance response uses the existing provider retry path;
- repeated maintenance failures become an explicit blocked result, not silent
  continuation with stale context;
- cycle/dependency failures in loaded skills remain skill-load failures, not map
  failures.

## Board-facts-as-data and origin tags

The codebase map is not a board-fact source. Board facts continue to come from
board YAML, MCP/server discovery, and governed hardware observations. If the map
mentions a board, target, probe, or run artifact, it must tag the origin as a
workspace/config/doc reference rather than live board truth.

Map entries and map-update events must include enough provenance to distinguish:

- deterministic scanner inventory;
- provider-authored descriptions;
- docs-derived logical/process dependencies;
- test-derived dependencies;
- run-artifact-derived changed-file observations;
- live board facts imported from governed events.

## Documentation plan

- Add this spec to `markdowns/curr/README.md` as active Wave 2 planning truth.
- Update `markdowns/things-to-change.md` Prototype Priority and entry #3/#23
  language so the codebase map is a hard Module G requirement.
- Update `markdowns/R12_P_SPLIT.md` Module G with codebase-map ownership,
  maintenance-turn sequencing, and shared-file constraints.
- Update `markdowns/ROADMAP.md`, `markdowns/current-progress.md`, and the Stage
  5 build plan with the new Wave 2 requirement.
- Do not archive this spec until the Wave 2 implementation and validation are
  complete.

## Portability

- Paths inside `codebase_map.md` are repo-relative where possible.
- The map location is stable for a workspace but must tolerate workspace
  relocation.
- Hashes are content hashes, not machine-specific mtimes.
- Generated runtime paths under `_provider-runtime/<run_id>/<provider>/...` may
  appear as provenance, but must not be required to resolve the map after a run.
- The map must work for both official target boards and any later board config;
  it may not bake in the currently attached probe pair as product truth.

## Verification plan

- Focused unit tests:
  - first boot creates an inventory skeleton and prompts map creation;
  - map parser/renderer preserves file path, purpose, definitions,
    code dependencies, logical/process dependencies, tags, and provenance;
  - map freshness compares file hashes and detects changed files;
  - full map is injected exactly once when a provider turn includes one or more
    loaded model-native workflow skills;
  - multiple skill loads in one turn de-dupe map injection;
  - ordinary turns include the map rule, path, hash, compact summary, skill
    index, governed-tool index, and memory according to the configured cadence;
  - changed files trigger one maintenance subturn before the next governed
    action is dispatched;
  - no changed files skip map maintenance with an event;
  - maintenance response can replay the prior decision;
  - maintenance response can replace the prior decision when new map information
    justifies it;
  - malformed maintenance response uses the existing retry path;
  - maintenance cannot execute board/server actions or generic host actions
    through the brain.
- Prompt snapshot tests:
  - skill turn prompt contains loaded skill ids, full `codebase_map.md`, skill
    index, available-tool index, and map provenance;
  - non-skill turn prompt contains the codebase-map rule without full map body;
  - provider-memory sync still appears every 10 turns by default for
    remote-primary providers.
- Integration smokes with Codex:
  - no-hardware workspace first-boot run creates or refreshes map;
  - model makes a small host-side edit, updates map, and replays the prior
    terminal/governed decision;
  - model loads a workflow skill and receives the full map once.
- Hardware validation:
  - no new board behavior is required for map mechanics;
  - final Wave 2 suite still proves the governed board boundary on both boards
    because map maintenance must not bypass the brain.

## Acceptance criteria

- `codebase_map.md` is created on first workspace boot before normal governed
  work proceeds.
- Each file entry includes description, defined symbols/functions/classes,
  code dependencies, logical/process dependencies, and provenance.
- The provider prompt includes skill index, available governed-tool index,
  codebase-map rule/path/hash/summary every turn, and compact memory on the
  configured cadence, defaulting to 10 provider turns.
- The codebase map does not satisfy governed execution detail flags. Wave 2 must
  still rely on the hardened scaffold's loaded-detail guardrail before governed
  tools, governed client scripts, or brain-owned compound actions execute.
- The full `codebase_map.md` is injected once, and only once, for each provider
  turn that receives model-native workflow skill context.
- Multiple skill calls/loads in one turn do not duplicate the map body.
- The model is explicitly prompted to consult the map before creating new code
  files or making significant code changes greater than about 100 lines.
- Provider-native file changes trigger a bounded map-maintenance subturn before
  the next governed action is trusted.
- The maintenance subturn updates the map or records a clear skip, then replays
  or validly changes the pending `TurnDecision`.
- Map creation/update events include changed files, map hashes, provenance, and
  decision replay/change status.
- No removed host actions return: `read_file`, `replace_file`, and `run_build`
  remain structurally absent from valid `TurnDecision` actions.
- Board/server actions remain governed by the brain; map logic does not
  introduce generic host execution into the brain or MCP server.

## Verified

- Spec drafted against current Wave 2 Module G ownership and Branch B
  model-native skill scaffolding on 2026-06-30.

## Pending verification

- Implementation has not started.
- No unit, prompt snapshot, Codex smoke, Claude smoke, or hardware validation has
  been run for this Wave 2 feature yet.
