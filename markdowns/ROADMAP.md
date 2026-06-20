# ROADMAP

> **STATUS (2026-06): R0–R10 COMPLETE and live-proven on the scoped pair
> (`nrf52833dk` + `nucleo_l476rg`); `R11` is the active item.** This is the
> original roadmap / decision record. Sections that describe R0–R10 work — including
> the `R7` "Current-state reconciliation" and the Phase-B/C frontier notes — now
> describe work that is **done**; read them as history, not as pending work. For
> live status see `current-progress.md`; for the file map see `repo_file_index.md`.

This document rewrites the project roadmap in simpler, more execution-focused language.

It is based on the current build plan in [firmware_agent_build_plan_concrete (10).md](./firmware_agent_build_plan_concrete%20%2810%29.md), but it is organized for implementation instead of product narration.

The goal is to answer three questions clearly:

1. What does each roadmap item mean in simple English?
2. What has to finish before the next thing can proceed?
3. What actual work is included inside each item?

## How To Read This Document

The roadmap uses IDs `R0` through `R15`.

Each roadmap item is a real delivery unit. It is not just an idea or a stage heading.

For each item, this document explains:

- what the item means in plain English
- why it exists
- what must already be true before it starts
- what it produces
- what work it includes
- how you know it is done

The roadmap is also designed for a team of three people working in parallel:

- `Track A`: board and probe enablement
- `Track B`: runtime platform and safety
- `Track C`: validation, fixtures, and product layer

Those tracks are not strict silos. They are recurring work lenses.

Through `R0-R10`, staffing should move with the current frontier: the active bottleneck, the next dependency that can already be prepared, and the automation or hardening work that keeps the current milestone trustworthy.

## Cross-Cutting Engineering Constraints

These are not separate roadmap items.

They are quality bars that must shape the implementation of the early roadmap items, especially `R0` through `R10`.

This matters because later objectives do not just depend on earlier items being **finished**. They depend on earlier items being finished **well**.

If the team completes early items with weak abstraction boundaries, ad hoc schemas, unclear observability, or inconsistent safety behavior, then later roadmap items will still exist on paper but become much harder, much noisier, and much less trustworthy in practice.

The most important rule is:

**Later-stage ambitions require early-stage discipline.**

In particular:

- `R12` depends on `R4-R10` being clean, stable, and parseable.
- `R13` depends on `R5`, `R9`, and `R10` having disciplined session, state, and config behavior.
- `R14` depends on `R7` being a true abstract SWD interface rather than a pyOCD-shaped one.
- `R15` depends on `R4-R11` producing trustworthy artifacts, logs, observability, and benchmark evidence.

### 1. Stable Abstraction Boundaries

What this means:

- The SWD interface must describe product-level behavior, not pyOCD internals.
- The UART interface must describe stable read/reconnect semantics, not "whatever pyserial happened to do."
- The MCP server must expose a stable contract, not a thin wrapper over unstable local implementation details.
- Flash, UART, recover, and board-validation behavior live in shared internal
  services below both frontends. This is now a settled build-plan decision
  (Step 1.0): the MCP tools and the turnkey CLI / local programmer flow are
  BOTH thin wrappers over those same stable services, and neither owns the
  logic. `stage0_check.py` is the CLI frontend in embryo — a wrapper over the
  shared board-validation code, not a parallel implementation — so behavior
  proven there is reused by the MCP tools, never rebuilt. The structural reason
  a capability can surface as a shell command today and an MCP tool later with
  no duplicated logic: same service underneath, different wrapper on top.
- **Current-state caveat (RESOLVED 2026-06).** This constraint is now satisfied. The shared service
  layer exists (`adapters/` + `services/` + `guardrails/`), the pyOCD Python-API path was proven on
  the bench, and both `stage0_check.py` and `server.py` are thin callers over the shared services —
  the J-Link workaround lives in one place. The two-parallel-implementations state described in
  earlier revisions of this bullet (and in `R7` "Current-state reconciliation" below) is history;
  the migration completed as part of Stage 1. See `current-progress.md` for the live proof.
- Documentation follows the same split (see the Doc-Sync and Tool-Description
  playbooks): an MCP tool's contract lives in its **docstring** — the
  description the client reads over the protocol, never a sidecar `.md`; the
  shell bring-up workflow lives in the single operator guide
  (`stage0_setup.md`); the shared service is plain code below both. Do not
  document an MCP tool in a `.md` the client can never read.

Why this matters later:

- `R12` needs clean, predictable lower layers so the brain can reason instead of carrying workaround logic.
- `R14` only works cleanly if the SWD interface is genuinely backend-agnostic.
- `R15` depends on stable underlying tools so capability changes come from better reasoning, not shifting substrate behavior.

### 2. Board Facts As Data, Not Code Branches

What this means:

- Board-specific facts belong in validated config files.
- Machine-local attachment facts belong in local overrides, not tracked board config.
- Higher layers should not accumulate scattered `if board == ...` logic.

Why this matters later:

- `R12` skills and orchestration become much harder if board knowledge leaks into unrelated code.
- `R13` multi-board operation becomes brittle if board identity is mixed with machine-local state.
- `R14` backend swapping is harder if board behavior is encoded in ad hoc conditionals.

### 3. Artifact Discipline

What this means:

- Flashed images, ELFs, recovery images, and known-good baselines must have explicit identities and canonical locations.
- The flashed artifact and the symbol-resolution artifact must be treated as a deliberate pair.
- Recovery-image paths must be stable because safety logic depends on them.

Why this matters later:

- `R10` safety gates cannot be trustworthy without clean artifact identity.
- `R11` and `R12` cannot compare outcomes or reason about fixes if the baseline is fuzzy.
- `R15` cannot produce credible capability evidence without reproducible artifact baselines.

### 4. Reproducible Observability

What this means:

- UART semantics must be explicit.
- Register and memory reads must be stable and well-defined.
- Logs must be structured.
- Session IDs must consistently tie together server state, run outputs, and later analytics.

Why this matters later:

- `R10` convergence detection depends on clean signals.
- `R11` benchmark evaluation depends on comparable evidence across runs.
- `R15` depends on good enough observability to distinguish real progress from noise.

### 5. Deterministic Safety Semantics

What this means:

- Destructive operations must never be implicit.
- Unlock/recover must be explicit, gated, and logged.
- Refusal behavior must be predictable and machine-interpretable.

Why this matters later:

- `R11` needs the first product to be trustworthy under a real external agent.
- `R12` needs the premium product to inherit the same hard safety guarantees.
- `R13` remote and scaled operation become dangerous if local safety semantics were left fuzzy.

