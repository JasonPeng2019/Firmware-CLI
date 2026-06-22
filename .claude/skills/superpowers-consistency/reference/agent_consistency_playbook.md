# Consistency Playbook — Single Source of Truth for Every Agent

> **Why this exists.** This project fragmented once: different people on different branches merged
> code that didn't match a roadmap that didn't match `build_plan_concrete`. Multiple agents each
> treated their own local view as the truth. This playbook fixes that by establishing ONE authority
> order and forcing every agent to **reconcile against it BEFORE writing anything** — not after.
>
> **Read this in full at the start of EVERY task, before reading anything else.** It is the first
> document an agent opens. It governs both code and `.md` files.

---

## 1. THE AUTHORITY ORDER (memorize this — it resolves every conflict)

When two sources disagree, the higher one wins. **No exceptions without explicit user sign-off.**

1. **`markdowns/firmware_agent_build_plan_concrete (10).md`** — THE source of truth for architecture, stages, decisions, repo
   layout, board schema, tool surface, guardrails, and build order. When *anything* conflicts with it,
   it wins.
2. **`superpowers/agent_coding_playbook.md`** — how code/docs must be written (no-hardcoding, origin tags,
   verify-don't-claim, build-on-libraries). Binding wherever it doesn't conflict with #1.
3. **The current committed `main` branch code** — the real, merged state. Reflects reality, but is
   SUBORDINATE to the plan: if committed code contradicts the plan, the *code* is the bug, not the plan
   (flag it; see §4).
4. **Any other roadmap / design doc / branch / `.py` file / comment** — treated as a *proposal or a
   work-in-progress*, never as authority. If it conflicts with #1–#3, it loses and the conflict is
   surfaced.

**The one rule that prevents fragmentation:** a roadmap, a teammate's file, or another branch is NOT
authority just because it exists. Only the plan (and the guidelines under it, and committed `main` as
reality-subject-to-the-plan) is authority. Everything else is a proposal to be reconciled.

---

## 2. MANDATORY pre-work: RECONCILE before you write (the gate that was missing)

Before writing a single line of code or doc, every agent MUST, in order:

1. **Read this playbook, then `markdowns/firmware_agent_build_plan_concrete (10).md`, then `superpowers/agent_coding_playbook.md`.** No task
   starts without these three in context.
2. **Read the current `main` state of every file you will touch or depend on** — in full, not skimmed.
3. **Read any roadmap/design doc/branch that claims to govern this area** — explicitly to *check it
   against the plan*, not to follow it. Assume it may be stale or divergent.
4. **Build a reconciliation list:** for the area you're about to work in, note (a) what the plan says,
   (b) what the current code does, (c) what any other doc/roadmap says, and (d) where these DISAGREE.
5. **Resolve every disagreement by the §1 authority order BEFORE writing.** The plan wins; the
   guidelines win under it; committed code is reality-but-correctable; everything else is a proposal.
6. **If resolution required overriding a lower source, you MUST surface it** (see §4) — do not silently
   pick a side and move on.

Only after this gate do you write code or docs. Writing first and reconciling later is the exact
behavior that fragmented the repo; it is prohibited.

---

## 3. WRITING consistently with what already exists

Once reconciled, match the codebase you're joining — don't import a foreign style:

- **Follow the repo layout and naming from `build_plan_concrete` Step 1.0 / 1.0b** exactly: board ids,
  directory structure, artifact naming, the board-config schema and its one validating loader. Never
  invent a parallel path/naming convention.
- **Match existing patterns over your own preferences.** Use the same MCP tool/resource conventions,
  the same SWD-interface-with-backends shape, the same session-keyed state, the same typed-error
  approach the codebase already uses. Consistency with existing code beats your idea of "better."
- **Respect the layering** (adapter ↔ tool ↔ server ↔ guardrails ↔ brain). A change lives in one
  layer; if it forces edits across many, STOP — that signals a design conflict to surface, not push
  through.
- **Apply the origin tags** (`HW-FIXED` / `VENDOR-FIXED` / `PROJECT-DEFINED`, plus `UNVERIFIED`) to
  every non-obvious value, in code and YAML, per the guidelines.
- **Don't re-decide settled decisions.** The plan's settled choices (pyOCD-in-process, native-probe
  default with CMSIS-DAP fallback, blocking-v1, multi-board-from-day-one, MCP-server-headless, etc.) are binding. If you think
  one is wrong, that's a §4 surface-it event, not a quiet divergence.

---

## 4. SURFACING ambiguity and conflict (do this; don't resolve silently)

Whenever the reconciliation step finds a conflict, or the plan is silent/ambiguous on something you
need, you MUST surface it to the user — clearly and in one place — rather than guessing.

**For a conflict (sources disagree):** state it explicitly:
> ⚠️ CONFLICT: `build_plan_concrete` says X (§ref). The current `main` code in `<file>` does Y. The
> roadmap doc says Z. Per the authority order I followed the plan (X) and did NOT follow Y/Z. The
> code/roadmap appears to be out of sync with the plan — flagging for you to reconcile or correct.

**For genuine ambiguity (plan is silent or unclear):** state your provisional choice and why:
> ⚠️ AMBIGUITY: the plan does not specify <thing>. I proceeded with <provisional choice> because
> <reason consistent with plan intent>. Confirm or correct — this is unverified by the plan.

**Rules for surfacing:**
- **Default to the plan, then flag.** When ambiguous, do the thing most consistent with the plan's
  intent, proceed, and note it — don't stall, but don't hide the assumption either.
- **Never silently "fix" code to match a roadmap, or a roadmap to match code.** If they disagree with
  the plan, the plan wins and you flag the disagreement; you do not unilaterally rewrite the loser.
- **Collect all conflicts/ambiguities for a task into ONE summary** at the end of your work, so the
  user has a single reconciliation list rather than scattered notes.
- **If a conflict is severe enough that proceeding would build substantial work on an unresolved
  contradiction, STOP and ask first** rather than building on a guess.

---

## 5. DOCS must obey the same order

`.md` files fragmented as badly as code, so:

- **Any new/edited doc must be consistent with `build_plan_concrete`.** If you write a doc that
  contradicts the plan, you are creating the next fragmentation — don't. Either align it, or surface
  the conflict and let the user decide whether the *plan* should change.
- **Do not create competing roadmaps.** If planning is needed, it amends the plan (with user sign-off)
  or is clearly marked "PROPOSAL — not authority, pending reconciliation with build_plan_concrete."
- **A doc that updates a decision must update `build_plan_concrete` itself** (with sign-off), not live
  as a separate doc that silently overrides it. One source of truth, amended in place.
- **End every doc with "Verified / Pending verification"** per the guidelines.

---

## 6. The pre-commit consistency check (run before every commit)
- [ ] Read playbook + `markdowns/firmware_agent_build_plan_concrete (10).md` + `superpowers/agent_coding_playbook.md` before starting (§2)
- [ ] Read current `main` of every touched/depended-on file, in full (§2)
- [ ] Built a reconciliation list; resolved conflicts by the authority order (§1, §2)
- [ ] Matched existing layout/naming/patterns/layering; didn't invent parallel conventions (§3)
- [ ] Didn't silently re-decide a settled plan decision or rewrite a conflicting file to match a
      non-authority source (§3, §4)
- [ ] Surfaced every conflict and ambiguity in ONE summary, with plan-ref citations (§4)
- [ ] Any doc written obeys the authority order; created no competing roadmap (§5)
- [ ] Status separates verified / unverified; origin tags applied (guidelines)

---

## The one-sentence version
**Read the plan first, reconcile everything against it before writing, let the plan win when sources
disagree, match the code that already exists, and surface every conflict and assumption in one place —
never silently pick a side.**
