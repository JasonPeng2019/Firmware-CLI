# Things-To-Change Entry 14 Skill Surface Addendum

> STATUS: ACTIVE ADDENDUM - source of truth for `markdowns/things-to-change.md`
> Prototype Priority item 14 until the large backlog file is directly reconciled.
> If this addendum conflicts with Entry 14 wording, this addendum wins for
> skill-surface terminology and ownership.

## Why This Exists

Entry 14 currently says the prototype needs a skill index and on-demand skill
bodies for static-context efficiency, including `load_skills(skill_ids=[...])`.
After the provider-native bridge and Wave 1.6-B planning, that wording needs one
ownership clarification:

> Skill loading, provider-native projection, and native provider skill authoring
> are three different surfaces. They must not all be called `.codex` or
> `.claude` skills without qualification.

Use `markdowns/curr/r12v2-skill-surface-ownership_spec.md` and
`markdowns/curr/wave1-6-B2-skill-terminology-and-user-native-sync-gap.md` as the
vocabulary source for this entry.

## Entry 14 Interpretation

Prototype Priority item 14 now means:

1. FirmCLI has **actual skills to preload**. These live in FirmCLI/client-owned
   source packages or a validated registry, and they are the source for
   `load_skills` fallback.
2. CLI providers can receive **projected preloaded skills**. These are generated
   runtime views under provider-native layouts such as `.codex/skills` or
   `.claude/skills`. Providers can see and use them, but should not edit them as
   deliverables.
3. Users may have **user-owned skills** in a target workspace. Providers can see
   and edit them natively as ordinary workspace files. Validation, repair
   prompting, acceptance, registry sync, and use are gated by the sync flow.
4. User-owned skills must sync into a client-owned registry before API fallback
   is considered successful.
5. The workspace diff filter must not hide all `.codex`, `.claude`, or
   `.agents` paths. It should ignore only marker-proven projected preloads and
   preserve user-owned skill changes.

## Links

- Vocabulary: `markdowns/curr/r12v2-skill-surface-ownership_spec.md`
- Ground truth gap record: `markdowns/curr/wave1-6-B2-skill-terminology-and-user-native-sync-gap.md`
- Provider-native projection: `markdowns/curr/r12-provider-native-skill-bridge_spec.md`
- Bridge addendum: `markdowns/curr/r12v2-provider-native-skill-bridge-ownership-addendum.md`
- Native authoring and fallback sync: `markdowns/curr/wave1-6-B-actions-spec.md`
- Skill tree docs: `skills/README.md`

## Direct Replacement Wording For Entry 14

When `markdowns/things-to-change.md` is next directly reconciled, replace the
provider-native skill paragraph under item 14 with wording equivalent to:

> Provider-native skill bridge hardening distinguishes actual skills to preload,
> projected preloaded skills, and user-owned skills. Actual skills to preload
> remain FirmCLI/client-owned source packages or validated registry entries.
> CLI providers may see generated projected preloaded skills under run-local
> `.codex/skills` or `.claude/skills`, but may not edit those projections as the
> deliverable. Providers may natively edit user-owned target-workspace native
> skill folders as ordinary file edits. Successful sync copies validated
> user-owned skills into the client-owned registry so API providers can use the
> same skill through `load_skills` or the registry-backed fallback path.
