# Process ledger for r12-provider-native-skill-bridge

Status: IMPLEMENTED AND ATTACHED-BOARD VALIDATED for the current connected pair.

## Goal and roadmap anchor

Task: Implement provider-native skill bridge using Codex and Claude native skill behavior.

Roadmap anchor: R12 Stage 5 turnkey brain, Wave 1 provider-native host work,
scaffold hardening, prompt/memory cost hardening, and Wave 2 Module G static
context efficiency substrate.

## Done

- Read the governing spec and current provider/runtime code paths.
- Proved Phase 0 native skill access in the actual brain/provider architecture:
  - Codex CLI `0.142.2` can read runtime `.codex/skills` in `codex exec`.
  - Claude CLI `2.1.76` can read runtime `.claude/skills` in
    `claude --print --output-format json` when FirmCLI passes
    `--allowedTools Skill(<skill-id>)`.
- Added `src/pyocd_debug_mcp/brain/provider_native_skills.py`.
- Added provider-native capability fields and prompt accounting fields.
- Added runtime projection into `.codex/skills` and `.claude/skills`.
- Added `firmcli-native-skills.json` projection metadata with hashes.
- Added compact provider-native skill prompt index plus fallback
  `load_skills(skill_ids=[...])` guidance.
- Wired Claude CLI `--allowedTools Skill(...)` for projected native skills.
- Added env/config/CLI controls:
  - `PYOCD_TURNKEY_PROVIDER_NATIVE_SKILLS`
  - `PYOCD_TURNKEY_PROVIDER_NATIVE_SKILL_ROOT`
  - `--provider-native-skills off|auto|require`
  - `--provider-native-skill-root`
- Added product-owned skill packages:
  - `skills/provider_native/common/firmcli-firmware-debug`
  - `skills/model_native/firmcli-firmware-debug`
- Added focused tests in `tests/test_provider_native_skills.py`.
- Updated `tests/test_r12_turnkey.py` for config, prompt accounting, CLI
  parsing/threading, Claude allowlist, and loop projection behavior.
- Added projection overwrite protection: FirmCLI refuses to replace an existing
  `.codex/skills/<skill>` or `.claude/skills/<skill>` directory unless it
  carries FirmCLI's generated projection marker.
- Focused test result before the final adversarial patch:
  `uv run pytest tests/test_provider_native_skills.py tests/test_r12_turnkey.py -q`
  -> `78 passed`.
- Python-change gate result before the final adversarial patch:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py --continue-on-error`
  -> Ruff check/fix pass, Ruff format pass, Pyright `0` diagnostics, full
  pytest `372 passed`.
- FirmCLI suite ladder result before the final adversarial patch:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> full pytest `372 passed`, Ruff pass, mypy pass, R11 benchmark pytest
  `34 passed`, R11 benchmark help pass.
- Full Wave 1 attached-board validation later passed with native projection on
  the currently attached `nucleo_l476rg + nrf52840dk` boards:
  - Branch C harness: Codex and Claude CLI on both boards, `9 passed` per row.
  - Code-writing repair benchmarks with `--provider-native-skills require`:
    `nucleo_l476rg__b001_wrong_boot_text` and
    `nrf52840dk__b001_wrong_boot_text` reached `FULL_SUCCESS` score `100` with
    both `codex-cli` and `claude-cli`.
  - Focused credentials-free OpenAI/Anthropic API-path simulation passed
    through the real provider factory/turnkey-loop paths.
- Process audits after provider/hardware checks found no new leaked validation
  children beyond pre-existing user-owned Codex/Claude app processes and
  pre-existing app-owned MCP workers.
- After the projection overwrite-protection patch, the Python-change gate,
  suite ladder, focused API simulation, Branch C four-row provider/hardware
  matrix, and four representative code-writing repair benchmarks were rerun to
  green. The final code-writing run roots were
  `20260701T083254Z-987cf201`, `20260701T083805Z-ad7caba6`,
  `20260701T084025Z-552f6748`, and `20260701T084536Z-120d39a4`.

## In progress

- None.

## TODO

- Re-run the same native-projection hardware ladder on the exact official
  `nrf52833dk + nucleo_l476rg` pair when the `nrf52833dk` is attached.
- Re-run live API-provider validation when API credentials/credits are
  available.

## Limitations and known gaps

- This pass records static Phase 0 probe evidence in provider capabilities. It
  does not yet re-run live burner probes per provider binary/version at the
  start of each hardware run.
- API providers are intentionally fallback-only for this feature and must use
  deterministic FirmCLI `load_skills`; live API calls still require
  credentials/credits.
- Claude `/loop`, Codex `/goal`, subagents, and future native workflow features
  remain unproven for hardware-attached FirmCLI runs.
- Native skill projection is a host-work accelerator only. It does not and must
  not bypass FirmCLI governed board actions or loaded-detail guardrails.
- The full attached-board/provider-heavy product suite has been run on the
  attached `nucleo_l476rg + nrf52840dk` pair, not on the exact official
  `nrf52833dk + nucleo_l476rg` pair.

## Hardware hand-off

- Pending after attached-board validation:
  - repeat on the exact official `nrf52833dk + nucleo_l476rg` pair;
  - run live OpenAI/Anthropic API provider rows when credentials/credits are
    available;
  - compare at least one fallback-only `--provider-native-skills off` run for
    equivalent behavior when native projection is unavailable if that comparison
    is promoted into the release gate.

## Open decisions and surfaced issues

- Selected Codex runtime layout is `.codex/skills`. `.agents/skills` worked in
  local probes but is not selected for product behavior.
- Claude native skills require `--allowedTools Skill(<skill-id>)` in the current
  noninteractive CLI path.
- `--json-schema` with Claude hung during probe and remains rejected.
- Exact official Nordic closure is blocked on which physical board is attached,
  not on code known to fail.

## Verified

- Phase 0 proof recorded in
  `markdowns/curr/r12-provider-native-skill-bridge_probe_notes.md`.
- Focused projection/config/prompt tests are green.
- Python-change gate and FirmCLI suite ladder are green after the final
  adversarial patch.
- Attached-board projected-skill hardware repair proof is green on the connected
  `nucleo_l476rg + nrf52840dk` boards with both CLI providers.
- Projection overwrite protection is covered by focused regression tests and
  the provider-native hardware repair rows still pass after the patch.

## Pending verification

- Exact official `nrf52833dk` proof remains pending unless the board is attached
  for the run.
- Live API-provider proof remains pending until API credentials/credits are
  available.