### 6. Testability And Harnesses From Early On

What this means:

- Stage 1 should be proven by a repeatable smoke harness, not just ad hoc REPL success.
- Benchmark fixtures should begin forming before the product layer is "finished."
- Captured outputs should be structured enough to compare and rerun.

Why this matters later:

- `R11` depends on benchmark rigor, not demo optimism.
- `R12` needs a way to prove the turnkey product is actually better.
- `R15` only becomes a real experimental ladder if the project already knows how to measure success and failure.

### 7. Cross-Platform Hygiene

What this means:

- No committed machine-specific serial paths.
- No committed machine-specific probe bindings.
- No shell-specific primary workflow.
- No OS-specific path assumptions in product code.

Why this matters later:

- `R0-R7` become slower and noisier without it.
- `R11` results become less credible if different developers are effectively running different systems.
- `R13` later scale and hosted work become more complicated if the local substrate was never normalized.

## The Roadmap In Simple English

### `R0` Team Development Protocol And Toolchain Standard

Simple English:
This is the team agreement for how development works. It answers questions like: which Python version do we use, how do we install dependencies, where do local machine overrides live, and how do we avoid "works on my machine" problems between macOS and Windows.

Why it exists:
If the team does not standardize the environment first, later failures are ambiguous. A bug could be in the code, or it could be a Python-version mismatch, a bad PATH, a local probe-selection issue, or a dependency mismatch.

Early quality bars this item must enforce:

- cross-platform hygiene starts here
- local-machine facts must be separated from tracked repo facts
- the team command surface must be consistent enough that later benchmarks and smoke harnesses mean the same thing on every machine

### `R1` Repo Skeleton, Packaging, Canonical Layout, And README

Simple English:
This is the package that creates the actual project structure on disk. It decides where code lives, where board configs live, where firmware artifacts live, where runtime outputs go, and how the package is installed and run.

Why it exists:
Without one shared repo layout, different people will solve the same problem in incompatible ways.

Early quality bars this item must enforce:

- artifact discipline starts here
- session outputs must already be shaped with later logging and session-state needs in mind
- the layout must support later safety, benchmark, and skills work without moving paths later

### `R2` STM32 Stage 0 Bring-Up On Bench

Simple English:
This is the first real hardware validation package. It proves that the STM32 Nucleo board works from the host machine: the probe is visible, the target is correct, the board flashes, and UART output is real.

Why it exists:
The STM32 board is the cleanest open-stack path. It is the fastest way to prove that the basic hardware strategy is sound.

Early quality bars this item must enforce:

- evidence must be documented repeatably, not left as bench folklore
- probe and serial behavior must be captured in a way that informs later config and adapter design
- this board should establish the first "known-good hardware loop" baseline for later comparison

### `R3` nRF Stage 0 Bring-Up, J-Link Route Decision, And Recover Proof

Simple English:
This is the second hardware validation package, focused on the harder board. It proves the nRF board works, forces a J-Link path decision, and proves that the recover/unlock flow is understood on real hardware.

Why it exists:
The board abstraction is not real until both probe families work. This package also makes the destructive unlock behavior concrete instead of theoretical.

Early quality bars this item must enforce:

- destructive recover behavior must be observed and documented carefully because later safety semantics depend on it
- the J-Link path decision must be made in a way that does not leak probe-specific assumptions upward into the SWD abstraction
- the distinction between "locked target" and "dead connection" must be made explicit for later error handling

### `R4` Reference Firmware Baselines And Artifact Contract For Both Boards

Simple English:
This package defines the "known-good" firmware for each board. It chooses the exact source tree, build command, output artifacts, and expected UART behavior that count as the baseline.

Why it exists:
Later checks like flashing, UART validation, symbol resolution, and bug injection all depend on having one trustworthy reference artifact per board.

Early quality bars this item must enforce:

- baseline artifacts must be canonical and reproducible
- the flashed image and ELF must be treated as a deliberate pair
- recovery artifacts must be versioned and discoverable enough for later safety logic
- benchmark and bug-fixture work later on is only as credible as the discipline established here

### `R5` Board Schema, Loader, And Local Override Model

Simple English:
This package defines how the project represents board-specific facts as data instead of scattering them through code. It also defines how each developer machine can supply local attachment info without polluting tracked repo config.

Why it exists:
Board identity must be repo-tracked, while machine attachment must stay local. This is one of the most important architectural rules in the project.

Early quality bars this item must enforce:

- board facts must remain data, not drift back into code branches
- local machine overrides must never become accidental global defaults
- config loading must be centralized so later products do not parse board metadata inconsistently
- this item is one of the main prerequisites for scaling beyond two boards without structural rewrite

### `R6` UART Adapter And Serial Discovery Contract

Simple English:
This package creates the serial/UART layer. It defines how the code opens ports, reads output, handles reconnects, and maps a logical board to the right serial endpoint on macOS and Windows.

Why it exists:
UART is one of the main observability channels for the agent. If it is unreliable or underspecified, everything built on top of it becomes noisy.

Early quality bars this item must enforce:

- observability semantics must be stable, not "best effort"
- reconnect behavior must be deliberate because later loops depend on reset/reflash resilience
- the adapter contract must be explicit enough that benchmark expectations and convergence logic can rely on it
- serial discovery must be robust enough that cross-platform differences do not leak into product logic

### `R7` SWD Interface And pyOCD Backend For Both Boards

Simple English:
This package creates the hardware control layer. It defines the abstract SWD interface and implements it with pyOCD for both the STM32 and nRF boards.

Why it exists:
This is the control plane of the product. Flashing, halting, reading registers, and reading memory all depend on this being stable and board-agnostic.

Early quality bars this item must enforce:

- the SWD interface must stay backend-agnostic from the start
- pyOCD-specific types or assumptions should not leak through the abstraction
- board-specific quirks should be absorbed in the backend, not pushed upward
- if this is done poorly, later vendor backends and later brain logic both become much harder

### `R8` Symbol Resolution And Stage 1 Smoke Harness

Simple English:
This package closes Stage 1. It adds ELF/symbol support and creates a repeatable smoke harness that proves the UART and SWD layers work together in a real loop.

Why it exists:
Stage 1 is not done when methods exist. It is done when the direct board-control substrate works repeatably and can be exercised by one repeatable harness.

Early quality bars this item must enforce:

- the smoke harness must become the first real repeatability standard for the project
- symbol resolution must rely on explicit artifact pairing, not ad hoc guesses
- this is where the project begins proving that its lower layers are measurable rather than merely plausible

