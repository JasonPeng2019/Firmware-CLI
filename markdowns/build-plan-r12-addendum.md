# R12 Build Plan Addendum

Use `markdowns/curr/r12-skill-surface-ownership_spec.md` for R12 skill wording.

Actual skills to preload are source packages or validated registry entries.
Projected preloaded skills are generated runtime views for CLI providers.
User-owned skills live in the target workspace.

Providers can see projected preloaded skills and user-owned skills. Providers can author skill changes only in user-owned skill folders during the appropriate sync flow.

API fallback is successful only after validated user-owned skills sync into the client-owned registry used by `load_skills` or the registry-backed equivalent.
