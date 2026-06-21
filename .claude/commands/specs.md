---
description: "Spec-driven loop step 1 — produce a reconciled, plan-anchored spec for a task (PROPOSAL until signed off)"
argument-hint: "<what to build — a sentence, a roadmap id like R12, or a bug/feature>"
---

# /specs — write the spec before any code

You are starting the **spec** phase of this repo's spec → build → review loop. Your only job in this
phase is to produce a precise, reconciled specification. **Do not write product code or edit anything
under `src/`, `tests/`, `boards/`, or `firmware/` in this phase.**

The task to specify:

> $ARGUMENTS

## Step 0 — load the authority (non-negotiable gate)

This project fragmented once because agents wrote before reconciling. Do not repeat that. Read, in this
order, before writing a single line of spec:

1. `superpowers/agent_index_START_HERE.md` — the operating manual and doc router.
2. `superpowers/agent_consistency_playbook.md` — the authority order and the reconcile-before-writing gate.
3. `markdowns/firmware_agent_build_plan_concrete (10).md` — **THE source of truth.** When anything
   conflicts with it, it wins.
4. The task-relevant playbooks per the router table in the index (coding / doc-sync / portability /
   tool-description), based on what this task touches.
5. `markdowns/ROADMAP.md` and `markdowns/current-progress.md` to place the task on the roadmap (which
   `R#`, which gate `G#`, what is already proven on the scoped pair `nrf52833dk` + `nucleo_l476rg`).
6. The **current `main` state of every file the task will touch or depend on**, in full — not skimmed.

## Step 1 — build the reconciliation list

For the area this task lives in, write down:

- (a) what the **build plan** says,
- (b) what the **current code** actually does,
- (c) what any **other doc / roadmap / scratch note** says,
- (d) where these **disagree**.

Resolve every disagreement by the authority order (plan > coding playbook > committed `main` >
everything else) **before** finalizing the spec. Surface — do not silently resolve — every conflict and
ambiguity, using the `⚠️ CONFLICT` / `⚠️ AMBIGUITY` format from the consistency playbook §4.

## Step 2 — write the spec

Write to **`markdowns/curr/<slug>_spec.md`** (pick a short kebab-case `<slug>` from the task; if this
maps to a roadmap item, prefix it, e.g. `r12_turnkey_brain_spec.md`). If a spec for this step already
exists, update it in place rather than forking a second one.

The spec MUST contain these sections, in the repo's prose-first style (minimal bullets/bold — match the
existing `curr/` docs, not a wall of formatting):

1. **Header banner** — the first line states `> STATUS: PROPOSAL — not authority, pending reconciliation
   with build_plan_concrete and user sign-off.` Per consistency playbook §5 a spec is never authority
   until accepted; if accepted it amends the plan in place, it does not live as a silent override.
2. **Goal in plain English** — what this delivers and why, and the roadmap anchor (`R#` / gate `G#`).
3. **Scope & non-scope** — explicitly what this does NOT include (mirror the build plan's "What it does
   not include" style). Guard against silent scope expansion.
4. **Reconciliation summary** — the (a)/(b)/(c)/(d) list from Step 1, with every `⚠️ CONFLICT` /
   `⚠️ AMBIGUITY` collected in ONE place for the user.
5. **Design** — the *what and why*, decision-not-code. Name the architectural layer(s) it touches
   (adapter ↔ service ↔ server ↔ guardrails ↔ brain) and confirm the change lives in one layer; if it
   forces edits across many, STOP and flag a design conflict.
6. **Board-facts-as-data & origin tags** — list every new/changed value and its required origin tag
   (`HW-FIXED` / `VENDOR-FIXED` / `PROJECT-DEFINED`, plus `UNVERIFIED`). No board fact may become an
   `if board == ...` branch.
7. **Documentation plan (doc-sync)** — for each change, name the ONE doc that must move with it: build
   plan (architecture/decision/tool/board/stage), a playbook (how-we-write rule), an MCP tool
   **docstring** in `server.py` (tool behavior — never a sidecar `.md`), or `stage0_setup.md` (bench
   script). One fact, one home.
8. **Portability** — anything touching setup/install/config/paths/first-run must work for the absent
   stranger on a fresh macOS/Windows box. Flag any unautomatable install per portability playbook §3
   (STOP-and-ask, don't bake in a manual step).
9. **Verification plan** — the cheapest-first ladder of checks (`uv run pytest -q` → `uv run ruff check
   .` → `uv run mypy ...` → dry-run → **hand-off for hardware**). Explicitly mark which acceptance
   criteria can only be proven on a real board (you cannot touch hardware) and must be handed off.
10. **Acceptance criteria** — a concrete, checkable "definition of done" mirroring the roadmap item's
    style.
11. **Verified / Pending verification (esp. hardware)** — end every doc with these two lists.

## Step 3 — hand off

End your reply with: the spec path, the roadmap anchor, the one-paragraph reconciliation summary (or the
list of surfaced conflicts the user must resolve), and the single line:
**"Spec ready. Run `/build markdowns/curr/<slug>_spec.md` to implement it."**
