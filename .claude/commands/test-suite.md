---
description: "Exercise and validate an entire chain of features as one suite — run the full check ladder, report a clean pass/fail matrix before coming back"
argument-hint: "<feature chain to validate, e.g. 'MCP runtime + guardrails on the scoped pair' or a suite name like pilot_v1>"
---

# /test-suite — validate a whole feature chain before I come back

Validate this chain of features end to end and return a single trustworthy pass/fail matrix. Don't come
back with "looks fine" — come back with what actually ran, what passed, and what is blocked on hardware.

The chain to validate:

> $ARGUMENTS

## Honesty boundary

You cannot reach the boards. So the suite splits cleanly into two halves: the **agent-runnable** half
(unit/contract/lint/type/schema, MCP Inspector, dry-runs) which you run and prove now, and the
**hardware half** (Stage 0, Stage 1 smoke, MCP runtime matrix, live benchmark) which you turn into an
exact, ordered hand-off script. Never report a hardware step as passed unless its real output is in front
of you.

## Run it as a spec → build → review loop

Validating a chain is itself a spec-driven loop: **spec** the coverage the chain should have, **build**
any missing coverage or fixes the validation exposes, and **review** by running the checks and judging
against the playbook gates — feeding findings back into build until the agent-verifiable surface is
green. Use the same phase semantics as `/spec-loop` (`.claude/commands/spec-loop.md`).

### Spec phase — map the chain and its required coverage

1. **Map the chain.** Read the build plan, `README.md`, `ROADMAP.md`, and `current-progress.md` to list
   the concrete features in this chain and the existing validation surface for each: `tests/`,
   `tests/harness/stage1_smoke.py`, `tests/harness/r11_benchmark.py`, the regression checklist in
   `current-progress.md`, and the per-tool MCP runtime matrix. Write the intended coverage matrix
   (feature → the check that proves it) as the spec for this run; for a larger effort capture it in
   `markdowns/curr/<slug>_spec.md` per `.claude/commands/specs.md`.

### Build phase — run the ladder; close gaps and failures via the loop

2. **Run the agent-runnable ladder, cheapest first, capturing real output:**
   ```bash
   uv run pytest -q
   uv run ruff check .
   uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py
   uv run pytest -q tests/test_r11_benchmark.py
   uv run python -m tests.harness.r11_benchmark --help
   ```
   For MCP surface changes, launch `uv run mcp dev src/pyocd_debug_mcp/server.py` and confirm the tool
   surface/docstrings load.
3. **When validation exposes a real defect or a missing/weak check, drive the inner loop to fix it**
   (per `.claude/commands/build.md`): make the smallest one-layer change or add the missing coverage,
   sync any doc it touches, then re-run the ladder. A failing check is not a "FAIL" to merely report —
   it's a build pass to perform, unless the fix needs a settled-decision change or real hardware (then
   surface/hand off). Do not paper over a gap: a feature with no validation surface at all is a real
   finding, and adding that surface is itself a build pass.

### Review phase — judge, then loop

4. **Self-review against the playbook gates** (the `/review` checklist) and re-run the ladder until the
   agent-verifiable surface is green or only hardware/decision items remain. Stop and escalate if you
   thrash the same fix without progress (coding §7).
5. **Assemble the hardware hand-off**, in dependency order, straight from `current-progress.md`: Stage 0
   preflight → Stage 1 smoke → MCP runtime matrix (STM32 + Nordic) → benchmark suite — for whichever
   boards/features the chain covers. Give exact commands and the expected "done/ready" signal for each.

## Report back with — the pass/fail matrix

A table: `feature | check run | result (PASS / FAIL / BLOCKED-ON-HARDWARE / NO-COVERAGE) | evidence`.
Then:

- the real command output for everything you ran,
- the ordered hardware hand-off script for the BLOCKED rows,
- an explicit top-line verdict: "agent-verifiable surface is GREEN/RED; N items await hardware,"
- any coverage gaps worth closing.

Keep the three states distinct (verified-here / non-hardware-verified / pending-hardware). A suite is
never "all green" while hardware rows are unproven — say "green up to the hardware boundary."
