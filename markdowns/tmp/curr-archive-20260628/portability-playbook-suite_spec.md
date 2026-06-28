> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# portability playbook suite

## Goal in plain English

Task: Validate the post-bootstrap portability contract, the portability
playbook update, and the current repo/runtime surface on the two attached
boards.
Roadmap anchor: `R0`, `R2-R7`, `R9-R12`, and the deferred portability-proof
boundary called out in `ROADMAP.md` and `current-progress.md`.

## Scope and non-scope

In scope:

- the portability playbook rewrite
- full non-hardware suite validation
- live validation on the attached Windows pair:
  - `nucleo_l476rg`
  - `nrf52840dk`
- bootstrap, Stage 0, Stage 1, stdio MCP runtime, and turnkey healthy-run
  proof on that attached pair

Out of scope:

- macOS proof
- fresh-machine proof on a second Windows or macOS host
- replacing the public scoped Nordic claim with `nrf52840dk`
- silent automation of proprietary OS drivers or vendor probe packages

## Reconciliation summary

- Build plan:
  - portability is compatible with a short documented bootstrap
  - post-bootstrap runtime behavior should be repo-owned and portable
- Current code:
  - setup helpers and host/bootstrap tooling already implement the narrower
    contract better than the old playbook text did
  - the portability playbook was the remaining wording outlier and is now
    aligned
- Other docs or notes:
  - `README.md`, `init.md`, `stage0_setup.md`, and `current-progress.md`
    already describe the narrower post-bootstrap contract
- Disagreements:
  - no remaining code-side contract disagreement after the playbook rewrite

## Design

The suite proves three layers:

1. the contract text is internally consistent
2. the repo remains green on the agent-runnable ladder
3. the attached hardware pair remains green through the core bootstrap and
   runtime chain

## Board-facts-as-data and origin tags

- supported-board identity remains data in `boards/<board>.yaml`
- machine-local attachment remains runtime discovery
- the public support matrix remains `PROJECT-DEFINED`
- the attached-board rerun is proof evidence, not an automatic support-matrix
  expansion

## Documentation plan

- update `superpowers/agent_portability_playbook.md`
- sync the portability workflow docs in `markdowns/curr/`
- report the live suite outcome honestly, including the remaining scoped-pair
  and macOS proof gaps

## Portability

For this suite, portability means:

- no machine-specific hardcoding
- clear bootstrap boundary
- repo-owned behavior after bootstrap
- deterministic failure or success on the attached supported runtime surface

It does not mean:

- zero-bootstrap first-run magic
- arbitrary-board support
- silent vendor-driver redistribution or guaranteed unattended install

## Verification plan

- non-hardware ladder:
  - `python .codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py --preset suite`
- live hardware ladder:
  - `host_bootstrap.py` on both attached boards
  - `stage0_check.py` on both attached boards
  - `tests.harness.stage1_smoke` on both attached boards
  - live stdio MCP smoke on both attached boards
  - live `pyocd-debug-brain run --provider codex-cli ...` healthy proof on
    both attached boards

## Acceptance criteria

- the portability playbook matches the narrower post-bootstrap contract
- the non-hardware suite ladder is fully green
- the attached Windows pair is green through bootstrap, Stage 0, Stage 1, stdio
  MCP runtime, and turnkey healthy verification
- remaining proof gaps are stated as proof gaps, not hidden as if already
  closed

## Verified

- portability playbook rewritten and aligned
- full suite ladder passed
- attached `nucleo_l476rg + nrf52840dk` Windows pair passed the planned live
  validation chain

## Pending verification

- official scoped-pair rerun on `nrf52833dk + nucleo_l476rg` if exact public
  claim closure is required now
- macOS proof
- fresh-machine proof on another host