### `R9` stdio FastMCP Server, Tool/Resource Schema, And Inspector Validation

Simple English:
This package turns the shared board-control operations built on the Stage 1
adapters into a local MCP server surface. It defines the exact tool/resource
contract and validates it in the MCP Inspector.

Why it exists:
This is the interface between the board-control substrate and any external agent client.

Early quality bars this item must enforce:

- response schemas must be stable enough for both external agents and the later turnkey brain
- tool/resource boundaries must avoid accidental side effects in read paths
- the server surface must describe product semantics, not just expose local implementation details
- if this layer is loose, later clients will couple to formatting accidents and brittle behavior

### `R10` Guardrails: Flash Gate, Unlock Gate, Logging, Session Store, And Convergence Watcher

Simple English:
This package implements the safety layer in the server. It decides when flashing is allowed, when unlock/recover is allowed, what gets logged, how session state is stored, and how repeated non-converging behavior is blocked.

Why it exists:
This is the core safety and differentiation layer of the project. The whole architecture depends on these protections living below the brain.

Early quality bars this item must enforce:

- safety semantics must be deterministic and machine-interpretable
- session state, run outputs, and logs must share one coherent identity model
- structured logging must be good enough for both support/debugging and later benchmark evidence
- the convergence watcher must consume reproducible signals, not informal heuristics layered over noisy substrate behavior

### `R11` BYO-Agent Benchmark Suite And Product #1 Validation

Simple English:
This package proves the first real product: a stock external agent can use the MCP server to debug safely on real boards using defined bug cases and fault cases.

Why it exists:
This is where the project stops being just a stack of components and becomes a real, testable product.

Early quality bars this item depends on:

- good artifact discipline from `R4`
- good observability from `R6-R8`
- stable server semantics from `R9`
- deterministic safety and logging from `R10`

Implication:

`R11` is where weak early discipline becomes visible. If earlier items were implemented sloppily, benchmark outcomes here become hard to interpret and hard to trust.

### `R12` Turnkey Brain, Skills, CLI, And Acceptance Benchmark

Simple English:
This package builds the premium product tier: your own brain, your own skills layer, and your own CLI on top of the same server.

Why it exists:
This is the path from "safe hardware substrate for external agents" to "our own differentiated product."

Early quality bars this item depends on:

- clean artifact and config contracts from `R4-R5`
- stable observability and control semantics from `R6-R8`
- stable MCP and refusal semantics from `R9-R10`

Implication:

If lower layers are inconsistent, the brain will absorb workaround logic and the architecture will start collapsing upward.

### `R13` Scale And Remote Transport

Simple English:
This package handles multi-board operation and optional hosted/remote operation later, after the local product is already proven.

Why it exists:
Scale and remote access matter operationally, but they should not be on the critical path to proving the core product.

Early quality bars this item depends on:

- disciplined session identity from `R1` and `R10`
- clean config and board binding from `R5`
- stable protocol surface from `R9`

Implication:

This item remains a clean extension only if hidden global state and local assumptions were kept out of earlier work.

### `R14` Vendor GDB Backends

Simple English:
This package adds optional alternate probe backends if pyOCD turns out not to be good enough for some board capability or reliability requirement.

Why it exists:
It is a hedge against open-stack limits, especially on J-Link-heavy flows.

Early quality bars this item depends on:

- a true abstract SWD contract from `R7`
- clear error and capability semantics that are not pyOCD-shaped

Implication:

If `R7` leaks pyOCD internals upward, `R14` stops being a contained backend swap and turns into a broader rewrite.

### `R15` Capability Ladder Experiments

Simple English:
This package is the post-MVP research and product-expansion track. It pushes the system from bug-fixing toward harder tasks like driver writing, bring-up, and later more autonomous experiments.

Why it exists:
This is where the long-term frontier and moat-building work lives, but it is deliberately not part of the critical path to the first products.

Early quality bars this item depends on:

- artifact rigor from `R4`
- observability rigor from `R6-R8`
- structured logs and watcher evidence from `R10`
- benchmark discipline from `R11-R12`

Implication:

This item only becomes a real experimental ladder if the earlier project already knows how to produce reproducible evidence instead of one-off demos.

## Dependency Tree

This section shows exact prerequisite flow.

### Short Version

```text
R0
├── R1
│   ├── R4
│   │   ├── R6
│   │   │   ├── R8
│   │   │   └── R10
│   │   ├── R8
│   │   ├── R10
│   │   ├── R11
│   │   └── R12
│   └── R5
│       ├── R6
│       ├── R7
│       ├── R9
│       ├── R10
│       └── R12
├── R2
│   ├── R4
│   ├── R5
│   └── R7
└── R3
    ├── R4
    ├── R5
    ├── R7
    └── R10

R6 + R7 + R4 -> R8
R8 -> Stage 1 Gate
Stage 1 Gate + R5 -> R9
R3 + R4 + R5 + R6 + R7 + R9 -> R10
R4 + R8 + R9 + R10 -> R11
Stage 4 Gate + R4 + R5 + R9 + R10 -> R12
Stage 4 Gate + R10 -> R13
R7 + concrete pyOCD gap -> R14
Stage 5 Gate -> R15
```

### Critical Path To Product #1

```text
R0
-> R2 and R3
-> R4 and R5
-> R7
-> R8
-> R9
-> R10
-> R11
```

This is the shortest path to the first shippable BYO-agent product.

### Critical Path To Product #2

```text
R0
-> R2 and R3
-> R4 and R5
-> R7
-> R8
-> R9
-> R10
-> R11
-> R12
```

This is the shortest path to the turnkey brain + CLI product.

## Full Item Outlines

Each item below expands the simple-English description into real work.

---

## `R0` Team Development Protocol And Toolchain Standard

### What this item actually entails

This item defines the rules that every developer machine must follow.

### Included work

- choose the exact Python version for the team
- define how virtual environments are created and activated
- define how dependencies are installed
- commit the first lockfile or equivalent pinned dependency set
- define local-machine override policy
- define config precedence
- define the command surface the team will use in development
- define "do not commit OS-specific attachment facts" as an explicit rule

### Concrete outputs

- a short developer protocol document
- a pinned dependency file
- a standard local environment bootstrap command sequence
- a local override convention such as `.env` plus optional `pyocd.local.yaml`

### Questions this item must answer

- Which Python version is mandatory?
- Do we use `venv` in-repo?
- How are dependencies installed?
- What values are allowed in tracked board config?
- Where do probe UIDs and local port overrides live?
- What command do all developers use to run checks?

