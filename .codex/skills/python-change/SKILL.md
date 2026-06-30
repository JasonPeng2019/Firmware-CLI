---
name: python-change
description: Use for any Python code change in Firmware-CLI, including edits to .py files, Python test files, Python harnesses, or Python-affecting project configuration. Enforces smallest-scope edits, repo conventions, Ruff autofix/format, Pyright JSON type checking, pytest, and explicit closeout risks.
---

# Python Change

Use this skill whenever a task changes Python code or Python-facing project
configuration. This includes `src/**/*.py`, `tests/**/*.py`, `scripts/**/*.py`,
Python harnesses, Python entrypoints, and config changes that affect Python
checking or execution.

## Workflow

1. Identify the smallest relevant files to edit. Read those files before
   changing them.
2. Make the smallest correct change in the existing style and layer.
3. Add or update focused tests when behavior changes.
4. Run the Python-change validation sequence from the repo root:

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py
```

The script runs these commands in order:

```powershell
uv run ruff check --fix .
uv run ruff format .
uv run pyright --outputjson
uv run pytest -q
```

If you need raw command output or want to collect all failures in one pass, run:

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py --continue-on-error
```

## Type Discipline

- Fix Pyright errors caused by the change before reporting success.
- Do not add `# type: ignore` unless there is no better fix.
- If a `# type: ignore` is unavoidable, keep it as narrow as possible and
  explain why in the final answer.
- Do not hide changed-code type errors by broadening public types to `Any`
  unless the existing interface genuinely requires it.

## When Checks Cannot All Run

If a required command cannot run because of missing credentials, unavailable
hardware, provider quota, or an environment problem unrelated to the code
change, say exactly which command was skipped or failed, why, and what command
should be rerun later. Do not claim the Python-change gate is green.

## Closeout

Final answers after Python code changes must include:

- files changed
- verification commands run
- remaining risks or skipped checks
