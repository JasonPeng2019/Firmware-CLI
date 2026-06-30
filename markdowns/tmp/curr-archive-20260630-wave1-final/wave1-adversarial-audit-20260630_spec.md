> STATUS: ACTIVE HARD BAR - adversarial verification pass for the current
> Branch B/Wave 1 prototype. Do not claim full product closure past the explicit
> Claude quota and exact-board proof gaps.

# wave1 adversarial audit 20260630

## Goal in plain English

Task: Adversarial audit and validation pass for Wave 1 A/B/C plus Branch B
model-native skills and compact tool index.
Roadmap anchor: R12 Wave 1 A/B/C.

## Scope and non-scope

In scope:

- Audit the current Branch B hard-bar implementation:
  - old governed host actions are structurally absent;
  - `load_skills` resolves dependencies, runs init scripts safely, exposes
    usable folders, and injects context;
  - compact MCP tool index replaces repeated full tool schema bodies.
- Audit Wave 1 A/B/C consistency against `README.md`, `R12_P_SPLIT.md`,
  `current-progress.md`, `things-to-change.md`, and `curr/r12_turnkey_spec.md`.
- Fix only criticisms that have concrete code, test, or product merit.
- Run focused regression tests, full Python-change validation, suite preset, and
  Codex no-hardware smoke checks available from this host.
- Leave a Claude/hardware handoff for quota reset and exact official-board proof.

Out of scope:

- Claiming Claude CLI success while Claude usage is exhausted.
- Claiming exact `nrf52833dk` proof from an attached `nrf52840dk` substitute.
- Reintroducing generic host execution into the brain or MCP server.
- Broad Wave 2 feature work unrelated to the audited Branch B/Wave 1 surface.

## Reconciliation summary

- Build plan: Wave 1 A/B/C is a prototype merge-back candidate only after
  Branch A provider continuity, Branch B action-boundary behavior, and Branch C
  timeout/event behavior stay green on the available validation ladder.
- Current code: `read_file`, `replace_file`, and `run_build` are absent from
  `ActionUnion`; `load_skills` exists as context expansion; prompt tool metadata
  is compact.
- Other docs or notes: `things-to-change.md` entry #11 still carried older
  `run_build` governed wording before this audit; that is a valid doc drift and
  must be corrected.
- Disagreements: init scripts were documented as unable to touch board hardware,
  but the loader originally only bounded and recorded them. This is a valid
  product-boundary bug because model-native skill initialization is
  brain-mediated and must not bypass governed server tools.

## Design

- Add a deterministic preflight policy to model-native skill init scripts:
  - reject Python imports of known direct probe/serial stacks such as `pyocd`,
    `serial`, `usb`, `hid`, `pylink`, and `jlink`;
  - reject direct subprocess calls to known board/probe commands such as
    `pyocd`, `openocd`, `nrfjprog`, `probe-rs`, `st-flash`, and J-Link tools;
  - keep pure host init scripts legal;
  - run the preflight before any init subprocess starts.
- Require a manifest `skill_id` to match the requested skill folder. Runtime
  folders, dependency closure, state keys, and prompt context must not be
  spoofable by a mismatched manifest.
- Keep provider-native host work free. This audit does not sandbox Codex/Claude
  host tools; it only tightens brain-mediated skill init scripts.

## Board-facts-as-data and origin tags

- The new init-script denylist is PROJECT-DEFINED boundary policy, not a
  board-facts table.
- No board-specific constants or probe IDs are introduced.

## Documentation plan

- Update `things-to-change.md` entry #11/#12 to reflect the implemented Branch B
  hard bar.
- Record this audit in this spec, the process ledger, review/audit doc, current
  progress, and the next-Claude handoff.

## Portability

- The preflight uses Python AST parsing and path/name checks only.
- The command denylist normalizes `.exe` suffixes so Windows and POSIX command
  spellings are handled consistently.

## Verification plan

- Focused regression: `uv run pytest -q tests/test_model_native_skills.py`.
- Full Python gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py`.
- Suite preset:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`.
- Codex no-hardware smoke for `load_skills` and compact tool index after fixes.
- Claude no-hardware and live hardware reruns remain in the morning handoff
  because quota is exhausted.

## Acceptance criteria

- Init scripts that directly import known board/probe modules fail before
  execution with a clear error.
- Init scripts that directly invoke known board/probe commands fail before
  execution with a clear error.
- Pure host init scripts still run dependency-first and exactly once per loaded
  skill.
- Manifest skill IDs cannot disagree with the requested skill folder.
- Active docs no longer describe `run_build` or firmware source edits as
  governed `TurnDecision` host actions.
- All agent-verifiable checks listed above pass, or any skipped check is
  explicitly blocked by quota/hardware availability.

## Verified

- Reproducer before fix: `uv run pytest -q tests/test_model_native_skills.py`
  failed three new tests proving the gap.
- Post-fix focused regression: `uv run pytest -q tests/test_model_native_skills.py`
  -> `5 passed`.
- Full Python-change gate:
  `python .codex\skills\python-change\scripts\run_python_change_checks.py` ->
  Ruff pass, Pyright `0`, full pytest `350 passed`.
- Suite preset:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
  -> pass.
- Codex host-native workspace smoke passed at
  `runs/turnkey-20260630T090753Z-02dee333`; Codex edited the temp workspace
  file with provider-native host tools, returned `finalize`, and used no MCP
  tools.
- Codex `load_skills` no-hardware smoke passed at
  `runs/turnkey-20260630T090914Z-044ef516`.
- Codex compact tool-index no-hardware smoke passed at
  `runs/turnkey-20260630T090947Z-703de0e5`; prompt inspection found no
  `input_schema:` marker.
- Second adversarial pass found no further valid code/product criticisms within
  the Codex-verifiable scope.

## Pending verification

- Claude and exact-board handoff reruns after quota/hardware availability.
