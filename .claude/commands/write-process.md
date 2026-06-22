---
description: "Drive an entire multi-step process to completion — write, validate, test, document, and track progress/todos/limitations — before coming back"
argument-hint: "<the process/feature to deliver, e.g. 'R12 turnkey brain skeleton' or 'add nrf52840dk reference baseline'>"
---

# /write-process — deliver a whole process, tracked, before I come back

Take this process from nothing to as-done-as-an-agent-can-take-it: write it, validate it, test it,
document it, and maintain a living progress/todo/limitations record throughout. Come back with a clear
ledger of what's done, what's pending, and what's blocked on hardware — not a vague "made progress."

The process to deliver:

> $ARGUMENTS

## This is the spec → build → review loop plus a tracking ledger

Run the repo's spec → build → review loop as the backbone — the same phase semantics as `/spec-loop`
(`.claude/commands/spec-loop.md`) — rather than improvising. A whole process is usually several loop
iterations: spec the process, then build → review → re-build each sub-step until its review is CLEAN,
then move to the next sub-step. The addition unique to this command is a **persistent process ledger**
you keep current across every iteration.

### Spec phase — reconcile, anchor, and open the ledger

1. **Reconcile-gate + spec** (per `.claude/commands/specs.md`). Load `agent_consistency_playbook.md`,
   the build plan, `agent_coding_playbook.md`, `agent_doc_sync_playbook.md`, and (if setup/config is
   touched) `agent_portability_playbook.md`. Place the process on the roadmap (`R#` / gate `G#`).
   Produce/locate `markdowns/curr/<slug>_spec.md` (PROPOSAL banner; reconciliation list; scope &
   non-scope; acceptance criteria). If a `⚠️ CONFLICT` or settled-decision change needs the user, STOP
   and ask before building.
2. **Create the process ledger** at `markdowns/curr/<slug>_process.md` and keep it updated as you work.
   It MUST contain, in the repo's prose-first style:
   - **Goal & roadmap anchor.**
   - **Done** — completed sub-steps with the evidence (which check, what output) and the loop state
     (spec'd / built / reviewed-CLEAN).
   - **In progress** — current sub-step and which loop phase it's in.
   - **TODO** — ordered remaining sub-steps.
   - **Limitations / known gaps** — what's intentionally out of scope, what's fragile, what assumptions
     are `UNVERIFIED`.
   - **Hardware hand-off** — every step only a real board can confirm, with exact commands + expected
     output from `current-progress.md`.
   - **Open decisions / ⚠️ surfaced** — anything needing user sign-off.
   - **Verified / Pending verification.**
   (Convert any relative dates to absolute. This file graduates `curr/ → tmp/` when the step is done.)

### Build phase — implement each sub-step (per `.claude/commands/build.md`)

3. **Build in small, reversible, one-layer steps.** Apply every coding rule: verify-don't-claim, no
   hardcoding, origin tags, build-on-libraries, respect the layering, route through shared services. After
   each sub-step, update the ledger's Done/In-progress/TODO.
4. **Validate cheapest-first, real output**, after each meaningful sub-step:
   ```bash
   uv run pytest -q
   uv run ruff check .
   uv run mypy src
   ```
   Plus targeted tests/harness runs and the MCP Inspector for tool changes. Add regression coverage where
   the process creates new behavior.
5. **Sync docs in the same unit of work.** Amend the one right doc at the right level (build plan for
   decisions; `server.py` docstrings for MCP tools — no sidecar `.md`; `stage0_setup.md` for bench
   scripts; a playbook for how-we-write rules). The process is not done while code and governing docs
   disagree.

### Review phase — judge each sub-step, then loop (per `.claude/commands/review.md`)

6. **Self-review against the playbook gates** (the `/review` checklist) after each sub-step. Any finding
   → go back to the build phase, fix highest-severity first, re-run the checks, and update the ledger.
   Repeat build↔review until that sub-step's review is CLEAN, then advance to the next TODO sub-step. If
   you've thrashed the same fix twice without progress, stop and escalate (coding §7).
7. **Hardware hand-off.** Leave the board-only steps as a precise, ordered runbook in the ledger and in
   your reply — do not claim them.

## Report back with

- the ledger path (`markdowns/curr/<slug>_process.md`) and a one-screen summary of Done / TODO /
  Limitations,
- files changed and docs synced (which doc, which section),
- validation output in three buckets: verified-here / non-hardware-verified / pending-hardware,
- the hardware hand-off runbook,
- every `⚠️ CONFLICT` / `⚠️ AMBIGUITY` / open decision needing your sign-off.
