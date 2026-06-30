# Process ledger for r12-delta-compact-indexes

## Goal and roadmap anchor

Task: Implement and validate compact skill/tool indexes in remote-delta provider turns
Roadmap anchor: R12 Stage 5 Wave 1

## Done

- Loaded FirmCLI workflow skills: `firmcli-specs`, `firmcli-write-process`,
  `firmcli-spec-loop`, `firmcli-test-suite`, `firmcli-fix-bug`,
  `firmcli-workflow-core`, and `python-change`.
- Loaded authority docs and reconciled the task against the build plan, active
  R12 turnkey spec, scaffold-hardening spec, current provider render code, and
  provider tests.
- Created `markdowns/curr/r12-delta-compact-indexes_spec.md`.
- Confirmed starting worktree for this pass only had the new spec/process docs.
- Implemented `remote-delta` rendering as compact skill context + compact
  governed-tool index + turn context.
- Updated remote-primary provider metadata so compact tool-index injection is
  true on normal `remote-delta` turns when a compact tool index is present.
- Updated focused provider prompt tests for OpenAI, Claude CLI, Codex CLI, and
  the prompt bundle.
- Focused prompt/provider pytest passed:
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle" tests/test_r12_turnkey_merge.py -k "previous_response_id or resumes_remote_session or resumes_remote_thread or retry_updates_prompt_metadata"`
  -> `5 passed, 90 deselected`.

## In progress

- Complete.

## TODO

- None for the agent-verifiable surface.

## Limitations and known gaps

- This change intentionally does not alter provider memory cadence; memory still
  follows `native_sync_every`.
- This change intentionally does not inject full MCP schemas or full skill
  bodies every turn.
- Claude CLI live proof remains external-auth dependent if the local CLI is not
  logged in.
- API-provider parity remains credential dependent.

## Hardware hand-off

- Codex CLI provider + live hardware passed on both attached boards:
  - `nucleo_l476rg`: `runs/20260630T200822Z-b69e332f`
  - `nrf52840dk`: `runs/20260630T201005Z-f2c1d62b`

## Open decisions and surfaced issues

- No settled-decision conflict found. The build plan already points toward
  compact selected-skill and governed-tool indexes every provider turn.

## Verified

- Reconciliation/design spec completed.
- Focused prompt/provider pytest passed:
  `5 passed, 90 deselected`.
- Python-change gate passed:
  Ruff check/format, Pyright JSON, full pytest `359 passed`.
- FirmCLI suite ladder passed:
  `runs/r12-delta-compact-indexes-suite-report.txt`.
- Live Codex CLI provider + hardware checks passed on both attached boards:
  each `9 passed, 0 failed, 0 skipped`.
- Review artifact is clean:
  `markdowns/curr/r12-delta-compact-indexes_review.md`.

## Pending verification

- Claude CLI live proof after login.
- API-provider parity with credentials.
