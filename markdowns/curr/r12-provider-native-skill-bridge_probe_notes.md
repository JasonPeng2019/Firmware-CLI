# R12 Provider-Native Skill Bridge Probe Notes

Date: 2026-07-01

## Purpose

This note records the no-hardware Phase 0 discovery that determines whether the
FirmCLI brain/provider architecture can access provider-native skills in the
same noninteractive CLI modes used by the product.

The proof uses disposable burner skills only. It does not touch pyOCD, serial,
vendor tools, board configs, or hardware.

## Result Summary

| Provider | Version | Candidate | Result | Selected |
| --- | --- | --- | --- | --- |
| Codex CLI | `0.142.2` | `working-dir/.codex/skills/<skill>/SKILL.md` | works in `codex exec` | yes |
| Codex CLI | `0.142.2` | `working-dir/.agents/skills/<skill>/SKILL.md` | works locally | no |
| Codex CLI | `0.142.2` | isolated `CODEX_HOME/skills/<skill>` | not selected | no |
| Claude CLI | `2.1.76` | `working-dir/.claude/skills/<skill>/SKILL.md` | works with `--allowedTools Skill(<skill-id>)` | yes |
| Claude CLI | `2.1.76` | `.claude/commands` legacy command | works, but commands are not skills | no |
| Claude CLI | `2.1.76` | `--json-schema` mode | probe hung | no |

## Claude Proof

The working command shape was:

```powershell
'/firmcli-claude-proof' | claude --print --output-format json `
  --permission-mode bypassPermissions `
  --allowedTools 'Skill(firmcli-claude-proof)' `
  --append-system-prompt 'Return only JSON. Do not read files. Use the requested native skill if available.' `
  --no-session-persistence --max-budget-usd 0.05
```

Evidence:

- A burner skill under the disposable provider working directory's Claude
  skills folder returned the hidden token from its `SKILL.md`.
- Natural-language invocation also worked when the same `Skill(...)` allowance
  was present.
- Running without a useful skill allowance did not prove native skill access.
- `--json-schema` mode hung in this probe and is rejected for the current
  FirmCLI provider path.

Implementation decision:

- Project FirmCLI provider-native skills into the provider working directory
  under `.claude/skills`.
- Pass `--allowedTools Skill(<skill-id>)` for every projected Claude skill.
- Do not use `--json-schema` for the current bridge.

## Codex Proof

Evidence:

- A burner skill under `working-dir/.codex/skills/<skill>/SKILL.md` was visible
  to `codex exec` and returned the expected hidden token.
- A burner skill under `.agents/skills` also worked locally.
- `.codex/skills` is selected because the requested product behavior is native
  `.codex` behavior and because it is project-local to the runtime working
  directory.

Implementation decision:

- Project FirmCLI provider-native skills into the provider working directory
  under `.codex/skills`.
- Prompt Codex to use `$<skill-id>` or explicit skill requests as the preferred
  native invocation style.

## API Provider Decision

OpenAI API and Anthropic API providers do not receive native `.codex` or
`.claude` runtime projections in this pass. They stay on the deterministic
FirmCLI fallback path:

- compact provider-native skill index when useful;
- request `load_skills(skill_ids=[...])` if full workflow context is needed;
- no dependency on local Codex or Claude CLI auth.

## Safety Notes

- No global user `.codex`, `.claude`, or `.agents` folders are written.
- Projection happens inside the provider runtime/working directory.
- Provider-native skills are host-reasoning accelerators only; board actions
  still return through FirmCLI `TurnDecision` and loaded-detail guardrails.
- Provider self-report that a skill was used is not treated as proof. Proof in
  this note came from burner-skill-only hidden-token output.
