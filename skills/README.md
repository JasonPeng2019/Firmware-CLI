# Turnkey Skills

This tree holds the R12 turnkey brain's YAML skill manifests.

Layout:

- `skills/common/`: board-agnostic skills reused across the scoped pair
- `skills/mcu_families/<family>/`: MCU-family-specific skills

Each skill file is data-only and must define:

- `skill_id`
- `title`
- `applies_to`
- `priority`
- `facts`
- `diagnostic_hints`
- `verification_checks`
- `forbidden_actions`
