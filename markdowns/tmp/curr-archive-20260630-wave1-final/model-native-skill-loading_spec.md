> STATUS: ACTIVE HARD BAR - user-directed 2026-06-30 implementation spec for the
> current R12 prototype pass. This spec supersedes the earlier compatibility
> stance that merely hid/refused governed host actions.

# Model-Native Skill Loading

## Goal in plain English

Task: Remove brain-governed host actions and add model-native skill loading.
Roadmap anchor: `R12` turnkey brain prototype, Branch B action-boundary
correction plus Module G-style model-native context expansion.

The turnkey brain must stop treating host-local work as governed
`TurnDecision` actions. File reads, file edits, builds, and pure host scripts
are provider-native work done inside the provider turn. The provider returns a
turn-closing decision only for governed board/server actions, governed
client-action execution, brain-local waits, final verification/finalization, or
the new context-expansion decision `load_skills`.

## Scope and non-scope

In scope:

- delete the old governed host action models `read_file`, `replace_file`, and
  `run_build` everywhere they are valid action variants
- remove the old compatibility refusal path for those host actions; they must be
  structurally impossible, not special-cased as known-but-refused actions
- keep host file/edit/build work provider-native in prompt language
- add `load_skills` as a valid turn-closing context-expansion decision that
  accepts one or more `skill_ids`
- resolve model-native skill dependencies recursively with de-duping and clear
  cycle errors
- run skill init scripts dependency-first, post-order, once per provider
  session/run, with deterministic cwd, timeout, stdout/stderr/result capture,
  and failure propagation
- track loaded skill state in the brain/session artifact
- inject loaded skill markdown/context into the next provider turn
- expose usable skill scripts/assets under stable per-skill provider-runtime
  folders
- add focused tests for schema absence, parsing invalidity, batch conversion,
  skill dependency resolution/init order/cycles/repeat loads, prompt injection,
  and runtime exposure

Out of scope:

- adding generic host command/file execution to the brain or MCP server
- migrating the existing board/diagnostic YAML skill selector
- letting init scripts access board hardware or bypass governed server tools
- replacing required live board green checks with cached/context proof
- broad provider-adapter rewrites unrelated to prompt/context injection

## Reconciliation summary

- Build plan: `R12` owns the turnkey brain, skills, CLI, and acceptance
  benchmark. The current prototype amendment already requires free host-side
  model work followed by governed board/client/terminal decisions.
- Current code: Branch B removed the host actions from the rendered schema and
  prompt, but `ReadFileAction`, `ReplaceFileAction`, `RunBuildAction`,
  `MODEL_NATIVE_HOST_ACTION_KINDS`, executor branches, and stale-action refusal
  code still exist.
- Other docs or notes: `things-to-change.md` and `R12_P_SPLIT.md` already point
  at on-demand skill loading/context efficiency, but they still contain stale
  language that treats host actions as valid or refused governed actions.
- Disagreements: the new user instruction resolves the conflict. Governed host
  actions must be removed completely; refusing them is no longer acceptable.

## Design

### Final Action Boundary

- Model-native/free: reading files, editing files, running builds, running pure
  host scripts, and inspecting skill folders through provider-native host tools.
- Context expansion: `load_skills`, handled by the brain between provider turns.
- Brain-local: `wait`.
- Governed client action: `run_script` when it invokes the gated server API.
- Server-native/board: `connect`, `flash_firmware`, `read_memory`,
  `read_serial`, `write_serial`, `unlock_recover`, and the rest of the curated
  server tool surface.
- Verification/final: `run_green_check` and `finalize`.

### Removed Host Actions

The following must not exist as valid output decisions, action models, schema
variants, batch action types, executor branches, policy classes, imports,
prompt-visible decisions, tests expecting refusal, or `__all__` exports:

- `read_file`
- `replace_file`
- `run_build`

`WorkspaceSession.run_build()` may remain as internal support for
`run_green_check` rebuild-before-flash behavior, but it must not be callable as
a governed model decision.

### New `load_skills` Decision

Shape:

```json
{
  "kind": "load_skills",
  "skill_ids": ["firmcli-fix-bug"]
}
```

The action accepts one or more non-empty skill IDs. On receipt, the brain:

1. resolves every requested skill ID;
2. resolves transitive dependencies;
3. detects cycles and reports the full cycle path;
4. computes dependency-first post-order init order;
5. runs each not-yet-initialized skill's init scripts once;
6. exposes usable paths under
   `runs/_provider-runtime/<run_id>/<provider>/skills/<skill_id>/`;
7. records loaded state, init results, runtime paths, context file hashes, and
   failures in session state/events/artifacts;
8. injects loaded markdown/context into the next provider prompt.

