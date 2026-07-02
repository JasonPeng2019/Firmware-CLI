# R12v2 Build Plan Addendum

> STATUS: ACTIVE ADDENDUM - source of truth for R12 skill-surface wording in
> `markdowns/build-plan.md` / build-plan references until those files are directly
> reconciled.
>
> If this addendum conflicts with older build-plan R12 wording, read this addendum
> as the authoritative correction.

Use `markdowns/curr/r12-skill-surface-ownership_spec.md` and `markdowns/curr/wave1-6-B2-skill-terminology-and-user-native-sync-gap.md` for corrected skill wording.

Actual skills to preload are source packages or validated registry entries.
Projected preloaded skills are generated runtime views for CLI providers.
User-owned skills live in the target workspace.

Providers can see projected preloaded skills and user-owned skills. Providers can edit user-owned workspace skill files natively as ordinary file edits; validation, repair prompting, acceptance, registry sync, and use are gated by the sync flow.

API fallback is successful only after validated user-owned skills sync into the client-owned registry used by `load_skills` or the registry-backed equivalent.
