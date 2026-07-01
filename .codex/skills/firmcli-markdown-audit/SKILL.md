---
name: firmcli-markdown-audit
description: Deeply audit Firmware-CLI markdowns against code, runs, and canonical feature intent, pruning stale docs and consolidating redundant ones.
---

# FirmCLI Markdown Audit

Use this skill when the user asks for a deep markdown audit, doc freshness pass, markdown bloat reduction, curr cleanup, or verification that docs match the current Firmware-CLI codebase, recorded runs, and the product's governing feature intent.

This workflow is not just a stale-link checker. It must rebuild the product's feature/phase truth from the authority order, the current code, and verified run evidence, then reconcile every active markdown against that truth.

## Required Inputs

Use `firmcli-workflow-core` first for the repo authority order and validation ladder. Treat these as the default audit targets unless the user narrows scope:

- `markdowns/**/*.md`
- other repo markdowns that are directly relevant to the requested docs pass
- exclude any path under a `tmp` directory from the audit target set

Do not audit generated caches, `.git`, `.venv`, `node_modules`, or archived tmp markdowns unless the user explicitly asks.

For normal product-doc cleanup, `markdowns/curr/*.md` and all non-archived markdowns under `markdowns/` are in scope. Do not skip `curr` because a file looks like a temporary process artifact; classify it, reconcile it, and either update it, merge it into a canonical doc, or move it to an archive path.

When the user explicitly asks to audit archives too, include archived markdowns in the inventory, but classify them as historical evidence. Archived docs must not override active authority; if they contain still-current requirements, migrate the requirement into the aggregation doc and a canonical active doc.

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

3. Create or update the durable feature aggregation document.
   - Use `markdowns/curr/feature_aggregation.md` unless the repo already has a canonical aggregation doc for the same purpose.
   - This aggregation doc is an audit output and must remain in the tree. It is not the temporary mapping document.
   - Read every target markdown needed to classify product features, phases, waves, specs, process docs, roadmap notes, and gap docs. Do not rely on headings alone; read the body text that states product behavior, status, requirements, or deferrals.
   - For each feature, phase, wave, or branch, write one canonical aggregation entry with:
     - `feature_id` or stable name
     - owning phase/wave/module when known
     - authority sources, ordered by the repo authority order
     - hard `should-have` requirements
     - hard `should-not-have` constraints
     - current implementation evidence with code paths and tests
     - provider/CLI/product behavior expectations
     - verification status: verified here, non-hardware verified, pending provider, pending hardware, or unresolved
     - docs where the feature appears
     - valid gaps or conflicts
   - Build the aggregation additively from model-determined correct design and implementation requirements. Add requirements that the feature should have; do not add lower-authority stale ideas, contradicted design fragments, obsolete actions, or requirements the product should not have.
   - If sources conflict, do not average them. Keep the higher-authority requirement, mark the lower-authority text as stale, and record the conflict in the aggregation doc and final answer.
   - Current code is evidence of reality, not automatic authority. If code lacks a hard requirement, the aggregation entry records a valid implementation gap instead of silently redefining the requirement downward.

4. Verify docs against the real repository and the aggregation doc.
   - Check file paths, command names, scripts, tests, config keys, branch notes, run IDs, hardware claims, provider claims, and status statements.
   - For each nontrivial claim, read the relevant code or run artifact instead of trusting another markdown.
   - Run smoke commands when a doc claim depends on executable behavior and the command is practical in the current environment.
   - For anything not immediately testable, audit the code path adversarially, state the deployment gap in the updated doc or final answer, and smoke test the closest practical substitute.
   - For every target markdown, map each feature/phase claim back to the matching aggregation entry. Compare the doc's text against the aggregation entry's `should-have`, `should-not-have`, implementation evidence, and verification status.
   - A doc is stale if it omits a hard requirement, claims an unimplemented feature is implemented, demotes a hard requirement to optional, promotes a rejected idea, points to the wrong wave/module, misstates provider/CLI behavior, misstates verification status, or contradicts the aggregation doc.

5. Rewrite, prune, and consolidate.
   - Update stale markdowns so they match code and run evidence.
   - Update stale markdowns so they match the aggregation doc's feature requirements and current verification status.
   - If a feature appears in multiple markdowns, keep one canonical explanation and turn the others into concise pointers or status notes. Do not copy the same detailed requirement into many docs unless those docs have distinct audiences that need it.
   - If a markdown is missing a feature it must cover, add the feature in the correct section. If a markdown should not cover that feature, do not add noise; add or fix only the appropriate cross-reference.
   - In `markdowns/curr`, do not leave completed process/spec/gap docs as active current truth after their contents have been merged into canonical docs. Move them to an appropriate `markdowns/tmp/...` archive path or delete only when they are clear duplicates and no useful unique content remains.
   - Move obsolete or superseded markdowns to an appropriate `markdowns/tmp/...` archive path.
   - If two markdowns are related and redundant enough, merge the useful content into the better canonical doc, update indexes or links, and move the redundant source to `tmp`.
   - Prefer fewer, clearer canonical docs over preserving duplicate process artifacts.

6. Re-run the audit checks.
   - Re-run the reference checker and overlap finder after edits.
   - Re-run repo validation that matches the changed surface. If Python files changed, use `python-change`.
   - Run `git diff --check`.
   - Re-scan for stale gap phrases, stale wave names, stale action names, contradicted provider behavior, and files remaining in `markdowns/curr` that no longer represent active work.
   - Re-open the aggregation doc after edits and confirm it still matches the final markdown set.

7. Delete the temporary mapping document.
   - The mapping document is a mid-skill work product and must not remain in the final tree.
   - Before finishing, confirm it is absent from `git status --short`.
   - Do not delete the durable feature aggregation document.

## Helper Scripts

Use these scripts to seed and verify the mapping. They are helpers, not substitutes for reading the referenced code and run artifacts.

```powershell
python .codex\skills\firmcli-markdown-audit\scripts\inventory_markdowns.py --root markdowns --output markdowns\tmp\_markdown_audit_inventory.md
python .codex\skills\firmcli-markdown-audit\scripts\check_markdown_references.py --root markdowns --all --output markdowns\tmp\_markdown_audit_refs.md
python .codex\skills\firmcli-markdown-audit\scripts\find_markdown_overlap.py --root markdowns --output markdowns\tmp\_markdown_audit_overlap.md
```

If the user wants one mapping document, paste or summarize the script outputs into `markdowns/tmp/_markdown_audit_mapping.md`, then add hand-verified claim mappings.

The helper scripts exclude `tmp` by default. That is correct for normal active-doc audits. If the user explicitly asks to include archives, supplement the scripts with manual `rg --files -g '*.md' markdowns` inventory and classify archived files separately.

## Closeout Requirements

Final answers for this workflow must include:

- scope audited, including whether it was full or delta
- path to the durable feature aggregation document and whether it was created or updated
- markdowns changed, moved, deleted, or consolidated
- feature/phase conflicts found and how they were resolved under the authority order
- verification commands and smoke tests run
- remaining deployment or hardware/provider gaps
- confirmation that the temporary mapping document was deleted
