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
4. **Document each thing where its reader looks.** An MCP client reads a tool's *description and handle
   over the protocol* — its docstring in the code — never a sidecar `.md`; so MCP tools are documented in
   their docstrings, and the current human/terminal shell workflow shares ONE operator guide rather than a
   separate doc per file.
5. **Verify, don't claim; never hardcode; tag every value's origin.** Honesty about what's verified vs.
   assumed is non-negotiable.

If you internalize only these five, you will avoid the project's known failure modes (fragmentation,
doc drift, bench-only setup, documenting a tool where its reader never looks, confident-but-wrong claims).

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
6. **`agent_script_doc_playbook.md`** - Where documentation lives in an MCP product. MCP tools are
   documented in their *docstrings* (the description + handle the client reads over the protocol, never a
   sidecar `.md`); the current shell-based bring-up workflow shares ONE operator guide (`stage0_setup.md`)
   covering sequence, operator-facing flags, and a consolidated symptom->cause->fix->rerun table - not a
   separate exhaustive doc per file. Shared internal services sit underneath both MCP tools and local
   programmer flows. *Read when adding or changing any MCP tool, or any setup/bench script the operator
   runs.*

---

## Which docs apply to which task (quick router)

| Your task... | Always read | Also read |
|---|---|---|
| Any task at all | Index + Consistency + Build Plan | - |
| Writing/editing code | + Coding Guidelines | + Doc-Sync (you're changing things) |
| Adding/changing an MCP tool | + Coding Guidelines + Tool-Description/Operator (§1) | + Doc-Sync (docstring moves with the code) |
| Writing/changing a bench/setup script | + Coding Guidelines + Tool-Description/Operator (§2) | + Doc-Sync + Portability (if it's setup) |
| Updating the operator guide (`stage0_setup.md`) | + Tool-Description/Operator (§2) + Doc-Sync | + Portability (if setup/first-run) |
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
a stranger's machine; document each thing where its reader looks — MCP tools in their docstrings (the
description the client reads over the protocol), the current shell workflow in one operator guide; and never
claim what you didn't verify.**
