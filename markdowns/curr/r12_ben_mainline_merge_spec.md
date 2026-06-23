> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# R12 Ben Mainline Merge Spec

## Goal and roadmap anchor

This spec defines how to take the current `Ben-FCLI/ben-FCLI` `R12` brain as
the mainline product direction and fold in the specific Jason-originated
strengths that make it more portable, more testable, and more reliable on a
fresh Windows or macOS machine.

Roadmap anchor:

- primary: `R12` turnkey brain, skills, CLI, and acceptance benchmark
- secondary: portability closure work that currently still sits below full
  product closure in `current-progress.md`

The goal is not to preserve two equal `R12` products. The goal is to specify
one final product direction:

- intelligent
- self-code-writing when a task requires a fix
- self-debugging
- self-iterating until it reaches a trustworthy green state or a clear refusal
  or block boundary
- portable by default on Windows and macOS
- no mandatory `NCS` dependency for the normal build path, while still
  reusing an existing `NCS` install when present
- configurable enough to absorb more boards without re-architecting the brain
- autonomous by default after a bounded bootstrap

## Scope and non-scope

### In scope

This spec covers:

- what Ben's current `R12` keeps as the outer product architecture
- what Jason-originated ideas should be moved into Ben's branch
- what additional Ben-side work is still required before this branch can be
  treated as the single mainline product
- how to preserve benchmark comparability, portability, and honest proof
  boundaries while migrating toward the stronger product shape

### Out of scope

This spec does not:

- replace the current scoped-pair validation bar with an unproven
  "any board works" claim
- change the Stage 0 through `R11` substrate architecture
- declare Ben's current branch already closed on fresh-machine portability
- require replacing the current `R11` corpus with a new benchmark taxonomy
- require shipping the Jason deterministic `run --skill-id` runner as the
  primary user-facing `R12` product
- define `R13+` hosted transport or capability-ladder work in detail

## Reconciliation summary

### What the build plan says

The build plan and roadmap currently require that `R12` be:

- a native Python brain package
- an MCP client of the already-proven server
- provider-isolated
- owner of the orchestration loop
- benchmark-comparable against the already-frozen `R11` corpus
- lower-friction for the user than the BYO-agent path
- portable on macOS and Windows
- still bounded by the scoped-pair proof bar until more boards are explicitly
  proven

The build plan also requires:

- shared hardware logic below both frontends
- no hardcoded OS behavior
- no manual "go debug your machine forever" setup model
- self-hosted local hardware control

### What the current Ben code does

The current Ben branch already implements the stronger product shape:

- provider-flexible brain package under `src/pyocd_debug_mcp/brain/`
- `pyocd-debug-brain run --board-id ... --task ...`
- `pyocd-debug-brain benchmark --case-id ...` and `--suite ...`
- four provider backends:
  - `openai-api`
  - `anthropic-api`
  - `codex-cli`
  - `claude-cli`
- workspace-aware file read, replace, build, diff, and green-check flow
- benchmark reuse of the frozen 12-case `pilot_v1_plus_b003_b004` corpus
- live `codex-cli` proof on the scoped pair

At the same time, the current Ben code still has gaps relevant to the desired
mainline product:

- local build execution is still `bash`-hardcoded in
  `src/pyocd_debug_mcp/brain/workspace.py`
- the MCP client layer is still too monolithic and too coupled to parsed
  product behavior
- typed evidence tracking is lighter than it should be for cross-provider
  comparison and trustworthy iteration analysis
- deterministic known procedures exist only implicitly, not as a clean helper
  layer separate from model-facing prompt skills
- portability closure is still incomplete on fresh Windows/macOS no-`NCS`
  hosts

### What Jason's current code does

The current Jason branch is not the better outer product, but it has several
concrete internal strengths:

- clean `ServerCommand` and `ToolClientProtocol` seams in
  `Firmware-CLI/src/pyocd_debug_mcp/brain/mcp_client.py`
- host-aware local command execution in
  `Firmware-CLI/src/pyocd_debug_mcp/brain/runner.py`
- typed evidence models:
  - `Observation`
  - `Hypothesis`
  - `Experiment`
  - `StrategyEvaluation`
- deterministic workflow YAMLs that are useful as fixed internal procedures
  and regression helpers

Jason's current branch is still weaker as the top-level product shape because:

- it is driven by `skill_id`, not by a user task
- it is deterministic-first rather than product-turnkey-first
- it does not express the multi-provider product direction Ben already has

### What the merge note says

