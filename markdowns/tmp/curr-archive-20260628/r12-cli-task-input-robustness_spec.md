# R12 CLI Task Input Robustness Spec

Status: PROPOSAL - not authority.

## Goal

Make deployed CLI prompts robust when users provide long task text containing
quotes, braces, JSON examples, or shell-sensitive punctuation.

This closes the deployment issue found during Branch B validation: PowerShell
can split a complex `--task` string before `pyocd-debug-brain` receives it.
The model and brain loop behaved correctly once the task text arrived; the gap
was shell argument transport.

Roadmap anchor: `R12` turnkey CLI / Branch B deployment validation.

## Scope

Add portable task ingestion for both human-facing run commands:

- `pyocd-debug-brain run --task "..."`
- `pyocd-debug-brain run --task-file path/to/prompt.txt`
- `pyocd-debug-brain run --task-stdin`
- `pyocd-debug run --task "..."`
- `pyocd-debug run --task-file path/to/prompt.txt`
- `pyocd-debug run --task-stdin`

The three task sources are mutually exclusive. The selected task text is passed
unchanged to the existing app and brain loop after rejecting empty input.

## Non-Scope

- No provider prompt redesign.
- No model behavior change.
- No MCP tool change.
- No server-side host executor.
- No shell-specific quoting rules or per-shell escaping logic.

## Design

Implement a small shared helper under the brain CLI layer that:

- registers the mutually exclusive task-source arguments;
- reads task files with UTF-8;
- reads stdin only when explicitly requested;
- raises `BrainConfigError` for missing, empty, unreadable, or conflicting task
  input;
- keeps paths as user-provided runtime input rather than tracked config.

This is portable because it relies on `argparse`, `pathlib`, UTF-8 text files,
and stdin rather than shell-specific quoting behavior.

## Acceptance Criteria

- Existing `--task` behavior still works.
- `--task-file` can carry text that includes JSON-like quotes/braces without
  shell parsing problems.
- `--task-stdin` works for piped or redirected prompt text.
- `pyocd-debug-brain run` and `pyocd-debug run` expose the same task-source
  behavior.
- Unit tests cover parser shape, file loading, stdin loading, empty input, and
  app handoff.
- Full non-hardware suite passes after the change.

## Verified / Pending verification

Verified:

- `--task-file` and `--task-stdin` are implemented for `pyocd-debug-brain run`
  and `pyocd-debug run`.
- Targeted CLI tests passed.
- Full non-hardware suite passed.
- Real `--task-file` deployment smokes passed on the attached
  `nucleo_l476rg + nrf52840dk` pair.

Pending verification:

- Exact `nrf52833dk` task-file smoke remains pending until that board is
  physically attached.
