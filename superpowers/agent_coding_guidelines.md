# Coding Agent Guidelines — Agentic Firmware Debug Tool

> **Purpose.** Standing rules for any AI agent writing code or implementation docs for this project.
> These are not generic "write clean code" tips — they target the *specific* ways an agent tends to
> go wrong on a hardware-tooling project: hardcoding environment values, reimplementing mature
> libraries, and — most dangerous — claiming things work without having verified them against real
> hardware it cannot actually reach.
>
> **Read this whole doc before starting any task. Re-read the relevant section before each commit.**

---

## 0. The prime directive: never claim what you didn't verify

This project controls physical hardware you (the agent) usually **cannot touch**. Your single most
important obligation is to be honest about the boundary between what you *verified* and what you
*assume*.

- **Never report "this works" / "flashing succeeds" / "the board responds" unless a real execution
  against real hardware produced that result in this session.** If you didn't run it on the board, say
  so explicitly: "this should work pending hardware verification — I have not run it on a board."
- **Mark every unverified claim.** Use a clear tag in code comments and in docs, e.g.
  `# UNVERIFIED: needs hardware check` or a "Pending hardware verification" list at the end of a doc.
- **Distinguish three states explicitly in any status you report:** (a) verified by running it here,
  (b) verified by a non-hardware check (unit test, type check, lint, dry-run), (c) unverified
  assumption. Never let (c) masquerade as (a).
- **If a step requires hardware you can't access, STOP and hand off** with a precise, runnable
  instruction for the human ("run `X`; expected output `Y`; report back") rather than guessing the
  outcome and proceeding on the guess.

Confident-but-wrong is far more expensive here than "I'm not sure" — a false "it flashes" can send a
human chasing a phantom bug, or worse, brick a board.

---

## 1. No hardcoding — environment values come from config or discovery

The mixed macOS+Windows team makes this non-negotiable from the first line.

- **Never hardcode a serial port.** It comes from board config or pyserial enumeration. (`COM3` vs
  `/dev/tty.usbmodem…` is the #1 "works on my machine" failure.)
- **Never hardcode file paths or path separators.** Use `pathlib`. Reference the canonical repo layout;
  don't invent paths.
- **Never hardcode a `pyocd` target, baud rate, probe type, or board id in code.** These live in
  `boards/<board>.yaml` and are read through the one board-config loader.
- **No secrets/keys in code.** Config or environment only.
- **No OS-specific assumptions** (shell commands, line endings, drive letters). If you must branch on
  OS, isolate it in one clearly-labeled place, never sprinkled.
- **Rule of thumb:** if a value would differ on another machine, another board, or another OS, it is
  config or discovery — not a literal in the code.

---

## 1b. Origin tags — every meaningful value declares where its authority comes from

Any non-obvious value — in **code comments AND in `.yaml`/config files** — must carry an **origin tag**
saying where it came from and therefore who is allowed to change it and which source of truth to consult.
This matters on a multi-board project: a future reader (human or agent) must know whether a value was
handed down by the silicon, by a tool, or chosen by us.

**The vocabulary (use these exact tags):**
- **`HW-FIXED`** — dictated by the silicon or a hardware spec. Source of truth = the **chip datasheet /
  reference manual**. Changing it doesn't make a new choice; it makes the code *wrong*. (e.g. a flash
  base address, a peripheral register address, SWD being 2-wire.)
- **`VENDOR-FIXED`** — a contract with an external tool/library/protocol you don't control. Source of
  truth = **that tool's docs**. Can *drift with versions*. (e.g. a `pyocd` target string, an `mcp`
  protocol field name, a pyserial parameter name.)
- **`PROJECT-DEFINED`** — a choice *we* made that could reasonably have been otherwise. Source of truth
  = **our own decisions / this plan**. Changeable as a design decision. (e.g. `board_id` strings, the
  directory layout, tool names, timeout values, convergence thresholds.)

**Plus an orthogonal marker (combine with an origin tag when it applies):**
- **`UNVERIFIED`** — the value is a best guess **not yet confirmed against its source of truth**. Ties
  directly to §0. A target name written from memory is `VENDOR-FIXED, UNVERIFIED` until `pyocd list
  --targets` confirms it on the actual board. Remove `UNVERIFIED` only after real confirmation.

**In code (comment next to the value):**
```python
FLASH_BASE = 0x00000000      # HW-FIXED (nRF52840 datasheet §flash)
DEFAULT_TIMEOUT_S = 30       # PROJECT-DEFINED (our v1 default; tune later)
```

**In YAML (inline comment per field):**
```yaml
board_id:        nrf52840dk     # PROJECT-DEFINED (our canonical id)
mcu_family:      nrf52840        # HW-FIXED (the silicon)
pyocd_target:    nrf52840        # VENDOR-FIXED, UNVERIFIED (confirm via `pyocd list --targets`)
serial_baudrate: 115200          # PROJECT-DEFINED (our chosen default; matches reference firmware)
probe_family: jlink              # HW-FIXED (the onboard debug probe family)
```

**Why the three-way split (not just "fixed vs. ours"):** the tag tells the reader *which authority to
consult* when a value looks wrong — datasheet (`HW-FIXED`), tool docs (`VENDOR-FIXED`), or our own plan
(`PROJECT-DEFINED`). Collapsing HW and VENDOR loses that, and they fail differently: a vendor value can
break on a library upgrade; a hardware value cannot.

