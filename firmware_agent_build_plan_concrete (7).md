# Agentic Firmware Debug Tool — Concrete Build Plan (step-ordered)

> **Scope of this document.** This is the *design + implementation plan* — what to build, in what
> order, and the design decision behind each step. It deliberately stops short of writing the code
> itself: where a design choice is straightforward, the "how" is stated plainly; where it isn't, the
> decision is specified and the coding is left to build time. Trying to settle both the plan and the
> code at once is where errors creep in, so this stays at the plan level.
>
> **Hardware — TWO co-primary boards (build and prove the loop on both):**
> - **Nordic nRF52840-DK** — onboard **SEGGER J-Link**; UART → virtual COM port; SWD + UART on one
>   USB. Radio-relevant (BLE/802.15.4). *Wrinkle to plan around:* J-Link's native protocol isn't
>   pyOCD's native CMSIS-DAP, and nRF52 **APPROTECT** can lock the chip (needs a `recover`/unlock).
> - **STM32 Nucleo-L476RG** — onboard **ST-Link/V2-1**; UART on **USART2 @115200 8N1**; SWD + UART on
>   one USB. Cleanest open-stack path (pyOCD/OpenOCD support ST-Link out of the box).
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
`mcp` SDK and pyOCD both want a reasonably recent Python). 
Selection: 3.11

**Dependency versions:** don't pin thoughtfully upfront — install current versions, **commit a
lockfile** (`pyproject.toml` + lock, or `requirements.txt`) so the mixed team stays in sync, then pin
"what worked" once it works and revisit later. The lockfile matters *more* with a team than it would
solo, because it keeps two OSes' environments matched so a bug isn't an environment mismatch in disguise.



**Per-OS bootstrap docs — authored incrementally, not planned upfront.** The first teammate to set up
each OS writes a short "on macOS do X / on Windows do Y" onboarding note as they go, so the next person
on that OS has a path. This is a Stage-0 byproduct of setting up your own machine, not a document to
pre-write from guesses.

-------------------------------Do Not Implement Until Stage 3----------------------------------------
**Redis (external state store, not needed until Stage 3):** a single local Redis is the obvious default
when you reach Stage 3.2. Defer until then.
----------------------------------------------------------------------------------------------

Shiptime Notes:
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
**Do every step for the nRF52840-DK AND the L476RG.**

1. **Confirm each board's pyOCD target name** (`pyocd list`, `pyocd list --targets`; install the
   CMSIS-Pack if prompted). Expect roughly `nrf52840` and an `stm32l476`-family target. *Why first:*
   the generic `cortex_m` type debugs but **cannot program flash** — the "connects but won't flash" trap.
