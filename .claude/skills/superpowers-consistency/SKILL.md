---
name: superpowers-consistency
description: "Reconcile-before-writing gate and authority order for Firmware-CLI. Use BEFORE writing or editing ANY code or .md in this repo: read the build plan, build a reconciliation list, resolve conflicts by authority order (the plan wins), and surface every conflict instead of silently picking a side. The single rule that prevents repo fragmentation."
---

# Consistency — single source of truth, reconcile before writing

This project fragmented once because agents treated their own local view as truth and wrote before
reconciling. This is the gate that prevents it.

## The authority order (resolves every conflict)

When two sources disagree, the higher one wins — no exceptions without explicit user sign-off:

1. **`markdowns/firmware_agent_build_plan_concrete (10).md`** — THE source of truth (architecture,
   stages, decisions, repo layout, board schema, tool surface, guardrails, build order).
2. **`superpowers/agent_coding_playbook.md`** (skill `superpowers-coding`) — how code/docs must be
   written. Binding under #1.
3. **Current committed `main`** — real merged state, but subordinate to the plan: if code contradicts the
   plan, the *code* is the bug (flag it).
4. **Any other roadmap / design doc / branch / comment** — a *proposal*, never authority.

A roadmap or teammate's file is NOT authority just because it exists.

## The mandatory pre-work (the gate that was missing)

Before writing a single line:

1. Read this skill, then the build plan, then `superpowers-coding`.
2. Read the current `main` state of every file you'll touch or depend on — in full, not skimmed.
3. Read any roadmap/design doc that claims to govern the area — to *check it against the plan*, not follow it.
4. Build a **reconciliation list**: (a) what the plan says, (b) what the code does, (c) what other docs
   say, (d) where they disagree.
5. Resolve every disagreement by the authority order BEFORE writing.
6. If resolution required overriding a lower source, **surface it** — don't silently pick a side.

## Surface, don't resolve silently

- **CONFLICT (sources disagree):** "⚠️ CONFLICT: plan says X (§ref); code in `<file>` does Y; roadmap
  says Z. Per authority order I followed X and did NOT follow Y/Z — flagging for you to reconcile."
- **AMBIGUITY (plan silent):** "⚠️ AMBIGUITY: plan doesn't specify <thing>; I proceeded with <choice>
  because <plan-consistent reason>. Confirm or correct."
- Collect all conflicts/ambiguities into ONE summary at the end. If proceeding would build substantial
  work on an unresolved contradiction, STOP and ask first.
- Don't silently re-decide settled decisions (pyOCD-in-process, native-probe-default-with-CMSIS-DAP-
  fallback, blocking-v1, board-facts-as-data, session-keyed state, shared-services-below-both-frontends).

Full playbook: `reference/agent_consistency_playbook.md`.