**Don't tag the obvious.** Loop counters, local temporaries, self-evident literals don't need tags —
only values whose *origin and changeability* a future reader would need to know. When unsure, tag it.

---

## 2. Read everything before writing anything

- **Read the current build plan and this doc before each task.** Decisions already made (blocking v1,
  CMSIS-DAP default, session-keyed state, data-not-branches board config, the repo layout) are binding
  — do not silently re-decide them. If you think a prior decision is wrong, **flag it and ask**, don't
  quietly diverge.
- **Read the actual files you're about to touch, in full, before editing.** No editing from assumption
  about what a file contains.
- **For any library call (pyOCD, pyserial, `mcp`), confirm the exact current API** against the
  installed version's docs — do not write the call from memory. Library APIs drift; this project's plan
  repeatedly flags "verify the exact call at build time" for this reason.
- **Read the relevant board's `boards/<board>.yaml`** before writing board-touching code, so you use
  real field names, not invented ones.

---

## 3. Build on the libraries — do NOT reimplement them

- **Flashing, SWD debug, register/memory reads, breakpoints, nRF unlock → pyOCD already does these.**
  Your code is a *thin wrapper* calling pyOCD. If you find yourself implementing flash-sector erase or
  SWD protocol, STOP — you're rebuilding what exists.
- **Serial open/read/write/timeout/cross-platform port handling → pyserial already does these.** Wrap,
  don't reimplement.
- **MCP protocol plumbing → the `mcp` SDK + FastMCP do this.** Use the decorators; don't hand-roll
  JSON-RPC.
- **Where your real code lives** (and the only place to spend real effort): the uniform adapter
  interface, the MCP tool wrappers, and the safety/convergence/logging/skills layer. That last layer is
  the product; the libraries are the hands it uses.

---

## 4. Smoke-check everything you can, at the lowest level possible

- **After any change, run the cheapest check that proves it before moving on.** Prefer: type check →
  lint → unit test → dry-run → (hand off for) hardware test. Don't skip to "done."
- **Test adapters in isolation before wiring them into the server; test tools in the MCP Inspector
  before wiring a real agent.** (The plan mandates Inspector-before-real-client because schema errors
  fail *silently* in the client.)
- **Write a smoke test alongside each component** — the minimal "does this basic thing work at all"
  check, runnable without ceremony.
- **Never report a component complete without stating which smoke checks ran and which are still
  pending hardware** (ties back to §0).
- **Destructive operations get extra care:** anything that flashes or unlocks/mass-erases must go
  through its safety gate and must be tested in a way that *cannot* accidentally brick a board (gate
  tests use refusals and dry-runs, not live destructive flashes, unless a human explicitly authorizes).

---

## 5. Small, isolated, reversible changes

- **One concern per change.** Don't mix an adapter refactor with a new feature with a config change.
- **Respect the layering** (adapter ↔ tool ↔ server ↔ guardrails ↔ brain). A change should live in one
  layer; if it forces edits across many, stop and reconsider the design before proceeding.
- **Keep the abstractions intact:** probe differences stay behind the SWD interface; board differences
  stay in config; OS differences stay isolated. Don't let a quick fix leak a probe/board/OS specific
  into a layer that's supposed to be generic.
- **Prefer changes that are easy to undo.** Note in the change what would reverse it.

---

## 6. Document honestly, in the project's style

- **Implementation docs distinguish decision from code** (this project deliberately separates the two).
  Write the *what and why*; leave exact code to the code, unless a snippet is the clearest way to show a
  decision.
- **Every doc you write ends with two lists:** "Verified" and "Pending verification (esp. hardware)."
- **Record assumptions explicitly.** If you assumed a pyOCD target name, a baud rate, a field name —
  say so and mark it for confirmation. Never present an assumption as established fact.
- **Don't over-format.** Match the existing docs: prose and minimal structure, not walls of bullets and
  bold. (Yes, this doc uses headers — a guidelines reference is the exception, not the model for every
  doc.)
- **No invented citations or fabricated tool output.** If you reference behavior, it's either something
  you verified or something marked unverified.

---

## 7. When in doubt, stop and ask — don't guess forward

- **Ambiguity about a prior decision, a hardware result, or a library API → ask or hand off**, don't
  pick a guess and build a tower on it. A wrong guess at the bottom is expensive at the top.
- **Detect non-progress in yourself.** If you've attempted the same fix twice without a different
  result, stop and escalate rather than thrash — the same discipline the product's own convergence
  watcher enforces.
- **Never expand scope silently.** If a task seems to require a decision not yet made in the plan
  (shipped-OS support, packaging format, a new board field), flag it as a decision needed, don't
  unilaterally settle it in code.

---

## Quick pre-commit checklist
- [ ] No hardcoded ports, paths, targets, baud rates, or OS assumptions (§1)
- [ ] Every non-obvious value (code AND yaml/config) carries an origin tag: `HW-FIXED` / `VENDOR-FIXED` / `PROJECT-DEFINED`, plus `UNVERIFIED` where it's still a guess (§1b)
- [ ] Read the files I touched and confirmed library calls against current docs (§2, §3)
- [ ] Didn't reimplement what pyOCD / pyserial / `mcp` already provide (§3)
- [ ] Ran the lowest-level smoke checks available; stated what's still pending hardware (§4)
- [ ] Change is one concern, in one layer, abstractions intact (§5)
- [ ] Status honestly separates verified / non-hardware-verified / unverified (§0, §6)
- [ ] Flagged (not silently decided) anything that needed a new decision (§7)
