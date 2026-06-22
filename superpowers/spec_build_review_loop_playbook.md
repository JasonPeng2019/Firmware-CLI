# Spec → Build → Review Loop Playbook — The Project's Slash-Command Workflow

> **What this is.** A set of versioned Claude Code slash commands in `.claude/commands/` that turn this
> repo's superpowers rules into a repeatable, spec-driven workflow. The commands are not generic
> "spec it / build it / review it" prompts — each one **loads and enforces the playbooks you already
> have** (authority order, reconcile-before-writing, verify-don't-claim, origin tags, doc-sync,
> portability, MCP-docstring-as-doc). They make the whole team run the same disciplined loop instead of
> re-deriving it by memory each session.
>
> **Why a loop.** Popularized by Karpathy: spec it out, build it, review it — then feed the review's
> findings back into another build pass until the review is clean. The commands below are that loop,
> wired to *this* project's source of truth (`markdowns/firmware_agent_build_plan_concrete (10).md`) and
> its hardware-honesty constraint (the agent cannot touch the boards, so "done" always stops at a
> hardware hand-off).
>
> **Read this when you want to use the commands, or before editing them.** The commands live in
> `.claude/commands/`; this guide explains how to drive them and how they map onto the playbooks.

---

## The commands at a glance

| Command | Phase | What it does | Reads | Writes |
|---|---|---|---|---|
| `/specs <task>` | 1. Spec | Reconciles the task against the build plan, builds a conflict list, writes a PROPOSAL spec | all authority docs | `markdowns/curr/<slug>_spec.md` |
| `/build <spec> [review]` | 2. Build | Implements the spec (or fixes review findings); code + docs move together; smoke-checks; hands off hardware | spec, coding/doc-sync playbooks, touched files | code, docs, the right doc at the right level |
| `/review <spec>` | 3. Review | Judges the build against the spec and every playbook gate; runs the checks itself; emits findings | spec, all playbooks, changed code | `markdowns/curr/<slug>_review.md` |
| `/spec-loop <task>` | 1→2→3→2… | Runs the full loop, feeding review findings back into build until CLEAN or a hardware/decision stop | the three above | spec + review + code/docs |
| `/fix-bug <bug>` | loop (end-to-end) | Runs the loop on a defect — reproduce+root-cause = spec, fix = build, prove+gate-check = review, iterating to CLEAN | implicated files, playbooks | fix, test, docs |
| `/test-suite <chain>` | loop (validation) | Specs the coverage, builds missing coverage / fixes exposed, reviews by running the ladder; returns a pass/fail matrix + hardware hand-off | tests, harnesses, checklist | coverage + a matrix + hand-off |
| `/write-process <process>` | loop (whole process) | Runs the loop per sub-step to done while keeping a living progress/todo/limitations ledger | playbooks, roadmap | `markdowns/curr/<slug>_process.md` + code/docs |

The bottom three are not separate from the loop — each one **runs the spec → build → review loop
internally**, specialized to its job (a defect, a feature chain, a whole process), and iterates build↔review
until CLEAN or a hardware/decision stop. `/spec-loop` is the bare orchestrator; these add domain framing
(reproduce-first, a coverage matrix, a progress ledger) on top of the same loop.

---

## The core loop, in order

```text
/specs  "<task or R# >"          → markdowns/curr/<slug>_spec.md   (PROPOSAL, reconciled, conflicts surfaced)
   │   (resolve any ⚠️ CONFLICT / settled-decision change with a human first)
   ▼
/build  markdowns/curr/<slug>_spec.md      → code + synced docs, smoke-checked, hardware handed off
   ▼
/review markdowns/curr/<slug>_spec.md      → markdowns/curr/<slug>_review.md   (CLEAN | CHANGES REQUESTED)
   │
   ├─ CHANGES REQUESTED → /build <spec> markdowns/curr/<slug>_review.md → /review …   (repeat)
   └─ CLEAN → only hardware hand-off remains → run the hand-off on a real bench
```

`/spec-loop "<task>"` runs that whole thing for you, stopping when the review is CLEAN, when a finding
needs a human decision or a real-hardware result, or after 3 build↔review iterations without progress
(anti-thrash, per coding playbook §7).

### Artifact conventions

- **Specs, reviews, and process ledgers live in `markdowns/curr/`** — the existing home for
  step-scoped docs — using `<slug>_spec.md`, `<slug>_review.md`, `<slug>_process.md`. Pick a short
  kebab-case `<slug>`; prefix with the roadmap id when it maps to one (e.g. `r12_turnkey_brain_spec.md`).
