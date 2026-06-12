# Firmware Agent Build Plan: Step-By-Step Specification Gaps

This document is a step-indexed pass over the build plan.

For each stage item, it answers one question:

What still needs to be defined so implementation becomes clear-cut instead of turning into more design work during coding?

Reviewed sources:
- `firmware_agent_build_plan_concrete (3).md`
- `firmware_agent_mcp_architecture.md`

## Cross-Cutting Definitions To Lock Before Stage Work

These are not individual stage items, but they affect nearly every stage below.

### X.1 Supported environment
Needs clarification:
- whether v1 is Windows-only, Windows plus Linux, or cross-platform
- supported Python version range
- pinned or minimum versions for `pyocd`, `pyserial`, `mcp`, and Redis
- whether development environment support and shipped-product support are intentionally different

What should be defined:
- one explicit support matrix table
- one bootstrap document or script per supported host OS

Why this matters:
- USB detection, COM-port mapping, driver instructions, process launch, and packaging all depend on OS decisions
###  ADRESSED ABOVE! #############

### X.2 Repository and artifact layout
Needs clarification:
- where board configs live
- where known-good firmware artifacts live
- where reference firmware source trees live
- where injected-bug variants live
- where logs live
- where recovery images live
- where session-state config lives

What should be defined:
- one canonical directory layout
- one artifact naming convention shared by all later tooling

Why this matters:
- otherwise `flash_firmware`, `apply_patch`, bug injection, and recovery-image logic will all invent different path conventions

###  ADRESSED ABOVE! #############

### X.3 Board configuration schema
Needs clarification:
- whether board configuration is Python, YAML, JSON, or TOML
- what fields are mandatory for every board

What should be defined:
- a concrete schema with fields like:
  - `board_id`
  - `display_name`
  - `mcu_family`
  - `probe_family`
  - `pyocd_target`
  - `probe_discovery_hints`
  - `serial_discovery_hints`
  - `serial_baudrate`
  - `flash_artifact_type`
  - `reference_uart_patterns`
  - `recover_mode` as a typed selector, not a free-form recover command
  - `memory_protection_rules`
  - `register_aliases`

Artifact locations should be frozen by repo layout and naming rules instead of
tracked board-config fields in Phase A. That means canonical reference and
recovery paths belong under `firmware/<board>/...`, not in board YAML.

Why this matters:
- if board knowledge is not formalized as data, later "multi-board" support will collapse back into code branches

### X.4 Error model
Needs clarification:
- how low-level hardware failures are represented
- how user mistakes are represented
- how safe refusals are represented
- how watcher blocks are represented

What should be defined:
- a standard error taxonomy
- a stable set of error codes or categories
- a rule for what goes into human-readable text versus machine-readable metadata

Why this matters:
- the server, the watcher, the brain, and Claude Code need to distinguish "probe missing", "board locked", "unsafe flash refused", and "patch failed" in consistent ways

### X.5 Logging and event schema
Needs clarification:
- exact log format
- exact event names
- correlation ID scheme
- retention and redaction policy

What should be defined:
- a structured event schema shared across Stage 2 through Stage 5
- one event ID and session ID policy

Why this matters:
- logs feed the watcher, debugging, support, and future analytics

## Stage 0: Foundations

### 0.1 Confirm each board's pyOCD target name
What is still underspecified:
- the exact accepted target string for each board
- whether family aliases are acceptable or forbidden
- whether the script accepts "close enough" targets or insists on one canonical target
- whether target-pack installation should be automatic, guided, or manual only
- what package source is trusted for target packs

What should be clarified:
- one exact canonical `pyocd_target` per board
- one fallback/alias list if aliases are intentionally allowed
- whether the tool should hard-fail if it only finds `cortex_m` or a family-level target
- whether pack installation is part of the tool flow or a precondition

What code becomes easier once this is defined:
- board validation
- helpful error messages
- pack bootstrap automation
- flash preflight checks

### 0.2 Probe-specific setup

**RESOLVED (2026-06-11, user sign-off — see the driver sidebar DECISION in `build_plan_concrete`):**
the probe route is **the board's native probe family by default, with CMSIS-DAP as the fallback** (and
as the default only for boards whose native family is CMSIS-DAP). The native J-Link path is a
**supported runtime path**, not merely a dev convenience, because the Nordic DK's onboard J-Link OB does
not expose CMSIS-DAP unless explicitly switched into it — so a CMSIS-DAP default would fail it. CMSIS-DAP
remains fully supported: everything must work through it, and it is the automatic fallback when the
native route fails. The items below are kept as the original gap record.

