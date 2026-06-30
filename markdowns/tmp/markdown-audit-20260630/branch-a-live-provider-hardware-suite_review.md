# Review for Branch A live provider hardware suite

Task: Review the post-refresh Branch A/B live provider suite, including the
fix-bug loop for nested legacy `server_tool` arguments.

## Verdict

CLEAN FOR ATTACHED-BOARD SCOPE

Official `nrf52833dk` closure remains pending because the connected Nordic
board identifies as `0x52840`; the live suite is green for the actual attached
pair, `nucleo_l476rg + nrf52840dk`.

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |
| none | attached-board live provider suite | n/a | No blocking issue remains after the nested legacy `server_tool` normalization fix and rerun. | n/a |

## Hardware hand-off status

No hand-off is needed for the attached-board scope; this session ran the live
commands directly.

Still pending for official closure:

- attach an actual `nrf52833dk`;
- rerun the same Claude/Codex provider repair matrix on
  `nrf52833dk + nucleo_l476rg`;
- run Anthropic/OpenAI API provider smokes only when paid API credits are
  available.

## What is good

- The full non-hardware ladder is green after the fix: `324` pytest tests,
  ruff, mypy, `34` R11 benchmark tests, and R11 benchmark help.
- Stage 1 is green on both attached boards.
- Claude CLI completed two real code-writing repair prompts on each attached
  board.
- Codex CLI completed the same comparison repair prompts on each attached
  board.
- The public client-action path is green and records audited execution.
- The process ledger records that representative artifacts showed provider
  remote resume handles and no recovery-created replacement provider session.
- The review/process ledger records the relevant run IDs. A 2026-06-30 local
  audit found that the Branch A `runs/20260629T03...`, `04...`, `17...`, and
  `18...` artifact directories are not currently present in this checkout, so
  those specific artifacts cannot be reinspected locally until restored.

## Verified

- See `markdowns/curr/branch-a-live-provider-hardware-suite_process.md` for
  commands, run IDs, and artifact evidence.
- Local run-artifact reinspection is currently limited by the missing untracked
  Branch A/B run folders noted above.

## Pending verification

- Official `nrf52833dk` second-provider closure.
- Paid API-provider smokes.
- Restoration or rerun of the missing Branch A/B run folders if artifact-level
  reinspection is required.