### Definition of done

`R0` is done when a new developer on macOS or Windows can follow one documented bootstrap path and end up with the same command surface and the same dependency versions.

### What it does not include

- actual board bring-up
- package publishing
- MCP work
- agent work

---

## `R1` Repo Skeleton, Packaging, Canonical Layout, And README

### What this item actually entails

This item creates the initial project structure and makes the repo legible.

### Included work

- create `src/pyocd_debug_mcp/`
- **create the internal package layout — `adapters/`, `services/`, `tools/`, `guardrails/`,
  `server/`, `brain/`.** These are part of the canonical layout but do NOT exist in the repo yet;
  today `src/pyocd_debug_mcp/` holds flat modules plus a `server.py`. The `adapters/` + `services/`
  split is the spine the whole architecture wraps (see Cross-Cutting Constraint §1), so standing it
  up is an `R1` concern, and creating those two dirs is the first keystroke of the service-layer
  work proven in `R7` (the API-validation gate, build-plan Step 1.0d).
- create `boards/`
- create `firmware/`
- create `runs/`
- create `tests/`
- create initial `pyproject.toml`
- create root README explaining layout and naming rules
- choose canonical board IDs and make them visible everywhere

### Concrete outputs

- real directory tree committed to the repo
- packaging metadata committed
- root README documenting the tree
- naming rules for:
  - board IDs
  - artifact names
  - session output folders
  - bug-variant naming

### Questions this item must answer

- Where does product code live?
- Where do board configs live?
- Where do reference and recovery artifacts live?
- Where do runtime logs and per-session outputs go?
- Where do tests and bug variants live?

### Definition of done

`R1` is done when every later component can point at one stable repo layout instead of inventing its own paths.

### What it does not include

- fully implemented adapters
- benchmark fixtures
- server wiring

---

## `R2` STM32 Stage 0 Bring-Up On Bench

### What this item actually entails

This is real manual validation of the STM32 Nucleo board.

### Included work

- verify probe visibility through pyOCD
- verify the correct target name
- verify the target pack is present
- verify connection and simple register/memory access
- identify the correct UART endpoint
- flash a known-good image manually
- verify UART output manually
- document any host-machine quirks

### Concrete outputs

- validated `pyocd_target` for the STM32 board
- known-good probe-selection behavior
- known-good serial enumeration behavior
- a repeatable manual checklist for STM32 bring-up

### Questions this item must answer

- Does pyOCD see the ST-Link probe consistently?
- What exact target name is correct?
- What UART endpoint corresponds to the board?
- Can the board be flashed and observed cleanly?

### Definition of done

`R2` is done when a developer can take the STM32 board on a supported machine and reproduce the full manual Stage 0 flow without guesswork.

### What it does not include

- adapter code
- MCP
- safety logic

---

## `R3` nRF Stage 0 Bring-Up, J-Link Route Decision, And Recover Proof

### What this item actually entails

This is the manual validation package for the nRF board and its harder operational edge cases.

### Included work

- verify J-Link visibility through pyOCD
- document the J-Link route (DECIDED: native SEGGER J-Link path is the default; CMSIS-DAP is the
  fallback — the onboard J-Link OB does not expose CMSIS-DAP unless explicitly switched into it)
- verify the correct target name
- verify connection and simple memory access
- identify the correct UART endpoint and capture how it is selected on real hosts
- prove vendor-assisted serial auto-detect where it is defensible:
  `nrfjprog --com` for Nordic J-Link boards, `STM32_Programmer_CLI -l` for ST-LINK boards
- define the fallback behavior when serial selection remains ambiguous:
  interactive prompt on a real terminal, explicit `--port` rerun guidance otherwise
- flash a known-good image manually
- verify UART output manually
- manually prove a recover/unlock cycle and document the exact behavior
- keep recover policy typed in board data (`requires_recover_validation`, `recover_mode`) rather than
  letting tracked YAML inject arbitrary recover commands
- automate or guide the vendor (SEGGER J-Link) driver/software install for J-Link boards instead of
  emitting a manual "go download it" step (portability playbook §3); detect the missing vendor software,
  run/guide its install, or STOP-and-ask the author

### Concrete outputs

- validated `pyocd_target` for the nRF board
- documented J-Link path decision (native SEGGER default, CMSIS-DAP fallback)
- known-good serial enumeration behavior for the nRF board, including the dual-CDC case
- a documented vendor-assisted serial-selection path with prompt/manual fallback rules
- documented recover/unlock checklist and observed behavior

### Questions this item must answer

- What exact pyOCD path is used for J-Link on the team bench? (ANSWERED: native SEGGER J-Link path by
  default, CMSIS-DAP as fallback)
- Does the onboard J-Link behave consistently on the chosen hosts?
- What does a real unlock/recover cycle look like on this board?
- What evidence distinguishes a locked board from a dead connection?

### Definition of done

`R3` is done when the nRF board is no longer a theoretical second board and its destructive recover behavior is well-understood by the team.

### What it does not include

- automated unlock policy
- server-side guardrails

---

## `R4` Reference Firmware Baselines And Artifact Contract For Both Boards

### What this item actually entails

This item makes "known-good firmware" concrete and shareable.

### Included work

- pick one blessed reference source tree per board
- define one build command per board
- define the output artifact set per board
- ensure debug-symbol-bearing artifacts exist
- define where recovery artifacts live
- define the initial expected UART behavior of the reference image
- keep tracked board YAML hardware-focused while the reference firmware path is
  still supplied to Stage 0 as a runtime argument

### Concrete outputs

- one reference firmware source tree per board
- one repeatable build path per board
- canonical ELF and flashable artifact locations
- initial UART expectations documented
- a documented runtime handoff from Stage 0 to the selected reference artifact,
  without moving artifact paths into tracked board YAML

### Questions this item must answer

- What exact firmware is the baseline?
- Which artifacts are required by later tooling?
- Which artifact is flashed?
- Which artifact is used for symbol resolution?
- What is the recovery image and where does it live?
- How does Stage 0 receive the chosen reference artifact without turning
  artifact paths into tracked board-config fields?

### Definition of done

`R4` is done when every developer and every later component can point to exactly one baseline artifact set for each board.

### What it does not include

- bug variants beyond the baseline setup
- agent evaluation yet
- storing reference firmware paths in tracked board YAML

---

## `R5` Board Schema, Loader, And Local Override Model

### What this item actually entails

This item defines how the project represents board facts and how local machine attachment facts are layered on top.

### Included work

