# Agentic Firmware Debug Tool — Concrete Build Plan (step-ordered)

> **STATUS (2026-06): Stages 0–4 through roadmap `R11` are IMPLEMENTED and
> live-proven on the scoped pair (`nrf52833dk` + `nucleo_l476rg`). `R12` is now
> implemented in code, and the Codex-backed turnkey path has already cleared the
> full frozen 12-case corpus on the scoped pair. Claude CLI has also cleared the
> live attached-board A/B repair matrix on `nucleo_l476rg + nrf52840dk`, but that
> retained Nordic board is not the official `nrf52833dk`.** This is the original design /
> decision record. Steps that describe building the substrate, the MCP server,
> the guardrails, or the benchmark layer — including **Step 1.0d** (the API
> de-risk and service-layer migration) — are **done**; read them as the
> rationale behind the shipped code, not as pending work. The remaining active
> proof work is exact official-pair `nrf52833dk + nucleo_l476rg` closure,
> API-provider parity, and the broader fresh-machine portability proof. Live status: `current-progress.md`; file map:
> `repo_file_index.md`.

> **R12 prototype hard-bar amendment (2026-06-30):** host-local work is
> provider-native, not a governed brain action. The old `read_file`,
> `replace_file`, and `run_build` `TurnDecision` action types have been removed
> structurally, including models, schema variants, executor branches, batch
> special-cases, and stale-action refusal code. Model-native workflow context is
> loaded through the new `load_skills(skill_ids=[...])` context-expansion
> decision, with recursive dependencies, dependency-first init scripts,
> per-skill provider-runtime folders, and prompt injection on the next provider
> turn. The MCP tool prompt injection is now compact: the brain renders a
> curated tool index with short descriptions and required/optional argument
> hints, not repeated full MCP JSON schema bodies. Current proof is focused
> tests, full Python-change gate, and a no-hardware Codex CLI smoke;
> Claude/live-board reproof remains a handoff item.

> **Scope of this document.** This is the *design + implementation plan* — what to build, in what
> order, and the design decision behind each step. It deliberately stops short of writing the code
> itself: where a design choice is straightforward, the "how" is stated plainly; where it isn't, the
> decision is specified and the coding is left to build time. Trying to settle both the plan and the
> code at once is where errors creep in, so this stays at the plan level.
>
> **Hardware — TWO co-primary boards (build and prove the loop on both):**
> - **Nordic nRF52833 DK** — onboard **SEGGER J-Link**; UART → virtual COM port; SWD + UART on one
>   USB. Radio-relevant (BLE/802.15.4). *Wrinkle to plan around:* J-Link's native protocol isn't
>   pyOCD's native CMSIS-DAP, and nRF52 **APPROTECT** can lock the chip (needs a `recover`/unlock).
> - **STM32 Nucleo-L476RG** — onboard **ST-Link/V2-1**; UART on **USART2 @115200 8N1**; SWD + UART on
>   one USB. Cleanest open-stack path (pyOCD/OpenOCD support ST-Link out of the box).
>
> The repo may still retain related Nordic board profiles outside this scoped pair; those are support-
> in-progress references, not part of the validated Phase A contract.
>
> Supporting two probe families (J-Link **and** ST-Link) from the start is deliberate: it forces the
> probe abstraction to be real on day one instead of being retrofitted — which is exactly the
> isolation the later vendor-backend work depends on.
>
> **Stack:** Python; `mcp` SDK + bundled FastMCP; pyOCD for SWD; pyserial for UART.
> **Verify at build time:** MCP is mid-transition — confirm SDK calls, transport, state/auth against
> the live spec when you actually write each piece.

---

## v1 Scope Assumptions (team & environment ground rules)

These are the defaults the rest of the plan assumes. They exist so the team shares one understanding
instead of each person discovering them independently. Most are "stay flexible / capture as you go,"
not heavy upfront decisions.

**Team is mixed macOS + Windows → cross-platform is a DEV requirement from day one (not a deferred
product decision).** Code one teammate writes must run on the other's OS immediately. This forces the
OS-agnostic discipline early, while it's cheap. (Note: neither OS is Linux, so the udev-rules driver
story elsewhere in this plan doesn't apply to the team's own setup — care about the **macOS** and
**Windows** paths. macOS usually needs fewer driver gymnastics for CMSIS-DAP/serial; Windows is the
one more likely to need a driver-association step.)

