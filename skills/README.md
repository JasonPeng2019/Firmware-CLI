# Turnkey Skills

This tree holds the R12 turnkey brain's shipped skill assets.

Layout:

- `skills/common/`: board-agnostic skills reused across the scoped pair
- `skills/mcu_families/<family>/`: MCU-family-specific skills
- `skills/model_native/`: deterministic FirmCLI workflow skills loaded by the
  brain through `load_skills(skill_ids=[...])`
- `skills/provider_native/`: FirmCLI-owned native provider skill packages that
  are projected into a run-local `.codex/skills` or `.claude/skills` view for
  CLI providers

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

Model-native workflow skills under `skills/model_native/<skill_id>/` use
folder manifests:

- `skill.yaml`
- `SKILL.md`
- optional `references/` or `scripts/`

They are copied into the provider runtime by the brain when a provider returns
`load_skills`. Installed source packages are read-only; any repair or execution
uses the runtime copy.

Provider-native workflow skills under `skills/provider_native/` are also
FirmCLI-owned source packages. They are not global `.codex` or `.claude`
configuration. During a CLI-provider run, the brain generates a runtime view:

- Codex CLI: `<provider-working-dir>/.codex/skills/<skill_id>/`
- Claude CLI: `<provider-working-dir>/.claude/skills/<skill_id>/`

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
and cleanup rules. If native skill handling is unavailable or uncertain, the
provider should request the model-native fallback with `load_skills`.
