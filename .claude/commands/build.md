---
description: "Spec-driven loop step 2 — implement a spec (or apply review findings) with code+docs moving together, smoke-checked, hardware honestly handed off"
argument-hint: "<path to *_spec.md>  [and/or <path to *_review.md> to fix findings]"
---

# /build — implement the spec, keep code and docs together

You are in the **build** phase of the spec → build → review loop. Implement exactly what the spec
defines — no more (no silent scope expansion), no less.

Input(s):

> $ARGUMENTS

If a `*_spec.md` is given, implement it. If a `*_review.md` is also (or only) given, you are on a
**re-build pass**: fix the review findings (highest severity first) and nothing else. If no path is
given, look for the most recent `markdowns/curr/*_spec.md`.

## Step 0 — reconcile before you write (the gate)

Per the consistency playbook, before touching any file:

1. Read `superpowers/agent_consistency_playbook.md`, `markdowns/firmware_agent_build_plan_concrete
   (10).md`, and `superpowers/agent_coding_playbook.md` — always, every build.
2. Read the spec (and review file) in full, plus the **current `main` state of every file you will
   touch**, in full.
3. Re-check the spec's reconciliation list still holds against current code. If the spec is stale or now
   conflicts with the plan, STOP and surface it — do not build on a contradiction.
4. Confirm the change is settled-decision-safe: do not silently re-decide a settled plan choice
   (pyOCD-in-process, native-probe-default-with-CMSIS-DAP-fallback, blocking-v1, board-facts-as-data,
   session-keyed state, shared-services-below-both-frontends). If the spec requires changing one, that
   is a user sign-off event — ask first.

## Step 1 — implement, respecting the rules that are specific to this repo

- **Verify, don't claim (§0 coding playbook).** You control physical hardware you cannot touch. Never
  write or report "this works / it flashes / the board responds" for anything not actually executed on a
  real board in this session. Tag unproven code `# UNVERIFIED: needs hardware check`.
- **No hardcoding (§1).** No serial ports, paths, pyOCD targets, baud rates, probe types, or OS
  assumptions as literals. Ports come from discovery; board facts from `boards/<board>.yaml` through the
  one loader; paths via `pathlib`.
- **Origin tags (§1b).** Every non-obvious value, in code AND yaml, carries `HW-FIXED` /
  `VENDOR-FIXED` / `PROJECT-DEFINED`, plus `UNVERIFIED` where still a guess.
- **Build on the libraries, don't reimplement them (§3).** pyOCD does flashing/SWD/registers/unlock;
  pyserial does serial; the `mcp` SDK does protocol. Your code is the thin wrapper + the shared services
  + guardrails/brain. If you're writing flash-sector erase or JSON-RPC by hand, STOP.
- **Confirm library calls against the installed version (§2)** — do not write pyOCD/pyserial/`mcp` calls
  from memory.
- **Respect the layering (§5).** One concern, one layer. Probe specifics stay behind the SWD interface /
  `board_config` — never scattered `if probe == ...` / `if board == ...`. Go through the shared
  `target_control.open_session()` / `adapters.swd_pyocd` path; do not call `ConnectHelper` directly from
  new code (see current-progress.md "Rule for future files").
- **Destructive ops gate.** Anything that flashes or unlocks/mass-erases routes through its safety gate
  and is tested with refusals/dry-runs, never a live destructive flash unless the user explicitly
  authorizes.

## Step 2 — docs move with the code, in the SAME unit of work

A change is **not done** until the docs reflect it (doc-sync playbook §0). For every change, update the
ONE right doc at the right level:

- architecture / decision / stage / tool-surface / board / config-field / layout → **amend the build
  plan in place** (with sign-off if it's a settled decision);
- a how-we-write rule → the relevant **playbook**;
- an MCP tool's behavior/inputs/returns/guard text → that tool's **docstring in `server.py`** (never a
  sidecar `.md`);
- a bench/setup script's sequence/flag/ready-signal/failure-mode → **`stage0_setup.md`**.

Edit the now-wrong statement; don't append a contradicting note above stale text. Keep cross-references
(step numbers, tool names, paths) valid.

## Step 3 — smoke-check at the lowest level possible

Run the cheapest checks that prove the change before declaring anything (coding playbook §4):

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

(Scope `mypy`/`pytest` to the touched modules when a full run is noisy, matching how
`current-progress.md` already invokes them.) For MCP tool changes, validate in the Inspector
(`uv run mcp dev src/pyocd_debug_mcp/server.py`) — schema errors fail *silently* in a real client. If a
check fails, fix the root cause; do not skip ahead to "done." Report the actual command output, not a
claim.

## Step 4 — hand off what you cannot verify

You cannot reach the boards. For every acceptance criterion that needs real hardware, STOP and emit a
precise, runnable hand-off — the exact command, the expected output, and "report back" — drawn from the
`current-progress.md` regression checklist (Stage 0 → Stage 1 smoke → MCP runtime matrix on the scoped
pair). Never guess a hardware outcome and proceed on the guess.

## Step 5 — report honestly

End your reply with a status that **separates the three states**: (a) verified by running it here, (b)
verified by a non-hardware check (which check, what output), (c) unverified assumption / pending
hardware. Then list: files changed, docs synced (which doc, which section), every `⚠️` conflict or
new-decision surfaced, and the single line:
**"Build pass complete. Run `/review <spec-path>` to check it."**