- define the YAML schema for tracked board config
- implement one loader/validator
- keep tracked board YAML hardware-focused and ban free-form recover command injection
- model recover selection as typed board data such as `recover_mode`
- define local override format for:
  - preferred probe UID
  - preferred serial-port override or matching hints
- define config precedence
- make malformed board files fail loudly

### Concrete outputs

- board YAML files for both boards
- one config loader module
- one local override convention such as `.env` plus optional
  `pyocd.local.yaml`, with documented precedence

### Questions this item must answer

- What fields are required for every board?
- Which fields are machine-local and must stay untracked?
- How does the runtime merge defaults, board config, and local overrides?
- How are invalid configs reported?
- Which recovery semantics belong in tracked board data versus code and later server guardrails?

### Definition of done

`R5` is done when every component gets board data through one validated loader instead of parsing config its own way.

### What it does not include

- actual UART or SWD control logic

---

## `R6` UART Adapter And Serial Discovery Contract

### What this item actually entails

This item creates the serial/UART code and its behavior contract.

### Included work

- define adapter method signatures
- define blocking vs bounded-read behavior
- define buffering and newline handling
- define reopen behavior after reset/reflash
- define error handling for disappearing ports
- implement shared UART helper/service behavior above the raw adapter so local
  flows and MCP tools do not fork their own capture/wait/reopen logic
- implement serial-port discovery and selection using config, vendor-assisted
  helpers where proven, and local overrides
- make ambiguity handling explicit: prompt in interactive runs, fail with a
  `--port BOARD_ID=PORT` rerun hint in non-interactive runs
- validate behavior on both macOS and Windows

### Concrete outputs

- UART adapter module
- UART-specific tests or harness coverage
- serial discovery and selection logic
- documented UART semantics

### Questions this item must answer

- What does `read_lines()` or equivalent actually mean?
- How long does a read wait?
- What happens to partial lines?
- What happens if the board disconnects and re-enumerates?
- How do we pick the correct port on a machine with many ports?
- When should the runtime prompt for human port selection instead of guessing?

### Definition of done

`R6` is done when UART access is reliable enough to be used as a substrate for smoke tests and later convergence logic.

### What it does not include

- SWD logic
- MCP server wrapping

---

## `R7` SWD Interface And pyOCD Backend For Both Boards

### What this item actually entails

This item creates the abstract hardware control API and its pyOCD implementation.

### Included work

- define SWD interface methods
- decide connection lifecycle behavior
- decide reset semantics
- implement flash support
- implement halt/resume
- implement register reads
- implement memory reads
- implement board-specific locked-target detection
- expose those capabilities through shared internal operations that later MCP
  handlers and local programmers both call
- implement native-default-with-CMSIS-DAP-fallback routing: try the board's native `probe_family` route
  first, automatically fall back to CMSIS-DAP on failure, and surface which route was used
- handle the J-Link open quirk: set pyOCD `jlink.non_interactive=false` so pylink's
  `disable_dialog_boxes()` does not clear the USB emulator selection (else open-by-serial fails with
  "No emulator with serial number ... found"); verified with pyOCD 0.44.1 + pylink 1.7.0 + J-Link DLL
  V9.50, reconfirm on version changes
- keep the interface board-agnostic even if the backend has board quirks

### Current-state reconciliation (COMPLETED 2026-06)

> This section is historical. The reconciliation below is **done**: the API path was proven on
> hardware, `adapters/`+`services/` were stood up, and both `stage0_check.py` and `server.py` are
> now thin callers over the shared services. The text is kept as the record of how the migration
> was sequenced.

The repo (at the time this was written) had TWO independent pyOCD callers, which this item had to
collapse, not extend:

- `stage0_check.py` drives pyOCD by **subprocess** (`pyocd cmd`, `pyocd load`,
  `pyocd erase --mass`) and is the **only** target-control path validated on real hardware.
- `src/pyocd_debug_mcp/server.py` drives pyOCD via the **Python API** and is **not yet
  validated on hardware**.

The ordered work that turns this into one validated service layer (full detail in build-plan
Step 1.0d):

1. **Prove the Python-API path on hardware first (de-risk).** Reproduce stage0's proven
   target-control ops through the pyOCD API in a throwaway script — connect → read silicon-ID,
   then flash and recover — oracle'd against the subprocess output. STM32 first (no J-Link open
   quirk); carry the `jlink.non_interactive=false` workaround onto the API path for the nRF.
2. **Fix before migrate — never migrate red code.** Fix the calls `server.py` already has
   (connect/read) in place when trivial, in the script when not; get green on the bench first.
3. **Write the proven calls directly as services** in `adapters/` + `services/` (the Step 1.0
   layout, created here), hand-tested per-operation. Do not build new ops into `server.py` and
   relocate them — write `flash`/`recover`/`read_serial` straight into services.
4. **Thin both wrappers onto the services (the migration).** `server.py` tools and
   `stage0_check.py` target-control calls become thin callers; the J-Link workaround ends up in
   exactly one place. Incremental and per-operation, not a single phase after parity.

Scope: only target-control ops (`connect`, `read_memory`/silicon-ID, `flash`, `recover`,
`halt`/`reset`/`resume`) need this. Probe enumeration, serial discovery, and pack checks stay.

**Probe-abstraction discipline (when only one probe family is on the bench).** This work is done
J-Link-first, and the STM32/ST-Link board may not be present while the service layer is built.
Keep probe specifics — the J-Link `jlink.non_interactive=false` option, native-vs-CMSIS-DAP
routing, locked-target handling — routed through `board_config` / the probe backend, **never as
scattered `if probe == ...` branches** in the service or wrapper layers (the code already applies
the J-Link option conditionally from `board.probe_family` — keep that pattern). Building with only
J-Link present puts the burden on the author to keep ST-Link assumptions out, since they cannot yet
be tested; this discipline is what makes the eventual STM32/ST-Link bring-up a **drop-in** rather
than a rewrite, and turns the STM32 into a verification of the abstraction instead of a trigger to
redesign it.

### Concrete outputs