What was underspecified (now resolved per the decision above):

- the nRF probe route to standardize on during development → native SEGGER J-Link, CMSIS-DAP fallback
- the route to standardize on for the shipped product → per-board native default, CMSIS-DAP fallback
- whether native J-Link support is merely a dev convenience or a supported runtime path → supported runtime path
- whether ST-Link setup assumes vendor drivers, generic drivers, or both → native ST-Link default, CMSIS-DAP fallback
- whether WinUSB/Zadig is ever considered part of the happy path → only for probes whose native/fallback route is CMSIS-DAP

Decision recorded:

- primary route: the board's native probe path (`probe_family`)
- the other path (CMSIS-DAP) is: **fallback-only** (and the default where a probe is natively CMSIS-DAP)
- define the Windows driver story for each supported probe family
- define whether the tooling detects driver state or merely infers likely causes from probe visibility failures

Why this is the Stage 0.2 implementation note:
- Stage `0.2` is not algorithmically hard, but it is not fully specified enough yet to be clean to implement
- once the probe path and driver policy are fixed, the code is mostly subprocess wrappers, device detection, and board-specific instructions
- without those decisions, the Python is easy to write syntactically but ambiguous in behavior

What should be defined to make implementation straightforward:
- supported host OS for the Stage `0.2` tooling
- chosen nRF probe path during development
- chosen probe path for the shipped product
- whether the script may perform destructive recover operations
- whether missing-driver diagnosis is best-effort or authoritative
- how multiple connected probes are handled

### 0.3 Confirm one USB cable yields both debug probe and virtual COM port
What is still underspecified:
- how COM ports are discovered
- how a COM port is matched to a specific board when multiple devices are present
- whether the tool relies on USB VID/PID, interface names, serial numbers, or user-provided port selection
- how long the tool waits for a VCP to enumerate after reset or flash

What should be clarified:
- one serial-port discovery strategy per OS
- one mapping strategy from probe to VCP
- one timeout/retry policy for USB re-enumeration
- one rule for "ambiguous ports found"

What code becomes easier once this is defined:
- UART adapter initialization
- reconnect-after-flash logic
- stage validation scripts

### 0.4 Get a known-good reference firmware per board
What is still underspecified:
- exact source project per board
- exact build system per board
- exact artifact type to flash
- exact UART output expected from the reference image
- whether the reference image must embed known symbols for later Stage 1.3 checks
- whether the reference image also doubles as the Stage 3 recovery image

What should be clarified:
- one blessed source tree per board
- one blessed build command per board
- one blessed output artifact per board
- one UART success pattern per board
- one list of known symbols guaranteed to exist in debug builds

What code becomes easier once this is defined:
- flash verification
- UART verification
- symbol-resolution tests
- injected-bug fixture generation

### 0.E Exit criteria for Stage 0
What is still underspecified:
- whether Stage 0 proof is manual only or partly automated
- exactly what evidence counts as "reference firmware flashes and prints by hand"
- whether nRF recover proof must be demonstrated every time or only once per bench setup

What should be clarified:
- a repeatable Stage 0 checklist
- what outputs to capture
- whether `stage0_check.py` is advisory, required, or just a convenience

## Stage 1: Adapters, Hand-Tested In Isolation

### 1.1 UART adapter
What is still underspecified:
- exact method signatures
- whether `read_lines()` is blocking, polling, or bounded blocking
- timeout behavior
- read buffering behavior
- encoding assumptions
- line termination handling
- behavior on partial lines
- behavior when the port disappears mid-read
- semantics of `reopen()`

What should be clarified:
- whether the adapter is snapshot-based or stream-based
- whether `read_lines()` means:
  - "read everything available now"
  - "block until at least one line"
  - "collect for N seconds"
- the retry/backoff policy for `reopen()`
- whether UART reads return raw bytes, decoded strings, or structured line objects

What code becomes easier once this is defined:
- MCP `read_serial`
- failure-signature extraction
- serial-based test assertions
- reset/reflash reconnect handling

### 1.2 SWD adapter interface plus pyOCD backend
What is still underspecified:
- exact interface signatures
- exact return types
- connection ownership and lifecycle
- whether the adapter is stateful across calls
- what artifact type `flash()` accepts
- reset semantics
- halt semantics
- read-memory width and alignment rules
- register naming rules
- symbol-resolution placement in this interface versus a separate symbol service

