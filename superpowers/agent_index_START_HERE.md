# START HERE - Agent Operating Manual & Document Index

> **Every agent (Claude, Codex, ChatGPT) reads THIS document first, before any task.** It is the entry
> point to the whole rule set. If you load nothing else, load this - then load the documents it points
> to that are relevant to your task. The dominant failure mode at this point is an agent acting on
> *some* of the rules because it never saw the rest. This index exists to prevent that.

---

## The meta-rules (the whole system in five lines)
1. **`markdowns/firmware_agent_build_plan_concrete (10).md` is the sacred, living source of truth.** Obey it; when sources disagree,
   it wins.
2. **Keep it true.** Any change to code or decisions updates the authoritative doc in the SAME unit of
   work - code and docs move together.
3. **Build for the absent stranger.** Everything ships self-hosted and self-installing; the user does
   nothing manual; never tell the user to "go download X."
4. **The operating agent is blind to source.** Every runnable script carries a script-doc that fully
   replaces reading its code, and every multi-script workflow carries an operator guide.
5. **Verify, don't claim; never hardcode; tag every value's origin.** Honesty about what's verified vs.
   assumed is non-negotiable.

If you internalize only these five, you will avoid the project's known failure modes (fragmentation,
doc drift, bench-only setup, blind-agent operation, confident-but-wrong claims).

---

## The documents, in reading order

**Read these two on EVERY task, always:**

1. **`agent_consistency_playbook.md`** - The authority order and the reconcile-before-writing gate. How
   to stay aligned with the codebase and resolve conflicts. *Read first on every task - it tells you
   what wins.*
2. **`markdowns/firmware_agent_build_plan_concrete (10).md`** - THE source of truth: architecture, stages (0-8), settled decisions,
   repo layout (Step 1.0), board schema (Step 1.0b), tool surface, guardrails, build order, and the
   reference-repo policy (Appendix R). *Everything you build conforms to this.*

**Read the relevant ones based on what your task touches:**

3. **`agent_coding_playbook.md`** - How code/docs must be written: prime directive (verify, don't
   claim), no-hardcoding, origin tags (`HW-FIXED`/`VENDOR-FIXED`/`PROJECT-DEFINED`/`UNVERIFIED`),
   build-on-libraries-don't-reimplement, smoke checks, small isolated changes. *Read when writing any
   code or doc.*
4. **`agent_doc_sync_playbook.md`** - A change isn't done until the docs reflect it. The triggers for
   syncing, which doc to update at which level, asking-first before changing settled decisions. *Read
   whenever you change code, fix an error, find an inconsistency, or deviate from the plan.*
5. **`agent_portability_playbook.md`** - Build for the absent stranger on a fresh macOS/Windows machine:
   everything installable goes in an OS-detecting, idempotent script; STOP and ask before any
   unautomatable install. *Read on any task touching setup, install, dependencies, config, paths, or
   first-run.*
6. **`agent_script_doc_playbook.md`** - Defines BOTH doc types needed for blind operation:
   script-docs for individual runnable scripts and operator guides for multi-script workflows. Script-docs
   cover exact behavior, every input, every log/output/exit-code meaning, and every failure mapped
   symptom->cause->fix->rerun; operator guides cover cross-script sequence and branching. *Read when
   creating or changing any runnable script or any workflow doc that orchestrates multiple scripts.*

---

## Which docs apply to which task (quick router)

| Your task... | Always read | Also read |
|---|---|---|
| Any task at all | Index + Consistency + Build Plan | - |
| Writing/editing code | + Coding Guidelines | + Doc-Sync (you're changing things) |
| Writing/changing a runnable script | + Coding Guidelines + Script-Doc | + Doc-Sync + Portability (if it's setup) |
| Writing/changing a multi-script workflow guide | + Script-Doc + Doc-Sync | + Portability (if setup/first-run) |
| Setup / install / dependency / config / first-run | + Portability | + Coding Guidelines + Doc-Sync |
| Fixing a bug / resolving an inconsistency | + Doc-Sync | + Coding Guidelines |
| Writing/editing a `.md` doc | + Doc-Sync + Consistency | (Build Plan if it's a decision) |
| Making/changing a decision | + Doc-Sync + Consistency | Build Plan (amend it, with sign-off) |

When in doubt, read more, not less. These docs are short relative to the cost of acting on a partial
view of the rules.

---

## The non-negotiable gate before you write anything
From the Consistency Playbook, restated here because it is the single most important behavior:
**Reconcile before you write.** Read this index -> the consistency playbook -> the build plan -> the other
relevant docs -> the current `main` state of files you'll touch. Build a reconciliation list. Resolve
conflicts by the authority order (the plan wins). Surface every conflict and assumption to the user in
one place. *Only then write.* Writing first and reconciling later is what fragmented this project; it is
prohibited.

---

## If the docs themselves conflict
- The authority order in the Consistency Playbook governs (plan > guidelines > committed `main` >
  everything else).
- If two playbooks seem to conflict, the more specific/safety-preserving rule wins, and you **surface
  the conflict** so the human can reconcile the docs - per the Doc-Sync Playbook, a doc-vs-doc conflict
  is itself drift to be fixed, not worked around silently.

---

## The one-sentence version
**Read this index first, then the consistency playbook and build plan, then whatever your task touches;
reconcile against the plan before writing; keep code and docs moving together; build self-installing for
a stranger's machine; document every script for an agent that can't see code, plus every multi-script
workflow it must navigate; and never claim what you didn't verify.**
