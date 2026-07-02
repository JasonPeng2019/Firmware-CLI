# R12 Skill Terminology And User-Native Sync Gap

> Status: active gap record / ground truth for current docs cleanup  
> Scope: R12 skill terminology, current preloaded-skill implementation, and future user-owned native skill sync  
> Authority: use this file when reconciling `wave1-6-B-actions-spec.md`, `r12-skill-surface-ownership_spec.md`, and the provider-native bridge docs.

## 1. Correct Vocabulary

Use **native** only for behavior the provider/model can perform through its normal environment without FirmCLI translating it into prompt text or a FirmCLI action.

Correct terms:

- **FirmCLI-owned preloadable skill source**: skill files shipped with or accepted by FirmCLI/client runtime policy.
- **Preloaded mirror / projected preload**: a FirmCLI-generated copy of preloadable skill source placed where a CLI provider can read it, such as `.codex/skills` or `.claude/skills`.
- **Native provider use**: Codex/Claude CLI reading or invoking a skill through its own normal skill behavior.
- **Agent-loaded fallback context**: skill text/context injected by FirmCLI through `load_skills` or an equivalent prompt-context path. This is not native.
- **User-owned native skill**: a skill folder in the target workspace/codebase repo that the user can see and the provider can edit as normal files.
- **Client-owned accepted registry**: hidden/internal FirmCLI state containing validated user-owned skill content/metadata for audit and API fallback.

Avoid these terms unless quoted as legacy code names:

- `model-native` for `load_skills` fallback context. API providers do not have native workspace skill behavior.
- `client-owned .codex` or `client-owned .claude` when those folders live in the target workspace. Workspace folders are user-owned.
- `provider-native skill` without saying whether it means a preloaded mirror or a user-owned native skill.

## 2. Current Implementation, Described Correctly

The current preloaded-skill behavior is desired for packaged FirmCLI skills.

```text
FirmCLI-owned preloadable skill source
        |-- CLI provider path:
        |     FirmCLI creates a preloaded mirror under .codex/skills or .claude/skills.
        |     Codex/Claude CLI can then use that mirror natively.
        |
        `-- API/fallback path:
              FirmCLI injects skill context through load_skills.
              This is agent-loaded fallback context, not native behavior.
```

Current behavior does not ask the provider to edit skills. It prompts CLI providers to use preloaded mirrors and to request `load_skills` fallback if native provider use is unavailable, fails, or is uncertain.

Current behavior does not use user-owned native skills. If a user workspace already contains `.codex/skills` or `.claude/skills`, the provider can edit those files as normal workspace files, but FirmCLI does not yet detect, validate, repair-loop, accept, or expose those edits as synced skills.

## 3. What Is Not A Gap

The current preload/fallback split is not a gap:

- CLI providers should use the mirrored/preloaded copy because that is their natural delivery path.
- API providers should use `load_skills` / agent-loaded fallback context because they have no native workspace skill surface.
- No registry-to-projection flow is required for the normal user-owned-skill case, because accepted user-owned skills already live in the user's codebase repo and remain visible to Codex/Claude CLI there.

## 4. Actual Terminology Gaps

1. Legacy code/docs use `model_native`, `ModelNativeSkillRegistry`, and "model-native skill loading" for what is actually agent-loaded fallback context.
2. Docs overload "provider-native skill" across preloaded mirrors and user-owned native skills.
3. Docs must clearly separate FirmCLI-owned preloadable source, generated mirrors, user-owned native skills, and client-owned accepted registry state.
4. Docs must say the current preloaded-skill implementation is intentionally correct for FirmCLI-owned skills before user-owned sync exists.

## 5. Actual Implementation Gaps

### 5.1 Old #13 / broad diff filtering

The current internal diff/filter path ignores all top-level `.codex`, `.claude`, and `.agents` paths. That is too broad.

Correct behavior:

- hide or ignore only FirmCLI-generated preloaded mirrors, proven by marker/provenance;
- do not hide user-owned native skill edits under `.codex`, `.claude`, or `.agents`;
- classify ambiguous paths conservatively as visible artifact/diff entries rather than hiding them.

### 5.2 User-owned native skill watcher

FirmCLI does not yet scan user-owned native skill folders in the target workspace/codebase repo, such as:

```text
<target-workspace>/.codex/skills/...
<target-workspace>/.claude/skills/...
```

for provider edits after turns or at explicit sync points.

### 5.3 Sync trigger

There is no implemented provider-visible sync trigger, such as `sync_skills`, meaning "scan user-owned native skill folders and try to validate/sync changed skills now."

### 5.4 Ready-for-validation signal

There is no implemented `skill_ok` or equivalent signal meaning "I think this user-owned skill is ready; validate it now."

### 5.5 Deterministic validation

FirmCLI does not yet validate user-owned native skill edits for:

- required files;
- manifest/frontmatter;
- stable skill id/title;
- provider-specific layout;
- safe paths and no path escapes;
- dependency closure;
- no hidden generated junk;
- no direct hardware-bypass instructions;
- API fallback renderability.

### 5.6 Repair loop

The desired future loop is:

```text
provider edits user-owned skill natively
FirmCLI validates it
if invalid, FirmCLI tells provider exactly what failed
provider edits again
repeat until valid or stopped
```

The edit itself is native and unguarded as normal file editing. The gated step is acceptance/sync/use, not editing.

### 5.7 Client-owned accepted registry

FirmCLI needs hidden/internal accepted state for validated user-owned skills. It should record at least:

- skill id;
- user-owned source path;
- accepted content hash;
- provider format/source;
- validation result;
- accepted timestamp/turn;
- fallback-renderable content or reference.

This does not exist yet.

### 5.8 API fallback for user-created skills

Existing fallback works for packaged FirmCLI skills. It does not work for a new provider-authored user-owned skill, because there is no accepted registry that API fallback can load from.

Required future flow:

```text
user-owned native skill
        -> validated/synced
