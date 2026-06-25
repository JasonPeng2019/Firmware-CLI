> STATUS: IMPLEMENTED AND VERIFIED ON WINDOWS NUCLEO REPROOF PASS.

# r12 windows cmdline bug

## Goal in plain English

Task: Fix Windows Codex CLI command-line length overflow in turnkey benchmark runs
Roadmap anchor:
- primary: `R12` turnkey brain
- secondary: Windows portability hardening for CLI-backed providers

## Scope and non-scope

In scope:
- the Codex CLI provider invocation path under
  `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- Windows turnkey runs where long benchmark prompts exceed the Win32 process
  command-line length limit
- regression coverage proving the prompt is sent through stdin rather than as a
  trailing command-line argument
- rerunning the real failing STM32 benchmark case and the surrounding ladder
  after the fix

Out of scope:
- changing the outer turnkey contract
- changing benchmark prompts to be shorter just to avoid the Windows limit
- changing non-Codex provider behavior unless a real bug is reproduced there too

## Reconciliation summary

- Build plan:
  - CLI-backed turnkey providers must remain portable on Windows and macOS and
    must not depend on host-specific shell quirks.
- Current code:
  - the Codex provider appended the fully composed prompt as the final
    positional argument to `codex exec`.
- Other docs or notes:
  - the real failure was reproduced on the attached `nucleo_l476rg` during
    `nucleo_l476rg__b003_silent_uart`.
- Disagreements:
  - none. This is a clear implementation defect, not a product-contract issue.

## Design

- keep the `codex exec` transport and output-file contract unchanged
- switch prompt delivery from command-line argument transport to stdin
- pass `-` to `codex exec` so the CLI reads the prompt from stdin
- keep UTF-8-with-replacement capture in place for stdout/stderr
- add regression tests for:
  - command construction using `-` rather than the full prompt
  - provider subprocess invocation receiving the composed prompt via `input=...`

## Board-facts-as-data and origin tags

- reproduced on `board_id=nucleo_l476rg`
- failing case: `nucleo_l476rg__b003_silent_uart`
- the bug is host-specific to Windows command-line limits, not board-specific

## Documentation plan

- record the fixed boundary in the active process ledger
- update `markdowns/current-progress.md` so the old Windows STM32 / Claude
  provider boundary text does not remain stale

## Portability

- stdin-backed prompt delivery is the portable path across Windows and macOS
- this avoids Win32 `CreateProcess` length failures without changing the model
  prompt contents or the benchmark contract

## Verification plan

- `uv run pytest -q tests/test_r12_turnkey.py -k codex_cli_command`
- `uv run pytest -q tests/test_r12_turnkey_merge.py -k codex_cli_provider`
- `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
- rerun the reproduced real failure:
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b003_silent_uart`
- rerun the remaining STM32 ladder after the fix

## Acceptance criteria

1. The Codex CLI provider no longer places the full prompt on the Windows
   command line.
2. Regression tests prove stdin prompt delivery.
3. The previously failing real STM32 benchmark case is green.
4. The surrounding non-hardware ladder remains green.

## Verified

- regression tests for command construction and provider subprocess capture
  passed
- the non-hardware suite ladder passed after the fix
- the reproduced failing case `nucleo_l476rg__b003_silent_uart` passed after
  the fix
- the remaining STM32 case `nucleo_l476rg__b004_dual_signal_regression` also
  passed afterward

## Pending verification

- full official scoped-pair second-provider suite closure remains outside this
  single Windows STM32 bug-fix artifact
