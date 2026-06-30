# Process ledger for pyright-baseline-cleanup

## Goal and roadmap anchor

Task: Make Pyright a clean repo-wide gate, update workflow policy, and burn down current Pyright diagnostics before final Wave 1 deployment validation
Roadmap anchor: Wave 1 A/B/C quality gate hardening for the R12 turnkey
product path.

## Done

- Updated the Python-change skill to define repo-wide Pyright as the desired
  hard gate, with changed-file/new diagnostics blocking during any temporary
  baseline exception.
- Updated the shared FirmCLI workflow core to carry the same policy across
  fix-bug, spec-loop, test-suite, and write-process flows.
- Updated the coding playbook so the Pyright policy is durable repo guidance,
  not only a Codex-skill convention.
- Updated the named workflow skills (`firmcli-fix-bug`,
  `firmcli-test-suite`, `firmcli-write-process`, and `firmcli-spec-loop`) so
  Python-changing loops require full Pyright after this baseline is green.
- Burned down the current Pyright baseline from 95 diagnostics to zero without
  adding broad ignores.
- Verified `uv run pyright --outputjson`: 105 files analyzed, 0 errors, 0
  warnings.
- Verified full Python-change gate after final edits:
  - `uv run ruff check --fix .`: pass
  - `uv run ruff format .`: pass
  - `uv run pyright --outputjson`: pass, 105 files analyzed, 0 diagnostics
  - `uv run pytest -q`: pass, 339 tests
- Verified the FirmCLI suite ladder:
  - `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`:
    pass, including full pytest, ruff, mypy, R11 benchmark tests, and R11
    benchmark help
- Verified live Branch C provider/hardware harness on both attached boards and
  both local CLI providers:
  - `nucleo_l476rg`: `codex-cli` run root
    `runs/20260630T050810Z-8a1abf43`, `claude-cli` run root
    `runs/20260630T050841Z-1aaaf4a0`
  - `nrf52840dk`: `codex-cli` run root
    `runs/20260630T050814Z-ac5c22c2`, `claude-cli` run root
    `runs/20260630T050845Z-c42644ee`
- Verified public CLI two-turn smokes on both attached boards and both local
  CLI providers by artifact semantics. Each used turn 1
  `action_batch(connect, get_board_info)` and turn 2 standalone `finalize`:
  - `runs/20260630T050932Z-f84bc258`
  - `runs/20260630T051005Z-56326461`
  - `runs/20260630T051045Z-34e7d70e`
  - `runs/20260630T051113Z-f12e5c29`
- Process cleanup audit found no new leftover spawned provider, MCP, pyOCD,
  serial, or validation children. The only matching long-lived repo MCP process
  tree was the pre-existing VS Code/Codex app-server-owned process tree.
- Repeated adversarial audit after the green gate:
  - stale Pyright-status search found only historical notes that now point to
    the current full-green cleanup
  - broad typing/ignore audit found no new useful criticism; new casts are
    limited to test-boundary narrowing and dynamic CFFI symbol access
  - post-doc-sync `uv run pyright --outputjson` passed with 0 diagnostics
  - post-doc-sync suite ladder passed again

## In progress

- Complete.

## TODO

- None for this process.

## Limitations and known gaps

- The exact official Nordic board gate remains `nrf52833dk`; the currently
  attached Nordic board for this session is `nrf52840dk`.

## Hardware hand-off

- No hand-off yet. Live attached-board validation is planned after Pyright is
  green.

## Open decisions and surfaced issues

- None so far.

## Verified

- Initial Pyright failure was reproduced: repo-wide Pyright reported 95 errors
  across 15 files before this cleanup.

## Pending verification

- None for this process.