What should be clarified:
- whether `connect()` is explicit or implicit on first use
- whether `flash()` accepts:
  - filesystem path
  - bytes
  - artifact object with metadata
- whether `reset_and_halt()` means hardware reset, software reset, or best available
- whether `read_register()` accepts architecture names like `pc`, `sp`, `lr`, raw indices, or both
- whether the adapter returns board-neutral data structures or pyOCD-shaped objects

What code becomes easier once this is defined:
- backend swapping
- MCP wrapping
- consistent exception handling
- stage-test harnesses

### 1.2.nRF Locked-chip behavior
What is still underspecified:
- whether lock detection happens during `connect()`, `flash()`, or any access failure
- how a locked nRF is surfaced distinctly from a disconnected target
- whether `recover` is an adapter method, an out-of-band utility, or part of `flash()`

What should be clarified:
- one dedicated locked-chip error category
- whether recover is:
  - manual only
  - separate explicit adapter method
  - optional helper behind an explicit flag

What code becomes easier once this is defined:
- Stage 0 recover proof
- Stage 3 safe recovery flows
- user-facing diagnostics

### 1.2 Build-order smoke tests
What is still underspecified:
- exact commands or calls used for `connect -> read register -> flash -> halt -> read PC`
- which register is used for the first smoke test
- what counts as success for `read PC`
- whether success thresholds differ by board

What should be clarified:
- a precise per-board Stage 1 smoke-test procedure
- one small script or REPL checklist that all developers use

### 1.3 Symbol resolution
What is still underspecified:
- required debug info format
- whether stripped or optimized builds are allowed
- how the ELF is located
- how symbol results are returned
- whether reading a symbol's current value belongs here or in `read_memory`

What should be clarified:
- one exact rule for artifact pairing between flashed image and ELF
- one exact symbol lookup API and result shape
- one required known symbol in reference firmware

What code becomes easier once this is defined:
- automated symbol tests
- MCP `resolve_symbol`
- bug-injection scenarios using globals

### 1.E Exit criteria for Stage 1
What is still underspecified:
- what "all by hand" means operationally
- whether a small script-driven harness still counts as hand-tested
- how intermittent hardware failures are judged

What should be clarified:
- one pass/fail checklist
- one set of expected outputs per board
- one retry policy before a bench is considered unhealthy

## Stage 2: Wrap Adapters As A Local MCP Server

### 2.1 FastMCP server, stdio transport
What is still underspecified:
- how the server process is started
- whether board selection is startup config or per-call input
- where config comes from
- how one stdio server instance is bound to a board

What should be clarified:
- exact server startup contract
- exact config precedence:
  - CLI flags
  - env vars
  - config file
  - defaults
- whether one process serves one board or can switch boards dynamically

What code becomes easier once this is defined:
- launch scripts
- Claude Code registration
- local bench workflows

### 2.1 Primitive split: tools versus resources
What is still underspecified:
- whether parameterized reads like `read_memory(address, length)` are really resources or should be tools
- what URI scheme or resource-template format is used if they stay resources
- whether read operations need side effects like establishing a connection, which complicates "resource" semantics

What should be clarified:
- exact MCP primitive choice for each operation
- if resources are kept, the exact URI or template schema
- whether there is a board/session namespace inside those URIs

What code becomes easier once this is defined:
- resource registration
- Inspector validation
- client-side consumption

### 2.1 Return types
What is still underspecified:
- what "typed text/content blocks" means concretely for this project
- whether outputs include machine-readable JSON encoded in text
- whether a stable response schema exists across tools

What should be clarified:
- one response envelope pattern for all tools
- one rule for success text versus structured metadata
- one rule for how errors are surfaced

What code becomes easier once this is defined:
- Claude Code integration
- turnkey brain parsing
- audit logging

### 2.1 Board selection
What is still underspecified:
- whether the server holds one board binding at startup
- whether the caller can name a board on each operation
- whether v1 supports multiple attached boards per process

What should be clarified:
- one process-topology decision for v1
- one board-identity model

Why this matters:
- this affects almost every tool signature

### 2.2 Validate every tool with the MCP Inspector
What is still underspecified:
- which exact tools/resources must be exercised
- the sample inputs for each
- the expected outputs for each
- the negative tests