`markdowns/R12JasonBenMerge.md` is directionally right:

- keep Ben's outer product
- selectively absorb Jason's better internals

That note is useful, but it is incomplete for the final objective because it
does not fully spell out:

- the full fresh-machine portability closure requirements
- the no-`NCS`-required product bar
- the migration of known-good deterministic procedures into an explicit
  internal helper layer
- the need to preserve and extend the current managed-Zephyr bootstrap story

### Surfaced conflicts and ambiguities

⚠️ AMBIGUITY: the user objective says the final product should work with
"most any board and any hardware" and be "fully configurable." The current
build plan and current proof boundary are still scoped to:

- `nrf52833dk`
- `nucleo_l476rg`

This spec interprets the user goal as:

- architecture must be extensible and data-driven for additional boards
- portability and configuration flow must not be scoped only to the current
  pair
- but product truth and closure claims must still remain tied to the boards
  actually proven

⚠️ AMBIGUITY: the user wants the product to be autonomous by default with
minimal manual intervention. The portability playbook still allows a short,
bounded bootstrap before the agent starts. This spec therefore treats "minimal
/ no manual intervention" as:

- short bootstrap allowed
- ongoing setup labor after bootstrap is not allowed

⚠️ CONFLICT: the current Ben `R12` implementation is the stronger product
shape, but its current `workspace.py` still violates the portability direction
by hardcoding `bash`. Per the authority order, the portability rule wins. The
mainline product direction remains Ben's, but that implementation detail must
change before the branch is treated as the portable mainline.

⚠️ CONFLICT: the current Ben docs describe `R12` closure primarily as a
second-provider proof problem. The broader user objective also requires:

- self-contained build bootstrap
- managed no-`NCS` path
- cross-host portability closure

Per the authority order, those broader portability requirements remain part of
the closure bar even if the current `R12` narrative emphasizes provider proof.

## Design

### Product decision

The final product direction should use Ben's current branch as the mainline
`R12` architecture.

That means the mainline product keeps:

- the freeform task-driven CLI
- the benchmark CLI
- the provider-flexible architecture
- the provider-driven structured action loop
- the workspace/build/edit path
- the benchmark-comparison story against the frozen `R11` corpus

Jason's branch should not replace that outer product. Its value is as a source
of internal boundaries and deterministic helpers that strengthen Ben's branch.

### Architecture layers

This merge should remain mostly inside the `brain/` layer, with tightly scoped
portability consequences in the build/setup path and doc consequences in the
repo status docs.

Primary touched layer:

- `brain/`

Secondary touched surfaces:

- managed build portability helpers already used by the brain
- docs that describe `R12` closure and portability status

This avoids reopening the shared Stage 0-`R11` substrate architecture.

### Keep from Ben as the outer architecture

These stay as the canonical product path:

