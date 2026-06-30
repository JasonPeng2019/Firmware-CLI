# R12 Branch A Live Provider Status

This is the current compact Branch A / merged A+B live-provider handoff. It
replaces the overlapping Branch A live-provider spec, process ledger, and review
files after their attached-board implementation/review loop completed.

## Current Status

Branch A is implemented for the current prototype boundary:

- provider-session continuity where the provider supports it;
- explicit local-memory fallback where native continuation is not available;
- strict no-silent-fresh-session behavior for modes that promise a continued
  session;
- curated server-tool schema forwarding in the model prompt;
- provider progress events and run artifacts.

The later merged A/B live suite also exercised Branch B's added governed action
surface through the same provider paths.

## Latest Verification

Non-hardware:

- default check ladder passed with `324` pytest tests, Ruff, and mypy;
- suite ladder passed with pytest, Ruff, mypy including harnesses, R11 benchmark
  tests, and R11 benchmark help;
- focused A/B tests passed for turnkey loop behavior, provider resume, Branch B
  action surface, server runtime tools, and UX CLI behavior.

Attached-board live provider proof:

- `codex-cli` and `claude-cli` both ran real attached-board repair tasks;
- proof covered the attached `nucleo_l476rg + nrf52840dk` pair;
- the attached Nordic board identified as `nrf52840dk`, not the official scoped
  `nrf52833dk`;
- the run ledger recorded public `--client-action` execution, provider resume
  handles, and no unlabeled recovery-created replacement provider session.

A 2026-06-30 local audit found that the Branch A/B run directories named in the
archived process ledger under `runs/20260629T03...`, `runs/20260629T04...`,
`runs/20260629T17...`, and `runs/20260629T18...` are not present in this
checkout's local `runs/` tree. The historical verdicts are preserved in the
archived ledger, but those untracked artifacts cannot be reinspected locally
unless restored or rerun.

## Remaining Proof

Before claiming exact official scoped-pair closure for Branch A, rerun the live
provider matrix with an actual `nrf52833dk` attached:

```powershell
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider claude-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
```

Paid API-provider parity remains pending until real `openai-api` and
`anthropic-api` credits are available.

## Archived Source Docs

The detailed build-loop artifacts that produced this status were moved to:

```text
markdowns/tmp/markdown-audit-20260630/
```

Relevant archived files include:

- `branch-a-live-provider-hardware-suite_spec.md`
- `branch-a-live-provider-hardware-suite_process.md`
- `branch-a-live-provider-hardware-suite_review.md`

## Verified

- This file was reconciled against the former Branch A spec/process/review
  cluster, `current-progress.md`, `r12_turnkey_spec.md`, and the repository's
  current provider/action code.

## Pending Verification

- Exact `nrf52833dk` Branch A/second-provider closure.
- Paid OpenAI/Anthropic API-provider proof.
- Restoration or rerun of the missing Branch A/B run folders if artifact-level
  reinspection is required.
