---
description: "Spec-driven loop step 3 — review the build against the spec and every superpowers playbook; emit findings to feed the next build pass"
argument-hint: "<path to *_spec.md>  (reviews the latest build against it)"
---

# /review — judge the build against the spec and the playbooks

You are in the **review** phase. You are an independent reviewer, not the builder. Be skeptical: the most
expensive failure mode on this project is **confident-but-wrong** — a claim of "it works" that was never
verified against real hardware. Hunt for exactly that.

Spec under review:

> $ARGUMENTS

If no path is given, find the most recent `markdowns/curr/*_spec.md`. Read the spec, then read the
actual changed code and docs in full. Reload the authority docs you are judging against:
`agent_consistency_playbook.md`, `agent_coding_playbook.md`, `agent_doc_sync_playbook.md`,
`agent_portability_playbook.md`, `agent_script_doc_playbook.md`, and the build plan.

## What to check — the merged pre-commit gates from every playbook

Go through these as a checklist. For each, decide PASS / FAIL / N/A and cite the file:line evidence.

**Spec conformance**
- [ ] Implements exactly the spec's scope — nothing added beyond it (no silent scope expansion), nothing
      missing.
- [ ] Every spec acceptance criterion is either met-and-verified, or explicitly handed off as
      hardware-pending (not silently skipped).

**Verify-don't-claim (coding §0, §6)**
- [ ] No claim of hardware success ("flashes", "board responds") that wasn't actually run on a board this
      session. Unproven paths are tagged `# UNVERIFIED`.
- [ ] Status honestly separates (a) verified-here / (b) non-hardware-verified / (c) unverified.
- [ ] Every doc touched ends with "Verified / Pending verification".

**No hardcoding & origin tags (coding §1, §1b)**
- [ ] No hardcoded ports, paths, pyOCD targets, baud rates, probe types, or OS assumptions.
- [ ] Every non-obvious value (code AND yaml) carries `HW-FIXED` / `VENDOR-FIXED` / `PROJECT-DEFINED`
      (+ `UNVERIFIED` where a guess).

**Build-on-libraries & layering (coding §3, §5; consistency §3)**
- [ ] No reimplementation of what pyOCD / pyserial / `mcp` already provide.
- [ ] Change lives in one layer; abstractions intact; probe/board/OS specifics not leaked upward.
- [ ] Goes through shared `target_control` / `swd_pyocd`; no direct `ConnectHelper` in new code; no
      scattered `if board == ...` / `if probe == ...`.

**Consistency / authority order (consistency §1–§4)**
- [ ] Reconciled against the build plan; no settled decision silently re-decided; no parallel
      path/naming convention invented.
- [ ] Every conflict/ambiguity was surfaced in one place, not silently resolved.

**Doc-sync (doc-sync §0–§3)**
- [ ] Code and docs moved together. The RIGHT doc at the RIGHT level was amended in place (build plan for
      decisions; docstring in `server.py` for MCP tools — **no sidecar `.md` for a tool**; `stage0_setup.md`
      for bench scripts; a playbook for how-we-write rules).
- [ ] No two docs left disagreeing; no decision left living only in code or chat; cross-refs still valid.

**Portability (portability §1–§4)**
- [ ] Written for the absent stranger on a fresh macOS/Windows box; high-friction setup is scripted,
      idempotent, OS-detecting; no machine-specific values baked in.
- [ ] No vague "user must download/install X" step; anything unautomatable was STOP-and-asked, not baked in.
- [ ] Destructive actions still gate; failures self-diagnose.

**Smoke checks (coding §4)**
- [ ] The lowest-level checks were actually run with real output shown (`pytest` / `ruff` / `mypy`, and
      Inspector for tool changes). Re-run them yourself to confirm; do not trust the build's claim.

## Run the checks yourself

Don't take the builder's word for green. Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

Report the real outcome.

## Emit findings — this is what the loop feeds back

Write findings to **`markdowns/curr/<slug>_review.md>`** (same `<slug>` as the spec), in this shape:

1. **Verdict** — `CLEAN` (no must-fix findings) or `CHANGES REQUESTED`.
2. **Findings table** — each finding with: `severity` (BLOCKER / MAJOR / MINOR), which playbook gate it
   violates, file:line, what's wrong, and the concrete fix. Order by severity.
3. **Hardware hand-off status** — which acceptance criteria remain unproven on a real board and the exact
   commands the human must run (from `current-progress.md`).
4. **What's genuinely good** — so the next pass doesn't regress it.

End your reply with the review path and either:
- if CLEAN: **"Review CLEAN. Hardware hand-off items remain — see the review. Loop done for what an agent can verify."**
- if CHANGES REQUESTED: **"Review requests changes. Run `/build <spec-path> markdowns/curr/<slug>_review.md` to address them, then `/review` again."**
