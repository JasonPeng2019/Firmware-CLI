---
description: "Fix a bug end to end — reproduce, root-cause, fix, sync docs, and validate everything an agent can before reporting back"
argument-hint: "<bug description, failing command, error text, or case id like nrf52833dk__b001_wrong_boot_text>"
---

# /fix-bug — end-to-end fix, validated before I come back

Fix this bug completely and come back only when it's done and validated as far as an agent can validate
it. Do not return after merely editing a line — reproduce, fix, prove, and sync docs first.

The bug:

> $ARGUMENTS

## Honesty boundary (read first)

You cannot touch the physical boards. So "fixed and validated" means: **root-caused, fixed, doc-synced,
and proven green by every non-hardware check available** — with a precise hardware hand-off for anything
that can only be confirmed on a real `nrf52833dk` / `nucleo_l476rg`. Never report a hardware-dependent
fix as "working" without a real run; tag it `# UNVERIFIED` and hand it off (coding playbook §0).

## Run it as a spec → build → review loop

A bug fix is a small spec-driven loop, not a one-shot edit. Drive the same three phases as
`/spec-loop` (`.claude/commands/spec-loop.md`), specialized for a defect: reproduce + root-cause are the
**spec**, the fix is the **build**, and proving it (plus the playbook gates) is the **review** — feed any
review finding back into another build pass until the review is CLEAN.

### Spec phase — reproduce and root-cause (this is the bug's spec)

1. **Reconcile-gate.** Read `agent_consistency_playbook.md`, the build plan, `agent_coding_playbook.md`,
   and `agent_doc_sync_playbook.md`. Read the full current state of the files implicated.
2. **Reproduce first.** Establish a failing signal before changing anything: a failing test, a `ruff` /
   `mypy` error, a benchmark case (`uv run python -m tests.harness.r11_benchmark --case-id <id>`), or a
   minimal repro you write. If the bug is only reproducible on hardware, say so and write the exact
   repro command for the human — then fix against the strongest non-hardware signal you can build (e.g.
   a unit test that captures the logic error).
3. **Root-cause, don't patch symptoms.** State the actual cause in one or two sentences. Capture it (and
   the intended fix + how it'll be verified) in a short spec at `markdowns/curr/<slug>_spec.md` — for a
   tiny one-file fix an inline root-cause + fix-plan note is enough; for anything larger write the spec
   per `.claude/commands/specs.md`. If the bug reveals a doc was wrong (a stale assumption in the build
   plan / a tool docstring / `stage0_setup.md`), that doc is part of the fix (doc-sync §1.3). If the fix
   would change a settled decision, STOP and ask before building.

### Build phase — fix it (per `.claude/commands/build.md`)

4. **Fix in one layer.** Smallest, most reversible change in the right layer; respect the adapter ↔
   service ↔ server ↔ guardrails ↔ brain split; no hardcoding; origin-tag any new value; go through the
   shared `target_control` / `swd_pyocd` path, never `ConnectHelper` directly.
5. **Add a regression guard.** Where the bug allows it, add or extend a test/harness assertion so it
   can't silently come back. Prefer the lowest level that captures it.
6. **Sync docs in the same unit of work.** Amend the one right doc at the right level; edit the wrong
   statement, don't append a contradiction.

### Review phase — prove it, then loop (per `.claude/commands/review.md`)

7. **Validate (cheapest-first, real output).**
   ```bash
   uv run pytest -q
   uv run ruff check .
   uv run mypy src
   ```
   Plus the specific repro from step 2, now passing. For MCP tool changes, validate in the Inspector.
   Show the actual command output, not a claim.
8. **Self-review against the playbook gates** (the `/review` checklist: verify-don't-claim, no
   hardcoding, origin tags, layering, doc-sync, portability). Any finding → go back to the build phase,
   fix highest-severity first, re-validate. Repeat until CLEAN, or stop and escalate if you've made the
   same fix twice without progress (coding §7).
9. **Hardware hand-off.** For anything only a board can confirm, emit the exact command + expected
   output from `markdowns/current-progress.md` and stop there for that part.

## Report back with

- the root cause (one or two sentences),
- the fix (files changed, which layer),
- the regression guard added,
- docs synced (which doc, which section),
- validation output in three buckets: verified-here / non-hardware-verified / pending-hardware,
- the hardware hand-off commands, if any,
- any `⚠️ CONFLICT` / `⚠️ AMBIGUITY` surfaced.
