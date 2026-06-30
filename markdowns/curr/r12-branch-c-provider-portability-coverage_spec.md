> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# R12 Branch C Provider And Portability Coverage Spec

## Goal in plain English

Close the gap between the current Branch C harness, which is still Codex-shaped,
and the intended portable R12 product, which must work through the same brain
contract across supported providers and supported developer host OSes.

This spec extends the provider and portability acceptance criteria for
`P-Wave-C`. It does not replace the narrower Branch C event/timeout completion
spec; it adds the missing deployment-shaped coverage needed before Branch C can
support a deployable product claim.

Roadmap anchor: `R12` / Stage 5 product #2 prototype, Wave 1 Branch C. Broader
product gate: `G7`.

## Scope and non-scope

In scope:

- Make the Branch C harness provider-neutral instead of Codex-only.
- Cover at least the two local CLI providers in real non-hardware provider
  checks:
  - `codex-cli`
  - `claude-cli`
- Keep API providers covered by config/schema/unit tests when API keys are not
  supplied. Live API proof is optional unless keys/models are explicitly
  available for the run.
- Exercise the real provider wrapper path wherever possible, not only private
  Codex helper functions.
- Add acceptance semantics that distinguish:
  - provider executable missing;
  - provider authentication failure;
  - provider parse/schema failure;
  - Branch C prompt missing effective timeout state;
  - hardware skipped.
- Ensure selected provider skips are not accepted as green in acceptance mode.
- Define Windows and macOS validation commands and keep implementation
  OS-neutral.
- Keep board selection portable: board config, discovery, optional `--port`,
  no hardcoded probe UID, serial port, or machine-local path.

Out of scope:

- Branch A persistent provider-session implementation.
- Branch B batches, `wait`, UART write, and client actions.
- Branch D progress rendering and inspector UI.
- Branch E checkpoints.
- Branch F scoped green approval.
- Provider-native tool-call conversion.
- Live API-provider proof when API keys/models are unavailable.
- Claiming macOS or fresh-host proof from a Windows-only run.

## Reconciliation summary

- Build plan: the R12 brain supports four provider backends
  (`openai-api`, `anthropic-api`, `codex-cli`, `claude-cli`) and the provider
  layer is isolated from the orchestration loop. The team environment is
  Windows + macOS from day one, so cross-platform development is not optional.
- R12 turnkey spec: every provider must return the same structured next-action
  shape. CLI providers use existing local auth; API providers use BYOK keys.
- Things-to-change: provider-call timeouts and provider behavior apply to both
  Codex and Claude CLI providers, not only Codex.
- Current code: `brain/config.py` recognizes all four provider kinds, and
  `provider_claude_cli.py` exists, but `tests/harness/branch_c_tests.py` imports
  Codex-specific private helpers and exposes `--skip-codex`.
- Current docs: `branch_c_test_plan.md` and the first Branch C completion spec
  focus on Codex dry-run and Codex live hardware proof. That is insufficient
  for the intended multi-provider product claim.

Conflicts and ambiguities:

- CONFLICT: the prior Branch C completion acceptance allowed a green
  non-hardware result with Codex-only provider coverage. The product docs imply
  provider-facing Branch C behavior must not be Codex-only. Resolve by treating
  Codex-only proof as partial and requiring this follow-on provider matrix for
  deployable Branch C closure.
- AMBIGUITY: whether local Branch C completion requires all four providers live.
  Proposed resolution: require `codex-cli` and `claude-cli` for local CLI
  provider proof; require API provider config/schema/unit coverage by default;
  run live API proof only when keys/models are supplied.
- AMBIGUITY: a single Windows host cannot prove macOS portability. Proposed
  resolution: implementation must stay OS-neutral and the spec must provide
  exact macOS commands, but current status remains pending until run on macOS.

## Design

Replace Codex-specific harness concepts with provider-neutral ones.

The harness should accept repeatable provider selection:

```bash
--provider codex-cli --provider claude-cli
```