What should be clarified:
- one Inspector validation checklist covering:
  - nominal tool calls
  - bad arguments
  - missing board config
  - missing probe
  - locked nRF

### 2.3 `apply_patch` design
What is still underspecified:
- what path roots are writable
- whether the tool can create files
- whether binary files are prohibited
- whether it can touch only firmware code or also tests and config
- how patch conflicts are detected
- whether patch application is atomic

What should be clarified:
- one explicit filesystem safety policy
- one exact request format for full-file rewrite
- one exact success/failure contract

What code becomes easier once this is defined:
- safe file editing
- watcher hashing
- reproducible bug-fix loops

### 2.4 Long-running operations
What is still underspecified:
- how the background worker is modeled
- whether there is one serialized queue per board
- cancellation semantics
- timeout semantics
- how serial capture and hardware actions interact during long calls
- whether progress is surfaced in v1

What should be clarified:
- one concurrency model
- one cancel model
- one timeout model
- one sequencing rule for flash/reset/read operations

What code becomes easier once this is defined:
- reliable tool execution
- responsive stdio server behavior
- clean Stage 3 watcher integration

### 2.E Exit criteria for Stage 2
What is still underspecified:
- what "every tool/resource works in the Inspector" means exactly
- what evidence is captured
- whether success is per board or combined

What should be clarified:
- one validation report template
- one minimum manual test matrix per board

## Stage 3: Deterministic Guardrails In The Server

### 3.1 Pre-flash safety gate
What is still underspecified:
- what counts as a valid image
- what memory regions are forbidden
- how fuse or option-byte writes are detected
- whether image target-family validation is enforced
- whether vector table, image size, checksum, and format are validated
- whether the gate is artifact-type-specific

What should be clarified:
- one board-specific image validation policy
- one forbidden-write map per board
- one exact refusal condition set

What code becomes easier once this is defined:
- `flash_firmware`
- refusal reporting
- recovery-image workflows

### 3.1 Recovery image requirement
What is still underspecified:
- what a recovery image is
- where it lives
- who blesses it
- whether it is per board, per firmware family, or per project

What should be clarified:
- one recovery-image lifecycle
- one rule for how the gate verifies the recovery image exists and is compatible

### 3.2 Session state in Redis
What is still underspecified:
- exact Redis key structure
- exact session ID source
- TTL policy
- persistence expectations
- local-dev fallback if Redis is absent

What should be clarified:
- one session identity contract
- one store API internal to the server
- one local-development stance:
  - Redis required always
  - Redis required for production only
  - pluggable store with Redis as default

What code becomes easier once this is defined:
- watcher implementation
- local testing
- future stateless migration

### 3.3 Behavioral convergence watcher
What is still underspecified:
- exact definition of repetition
- exact definition of oscillation
- exact definition of non-shrinking failure signature
- exact thresholds
- whether thresholds vary by task class
- what tool calls are watched

What should be clarified:
- one deterministic predicate set
- one threshold configuration policy
- one list of mutating actions subject to blocking

What code becomes easier once this is defined:
- watcher core logic
- unit tests
- end-to-end Stage 4 validation

### 3.3 Failure-signature model
What is still underspecified:
- what inputs comprise a failure signature
- how serial output is normalized
- whether register values are included
- whether timeouts, disconnects, and tool errors are included
- whether patch hash and flashed-image hash are tracked separately

What should be clarified:
- one concrete signature schema
- one normalization policy
- one hashing policy

### 3.3 Block behavior
What is still underspecified:
- whether the watcher blocks only flash-like actions or all mutating actions
- whether blocks are sticky
- how an operator clears a block
- whether the brain can ask for watcher state

What should be clarified:
- one refusal protocol
- one unblock/reset policy
- one read-only introspection tool or status resource if needed

### 3.4 Structured logging and audit
What is still underspecified:
- exact event names
- exact required fields
- whether raw serial is logged verbatim
- whether patch contents are logged verbatim, hashed, or summarized
- how privacy and storage volume are handled

What should be clarified:
- one event schema
- one payload-size policy
- one retention policy

### 3.E Exit criteria for Stage 3
What is still underspecified:
- what exact bad-image scenario is used
- what exact deliberately-unfixable loop is used
- how block success is verified
- what must be logged to count as success

What should be clarified:
- one Stage 3 validation suite
- one artifact and transcript capture rule

## Stage 4: Prove BYO-Agent Mode End To End

