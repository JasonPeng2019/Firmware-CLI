---
name: merge-conflicting-repos
description: Audit two divergent repos or refs, inventory their overlapping and non-overlapping changes, selectively preserve the best implementation for a specific goal, and validate the merged result end to end. Use when Codex needs to reconcile two branches, two remotes, or two repo states that both contain useful work and a blind merge would lose quality or introduce regressions.
---

# Merge Conflicting Repos

If you are working inside Firmware-CLI, read `.codex/skills/firmcli-workflow-core/SKILL.md` first.

If the merge target is Firmware-CLI itself, start with
`.codex/skills/firmcli-spec-loop/SKILL.md` and drive the merge as a real
spec-build-review loop, not as an ad hoc merge.

Use `.codex/skills/firmcli-fix-bug/SKILL.md` for any bug exposed by the merge
or by the later validation passes.

## Inputs you need before touching history

- the repo root that will become the final merged result
- the target ref that should remain the spine
- the source ref or repo to mine for useful work
- the specific goal of the merge
- the validation boundary you must satisfy before declaring success

If the two histories live in different repos, do not compare them by eyeballing
files. First make both histories reachable from one git namespace by using a
temporary integration clone or by adding the second repo as a remote and
fetching the needed refs.

## Workflow

1. **Spec the merge goal first.**
   - In Firmware-CLI, run the `firmcli-spec-loop` flow first.
   - Write the merge goal as a real acceptance surface: what behavior must be
     preserved, what useful additions must be carried over, and what can be
     discarded.
   - If the merge would change a settled product decision, stop and ask before
     editing code or history.

2. **Keep the target ref as the spine.**
   - Do not start from a random conflict worktree.
   - Build the final result on top of the target branch or a fresh merge branch
     cut from it.
   - Preserve the original source branch tip separately if it contains work you
     may want to revisit.

3. **Inventory the two sides before editing.**
   - Run `scripts/compare_refs.py` to capture:
     - merge base
     - left-only commits
     - right-only commits
     - files changed on each side
     - files changed on both sides
   - Run `scripts/merge_probe.py` to perform a safe scratch merge in a
     temporary worktree and record:
     - whether the merge is clean
     - which files conflict
     - which non-conflicting files are still touched by the merge
   - These scripts are inventory tools, not decision makers.

4. **Audit both sides against the goal.**
   - Audit the target side for weak points, missing capability, technical debt,
     bad docs, weak tests, or regressions relative to the goal.
   - Audit the source side the same way.
   - For each side, identify:
     - what it does better
     - what it does worse
     - what risks it introduces
     - what validation surface already exists for it

5. **Classify all differences into two buckets.**
   - **Same-problem differences**:
     both sides changed the same feature, layer, or contract for the same
     reason.
   - **Different-problem differences**:
     each side changed different behavior, or one side added something the
     other never touched.

6. **Resolve same-problem differences selectively.**
   - For overlapping implementations that solve the same problem:
     - pick the cleaner implementation in the correct layer
     - prefer the one with clearer contracts, stronger tests, better doc-sync,
       and fewer hidden assumptions
     - transplant beneficial additions from the weaker implementation instead of
       discarding them blindly
   - Do not keep duplicate parallel implementations unless the spec explicitly
     requires both.

7. **Resolve different-problem differences by usefulness to the goal.**
   - Pull in changes that are:
     - directly required for the merge goal
     - broadly useful hardening
     - tests, docs, or validation additions that improve trust
   - Discard or archive changes that are:
     - unrelated experiments
     - stale temporary conflict artifacts
     - contradictory docs
     - goal-neutral churn that increases merge risk

8. **Handle docs deliberately.**
   - Keep active docs in the right active location.
   - Move historical but useful docs to an archive area such as `tmp/`.
   - Delete stale active docs that would mislead future work.
   - Never leave two active docs disagreeing about the same feature.

9. **Validate in layers, not once at the end.**
   - Run the cheapest relevant static checks first.
   - Run targeted tests for the files or features you changed.
   - Run the repo's smoke or integration harnesses.
   - Run on-hardware or full application checks when the repo and task require
     them.
   - If any validation exposes a real bug, route that pass through
     `firmcli-fix-bug`, then rerun validation.
   - Continue until the repo is green up to the real hardware boundary.

10. **Report the merge honestly.**
   - Provide:
     - what was kept from each side
     - what was discarded and why
     - what was archived
     - the final validation matrix
     - any remaining hardware-only proof boundary

## Selection rules

- Prefer the correct layer over the flashier diff.
- Prefer the implementation with the smaller coherent surface area.
- Prefer deterministic tests and real validation over hand-wavy confidence.
- Prefer doc-sync that amends one correct doc over duplicated status notes.
- Prefer preserving additive improvements from both sides where they compose.
- Do not preserve stale branch history artifacts just because they were hard to
  produce.

Read `references/selection-matrix.md` when you need the full resolution matrix.

## Helper scripts

- `scripts/compare_refs.py`
  - Inventories two refs in one repo and produces a file/commit overlap matrix.
- `scripts/merge_probe.py`
  - Creates a temporary detached worktree, attempts the merge there, reports
    conflict paths and touched files, and removes the scratch worktree without
    touching the current working tree.

## Firmware-CLI validation expectation

When the merge target is Firmware-CLI, the usual closeout is:

1. `firmcli-spec-loop` for the merge goal
2. `firmcli-test-suite` for the affected feature chain
3. `firmcli-fix-bug` for any defects exposed during merge or validation
4. loop until the agent-verifiable surface is green and the only remaining
   boundary is hardware or a human decision

## Closeout

Return:

- the spec path and review path if you used the Firmware-CLI workflow
- the kept/discarded/archived change summary
- the validation matrix
- the exact commands run
- the three verification buckets:
  - verified here
  - non-hardware verified
  - pending hardware