- When the step is finished, **graduate those docs from `curr/` to `markdowns/tmp/`**, per the existing
  `curr/ → tmp/` convention in `README.md`.
- A spec is **PROPOSAL — not authority** until signed off (consistency playbook §5). If accepted, it
  amends `build_plan_concrete` in place; it never lives on as a silent override.

---

## What makes these commands *this project's* commands

Every command bakes in the rules that already govern this repo, so you don't have to remember them:

- **Authority order & reconcile-before-writing.** `/specs` and `/build` open with the same gate as
  `agent_consistency_playbook.md`: read the index → consistency playbook → build plan → relevant
  playbooks → current `main` of touched files, build a reconciliation list, and **surface every conflict
  in one place** before writing.
- **Verify, don't claim — and you can't touch the boards.** Every command separates three states:
  verified-here / non-hardware-verified / pending-hardware. Hardware-dependent results are never
  claimed; they become a precise hand-off drawn from `markdowns/current-progress.md`. This is the
  project's single most important rule (coding playbook §0) and the loop refuses to violate it.
- **No hardcoding + origin tags.** `/build` enforces "no ports/paths/targets/baud/probe/OS literals" and
  `HW-FIXED` / `VENDOR-FIXED` / `PROJECT-DEFINED` (+`UNVERIFIED`) on every non-obvious value; `/review`
  fails the build if they're missing.
- **Build on the libraries; respect the layering.** Thin wrappers over pyOCD / pyserial / `mcp`; one
  concern in one layer (adapter ↔ service ↔ server ↔ guardrails ↔ brain); go through the shared
  `target_control` / `swd_pyocd` path, never `ConnectHelper` directly (per `current-progress.md`).
- **Doc-sync is half the work.** A change isn't done until the one right doc moved with it — the build
  plan for decisions, an MCP tool's **docstring** in `server.py` (never a sidecar `.md`),
  `stage0_setup.md` for bench scripts, a playbook for how-we-write rules. `/review` checks this.
- **Portability for the absent stranger.** Setup/config/first-run work is checked against the
  portability playbook; unautomatable installs are STOP-and-asked, not baked in.

In other words: the commands are the playbooks, executable.

---

## Quick start

```text
# One feature, full loop, hands-off:
/spec-loop "R12 turnkey brain skeleton: minimal MCP-client loop over the proven server surface"

# Or drive each phase yourself:
/specs   "add nrf52840dk reference baseline and stage0 path"
/build   markdowns/curr/nrf52840dk_reference_spec.md
/review  markdowns/curr/nrf52840dk_reference_spec.md
/build   markdowns/curr/nrf52840dk_reference_spec.md markdowns/curr/nrf52840dk_reference_review.md
/review  markdowns/curr/nrf52840dk_reference_spec.md

# Targeted helpers:
/fix-bug       "nrf52833dk__b001_wrong_boot_text regresses after the last UART change"
/test-suite    "MCP runtime + guardrails on the scoped pair"
/write-process "R12 turnkey brain skeleton"
```

After any loop finishes, the agent-verifiable surface is green but the **hardware hand-off still has to
be run on a real bench** (`nrf52833dk` + `nucleo_l476rg`) — the command output tells you the exact
commands, which mirror the regression checklist in `markdowns/current-progress.md`.

---

## Editing or extending the commands

- Commands are plain markdown in `.claude/commands/`; the filename is the command name. Keep them under
  version control so the whole team runs the identical workflow.
- A command should **reference the playbooks, not re-explain them** (one fact, one home) — if a rule
  changes, it changes in the playbook and the command still points there.
- If you add a command, add a row to the table above and keep this guide in sync (doc-sync applies to
  this file too).

---

## Verified / Pending verification

Verified (non-hardware):
- The command files exist in `.claude/commands/` and reference real repo paths, playbooks, and the
  documented `uv run` check surface (`pytest` / `ruff` / `mypy`, `mcp dev`, the harness entrypoints).
- The artifact convention (`markdowns/curr/<slug>_*.md`, graduating to `tmp/`) matches the existing
  `README.md` layout and the `curr/`-vs-`tmp/` split.

Pending verification:
- These commands have not yet been exercised on a live task in this repo; the first real `/spec-loop`
  run is the proof. Treat the workflow itself as `UNVERIFIED` until a full pass produces a spec, a clean
  review, and a runnable hardware hand-off.