### 4.1 Register the server with Claude Code
What is still underspecified:
- exact registration command after docs verification
- exact command line for launching the server
- env vars needed by the server
- log capture approach during agent-driven sessions

What should be clarified:
- one blessed local integration command
- one example config snippet
- one troubleshooting guide for common registration failures

### 4.2 Run the injected-bug suite through Claude Code
What is still underspecified:
- exact bug cases
- whether bug cases are identical across boards
- where buggy variants live
- how each bug is introduced
- what counts as correct diagnosis
- what counts as correct fix

What should be clarified:
- one benchmark suite per board
- one expected-outcome description per bug case
- one result-capture format

What code becomes easier once this is defined:
- automated evaluation
- regression testing
- product demos

### 4.3 Run safety and convergence tests live
What is still underspecified:
- which Stage 3 scenarios are replayed here
- how agent transcripts are evaluated
- whether the agent is allowed hints
- whether retries are allowed

What should be clarified:
- one Stage 4 safety/convergence validation rubric

### 4.4 Wiring-fault test
What is still underspecified:
- which physical fault scenarios are in scope
- how they are introduced safely
- what evidence shows the agent recognized a physical fault rather than code fault
- whether all faults are expected to be classified correctly

What should be clarified:
- one wiring-fault matrix
- one expected symptom table
- one pass/fail rubric

### 4.E Exit criteria for Stage 4
What is still underspecified:
- how many bug cases must pass
- how many turns or retries are allowed
- whether partial success counts
- what artifacts must be preserved

What should be clarified:
- one benchmark score threshold
- one transcript/log retention rule

## Stage 5: The Turnkey Brain Plus CLI

### 5.1 Build the brain as a second MCP client
What is still underspecified:
- the brain loop state machine
- prompt construction
- tool-selection policy
- evidence-gathering policy
- stop conditions
- retry limits

What should be clarified:
- one orchestration contract
- one per-iteration data model
- one budget model for turns, patches, and flashes

What code becomes easier once this is defined:
- prompt assembly
- loop implementation
- convergence-aware orchestration

### 5.2 Add skills injection
What is still underspecified:
- exact file format
- exact schema
- how skills are indexed and selected
- whether skills are static data, generated summaries, or mixed
- update/versioning policy

What should be clarified:
- one formal skills schema
- one retrieval/selection rule
- one authoring and validation process

### 5.3 Add loop-aware convergence logic in the brain
What is still underspecified:
- how brain-level convergence differs from server-level thrash detection
- what internal state the brain tracks
- what signals trigger self-stop, ask-for-human, or pivot-in-strategy

What should be clarified:
- one separation-of-responsibility rule:
  - server watcher handles hard deterministic stops
  - brain logic handles softer strategy-level self-evaluation
- one state model for hypotheses and experiments

### 5.4 Build the CLI frontend
What is still underspecified:
- exact command names
- exact flags
- config precedence
- defaults for board, target, ports, ELF, tasks, and max-iters
- output format
- interactive versus non-interactive behavior

What should be clarified:
- one CLI spec
- one config file format if config files exist
- one output contract for humans and automation

### 5.5 Keys
What is still underspecified:
- how BYOK is supplied
- where it is stored
- how managed-mode credentials are selected
- what local versus hosted differences exist

What should be clarified:
- one credential-loading policy
- one secret-storage recommendation
- one separation between local config and hosted credentials

### 5.6 Closed-source boundary
What is still underspecified:
- what exactly runs on the customer machine
- what can remain remote
- whether the brain is ever shipped locally
- how the server and brain are deployed relative to each other

What should be clarified:
- one deployment topology for local-only mode
- one deployment topology for hosted/managed mode

### 5.E Exit criteria for Stage 5
What is still underspecified:
- what tasks the CLI must succeed at
- how turnkey performance is measured against BYO-agent mode
- what degree of autonomy is required for success

What should be clarified:
- one turnkey acceptance benchmark
- one comparison rubric against Stage 4

## Stage 6: Scale And Remote

### 6.1 Multiple boards equals multiple agent-server pairs
What is still underspecified:
- whether there is a supervisor process
- how pairs are launched
- how logs are partitioned
- how sessions are named
- whether one brain may coordinate several board-local servers

What should be clarified:
- one multi-board operating model
- one naming and lifecycle convention for board instances

### 6.2 Thin coordination for shared resources
What is still underspecified:
- what exactly counts as a shared resource
- how locks are acquired and released
- what happens on crash or disconnect
- whether coordination is local-only or cross-host