**Hard rule from the first line of code — never hardcode OS-specific values:**
- **Serial ports come from config or pyserial enumeration**, never hardcoded. (Windows `COM3` vs macOS
  `/dev/tty.usbmodem…` is the #1 "works on my machine" failure for this kind of project.)
- **Paths via `pathlib`**, never literal separators. No shelling out to OS-specific commands.
- The core stack (Python, pyserial, pyOCD, `mcp` SDK) is already cross-platform — you're not fighting
  the tools, just avoiding places your *own* code accidentally assumes one OS.

**Python version:** pick one modern version as the team standard (3.11 or 3.12 is a safe default; the
`mcp` SDK and pyOCD both want a reasonably recent Python). Not a deliberation — just pick and record it.

**Dependency versions:** don't pin thoughtfully upfront — install current versions, **commit a
lockfile** (`pyproject.toml` + lock, or `requirements.txt`) so the mixed team stays in sync, then pin
"what worked" once it works and revisit later. The lockfile matters *more* with a team than it would
solo, because it keeps two OSes' environments matched so a bug isn't an environment mismatch in disguise.

**Redis (external state store, not needed until Stage 3):** a single local Redis is the obvious default
when you reach Stage 3.2. Defer until then.

**Per-OS bootstrap docs — authored incrementally, not planned upfront.** The first teammate to set up
each OS writes a short "on macOS do X / on Windows do Y" onboarding note as they go, so the next person
on that OS has a path. This is a Stage-0 byproduct of setting up your own machine, not a document to
pre-write from guesses.

**Dev support vs. shipped-product support are intentionally different.** You develop on macOS+Windows
because the team is on those; which OSes *customers* get supported is a separate, later decision
(Stage 4+, driven by who buys). Building cross-platform for the team's sake means you'll naturally be
cross-platform-*capable* for customers — product flexibility falls out of the team necessity for free,
so this commitment stays cheap and open.

**What is deliberately NOT decided yet** (and shouldn't be, to avoid premature lock-in): shipped-product
OS matrix, a formal support-matrix table, and packaging/distribution format. These become meaningful at
Stage 4+ and are recorded here only so it's clear their omission is intentional, not an oversight.

---

## STAGE 0 — Foundations (do before anything else), on BOTH boards

**Goal:** two known-good boards + toolchains, so later failures are *your* bugs, not setup bugs.
**Do every step for the nRF52833 DK AND the L476RG.**

1. **Confirm each board's pyOCD target name** (`pyocd list`, `pyocd list --targets`; install the
   CMSIS-Pack if prompted). Expect roughly `nrf52833` and an `stm32l476`-family target. *Why first:*
   the generic `cortex_m` type debugs but **cannot program flash** — the "connects but won't flash" trap.
2. **Probe-specific setup:**
   - **nRF52833 DK (J-Link):** install SEGGER J-Link software (drivers). Route decision is made: use the
     **native SEGGER J-Link path by default** (the OB does not expose CMSIS-DAP without being explicitly
     switched into it — see the driver sidebar), with CMSIS-DAP as the fallback. **Test a flash + a
     recover/unlock cycle** — confirm you can recover the chip if APPROTECT locks it. This is the nRF's
     one real setup risk; clear it now.
   - **L476RG (ST-Link):** install ST-Link drivers. pyOCD should see it out of the box.
3. **Confirm one USB cable yields BOTH** a debug probe and a virtual COM port, on each board.
4. **Get a known-good reference firmware per board** that prints over UART (a vendor sample; for the
   Nucleo target **USART2** specifically). You need a *correct* binary on each to prove the adapters
   and to derive injected-bug tests later.

**Exit criteria (per board):** plugged in, probe + COM port visible, reference firmware flashes and
prints by hand — and on the nRF, you've proven you can recover a locked chip. No Python yet.

> ### Drivers vs. libraries, and what ships to customers (read before designing the install)
>
> **A driver and a library are different layers — don't conflate them.** Your code never "paths to"
> a driver. The stack is layered:
>
> ```
> your code → pyOCD (library you import) → OS → USB driver (OS-level) → probe → chip
> ```
>
> - **A USB driver** is OS-level: it lets the operating system *see* the plugged-in probe. Your code
>   doesn't import it; it just has to be **present on the machine**.
> - **pyOCD** is the library your code imports (`pip install`, then `import`). It speaks CMSIS-DAP /
>   J-Link / ST-Link to a probe the OS can already see. This is the only one your code references.
>
> **What each probe path requires *on the machine* (this drives the shipping story):**
> - **CMSIS-DAP** — lightest; effectively *driverless*. Uses a generic USB class the OS already has.
>   Typically just a **udev rule** on Linux (a permission file, not a driver) or a generic WinUSB
>   association on Windows (sometimes via Zadig). No proprietary install.
> - **SEGGER J-Link software** — a full *proprietary suite* (driver + runtime). Required on the machine
>   ONLY if your code uses the **native J-Link** path. Carries SEGGER's license.
> - **ST-Link drivers** — ST's drivers; lighter than SEGGER's suite, often enumerates with generic
>   drivers on modern systems.
>
> **Key point:** what the machine needs depends on **which path your code uses to reach the probe**,
> not on anything you embed in your code.
>
> **DECISION (amended 2026-06-11, user sign-off — supersedes the earlier "standardize on CMSIS-DAP"
> framing throughout this doc): default to each board's NATIVE probe path; CMSIS-DAP is a supported
> FALLBACK, not the default.** pyOCD reaches a probe over the route named by the board's `probe_family`
> — SEGGER native for J-Link boards, ST-Link for ST boards, CMSIS-DAP for boards whose probe is natively
> CMSIS-DAP. CMSIS-DAP is **not** the global default because some onboard probes — notably the Nordic
> DK's **SEGGER J-Link OB** — do **not** expose a CMSIS-DAP interface unless it is explicitly switched on,
> so defaulting everything to CMSIS-DAP would make those boards fail outright. CMSIS-DAP stays a
> first-class, fully supported path: everything must work through it, it is the automatic fallback when
> the native route fails, and it is the default for boards whose native family already *is* CMSIS-DAP.
> This is empirically confirmed on the bench (see "Verify empirically" below).
>
> **What ships to customers — declare + guide, do NOT bundle drivers:**
> - **You DON'T redistribute vendor drivers inside your CLI.** Legally, SEGGER's/ST's software is
>   theirs to distribute, not yours to repackage. Technically, OS-level drivers don't live inside a
>   Python CLI anyway (admin rights, OS-specific installers).
> - **You DO declare Python deps** — pyOCD + target device packs travel with your package normally
>   (`pip install your-tool` pulls them). Clean.
> - **For OS-level drivers: detect-and-instruct.** Your CLI checks whether a working probe is visible
>   and, if not, points the customer to the vendor's installer. (This is how existing embedded tools
>   do it — they tell you to install the J-Link/ST-Link software; they don't ship it for you.)
> - **Automate only the light, non-proprietary setup** — a udev rule (Linux) or WinUSB association
>   (Windows) your installer *can* help with, because those aren't vendor software.
>
> **What this means for the customer's OS-level setup:** when CMSIS-DAP *is* the route for a board
> (its native family, or a working fallback), the required setup shrinks to the lightest case — often
> just a udev rule / WinUSB association your installer can automate. When a board's native route is
> SEGGER J-Link (the Nordic DK default), that path requires the customer to have SEGGER's proprietary
> software present — a real deployment cost. So the routing rule is: use the native path because it is
> what actually works on that probe out of the box, and prefer CMSIS-DAP wherever a probe genuinely
> supports it (lighter setup), falling back to CMSIS-DAP when the native route fails. CMSIS-DAP is
> lighter *when available*; it is not assumed available everywhere.
>
> **Dev bench vs. shipped product:**
> - *You, in Stage 0:* install everything (SEGGER software, ST drivers) — safest way to get both
>   boards working and to have vendor fallback tools.
> - *Shipped product:* pyOCD + device packs as Python deps; route per board (native default,
>   CMSIS-DAP fallback); automate the light USB setup; detect-and-instruct for anything proprietary;
>   never redistribute vendor drivers. CMSIS-DAP remains fully supported and is preferred wherever a
>   probe exposes it, but is not the forced global default.
>
> **Verify empirically in Stage 0 (platform/board-specific, don't trust the general picture):** whether
> a given CMSIS-DAP probe needs Zadig on Windows, what udev rules pyOCD needs on Linux, and especially
> **whether the DK's onboard J-Link presents cleanly as CMSIS-DAP without any SEGGER component present**
> (onboard probes can behave differently from standalone CMSIS-DAP probes).
>
> **ANSWERED (2026-06-11, Nordic DK J-Link OB bench path):** the Nordic DK's onboard SEGGER J-Link OB does
> **not** present as CMSIS-DAP without a SEGGER component — its USB interface is the SEGGER bulk/WinUSB
> debug channel, driven through SEGGER's J-Link DLL, not a generic CMSIS-DAP class. Reaching it over
> CMSIS-DAP would require explicitly switching the OB into CMSIS-DAP mode. This is the concrete reason
> the routing decision above defaults to the native probe path and treats CMSIS-DAP as a fallback rather
> than the forced default.
>
> **Implementation items this decision creates (build time — not yet coded):**
>
> 1. **Native-default-with-CMSIS-DAP-fallback routing in the SWD layer (Stage 1 adapter / `R7` backend).**
>    Connection logic tries the board's native `probe_family` route first and, on failure, automatically
>    retries over CMSIS-DAP — surfacing which route succeeded. Today the tooling only does native-default;
>    the automatic fallback is documented intent, not working code.
> 2. **J-Link open workaround in the J-Link backend (`R7`).** pyOCD calls pylink's
>    `disable_dialog_boxes()` when `jlink.non_interactive` is True (its default); with current DLLs that
>    clears the USB emulator selection and the subsequent open-by-serial fails with a "No emulator with
>    serial number ... found" error. Set the pyOCD option `jlink.non_interactive=false` (or otherwise skip that
>    call). VENDOR-FIXED, UNVERIFIED ACROSS VERSIONS — verified on the bench with pyOCD 0.44.1 + pylink
>    1.7.0 + J-Link DLL V9.50; reconfirm if those versions change.
> 3. **Automated/guided vendor-driver install for native-J-Link boards (host bootstrap / setup).** Native
>    SEGGER routing puts a proprietary install on the happy path, which collides with the portability
>    playbook (§3: a manual "go download SEGGER" step is a defect). The setup flow must detect the missing
>    vendor software and run/guide its install, or STOP-and-ask the author — not emit a manual instruction.

---

## STAGE 1 — Adapters, hand-tested in isolation (the first mile), on BOTH boards

**Goal:** drive both boards from plain Python before any MCP/agent layer.
**Design rule:** each adapter is a small class with a stable method interface; test from a REPL until
boringly reliable. The probe differences (J-Link vs ST-Link) must hide *behind* the SWD interface.

> **On reference repos:** the useful *ideas* from surveyed open repos are already captured as plan
> decisions in **Appendix R.1** (serial-sequence batching, tools/adapter/skills split, tool taxonomy +
> typed errors, simulation mode, chip-knowledge tool shape) — so you generally **build from this plan,
> not from repos.** At most, Claude Code may glance at two repos for one narrow thing each (Appendix R.2:
> `xds110` folder shape, `embedded-debugger-mcp` tool-list checklist), kept in a scratch/gitignored
> `reference/` area, never the shipped tree. Where a repo contradicts this plan, the plan wins.

### Step 1.0 — Define the canonical repo & artifact layout FIRST (do before any adapter code)
**Why first:** `flash_firmware`, `apply_patch`, bug injection, recovery-image logic, logging, and the
agent itself all need to *find* files. If each invents its own path convention they won't compose. This
is one ten-minute decision that prevents six components from diverging. Decide it now, commit it, point
all later tooling at it. (Not in Stage 0 — Stage 0 is hand-testing with no code/paths yet.)

**Canonical directory layout:**
```
pyocd-debug-mcp/
├── pyproject.toml + lockfile        # deps + pinned versions (team sync, see Scope Assumptions)
├── src/pyocd_debug_mcp/             # all product code
│   ├── adapters/                    # uart.py, swd_interface.py, swd_pyocd.py
│   ├── services/                    # shared board-control operations used by MCP tools and local flows
│   ├── tools/                       # thin MCP tool/resource definitions + dispatch
│   ├── guardrails/                  # flash gate, unlock gate, convergence watcher, logging
│   ├── server/                      # FastMCP server wiring
│   └── brain/                       # turnkey client + skills loader (Stage 5)
├── boards/                          # ONE config file per board (board definitions)
│   ├── nrf52833dk.yaml              #   pyocd target, default baud, probe path, recovery-image ref
│   └── nucleo_l476rg.yaml           #   (USART2, 115200, stm32l476 target, …)
├── firmware/                        # YOUR OWN test firmware ONLY — never the user's (see note below)
│   ├── nrf52833dk/
│   │   ├── reference/src/           #   reference firmware SOURCE tree (known-good, builds clean)
│   │   ├── reference/build/         #   compiled known-good ARTIFACT (the baseline binary)
│   │   ├── recovery/                #   known-good RECOVERY image the safety/unlock gates require
│   │   └── bugs/                    #   injected-bug VARIANTS (see naming below)
│   └── nucleo_l476rg/               #   (same shape)
├── skills/                          # per-chip/peripheral knowledge data files (Stage 5)
│   ├── nrf52833/
│   └── stm32l476/
├── runs/                            # all runtime OUTPUT, keyed by session id
│   └── <session_id>/                #   logs/, captured-serial/, applied-patches/, run-metadata
└── tests/                           # injected-bug test definitions, harness
```

**Decision (settled) — the two frontends are thin wrappers over one shared internal service layer; this
binds Stages 2 and 5.** The hardware/board logic — flash, UART, recover, register/memory access,
board-config and serial resolution, Stage-0 validation — lives in shared internal services (the
`adapters/` layer and the small primitives beside it). BOTH frontends call down into those services and
neither owns the logic: the MCP `tools/` are thin wrappers exposing the services over the protocol, and
the turnkey CLI / any local programmer flow (Stage 5) calls the same services directly. The current
`stage0_check.py` shell path is the CLI frontend in embryo — a wrapper over the shared board-validation
code, not a parallel implementation — so behavior proven there is *reused* by the MCP tools, never
rebuilt. This is the structural reason a board-validation capability can surface as a shell command today
and an MCP tool later with zero logic duplicated: same service underneath, different wrapper on top. It
also fixes where each surface is *documented* — an MCP tool's contract lives in its docstring (the
description the client reads over the protocol), the shell workflow lives in the one operator guide
(`stage0_setup.md`), and the shared service is plain code below both (see the Doc-Sync and Tool-Description
playbooks).

