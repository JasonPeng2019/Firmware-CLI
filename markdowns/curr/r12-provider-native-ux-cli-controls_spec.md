> STATUS: IMPLEMENTED - narrow R12 provider-native public UX CLI gap closed and
> validated by focused tests, Python-change, and the non-hardware suite ladder.

# R12 Provider-Native UX CLI Controls Spec

## Goal in plain English

Close the gap between the implemented provider-native skill bridge and the
operator-facing `pyocd-debug` CLI. The headless `pyocd-debug-brain` CLI already
exposes `--provider-native-skills` and `--provider-native-skill-root`; the public
UX entrypoint must expose the same controls for `run` and `benchmark`, pass them
to the shared brain helpers, and preserve them for reruns.

Roadmap anchor: R12 Stage 5 Wave 1 provider-native skill bridge and Prototype
Priority item 14 in `markdowns/things-to-change.md`.

## Scope and non-scope

In scope:

- Add `--provider-native-skills off|auto|require` to `pyocd-debug run` and
  `pyocd-debug benchmark`.
- Add `--provider-native-skill-root PATH` to `pyocd-debug run` and
  `pyocd-debug benchmark`.
- Pass both values through `src/pyocd_debug_mcp/ux/cli.py` into the shared
  `run_freeform_task`, `run_benchmark_case`, and `run_benchmark_suite` helpers.
- Persist provider-native mode/root in `turnkey_request.json` as explicit
  request fields, not only as a nested projection record.
- Teach `pyocd-debug rerun` and the interactive shell rerun path to replay those
  explicit fields when present.
- Add focused regression tests for parser support, run/benchmark plumbing, and
  rerun plumbing.

Out of scope:

- Changing provider-native projection semantics.
- Changing native skill package layout, prompt text, or provider allowlisting.
- Adding new hardware validation. This is an operator CLI/control-surface fix.
- Adding interactive slash commands for provider-native controls. The CLI/env
  surfaces are sufficient for this gap.

## Reconciliation summary

- Build plan and hard bar: provider-native skill projection is part of Wave 1
  and must be configurable with conservative `auto`, `off`, and `require`
  modes.
- Current code: `pyocd-debug-brain` and the module benchmark parser expose the
  provider-native flags and pass them into the brain. The shared app/config layer
  supports the fields. `pyocd-debug` UX CLI does not expose or pass those flags.
- Current docs: `README.md` documents provider-native controls in the turnkey
  provider rules without limiting them to the headless CLI, so the public
  operator entrypoint should support them.
- Disagreement: the provider-native implementation is complete in the brain
  path, but incomplete at the public UX CLI surface. This spec treats that as a
  product gap, not a change to the underlying provider-native feature.

## Design

`src/pyocd_debug_mcp/ux/cli.py` should mirror the existing headless CLI flags for
provider-native skills on both `run` and `benchmark`. The parsed values should
flow directly into the existing shared helpers.

`src/pyocd_debug_mcp/brain/loop.py` should add explicit request fields:

- `provider_native_skill_mode`
- `provider_native_skill_root`

The existing nested `provider_native_skills` projection record remains for
status, hashes, paths, and prompt accounting.

`src/pyocd_debug_mcp/ux/shell.py` rerun should read the explicit request fields
and pass them back into `run_freeform_task` or `run_benchmark_case`. If an older
request lacks those fields, rerun should keep existing resolver behavior.

## Board-facts-as-data and origin tags

- This feature introduces no board facts.
- Provider-native skill mode is `PROJECT-DEFINED` CLI/product policy.
- Provider-native skill root is operator/project configuration and must be
  resolved through existing pathlib/config code.
- No board-id-specific behavior is allowed.

## Documentation plan

- Update this spec and process ledger with implementation and validation status.
- No build-plan change is required because this is a public-entrypoint gap in an
  already-accepted Wave 1 bridge.
- README already documents the controls; no README wording change is required
  unless the final implementation changes the flag names.

## Portability

- Use existing argparse/path plumbing; do not introduce shell-specific parsing.
- Rerun should handle string paths from JSON artifacts and should not require the
  path to exist until the shared config resolver validates it.
- No absolute repo paths should be hardcoded.

## Verification plan

- Reproduce the missing parser behavior before the fix.
- Add focused tests in `tests/test_ux_cli.py` proving:
  - `pyocd-debug run` parses both provider-native flags.
  - `pyocd-debug benchmark` parses both provider-native flags.
  - `_render_run` passes both values to `run_freeform_task`.
  - `_render_benchmark` passes both values to `run_benchmark_case` or suite.
  - shell rerun replays explicit provider-native mode/root request fields.
- Run focused UX tests.
- Run the Python-change gate.
- Run the non-hardware suite ladder if the Python-change gate is green.

## Acceptance criteria

- Public `pyocd-debug run` accepts provider-native mode and root flags.
- Public `pyocd-debug benchmark` accepts provider-native mode and root flags.
- Those flags reach the shared brain helper calls unchanged.
- Saved turnkey requests contain explicit provider-native mode/root fields.
- Rerun preserves those fields when they are present.
- Existing env/default behavior remains unchanged when flags are omitted.
- No hardware behavior changes.

## Verified

- Pre-fix repro:
  `pyocd-debug` parser rejects `--provider-native-skills require` and
  `--provider-native-skill-root skills/provider_native` with argparse exit `2`.
- Implementation added public `pyocd-debug run` and `pyocd-debug benchmark`
  parser flags in `src/pyocd_debug_mcp/ux/cli.py`, passes them into
  `run_freeform_task`, `run_benchmark_case`, and `run_benchmark_suite`, records
  explicit request fields in `src/pyocd_debug_mcp/brain/loop.py`, and replays
  them from `src/pyocd_debug_mcp/ux/shell.py`.
- Focused tests:
  `uv run pytest -q tests/test_ux_cli.py -k "provider_native_skill_controls or rerun_replays_provider_native"`
  -> `5 passed`.
- Focused brain payload test:
  `uv run pytest -q tests/test_r12_turnkey.py -k "projects_provider_native_skills_into_runtime"`
  -> `1 passed`.
- Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`
  -> Ruff check/format, Pyright `0`, full pytest `386 passed`.
- FirmCLI non-hardware suite ladder:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> full pytest `386 passed`, Ruff, mypy, R11 benchmark tests `34 passed`,
  and R11 harness help all passed.
- Direct public CLI help smoke:
  `uv run pyocd-debug run --help | Select-String -Pattern "provider-native"`
  -> shows `--provider-native-skills {off,auto,require}` and
  `--provider-native-skill-root PROVIDER_NATIVE_SKILL_ROOT`.

## Pending verification

- None for this software/control-surface gap.
