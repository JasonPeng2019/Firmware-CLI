# R12 Provider-Native Skill Invocation Proof Spec

Status: ACCEPTED IMPLEMENTATION SPEC for closing the remaining Wave 1 native
skill evidence gap.

## Goal in plain English

Prove that Codex CLI and Claude CLI can actually consume a FirmCLI-owned
provider-native skill from the run-local native skill layout, not merely that
FirmCLI projected files into `.codex/skills` or `.claude/skills`.

This spec closes only the native-skill invocation evidence gap. It does not
attempt live OpenAI/Anthropic API proof, exact physical `nrf52833dk` proof, or
fresh-machine deployment proof.

## Scope

- Add a focused non-hardware live-provider smoke harness that:
  - creates a temporary client-owned provider-native skill root;
  - writes a provider-native proof skill with a secret token present only inside
    the skill body;
  - uses the existing FirmCLI projection code to copy that skill into the
    provider working directory;
  - calls the real Codex CLI or Claude CLI provider through the same
    provider-wrapper classes used by the turnkey brain;
  - requires the provider to use the projected native skill and return a valid
    FirmCLI `TurnDecision` containing the secret token.
- Run the smoke for both `codex-cli` and `claude-cli` when those CLIs are
  available and authenticated.
- Keep `load_skills` as fallback behavior in the product, but fail this proof
  smoke if the provider returns `load_skills` instead of the proof token.
- Persist a compact JSON report with provider, projection, allowed-tools,
  decision, and pass/fail evidence.
- Add unit coverage for the proof harness so the command remains stable.
- Update the final handoff with the exact proof command and result.

## Non-scope

- No live OpenAI/Anthropic API calls.
- No exact official `nrf52833dk` proof.
- No fresh-machine installation proof.
- No change to the runtime board-control policy.
- No provider-native skill execution of pyOCD, serial, flash, or other board
  actions.
- No claim that every historical hardware repair benchmark visibly invoked the
  native skill.

## Design

The harness should live under `tests/harness/` because it is a validation
surface, not production brain behavior.

The proof skill should be generated in a temporary source root. Its token must
not appear in the provider prompt or projection metadata. The prompt may name
the skill ID and the expected native invocation form, but the only place the
token appears is the projected `SKILL.md`.

The provider is asked to return a normal FirmCLI `TurnDecision`:

- `action.kind = "finalize"`
- `final_status = "diagnosed_only"`
- `classification = "healthy"`
- `root_cause` or `summary` contains the exact token

The harness fails if:

- projection is unavailable;
- Claude allowed-tools does not include `Skill(<skill-id>)`;
- the provider returns `load_skills`;
- the provider returns valid JSON without the token;
- the provider output cannot be parsed as a `TurnDecision`;
- the provider CLI fails or times out.

This is a live provider proof. It can still be skipped manually by not running
the harness, but when run it must be reported honestly as pass/fail.

## Files expected to change

- `tests/harness/provider_native_skill_usage.py`
- `tests/test_provider_native_skill_usage_harness.py`
- current status docs if the proof result changes a published claim
- archived handoff/process docs under
  `markdowns/tmp/curr-archive-20260701-current-adversarial-audit/` if later
  audits need to inspect the completed final-check instructions

## Verification plan

Focused non-provider tests:

```powershell
uv run pytest -q tests/test_provider_native_skill_usage_harness.py tests/test_provider_native_skills.py
```

Live provider invocation proof:

```powershell
uv run python tests\harness\provider_native_skill_usage.py --provider codex-cli --provider claude-cli --timeout-seconds 180
```

Suite gate after fixes:

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py --continue-on-error
python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\r12-provider-native-skill-invocation-proof-suite.txt
```

## Acceptance criteria

- The focused tests pass.
- The live provider invocation proof passes for both `codex-cli` and
  `claude-cli`.
- The provider proof report contains the projected skill ID, provider-native
  layout, Claude allowed-tools entry where applicable, the secret token, and a
  valid `TurnDecision` from the provider.
- The full local suite ladder is green after any code changes.
- The handoff tells the next Codex session that native skill invocation proof is
  available, with the command and report path.

## Verified

- Focused non-provider regression tests passed:
  `uv run pytest -q tests/test_provider_native_skill_usage_harness.py tests/test_provider_native_skills.py`
  -> `11 passed`.
- Focused Ruff check passed:
  `uv run ruff check tests/harness/provider_native_skill_usage.py tests/test_provider_native_skill_usage_harness.py`.
- Live Codex CLI native skill invocation proof passed:
  `runs/provider-native-skill-usage/codex-cli-provider-native-skill-usage.json`.
  The provider returned a valid `finalize` `TurnDecision`, `fallback_used=false`,
  and included latest proof token
  `FIRMCLI_NATIVE_SKILL_USAGE_CODEX_CLI_cb3d90b2`.
- Live Claude CLI native skill invocation proof passed:
  `runs/provider-native-skill-usage/claude-cli-provider-native-skill-usage.json`.
  The provider returned a valid `finalize` `TurnDecision`, `fallback_used=false`,
  included `Skill(firmcli-native-usage-proof)` in the allowlist, and included
  latest proof token `FIRMCLI_NATIVE_SKILL_USAGE_CLAUDE_CLI_d96026c2`.
- Python-change gate passed after the harness type-boundary fix:
  Ruff check/fix, Ruff format, Pyright `0`, and `378 passed` in the final
  double-check pass.
- FirmCLI suite ladder passed:
  `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite --report-path runs\r12-provider-native-skill-invocation-proof-suite.txt`.