Repeated requests for already-loaded skills are no-op for init/exposure and
return a result listing those skills as already loaded. Markdown may appear
again in the next provider prompt because prompt assembly is derived from loaded
session state.

### Skill Format

Model-native skills are folder-based. A skill folder contains a manifest plus
instruction/context files and optional scripts/assets/references. The manifest
minimum fields are:

```yaml
skill_id: firmcli-fix-bug
title: FirmCLI Fix Bug
description: Fix a Firmware-CLI bug end to end.
depends_on:
  - firmcli-workflow-core
init_scripts:
  - scripts/init.py
context_files:
  - SKILL.md
usable_paths:
  - scripts/
  - references/
```

Existing board/diagnostic YAML skills remain a separate system unless they are
deliberately migrated later.

## Board-facts-as-data and origin tags

This feature does not change board-facts-as-data. Skill manifests are workflow
metadata, not board metadata. Board-specific diagnostic YAML skill selection
continues to come from the existing board/case context selector.

## Documentation plan

- Update `things-to-change.md`, `current-progress.md`, `R12_P_SPLIT.md`,
  `ROADMAP.md`, the concrete build plan, and `r12_turnkey_spec.md` before code
  to make this change a current hard requirement.
- Update `next-codex-handoff-20260630.md` after implementation with Codex
  validation and Claude morning handoff commands.
- If a new runtime module is added, update `repo_file_index.md`.

## Portability

Skill paths and runtime exposure must use `pathlib`, repo-relative provenance,
and provider-runtime roots already created for the current run. Init scripts
must run with explicit timeouts and deterministic cwd and must not rely on
Windows-only shell quoting. Runtime folder names are per-skill namespaces, not
global script paths.

## Verification plan

Focused tests:

- rendered action schema excludes `read_file`, `replace_file`, and `run_build`
- `TurnDecision` cannot parse those kinds as `action` variants
- batch conversion no longer special-cases or model-native-refuses those action
  types; they are unsupported batch actions
- `load_skills` accepts one and many skill IDs
- dependencies resolve transitively
- init scripts run dependency-first post-order
- init scripts that directly import known probe/serial stacks or invoke known
  board/probe commands fail before subprocess execution
- manifest `skill_id` must match the requested skill folder
- duplicate dependencies initialize once
- cycles fail clearly with the full cycle path
- loaded skill markdown appears in the next provider prompt
- usable folders are exposed under stable provider-runtime paths
- repeat load is no-op for init/exposure and reports already-loaded skills

Python-change gate after final Python edits:

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py
```

Claude quota is unavailable during this pass, so live Claude proof is a handoff
item. Codex/local smoke should be run as far as practical without widening the
scope into a full hardware suite unless a real bug demands it.

## Acceptance criteria

- governed host actions are deleted, not merely hidden or refused
- provider prompts no longer advertise file/build host actions as decisions
- provider prompts still say host work is provider-native before returning a
  governed or terminal decision
- `load_skills` is a valid turn-closing context-expansion decision
- skill dependency closure is recursive, de-duped, and cycle-safe
- init scripts run dependency-first post-order with timeout/result capture and
  preflight rejection for direct probe/serial bypasses
- skill manifests cannot spoof their requested folder IDs
- loaded skill state is persisted in brain/session state and events/artifacts
- loaded markdown/context is injected into subsequent provider turns
- usable scripts/assets are exposed under per-skill runtime folders
- the board/server boundary remains structurally governed by the brain
- focused tests and the required Python-change gate pass, or any impossible
  live-provider/hardware proof is explicitly handed off

## Verified

- Focused unit/runtime tests prove schema absence, invalid host-action parsing,
  `load_skills` parsing, unsupported stale batch conversion, dependency closure,
  dependency-first init order, duplicate de-dupe, cycle errors, prompt injection,
  per-skill runtime exposure, repeat no-op load, and deleted executor helpers.
- Python-change gate passed after implementation: Ruff, format, full Pyright
  with `0` diagnostics across `107` analyzed files, and full pytest
  `347 passed`.
- Codex CLI no-hardware smoke passed at
  `runs/turnkey-20260630T084055Z-0a0377bc`: first turn loaded
  `firmcli-fix-bug`, dependency closure resolved `firmcli-workflow-core` and
  `python-change`, second turn finalized without board session or MCP tool use.
- Adversarial audit follow-up passed at
  `markdowns/curr/wave1-adversarial-audit-20260630_review.md`: focused tests
  now cover init-script probe/serial bypass rejection and manifest ID/folder ID
  consistency; Python-change gate, suite preset, Codex host-native smoke, Codex
  `load_skills` smoke, and Codex compact tool-index smoke are green.

## Pending verification

- Claude CLI proof pending provider quota reset.
- Optional live hardware reproof for broader Branch B behavior after quota reset
  or if the team wants this schema/context change tied to another board run.
