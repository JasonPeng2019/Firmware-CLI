# Process ledger for r12-provider-native-ux-cli-controls

## Goal and roadmap anchor

Task: Close the public `pyocd-debug` UX CLI control gap for provider-native skill
mode/root flags, while preserving the existing provider-native bridge behavior.
Roadmap anchor: R12 Stage 5 Wave 1 provider-native skill bridge; Prototype
Priority item 14.

## Done

- Audited active current specs against code and found one real implemented-spec
  gap: `pyocd-debug-brain` exposes provider-native controls, but public
  `pyocd-debug run/benchmark` does not.
- Reproduced the public parser failure: `pyocd-debug` rejects
  `--provider-native-skills require --provider-native-skill-root
  skills/provider_native` with argparse exit `2`.
- Wrote the narrow gap spec:
  `markdowns/curr/r12-provider-native-ux-cli-controls_spec.md`.
- Patched `src/pyocd_debug_mcp/ux/cli.py`,
  `src/pyocd_debug_mcp/ux/shell.py`, and
  `src/pyocd_debug_mcp/brain/loop.py`.
- Added focused regression coverage in `tests/test_ux_cli.py` and
  `tests/test_r12_turnkey.py`.
- Ran focused tests, Python-change, and the non-hardware suite ladder.
- Synced this ledger and the spec status after validation.

## Spec-to-code audit map

- `r12_turnkey_spec.md`: governed board/client action boundary and turnkey run
  artifacts map to `brain/actions.py`, `brain/action_policy.py`,
  `brain/loop.py`, `brain/app.py`, `brain/cli.py`, and `tests/test_p0_foundation.py`,
  `tests/test_r12_turnkey.py`, `tests/test_r12_turnkey_merge.py`. Audit found
  no remaining action-boundary gap in the implemented Wave 1 surface.
- `r12-context-scaffold-hardening_spec.md`: model-native skill scaffold,
  runtime-copy recovery, loaded-detail guardrails, and invalid-call details map
  to `brain/model_native_skills.py`, `brain/skills.py`, `brain/tool_schemas.py`,
  `brain/state.py`, `brain/loop.py`, and `tests/test_model_native_skills.py`,
  `tests/test_r12_turnkey.py`. Audit found no remaining scaffold gap.
- `r12-delta-compact-indexes_spec.md`: compact skill/governed-tool indexes in
  ordinary remote-delta turns map to `brain/provider_types.py`,
  `brain/loop.py`, provider adapters, and `tests/test_r12_turnkey.py`,
  `tests/test_r12_turnkey_merge.py`. Audit found no remaining delta-index gap.
- `r12-prompt-memory-cost-hardening_spec.md` and
  `r12-tier2-memory-bridge_spec.md`: bounded Tier 0/Tier 1/Tier 2/Tier 3 memory,
  prompt accounting, model-summary fallback, and UX controls map to
  `brain/provider_types.py`, `brain/loop.py`, `brain/config.py`, `brain/app.py`,
  `brain/cli.py`, `benchmark.py`, `ux/cli.py`, `ux/shell.py`, provider
  adapters, and `tests/test_r12_turnkey.py`, `tests/test_ux_cli.py`. Audit
  found no remaining Tier 2/Tier 3 implementation gap.
- `r12-provider-native-skill-bridge_spec.md` and
  `r12-provider-native-skill-invocation-proof_spec.md`: native skill projection,
  provider allowlists, fallback behavior, proof harness, and prompt accounting
  map to `brain/provider_native_skills.py`, `brain/provider_codex_cli.py`,
  `brain/provider_claude_cli.py`, `brain/provider_types.py`, `brain/loop.py`,
  `brain/config.py`, `skills/provider_native/`,
  `tests/test_provider_native_skills.py`, `tests/test_r12_turnkey.py`, and
  `tests/harness/provider_native_skill_usage.py`. Audit found one real product
  gap: the public UX CLI did not expose/replay the provider-native mode/root
  controls even though headless brain paths and docs did.
- `wave2-codebase-map_spec.md`: intentionally future Wave 2 scope. Its lack of
  implementation is not a Wave 1 spec gap.

## Limitations and known gaps

- This is a software/control-surface fix. No hardware validation is required.
- Live provider/native skill invocation behavior is already covered by the
  provider-native bridge specs; this process validates the public UX plumbing.

## Hardware hand-off

- None required.

## Open decisions and surfaced issues

- Interactive slash commands for provider-native mode/root are out of scope for
  this narrow gap. CLI flags and env vars cover the public control surface.

## Verified

- Pre-fix parser repro completed.
- Focused UX tests:
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
  -> shows both provider-native public flags.

## Pending verification

- None for this gap.
