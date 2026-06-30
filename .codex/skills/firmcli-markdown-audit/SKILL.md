---
name: firmcli-markdown-audit
description: Deeply audit Firmware-CLI markdowns against code and runs, pruning stale docs and consolidating redundant ones.
---

# FirmCLI Markdown Audit

Use this skill when the user asks for a deep markdown audit, doc freshness pass, markdown bloat reduction, or verification that docs match the current Firmware-CLI codebase and recorded runs.

## Required Inputs

Use `firmcli-workflow-core` first for the repo authority order and validation ladder. Treat these as the default audit targets unless the user narrows scope:

- `markdowns/**/*.md`
- other repo markdowns that are directly relevant to the requested docs pass
- exclude any path under a `tmp` directory from the audit target set

Do not audit generated caches, `.git`, `.venv`, `node_modules`, or archived tmp markdowns unless the user explicitly asks.

## Delta Exception

You may skip the full mapping-and-audit pass only when both are true:

- the markdowns were just audited or edited for the same scope
- there have been no meaningful code changes, run changes, or new validation outputs since that audit

When using this exception, state exactly what changed since the last audit and perform only the delta verification. If that evidence is weak, run the full process.

## Workflow

1. Establish the target set.
   - Run `git status --short`.
   - Inspect recent markdown, code, and `runs/` changes with `git diff --name-only`, `git log`, and filesystem timestamps as needed.
   - Decide whether this is a full audit or a defensible delta pass.

2. Create a temporary mapping document before rewriting docs.
   - Use a path such as `markdowns/tmp/_markdown_audit_mapping.md`.
   - The mapping document must list every target markdown and map its concrete claims to code paths, tests, scripts, run artifacts, or "no live backing found".
   - Seed the map with the scripts in this skill, then fill gaps by reading the referenced code and run outputs yourself.

3. Verify docs against the real repository.
   - Check file paths, command names, scripts, tests, config keys, branch notes, run IDs, hardware claims, provider claims, and status statements.
   - For each nontrivial claim, read the relevant code or run artifact instead of trusting another markdown.
   - Run smoke commands when a doc claim depends on executable behavior and the command is practical in the current environment.
   - For anything not immediately testable, audit the code path adversarially, state the deployment gap in the updated doc or final answer, and smoke test the closest practical substitute.

4. Rewrite, prune, and consolidate.
   - Update stale markdowns so they match code and run evidence.
   - Move obsolete or superseded markdowns to an appropriate `markdowns/tmp/...` archive path.
   - If two markdowns are related and redundant enough, merge the useful content into the better canonical doc, update indexes or links, and move the redundant source to `tmp`.
   - Prefer fewer, clearer canonical docs over preserving duplicate process artifacts.

5. Re-run the audit checks.
   - Re-run the reference checker and overlap finder after edits.
   - Re-run repo validation that matches the changed surface. If Python files changed, use `python-change`.
   - Run `git diff --check`.

6. Delete the temporary mapping document.
   - The mapping document is a mid-skill work product and must not remain in the final tree.
   - Before finishing, confirm it is absent from `git status --short`.

## Helper Scripts

Use these scripts to seed and verify the mapping. They are helpers, not substitutes for reading the referenced code and run artifacts.

```powershell
python .codex\skills\firmcli-markdown-audit\scripts\inventory_markdowns.py --root markdowns --output markdowns\tmp\_markdown_audit_inventory.md
python .codex\skills\firmcli-markdown-audit\scripts\check_markdown_references.py --root markdowns --all --output markdowns\tmp\_markdown_audit_refs.md
python .codex\skills\firmcli-markdown-audit\scripts\find_markdown_overlap.py --root markdowns --output markdowns\tmp\_markdown_audit_overlap.md
```

If the user wants one mapping document, paste or summarize the script outputs into `markdowns/tmp/_markdown_audit_mapping.md`, then add hand-verified claim mappings.

## Closeout Requirements

Final answers for this workflow must include:

- scope audited, including whether it was full or delta
- markdowns changed, moved, deleted, or consolidated
- verification commands and smoke tests run
- remaining deployment or hardware/provider gaps
- confirmation that the temporary mapping document was deleted
