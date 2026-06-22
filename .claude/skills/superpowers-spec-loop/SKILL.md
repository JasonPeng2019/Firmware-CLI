---
name: superpowers-spec-loop
description: "The spec → build → review slash-command workflow for Firmware-CLI. Use when you want to run the spec-driven loop (/specs → /build → /review, the /spec-loop orchestrator) or the /fix-bug, /test-suite, /write-process helpers, or before editing those commands. Explains how the commands map onto the superpowers rules."
---

# Spec → Build → Review Loop — the project's slash-command workflow

A versioned set of slash commands in `.claude/commands/` that turn the superpowers rules into a
repeatable, spec-driven loop: spec it out, build it, review it — then feed review findings back into
another build pass until the review is CLEAN. The commands are the playbooks made executable.

## The commands

| Command | Phase | What it does |
|---|---|---|
| `/specs <task>` | Spec | Reconciles the task against the build plan, surfaces conflicts, writes a PROPOSAL spec to `markdowns/curr/<slug>_spec.md` |
| `/build <spec> [review]` | Build | Implements the spec (or fixes review findings); code + docs move together; smoke-checks; hands off hardware |
| `/review <spec>` | Review | Judges the build against the spec and every playbook gate; runs the checks itself; emits `markdowns/curr/<slug>_review.md` |
| `/spec-loop <task>` | loop | Runs the whole loop, feeding review findings back into build until CLEAN or a hardware/decision stop |
| `/fix-bug <bug>` | loop | Defect end-to-end: reproduce+root-cause = spec, fix = build, prove = review |
| `/test-suite <chain>` | loop | Specs coverage, builds missing coverage/fixes, reviews by running the ladder; returns a pass/fail matrix |
| `/write-process <process>` | loop | Runs the loop per sub-step while keeping a living progress/todo/limitations ledger |

## How it encodes the superpowers

Every command opens with the **reconcile-before-writing** gate (`superpowers-consistency`), enforces
**verify-don't-claim + no-hardcoding + origin tags** (`superpowers-coding`), keeps **code and docs moving
together** (`superpowers-doc-sync`), checks **portability** for setup work, and respects the
**MCP-docstring-as-doc** rule (`superpowers-tool-docs`). Because the agent cannot touch the boards,
"done" always stops at a precise hardware hand-off drawn from `markdowns/current-progress.md` — results
are reported in three buckets: verified-here / non-hardware-verified / pending-hardware.

## Artifact conventions

Specs, reviews, and process ledgers live in `markdowns/curr/` as `<slug>_spec.md` / `<slug>_review.md` /
`<slug>_process.md`, graduating to `markdowns/tmp/` when the step is done. A spec is PROPOSAL — not
authority — until signed off; if accepted it amends the build plan in place.

These are user-invoked slash **commands** (you type `/specs`), distinct from the auto-invoked superpowers
**skills**. Full guide: `reference/spec_build_review_loop_playbook.md`.
