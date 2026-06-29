> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Branch A Live Provider Hardware Suite

## Goal in plain English

Validate the merged Branch A/B surface as an `R12` / `G7` closure candidate on
real hardware. The run must prove that the current turnkey CLI can drive both
real local CLI providers, `codex-cli` and `claude-cli`, through multiple
top-level user tasks where each task is allowed to run a full provider/tool loop,
write simple firmware code in a benchmark workspace, rebuild, flash, and pass
runner-owned final verification.

The roadmap anchor is `R12` Stage 5: turnkey brain, skills, CLI, provider
continuity, governed board actions, and the frozen benchmark corpus on the
official scoped pair.

## Scope and non-scope

In scope:

- Clean up stale `markdowns/curr/` artifacts so active docs reflect the merged
  `P-Wave-A` state.
- Run the non-hardware suite ladder after the A/B merge.
- Discover the attached boards and run host/bootstrap substrate checks for both
  boards that will be used in this proof.
- Prefer the official scoped pair: `nrf52833dk` and `nucleo_l476rg`.
- If the attached Nordic board is `nrf52840dk` rather than `nrf52833dk`, record
  that as an alternate-board proof and keep official `nrf52833dk` closure
  pending instead of pretending the retained profile closes the official gate.
- Run real `codex-cli` and real `claude-cli` providers through freeform healthy
  hardware tasks on both available boards.
- Run multiple top-level code-writing benchmark tasks for each provider/board
  combination. The minimum acceptance set is two injected-code-bug cases per
  provider per board, using `b001_wrong_boot_text` and
  `b002_wrong_known_value` when those cases exist for the board.
- For every benchmark task, require actual workspace edit/build/flash/final
  green verification artifacts under `runs/<session_id>/`.
- Inspect artifacts enough to prove no silent fresh-provider fallback hid a
  resume failure, and that recovery-created sessions, if any, are labeled as
  new provider sessions.
- Fix any real code defect exposed by the suite through the normal
  `firmcli-fix-bug` loop, rerun the targeted failure, then rerun the full
  suite from the beginning.

Out of scope:

- Changing provider semantics, benchmark taxonomy, board IDs, or the R12 closure
  bar unless the live run exposes an actual bug.
- Claiming fresh-machine Windows/macOS portability from this current workspace.
- Treating `anthropic-api` as equivalent to `claude-cli` session continuity.
- Treating a retained alternate Nordic proof as official `nrf52833dk` closure.
- Adding a new interactive multi-user session feature if the existing product
  only supports sequential top-level `run`/`benchmark` invocations. Sequential
  top-level tasks are the objective deployment proof for this pass.

## Reconciliation summary

- Build plan: `R12` requires the turnkey brain/CLI to run the full loop on the
  scoped pair, reuse the frozen benchmark corpus, preserve provider session
  continuity where available, fail closed on real-session resume failure, keep
  board facts in YAML/data, and use governed board actions for flash/UART/SWD.
- Current code: `pyocd-debug-brain run` supports task-file input, provider
  selection, workspaces, build commands, client actions, and bounded iteration
  loops. `pyocd-debug-brain benchmark` prepares benchmark workspaces, calls the
  same brain loop, records artifacts, and performs runner-owned final
  verification.
- Other docs or notes: `README.md` and `current-progress.md` say Codex CLI has
  prior scoped-pair proof, Claude CLI has only partial proof, Branch B has
  attached-board deployment proof, and broader multi-prompt deployment proof
  remains open.
- Disagreements: no implementation conflict is known before running the suite.
  There is one hardware-scope ambiguity: earlier Windows proof used attached
  `nrf52840dk` while the official scoped pair remains `nrf52833dk` plus
  `nucleo_l476rg`. This suite resolves that by testing the attached boards but
  only marking official closure if `nrf52833dk` is actually present.

## Design

The suite is validation-first. It does not introduce new code unless a real
failure appears.

The proof surface is split into four layers:

1. Non-hardware regression ladder: the existing `run_check_ladder.py --preset
   suite` output proves unit, lint, type, and benchmark harness health.
2. Hardware substrate: `host_bootstrap.py`, `stage0_check.py`, and
   `tests.harness.stage1_smoke` prove the attached boards before provider runs.
3. Freeform turnkey deployment: `pyocd-debug-brain run --provider ...` and
   `pyocd-debug run --provider ...` prove the user-facing task path on real
   boards without case scaffolding hiding provider behavior.
4. Code-writing benchmark deployment: repeated `pyocd-debug-brain benchmark
   --case-id ... --provider ...` runs prove that each provider can edit simple
   code, build, flash, and pass final verification. Each benchmark case is
   treated as one simulated user prompt with its own full provider/tool loop.

