> STATUS: ACTIVE WORKING SPEC FOR THE FIRST `R12` SLICE. This is the tracked
> implementation contract for the current pass, not a claim that all of Stage 5
> is already complete.

# `R12` Turnkey Phase 1

## Goal in plain English

Task: Freeze and implement the first turnkey brain/CLI slice as an MCP client
with live Nordic proof
Roadmap anchor: `R12`

This phase starts the turnkey product honestly instead of trying to finish the
entire premium tier in one jump.

The output of this pass is:

- a repo-owned turnkey CLI that starts its own local MCP server process
- a real stdio MCP client implementation in product code
- a repo-owned skills data shape and initial board-agnostic task skills
- deterministic step budgets and simple self-evaluation inside the turnkey loop
- a first acceptance slice proven on attached Nordic hardware

This phase does **not** claim that the full premium bug-fixing brain is done.
It establishes the first working turnkey execution path on the already-proven
substrate.

## Scope and non-scope

In scope:

- create the first `src/pyocd_debug_mcp/brain/` package
- add a turnkey CLI entrypoint that is agent-runnable on Windows and macOS
- launch the current MCP server as a child stdio process from the turnkey CLI
- load skills from tracked repo data files under the repo-root `skills/` tree
- implement one deterministic turnkey run loop that calls MCP tools with
  explicit per-step time budgets
- support at least two initial skills:
  - reference runtime health check
  - Nordic recover -> reflash -> reverify cycle for boards that allow recover
- keep board identity/config/artifact facts data-driven through the existing
  board loader and reference-artifact resolver
- emit structured turnkey run summaries suitable for later acceptance analysis
- add unit coverage for the skill loader, run planner, and CLI wiring
- prove the implemented slice live on the attached `nrf52840dk`

Out of scope:

- a general LLM-driven repair loop
- code-editing or patch-application from the turnkey brain
- replacing the existing `R11` benchmark harness
- claiming full premium advantage over `R11` yet
- hosted deployment, remote transport, OAuth, or multi-board orchestration
- widening support claims beyond the existing repo/board/toolchain boundaries

## Reconciliation summary

- Build plan:
  - `R12` requires a turnkey brain implemented as an MCP client of the server,
    skill loading/selection, CLI frontage, and an acceptance benchmark.
  - The build plan explicitly separates deterministic server guardrails from
    softer brain-side orchestration.
  - The canonical repo layout expects a root `skills/` tree and a
    `src/pyocd_debug_mcp/brain/` package, neither of which exists yet.
- Current code:
  - the Stage 1 to `R11` substrate is real and green on the scoped pair
  - the current product code ends at the server/tools/shared-services layer
  - no turnkey client, CLI, or product-owned skills loader exists today
- Other docs or notes:
  - `current-progress.md` already says the next work is to freeze the `R12`
    contract, define the CLI/state/skills model, and implement the first real
    turnkey loop
  - `firmware_agent_mcp_architecture.md` says the CLI belongs to the turnkey
    brain, not to the server surface
- Disagreements:
  - the broad roadmap definition of `R12` is larger than one implementation
    pass; this spec narrows the current pass to a truthful phase-1 slice rather
    than pretending all of Stage 5 is landing at once

## Design

### 1. Product shape for this phase

Add a new turnkey package under `src/pyocd_debug_mcp/brain/` with four
responsibilities:

- spawn and manage the local stdio MCP server
- load and validate tracked skill descriptors
- execute one skill as a bounded step plan over the MCP tool surface
- summarize the result in a stable machine-readable form

The CLI is the human/operator frontage for this package.

### 2. CLI contract

Add a new script entrypoint:

```bash
uv run pyocd-turnkey --board-id nrf52840dk --skill-id reference-health-check
```

Initial required subcommands:

- `list-skills`
- `run`

Initial `run` flags:

- `--board-id`
- `--skill-id`
- `--json`
- `--server-command` and `--server-arg` as escape hatches

Config precedence:

1. explicit CLI flags
2. tracked board config + reference artifact defaults
3. environment inherited by the child server process

### 3. Skill contract

Skills live under the repo-root `skills/turnkey/`.

Each skill file is YAML and must define:

- `skill_id`
- `title`
- `supported_kinds`
  - `all`
  - `nordic_only`
- `steps`
  - MCP tool name
  - argument template
  - timeout seconds
  - expected text markers when applicable
- `final_assertions`

Initial skills for this phase:

- `reference-health-check`
  - connect
  - flash reference firmware
  - halt
  - inspect PC
  - resolve the tracked reference symbol locally, then verify its value through
    `read_memory`
  - resume
  - verify UART contains `boot ok`
  - disconnect
- `nordic-recover-cycle`
  - connect
  - recover with explicit confirmation
  - reflash reference firmware
  - verify UART
  - disconnect

The skill loader must reject malformed files loudly because later agent-facing
reliability depends on skill-data trustworthiness.

### 4. Brain state model

The first run state model is deterministic and small:

