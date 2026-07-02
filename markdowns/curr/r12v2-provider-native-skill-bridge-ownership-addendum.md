# R12v2 Provider-Native Skill Bridge Ownership Addendum

> STATUS: ACTIVE ADDENDUM - source of truth for ownership and terminology
> corrections to `r12-provider-native-skill-bridge_spec.md` until that spec is
> directly reconciled.
>
> If this addendum conflicts with the bridge spec, read this addendum as the
> authoritative correction for the implemented projection feature.

The bridge spec's implemented projection feature should be read with the vocabulary in `r12-skill-surface-ownership_spec.md` and the corrected ground truth in `wave1-6-B2-skill-terminology-and-user-native-sync-gap.md`.

## Correction

When the bridge spec says FirmCLI projects provider-native skills into `.codex/skills` or `.claude/skills`, interpret that as:

> FirmCLI projects actual skills to preload into projected preloaded skills under the provider runtime so CLI providers can read and use them through native skill discovery.

Do not interpret it as:

- `.codex` or `.claude` becoming the FirmCLI store of record;
- target-workspace user-owned `.codex` or `.claude` folders becoming client-owned;
- the provider being allowed to edit projected preloaded skills as the deliverable;
- API providers depending on native provider folders.

## Rules

- Actual skills to preload live in FirmCLI/client-owned source packages or a validated registry.
- Projected preloaded skills are generated runtime views under provider-native layouts.
- User-owned skills live in the target workspace and are visible to the user.
- Providers can see projected preloaded skills and user-owned skills.
- Providers can natively edit user-owned workspace skill files as ordinary file edits. The gated step is validation, repair prompting, acceptance, registry sync, and use.
- API fallback is successful only after user-owned skills sync into the client-owned registry used by `load_skills` or the registry-backed equivalent.

## Diff rule

Run diffs must not blanket-ignore `.codex`, `.claude`, or `.agents`. They should ignore only marker-proven projected preloaded skill subtrees and preserve user-owned skill changes.