- abstract SWD interface module
- pyOCD backend module
- per-board backend configuration through board data, not branches
- a throwaway API-validation reproduction (oracle'd against the subprocess path), then deleted
- `stage0_check.py` and `server.py` reduced to thin wrappers over the shared services

### Questions this item must answer

- Is `connect()` explicit or lazy?
- What does `flash()` accept?
- What reset style is canonical?
- How are register names represented?
- How is locked nRF behavior surfaced distinctly from normal connection failure?

### Definition of done

`R7` is done when both boards can be controlled through the same SWD interface without higher layers knowing which probe family they are using.

### What it does not include

- vendor GDB backends
- MCP server wrapping

---

## `R8` Symbol Resolution And Stage 1 Smoke Harness

### What this item actually entails

This item proves the Stage 1 substrate works as a whole.

### Included work

- add ELF pairing support to the SWD side
- implement symbol resolution
- define one or more known symbols in the reference firmware
- build the first shared board-validation operations that compose SWD + UART
  behavior instead of leaving that composition trapped inside one script
- write a repeatable smoke harness that:
  - connects
  - flashes
  - halts
  - reads a register
  - resolves a symbol
  - reads UART output

### Concrete outputs

- symbol resolution support
- Stage 1 smoke harness script or test
- expected outputs for both boards

### Questions this item must answer

- How do flashed artifacts pair with ELF files?
- What known symbol proves symbol resolution works?
- What exact harness proves Stage 1 is green?

### Definition of done

`R8` is done when the Stage 1 smoke harness passes on both boards and the team can say the direct board-control substrate is real.

### What it does not include

- MCP server
- agent integration

---

## `R9` stdio FastMCP Server, Tool/Resource Schema, And Inspector Validation

### What this item actually entails

This item turns the direct adapters into an agent-consumable protocol surface.

### Included work

- define exact server startup shape
- wire the adapters into a FastMCP server
- make MCP handlers thin wrappers over shared board-control operations
- **thin the existing `server.py` spike onto the R7 services, do not extend it in place.**
  `server.py` already exists as a working FastMCP server built directly on the pyOCD Python API,
  ahead of the R6-R8 substrate. Its tools (connect/halt/resume/step/reset/read*/breakpoints) are
  rewired to call the shared services, and the operations it lacks (`flash_firmware`,
  `read_serial`, `unlock_recover`) are added as thin wrappers over services written in R7/R8 —
  never reimplemented in the handler.
- choose the tool/resource split
- define response schema conventions
- define board-selection/config flow
- validate every tool/resource in MCP Inspector

### Concrete outputs

- local stdio MCP server
- defined tool/resource contract
- Inspector validation checklist and results

### Questions this item must answer

- Which operations are tools and which are resources?
- How are outputs structured?
- How is the correct board chosen?
- How are schema errors caught before real client integration?

### Definition of done

`R9` is done when the local MCP server works end-to-end in the Inspector against both boards.

### What it does not include

- guardrails
- benchmark suite
- turnkey brain

---

## `R10` Guardrails: Flash Gate, Unlock Gate, Logging, Session Store, And Convergence Watcher

### What this item actually entails

This item implements the server-side safety system.

### Included work

- define and implement image validation before flash
- define and implement explicit gated unlock/recover behavior
- disable unsafe silent unlock paths in normal server operation
- keep those flash/unlock guardrails in shared internal code so every mutation
  path, not just MCP wrappers, inherits the same policy
- define and implement structured log schema
- define and implement session-state storage abstraction
- implement deterministic convergence-thrash detection
- define how blocked actions are reported

### Concrete outputs

- flash gate module
- unlock/recover gate module
- structured logging implementation
- session store abstraction and initial backend
- convergence watcher implementation

### Questions this item must answer

- What exactly counts as a valid flashable image?
- When is unlock/recover permitted?
- What gets logged, and at what severity?
- What exact signals count as repetition, oscillation, or non-shrinking failure?
- What happens when the watcher blocks further action?

### Definition of done

`R10` is done when the MCP server can refuse unsafe actions and can stop obviously non-converging loops in a deterministic way.

### What it does not include

- the external-agent benchmark itself
- the turnkey brain

---

## `R11` BYO-Agent Benchmark Suite And Product #1 Validation

### What this item actually entails

This item proves the first product in realistic conditions.

### Included work

- define injected-bug cases for both boards
- define wiring-fault cases
- define success criteria and scoring
- define transcript/log capture requirements
- run the benchmark against a real external agent client
- document failure modes and false-positive/false-negative patterns

### Concrete outputs

- benchmark suite
- pass/fail rubric
- captured runs and reports
- evidence that product #1 works or does not yet work

### Questions this item must answer

- Can an external agent use the MCP server to debug real cases?
- Does the server distinguish physical faults from code faults well enough?
- Do the safety and convergence protections work under a real client?
- What is the product's actual win rate and failure pattern?

### Definition of done

`R11` is done when the team can honestly say the BYO-agent product has been proven on real benchmark cases.

### What it does not include

- your own premium brain and CLI

---

## `R12` Turnkey Brain, Skills, CLI, And Acceptance Benchmark

### What this item actually entails

This item builds the premium product tier on top of the proven substrate.

### Included work

- implement the turnkey brain as an MCP client of the server
- define prompt/orchestration loop structure
- implement skills loading and selection
- implement brain-level convergence/self-evaluation logic
- build the CLI
- define the acceptance benchmark for product #2

### Concrete outputs

- brain implementation
- skills data shape and initial skill sets
- CLI frontend
- product #2 benchmark results

### Questions this item must answer

- What internal state does the brain track?
- How are skills selected?
- What does the CLI expose?
- In what way is the turnkey product better than the BYO-agent product?

### Definition of done

`R12` is done when the turnkey CLI can drive the full loop on either board and demonstrates a meaningful premium advantage.

### What it does not include

- remote hosting and scale
- high-rung autonomy experiments

---

## `R13` Scale And Remote Transport

### What this item actually entails

This item handles later operational scaling and optional hosted paths.

### Included work

- define how multiple board/server pairs are launched and named
- define how logs and sessions are partitioned
- add coordination only for shared resources if needed
- add optional remote/hosted transport and auth boundaries later

### Concrete outputs

- multi-board operating model
- remote topology design and implementation if pursued
- auth boundary documentation for hosted mode

### Questions this item must answer

- How do multiple boards operate without stepping on each other?
- What state and logs belong to which session?
- What trust boundary exists in remote mode?

### Definition of done

`R13` is done when the project can scale beyond one simple local pair without collapsing into shared-state confusion.

### What it does not include

- proving the MVP
- replacing the local-first development model

---

## `R14` Vendor GDB Backends

### What this item actually entails

This item adds optional alternate probe-control paths when pyOCD is not enough.

### Included work

- define the trigger conditions for vendor backend work
- implement a backend using vendor GDB server processes if required
- keep the same abstract SWD interface
- report optional capability differences cleanly upward

### Concrete outputs

- one or more vendor backend implementations
- capability matrix against the pyOCD backend

### Questions this item must answer

- What exact pyOCD limitation justifies this work?
- Which board needs it first?
- How does the product choose the backend?

### Definition of done

`R14` is done when a justified board capability gap has been closed without changing higher layers.

### What it does not include

- mandatory rewrite of the core architecture

---

## `R15` Capability Ladder Experiments

### What this item actually entails

This item is the structured post-MVP expansion track.

### Included work

- define the ladder rungs and benchmark tasks
- run experiments from:
  - bug fixing
  - driver modification
  - driver authoring
  - board bring-up
  - simple scheduler work
  - later harder autonomy tasks
- measure convergence boundaries honestly

### Concrete outputs

- capability-rung benchmark corpus
- experiment reports
- evidence-backed product-boundary claims

### Questions this item must answer

- How far can the system go before convergence breaks down?
- Which observability channels matter most at each rung?
- Which claims are product-real and which are still research?

### Definition of done

`R15` is never "done" in the same way as the earlier items. It is an ongoing experimental program built on top of a stable product substrate.

### What it does not include

- the initial product critical path

## The Gates

The roadmap has explicit gates so the team does not mistake partial progress for stable foundations.

### `G0` Team Protocol Frozen

This means `R0` is done.

### `G1` Stage 0 Proven On Both Boards

This means `R2` and `R3` are done in a real bench sense.

### `G2` Repo And Schema Frozen For Stage 1

This means `R1` and `R5` are stable enough for adapter work.

### `G3` Stage 1 Pass

This means `R6`, `R7`, and `R8` together prove direct board control is real.

### `G4` Stage 2 Pass

This means `R9` is done and the MCP server is validated.

### `G5` Stage 3 Pass

This means `R10` is done and the safety/runtime substrate is trustworthy.

### `G6` Stage 4 Pass / Product #1

This means `R11` is done and the BYO-agent product is real.

### `G7` Stage 5 Pass / Product #2

This means `R12` is done and the turnkey product is real.

## Rolling Frontier Staffing Through `R10`

The clear-scope part of this project should not use permanent ownership.

Instead, use a rolling frontier model through `R0-R10`, then replan after `G5` based on what actually turned out to be hard.

That means:

- through `R0-R10`, everyone should always have active work
- ownership is temporary and phase-based
- each roadmap item can have a lead without creating a permanent silo owner
- after `G5`, `R11-R15` should be replanned based on real execution evidence rather than early guesses

This is a better fit for this roadmap because:

- the work through `R10` is concrete enough to split now
- many of the dependencies are partial, not total, so only some sub-packets are blocked at a time
- the later roadmap items are too variable to assign credibly before the earlier substrate is proven

### Why The Old Static Split Causes Idle Time

The old ownership split creates predictable planning problems:

- one person can end up waiting for board bring-up before starting meaningful work
- one person can inherit a giant later package such as `R12` and become overloaded much later
- one person can finish a narrow early package and have too little to do while others sit on the critical path
- too much work gets grouped into large roadmap items instead of overlapping sub-packets

The core issue is that roadmap items are not equal-sized, and many of them naturally split into:

- bench truth
- interface definition
- automation and harness work
- integration and polish work

Once the work is split that way, the project parallelizes much more cleanly.

### Planning Principle

**Freeze interfaces early, not ownership early.**

This means:

- keep the architecture disciplined
- keep the quality bars disciplined
- let staffing move with the bottleneck

That gives the team both lower idle time and less long-term architectural damage.

### Operating Rules Through `R10`

- Each phase has one lead on the active bottleneck.
- Each phase has one lead on the next dependency that can already be prepared.
- Each phase has one lead on automation, harnesses, or hardening around the current work.
- Nobody should be blocked for more than one day without switching to a ready backup task.
- No one should work more than one phase ahead speculatively.
- Large items such as `R7`, `R9`, and `R10` should be split internally into smaller parallel sub-parts.

This gives the team continuous motion without encouraging random speculative work.

### Phase A: Foundation Setup

Goal:
Get the repo, toolchain, and work surfaces ready so real hardware work can start immediately.

- `Person 1`: `R0` Python version, venv policy, dependency install flow, and local override policy
- `Person 2`: `R1` repo skeleton, `pyproject.toml`, canonical layout, and root README
- `Person 3`: draft `R5` board-schema shape, improve `stage0_check.py` toward the new Stage 0 expectations, and prepare the reference-firmware candidate list for both boards from `R4`

Why this works:

- no one is blocked
- two people build the shared substrate
- the third person gets ahead on the first hardware-adjacent support work without waiting for bench truth

### Phase B: Stage 0 Bring-Up On Both Boards

Goal:
Prove the boards and toolchains are real.

- `Person 1`: `R2` STM32 bring-up
- `Person 2`: `R3` nRF bring-up
- `Person 3`: finish the `R5` loader and local-override model using real findings as they arrive, keep improving `stage0_check.py`, and curate the reference firmware artifacts and build instructions for `R4`
- **Pull-forward prep (whoever has slack, or a board-bring-up lead who stalls): the pyOCD
  Python-API de-risk.** As soon as a board is up on the bench (the first half of Phase B), prove
  the pyOCD *Python API* can do what stage0's subprocess path already does — connect → read →
  flash → recover — via a throwaway reproduction, STM32 first, oracle'd against the subprocess
  output (build-plan Step 1.0d). This is the "next dependency that can already be prepared": it
  needs only Stage-0 hardware truth (which Phase B is establishing) plus the existing `server.py`,
  and it removes the single biggest unknown blocking `R7`. If it passes, Phase C starts the SWD
  service on known-good substrate; if it fails, the team learns it now instead of mid-`R7`.

Why this works:

- two people attack the biggest uncertainty directly
- the third person converts raw bench discoveries into shared structure and tooling
- if one board path stalls, that person can temporarily help the other bench path or refine automation
- the API de-risk is cheap and only needs a working bench, so pulling it into Phase B means the
  `R7` substrate question is answered before Phase C commits to the SWD interface

### Phase C: Stage 1 Substrate Split

Goal:
Build the first real code substrate.

**Phase-C entry gate (blocks the rest of `R7`): the pyOCD Python-API path must be proven on
hardware before the SWD service is built.** Ideally this was already cleared as the Phase-B
pull-forward task; if so, Phase C confirms it still holds and proceeds. If Phase B did not get to
it, it is the first thing Phase C does, before any adapter/service is written — a throwaway
reproduction oracle'd against `stage0_check.py`'s subprocess output (see `R7` "Current-state
reconciliation" and build-plan Step 1.0d). Either way it is a ~half-day de-risk that decides
whether the service layer is built on the API or needs a different approach — STM32 first.

- `Person 1`: ensure the **API-validation gate is green** (run it now if Phase B didn't —
  throwaway repro: connect → read → flash → recover through the pyOCD API, STM32 first, J-Link
  workaround carried over; fix-before-migrate any wrong calls), THEN build the `R7` SWD interface
  skeleton + STM32 backend as the first real
  services in `adapters/`/`services/`
- `Person 2`: `R6` UART adapter and serial discovery behavior, written as a service from the
  start (lift `stage0_check.py`'s inline UART capture into the shared layer, do not leave it in
  the script)
- `Person 3`: finalize `R4` artifact contract and reference baseline structure, then start `R8` smoke-harness scaffolding and the symbol-resolution contract

Why this works:

- SWD, UART, and artifact or harness work can all progress in parallel
- none of these sub-packets require all of Stage 1 to be finished before starting
- this avoids making one person own all observability work alone
- the API-validation gate keeps `Person 1` from pouring the SWD service onto an unproven
  substrate; if it fails, the team learns it before the interface is committed

### Phase D: Stage 1 Close And Stage 2 Open

Goal:
Finish Stage 1 cleanly and start wrapping it in the first server surface.

- `Person 1`: extend `R7` to the nRF backend and locked-target semantics (this is where the
  J-Link open quirk and APPROTECT/recover path get proven through the API, not just subprocess)
- `Person 2`: **thin the existing `server.py` spike onto the `R7` services** rather than build a
  greenfield shell — rewire its existing tools to call the shared services, add the missing
  `flash_firmware`/`read_serial`/`unlock_recover` as thin wrappers, then do `R9` config
  integration and response-schema conventions on that base
- `Person 3`: complete the `R8` smoke harness, integrate symbol resolution into the harness,
  harden `R6` UART behavior based on real runs, AND **migrate `stage0_check.py`'s target-control
  calls from subprocess to the shared services** (the second half of the convergence — when done,
  the J-Link workaround lives in exactly one place)

Why this works:

- once STM32 substrate behavior is real, the MCP shell can start
- the harness work closes Stage 1 with actual evidence instead of ad hoc confidence
- the nRF backend finishes the real both-boards requirement
- thinning `server.py` and `stage0_check.py` onto the services in this phase is what actually
  retires the two-parallel-implementations problem, instead of leaving it for "later"

### Phase E: Stage 3 Split Into Three Parallel Streams

Goal:
Build the safety and runtime substrate without making one person own all of `R10`.

Use internal staffing labels `R10a`, `R10b`, and `R10c`. These are not new roadmap IDs. They are sub-packets used to parallelize `R10`.

- `Person 1`: `R10a` board-aware safety rules, flash constraints, unlock and recover policy behavior, and board-specific refusal scenarios
- `Person 2`: `R10b` runtime safety infrastructure, refusal protocol, logging schema, session identity, session-store abstraction, and server enforcement wiring
- `Person 3`: `R10c` watcher signal quality and validation, failure-signature structure, convergence test corpus, and validation harnesses for noisy versus clean signals

Why this works:

- `R10` is too large to sit under one owner if the goal is throughput
- this split maps naturally to hardware semantics, runtime mechanics, and evidence quality
- everyone stays on active work while still converging on one milestone

### What Happens When Someone Gets Blocked

If a person is blocked for more than one day, that person should not wait. They should switch to a ready backup task from the same phase.

Good backup tasks include:

- improve `stage0_check.py`
- refine board-YAML validation
- document observed probe quirks
- harden serial detection
- build smoke-harness scaffolding
- prepare benchmark case format
- draft log and event schema
- add fixture-folder structure
- capture known-good outputs from successful board runs

The rule is:

No one waits for a dependency if there is a nearby artifact, harness, config, or automation task that makes the same milestone easier.

That is how the team keeps everyone productive without drifting too far ahead.

### What Not To Do

There are two bad extremes:

- permanent silos, where one person waits while another owns the active blocker
- unbounded task grabbing, where people work too far ahead, interfaces churn, and rework grows

So the project still needs discipline:

- temporary lead for each active item
- small parallel sub-packets
- no speculative work more than one phase ahead
- weekly replanning

### Weekly Frontier Planning

Run the clear-scope part of the roadmap as a weekly frontier plan.

At the start of each week, decide:

- what is the current bottleneck
- what is the next dependency that can already be prepared
- what can be automated or hardened now from work that just landed

Then assign:

- one person to bottleneck lead
- one person to next-up preparation
- one person to hardening, validation, or automation

That rotation should shift naturally over time:

- early weeks favor hardware bring-up
- middle weeks favor substrate work and MCP wrapping
- later clear-scope weeks favor guardrails and validation

This is healthier than static ownership because it keeps staffing aligned with the real frontier instead of the original guess.

### Is This More Equal

Yes, much more equal through the clear-scope portion of the roadmap.

It will not be perfectly equal every week, but it is much more balanced overall because:

- early hardware spikes are balanced by parallel tooling and schema work
- middle substrate spikes are balanced by harness and artifact work
- `R10` no longer sits as one giant monolith under one person

Through `R0-R10`, the workload can stay fairly even if the team uses the phase-based split above.

After `G5`, the team should still replan dynamically.

### After `G5`

Do not assign permanent owners for `R11-R15` now.

Those later items should stay intentionally flexible until `G5` because the real shape of the remaining work depends on what earlier execution reveals about:

- benchmark rigor gaps
- MCP and runtime stability gaps
- board-specific safety complexity
- backend-portability difficulty
- hosted-state and multi-board coordination complexity

The right time to divide `R11-R15` is after the team has real evidence from `R0-R10`, not before.

### Bottom Line

If the priority is to keep all three people productive through the clear-scope part of the project, then:

- do not use permanent track ownership
- do not assign huge later roadmap items now
- split the clear-scope work into overlapping sub-packets
- rotate staffing around the current frontier
- keep `R11-R15` intentionally flexible until `G5`

That is the version of the roadmap this document recommends executing.

## Short Summary

If you want the shortest useful mental model, the roadmap is this:

1. Standardize the development environment.
2. Prove both boards by hand.
3. Freeze repo layout and board schema.
4. Build and prove the UART + SWD adapter substrate.
5. Wrap that substrate in a local MCP server.
6. Add server-side safety and anti-thrash controls.
7. Prove the first real BYO-agent product with benchmarks.
8. Build the premium turnkey brain + CLI product.
9. Only then add scale, alternate probe backends, and higher-autonomy experiments.

That is the entire project, translated from stage language into execution language.
