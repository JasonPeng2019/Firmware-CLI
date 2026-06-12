# Doc-Sync Playbook — The Code and the Docs Move Together

> **Why this exists.** Agents (Claude, Codex, ChatGPT) discover inconsistencies, fix errors, and change
> code — but DON'T reflect those changes back into `build_plan_concrete`, the roadmap, or the other
> `.md` files. So the docs drift from the code, and the "source of truth" silently goes stale. A stale
> source of truth is *worse than none*: the Consistency Playbook makes agents obey the plan, so if the
> plan is wrong, agents faithfully build the wrong thing.
>
> **This playbook is the counterpart to the Consistency Playbook.** That one says *obey the docs*; this
> one says *keep the docs worth obeying.* Read it on any task that changes code, fixes an error, or
> discovers an inconsistency.

---

## 0. THE CORE RULE: a change is NOT done until the docs reflect it

Updating the docs is **part of the change, not a follow-up task.** "I changed the code" and "I updated
the docs to match" are one unit of work. You may not close, commit, or report a task complete while the
code and the governing docs disagree.

**Definition of done for ANY change:** code changed **AND** every doc the change affects updated to
match **AND** any conflict/ambiguity surfaced to the user. Miss the middle and the task is unfinished.

This single rule is the whole fix: drift happens because doc-updates are treated as optional and later.
They are neither. They are the back half of the same change.

---

## 1. THE TRIGGERS — when you MUST sync docs (these are the drift moments)

Sync the docs immediately, in the same unit of work, whenever you:

1. **Make a code change that contradicts or extends what a doc says** — new tool, changed interface,
   different file layout, altered behavior, a decision implemented differently than written.
2. **Discover an inconsistency** between code and a doc, or between two docs — even if you didn't cause
   it. Finding it makes it yours to surface and (per authority order) reconcile.
3. **Fix an error** that reveals a doc was wrong — the doc that described the buggy assumption must be
   corrected, not just the code.
4. **Deviate from `build_plan_concrete`** for any reason — the deviation either updates the plan (with
   user sign-off) or is flagged; it is NEVER left as undocumented divergence.
5. **Add/remove/rename anything the plan enumerates** — a tool in the tool surface, a board, a stage, a
   config field, a directory. The plan's lists must stay accurate.
6. **Make a new decision** the docs didn't cover — it gets recorded in the plan, not left in code/chat.

If any trigger fires and you do not sync, you have created drift — the exact failure this prevents.

---

## 2. WHICH doc gets updated (respect the authority order)

Per the Consistency Playbook's authority order — update at the RIGHT level, don't scatter:

- **A changed/!new architectural decision, stage, tool, board, layout, or schema → update
  `markdowns/firmware_agent_build_plan_concrete (10).md` ITSELF.** It is the source of truth; the change lives there, not in a side note.
- **A how-we-write-code rule → update `superpowers/agent_coding_playbook.md`.**
- **A setup/portability change → update the relevant playbook.**
- **NEVER record a decision only in a separate roadmap/side doc that then silently overrides the plan.**
  That recreates the original fragmentation. Decisions amend the source of truth in place.
- **If a roadmap or side doc now conflicts with reality, fix or retire it** — don't leave two docs
  disagreeing. Stale docs that contradict the plan are themselves drift; resolve them.
- **One change, updated once, at the right level** — not the same fact copied into five docs (which
  just creates five things to drift). Put it in the authoritative doc; reference it elsewhere.

---

## 3. HOW to update (so the doc stays trustworthy)

- **Update in the same commit/unit as the code change**, so they can never be out of sync in history.
- **Match the doc's existing style and structure** (the docs are prose-first, minimal formatting,
  decision-not-code, ending in Verified/Pending). Don't bolt on a differently-styled section.
- **Edit the actual statement that's now wrong** — don't append a contradicting note and leave the
  stale text above it. The doc should read as if the new reality was always true (with history in the
  commit, not in contradictory layers).
- **Carry the origin/verification discipline:** if the change introduced an assumption, mark it
  `UNVERIFIED`; if it's confirmed, state it plainly. Keep the plan's "settled vs. deferred vs. not-yet"
  distinctions intact.
- **Keep cross-references valid:** if you renamed/moved something the docs point to (a step number, a
  tool name, a file path), fix the references too, or you've created dangling pointers.

---

## 4. SURFACE the doc change, don't bury it

- **Report doc updates alongside code updates** in your task summary: "Changed X in `<file>`; updated
  `build_plan_concrete` §Y to match; flagged Z." The user should see that the docs moved with the code.
- **If a change SHOULD update the plan but needs a decision you can't make** (e.g. it changes a settled
  architectural choice), STOP and surface it before editing the plan:
  > ⚠️ PLAN CHANGE NEEDED: this change deviates from `build_plan_concrete` §<ref> (<what it said>). To
  > stay in sync I need to either update the plan to <new> or revert the code. This is a settled
  > decision — confirm which before I edit the source of truth.
- **Distinguish "I synced a doc to match an implementation detail" (just do it + report) from "I'm about
  to change a settled decision in the plan" (ask first).** Routine sync is automatic; changing the
  plan's core decisions needs sign-off — but EITHER WAY the docs never silently fall behind.

---

## 5. The drift-prevention pre-commit check (run before every commit)
- [ ] Did any §1 trigger fire (code change, found inconsistency, fixed error, deviated from plan,
      added/removed/renamed an enumerated thing, made a new decision)? If yes → docs MUST be synced.
- [ ] Updated the RIGHT doc at the RIGHT level (source of truth amended in place, not a side note) (§2)
- [ ] Edited the now-wrong statement (didn't just append a contradiction); cross-refs still valid (§3)
- [ ] Code change and doc change are in the SAME unit of work (§0, §3)
- [ ] Reported the doc updates in the task summary; asked first before changing any settled decision (§4)
- [ ] No two docs left disagreeing; no decision left living only in code or chat (§2)
- [ ] Task is NOT marked done if code and governing docs still disagree (§0)

---

## The one-sentence version
**A change isn't finished until the docs match it: whenever you change code, find an inconsistency, fix
an error, or deviate from the plan, update the authoritative doc in the same breath — amend the source
of truth in place, surface what you changed, and ask first only before altering a settled decision.**