client-owned accepted registry
        -> agent-loaded fallback context for API providers
```

### 5.9 Mirror/projection change classification

FirmCLI-generated preloaded mirrors and user-owned native skills may both live under `.codex/skills` or `.claude/skills`. FirmCLI must distinguish them by provenance:

```text
has FirmCLI projection marker
    -> generated preloaded mirror
    -> ignore/regenerate/flag if changed

no FirmCLI projection marker and in user repo
    -> user-owned native skill
    -> validate/sync
```

The projection marker exists today, but the watcher/diff/sync layer does not yet use it to classify changes.

### 5.10 Skill lifecycle artifacts

The future implementation should record:

- detected user-owned skill changes;
- validation attempts;
- validation failures;
- provider repair prompts/status;
- accepted hashes;
- accepted registry records;
- fallback availability;
- mirror/projection hashes;
- mirror tampering/regeneration events.

### 5.11 Provider-authored client-action scripts

Provider-authored client-action scripts are a parallel Wave 1.6-B gap. Current behavior supports pre-registered `--client-action NAME=PATH`, but not provider-authored script creation, validation, registration, accepted hashes, and later governed `run_script(name, inputs)` execution.

## 6. Alignment Audit Against `wave1-6-B-actions-spec.md`

`wave1-6-B-actions-spec.md` is directionally correct about the future goal: provider-authored skills/scripts should be written as normal files, FirmCLI should validate/sync them, and API fallback should use accepted registry/context rather than native folders.

However, it has wording gaps relative to this ground truth:

1. **Editing-mode wording is too restrictive.** The spec currently frames user-owned skill editing as allowed only in a skill-authoring/sync mode. Correct wording: providers can edit user-owned workspace files natively as ordinary file edits; the skill-authoring/sync mode gates validation, repair prompting, acceptance, registry sync, and use.
2. **"Model-native" / fallback terminology remains legacy.** Any reference to API/fallback skill loading as model-native should be rewritten as agent-loaded fallback context.
3. **Import-surface wording should distinguish detection from acceptance.** User-owned `.codex` / `.claude` folders are edit/detection surfaces before validation, but they become accepted imported skill source only after deterministic validation and registry sync.
4. **Projected preload wording must stay separate from user-owned skill wording.** The spec should consistently treat preloaded mirrors as read/use delivery surfaces, not editable deliverables and not user-owned source.

These are terminology and acceptance-boundary gaps, not a rejection of the Wave 1.6-B future goal.

## 7. Corrected One-Sentence Product Goal

FirmCLI should keep the current preloaded-skill delivery behavior for packaged skills, then add a separate user-owned native skill sync pipeline where provider file edits in the user's codebase are detected, validated, repair-looped until syncable, accepted into a client-owned registry, and exposed to API providers through agent-loaded fallback context.