2. **Probe-specific setup:**
   - **nRF52840-DK (J-Link):** install SEGGER J-Link software (drivers). Decide pyOCD's route to the
     J-Link (CMSIS-DAP mode vs. SEGGER path) and **test a flash + a recover/unlock cycle** — confirm
     you can recover the chip if APPROTECT locks it. This is the nRF's one real setup risk; clear it now.
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
> not on anything you embed in your code. Standardize the shipped product on **pyOCD-over-CMSIS-DAP**
> and the heavy proprietary packages (SEGGER especially) are not needed at runtime.
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
> **Why this reinforces the CMSIS-DAP-for-the-product decision:** standardizing on CMSIS-DAP shrinks
> the customer's required OS-level setup to the lightest case (often just a udev rule / WinUSB assoc),
> which your installer can automate. The native-J-Link path (Stage 7) reintroduces a
> "customer must install SEGGER's proprietary software" requirement — a real deployment cost, and
> another reason it's an opt-in upgrade, not the default.
>
> **Dev bench vs. shipped product:**
> - *You, in Stage 0:* install everything (SEGGER software, ST drivers) — safest way to get both
>   boards working and to have vendor fallback tools. A dev convenience, not a shipping commitment.
> - *Shipped product:* pyOCD + device packs as Python deps; standardize on CMSIS-DAP; automate the
>   light USB setup; detect-and-instruct for anything proprietary; never redistribute vendor drivers.
>
> **Verify empirically in Stage 0 (platform/board-specific, don't trust the general picture):** whether
> a given CMSIS-DAP probe needs Zadig on Windows, what udev rules pyOCD needs on Linux, and especially
> **whether the DK's onboard J-Link presents cleanly as CMSIS-DAP without any SEGGER component present**
> (onboard probes can behave differently from standalone CMSIS-DAP probes).

---

## STAGE 1 — Adapters, hand-tested in isolation (the first mile), on BOTH boards

**Goal:** drive both boards from plain Python before any MCP/agent layer.
**Design rule:** each adapter is a small class with a stable method interface; test from a REPL until
boringly reliable. The probe differences (J-Link vs ST-Link) must hide *behind* the SWD interface.

### Step 1.0 — Define the canonical repo & artifact layout FIRST (do before any adapter code)
**Why first:** `flash_firmware`, `apply_patch`, bug injection, recovery-image logic, logging, and the
agent itself all need to *find* files. If each invents its own path convention they won't compose. This
is one ten-minute decision that prevents six components from diverging. Decide it now, commit it, point
all later tooling at it. (Not in Stage 0 — Stage 0 is hand-testing with no code/paths yet.)

**Canonical directory layout:**
```
firmware-agent/
├── pyproject.toml + lockfile        # deps + pinned versions (team sync, see Scope Assumptions)
├── src/firmware_agent/              # all product code
│   ├── adapters/                    # uart.py, swd_interface.py, swd_pyocd.py
│   ├── tools/                       # MCP tool/resource definitions + dispatch
│   ├── guardrails/                  # flash gate, unlock gate, convergence watcher, logging
│   ├── server/                      # FastMCP server wiring
│   └── brain/                       # turnkey client + skills loader (Stage 5)
├── boards/                          # ONE config file per board (board definitions)
│   ├── nrf52840dk.yaml              #   pyocd target, default baud, probe path, recovery-image ref
│   └── nucleo_l476rg.yaml           #   (USART2, 115200, stm32l476 target, …)
├── firmware/                        # all firmware ARTIFACTS + sources, per board
│   ├── nrf52840dk/
│   │   ├── reference/src/           #   reference firmware SOURCE tree (known-good, builds clean)
│   │   ├── reference/build/         #   compiled known-good ARTIFACT (the baseline binary)
│   │   ├── recovery/                #   known-good RECOVERY image the safety/unlock gates require
│   │   └── bugs/                    #   injected-bug VARIANTS (see naming below)
│   └── nucleo_l476rg/               #   (same shape)
├── skills/                          # per-chip/peripheral knowledge data files (Stage 5)
│   ├── nrf52840/
│   └── stm32l476/
├── runs/                            # all runtime OUTPUT, keyed by session id
│   └── <session_id>/                #   logs/, captured-serial/, applied-patches/, run-metadata
└── tests/                           # injected-bug test definitions, harness
```

**Naming conventions (the part that's more than "pick a folder"):**
- **Boards:** lowercase board id used everywhere — `nrf52840dk`, `nucleo_l476rg`. Every per-board path
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

**Required v1 core (needed by Stage 2; every field traces to a decision already made):**
```yaml
board_id:            nrf52840dk          # the one canonical id (Step 1.0); keys all per-board paths
display_name:        "Nordic nRF52840-DK"
mcu_family:          nrf52840            # selects which skills/ dir applies (Stage 5)
probe_family:        jlink               # jlink | stlink — selects SWD backend (Stage 7 vendor swap)
pyocd_target:        nrf52840            # the Stage-0 confirmed target (the won't-flash trap)
serial_baudrate:     115200
reference_firmware_path: firmware/nrf52840dk/reference/build/firmware.elf
recovery_image_path:     firmware/nrf52840dk/recovery/        # what the safety + unlock gates check
```

**Add later, when its stage arrives (listed so the omission is intentional, not forgotten):**
- `reference_uart_patterns` — **Stage 4** (test harness). What "success/failure" looks like over serial;
  you can't write good patterns until you've seen real output.
- `recover_command` / `recover_mode` — **Stage 3.1b**. Likely just a flag, since the nRF unlock is
  pyOCD's built-in `auto_unlock`/mass-erase, not a custom command string.
- `register_aliases` — **Stage a / debug surface**. Convenience for the agent's register reads; you'll
  know which aliases matter only once it's actually reading registers.
- `probe_discovery_hints` / `serial_discovery_hints` — **only if needed.** Given the mixed-OS team,
  discovery is best driven by pyserial/pyOCD *enumeration*, which may make per-board hint strings
  unnecessary. Don't bake these in speculatively; add only if enumeration proves insufficient.
- `memory_protection_rules` — **already covered** by the guardrails (fuse/option-byte refusal, APPROTECT
  case in Steps 3.1/3.1b). Don't duplicate that logic into a vague config field; extend only if a real
  per-board protection rule appears that the gates can't express generically.

**Decision — validate the schema:** every component reads board config through one small loader that
validates the required core is present and fails loudly on a malformed/incomplete board file (a missing
`pyocd_target` should be an obvious error, not a silent wrong-target flash). One loader, one schema, one
source of truth — not each component parsing the YAML its own way.

**Exit:** the minimal schema + one loader committed; both boards have a valid `boards/<board>.yaml`; the
"data-not-branches, grows-per-stage" rule documented in the repo README.

### Step 1.1 — UART adapter (build first; easiest; board-agnostic)
- **Design:** `open() / read_lines() / write() / reopen()`, 115200 8N1. One adapter works for both
  boards — UART is the same; only the COM port differs.
- **Decision baked in now:** `reopen()` from the start — the Nucleo VCP can drop on reset/reflash, and
  reconnect-after-flash is good hygiene on both boards.
- **Exit:** see each board's reference firmware output in your own Python script.

### Step 1.2 — SWD adapter as an interface + pyOCD backend (this is where two probes pays off)
- **Design — the central decision of this stage:** one *abstract SWD interface*
  (`connect / flash / reset_and_halt / halt / resume / read_register / read_memory / resolve_symbol`),
  with the pyOCD calls inside a backend. Because you're running **both** a J-Link board and an ST-Link
  board, the interface has to genuinely abstract the probe from day one — you can't accidentally bake
  in ST-Link assumptions. That real-from-the-start abstraction is what makes later vendor GDB backends
  (Stage 7) a clean drop-in.
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
- **Design:** `@mcp.tool()` / resource decorators wrapping Stage-1 adapter methods. stdio only (local,
  no auth, lowest latency; the natural fit since the server must sit next to the board).
- **Decision — primitive split:** actions = **tools** (`flash_firmware`, `reset_and_halt`, `halt`,
  `resume`, `apply_patch`, `unlock_recover` [gated — destructive, see Step 3.1b]); read-only data =
  **resources** (`read_serial`, `read_register`, `read_memory`, `resolve_symbol`).
- **Decision — return types:** return typed text/content blocks (strings), **not raw dicts** (raw
  dicts can truncate silently in the client though they look fine in the Inspector).
- **Decision — board selection:** target + port are server config/params, so one server binary serves
  either board. (At scale, one server instance per board — see Stage 6.)

### Step 2.2 — Validate every tool with the MCP Inspector, against both boards
- **Why before a real client:** schema errors fail *silently* in a real client; the Inspector surfaces
  them. Exercise each tool by hand here, on each board.

### Step 2.3 — `apply_patch` design decision
- **Decision:** v1 = full-file rewrite (simpler, reliable). Diffs later (auditable, finer, harder to apply).

### Step 2.4 — Long-running operations: BLOCKING for v1
- **Decision (settled):** v1 uses **blocking** tool calls, not the async/ticket pattern — the debug
  loop is inherently sequential on a single board, so there's no independent work to parallelize.
- **But:** hardware work runs in a **background worker** so the server stays responsive (honors cancel,
  no freeze, no transport timeout). Blocking ≠ frozen server.
- **Forward-compat hook (cheap, do now):** isolate "run a slow op" behind one internal interface, so a
  later move to the ticket pattern / MCP Tasks extension reimplements *one* module. Don't build the
  ticket pattern yet.

**Stage 2 exit criteria:** a local stdio MCP server whose every tool/resource works in the Inspector,
verified on both boards.

---

## STAGE 3 — Deterministic guardrails IN THE SERVER

**Goal:** durable guarantees *below the brain* so they bind every client (yours or a user's Claude
Code). **Design rule:** guardrails are deterministic code, not model judgment.

### Step 3.1 — Pre-flash safety gate (first guardrail)
- **Design:** inside `flash_firmware`, before hardware is touched — validate image, refuse
  fuse/option-byte writes, require a known-good recovery image. Unsafe → refuse via the protocol.
- **Board note:** include the nRF APPROTECT/lock case — the gate (and recovery image) is what makes a
  locked nRF recoverable rather than a dead end. *Why first:* it prevents the most expensive failure.

### Step 3.1b — Gated unlock/recover (SECURITY FLAG — destructive action)
- **What it is:** the nRF APPROTECT unlock is **built into pyOCD** (option `auto_unlock`, default
  **True**; it unlocks by performing a **mass erase**). You do NOT write the unlock logic — your
  `unlock_recover` tool is a thin wrapper over pyOCD's built-in unlock/mass-erase.
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
   (`claude mcp add --transport stdio <name> -- <command>`; config in `~/.claude.json`; verify with
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

1. **Build the brain as a second MCP client** of the same server (reuses Stages 1–3 wholesale).
2. **Add skills injection** — structured per-chip/peripheral knowledge as data files. *The validated
   moat.* **Two boards = two chip families of skills from the start**, which is the right shape for a
   product meant to span many chips (don't over-fit skills to one MCU).
3. **Add loop-aware convergence logic** in the brain (the richer judgment the server can't do for
   external brains — the brain sees its own reasoning arc).
4. **Build the CLI frontend** (board/target, port, ELF, task, max-iters). Embedded engineers live in
   the terminal; GUI later. **This is the only frontend you build, and it belongs to the brain.**
5. **Keys:** BYOK by default (preserves the moat); optionally your keys for a managed offering.
6. **Closed-source:** keep the brain's valuable logic (skills, orchestration) server-side if real
   secrecy matters — local Python decompiles easily. Commodity (adapters) is hard to hide; moat
   (skills) is what you keep server-side.

**Exit criteria:** `your-cli --board <nrf|nucleo> --task ...` runs the full loop turnkey on either
board, with skills + loop-aware convergence the BYO tier lacks.

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
