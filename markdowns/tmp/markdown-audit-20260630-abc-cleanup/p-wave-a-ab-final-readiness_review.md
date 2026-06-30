# Review for P-Wave-A A/B final-readiness check

Task: Review current `P-Wave-A` with Branch B merged in against Branch A scope,
Branch B scope, the superpowers playbooks, and the final R12 product direction.

## Verdict

CLEAN FOR A/B SMALL-GAP SURFACE

The code is clean for the declared A+B prototype boundary: provider-session
continuity, tool-schema prompt forwarding, governed batches, bounded `wait`,
UART write, and session-scoped client actions are implemented and covered by
the current non-hardware suite.

The small source-of-truth and whitespace gaps from the first review pass have
now been fixed. This does not close the broader deployment/hardware proof items
listed below.

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |
| none | Doc-sync / single source of truth | `markdowns/curr/r12_turnkey_spec.md:94` and `markdowns/curr/r12_turnkey_spec.md:417` | Resolved: the active R12 contract now marks Branch B's implemented surface as current and keeps dynamic in-turn client-action registration, timeout policy, inspector/progress, stream checkpoints, scoped green approval, and deployment proof as pending where appropriate. | n/a |
| none | Hygiene / pre-commit whitespace | `markdowns/tmp/curr-archive-20260628/p_wave_a_chat_handoff_2026_06_28.md:171` | Resolved: the extra trailing blank line at EOF was removed. | n/a |

## Hardware hand-off status

No new hardware proof was run in this review pass.

Existing process-ledger evidence says the merged A/B surface is green on the
attached pair `nucleo_l476rg + nrf52840dk`, including real Claude CLI and
Codex CLI repair benchmarks and a public client-action smoke. A 2026-06-30
local audit found that the Branch A `runs/20260629T03...`, `04...`, `17...`,
and `18...` artifact directories are not present in this checkout, so those
specific run artifacts cannot be reinspected locally until restored.

Still pending before broader/final product claims:

- exact official Nordic proof with an actual `nrf52833dk` attached;
- fresh supported Windows and macOS post-bootstrap deployment proof;
- API-provider parity proof for `openai-api` and `anthropic-api`;
- one-shell multi-prompt proof for `pyocd-debug`;
- final robust provider integrations through Codex SDK/app-server style APIs
  and Claude Agent SDK sessions, if those remain the intended product path;
- Branch C timeout/session-scoped timeout policy and later Wave 2 items
  (progress/inspector, stream checkpoints, scoped green approval, static
  context/cache work).

## What is genuinely good

- The default check ladder passed here: `324` pytest tests, ruff, and mypy.
- The stricter suite ladder passed here: pytest, ruff, mypy including harnesses,
  `34` R11 benchmark tests, and R11 benchmark help.
- Focused A/B tests passed here: `156` tests covering the turnkey loop, provider
  resume, Branch B action surface, server runtime tools, and UX CLI behavior.
- The implementation keeps the model-facing server surface curated instead of
  exposing every MCP server function.
- Headless provider resume failures fail closed by default, and recovery-created
  sessions are explicitly labeled in provider metadata/events.
- Client actions are session-scoped, snapshotted by hash, audited in
  `client_actions.json`, and routed through a gated server API.

## Verified

- Read the superpowers review/coding/doc-sync/portability/script-doc rules and
  the build plan.
- Read the active A/B/R12 status docs and current implementation files for
  provider sessions, schema forwarding, action policy, client actions, loop
  execution, providers, and server UART write.
- Ran `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`.
- Ran `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`.
- Ran focused pytest for `tests/test_r12_turnkey.py`,
  `tests/test_r12_turnkey_merge.py`, `tests/test_p0_foundation.py`,
  `tests/test_server_runtime_tools.py`, and `tests/test_ux_cli.py`.
- Ran `git diff --check HEAD~20..HEAD`.
- Follow-up fix pass synced `markdowns/curr/r12_turnkey_spec.md` to the
  implemented Branch B surface and removed the archived EOF whitespace warning.
- Follow-up validation passed:
  `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset default`
  (`324` pytest tests, ruff, and mypy).
- Follow-up stale-text scan found no remaining A/B implementation-status
  contradiction in the active A/B docs checked.
- Follow-up `git diff --check` on the touched docs passed, with only Git
  LF-to-CRLF working-copy notices.

## Pending verification

- Hardware items listed above.
- No live provider/API or board commands were executed in this review turn.
- Restoration or rerun of the missing Branch A/B run folders if artifact-level
  reinspection is required.
