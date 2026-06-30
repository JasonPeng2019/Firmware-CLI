# Process ledger for r12-context-scaffold-hardening

## Goal and roadmap anchor

Task: R12 context scaffold hardening full write-process and deployment suite
Roadmap anchor: R12 turnkey brain context scaffolding / skill-tool detail loading

## Done

- Implemented `load_tool_details` as a governed context-expansion action.
- Added session-scoped loaded-detail state for governed MCP tools, governed
  client-action scripts, and brain-owned compound actions.
- Added hard details-required guardrails:
  - MCP server tools block and auto-load their full schema before first use.
  - Client-action scripts block and auto-load their script contract before first
    use.
  - `run_green_check` blocks and auto-loads its brain-owned contract before
    first use.
- Added prompt sections for loaded governed tool details, client-action details,
  and brain-owned compound-action details.
- Changed model-native workflow skill loading to copy skill packages into the
  runtime before validation/init/context injection, preserve source/runtime
  provenance, and return structured load failures.
- Removed native-provider wording aliases in favor of remote-provider wording.
- Updated the Branch C live-provider harness task so live provider/hardware
  checks load governed details before connecting.
- Added `details_required` to the event-kind registry.
- Added/updated regressions for `load_tool_details`, focused full-schema detail
  loading, details-required blocking, runtime-copy skill repair, and Branch C
  harness compatibility.

## In progress

- None.

## TODO

- Optional: format pre-existing `.codex/skills/firmcli-workflow-core/scripts/*.py`
  if the team wants `uv run ruff format --check .` to be a repo-wide gate.
  The suite preset does not currently include that gate, and those scripts were
  already dirty outside this R12 patch.

## Limitations and known gaps

- API-provider rows were not run: `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` were
  absent in this shell.
- Claude CLI rows were not green: `claude-cli` exists but returned
  `Not logged in - Please run /login`.
- The exact official `nrf52833dk` board was not attached. The connected Nordic
  probe reports FICR `0x52840`; `stage0_check.py --board-id nrf52833dk` failed
  the silicon identity row as expected. The attached Nordic board was verified
  as the retained alternate `nrf52840dk`.

## Hardware hand-off

- To close exact official-pair proof, attach a true `nrf52833dk` and run:
  - `uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk`
  - `uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk`
  - `uv run python -m tests.harness.branch_c_tests --board-id nrf52833dk --provider codex-cli --provider-timeout-seconds 300 --fail-on-skip`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52833dk__k001_reference_green --max-iters 8 --serial-read-seconds 3`
- To close Claude provider proof, run `claude /login` in the operator
  environment, then rerun the no-hardware smoke and Branch C provider rows with
  `--provider claude-cli`.
- To close API-provider proof, export `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
  and explicit supported models, then rerun equivalent no-hardware provider
  smokes before any hardware rows.

## Open decisions and surfaced issues

- Decide whether repo-wide `ruff format --check .` should include `.codex`
  workflow scripts. Current evidence: it would reformat `run_check_ladder.py`,
  `scaffold_workflow_doc.py`, and `self_test_skills.py`.

## Verified

- `uv run pytest -q tests/test_p0_foundation.py tests/test_model_native_skills.py tests/test_r12_turnkey.py`
  -> `93 passed`.
- `uv run pytest -q` -> `354 passed`.
- `uv run ruff check .` -> passed.
- `uv run pyright` -> `0 errors, 0 warnings, 0 informations`.
- `uv run python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite --report-path runs/r12-context-scaffold-hardening-suite-report-final.txt`
  -> all 5 suite rows passed, including pytest, ruff, mypy, R11 benchmark
  tests, and R11 benchmark help.
- Real stdio MCP server smoke via `LocalMCPClient`:
  - listed 21 live tools
  - built 13 curated tool-index entries
  - loaded focused full details for `connect`, `read_serial`, and
    `flash_firmware`
  - schema hash `abdeec0b6c74481fe1921fef5f869b3d548b49ca7cabde9ddbc36c802acd42d3`
- Real Codex CLI no-hardware provider loops:
  - `runs/turnkey-20260630T172046Z-4d5f5a2b`: two provider turns on
    `nucleo_l476rg`, `load_tool_details:connect`, then finalize, no MCP board
    calls.
  - `runs/turnkey-20260630T172154Z-553a3a6c`: two provider turns on
    `nrf52833dk`, `load_tool_details:read_serial`, then finalize, no MCP board
    calls.
- Real Stage 1 hardware smokes:
  - `nucleo_l476rg`: flashed, PC read, `stage1_known_value=0x1234ABCD`, UART
    matched `boot ok`.
  - `nrf52833dk` command ran against the attached Nordic probe and passed Stage
    1 behavior, but Stage 0 later proved the silicon is actually `nrf52840`.
  - `nrf52840dk`: flashed, PC read, `stage1_known_value=0x1234ABCD`, UART
    matched `boot ok`.
- Real Stage 0 on attached Nordic profile:
  - `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --confirm-shared-usb nrf52840dk`
    passed silicon identity, flash, and UART; recover remains intentionally
    manual because `--recover-test` was not passed.
- Real Branch C/MCP/provider/hardware harness with Codex CLI:
  - `nucleo_l476rg`: `9 passed, 0 failed, 0 skipped`, run root
    `runs/20260630T172533Z-a279b26a`.
  - `nrf52840dk`: `9 passed, 0 failed, 0 skipped`, run root
    `runs/20260630T172936Z-32828264`.
- Real turnkey benchmark known-good rows with Codex CLI:
  - `nucleo_l476rg__k001_reference_green` -> `FULL_SUCCESS`, score `100`,
    session `20260630T173107Z-9413453c`.
  - `nrf52840dk__k001_reference_green` -> `FULL_SUCCESS`, score `100`,
    session `20260630T173459Z-daf1440d`.
- Cleanup audit after live provider/MCP/hardware rows found no suite-spawned
  lingering children. Remaining matching processes were existing Codex app and
  VS Code/Codex app-server-owned MCP process trees.

## Pending verification

- Exact official `nrf52833dk` live proof on a physical `0x52833` board.
- Claude CLI provider rows after login.
- API-provider rows after credentials/model selection.