Legacy `--skip-codex` may remain as a compatibility alias during migration, but
the target interface should be `--skip-providers` or provider selection that
omits provider checks.

Provider checks should be renamed from Codex-specific names to provider-matrix
names:

- `provider_dry_run_prompt_render`
- `provider_live_run_events_and_clamp`

Each result should include the provider name in the detail or result key. A
Codex pass must not mask a Claude failure.

Preferred implementation shape:

- Build the same Branch C prompt through the brain's real prompt construction
  path.
- Instantiate providers through the same provider factory/config path used by
  `pyocd-debug-brain`, or through a small provider-neutral test adapter if the
  production factory cannot be used directly.
- Avoid importing provider-private helpers such as Codex-only command builders
  unless no public seam exists. If a public test seam is missing, add a narrow
  one in the provider layer rather than duplicating prompt/command logic in the
  harness.
- Keep the dry-run prompt task non-hardware: the provider should return a
  schema-valid final/action decision without touching the board.
- Keep the live check hardware-shaped: `run_freeform_task(...)` or
  `pyocd-debug-brain run` with the selected provider connects, reads board
  info, emits Branch C events, and records clamped effective timeouts.

Acceptance-mode result semantics:

- `PASS`: the selected provider/check ran and proved the intended behavior.
- `FAIL`: product behavior failed, provider output failed schema, prompt omitted
  Branch C state, or required hardware/provider proof was selected but invalid.
- `SKIP`: allowed only in development mode. With `--fail-on-skip`, any selected
  skip makes the run incomplete.

When `--skip-hardware` is used, hardware checks should not be selected at all.
They should not create a skip row that makes non-hardware provider acceptance
look incomplete. When a hardware check is selected and hardware is unavailable,
that is a skip in development mode and a failure/incomplete acceptance result
with `--fail-on-skip`.

## Board-facts-as-data and origin tags

This spec adds no board facts. Provider names are product-defined enum values.

- Provider enum values are `PROJECT-DEFINED`.
- Board IDs and port/probe identities remain data from board config, discovery,
  or explicit CLI override.
- Do not add `if board_id == ...` provider behavior.
- Do not add committed machine-local paths or port names.

## Documentation plan

- Update `markdowns/curr/branch_c_test_plan.md` to describe provider-neutral
  checks once implemented.
- Update `markdowns/current-progress.md` with exact provider/OS matrix results.
- Update `markdowns/R12_P_SPLIT.md` only for Branch C status, not to move
  ownership into another branch.
- If provider wrapper behavior changes, update provider docstrings or operator
  docs where the reader actually sees them.

## Portability

Implementation must be portable within the repo's post-bootstrap Windows/macOS
contract:

- Use `pathlib` and list-style subprocess commands.
- Avoid shell-specific quoting in product code and tests.
- Decode subprocess output with UTF-8 plus replacement or an equivalent robust
  path.
- Detect provider executables with `shutil.which`.
- Treat missing provider executable/auth as an environment precondition in
  development mode and an incomplete selected proof in acceptance mode.
- Provide both Windows and macOS commands in docs; do not claim macOS proof
  until run on macOS.

## Verification plan

Non-hardware provider matrix:

```bash
uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --skip-hardware --provider codex-cli --provider claude-cli --fail-on-skip
```

Hardware provider matrix when boards are available:

```bash
uv run python tests/harness/branch_c_tests.py --board-id nrf52833dk --provider codex-cli --provider claude-cli --fail-on-skip
uv run python tests/harness/branch_c_tests.py --board-id nucleo_l476rg --provider codex-cli --provider claude-cli --fail-on-skip
```

Direct deployment smoke for each official board and selected CLI provider:

