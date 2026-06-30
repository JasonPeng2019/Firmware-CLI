# Review for wave1-adversarial-audit-20260630

Task: Adversarial audit and validation pass for Wave 1 A/B/C plus Branch B
model-native skills and compact tool index.

## Verdict

CLEAN FOR AGENT-VERIFIABLE SCOPE after fixes and repeated audit. The remaining
criticisms are external proof blockers: Claude quota reset and exact
official-board availability. Do not convert those into a full product-suite
green claim until rerun.

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |
| High | Branch B product boundary | `src/pyocd_debug_mcp/brain/model_native_skills.py` | Init scripts are brain-mediated context expansion but originally ran as arbitrary subprocesses after only cwd/env/timeout setup. That violated the hard requirement that init scripts must not directly access board hardware or bypass governed server tools. | Add preflight validation before execution that rejects known direct probe/serial imports and direct board/probe command subprocess calls; add focused tests. |
| Medium | Skill namespace integrity | `src/pyocd_debug_mcp/brain/model_native_skills.py` | A folder `actual/skill.yaml` could declare `skill_id: spoofed`, which would skew closure IDs, state keys, prompt context, and runtime paths. | Require manifest `skill_id` to match the requested folder ID. |
| Medium | Active docs | `markdowns/things-to-change.md` | Prototype entry #11 still said `run_build` and firmware source edits were governed actions, contradicting the 2026-06-30 Branch B hard bar that removed `read_file`, `replace_file`, and `run_build`. | Update entry #11/#12 to make provider-native host work and `load_skills` the current rule, with Claude/exact-board proof still pending. |
| Info | Verification scope | `markdowns/curr/next-codex-handoff-20260630.md` | Full product closure cannot be truthfully claimed while Claude usage is exhausted and exact `nrf52833dk` proof is unavailable. | Keep this as a handoff blocker and rerun the listed Claude/live checks after quota reset and hardware availability. |

## Resolution

- High finding fixed in `model_native_skills.py` with init-script policy
  preflight and regression tests.
- Medium namespace finding fixed with manifest ID/folder ID validation and a
  regression test.
- Medium active-doc finding fixed in `things-to-change.md`.
- Repeated audit found no reintroduced removed host action models, executor
  branches, refusal paths, or full-schema prompt injection.
- Local validation green:
  - `tests/test_model_native_skills.py` -> `5 passed`;
  - Python-change gate -> Ruff pass, Pyright `0`, full pytest `350 passed`;
  - suite preset -> pass;
  - Codex host-native smoke -> pass at
    `runs/turnkey-20260630T090753Z-02dee333`;
  - Codex `load_skills` smoke -> pass at
    `runs/turnkey-20260630T090914Z-044ef516`;
  - Codex compact tool-index smoke -> pass at
    `runs/turnkey-20260630T090947Z-703de0e5`.

## Criticisms reviewed as no-merit or not actionable

- Compact tool index omits full JSON schema bodies: no merit. This is the
  requested product behavior; full schemas remain in records for provenance.
- Provider-native host tools are not sandboxed by the turnkey brain: no merit
  for this pass. The accepted design stance assigns host-machine safety to the
  provider/runtime sandbox and keeps the brain responsible for the board
  boundary. The valid exception is brain-mediated skill init scripts, which this
  audit fixes.
- `WorkspaceSession.read_file`, `replace_file`, and `run_build` still exist as
  internal helpers: no merit. They are no longer governed `TurnDecision`
  actions, schema variants, prompt-visible decisions, or executor branches.

## Hardware hand-off status

- Codex no-hardware proof is available and will be rerun after the fix.
- Claude proof is blocked by quota until reset.
- Existing attached-board Codex proof uses `nucleo_l476rg` plus `nrf52840dk`;
  exact official `nrf52833dk` proof remains pending if the product bar requires
  that board specifically.

## What's genuinely good

- Removed host actions are structurally absent rather than refused.
- `load_skills` dependency closure, cycle detection, repeat no-op behavior, and
  prompt injection are covered by focused tests.
- Compact tool index keeps the model-facing prompt small while preserving full
  schema provenance internally.
