---
name: superpowers-doc-sync
description: "Keep code and docs moving together in Firmware-CLI. Use whenever you change code, fix an error, discover an inconsistency between code and docs (or two docs), rename/add/remove an enumerated thing (tool/board/stage/config field/directory), make a new decision, or deviate from the build plan. A change is NOT done until the one authoritative doc reflects it, in the same unit of work."
---

# Doc-Sync — the code and the docs move together

The counterpart to consistency: that skill says *obey the docs*; this one says *keep the docs worth
obeying.* A stale source of truth is worse than none, because agents faithfully build the wrong thing.

## The core rule

Updating the docs is **part of the change, not a follow-up.** Definition of done for ANY change: code
changed **AND** every doc it affects updated to match **AND** any conflict surfaced. You may not close,
commit, or report a task complete while code and governing docs disagree.

## The triggers — sync immediately when you

1. Make a code change that contradicts/extends a doc (new tool, changed interface, different layout, altered behavior).
2. Discover an inconsistency (code↔doc or doc↔doc) — even if you didn't cause it.
3. Fix an error that reveals a doc was wrong — correct the doc, not just the code.
4. Deviate from the build plan — it updates the plan (with sign-off) or is flagged.
5. Add/remove/rename anything the plan enumerates (tool, board, stage, config field, directory).
6. Make a new decision the docs didn't cover.

## Which doc, at which level (respect the authority order)

- Architecture / decision / stage / tool-surface / board / layout / schema → **amend the build plan itself.**
- A how-we-write-code rule → `superpowers/agent_coding_playbook.md`.
- An MCP tool's behavior/inputs/returns/guard text → that tool's **docstring in `server.py`** (never a
  sidecar `.md` — see `superpowers-tool-docs`).
- A bench/setup script's sequence/flag/ready-signal/failure-mode → the single operator guide `stage0_setup.md`.
- A setup/portability change → the relevant playbook.
- **Never** record a decision only in a side doc that silently overrides the plan. One change, updated
  once, at the right level — not copied into five docs.

## How to update so the doc stays trustworthy

Same unit/commit as the code. Match the doc's prose-first style. **Edit the now-wrong statement** —
don't append a contradicting note above stale text. Keep cross-references valid. Mark new assumptions
`UNVERIFIED`. End docs with "Verified / Pending verification." Report doc updates alongside code updates.
If a sync needs a settled-decision change you can't make, STOP and ask before editing the plan.

Full playbook: `reference/agent_doc_sync_playbook.md`.