What should be clarified:
- one coordination API
- one timeout and recovery policy

### 6.3 Remote or hosted mode
What is still underspecified:
- whether HTTP is for the hardware-touching server, the brain, or both
- where OAuth terminates
- whether bench-local hardware services are ever exposed over the network
- what trust boundaries exist

What should be clarified:
- one remote topology diagram
- one auth boundary definition
- one local-versus-remote deployment policy

## Stage 7: Vendor GDB Backends

### 7.1 Trigger for adding a vendor backend
What is still underspecified:
- what specific pyOCD shortcomings justify a vendor backend
- whether the decision is global, per-board, or per-customer
- whether feature gaps, performance gaps, or reliability gaps all count

What should be clarified:
- one trigger policy with concrete criteria
- one decision owner

### 7.2 J-Link and ST-Link GDB server backends implementing the same SWD interface
What is still underspecified:
- exact backend contract
- process lifecycle
- stdout/stderr parsing
- GDB/MI event handling
- timeout policy
- reconnect policy

What should be clarified:
- one backend interface contract precise enough that pyOCD and GDB/MI implementations can be swapped under tests
- one capability-reporting mechanism

### 7.3 Optional vendor backends are not load-bearing
What is still underspecified:
- how optional capabilities are surfaced upward
- whether feature-discovery is runtime or config-based
- whether advanced features get separate tools or optional flags

What should be clarified:
- one capability matrix
- one fallback policy

## Stage 8: The Capability Ladder

### 8.1 The ambition statement
What is still underspecified:
- what exact scope each rung implies in practice
- whether Stage 8 uses only STM targets or later extends back to nRF
- what "from scratch" excludes

What should be clarified:
- a scope definition for each rung
- a board/task matrix for each rung

### 8.2 The tool suite barely changes
What is still underspecified:
- whether any additional debug primitives are required for higher rungs
- whether breakpoints, watchpoints, or trace become required rather than optional

What should be clarified:
- one explicit capability baseline for higher-rung experiments

### 8.3 Treat it as a ladder
What is still underspecified:
- what exact benchmark tasks belong in each rung
- what success means for each rung
- what artifacts the agent is allowed to create or edit

What should be clarified:
- one evaluation corpus per rung
- one success rubric per rung

### 8.4 "The AI writes the code"
What is still underspecified:
- how generated code quality is evaluated
- whether human review is mandatory
- what standards generated code must satisfy

What should be clarified:
- one review policy
- one code-quality gate for high-rung outputs

### 8.5 "By itself / autonomously, verified, no human"
What is still underspecified:
- what autonomy level is actually in scope for experiments
- what destructive actions still require human approval
- what evidence counts as "verified"

What should be clarified:
- one autonomy policy
- one human-approval boundary
- one verification-evidence policy

### 8.6 Climb empirically to find the convergence frontier
What is still underspecified:
- how results are recorded
- how regressions are detected
- how boundary-of-capability claims are made rigorously

What should be clarified:
- one experiment-tracking format
- one benchmark history policy

### 8.7 Honest positioning at high rungs
What is still underspecified:
- which claims are allowed in internal demos versus external product language

What should be clarified:
- one claims policy tied to measured benchmark results

### 8.8 Skills are the lever
What is still underspecified:
- how skills depth is measured
- how skill quality affects benchmark outcomes
- how skills are curated and validated over time

What should be clarified:
- one skill-quality evaluation process
- one linkage between skill updates and benchmark reruns

## Highest-Leverage Clarifications To Make Next

If the goal is to make implementation easy soon, these are the first definitions worth locking:

1. Supported OS and package-version matrix.
2. Canonical board configuration schema.
3. Stage `0.2` probe-path and recover policy for nRF.
4. COM-port discovery and probe-to-port mapping rules.
5. Reference firmware source, artifact, UART pattern, and known-symbol contract per board.
6. UART adapter signatures and read semantics.
7. SWD adapter signatures, lifecycle, and locked-chip error behavior.
8. MCP tool/resource schema and server process topology.
9. Pre-flash safety gate rules plus recovery-image lifecycle.
10. Convergence watcher predicates, signature model, and refusal protocol.
11. Injected-bug suite definition and Stage 4 evaluation rubric.
12. Brain-loop contract and skills schema.

Once those are defined, most of the remaining work becomes straightforward implementation rather than continued design.