- `src/pyocd_debug_mcp/brain/config.py`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/benchmark.py`
- `src/pyocd_debug_mcp/brain/cli.py`
- current provider modules
- current freeform `run` interface
- current benchmark interface
- current prompt/context skill system under:
  - `skills/common/`
  - `skills/mcu_families/`

Why:

- this is the product-facing architecture firmware engineers actually want
- it already matches the current build-plan direction
- it preserves benchmark comparability and provider flexibility

### Move from Jason into Ben

These are the Jason-originated items that should move over, either literally
or conceptually.

#### 1. MCP transport abstraction

Adopt Jason's client seam idea into Ben's `brain/mcp_client.py`:

- `ServerCommand`
- `ToolClientProtocol`
- a lower-level transport-only client
- a higher-level parsed wrapper for product use

Keep Ben's richer parsed metadata behavior:

- `session_id`
- `probe_uid`
- `route_used`
- refusal codes
- block codes

Target effect:

- Ben's loop depends on a protocol, not on one concrete client
- testing seams improve
- future remote transport and mocks become easier

#### 2. Host-aware local command execution

Port Jason's cross-host shell dispatch into Ben's local build flow:

- Windows:
  - `cmd.exe /d /s /c ...`
- POSIX:
  - `bash -lc ...`

This belongs in Ben's workspace/build helper layer, not in ad hoc scattered
call sites.

Target effect:

- Ben's brain can rebuild on Windows and macOS through one shared path
- current `bash` hardcoding is removed

#### 3. Typed evidence models

Adopt Jason's typed reasoning/evidence dataclasses into Ben's branch:

- `Observation`
- `Hypothesis`
- `Experiment`
- `StrategyEvaluation`

These should augment, not replace:

- `TurnDecision`
- the current action schema
- the current provider-driven loop

Target effect:

- better post-run analysis
- better cross-provider comparison
- stronger "self-debugging and self-iterating" evidence trail
- clearer reasoning artifacts for later scoring and regression analysis

#### 4. Deterministic internal playbooks

Move Jason's deterministic workflow YAML concept into Ben's branch, but not as
the primary product surface.

Good uses:

- internal health-check helper
- internal recover -> reflash -> reverify helper
- deterministic green-check helper
- benchmark prep and fallback procedures
- regression and smoke procedures

Important rule:

- do not replace the user-facing `run --task ...` product path with
  `run --skill-id ...`

Naming rule:

- do not overload Ben's existing prompt/context "skills" with executable
  Jason-style deterministic procedures
- introduce a separate concept such as:
  - `playbooks/`
  - `workflows/`
  - `macros/`

### Concrete move matrix

This is the file-level migration list for implementation planning.

#### Must port now

1. `Firmware-CLI/src/pyocd_debug_mcp/brain/mcp_client.py`
   -> concepts into
   `Ben-FCLI/src/pyocd_debug_mcp/brain/mcp_client.py`
   - port:
     - `ServerCommand`
     - `ToolClientProtocol`
     - transport-only stdio client seam
   - keep Ben-specific parsed response behavior on top

2. `Firmware-CLI/src/pyocd_debug_mcp/brain/runner.py`
   -> host-aware process execution logic only
   into
   `Ben-FCLI/src/pyocd_debug_mcp/brain/workspace.py`
   - port:
     - `_shell_command_for_host(...)`
     - `_run_local_command(...)` pattern
   - do not port:
     - deterministic health/repair runner as the main product loop

3. `Firmware-CLI/src/pyocd_debug_mcp/brain/models.py`
   -> evidence-model concepts into Ben brain
   - port:
     - `Observation`
     - `Hypothesis`
     - `Experiment`
     - `StrategyEvaluation`
   - adapt them to Ben's current action/loop/result shape rather than copying
     the full file unchanged

4. `Firmware-CLI/skills/turnkey/*.yaml`
   -> concepts only into a new Ben-side deterministic helper layer
   - port:
     - known-good health-check sequence
     - reference-contract diagnose sequence
     - reference-contract repair sequence
     - Nordic recover cycle sequence
   - rename the concept away from Ben prompt-skill YAMLs

#### May port later if still useful after the core merge

1. Jason deterministic CLI affordances from
   `Firmware-CLI/src/pyocd_debug_mcp/brain/cli.py`
   - only as developer-only helper commands
   - not as the primary user-facing interface

2. Jason deterministic benchmark-only helper logic from
   `Firmware-CLI/tests/harness/r12_turnkey_benchmark.py`
   - only where it strengthens regression helpers or internal fallback flows
   - not where it would weaken Ben's direct comparability to the current
     frozen `R11` turnkey story

3. Jason deterministic skill loader patterns from
   `Firmware-CLI/src/pyocd_debug_mcp/brain/skills.py`
   - only if Ben needs a separate loader for deterministic playbooks
   - not as a replacement for Ben's current prompt/context skill loader

#### Do not port

1. Jason's main product CLI model:
   - `run --skill-id ...`

2. Jason's deterministic runner as the default `R12` product loop:
   - `Firmware-CLI/src/pyocd_debug_mcp/brain/runner.py`

3. Jason's narrower `nrf52840dk`-centric proof story

4. Jason's deterministic skill system as the only meaning of "skills"

5. Any Jason-side assumptions that reduce Ben's current provider-flexible
   architecture back to one decision path

### Add to Ben beyond the current merge note

The merge note is good, but the final mainline product also needs the
following Ben-side additions or hardening work.

#### 1. Make portability a first-class closure bar

The final Ben mainline must explicitly treat these as required:

- fresh Windows validation with no preinstalled `NCS`
- fresh macOS validation with no preinstalled `NCS`
- reuse an existing `NCS` install when present
- otherwise bootstrap a managed upstream-Zephyr path automatically

This must apply to:

- freeform brain runs
- workspace rebuilds during repair
- benchmark runs

#### 2. Preserve the managed-Zephyr-by-default build story

The final mainline should not regress to:

- "developer must already have NCS"
- "developer must manually wire a Zephyr workspace"
- "brain repair only works if the workstation already looks like the author's
  machine"

The correct build policy is:

- prefer managed upstream-Zephyr bootstrap
- reuse existing `NCS` or Zephyr installations when valid
- keep board-specific build provenance data explicit
- never force `NCS` as the mandatory normal path

#### 3. Add a stronger artifact-writing contract for turnkey runs

Ben already writes strong run artifacts, but the final mainline should freeze
these as explicit acceptance requirements:

- request record
- result record
- state record
- prompt bundle
- model turns
- brain trace
- diff / applied patch record
- benchmark case/scoring records when in benchmark mode

These artifacts must remain:

- session-keyed
- machine-readable
- useful for cross-provider comparison

#### 4. Add reconnect-tolerant accounting only if it preserves trust

Ben's current `R12` spec freezes one benchmark case to one MCP session. Jason's
current and `R11`-side runner hardening show that real agent behavior can open
an extra short scouting session.

The final Ben mainline should not silently loosen this rule, but it should
specify a safe future direction:

- one canonical final session remains required
- extra sessions may be recorded as warnings rather than automatic failure
  only if the runner-owned final verification still remains authoritative

This should be treated as a hardening item, not as an automatic rewrite.

#### 5. Add stronger runner-owned green verification discipline

The final product must preserve the current "green" trust rule:

- model/provider self-report is not enough
- the runner-owned verification path remains authoritative

This is necessary for:

- self-debugging claims
- self-iteration claims
- benchmark credibility

#### 6. Add explicit bounded-progress and hang discipline

The final mainline should freeze one operational rule:

- short runtime calls such as a single UART read must fail fast when stuck
- longer build, flash, benchmark, and repair operations may run longer when
  they are making progress

This rule should be encoded in:

- local command helpers
- provider turn timeouts
- benchmark harness expectations

### What should not move from Jason

Do not import these as the mainline product shape:

- Jason's top-level `run --skill-id ...` CLI model
- Jason's deterministic runner as the user-facing product
- Jason's old `nrf52840dk`-centered story as the scoped product truth
- Jason's narrower benchmark/product framing when it would weaken Ben's current
  `R11`-comparability story

## Board-facts-as-data and origin tags

The merged mainline must preserve these value rules.

### Values that remain `PROJECT-DEFINED`

- `PYOCD_TURNKEY_PROVIDER` provider names
- CLI subcommand names
- deterministic playbook directory name once chosen
- run artifact filenames
- timeout defaults
- convergence thresholds
- benchmark warning vs failure rules for reconnect accounting
- managed-Zephyr bootstrap policy

### Values that remain `VENDOR-FIXED`

- provider API env var names:
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
- CLI executable names:
  - `codex`
  - `claude`
- shell dispatch executables:
  - `cmd.exe`
  - `bash`
- `mcp` client call semantics

### Values that remain `HW-FIXED`

- board IDs do not become hardware facts, but all MCU/probe-specific facts
  still remain in board config or board-owned metadata
- no merge work here should reintroduce board behavior as code branches

### Required rules

- no board fact becomes an ad hoc branch in the brain
- no machine-local path or port becomes a tracked repo default
- no host-specific build assumption gets hardcoded into the product layer

## Documentation plan

If this spec is implemented, the following docs will need to move.

### Must update

- `markdowns/firmware_agent_build_plan_concrete (10).md`
  - to clarify Ben's provider-flexible brain as the mainline `R12` product
  - to record deterministic internal playbooks as helpers rather than the
    primary product interface if that becomes a settled decision
- `markdowns/ROADMAP.md`
  - to align `R12` closure wording with the merged product and portability bar
- `markdowns/current-progress.md`
  - to separate:
    - Ben mainline product architecture
    - imported Jason hardening
    - remaining portability/provider proof gaps
- `README.md`
  - to reflect the final mainline product surface and bootstrap expectations
- `markdowns/curr/r12_turnkey_spec.md`
  - or its successor if the current accepted `R12` contract is amended rather
    than replaced

### May need update depending on implementation shape

- `init.md`
  - if provider/bootstrap behavior changes materially
- `stage0_setup.md`
  - only if the pre-agent setup flow changes materially
- MCP tool docstrings in `src/pyocd_debug_mcp/server.py`
  - only if implementation work changes tool contract wording

### Should not become sidecar authority

- this tmp spec is a planning artifact, not a new competing roadmap
- accepted decisions must eventually move into the authoritative docs above

## Portability

This is the most important addition beyond the current merge note.

The final Ben mainline must satisfy the absent-stranger bar:

- fresh Windows machine
- fresh macOS machine
- one supported board attached
- short bootstrap
- guided agent takes over
- no prolonged manual environment debugging after bootstrap

### Required portability outcomes

- the brain's rebuild path is host-aware
- the brain does not require `bash` on Windows
- the normal build path does not require a preinstalled `NCS`
- an existing `NCS` install is reused if present
- a managed upstream-Zephyr path is bootstrapped when needed
- build, flash, and verify loops use the same portable helper path as the rest
  of the repo
- no provider path requires manual MCP registration
- no provider path requires explicit probe UID or serial-port tuning in the
  normal path

### Allowed bootstrap

Allowed:

- `uv` install
- repo bootstrap helper
- one-time driver or vendor-tool install if bounded and explicit

Not allowed as the normal steady-state:

- repeated manual environment surgery after the agent starts
- per-run editing of local config files
- hidden dependency on the author's shell environment

## Verification plan

This is a spec-only task, so the verification plan here defines the later
implementation ladder rather than claiming implementation proof.

### Spec-phase verification

- verify this spec against:
  - build plan
  - roadmap
  - current progress
  - current Ben code surface
  - current Jason comparison surface
  - `R12JasonBenMerge.md`

### Build-phase non-hardware ladder

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run mypy src`
- targeted unit tests for:
  - transport abstraction
  - host-aware build execution
  - evidence-model serialization
  - deterministic playbook loading if added
- dry-run CLI checks for:
  - freeform run mode
  - benchmark mode

### Hardware-backed ladder

Scoped pair:

- freeform healthy verification on:
  - `nrf52833dk`
  - `nucleo_l476rg`
- full turnkey benchmark suite on both boards
- second-provider ladder rerun once provider issue is fixed

Alternate board:

- `nrf52840dk` reruns are optional parity proof, not scoped-pair closure

Fresh-machine portability proof:

- fresh Windows no-`NCS` validation
- fresh macOS no-`NCS` validation
- verify managed-Zephyr bootstrap, rebuild, flash, and one benchmarked repair
  path

## Acceptance criteria

The merged Ben mainline is done only when all of the following are true.

1. Ben remains the single mainline `R12` product architecture.
2. Jason's transport abstraction is integrated:
   - `ServerCommand`
   - `ToolClientProtocol`
   - transport-only client
   - higher-level parsed client wrapper
3. Ben's local build path becomes host-aware and no longer hardcodes `bash`.
4. Typed evidence tracking is present and recorded in run artifacts.
5. Deterministic Jason-style procedures exist only as internal helper
   playbooks, not as the primary user-facing product interface.
6. The freeform product CLI remains task-driven:
   - `run --board-id ... --task ...`
7. The benchmark CLI remains benchmark-driven and corpus-comparable against the
   frozen `R11` suite.
8. The mainline build path works without mandatory `NCS`, while still reusing
   an existing `NCS` install when present.
9. Fresh-machine Windows and macOS portability proof exists for the managed
   no-`NCS` path.
10. Scoped-pair `R12` proof remains green after the merge.
11. A second provider clears the same closure ladder or an explicitly approved
    replacement provider path is frozen and proven.
12. Docs are updated so the product story, proof boundary, and portability
    story all match reality.

## Recommended implementation order

1. Refactor Ben `brain/mcp_client.py` around Jason's transport boundary.
2. Replace hardcoded `bash` build execution with host-aware command helpers.
3. Add typed evidence models and artifact serialization.
4. Introduce deterministic internal playbooks under a separate concept
   boundary.
5. Reconcile benchmark accounting and final verification trust rules.
6. Re-run scoped-pair provider proof.
7. Close fresh-machine Windows/macOS portability proof.

## Verified

- this spec is reconciled against the current Ben build plan, roadmap, README,
  current-progress doc, current `R12` spec, the current Ben brain surface, the
  current Jason `R12` brain surface, and `markdowns/R12JasonBenMerge.md`
- the current Ben branch is already the stronger outer `R12` product
  architecture
- the current Jason branch has specific internal strengths worth porting:
  transport abstraction, host-aware command execution, typed evidence models,
  and deterministic helper workflows

## Pending verification

- implementation of any of the merge work described here
- confirmation that the final merged Ben mainline stays green on the scoped
  pair
- second-provider closure on real hardware
- fresh-machine Windows no-`NCS` proof
- fresh-machine macOS no-`NCS` proof
- proof that the merged branch satisfies the broader "autonomous by default
  after bootstrap" product bar without widening setup burden