```bash
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --timeout-proposal-json '{"connect_seconds":99999,"flash_seconds":1}' --iteration-estimate-json '{"requested_max_iterations":999}' --max-iters 4 --task "Connect to the board by board_id, read board info, and finalize without flashing or editing files."
uv run pyocd-debug-brain run --provider claude-cli --board-id nrf52833dk --timeout-proposal-json '{"connect_seconds":99999,"flash_seconds":1}' --iteration-estimate-json '{"requested_max_iterations":999}' --max-iters 4 --task "Connect to the board by board_id, read board info, and finalize without flashing or editing files."
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --timeout-proposal-json '{"connect_seconds":99999,"flash_seconds":1}' --iteration-estimate-json '{"requested_max_iterations":999}' --max-iters 4 --task "Connect to the board by board_id, read board info, and finalize without flashing or editing files."
uv run pyocd-debug-brain run --provider claude-cli --board-id nucleo_l476rg --timeout-proposal-json '{"connect_seconds":99999,"flash_seconds":1}' --iteration-estimate-json '{"requested_max_iterations":999}' --max-iters 4 --task "Connect to the board by board_id, read board info, and finalize without flashing or editing files."
```

MacOS portability proof repeats the non-hardware provider matrix on a supported
macOS host after the documented bootstrap. If the host lacks one provider CLI,
record that provider as pending rather than green.

## Acceptance criteria

- The Branch C harness no longer has Codex-only check names as the generic
  provider surface.
- Both `codex-cli` and `claude-cli` can run selected non-hardware Branch C
  provider checks through real CLI providers when installed/authenticated.
- Provider failures are attributed per provider; one provider pass cannot hide
  another provider failure.
- Selected provider skips fail acceptance with `--fail-on-skip`.
- Hardware checks are not selected during `--skip-hardware` non-hardware
  acceptance, so intentional hardware omission does not pollute provider proof.
- Docs and current progress record the exact provider and OS matrix.
- No hardcoded board, probe, port, path, or OS-specific shell dependency is
  introduced.

## Verified

- This proposal was restored after the accidental cleanup in this checkout.
- Implemented provider-neutral Branch C harness selection:
  `--provider`, `--provider-model`, `--provider-timeout-seconds`, and
  `--skip-providers`.
- Retained `--skip-codex` only as a deprecated compatibility alias.
- Replaced Codex-specific acceptance rows with
  `provider_dry_run_prompt_render[provider]` and
  `provider_live_run_events_and_clamp[provider]`.
- Fixed non-hardware acceptance semantics so `--skip-hardware` does not select
  live hardware provider rows and therefore does not create artificial SKIPs.
- Targeted validation after implementation passed:
  `uv run pytest -q tests/test_branch_c_harness.py tests/test_timeout_policy.py`
  returned `13 passed`, and targeted ruff passed.
- Full non-hardware ladder passed on June 29, 2026:
  `uv run pytest -q` returned `289 passed`, `uv run ruff check .` passed, and
  `uv run mypy src` passed.
- Non-hardware provider matrix passed for both attached board configs with
  `codex-cli` and `claude-cli` selected:
  - `nucleo_l476rg`: `6 passed, 0 failed, 0 skipped`
  - `nrf52840dk`: `6 passed, 0 failed, 0 skipped`
- Full hardware/provider Branch C matrix passed:
  - `nucleo_l476rg`: `11 passed, 0 failed, 0 skipped`
  - retained `nrf52840dk`: `11 passed, 0 failed, 0 skipped`
- Public deployed CLI smoke passed for both providers on both attached boards:
  - `codex-cli` + `nucleo_l476rg`: `runs/20260630T011733Z-ae2eb3ee`
  - `claude-cli` + `nucleo_l476rg`: `runs/20260630T011814Z-4c33bc87`
  - `codex-cli` + `nrf52840dk`: `runs/20260630T011858Z-f269f813`
  - `claude-cli` + `nrf52840dk`: `runs/20260630T011944Z-7b9c4186`

## Pending verification

- Official `nrf52833dk` hardware proof remains pending because the attached
  Nordic board reports nRF52840 silicon; this pass proves retained
  `nrf52840dk`.
- macOS/fresh-host proof remains pending; this pass proves the current Windows
  host only.
