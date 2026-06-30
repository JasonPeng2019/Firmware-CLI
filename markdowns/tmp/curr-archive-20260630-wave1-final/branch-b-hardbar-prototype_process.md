# Process Ledger For Branch B Hardbar Prototype

## Goal And Roadmap Anchor

Task: implement and validate the Branch B free-host-work / governed-board
decision boundary required by the prototype contract.

Roadmap anchor: `things-to-change.md` Prototype Priority item 2 and
`R12_P_SPLIT.md` Branch B.

## Done

- Read the relevant workflow skills and Claude command mirrors for
  write-process, spec-loop, test-suite, fix-bug, and Python-change.
- Reconfirmed the product requirement from `things-to-change.md`: host work is
  model-native/free; board access is brain-governed; every turn closes with one
  governed or terminal decision.
- Audited the current Branch B implementation and found the hardbar miss:
  `read_file`, `replace_file`, and `run_build` were still advertised and
  executable as TurnDecision actions.
- Removed those host actions from the model-facing TurnDecision schema.
- Updated the turnkey prompt to instruct provider-native host work instead of
  brain-governed file/build actions.
- Added deterministic refusal for stale direct or batched host actions.
- Kept `run_green_check` governed because it exercises the board verification
  path.
- Added event evidence for provider-native workspace changes observed at a
  governed boundary.
- Updated focused regression tests for schema, classification, stale-action
  refusal, and provider-native host edit followed by governed flash/green-check.

## In Progress

- Claude CLI live code-writing rerun is blocked by external provider quota until
  the reset window.
- Exact official `nrf52833dk` proof is pending because the attached Nordic board
  identifies as `nrf52840dk`.

## TODO

- After Claude quota resets, rerun the Claude CLI code-writing benchmark from
  scratch on `nucleo_l476rg` and then `nrf52840dk`.
- If Claude passes on the attached pair, rerun the same ladder on the official
  `nrf52833dk` when that board is attached.
- Continue to treat Wave 2 modules as prototype-required scope, not closed by
  this Branch B hardbar pass.

## Limitations And Known Gaps

- This pass does not implement Wave 2 modules: progress UI, stream checkpoints,
  scoped green approval, cache/static-context efficiency, or process cleanup
  guard.
- CLI providers still use subprocess-per-turn resume bridges, not final SDK
  integrations.
- Full success is not claimed until Pyright, pytest, live provider turns, and
  both-board checks are green.

## Hardware Hand-Off

Current attached-board evidence is green for `nucleo_l476rg + nrf52840dk` with
Codex CLI. Claude CLI remains pending because this session hit:

```text
You're out of extra usage - resets 7:30am (America/New_York)
```

Morning rerun commands:

```powershell
uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__b001_wrong_boot_text --max-iters 8 --serial-read-seconds 1.0
uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nrf52840dk__b001_wrong_boot_text --max-iters 8 --serial-read-seconds 1.0
```

## Open Decisions And Surfaced Issues

- Private compatibility helpers for old host actions remain in code, but the
  schema, prompt, batch parser, and executor now prevent them from being used as
  governed model-facing decisions.

## Verified

- Focused local boundary tests passed on 2026-06-30:
  `uv run pytest -q tests/test_p0_foundation.py::test_action_policy_classifies_branch_b_boundaries tests/test_p0_foundation.py::test_turn_decision_schema_excludes_model_native_host_actions tests/test_r12_turnkey.py::test_run_turnkey_refuses_model_native_read_file_action tests/test_r12_turnkey.py::test_run_turnkey_allows_green_check_after_first_failed_fix_verification`
- Non-hardware suite ladder passed on 2026-06-30:
  `342 passed`, ruff clean, mypy clean, `34` R11 benchmark tests passed, and
  R11 benchmark help rendered.
- Python-change gate passed on 2026-06-30: ruff check/fix, ruff format, full
  Pyright `0` diagnostics across `105` analyzed files, and full pytest
  `342 passed`.
- Attached `nucleo_l476rg` passed host bootstrap, Stage 0 flash/UART, and Stage
  1 smoke on 2026-06-30.
- Attached `nrf52840dk` passed host bootstrap, Stage 0 flash/UART/recover, and
  Stage 1 smoke on 2026-06-30.
- Branch C live harness with Codex CLI passed on both attached boards:
  `nucleo_l476rg` run root `20260630T080831Z-b996d530`; `nrf52840dk` run root
  `20260630T081021Z-31f3aaae`.
- Codex CLI code-writing `b001_wrong_boot_text` benchmark passed
  `FULL_SUCCESS` on both attached boards:
  `nucleo_l476rg` session `20260630T081152Z-0ed30757`; `nrf52840dk` session
  `20260630T081747Z-32904e64`.
- Process audit after live runs found two new Codex-spawned
  `pyocd-debug-mcp` trees; they were stopped by exact PID. The remaining
  matching MCP trees were pre-existing VS Code/Codex app-server-owned
  processes from the baseline snapshot.

## Pending Verification

- Claude CLI code-writing benchmark after quota reset.
- Exact official `nrf52833dk` proof.
- API-provider parity and fresh-machine portability proof.
