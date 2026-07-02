# Turnkey Skills

This tree holds the R12 turnkey brain's shipped skill assets.

## Layout

- `skills/common/`: board-agnostic diagnostic YAML skills reused across the
  scoped pair.
- `skills/mcu_families/<family>/`: MCU-family-specific diagnostic YAML skills.
- `skills/model_native/`: actual skills to preload through the deterministic
  FirmCLI `load_skills(skill_ids=[...])` fallback path.
- `skills/provider_native/`: actual skills to preload by projecting them into a
  provider-native runtime layout for CLI providers.

## Ownership Vocabulary

Use the vocabulary from
`markdowns/curr/r12-skill-surface-ownership_spec.md`:

1. **Actual skills to preload** are FirmCLI/client-owned source packages or
   validated registry entries. They are the store of record for packaged or
   synced skills.
2. **Projected preloaded skills** are generated provider-visible runtime
   copies/views of actual skills. Codex and Claude can read/use them through
   native skill discovery, but they are disposable scaffolding, not the editable
   source of truth.
3. **User-owned skills** are target-workspace `.codex`, `.claude`, or similar
   native skill folders. They are visible to the user and may be natively edited
   by the provider only when a user-requested skill-authoring/sync flow is active.

The provider can see projected preloaded skills and user-owned skills. The
provider may only natively edit user-owned skills. Actual skills to preload stay
FirmCLI/client-owned and are updated only by explicit validation/sync.

## Diagnostic YAML Skills

Diagnostic YAML files under `skills/common/` and `skills/mcu_families/` are
data-only and must define:

- `skill_id`
- `title`
- `applies_to`
- `priority`
- `facts`
- `diagnostic_hints`
- `verification_checks`
- `forbidden_actions`

## Model-Native Fallback Skills

Model-native workflow skills under `skills/model_native/<skill_id>/` use folder
manifests:

- `skill.yaml`
- `SKILL.md`
- optional `references/` or `scripts/`

They are copied into the provider runtime by the brain when a provider returns
`load_skills`. Installed source packages are read-only. Any repair or execution
uses a runtime copy and then must pass deterministic validation before it can
become durable source.

These are actual skills to preload, not projected preloaded skills and not
user-owned target-workspace skills.

## Provider-Native Skills

Provider-native workflow skills under `skills/provider_native/` are also actual
skills to preload. They are FirmCLI/client-owned source packages, not global
`.codex` or `.claude` configuration and not target-workspace user-owned skills.

During a CLI-provider run, the brain generates projected preloaded skills:

- Codex CLI: `<provider-working-dir>/.codex/skills/<skill_id>/`
- Claude CLI: `<provider-working-dir>/.claude/skills/<skill_id>/`

Projected preloaded skills should carry FirmCLI projection provenance, such as
`.firmcli-provider-native-projection.json`. They are regenerated or discarded as
runtime scaffolding and should not be counted as firmware/source edits in run
diffs.

Provider-native skill manifests must include:

- `skill_id`
- `title`
- `description`
- `providers`
- `native_invocation`
- `fallback_skill_ids`
- `context_files`
- `usable_paths`
- `requires_governed_actions`
- `source_status`

Provider-native skills are host-reasoning accelerators only. Board actions still
return through FirmCLI `TurnDecision`, loaded-detail guardrails, recover gates,
and cleanup rules.

## User-Owned Native Skill Sync

Wave 1.6-B will add a separate sync flow for user-owned native skill folders in a
target workspace, such as `.codex/skills` or `.claude/skills`.

That flow is not the same as projection:

1. The provider natively edits user-owned skill files in the target workspace.
2. FirmCLI scans and validates those files.
3. Valid skills sync into a client-owned registry.
4. API providers can use the synced skill through `load_skills` or a
   registry-backed equivalent.
5. CLI providers may later receive projected preloaded views generated from the
   validated registry.

Without that sync into the client-owned registry, API fallback has not succeeded.
