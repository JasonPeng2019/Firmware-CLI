# Review for wave1-turnkey-cleanup-failure

Task: Review final turnkey disconnect cleanup failure fix.

## Verdict

CLEAN for the Wave 1 agent-verifiable and attached-board prototype boundary.

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |
| - | - | - | No must-fix findings remain. | - |

## Hardware hand-off status

- Attached-board proof was rerun on `nucleo_l476rg + nrf52840dk` with both
  `codex-cli` and `claude-cli`.
- Official `nrf52833dk` proof remains pending because the attached Nordic board
  is the retained `nrf52840dk`.
- Full process-tree forced-hang cleanup remains Wave 2 Branch H, not this Wave 1
  fix.

## What's genuinely good

- The cleanup failure is now impossible to silently report as a successful final
  run: `run_turnkey` records `final_disconnect`, preserves the active session id,
  and returns `blocked` / `tooling_failure`.
- The regression covers result status, state visibility, and event evidence.
- Full Pyright is green after the fix, and the full Python-change gate passed.
- Public deployed CLI smokes verified the current entrypoint still performs the
  intended two-turn hardware-touching flow on both attached boards with both
  providers.