**Naming conventions (the part that's more than "pick a folder"):**
- **Boards:** lowercase board id used everywhere — `nrf52833dk`, `nucleo_l476rg`. Every per-board path
  and config keys off this exact string. One board id, used identically across `boards/`, `firmware/`,
  `skills/`.
- **Firmware artifacts:** `reference/` = the known-good baseline (one canonical name per board, e.g.
  `reference/build/firmware.elf` + `.bin`/`.hex`). Build always uses debug symbols (`-g`/DWARF) so
  `resolve_symbol` works.
- **Bug variants:** systematic, machine-iterable names — `bugs/<id>__<short-slug>/` (e.g.
  `bugs/001__spi-miso-wrong-pin/`), each a self-contained variant the harness/agent can enumerate and
  reference by id. The double-underscore separates the stable id from the human slug.
- **Recovery images:** the canonical path the safety gate AND unlock gate check —
  `firmware/<board>/recovery/`. The gates look here; nothing else writes here.
- **Runtime output:** everything a run produces lives under `runs/<session_id>/`, **keyed by the same
  session id the convergence watcher uses** (Stage 3.2). This aligns logs, captured serial, and applied
  patches with the session-keyed state already decided — one keying scheme, not a parallel one.
- **Session-state config:** the external store (Redis, Stage 3.2) is keyed by the same `<session_id>`;
  `runs/<session_id>/` is its on-disk companion. Same key, two locations (fast store + durable files).

**The alignment that makes this not-a-new-decision:** recovery-image path = what the safety/unlock
gates check; `runs/` keying = the watcher's session key; board id = one string shared by configs,
firmware, and skills. So this layout *implements* decisions already made (safety gate, session-keying,
per-chip skills) rather than introducing new ones.

**CRITICAL distinction — `firmware/` is YOUR test firmware only; the USER'S firmware is never in your
repo.** Two different things that were easy to conflate:
- **Your reference/test firmware** (the `firmware/` tree above): known-good baselines + injected-bug
  variants *you* control, used for *your own* testing. Lives in your repo. Stays here.
- **The user's custom firmware:** their code, in *their* directory/repo, on their disk. Your server
  **never owns, contains, or copies it into your repo.** It is reached by a **runtime path argument**,
  not a fixed location. See the firmware-ingestion tool (Step 2.5) for how this is wired. The server
  holds *no* hardcoded user-firmware path — it's the most user-specific value there is, so it's runtime
  input (no-hardcoding rule, §1 of the Coding Guidelines).

**Exit:** the tree + naming committed; a short README in the repo root documents both so every later
component references one convention.

### Step 1.0b — Board configuration schema (minimal now, grows per-stage)
**The principle (the durable part):** board differences live in `boards/<board>.yaml` as **data, never
as code branches.** If board specifics become `if board == "nrf": … else: …` scattered through the code,
"multi-board support" collapses into a tangle of conditionals that breaks on every new board. This is
the same abstraction as the SWD-interface-with-backends decision, applied to board knowledge.

**Format: YAML.** Decided, not worth deliberating — human-readable, comments allowed, matches Step 1.0.
(Not Python config: that lets logic creep back into what must be pure data — the exact thing this
prevents. JSON: no comments, worse to edit. TOML: also fine, but YAML is the convention here.)

**Schema rule: start minimal, extend per-stage. NEVER add a field before the component that reads it
exists** — otherwise you formalize guesses your later stages will correct.

**Required v1 core (needed by Stage 2; every field traces to a decision already made).** Note each
field carries an **origin tag** (see Coding Guidelines §1b) so a reader knows its authority/changeability:
```yaml
board_id:            nrf52833dk          # PROJECT-DEFINED — canonical id (Step 1.0); keys all per-board paths
display_name:        "Nordic nRF52833 DK" # PROJECT-DEFINED
mcu_family:          nrf52833            # HW-FIXED — the silicon; selects skills/ dir (Stage 5)
probe_family:        jlink               # HW-FIXED — onboard probe; selects SWD backend (Stage 7)
pyocd_target:        nrf52833            # VENDOR-FIXED, UNVERIFIED — confirm via `pyocd list --targets` (won't-flash trap)
serial_baudrate:     115200             # PROJECT-DEFINED — chosen default; must match reference firmware
```

**Decision — keep artifact paths out of tracked board YAML in Phase A.** The
canonical locations still exist and are fixed by the repo layout:
- reference baseline artifacts live under `firmware/<board>/reference/`
- the canonical symbol-bearing artifact is `firmware/<board>/reference/build/firmware.elf`
- recovery assets live under `firmware/<board>/recovery/`

Those are repo-layout and naming-rule decisions, not tracked board-config
fields. Board YAML stays hardware-focused; user and session paths stay out.

**Add later, when its stage arrives (listed so the omission is intentional, not forgotten):**
- `reference_uart_patterns` — **Stage 4** (test harness). What "success/failure" looks like over serial;
  you can't write good patterns until you've seen real output.
- `recover_mode` — a typed selector, not a free-form command string. A lightweight `recover_mode`
  dispatch is acceptable in Stage 0 for bench validation, but the real guarded semantics still belong
  to **Stage 3.1b**. The nRF unlock remains pyOCD's built-in `auto_unlock`/mass-erase path rather than
  custom project logic.
- `register_aliases` — **Stage a / debug surface**. Convenience for the agent's register reads; you'll
  know which aliases matter only once it's actually reading registers.
- `probe_discovery_hints` / `serial_discovery_hints` — **only if needed.** Given the mixed-OS team,
  discovery is best driven by pyserial/pyOCD *enumeration*, which may make per-board hint strings
  unnecessary. Don't bake these in speculatively; add only if enumeration proves insufficient.
  *(Decoupled-PCB note, IMPLEMENTED in the serial resolver:* for a custom PCB whose UART is on an
  external USB-serial adapter — not an onboard VCP tied to the probe — discovery also recognizes the
  common bridge chips (FTDI, Silicon Labs CP210x, WCH CH34x, Prolific PL2303) by USB vendor id and
  description, so the adapter surfaces as a serial candidate even with no board hint and no probe link.
  Onboard dev-board VCPs stay handled by the probe link / vendor helpers. An explicit `--port` override
  still wins.)*
- `memory_protection_rules` — **already covered** by the guardrails (fuse/option-byte refusal, APPROTECT
  case in Steps 3.1/3.1b). Don't duplicate that logic into a vague config field; extend only if a real
  per-board protection rule appears that the gates can't express generically.

**Decision — validate the schema:** every component reads board config through one small loader that
validates the required core is present and fails loudly on a malformed/incomplete board file (a missing
`pyocd_target` should be an obvious error, not a silent wrong-target flash). One loader, one schema, one
source of truth — not each component parsing the YAML its own way.

**Exit:** the minimal schema + one loader committed; both boards have a valid `boards/<board>.yaml`; the
"data-not-branches, grows-per-stage" rule documented in the repo README.

### Step 1.0c — Environment, container & boilerplate (uv-managed; do alongside 1.0)
**Why here:** Stage 1 is the first line of code, so the team needs one reproducible Python environment
and one set of per-developer config files *before* adapters are written — otherwise "works on my
machine" creeps in exactly where the Scope Assumptions warned (mixed macOS + Windows). This is the
Scope Assumptions' "pick a Python version / commit a lockfile" made operational.

**"The container" = a uv-managed virtualenv, not Docker.** *Initializing the container* means creating
the project's isolated Python environment with [uv](https://docs.astral.sh/uv/):
- **Pin the interpreter once:** `.python-version` = `3.12` (committed). uv installs that interpreter
  automatically — no system-Python assumption. (3.10 is the hard floor from the MCP SDK; 3.12 is the
  team standard chosen per Scope Assumptions.)
- **Sync = create + reproduce the env:** `uv sync` creates a gitignored `.venv/`, installs runtime +
  dev deps, and writes/honors the committed `uv.lock`. A teammate runs the *same* `uv sync` to get a
  byte-identical environment — this is the "lockfile keeps two OSes matched" rule, enforced. Runtime-only
  install (no dev tools): `uv sync --no-dev`.
- **Commit:** `pyproject.toml`, `uv.lock`, `.python-version`. **Never commit:** `.venv/`.
- **Run everything through `uv run …`** so each command uses the pinned env, never a stray global
  Python (`uv run pytest`, `uv run ruff check .`, `uv run pyocd list`).

**Boilerplate / local-override files — per-developer, never load-bearing for anyone else.** These are
the machine-specific values the no-hardcoding rule (§1) keeps out of code and out of shared config:
- **`.env`** — copy from `.env.example`; sets `PYOCD_PROBE_UID` (your probe's unique id, from
  `uv run pyocd list`) and `PYOCD_TARGET` (your chip, e.g. `nrf52833`, `stm32l476`). These are the
  per-machine defaults for `connect`/`flash`; **gitignored** (`.env` ignored, `.env.example` committed).
  The Phase A MCP server and host scripts auto-load `.env` when present. The `connect` path still
  accepts `unique_id`/`target` as runtime args that override these.
- **`pyocd.yaml`** (committed) — shared, project-wide pyOCD options; **`pyocd.local.yaml`**
  (gitignored) — per-developer tweaks. **Both are authored from scratch when first needed, not copied
  from a template** — pyOCD *reads* this file (its keys are pyOCD's schema) but ships no example, and
  the project may have no `pyocd.yaml` at all until a shared option actually exists. Don't treat a
  missing `pyocd.yaml` as an error.
- **Relationship to `boards/<board>.yaml` (Step 1.0b):** board YAML is the shared board *definition*
  (data, committed, same on every machine); `.env` / `*.local.yaml` are per-*machine* (which probe is
  plugged into *this* bench, which COM port). Different axes — don't fold one into the other.

**Verify the env reaches hardware (bridges to Stage 0):** `uv run pyocd list` shows each board's probe
and its unique id; copy that id into `.env`. If a probe doesn't appear, it's the OS-level driver/WinUSB
setup from Stage 0, not the Python env.

**Exit:** `.python-version` + `uv.lock` committed; `uv sync` reproduces the env on both macOS and
Windows; `.env.example` exists; `pyocd.local.yaml` is the gitignored per-developer override file; a
committed `pyocd.yaml` exists only if the team has real shared pyOCD options to standardize; `uv run
pyocd list` sees each board's probe.

## Future Fix: after Step 1.0d is completed, since its not relevant to the ROADMAP or TO DO after it has been fixed, should be replaced with something that describes how the codebase has been formatted / what has been done, not what NEEDS to be done. In particular, the ROAMAP and the build_plan should detail how the codebase is now setup (server + script is a thin wrapper, another file contains the actual tools), and should detail what should be done, and how it should be formatted in the future; the future steps in ROADMAP and build_plan should also be edited to follow the codebase structure & mechanistic operations of how this step specifies it.

### Step 1.0d — Validate the pyOCD Python-API path and stand up the shared service layer (do FIRST, before any adapter)
> **STATUS: COMPLETED (2026-06).** The API path was proven on hardware, `adapters/`+`services/`
> were created, and both `stage0_check.py` and `server.py` are now thin callers over the shared
> services. The discipline below is the record of how it was sequenced, not pending work.

**Why this is the first code step in Stage 1 (current-state reality, not a hypothetical).** The
repo (at the time this was written) had TWO independent pyOCD callers, and together they were
exactly the duplication Step 1.0 was written to prevent:
- `stage0_check.py` drives pyOCD by **subprocess** (`pyocd cmd -c "read32 …"`, `pyocd load`,
  `pyocd erase --mass`) and scrapes stdout with regex. This is the **only** target-control
  path validated on real hardware to date.
- `src/pyocd_debug_mcp/server.py` drives pyOCD via the **Python API** (`ConnectHelper`,
  `session.target.read_memory`). This path is **NOT yet validated on hardware.**

Neither calls the other; the J-Link `jlink.non_interactive=false` workaround lives only in the
subprocess path; the shared service layer the rest of the plan assumes (Step 1.0, `adapters/` +
`services/`) does not exist yet. **This gates every adapter step below:** Step 1.2's SWD
interface cannot be built on a pyOCD access path that hasn't been proven, and Steps 1.1, 1.2,
and 1.3 must all be written *as services in the layer this step stands up*, not as logic inside
a frontend. Doing this after the adapters would mean writing a third parallel implementation and
then unwinding it.

**The discipline — ordered, do NOT reorder:**

1. **Prove the API path at the smallest surface (de-risk first).** Before writing any
   adapter/service, reproduce stage0's proven target-control operations through the pyOCD
   **Python API** in a throwaway script — `connect → read silicon-ID` first, then the riskier
   `flash` and `recover`. Oracle every result against what the subprocess path already
   returns (stage0 is the reference of record). Do the **STM32 (ST-Link) first**: it has no
   J-Link open quirk, so a failure points at the API approach itself rather than the probe
   wrinkle. Carry the known workaround across — the API path must set pyOCD option
   `jlink.non_interactive=false` (mirroring `stage0_check.py:pyocd_base`) or open-by-serial
   fails on the nRF.
2. **Fix before migrate — never migrate red code.** If the API calls are wrong, fix them at
   the smallest reproduction and get them green on the bench FIRST. Fixing the calls
   `server.py` *already has* (connect/read) in place is fine when the bug is trivial; drop to
   the throwaway script when it is not, so you are not debugging through FastMCP + the lock +
   stdio. Migration is a behavior-preserving refactor — it needs passing behavior to preserve,
   so there must be nothing red crossing into the new layer.
3. **Stand up the service layer and write the proven calls into it — not into a frontend.**
   Create the `src/pyocd_debug_mcp/adapters/` + `services/` layout (the Step 1.0 layout, which
   does not exist yet) and land the corrected operations there. Hand-test each service in a
   REPL/small harness, oracle'd against the subprocess output. Do NOT grow `server.py` to full
   capability and then relocate it — that writes the logic twice. (Distinction that resolves the
   apparent fix-here-vs-there conflict: the calls `server.py` *already has* may be fixed in
   place before extraction; the operations it does *not* have yet — `flash`, `recover`,
   `read_serial` — are written straight into services, never built into `server.py` first.)
4. **Thin the wrappers onto the services (this swap IS the migration).** `server.py`'s tools
   become thin calls into the services, gaining the operations it lacks (`flash_firmware`,
   `read_serial`, `unlock_recover`); `stage0_check.py`'s target-control calls swap from
   subprocess to the same services. When done, the J-Link workaround exists in exactly one place.

**Probe-abstraction discipline (critical when only one probe family is on the bench).** This
de-risk happens on J-Link hardware first, and the STM32/ST-Link board may not be present when the
service layer is built. Keep probe specifics — the J-Link `jlink.non_interactive=false` option,
native-vs-CMSIS-DAP routing, locked-target handling — routed through `board_config` / the probe
backend, **never as scattered `if probe == ...` branches** in the service or wrapper layers (the
code already applies the J-Link option conditionally from `board.probe_family` — keep that
pattern). Building with only J-Link present puts the burden on the author to keep ST-Link
assumptions out, since they cannot yet be tested; this discipline is exactly what makes the
eventual STM32/ST-Link bring-up a **drop-in** rather than a rewrite, and turns the STM32 into a
verification of the abstraction instead of a trigger to redesign it.

**Ordering note:** steps 1-3 (prove the API, create the layout, adopt the wrapper discipline)
happen up front and gate the adapter work — that is why this is Step 1.0d and not a later step.
Step 4 (thinning `server.py` and `stage0_check.py`) completes *incrementally as each service
lands* through Steps 1.1-1.3 and the Stage 1 close; it is stated here so the discipline is owned
from the first keystroke, not deferred. UART (Step 1.1) does not touch the pyOCD API and can be
built in parallel with steps 1-2, but it still lands in the service layer this step creates.

**Scope — only target-control operations are in scope for the API de-risk.** Probe enumeration
(`pyocd list`), serial discovery (pyserial), and CMSIS-Pack checks do not touch the pyOCD
target API and stay as they are. The operations to validate-then-extract are exactly:
`connect`, `read_memory`/silicon-ID, `flash`, `recover` (unlock/mass-erase),
`halt`/`reset`/`resume`.

**Exit:** the `adapters/`/`services/` layout exists; the in-scope pyOCD target-control
primitives are proven on hardware **through the Python API** (not just subprocess) and live in
services; the wrapper-discipline is adopted so Steps 1.1-1.3 write into the service layer; the
thinning of `server.py`/`stage0_check.py` is underway. This is the precondition for Step 1.2's
SWD interface and for all of Stage 2.

### Step 1.1 — UART adapter (build first; easiest; board-agnostic)
- **Design:** `open() / read_lines() / write() / reopen()`, 115200 8N1. One adapter works for both
  boards — UART is the same; only the COM port differs.
- **Decision baked in now:** `reopen()` from the start — the Nucleo VCP can drop on reset/reflash, and
  reconnect-after-flash is good hygiene on both boards.
- **Code-shape rule:** the adapter is the low-level I/O layer. Any higher-level
  "capture UART for N seconds", "wait for expected text", or "reopen after
  flash" behavior belongs in shared services above the adapter so both CLI flows
  and MCP tools call the same logic.
- **Exit:** see each board's reference firmware output in your own Python script.

### Step 1.2 — SWD adapter as an interface + pyOCD backend (this is where two probes pays off)
- **Design — the central decision of this stage:** one *abstract SWD interface*
  (`connect / flash / reset_and_halt / halt / resume / read_register / read_memory / resolve_symbol`),
  with the pyOCD calls inside a backend. Because you're running **both** a J-Link board and an ST-Link
  board, the interface has to genuinely abstract the probe from day one — you can't accidentally bake
  in ST-Link assumptions. That real-from-the-start abstraction is what makes later vendor GDB backends
  (Stage 7) a clean drop-in.
- **Code-shape rule:** board-level operations such as "flash reference
  firmware", "run recover", "verify target identity", or "Stage 0 validate this
  board" should be implemented in shared services that compose these adapter
  calls. The MCP layer and any local programmer/CLI wrappers stay thin.
- **nRF-specific behavior to handle in the backend:** APPROTECT/locked-chip detection + a `recover`
  path, so a locked nRF doesn't look like a generic failure.
- **Build order within the step:** connect → read a register → flash → halt → read PC, on each board.
- **Exit:** on **both** boards, flash the reference firmware, halt, read the PC.

### Step 1.3 — Symbol resolution (thin; board-agnostic)
- **Design:** pyOCD's ELF symbol provider resolves a named variable → address/value. Firmware must be
  built with debug symbols (`-g`/DWARF).
- **Decision:** no separate GDB server for the MVP — pyOCD's direct API + symbol provider covers it.
  GDB/MI is a documented future option (Stage 7), not now.
- **Exit:** resolve a known global on both boards.

**Stage 1 exit criteria:** on BOTH boards — flash + read serial + halt + read register + resolve a
symbol, all by hand, all through the same adapter interface. *Nothing past here matters until this works.*

---

## STAGE 2 — Wrap adapters as a local MCP server (no agent yet)

**Goal:** expose the working adapters as MCP tools over **stdio**, validated in isolation.
**Board note:** the server is board-agnostic above the adapter — it takes a board/target + port as
config and uses the same tools for either. Prove the server against both boards.

### Step 2.1 — FastMCP server, stdio transport
- **Design:** `@mcp.tool()` / resource decorators wrapping shared Stage-1/Stage-0
  service methods, not reimplementing board logic in the handler itself. stdio
  only (local, no auth, lowest latency; the natural fit since the server must
  sit next to the board).
- **Decision — primitive split:** actions = **tools** (`flash_firmware`, `reset_and_halt`, `halt`,
  `resume`, `apply_patch`, `unlock_recover` [gated — destructive, see Step 3.1b], `load_firmware_project`
  [ingest external user firmware, see Step 2.5]); read-only data = **resources** (`read_serial`,
  `read_register`, `read_memory`, `resolve_symbol`).
- **Decision — return types:** return typed text/content blocks (strings), **not raw dicts** (raw
  dicts can truncate silently in the client though they look fine in the Inspector).
- **Decision — board selection (board-config-aware, IMPLEMENTED):** `connect` takes an optional
  `board_id` (or `PYOCD_BOARD_ID` env, plus `board_config` / `PYOCD_BOARD_CONFIG` for a custom board
  file outside `boards/`) and resolves the board's facts — pyOCD target, recover policy, silicon id,
  baud — through the **same shared loader the Stage 0 CLI uses** (`pyocd_debug_mcp.board_config`). This
  realizes the shared-service decision (Step 1.0): the server is a thin wrapper over the one loader, so a
  custom ST/nRF board connects by id with no hand-passed target, and its facts reach the tools, not just
  the CLI. Precedence for the target: explicit `target` arg > the board's `pyocd_target` > `PYOCD_TARGET`
  env > pyOCD auto-detect. A read-only `get_board_info` tool exposes the loaded facts; calling `connect`
  with no `board_id` stays valid (raw-target mode). One server binary still serves either board (at
  scale, one instance per board — see Stage 6).
- **Decision — entry point & startup (how the server actually launches):** declare a console-script
  entry point in `pyproject.toml` (`[project.scripts]`, e.g. `pyocd-debug-mcp = "pyocd_debug_mcp.server:main"`)
  so the server starts as **`uv run pyocd-debug-mcp`** over the MCP **stdio** transport. This exact
  command is what MCP clients are pointed at in Stage 4 — declaring it now avoids hardcoding a brittle
  `python path/to/server.py` invocation and keeps startup inside the pinned uv env (Step 1.0c).

### Step 2.2 — Validate every tool with the MCP Inspector, against both boards
- **Why before a real client:** schema errors fail *silently* in a real client; the Inspector surfaces
  them. Exercise each tool by hand here, on each board.
- **How:** `uv run mcp dev src/pyocd_debug_mcp/server.py` launches the server under the MCP Inspector (the `mcp`
  dev tooling comes from the `mcp[cli]` dependency). Run it through the pinned env so it matches what
  ships.

### Step 2.3 — `apply_patch` design decision
- **Decision:** v1 = full-file rewrite (simpler, reliable). Diffs later (auditable, finer, harder to apply).

### Step 2.4 — Long-running operations: BLOCKING for v1
- **Decision (settled):** v1 uses **blocking** tool calls, not the async/ticket pattern — the debug
  loop is inherently sequential on a single board, so there's no independent work to parallelize.
- **But:** blocking calls are **bounded** at every layer that can be bounded in-process: external
  helper CLIs, local MCP startup, model-provider subprocess/API calls, serial read/write windows, and
  MCP tool calls all carry explicit project-defined timeouts. pyOCD flash/reset/step paths also pass
  explicit pyOCD session timeout options. Blocking != unbounded waiting.
- **Known implementation boundary:** pyOCD session open and some vendor DLL calls run in-process. The
  installed pyOCD version exposes flash/reset/step timeout options, but not a direct connect timeout;
  if a vendor DLL blocks inside native code, Python cannot safely kill just that call. The future
  ticket/worker-process hook is the path to a hard kill guarantee for those calls.
- **Forward-compat hook (cheap, do now):** isolate "run a slow op" behind one internal interface, so a
  later move to the ticket pattern / MCP Tasks extension reimplements *one* module. Don't build the
  ticket pattern yet.

### Step 2.5 — Firmware ingestion (the user's custom firmware lives OUTSIDE your repo)
**The problem:** to flash a user's own firmware, the server needs it — but the user's firmware is *their*
code in *their* directory (often the very folder Claude Code / Codex is working in), NOT something that
goes in your repo. So the server is *pointed at* it, never *contains* it.

**What makes this simple — the local-server constraint:** your hardware-touching server runs on the
user's own bench machine (it must, to drive the USB board). So the user's firmware is *already on the
same machine*. "Ingest it" = read a path on the local filesystem. No upload, no network transfer, no
copying into your repo.

**Design — path-in-as-argument, never a fixed location:**
- A tool (e.g. `load_firmware_project`) takes the **external local path** to the user's project as a
  runtime **argument**, plus how to produce a binary: either *"already built, here's the binary path"*
  or *"build it with this command."* The server stores this as **session config** (keyed by session,
  like all other state — Stage 3.2). The server holds NO hardcoded user-firmware path.
- **Flow:** `load_firmware_project(path, build_cmd|binary)` → (if source) **invoke the user's own build
  command in the user's directory** → **locate the resulting artifact** (the user tells you where it
  lands; don't guess their build layout) → run that binary through the **pre-flash safety gate**
  (Step 3.1) → flash via the existing SWD adapter.

**Decision — drive the user's build, don't reproduce it (v1).** Firmware builds are brutally
environment-specific (toolchain version, SDK, build system). v1 reuses the build that already works on
the user's machine by invoking *their* command in *their* directory. Owning/standardizing the toolchain
(containerized reproducible builds) is a real but **much heavier, later** option — explicitly NOT v1.
(Per-board build flows genuinely differ — nRF `west`/nRF-Connect-SDK vs. ST Cube/Make — another reason
to drive the user's command rather than encode per-board build logic.)

**Safety/trust (not optional here):**
- A user-supplied binary is *less* trusted than one the agent itself produced — so the **pre-flash gate
  matters more, not less.** This feature is precisely why the gate exists; they are coupled.
- Treat the external path as **untrusted input:** validate it exists / is a directory / contains what
  the build expects; the produced binary still must pass the gate before touching the board.
- You are running a **user-supplied build command** in a user directory. Benign on the user's own local
  machine (they could run it themselves) — but flag it for the future hosted/remote tier, where "whose
  machine, whose code" gets murkier.

**Origin tags:** the user's project path and build command are `PROJECT-DEFINED` *by the user* at
runtime (their choice, supplied to you); the chip target/regions the gate checks remain
`HW-FIXED`/`VENDOR-FIXED`.

**Stage 2 exit criteria:** a local stdio MCP server whose every tool/resource works in the Inspector,
verified on both boards; `load_firmware_project` can ingest an external project path, build via the
user's command, locate the artifact, and (gated) flash it.

---

## STAGE 3 — Deterministic guardrails IN THE SERVER

**Goal:** durable guarantees *below the brain* so they bind every client (yours or a user's Claude
Code). **Design rule:** guardrails are deterministic code, not model judgment.

### Step 3.1 — Pre-flash safety gate (first guardrail)
- **Design:** inside `flash_firmware`, before hardware is touched — validate image, refuse
  fuse/option-byte writes, require a known-good recovery image. Unsafe → refuse via the protocol.
- **Code-shape rule:** the guarded flash path should live in shared internal
  code below both the MCP tool wrapper and any local programmer wrapper, so
  there is exactly one flash policy.
- **Board note:** include the nRF APPROTECT/lock case — the gate (and recovery image) is what makes a
  locked nRF recoverable rather than a dead end. *Why first:* it prevents the most expensive failure.

### Step 3.1b — Gated unlock/recover (SECURITY FLAG — destructive action)
- **What it is:** the nRF APPROTECT unlock is **built into pyOCD** (option `auto_unlock`, default
  **True**; it unlocks by performing a **mass erase**). You do NOT write the unlock logic — your
  shared recover operation is a thin wrapper over pyOCD's built-in unlock/mass-erase, and the
  `unlock_recover` MCP tool or local programmer flow should call that shared operation.
- **WHY IT'S A SECURITY FLAG, not just a convenience:** **unlocking erases the entire chip.** It is
  irreversible. `auto_unlock` silently wiping a chip is fine on a dev bench but is exactly the kind of
  destructive, irreversible action an autonomous agent must not trigger casually.
- **Decision — gate it, don't leave it free/automatic:**
  - In the shipped server, **disable silent `auto_unlock`** on connect; expose unlock only via the
    explicit, **gated** `unlock_recover` tool.
  - The gate (deterministic, like the flash gate) decides *when* an unlock is permitted — e.g. require
    explicit confirmation / a known-good recovery image staged / not allowed mid-autonomous-loop without
    sign-off. The unlock *call* is trivial; the **decision to allow it** is the real design work.
  - Log every unlock as a high-severity event (it destroyed chip state) — feeds the audit trail.
- **Related "mysterious won't-flash" gotchas to handle here (same symptom, different cause):**
  - **SoftDevice lock:** loading firmware containing a Nordic SoftDevice locks that flash region;
    reprogramming it requires a prior mass erase. Expected on BLE work (the nRF is the radio board).
  - **Re-lock on power cycle:** some nRF boards (notably the dongle, less so the DK) re-enable APPROTECT
    at startup, so "I unlocked it but it's locked again" can be the firmware, not a tooling failure.
- **Stage 0 verification (no code yet):** prove the recover cycle by hand in pyOCD Commander —
  `initdp` → `makeap 1` → `status` (Locked) → `unlock` → `status` (Unlocked) → `reinit`. Confirms the
  capability works on *your* board before you wrap it.
- **Current repo-aligned Stage 0 shape:** if a Stage 0 helper script automates bench validation, it
  should dispatch from a typed `recover_mode` selector in board data to an implementation in code. Do
  not put arbitrary recover shell commands in tracked board YAML.
- **Verify at build time:** the exact pyOCD Python entry point for programmatic unlock/mass-erase and
  the `auto_unlock` option name are version-specific — confirm against your installed pyOCD's API. The
  *capability* is solidly built in; the precise call is the part to check.

### Step 3.2 — Session state, externalized and session-keyed
- **Decision (settled):** store the watcher's per-session history in an **external store (Redis) keyed
  by session ID from day one**, even on one local instance. In-process memory can't be cloned for
  scaling; externalizing now makes scaling a config change, not a rewrite. The one "do-it-early" item.

### Step 3.3 — Behavioral convergence watcher
- **Design (deterministic backbone):** server sees every tool call in a session; hash each flashed
  image/patch; detect (a) exact repetition, (b) non-shrinking failure signature, (c) oscillation. On
  "stuck": **refuse further action tool calls** + return a non-convergence notice.
- **Decision — honest scope:** detects clear-cut thrashing fully; can't do the fuzzy "exploring vs.
  circling" judgment for an opaque external brain. A watcher-*model* may add a fuzzy advisory layer;
  deterministic signals stay the hard stops.

### Step 3.4 — Structured logging / audit
- **Design:** log every tool call structured. One mechanism, three payoffs: feeds the watcher, becomes
  the engineer-feedback feature, pre-conforms to the coming MCP audit spec.

**Stage 3 exit criteria:** flash gate blocks a bad image (both boards); **the `unlock_recover` tool is
gated and refuses without sign-off** (and silent `auto_unlock` is disabled in the server); watcher halts
a deliberately-unfixable loop; every tool call logged (unlocks as high-severity); watcher memory in the
external store keyed by session.

---

## STAGE 4 — Prove BYO-agent mode end to end (no frontend of your own), on BOTH boards

**Goal:** a real external agent drives your server safely — the headless product, working.

1. **Register the server with your own Claude Code** as a local stdio server
   (`claude mcp add --transport stdio <name> -- uv run pyocd-debug-mcp` — i.e. `<command>` is the
   Stage-2.1 entry point launched through the pinned uv env; config in `~/.claude.json`; verify with
   `claude mcp list`). *Confirm exact syntax against current docs at build time.*
2. **Run the injected-bug suite through Claude Code, on each board:** break the reference firmware in
   known ways (wrong register value, off-by-one, peripheral init order) and confirm diagnose + fix.
3. **Run safety/convergence tests live** under a real agent (both boards).
4. **Run the wiring-fault test:** disconnect/misconfigure and confirm the agent reports a *physical*
   fault instead of rewriting code forever — your original core insight. (Do this on both; the
   J-Link/ST-Link difference makes it a stronger test of the fault-vs-code distinction.)

**Exit criteria:** your headless server + stock Claude Code = a working debug loop with safety and
anti-thrash, on both boards, zero UI written. *This is a shippable BYO-agent product.*

---

## STAGE 5 — The turnkey brain + CLI (the only part with a frontend)

**Goal:** the premium product — your own loop, your skills, your frontend.

Frozen implementation choices for the first pass:

1. **Build the brain as a native Python MCP client** of the same server (reuses Stages 1–3 wholesale).
   Do **not** hand ownership of the loop to Codex CLI or Claude Code; if those CLIs are used, they
   act only as interchangeable decision backends under the brain's control.
2. **Keep the provider layer isolated.** The implemented R12 brain now supports:
   - `openai-api` via the official OpenAI SDK + Responses API
   - `anthropic-api` via the official Anthropic SDK + Messages API
   - `codex-cli` via local `codex exec`
   - `claude-cli` via local `claude --print`
   This lets the same turnkey loop run on either API credits or existing coding-agent subscriptions.
3. **Own the orchestration loop directly** in the brain. Do not delegate loop ownership to the Agents SDK
   in the first pass. Future provider SDK work is allowed only as an adapter
   implementation detail: Codex SDK/app-server thread APIs and Claude Agent SDK
   sessions may replace subprocess wrappers, but the repo-owned brain still
   decides prompts, parses `TurnDecision`, gates board actions, records evidence,
   owns timeout/convergence policy, and controls run artifacts.
4. **Add board-aware skills injection** as YAML data under `skills/`:
   - `skills/common/`
   - `skills/mcu_families/nrf52833/`
   - `skills/mcu_families/stm32l476/`
5. **Keep the model-facing action surface smaller than the server surface.** The first turnkey acceptance
   path used a temporary bridge:
   - MCP-backed actions: `connect`, `disconnect`, `get_board_info`, `get_state`, `halt`, `resume`,
     `reset`, `read_core_register`, `read_memory`, `flash_firmware`, `read_serial`, `unlock_recover`
   - local actions: read one file, replace one file, run the case build command, diff the workspace,
     run final green verification
   That bridge is not the final Stage 5 prototype bar. The hard prototype target
   below requires host-only file/shell/script work to be model-native/free, with
   only board/server-native or terminal decisions returned to the brain as the
   governed turn boundary. Do **not** expose write-memory/register or breakpoint
   tools to the model in v1.
6. **Build a dual-mode CLI frontend**:
   - `pyocd-debug-brain run --board-id ... --task ...`
   - `pyocd-debug-brain benchmark --case-id ...`
   - `pyocd-debug-brain benchmark --suite pilot_v1_plus_b003_b004`
   Embedded engineers live in the terminal; GUI later. **This is the only frontend you build, and it
   belongs to the brain.**
7. **Benchmark against the same 12-case corpus already frozen in R11.** The first product claim is
   parity on that corpus plus lower operator burden, not a harder corpus or a new benchmark taxonomy.

Current prototype capability target on top of that first pass:

This list is mandatory for the first capability prototype. Agents must not
declare a branch, wave, or product pass complete by implementing only a subset
that happens to test green. The bar is the product prototype described here and
in `markdowns/things-to-change.md`, not a narrower agent-selected definition.

1. **Use persistent provider sessions where available.** API providers should continue the same model
   conversation through native session/conversation handles. The current
   subscription-backed bridge uses Codex and Claude CLI resume handles. Future
   hardening should move Codex to SDK/app-server thread APIs and Claude API-key
   use to Claude Agent SDK sessions, while keeping Claude subscription use as a
   BYO local Claude Code CLI integration unless Anthropic approves another
   product arrangement. The brain contract is written around session continuity
   instead of one-shot reopening. For real-session providers, failed resume is
   not normal continuation: headless runs fail closed by default, and the
   interactive shell must ask before retrying or starting a new provider session
   from saved local memory. Any recovery-created provider session is labeled as
   new in events and artifacts.
2. **Split host freedom from board governance.** The model can do host-only code/file/process work as
   model-native actions. It emits a final governed decision only when it needs server-native board tools
   or needs to return a final answer.
3. **Forward real tool metadata compactly.** The turnkey prompt includes a curated compact index
   sourced from live MCP tool descriptions and input schemas: one-line descriptions,
   required/optional argument hints, and stable response/refusal semantics. Do not
   reprint full MCP JSON schema bodies into provider prompts.
4. **Support batched board decisions.** A decision may contain an ordered batch of actions. Add `wait`
   and UART write to the basic action surface. Keep write-memory/register and breakpoint mutation out of
   this prototype unless a later spec explicitly adds them.
5. **Make progress visible.** Add normalized progress events from the brain loop, stream them in the CLI,
   and add a developer inspector mode that records prompt turns, provider stream text, parsed decisions,
   tool calls, state snapshots, and server observations.
6. **Harden blocking paths before expanding autonomy.** Every provider, MCP startup, server helper,
   subprocess, UART, and hardware-adjacent path must have a bounded failure mode. In-process pyOCD/vendor
   calls that cannot be interrupted directly must be documented and wrapped by the strongest feasible
   outer bound until a killable worker is introduced.
7. **Let the model refine budgets inside hard caps.** Prompt the model to estimate per-action timeouts and
   iteration needs. The brain clamps those values, adds fixed safety cushions where appropriate, enforces
   an unattended-duration cap, and syncs allowed timeout changes to the server as partial updates for
   subsequent operations.
8. **Add client actions.** Model-authored scripts are saved in a session-scoped client-action store and
   run by name with inputs. Host-only scripts are model-native; scripts that call server-native tools are
   governed and route every server call through the brain.
9. **Scope green approval to proof value.** For the prototype, use manual/human-confirmed model-made tests
   or one narrow automated flipped-value gate for a benchmark type. The model supplies the script,
   parameters, correct values, and flipped values; the brain runs both and accepts only pass-correct /
   fail-flipped.
10. **Use the existing compact provider memory plus periodic native safety
    sync.** The brain owns durable memory as structured facts, not provider
    self-report alone: working snapshot, exact recent boundary decisions,
    compact older history, artifact refs, and code/workspace context. For
    remote-primary providers, inject that compact memory into the native session
    on a configurable cadence. The prototype default is every 10 provider turns,
    configurable with `--native-sync-every` or
    `PYOCD_TURNKEY_NATIVE_SYNC_EVERY`; `0` disables periodic sync injection.
11. **Keep static context cheap and cache-friendly.** Skill bodies, MCP schema
    bodies, and other large static prompt blocks should not be reprinted every
    turn. Render a compact governed-tool index plus selected-skill index and
    safety lines in the cached prefix, let the model pull large bodies on
    demand where applicable, and use content hashes for rendered tool/skill
    blocks and deterministic setup artifacts.
12. **Add chunked stream checkpoints only where payoff is high.** Implement checkpoint/cancel handling for
    UART reads, builds/external commands, and long client actions. Do not broaden this prototype into the
    pyOCD worker/job layer.

**Exit criteria:** `pyocd-debug-brain` still runs the full loop turnkey on the scoped pair (`nrf52833dk` +
`nucleo_l476rg`) and reuses the 12-case benchmark corpus, but the prototype is now judged by whether it can
show a substantially more agentic loop: persistent work context, periodic compact-memory safety sync, cheap
static context with on-demand detail, free host-side code work, governed board decisions, visible progress,
bounded waits, model-tuned budgets inside hard caps, client actions, and a scoped green-test story.
Shipped-product polish and broad UI completeness are explicitly later work.

Current status correction, 2026-06-30: the Wave 1 Branch B subset has now been
corrected in code for the Stage 5 prototype bar: host-side file/shell/build work
stays model-native/free, stale host-action decisions are refused, and every
provider turn still closes with exactly one governed board/client/terminal
decision. Codex CLI proof is green on the attached
`nucleo_l476rg + nrf52840dk` pair, but Claude CLI code-writing proof is blocked
by provider quota until the morning reset and exact official `nrf52833dk` proof
remains pending. Wave 2 visibility/proof/static-context/checkpoint/cleanup
items remain prototype requirements, not optional polish.

---

## STAGE 6 — Scale & remote (only when needed)

- **Multiple boards = multiple agent+server pairs, NOT multithreading.** One simple sequential agent
  per board beats one agent juggling many; isolation (separate processes/sessions) gives for free what
  shared-memory concurrency makes you fight for. The Stage-3 session-keyed state already supports this.
  (Having designed for two boards from day one, multi-board scaling is mostly "run more pairs.")
- **Thin coordination only for genuinely shared resources:** if boards must talk to *each other* (the
  mesh-protocol case — and the nRF's radio makes this a natural future direction) or share one
  instrument, add a small coordination layer for *that piece only*; keep agents otherwise isolated.
- **Remote/hosted:** add **Streamable HTTP transport + OAuth 2.1** (SSE is legacy — use HTTP). Build
  OAuth in from the start of the HTTP work. The hardware-touching server still runs locally on the
  bench; only non-hardware pieces (e.g. a hosted brain) live remote.

---

## STAGE 7 — Vendor GDB backends (only when a board needs it)

- **Trigger, not a schedule:** add a vendor backend when the open stack concretely falls short on a
  board (e.g. "pyOCD won't give me RTT/SWO trace on the nRF" — the likeliest first case, given the
  nRF's J-Link).
- **SEGGER J-Link GDB server backend** (nRF — likely first need; SEGGER's RTT/SWO/reliability on its
  own probe) / **ST-Link GDB server backend** (STM32). Each implements the *same* SWD interface from
  Step 1.2 but internally launches the vendor GDB server and drives it via GDB/MI. **Nothing above the
  adapter changes** — the entire payoff of the day-one two-probe abstraction.
- **Weigh:** both vendor servers are proprietary, free-to-use with terms, vendor-locked. Optional
  backends; not load-bearing in the core.

---

## STAGE 8 — The capability ladder (post-MVP ambition, climbed empirically)

**The ambition:** push the agent from "fix a bug" toward "write board init from scratch" and even
"build a multithreaded OS by itself" using only the standard STM libraries (HAL/LL/CMSIS).

**The crucial good news — the tool suite barely changes.** Whether the agent fixes a one-line
register bug or writes a scheduler from scratch, it needs the *same* hardware interface: flash, halt,
read registers/memory, read serial, breakpoints, resolve symbols. Higher ambition does NOT mean new
hardware adapters — it means the **brain + skills layer** does more with the tools you already built.
So this is not a tooling expansion; it's a brain/skills expansion on the existing Stage 1–3 foundation.

**Treat it as a ladder, not a binary goal. Climb it empirically.** Each rung uses the same tools with
a harder *diagnosis* problem and richer *skills* required:

```
fix-a-bug (MVP)
  → modify-a-driver
    → write-a-driver-from-scratch
      → board-init-from-scratch (clocks, peripherals, interrupt vectors)
        → simple scheduler (cooperative, then preemptive)
          → multithreaded OS
```

**Two distinct claims live inside "the AI does this autonomously" — keep them separate:**

1. **"The AI writes the code" — plausible, mostly a code-generation problem.** Board bring-up and
   basic schedulers are heavily-documented, patterned domains frontier models handle well, *especially*
   with skills injection feeding the chip's reference-manual details and standard-library conventions.
   "AI produces plausible from-scratch init/scheduler code" is realistic.
2. **"By itself / autonomously, verified, no human" — research frontier, and NOT a code problem.** The
   difficulty explodes on *diagnosis*, not authorship:
   - **The bugs become the hardest in the field:** race conditions, deadlocks, priority inversion,
     stack overflow on context switch, memory corruption that manifests far from its cause. Hard for
     expert humans with full tooling.
   - **Nondeterminism breaks the ground-truth loop.** Concurrency bugs often appear ~1 run in 50, so
     the agent can't reliably tell "my fix worked" from "I got lucky." This is the convergence problem
     at its worst.
   - **Bring-up undermines your own observability.** The loop leans on serial + registers. But if the
     agent is writing clock/UART init from scratch and gets it wrong, UART doesn't work — the agent is
     blind exactly when it most needs to see. Early bring-up must lean on the **SWD/debug-probe**
     channel (register reads work before the chip is initialized) rather than serial — so the brain has
     to reason about *which observability channel is even available at each bring-up stage*. (Usefully,
     your tool suite already has the SWD channel; the challenge is orchestration, not a missing tool.)

**Why climbing empirically is the point:** find the rung where the autonomous loop stops converging
reliably. *That boundary is your actual product frontier and your most valuable piece of knowledge* —
it's also where real differentiation from competitors (climbing the same ladder) is found. You learn
it by building the lower rungs and watching where it breaks; no amount of planning substitutes for it.

**Honest positioning at the high rungs:**
- "AI writes your OS bring-up and you review it" → real, valuable, achievable.
- "AI autonomously produces a *verified* multithreaded OS, no human in the loop" → research-frontier;
  be skeptical of this claim from anyone (you, BootLoop, anyone) on concurrency bugs specifically. The
  observability + nondeterminism problems are genuinely hard, not merely effort-away.

**Skills are the lever here, not models.** You can't win on having a better model. You can win on
skills depth (per-chip reference-manual knowledge, standard-library idioms, known-good init sequences)
and on the diagnosis/observability orchestration that makes the loop converge on hard bugs. Both are
the moat work already identified — Stage 8 just raises the stakes on them.

---

## The dependency spine (what blocks what)

```
Stage 0  (BOTH boards: toolchain known-good; nRF recover proven)
   └─▶ Stage 1  (BOTH boards: adapters work by hand, behind one probe-agnostic interface)  ◀── EVERYTHING depends on this
          └─▶ Stage 2  (adapters as MCP server, Inspector-validated, both boards)
                 └─▶ Stage 3  (server-side guardrails + externalized state)
                        └─▶ Stage 4  (BYO-agent proven end to end, both boards)  ← shippable product #1
                               └─▶ Stage 5  (turnkey brain + CLI, two chip families of skills)  ← shippable product #2
                                      ├─▶ Stage 6  (scale: multi-agent; remote: HTTP+OAuth)
                                      ├─▶ Stage 7  (vendor GDB backends, on demand)
                                      └─▶ Stage 8  (capability ladder: driver → bring-up → OS;
                                                    same tools, harder diagnosis, deeper skills;
                                                    climb empirically to find the convergence frontier)
```

**Two rules that govern the whole plan:**
1. **Don't build a stage before its predecessor's exit criteria are met** — on *both* boards where the
   stage says both. The temptation is to jump to the MCP/agent layers; resist it until the adapters
   work by hand (Stage 1).
2. **Don't build the hard version before you need it** — blocking before async, stdio before HTTP, open
   backend before vendor backends, one agent before many. Each upgrade is a swap, not a rewrite,
   *because* of an isolation decision made early (the probe-agnostic SWD interface, externalized state,
   the isolated slow-op module).

**Why two co-primary boards is worth the extra Stage 0–1 cost:** it forces the probe abstraction to be
real immediately (J-Link + ST-Link), gives you two chip families of skills from the start, and means
your "supports many boards" claim is proven, not aspirational — at the price of a heavier early setup
(notably the nRF APPROTECT/recover wrinkle). If early effort gets tight, the honest fallback is to lead
the *very first* hand-test on the L476RG (smoothest open-stack path) and bring the nRF up immediately
after — without dropping it to secondary.

---

## Appendix R — Borrowed ideas (captured inline) + the short list of repos worth a look

**This plan is the source of truth.** The valuable *ideas* from the surveyed open repos are captured
below as plan decisions, so you have them WITHOUT pointing Claude Code at repos whose architectures
(OpenOCD-subprocess, single-board, no guardrails, or Rust) *contradict* this plan and would pull a
build off-course. **Where any repo's pattern conflicts with this plan, the plan wins.**

### R.1 — Ideas worth keeping (now part of the plan; no repo visit needed)
- **Serial-sequence batching** *(from stm32-mcp)*: let `read_serial`/UART tooling accept a **batched
  send→delay→expect sequence in one tool call** (real in-process timing, expect-assertions, filtered
  responses) rather than many round-trips. Reduces tool-call overhead and fits the convergence-watching
  design. Build this into the UART tool surface (Stage 1.1 / Stage 2).
- **Tools/adapter/knowledge folder split** *(from xds110_mcp_server)*: the package shape this plan
  already uses (`tools/` + probe-backend adapter + `skills/`) is the right separation — keep tool
  definitions, the pyOCD backend, and skills in distinct layers (Step 1.0 layout already reflects this).
- **Complete tool taxonomy + typed errors** *(from embedded-debugger-mcp)*: aim for a *complete* debug
  tool surface (flash, erase, verify, reset/halt/run/step, HW/SW breakpoints, memory r/w, RTT
  attach/read/write, session mgmt) and return **typed errors** (a `DebugError`-style hierarchy mapped to
  MCP error codes), not bare strings. Use as a completeness checklist for Step 2.1's tool list.
- **Simulation/loopback mode** *(from UnitApi / mcp2serial)*: support a **hardware-free simulation mode**
  for the adapters so logic can be tested without a board attached — useful for the mixed-OS team and CI.
  Add when convenient (cheap to design in early at the adapter interface).
- **Chip-knowledge tool surface** *(from sheetsdata-mcp)*: when building skills (Stage 5), a good shape
  is `read_datasheet` / `check_design_fit → PASS/FAIL/WARNING` style tools. **Self-host the equivalent
  for nRF52/STM32L4 — do not depend on any paid external datasheet API.**

### R.2 — The only repos worth opening NOW (and only for the one noted thing)
Keep these OUT of the shipped tree (scratch/gitignored `reference/` only). For most work, building from
this plan beats referencing them.
- **xds110_mcp_server** (MIT) — glance at its **folder structure** if a concrete example of the
  tools/adapter/knowledge split helps. Structure only; its code is TI/OpenOCD-specific.
- **embedded-debugger-mcp** (MIT, Rust) — a **one-time skim of its tool list** as a completeness check
  against R.1's taxonomy. Nothing else (it's Rust; not portable).

### R.3 — NOT YET: revisit ONLY when you reach the matching stage (don't open now)
These are genuinely useful, just not for current work. Their *core ideas* are already in R.1; open the
repo itself only if you want a concrete example when you actually build that stage.
- **saleae-logic2-mcp** (Apache-2.0) — **revisit at Stage (a)**, logic-analyzer adapter. Reference for a
  stdio MCP instrument server + Saleae capture/decode integration.
- **scope-mcp** (confirm license in-repo) — **revisit at Stage (a)**, oscilloscope adapter. Compact
  FastMCP + SCPI/PyVISA instrument-control example.
- **sheetsdata-mcp** (MIT; client to a *paid* API) — **revisit at Stage 5**, skills design. Its tool
  *shape* is already captured in R.1; self-host the equivalent, don't depend on the paid API.
- **UnitApi/mcp** (Apache-2.0) — **revisit at Stage 5 / guardrails**. Its simulation-mode and
  permission/auditing patterns are already captured in R.1; open only if you want a fuller example.

### R.4 — SKIP entirely (ideas extracted; opening them is worse than building from this plan)
**stm32-mcp, mcp2serial, mcp2tcp, tinymcp** — their useful ideas are already in R.1, and their
architectures *contradict* this plan (OpenOCD-subprocess, single-board, cloud-mediated) or are
simpler/less specific than what you're building. Don't point Claude at these at any stage.

### R.5 — Tools you install, never clone
- **pyOCD** — your SWD backend; a dependency in `pyproject.toml`, not a repo to reference.
- **probe-rs** — a Rust *alternative* to pyOCD. **Don't clone, don't switch languages.** Only if pyOCD
  proves unreliable on a board in real testing (watch nRF52 quirks: pyOCD issues #1455 SWO, #1540 reset)
  add it as a **`ProbeRsBackend` behind the Stage-1 SWD interface**, via **subprocess to the probe-rs
  CLI** — nothing above the adapter changes. Research verdict: likely unneeded for these two boards.

### The principle
**Borrow techniques, not codebases — and once a technique is captured here, the repo has served its
purpose.** None of these repos contains your moat (safety gate, convergence watcher, session state,
skills); that's yours to build in Python. A repo that's functionally close but architecturally divergent
(e.g. stm32-mcp) is *more* hazardous as a live reference than an irrelevant one, because a build can
absorb its contradicting patterns — which is exactly why its one good idea is lifted into R.1 and the
repo itself is off the list.

## Verification Status

Verified:

- The current checked-in repo now uses `src/pyocd_debug_mcp/` as the canonical
  product-code path and `nrf52833dk` as the official scoped Nordic board in
  the Phase A docs.
- The canonical Windows `R0` bootstrap path has been verified on a real
  Windows host.
- The `nucleo_l476rg` reference baseline now has real Stage 0 flash and UART
  proof on the Mac bench.
- The official `nrf52833dk` board now has real Stage 0 proof, Stage 1 smoke
  proof, and live MCP surface validation on the Mac bench.
- The repo now contains the tracked R12 contract doc, native Python brain
  package, board-aware skills tree, `pyocd-debug-brain` CLI, and sibling
  turnkey benchmark path over the same frozen 12-case corpus.

Pending verification:

- Exact official-pair `nrf52833dk + nucleo_l476rg` R12 closure on the current
  branch state remains pending until an actual `nrf52833dk` is attached again.
- `nrf52840dk` is a retained alternate Nordic profile. It now has live attached
  proof in later R12 runs, but that proof does not replace the official
  `nrf52833dk` gate.
- The Codex-backed R12 turnkey path is live-proven on the scoped pair through
  the full frozen 12-case corpus.
- The Claude CLI provider is no longer globally blocked by the old macOS
  `claude-cli --model sonnet` provider-side 404. Later Windows/attached-board
  proof exists for `nucleo_l476rg + nrf52840dk`; API-provider parity
  (`openai-api`, `anthropic-api`) and exact official-pair second-provider proof
  remain pending.