- run id
- board id
- skill id
- selected reference artifacts
- step results in order
- session id once the server reports it
- warnings
- final status

This phase's self-evaluation logic is intentionally simple:

- each step has a fixed timeout
- expected text mismatches fail the run clearly
- no hidden retries on mutating steps
- the run aborts on the first hard failure and returns a structured summary

This is enough to make the turnkey path trustworthy without yet pretending to
solve open-ended repair strategy.

### 5. Use of shared services

Board facts must continue to come from tracked board configs and canonical
reference-artifact discovery.

Local symbol resolution should reuse the existing shared symbol service rather
than invent a second symbol parser inside the brain package.

The brain may use local shared helpers for read-only artifact facts, but all
hardware-touching actions in this phase must still go through the MCP server so
the turnkey path exercises the real product boundary.

### 6. Phase-1 acceptance benchmark

This pass defines a narrow acceptance slice for product #2:

- unit/static validation of the new turnkey package
- CLI-level smoke validation on the local host
- live `reference-health-check` on attached `nrf52840dk`
- live `nordic-recover-cycle` on attached `nrf52840dk`

This is not yet the full premium-vs-BYO benchmark. It is the first proof that a
repo-owned turnkey client can drive the real server end to end on hardware.

## Board-facts-as-data and origin tags

- board identity, pyOCD target, UART defaults, and recover policy remain
  tracked facts from `boards/<board>.yaml`
- reference firmware locations remain derived through the existing reference
  artifact resolver
- skill selection is tracked repo data under `skills/turnkey/`
- machine-local environment facts remain local environment/runtime concerns, not
  tracked board config edits

Origin tags to preserve in code/docs:

- tracked board facts
- tracked skill facts
- runtime-discovered session/run facts
- local environment overrides

## Documentation plan

Update, in the same unit of work:

- `README.md`
  - add the turnkey CLI entrypoint and the new `skills/` tree
- `current-progress.md`
  - record what `R12` phase 1 now covers and what remains open for later `R12`
- this spec and its paired process ledger

## Portability

- the turnkey CLI must launch the server with the current Python interpreter,
  not with a shell-specific wrapper
- the default server spawn path must work on Windows and macOS without assuming
  `bash`
- skills must reference board/runtime facts symbolically, not through
  machine-specific serial paths or probe UIDs
- the run loop must use explicit per-step timeouts so an abnormal child call
  does not hang the whole turnkey client indefinitely

## Verification plan

Static and contract checks:

- `uv run pytest -q tests/test_turnkey.py`
- `uv run ruff check src/pyocd_debug_mcp/brain tests/test_turnkey.py`
- `uv run mypy src`

CLI smoke:

- `uv run pyocd-turnkey list-skills`
- `uv run pyocd-turnkey run --board-id nrf52840dk --skill-id reference-health-check --json`

Live suite for this phase:

- `uv run python host_bootstrap.py --board-id nrf52840dk`
- `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --recover-test nrf52840dk --confirm-shared-usb nrf52840dk`
- `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`
- `uv run pyocd-turnkey run --board-id nrf52840dk --skill-id reference-health-check --json`
- `uv run pyocd-turnkey run --board-id nrf52840dk --skill-id nordic-recover-cycle --json`

If a failure appears in the new turnkey path, fix it before claiming the phase
green.

## Acceptance criteria

- a real `brain/` package exists in product code
- a real turnkey CLI script exists and is documented
- the CLI starts and talks to the current MCP server over stdio
- the repo has tracked turnkey skills data files
- the initial skills succeed locally and on the attached `nrf52840dk`
- the new code passes targeted tests/lint/type checks
- docs reflect what phase 1 proved and what later `R12` work still remains

## Verified

- `R11` substrate is already green and is the foundation for this phase
- `nrf52840dk` already has working Stage 0, Stage 1, and `R11` proof on this
  host, so it is a valid live bench target for the first turnkey slice
- product code now exists for the phase-1 turnkey package:
  - `src/pyocd_debug_mcp/brain/`
  - `skills/turnkey/`
  - `uv run pyocd-turnkey`
- targeted validation passed:
  - `uv run pytest -q tests/test_turnkey.py`
  - `uv run ruff check src/pyocd_debug_mcp/brain tests/test_turnkey.py`
  - `uv run mypy src`
- broader repo regression ladder passed again after the new slice landed:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy src`
- the phase-1 live acceptance slice passed on attached `nrf52840dk`:
  - `uv run python host_bootstrap.py --board-id nrf52840dk`
  - `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --recover-test nrf52840dk --confirm-shared-usb nrf52840dk`
  - `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`
  - `uv run pyocd-turnkey list-skills`
  - `uv run pyocd-turnkey run --board-id nrf52840dk --skill-id reference-health-check --json`
  - `uv run pyocd-turnkey run --board-id nrf52840dk --skill-id nordic-recover-cycle --json`

## Pending verification

- full scoped-pair rollout of the turnkey phase-1 slice
- richer `R12` skill set and open-ended repair path
- premium acceptance benchmark against `R11`
