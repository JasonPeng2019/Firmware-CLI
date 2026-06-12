# Tool-Description & Operator-Guide Playbook — Where Documentation Lives in an MCP Product

> **Why this exists, and what changed.** An earlier version of this playbook required a separate,
> exhaustive `.md` "script-doc" for *every* runnable script, on the premise that *"the operating agent
> is blind to the source — it can only run a script and read its output."* **The MCP architecture
> (see `markdowns/firmware_agent_mcp_architecture.md`) obsoletes that premise for the runtime tools.**
> An MCP client (the user's Claude Code, or the turnkey brain) does **not** run scripts and read sidecar
> markdown. It calls MCP tools and sees exactly three things over the protocol: the tool **name**, the
> tool **description** (the function's docstring), and the **input schema** + **typed return** (the
> "handle"). It never reads a `.md`. So for an MCP tool the agent is *not* blind to the tool — the
> docstring IS its interface, and the docstring lives in the code.
>
> Maintaining a sidecar `.md` per MCP tool therefore documented the tool in a place the agent can never
> read, while duplicating the docstring that it *does* read — pure drift surface. This playbook replaces
> "a script-doc for every file" with two precise rules:
>
> 1. **MCP tool documentation lives in the tool's docstring, in the code** (§1).
> 2. **Bench/setup scripts that a human or terminal agent runs get ONE operator guide**, not one doc per
>    script (§2).
>
> **Read this whenever you add or change an MCP tool, or any setup/bench script the operator runs.**

---

## 0. THE PRINCIPLE: document each thing in the one place its reader actually looks

There are two readers and two surfaces. Put each kind of documentation where its reader will see it,
and nowhere else.

| Surface | Who reads it | Where its documentation MUST live |
|---|---|---|
| **MCP tools** (`@mcp.tool()` / resources in `server.py`) | the MCP **client agent**, over the protocol | the function **docstring** + type-hinted signature + typed return string |
| **Bench/setup scripts** (`setup_host.*`, `host_bootstrap.py`, `stage0_check.py`, recover helpers) | a **human or terminal agent** at a shell, before/around the server | **one operator guide** (`stage0_setup.md`) covering sequence + troubleshooting |

The cardinal error this playbook now prevents is the inverse of the old one: **do not write a sidecar
`.md` to document an MCP tool.** The client can't read it, and it will drift from the docstring the
client *does* read.

---

## 1. MCP TOOL DESCRIPTIONS — the docstring is the interface

For anything exposed through the MCP server (`src/pyocd_debug_mcp/server.py`), the docstring is the
*entire* contract the model sees. Treat it with the rigor the old script-docs demanded — but put it in
the code, not beside it.

**Every `@mcp.tool()` / resource docstring must make the model able to:**
- **decide WHEN to call it** — one plain sentence on what it does and the state it expects (e.g. "Open a
  debug session to a connected probe" / "Call `connect` first").
- **choose the RIGHT inputs** — document every argument in the docstring's `Args:` block: meaning, units,
  accepted forms (e.g. "hex (0x...) or decimal"), and the default/fallback (e.g. "Defaults to the
  `PYOCD_PROBE_UID` environment variable").
- **interpret the RETURN** — the return string is the agent's only feedback. Make returns self-describing
  ("Connected to board '<name>' via probe <uid>.", "Halted.", "0x{value:08X}") and keep them stable;
  the agent pattern-matches on them.
- **recover from refusals/errors** — guard and error strings ARE documentation. Phrase them as the next
  action ("Already connected. Call `disconnect` first to switch probes.", "Not connected to a probe.
  Call `connect` first."). A raised error surfaces to the client as the tool error text, so make that
  text diagnostic.

**Rules that carry over from the Coding Guidelines and the build plan:**
- **Return typed text/content (strings), not raw dicts** — raw dicts can truncate silently in the client
  though they render fine in the Inspector (build plan Step 2.1; Coding Guidelines §3).
- **Destructive tools say so in the first line of the docstring** and route through their gate
  (`flash_firmware`, `unlock_recover`) — consistent with the Stage 3 safety gates. "This is destructive
  / irreversible (mass-erase)" belongs in the description the model reads before it calls.
- **Origin/verification honesty still applies** — if a tool's behavior is unverified on hardware, say so
  where it matters (a comment, and the operator guide's verification section), not as a silent assumption.
- **Validate every tool in the MCP Inspector** (`uv run mcp dev …`) before wiring a real client — schema
  errors fail silently in the client (build plan Step 2.2). The Inspector, not a sidecar `.md`, is how you
  confirm the description/schema the agent will receive.

**Cross-session operating sequence** (which tool to call before which — `connect` before reads, gate
before flash) is *agent-runtime* knowledge. Keep the per-tool slice of it in each docstring ("call
`connect` first"); keep the broader arc in the brain/skills layer (Stage 5), not in a sidecar doc the
server can't serve.

**There is no sidecar `.md` for an MCP tool.** If you find one, it is drift — fold any unique content
into the docstring and delete it.

---

## 2. OPERATOR GUIDE — ONE doc for the bench/setup scripts (not one per file)

`setup_host.*`, `host_bootstrap.py`, `stage0_check.py`, and recover helpers are **not** MCP tools. They
run at a terminal during host bootstrap and Stage 0, before the server is even in play, driven by a human
or a terminal-driving agent. These genuinely are "run it and read stdout" scripts — but they do **not**
each need an exhaustive standalone doc. They need **one operator guide** that an operator follows to take
a fresh machine to a Stage-0-ready bench.

**The single operator guide is `stage0_setup.md`.** It is the consolidated home for what used to be
scattered across `setup_host.md` / `host_bootstrap.md` / `stage0_check.md`. It must contain:

1. **Purpose & entry conditions** — when this bring-up flow is the right one.
2. **Ordered sequence** — the exact commands, in order: `setup_host.{ps1,sh}` → `host_bootstrap.py` →
   `stage0_check.py` → `uv run pyocd-debug-mcp`. State what each step is for in a sentence or two; do not
   reproduce every flag.
3. **Per-script essentials** — for each script, a short block: its one-line purpose, the handful of flags
   an operator actually chooses (`--board-id`, `--install-packs`, `--reference-firmware`, `--recover-test`,
   …), and what "done/ready" looks like. The script's `--help` carries the exhaustive flag list; the guide
   carries the *decisions*.
4. **Branch points & handoffs** — "if probes aren't visible, fix host visibility before Stage 0"; what each
   step must produce for the next (a probe UID for `.env`, a passing host check before board checks).
5. **Consolidated troubleshooting table** — symptom (visible in output) → cause → fix → what to rerun,
   merged across the scripts. This is the salvaged value of the old per-script failure tables; keep it
   rigorous and symptom-first, because the operator diagnoses from output alone.
6. **Verified / Pending verification** — per the Coding Guidelines, especially what is still unproven on
   real hardware.

**Bootstrap/environment specifics** (installing `uv`, the pinned `3.12` interpreter, `.env` /
`pyocd.local.yaml` local overrides) live in `init.md`; **canonical layout and naming** live in
`README.md`. The operator guide links to those rather than duplicating them. One fact, one home.

**When a NEW bench/setup script appears:** do not create a new standalone script-doc. Add its purpose,
its operator-facing flags, its "ready" signal, and its failure rows to `stage0_setup.md`, in sequence. A
second operator guide is warranted only if a genuinely separate operator workflow emerges (not the case
in Phase A).

---

## 3. SYNC: documentation still moves with the code (the drift rule is unchanged)

The Doc-Sync Playbook applies in full — only the *location* of the documentation changed.

- **Change an MCP tool's behavior, inputs, returns, or guard text → update its docstring in the SAME unit
  of work.** A drifted docstring misdirects the client agent exactly as a drifted script-doc once did —
  worse, because it's the only thing the agent sees.
- **Change a bench/setup script's sequence, an operator-facing flag, a "ready" signal, or a failure
  mode → update `stage0_setup.md` in the same unit of work.** Do not let the operator guide lag the
  scripts.
- **Never reintroduce a sidecar per-script `.md`.** If a change makes you want one, the content belongs in
  a docstring (MCP tool) or in `stage0_setup.md` (bench script).

---

## 4. Pre-commit documentation check

For an **MCP tool** change:
- [ ] The docstring lets the model decide WHEN to call, choose inputs, and interpret the return (§1)
- [ ] Every argument is documented in `Args:` with meaning, accepted forms, and default/fallback (§1)
- [ ] Return and guard/error strings are self-describing, stable, and phrased as the next action (§1)
- [ ] Returns typed text, not raw dicts; destructive tools flag it in the first line and route through the gate (§1)
- [ ] Validated in the MCP Inspector; no sidecar `.md` was created for the tool (§1)
- [ ] Docstring updated in the SAME commit as the code (§3)

For a **bench/setup script** change:
- [ ] `stage0_setup.md` carries the script's purpose, operator-facing flags, "ready" signal, and failure rows (§2)
- [ ] Ordered sequence and branch points still correct end-to-end; bootstrap/layout facts left to `init.md`/`README.md` (§2)
- [ ] Consolidated troubleshooting table updated; symptom→cause→fix→rerun intact (§2)
- [ ] No new standalone script-doc introduced; operator guide updated in the SAME commit (§2, §3)
- [ ] Verified vs. Pending-verification stated; UNVERIFIED hardware behavior marked (§2)

---

## The one-sentence version
**In the MCP product the client agent reads tool *descriptions and handles over the protocol, never a
sidecar `.md`* — so an MCP tool is documented in its docstring (in the code), and the human/terminal
bench scripts share ONE operator guide (`stage0_setup.md`) instead of a separate exhaustive doc per
file; documentation still moves with the code, it just lives where its reader actually looks.**
