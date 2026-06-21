---
name: superpowers-index
description: "Firmware-CLI operating manual and authority order. Load at the START of ANY task in this repo (pyOCD/MCP firmware-debug project) — it routes you to the right rule playbooks and names the source-of-truth docs to read before writing code or docs. Use whenever you begin work here and aren't sure which rules apply."
---

# Superpowers Index — read first on every task

This is the entry point to the Firmware-CLI rule system. The dominant failure mode is acting on *some*
of the rules because you never saw the rest. Load this first, then load the skills it points to.

## The meta-rules (the whole system in five lines)

1. **`markdowns/firmware_agent_build_plan_concrete (10).md` is the sacred, living source of truth.** When
   sources disagree, it wins.
2. **Keep it true.** Any change to code or decisions updates the authoritative doc in the SAME unit of
   work — code and docs move together (`superpowers-doc-sync`).
3. **Build for the absent stranger.** Everything ships self-hosted and self-installing; the user does
   nothing manual (`superpowers-portability`).
4. **Document each thing where its reader looks.** MCP tools in their docstrings (read over the protocol,
   never a sidecar `.md`); the shell workflow in one operator guide (`superpowers-tool-docs`).
5. **Verify, don't claim; never hardcode; tag every value's origin** (`superpowers-coding`).

## Which skills apply to which task (router)

| Your task… | Always load | Also load |
|---|---|---|
| Any task at all | this index + `superpowers-consistency` + the build plan | — |
| Writing/editing code | + `superpowers-coding` | + `superpowers-doc-sync` |
| Adding/changing an MCP tool | + `superpowers-coding` + `superpowers-tool-docs` | + `superpowers-doc-sync` |
| Writing/changing a bench/setup script | + `superpowers-coding` + `superpowers-tool-docs` | + `superpowers-doc-sync` + `superpowers-portability` |
| Setup / install / dependency / config / first-run | + `superpowers-portability` | + `superpowers-coding` + `superpowers-doc-sync` |
| Fixing a bug / resolving an inconsistency | + `superpowers-doc-sync` | + `superpowers-coding` |
| Writing/editing a `.md` doc | + `superpowers-doc-sync` + `superpowers-consistency` | (build plan if it's a decision) |
| Running the spec→build→review workflow | + `superpowers-spec-loop` | the loop already loads the rest |

When in doubt, read more, not less.

## The non-negotiable gate

**Reconcile before you write.** Index → `superpowers-consistency` → the build plan → the relevant
skills → the current `main` state of files you'll touch. Build a reconciliation list, resolve conflicts
by the authority order (the plan wins), surface every conflict in one place. *Only then write.*

Full operating manual: `reference/agent_index_START_HERE.md`.