This validates Branch A and Branch B additively: Branch A owns provider/session
continuity and strict resume failure handling; Branch B owns task-file input,
action batches, bounded wait, UART write, and client action routing. The test
does not force every Branch B action into every benchmark case, but at least one
freeform deployment task must exercise a registered `--client-action` and the
`run_script` path on available hardware.

## Board-facts-as-data and origin tags

No new board facts are introduced by this spec. Existing board IDs, pyOCD
targets, baud rates, probe families, recover policy, and UART expectations must
continue to come from `boards/<board>.yaml` through the shared loader.

Relevant values:

- `nrf52833dk`: PROJECT-DEFINED canonical official Nordic board ID.
- `nucleo_l476rg`: PROJECT-DEFINED canonical official STM32 board ID.
- `nrf52840dk`: PROJECT-DEFINED retained alternate Nordic board ID, not a
  substitute for official scoped-pair closure.
- benchmark suite/case IDs: PROJECT-DEFINED frozen acceptance corpus names.
- provider IDs `codex-cli` and `claude-cli`: PROJECT-DEFINED provider adapter
  names over user-installed local CLIs.

## Documentation plan

- Update this spec/process ledger with the exact commands and results.
- Update `markdowns/curr/README.md` so it lists only active current docs.
- Move completed or stale `markdowns/curr/` artifacts to
  `markdowns/tmp/curr-archive-20260628/` rather than leaving them active.
- If live results change the repo status boundary, update `README.md` and
  `markdowns/current-progress.md` in the same unit of work.
- If any product code or tool behavior changes during bug-fix loops, update the
  one authoritative product doc or docstring for that behavior.

## Portability

The commands must run through `uv run` and repo entrypoints. Prompts that are
long or quote-heavy should use `--task-file` to avoid shell-specific quoting and
Windows command-line length failures. No command may depend on a hard-coded
probe UID, serial port, target, local absolute path, or provider secret.

Provider auth is an external local CLI prerequisite. If `codex-cli` or
`claude-cli` is not installed/authenticated, that is a real deployment blocker
for this suite, not a code defect to mask.

## Verification plan

Run cheapest-first:

1. Confirm clean branch state and provider CLI availability.
2. Run `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`.
3. Discover attached boards and run board substrate checks:
   - `uv run python host_bootstrap.py --board-id nucleo_l476rg --install-packs`
   - `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg`
   - `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
   - equivalent Nordic commands for `nrf52833dk` if attached, otherwise
     `nrf52840dk` as retained alternate proof.
4. For each provider and board, run a healthy freeform task through
   `pyocd-debug-brain run` using `--task-file`.
5. For at least one provider/board path, run a Branch B public client-action
   smoke with `--client-action uart_write=tests/fixtures/client_actions/uart_write.py`.
6. For each provider and board, run at least:
   - `<board>__b001_wrong_boot_text`
   - `<board>__b002_wrong_known_value`
   using `uv run pyocd-debug-brain benchmark --provider <provider> --case-id <case>`.
7. If the above matrix is green and time permits, run aggregate suite commands:
   - `uv run pyocd-debug-brain benchmark --provider codex-cli --suite pilot_v1_plus_b003_b004`
   - `uv run pyocd-debug-brain benchmark --provider claude-cli --suite pilot_v1_plus_b003_b004`
   for official pair closure, or the retained Nordic suite when only
   `nrf52840dk` is attached.
8. Inspect representative run artifacts for provider session records, memory
   ledger/event records, client-action audit records, and final verification.

## Acceptance criteria

- The branch remains clean except for intentional docs/fixes.
- Stale `markdowns/curr/` docs are archived and the current index is accurate.
- Non-hardware suite ladder passes.
- Both attached boards pass substrate checks.
- Both providers run real freeform hardware tasks on both attached boards.
- Both providers complete multiple code-writing benchmark tasks per board, with
  `full_success` outcomes and runner-owned flash/UART/symbol/green-check
  verification.
- At least one public client-action deployment task records audited
  `client_actions.json` and governed `run_script` use.
- No test evidence depends on silent provider-session replacement after a resume
  failure.
- If `nrf52833dk` is attached and all scoped-pair rows pass for both providers,
  the current `R12` official-pair provider proof can be marked closed in docs.
- If only `nrf52840dk` is attached for Nordic, the suite can be green for the
  attached boards but official `nrf52833dk` closure remains pending.

## Verified

- Spec reconciled against `README.md`, `ROADMAP.md`, `current-progress.md`,
  the build plan `R12` sections, and the current `pyocd-debug-brain` CLI and
  benchmark code.

## Pending verification

- All commands in the verification plan.
- Exact attached-board identity for this session.
- Real `codex-cli` and `claude-cli` availability/authentication.
