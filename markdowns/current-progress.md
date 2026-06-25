# Current Progress

## How To Read This Document

Use this file after `README.md` and `ROADMAP.md`.

- `README.md` explains the repo layout, the scoped board pair, and the main
  commands.
- `ROADMAP.md` explains the full project plan and dependency order.
- This file explains the current real status of the repo:
  - what has already been implemented
  - what has already been proven on hardware
  - what commands should be rerun when validating the repo again
  - what outputs are expected and why
  - what work is still unfinished

This document intentionally uses plain-English status descriptions rather than
roadmap checkpoint shorthand.

## Current Position

In roadmap terms, all scoped work through `R11` is implemented for the
official board pair:

- `nrf52833dk`
- `nucleo_l476rg`

Historical live proof already exists for the scoped pair through `R11`, and
the latest mixed-board macOS rerun has now re-proved both scoped boards
through Stage 0 and Stage 1. That means the remaining work is no longer in the
shared hardware substrate; it is in the turnkey product layer and the broader
cross-host portability claims.

That means the following are already implemented, and at least historically
live-proven on the scoped pair:

- repo/environment standardization
- board bring-up and Stage 0 validation
- shared SWD and UART substrate
- Stage 1 smoke harness
- MCP server surface over the shared services
- runtime/session logging
- flash/recover guardrails
- mutation watcher behavior
- the first Codex-driven benchmark pilot

`R12` is now implemented in code, and the Codex-backed turnkey path has now
cleared the full frozen 12-case acceptance corpus on the scoped pair. The repo
now contains:

- the native Python brain package under `src/pyocd_debug_mcp/brain/`
- the typed turnkey evidence layer under `src/pyocd_debug_mcp/brain/evidence.py`
- the top-level `skills/` tree
- the internal deterministic helper tree under `playbooks/turnkey/`
- the `pyocd-debug-brain` CLI
- the additive `pyocd-debug` operator-facing CLI
- multiple decision-provider backends:
  - native OpenAI API
  - native Anthropic API
  - Codex CLI
  - Claude Code CLI
- the sibling turnkey benchmark path over the same 12-case corpus
- the new structured brain-event path that powers the operator shell and
  persists `runs/<session_id>/logs/brain_events.jsonl`
- the frozen `R12` contract in `markdowns/curr/r12_turnkey_spec.md`

The Ben mainline also now carries the Jason-originated hardening that was
missing before this merge pass:

- a transport seam in `brain/mcp_client.py`:
  - `ServerCommand`
  - `ToolClientProtocol`
  - transport-only stdio client
  - higher-level parsed client wrapper
- host-aware local rebuild execution instead of Windows-unsafe `bash`-only
  shelling
- typed observations / hypotheses / experiments / strategy-evaluation records
  in the turnkey state artifact
- internal deterministic helper playbooks separated from the model-facing
  prompt-skill tree
- per-tool timeout discipline in the turnkey loop so short runtime reads fail
  fast while connect/flash/recover/build paths still get longer budgets
- bounded runtime startup/provider/helper paths: local MCP startup, Codex/Claude
  CLI providers, OpenAI/Anthropic API providers, server probe helper commands,
  Stage 0/test-harness helper commands, and pyserial write windows now carry
  explicit project-defined timeout ceilings
- pyOCD flash/reset/step timeout options are passed explicitly through the
  shared session option builder; pyOCD connect remains a documented in-process
  vendor-call boundary because this installed pyOCD version has no direct
  connect-timeout option
- real file contents returned through `read_file(...)`, which fixed the live
  alternate-board repair loop
- UTF-8-with-replacement subprocess capture for Windows local builds and CLI
  provider calls
- generic alternate-suite acceptance logic so retained-board turnkey suites no
  longer fail only because the suite is not the scoped pair

What is still missing is full official-pair second-provider proof, live
operator-shell revalidation on the scoped pair, and fresh-machine portability
proof needed to call the turnkey layer fully closed.

The active prototype direction has also moved beyond the original narrow R12
acceptance layer. The current docs now track a capability prototype that adds
persistent provider sessions, free host-side model work with a final governed
board-decision boundary, real tool schemas, batched actions with `wait` and
UART write, live progress/inspector output, timeout hardening with
model-refined budgets, session-scoped client actions, scoped green approval via
model-made flipped tests, and stream checkpoints for UART/build/client-action
flows. Those items are planned prototype work unless a later status entry says
they have been implemented and verified.

The remaining proof work before making the broader "fresh customer machine"
portability claim is now narrower:

- extend the now-working second live provider path across the full official
  scoped pair and full turnkey ladder without changing the scoped corpus or the
  closure bar
- run a true fresh-machine Windows validation of the managed Zephyr/no-NCS path
- run the equivalent macOS managed-Zephyr validation on a clean host setup

The repo also still contains `nrf52840dk` as a retained alternate Nordic
profile. It is not the current blocker for the scoped project path, but it is
now live-proven on this Windows host for Zephyr rebuild, Stage 0, Stage 1, a
freeform healthy Codex turnkey run, the alternate six-case `R11` suite, and
the alternate six-case Codex-backed `R12` turnkey ladder both as individual
cases and as a one-command suite rerun.

## What Has Been Implemented

### Repo And Environment Foundation

These pieces are in place and are part of the working baseline:

- canonical product code under `src/pyocd_debug_mcp/`
- tracked board configs under `boards/`
- tracked reference firmware under `firmware/`
- runtime-output tree under `runs/`
- validation and harness code under `tests/`
- `uv`-based environment flow with `.python-version`
- auto-loaded local `.env` support
- shared board-config loader used by the main Python tools

### Board Bring-Up And Stage 0

These workflows exist and are live-proven:

- `host_bootstrap.py`
- `stage0_check.py`
- tracked reference firmware for:
  - `nucleo_l476rg`
  - `nrf52833dk`
- explicit serial/probe resolution and override paths
- real flash/UART validation against tracked reference artifacts
- Nordic recover/unlock validation

### Shared Hardware-Control Substrate

The repo now has one real shared control stack instead of separate one-off
paths:

- `adapters/swd_interface.py`
- `adapters/swd_pyocd.py`
- `adapters/uart_interface.py`
- `adapters/uart_pyserial.py`
- `services/target_control.py`
- `services/uart_capture.py`
- `services/symbols.py`
- `reference_artifacts.py`
- `probe_inventory.py`
- `serial_resolver.py`

Important architectural outcomes:

- probe inventory no longer depends on unsupported `pyocd list --output json`
- board-aware auto-selection is now API-first:
  - ask pyOCD for connected probes directly through `ConnectHelper.get_all_connected_probes(...)`
  - fall back to parsing `pyocd list --probes`, then plain `pyocd list`, only if the direct API path fails or returns no usable probes
- the shared path preserves real probe UIDs for both J-Link and ST-Link
- the shared SWD adapter now carries the J-Link serial-open quirk handling in
  one place:
  - always set pyOCD `jlink.non_interactive=false` for J-Link boards
  - if J-Link open-by-UID still fails with the known
    `No emulator with serial number ... found` error and exactly one matching
    probe is visible, retry the session open once without forcing the UID
- the MCP stdio path on this Windows host must not pre-run
  `pyocd list --probes` to auto-resolve an implicit J-Link UID before the real
  attach:
  - when `connect()` is called for a J-Link board without an explicit
    `unique_id` / `PYOCD_PROBE_UID`, the server now passes `unique_id=None`
    through to the shared backend and lets pyOCD choose the single attached
    probe directly
- the shared path is used by:
  - `host_bootstrap.py`
  - `stage0_check.py`
  - `tests.harness.stage1_smoke`
  - `server.connect(...)`

Rule for future files:

- do **not** call `ConnectHelper` directly from new wrappers, harnesses, or
  scripts
- always go through the shared `target_control.open_session()` /
  `adapters.swd_pyocd` path so probe-family-specific fixes such as the J-Link
  option policy and the guarded uidless retry stay centralized

### Stage 1 Smoke Harness

The tracked Stage 1 harness at `tests/harness/stage1_smoke.py` is real and
passing on both scoped boards.

It proves the following shared-service flow:

1. load board config
2. resolve reference artifacts
3. resolve the correct serial port
4. open the correct probe/session
5. flash the reference artifact
6. `reset_and_halt`
7. read `pc`
8. resolve `stage1_known_value` from the ELF
9. read back `0x1234ABCD` from target memory
10. reset/run
11. capture UART until `boot ok`

### MCP Server And Runtime Safety Layer

The current MCP server surface is implemented over the shared substrate and
has been exercised on both scoped boards.

Validated tool surface:

- `connect`
- `disconnect`
- `get_board_info`
- `get_state`
- `halt`
- `resume`
- `step`
- `reset`
- `read_core_register`
- `write_core_register`
- `read_memory`
- `read_memory_block`
- `write_memory`
- `set_breakpoint`
- `remove_breakpoint`
- `flash_firmware`
- `read_serial`
- `unlock_recover`

The runtime/safety layer that now exists in code includes:

- per-session `session_id` creation
- append-only JSONL event logging under `runs/<session_id>/logs/events.jsonl`
- per-session metadata under `runs/<session_id>/run-metadata/session.json`
- flash guardrails for local existing `.elf` / `.hex` files only
- recover guardrails based on board config and explicit confirmation
- mutation watcher rules for repeated flash failures, UART misses, and recover
  failures

### Turnkey Brain (`R12`) Implementation

The first turnkey product layer is now implemented in the repo.

Code that now exists:

- `src/pyocd_debug_mcp/brain/config.py`
- `src/pyocd_debug_mcp/brain/evidence.py`
- `src/pyocd_debug_mcp/brain/mcp_client.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/provider_factory.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_parsing.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/workspace.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/benchmark.py`
- `src/pyocd_debug_mcp/brain/cli.py`
- `src/pyocd_debug_mcp/brain/app.py`
- `src/pyocd_debug_mcp/brain/events.py`
- `src/pyocd_debug_mcp/brain/playbooks.py`
- `src/pyocd_debug_mcp/ux/cli.py`
- `src/pyocd_debug_mcp/ux/shell.py`
- `src/pyocd_debug_mcp/ux/renderer.py`
- `src/pyocd_debug_mcp/ux/history.py`
- `src/pyocd_debug_mcp/ux/artifacts.py`
- `src/pyocd_debug_mcp/ux/commands.py`
- `tests/harness/r12_turnkey_benchmark.py`
- `skills/common/...`
- `skills/mcu_families/nrf52833/...`
- `skills/mcu_families/stm32l476/...`
- `playbooks/turnkey/...`

What that code does:

- launches the existing MCP server as a local stdio subprocess
- talks to it directly without manual MCP registration
- supports four decision-provider modes:
  - `openai-api`
  - `anthropic-api`
  - `codex-cli`
  - `claude-cli`
- loads provider config from:
  - `PYOCD_TURNKEY_PROVIDER`
  - optional `PYOCD_TURNKEY_MODEL`
  - `OPENAI_API_KEY` for `openai-api`
  - `ANTHROPIC_API_KEY` for `anthropic-api`
- can reuse existing Codex or Claude Code CLI auth for subscription-backed
  turnkey runs
- selects board-aware YAML skills
- keeps local turnkey run state
- supports freeform `run` mode and benchmark mode
- captures turnkey artifacts into the same `runs/<session_id>/...` tree
- persists typed evidence inside `turnkey_state.json`
- emits and persists normalized brain events in `brain_events.jsonl`
- reuses the existing 12-case benchmark corpus instead of inventing a second
  benchmark taxonomy
- keeps deterministic repair/health-check helper playbooks in a separate
  internal layer rather than overloading the prompt-skill YAMLs

### Operator UX Layer Pass 1

The new operator-facing CLI is now implemented in code as `pyocd-debug`.

What it currently does:

- launches an interactive REPL shell with no args
- exposes pretty one-shot wrappers:
  - `pyocd-debug run ...`
  - `pyocd-debug benchmark ...`
  - `pyocd-debug history`
  - `pyocd-debug show <session_id>`
  - `pyocd-debug rerun <session_id>`
- renders live status for:
  - provider turns
  - MCP tool activity
  - builds
  - green-check runs
- shows evidence summaries after completed provider turns
- supports raw-provider-output visibility:
  - `/raw on`
  - `/raw off`
  - `/raw last`
  - one-shot `--raw-output off|final|all`
- now defaults the REPL to summary-first output instead of always echoing raw
  completed turns
- now persists v1 repair context in the REPL:
  - `/workspace <path|clear>`
  - `/build-command "<cmd>"|clear`
  - `/flash-artifact <path|default>`
  - `/elf <path|default>`
- now exposes guided commands over the existing freeform path:
  - `/verify [extra text]`
  - `/diagnose [extra text]`
  - `/repair [extra text]`
- now exposes common artifact shortcuts over the existing run tree:
  - `/prompt [session_id]`
  - `/diff [session_id]`
  - `/serial [session_id]`
  - `/score [session_id]`
  - `/events [session_id]`
- reuses the exact same brain loop and benchmark path as `pyocd-debug-brain`
  rather than forking any orchestration logic

What is not done yet:

- true token-level provider streaming
- live reconnection to an already-running historical session
- full fresh scoped-board live proof of the new summary-first/guided shell on
  this exact merged code across both required providers

### Latest Live UX Validation (2026-06-23, macOS mixed-board host)

This validation pass reran the scoped substrate first and then exercised the
new shell against the real attached boards.

What was re-proven before the shell work:

- `uv run pytest -q`
  - passed: `216 passed`
- `uv run ruff check .`
  - passed
- `uv run mypy src`
  - passed
- `uv run python host_bootstrap.py --board-id nucleo_l476rg`
  - passed
- `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg`
  - passed
- `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
  - passed
- `uv run python host_bootstrap.py --board-id nrf52833dk`
  - passed
- `uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk`
  - passed
- `uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk`
  - passed
- `uv run pyocd-debug --help`
  - passed
- `uv run pyocd-debug-brain --help`
  - passed

Additional code fix required during this live pass:

- the shell-guided `/verify` task initially failed incorrectly with
  `Refused [turnkey/missing-workspace-context]`
- root cause:
  - `task_requires_code_fix(...)` treated the phrase
    `Do not edit source files.` as a positive repair signal because it matched
    the raw token `edit`
- fix applied:
  - the code-fix heuristic now ignores common negated edit phrases before
    looking for real repair verbs
- verification after the fix:
  - targeted UX/turnkey tests passed
  - full repo checks still passed

Disposable repair workspaces prepared for this pass:

- root layout:
  - `/tmp/pyocd-ux-layout.DNtRkr`
- STM32 copied bug workspace:
  - `/tmp/pyocd-ux-layout.DNtRkr/firmware/nucleo_l476rg/bugs/b001__wrong_boot_text`
- Nordic copied bug workspace:
  - `/tmp/pyocd-ux-layout.DNtRkr/firmware/nrf52833dk/bugs/b001__wrong_boot_text`
- important detail:
  - the copied workspaces had to preserve the `firmware/...` relative layout,
    because the STM32 bug fixture references
    `../../../common/nucleo_l476rg.overlay`
  - the disposable copies were built successfully with the repo-rooted command
    form:
    - `uv run --project <repo-root> pyocd-zephyr-build ...`

Observed shell outcomes:

- live shell-side `/repair` refusal is now proven
  - command:
    - `/board nucleo_l476rg`
    - `/repair Restore the tracked healthy behavior.`
  - observed result:
    - deterministic shell refusal:
      `Refused [ux/missing-repair-context]: \`/repair\` requires /workspace <path> to be set first.`
  - no debug session was created for that refusal
- Codex shell proof is partial, not complete
  - provider:
    - `codex-cli`
  - board:
    - `nucleo_l476rg`
  - command:
    - `/verify Explain why this reference firmware is healthy.`
  - what was successfully observed:
    - summary-first rendering by default
    - no raw-provider-output panel before `/raw on`
    - real `connect(board_id="nucleo_l476rg")` path with no UID or serial-port override
    - real session created:
      - `session_id=20260623T215644Z-25551634`
      - run root:
        `runs/20260623T215644Z-25551634/`
    - server event log proves at least:
      - `connect`
      - `get_board_info`
  - what did **not** complete in a usable time window:
    - the freeform `/verify` run never reached a final healthy result during
      the validation window
    - `/raw on` completed-turn proof was therefore not established under Codex
    - fresh-session `/prompt`, `/serial`, `/events`, and `/score` checks were
      not completed under Codex
    - context-backed `/repair` was not completed under Codex
  - current interpretation:
    - this is a provider/loop completion problem, not a shell command-parsing
      problem and not a board-attach problem
- Claude shell proof is currently blocked by provider model resolution
  - provider:
    - `claude-cli --model sonnet`
  - board:
    - `nrf52833dk`
  - command:
    - `/verify Explain why this reference firmware is healthy.`
  - observed result:
    - provider failure before any board session was opened
    - exact error:
      `ProviderResponseError: Claude CLI provider did not return a valid turnkey action: API Error: 404 {"type":"error","error":{"type":"not_found_error","message":"model: claude-sonnet-4-20250514"}}`
  - consequence:
    - no `session_id`
    - no board attach
    - no artifact-shortcut validation under Claude
    - no context-backed `/repair` validation under Claude
  - current interpretation:
    - this is a provider precondition/configuration failure and must not be
      counted as successful UX proof

Remaining live UX gaps after this pass:

- rerun the Codex REPL ladder and get a complete `/verify` result to prove:
  - completed summary-first freeform success
  - `/raw on` completed-turn output
  - fresh-session `/prompt`, `/serial`, and `/events`
  - `/score` refusal on a completed freeform session
  - context-backed `/repair` on the disposable STM32 workspace
- fix or reconfigure the Claude CLI provider path so `--model sonnet` yields a
  valid live turn on this host, then rerun the same shell ladder on:
  - `nrf52833dk`
  - the disposable Nordic repair workspace
- only after those provider-dependent reruns should the remaining Pass 1 UX
  live-proof items be marked closed

### Manual UX Validation To Re-Run

Run these from repo root after the usual scoped substrate preflight:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run pyocd-debug --help
uv run pyocd-debug-brain --help
uv run pyocd-debug run --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug benchmark --case-id nucleo_l476rg__k001_reference_green
uv run pyocd-debug benchmark --case-id nrf52833dk__b001_wrong_boot_text
uv run pyocd-debug history
uv run pyocd-debug
```

Expected outcomes and why:

- `pyocd-debug --help`
  - should show `run`, `benchmark`, `history`, `show`, and `rerun`
  - because the new operator shell is an additive CLI layer, not a rewrite of
    `pyocd-debug-brain`
- `pyocd-debug run ...`
  - should create a normal turnkey `session_id`
  - should write the same `turnkey_request.json`, `turnkey_result.json`,
    `turnkey_state.json`, and now also `brain_events.jsonl`
  - should show live tool/progress activity plus a final result summary
  - because the shell is consuming real brain-loop events instead of replaying
    post-hoc text
- `pyocd-debug benchmark --case-id ...`
  - should reuse the same benchmark result/score path as the headless CLI
  - because the UX layer wraps the existing turnkey benchmark runner instead of
    creating a second benchmark implementation
- `pyocd-debug history`
  - should list saved turnkey sessions newest-first
  - because it reads `runs/<session_id>/run-metadata/turnkey_request.json`
    and `turnkey_result.json` rather than inventing a second state store
- `pyocd-debug` interactive shell
  - should default to summary-first rendering
  - should accept `/workspace`, `/build-command`, `/flash-artifact`, and
    `/elf` without changing the underlying turnkey invocation path
  - should let `/verify` and `/diagnose` run without code-edit context
  - should make `/repair` refuse until workspace/build context has been set
  - should surface `/prompt`, `/diff`, `/serial`, `/score`, and `/events`
    against the selected or most recent session
  - because the shell is meant to be a thin operator layer over the same brain
    runtime, not a second orchestration engine

Current rerun notes from the latest live pass:

- `/repair` refusal is already live-proven
- `/verify` no longer falsely refuses for missing repair context after the
  negated-`edit` heuristic fix
- Codex currently needs another rerun because the shell attached and created a
  real session, but the freeform verify path did not reach a final result in
  the validation window
- Claude currently needs provider repair or configuration before any of the
  shell-board proofs can count, because `--model sonnet` returned a live 404
  model-not-found error on this host

## Live Bench Facts

These are the current real bench facts that were proven on the Mac and Windows
hosts used for the scoped validation.

### `nucleo_l476rg`

- probe UID: `0668FF514988525067213913`
- serial port: `/dev/cu.usbmodem143103`
- pyOCD target: `stm32l476rgtx`
- pack token: `stm32l476`
- probe and COM port were confirmed to come from the same physical board

Additional proven host quirk for this board on the current Mac host:

- `connect_mode=under-reset`
- `frequency=1000000`

That matters because direct ST-Link attach could otherwise fail with the
pyOCD/ST-Link `DP wait` error even when the board is physically present.

Additional proven Windows host facts for this board:

- probe UID: `0670FF3031454D3043223536`
- serial port: `COM9`
- `host_bootstrap.py --board-id nucleo_l476rg --install-packs` passes
- `stage0_check.py --board-id nucleo_l476rg --reference-firmware ...` passes
- the local pinned `STM32L4xx_DFP` pack resolves `stm32l476rgtx` correctly on
  Windows too
- on this Windows host, `pyocd list --probes` can incorrectly report no probes,
  while `pyocd list` still prints the real ST-Link row; the shared
  `probe_inventory` path now falls back to plain `pyocd list` and also tolerates
  the Windows console encoding error path where pyOCD returns a nonzero exit code
  but still prints the valid probe table to stdout
- on this Windows host, MCP stdio `connect(board_id="nucleo_l476rg")` could
  also hang for roughly 30 to 40 seconds before attach because subprocess-based
  probe auto-resolution was slow inside the live server process; the shared
  fix is now to enumerate probes through the pyOCD Python API first, which makes
  the real MCP `connect` path return promptly again

### `nrf52833dk`

- probe UID: `685400693`
- serial port: `/dev/cu.usbmodem0006854006931`
- pyOCD target: `nrf52833`
- pack token: `nrf52833`
- silicon identity address: `0x10000100`
- expected silicon identity value: `0x00052833`
- live silicon identity match: confirmed
- probe and COM port were confirmed to come from the same physical board

## What Has Already Been Proven On Hardware

### STM32 Proof

These live runs were completed successfully on the scoped validation hosts:

```bash
uv run python host_bootstrap.py --board-id nucleo_l476rg --install-packs
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
```

Those runs prove:

- probe visibility
- target-pack availability
- SWD connect/read
- baseline flash
- UART `boot ok`
- symbol-resolution readback of `stage1_known_value = 0x1234ABCD`

### Nordic Proof

These live runs were completed successfully:

```bash
./firmware/nrf52833dk/reference/build_reference.sh
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

Those runs prove:

- probe visibility
- target-pack availability
- SWD connect/read
- exact silicon identity
- baseline flash
- UART `boot ok`
- recover/unlock behavior
- post-recover reachability
- symbol-resolution readback of `stage1_known_value = 0x1234ABCD`

### Server Runtime And Safety Proof

The current `server.py` implementation was exercised live against both scoped
boards. That proof covered:

- board-aware `connect(board_id=..., unique_id=None)` while both probes were
  attached
- creation of `session_id`
- creation of:
  - `runs/<session_id>/logs/events.jsonl`
  - `runs/<session_id>/run-metadata/session.json`
- default flash artifact resolution
- explicit flash artifact override
- default serial resolution
- explicit serial override
- Nordic recover success with explicit confirmation
- STM32 recover refusal because no supported recover mode is tracked
- watcher blocking for repeated bad mutation loops
- disconnect/reconnect clearing watcher block state

## Regression And Manual Validation Checklist

Use this section whenever you need to re-validate the repo on a new host, after
a substrate change, before rerunning the benchmark suite, or before claiming
that new higher-level work is being run on a known-good foundation.

### 1. Static And Contract Checks

Run from the repo root:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

Expected result:

- all commands succeed with exit code `0`

Why this is expected:

- the repo test suite, lint, and type-check path were already green when the
  current benchmark runner work landed
- a failure here means the repo is not even at the previously proven baseline,
  so hardware debugging would be misleading

### 2. Scoped Board Preflight

Run the foundation checks for both boards:

```bash
uv run python host_bootstrap.py --board-id nucleo_l476rg --install-packs
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg

uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

Expected result:

- all six commands pass
- `stage0_check.py` proves flash and UART on both boards
- `stage0_check.py` proves Nordic recover on `nrf52833dk`
- `stage1_smoke.py` proves symbol resolution and UART on both boards

Why this is expected:

- both boards already passed these exact workflows on the current Mac host
- the reference firmware artifacts, board configs, and shared services are now
  aligned around those flows

Windows retest note:

- on a fresh Windows STM32 host, prefer the exact same STM32 sequence above with
  `--install-packs`
- this is the repo-standard way to provision the pinned `STM32L4xx_DFP` pack
  before Stage 0 runs
- this STM32 Windows sequence is now bench-proven on the current Windows host

### 3. MCP Server Launch

Launch the server:

```bash
uv run mcp dev src/pyocd_debug_mcp/server.py
```

Expected result:

- the MCP dev server starts cleanly
- tool docstrings and tool surface are visible to the MCP client

Why this is expected:

- the current repo status already includes live tool-function validation over
  this server entrypoint

### 4. STM32 Manual Runtime Validation

Use `connect(board_id="nucleo_l476rg")` as the primary path. Do not pass
`unique_id` unless you are debugging probe-selection behavior.

Run this sequence:

1. `connect(board_id="nucleo_l476rg")`
2. verify success text contains:
   - `Connected to board`
   - `[board config: nucleo_l476rg]`
   - `via pyocd-native`
   - `session_id=`
3. verify:
   - `runs/<session_id>/logs/events.jsonl`
   - `runs/<session_id>/run-metadata/session.json`
4. `get_board_info()`
5. `flash_firmware()`
6. `flash_firmware(path="<repo-root>/firmware/nucleo_l476rg/reference/build/firmware.elf", halt_after_reset=true)`
7. `flash_firmware(path="<repo-root>/firmware/nucleo_l476rg/reference/build/firmware.hex")`
8. `halt()`
9. `read_core_register(name="pc")`
10. `read_memory(address="0x08000000", word_size=32)`
11. `resume()`
12. `read_serial(expected_text="boot ok", reset_on_open=true)`
13. `unlock_recover(confirm=false)`
14. `unlock_recover(confirm=true)`
15. repeat `unlock_recover(confirm=true)` twice more
16. `read_memory(address="0x08000000", word_size=32)`
17. `disconnect()`
18. reconnect with `connect(board_id="nucleo_l476rg")`
19. `flash_firmware(path="/tmp/r10-missing.elf")` three times
20. `read_memory(address="0x08000000", word_size=32)`
21. `disconnect()`

Expected result:

- `connect(...)` returns a `session_id`
- default and explicit flash succeed for valid baseline artifacts
- `read_serial(expected_text="boot ok", ...)` reports `UART matched` with
  expected text `boot ok`
- `unlock_recover(confirm=false)` refuses cleanly
- `unlock_recover(confirm=true)` refuses cleanly because STM32 has no tracked
  recover mode
- after repeated identical recover failures, only `unlock_recover` becomes
  blocked
- after repeated identical missing-file flash attempts, only
  `flash_firmware` becomes blocked
- read-only tools still work after watcher blocks
- disconnect/reconnect clears the block state
- refusal/block policy outcomes stay in normal tool text with prefixes such as
  `Refused [...]` and `Blocked [...]`, rather than surfacing as transport-level
  MCP errors

Why this is expected:

- the runtime session layer now logs per-session events
- the flash gate only allows real local `.elf` / `.hex` files
- the STM32 board config intentionally defines no recover path
- the watcher only blocks repeated mutation failures inside one session

### 5. Nordic Manual Runtime Validation

Use `connect(board_id="nrf52833dk")` as the primary path.

Run this sequence:

1. `connect(board_id="nrf52833dk")`
2. verify success text contains:
   - `Connected to board`
   - `[board config: nrf52833dk]`
   - `via pyocd-native`
   - `session_id=`
3. verify:
   - `runs/<session_id>/logs/events.jsonl`
   - `runs/<session_id>/run-metadata/session.json`
4. `get_board_info()`
5. `flash_firmware()`
6. `flash_firmware(path="<repo-root>/firmware/nrf52833dk/reference/build/firmware.elf", halt_after_reset=true)`
7. `flash_firmware(path="<repo-root>/firmware/nrf52833dk/reference/build/firmware.hex")`
8. `halt()`
9. `read_core_register(name="pc")`
10. `read_memory(address="0x10000000", word_size=32)`
11. `resume()`
12. `read_serial(reset_on_open=true)`
13. `unlock_recover(confirm=false)`
14. `unlock_recover(confirm=true)`
15. `flash_firmware()`
16. `read_serial(reset_on_open=true)`
17. `disconnect()`

Expected result:

- `connect(...)` returns a `session_id`
- default and explicit flash succeed for valid baseline artifacts
- `read_serial(expected_text="boot ok", ...)` reports `UART matched` with
  expected text `boot ok`
- `unlock_recover(confirm=false)` refuses cleanly
- `unlock_recover(confirm=true)` succeeds
- after recover, the baseline can be reflashed and UART can be re-verified

Why this is expected:

- `nrf52833dk` has a tracked recover policy
- its reference baseline is already known-good and recover-safe on the current
  Mac bench

### 6. Nordic UART Watcher Validation

Use a fresh Nordic session:

1. `connect(board_id="nrf52833dk")`
2. `read_serial(expected_text="__never_matches__", reset_on_open=true, read_seconds=3.0)`
3. repeat the same call three more times
4. verify the fourth call is blocked
5. run `get_state()` or `read_memory(address="0x10000000", word_size=32)`
6. `disconnect()`
7. reconnect with `connect(board_id="nrf52833dk")`
8. `read_serial(reset_on_open=true)`
9. `flash_firmware(path="/tmp/r10-guardrail.bin")`
10. `disconnect()`

Before this check, create an invalid flash artifact:

```bash
printf 'not firmware\n' > /tmp/r10-guardrail.bin
```

Expected result:

- the first three bad UART checks produce non-match summaries, not crashes
- the fourth identical UART miss is blocked
- read-only tools still work while UART reads are blocked
- reconnect clears the block state
- `.bin` flashing refuses deterministically

Why this is expected:

- the watcher tracks repeated identical UART misses per session
- the flash guardrail explicitly rejects unsupported suffixes

### 7. Expected Response Shapes

These response shapes are important because the repo now depends on them being
stable and understandable.

`connect(...)` success should contain:

- `Connected to board`
- `[board config: <board_id>]`
- `via pyocd-native`
- `session_id=<id>`

Why expected:

- the runtime layer now creates a named session on successful connect

`flash_firmware(...)` success should look like:

- `Flashed <path> via pyocd-native; target left running.`
- or `Flashed <path> via pyocd-native; target left halted.`

Why expected:

- the wrapper now reports both the artifact identity and the post-flash target
  state

`read_serial(...)` success should look like:

- `UART matched on <port> at <baud> baud via pyocd-native; expected=(none); reopen_count=<n>; duration=<s>; excerpt=<text>`
- or, when an explicit substring is requested:
  `UART matched on <port> at <baud> baud via pyocd-native; expected='boot ok'; reopen_count=<n>; duration=<s>; excerpt=<text>`

Why expected:

- the UART service now returns bounded, deterministic capture summaries instead
  of ambiguous empty success

Recover refusal should look like:

- `Refused [<code>]: <message> session_id=<id>`

Watcher block should look like:

- `Blocked [<code>]: <message> session_id=<id>`

Why expected:

- the runtime policy layer distinguishes deliberate refusal from unexpected
  backend failure

## What Should Be Verified Again Before Rerunning The Benchmark Suite

Before rerunning the benchmark suite on a host, or before starting the next
turnkey-product layer on top of this substrate, re-check these exact things:

- both scoped boards still pass Stage 0 and Stage 1 smoke
  - because the benchmark runner assumes known-good baseline behavior exists
- board-aware auto-selection still chooses the correct probe while both boards
  are attached
  - because the benchmark prompts are supposed to connect by `board_id`, not by
    hard-coded probe UID
- `session_id` creation and `runs/<session_id>/...` logging still happen
  - because benchmark artifacts are keyed off the session directory
- default artifact resolution still points at the tracked baseline per board
  - because the runner and server both depend on that contract
- recover behavior still differs correctly by board
  - `nrf52833dk` should recover
  - `nucleo_l476rg` should refuse
- watcher state still clears on disconnect/reconnect
  - because the benchmark runner assumes each case starts from a clean session
- the STM32 benchmark target is the exact tracked `nucleo_l476rg` baseline, not
  a near-family substitute
  - because the R11 oracle assumes the tracked reference firmware, UART
    contract, and symbol contract for that exact board id

## Benchmark Phase Status

The benchmark phase is implemented in the repo and is now live-proven on the
current mixed-board Mac host.

What is already tracked:

- benchmark spec in `markdowns/curr/r11_benchmark_spec.md`
- case format under `tests/cases/<case_id>/case.yaml`
- Codex result schema under `tests/cases/r11_result_schema.json`
- pilot suite ordering under `tests/cases/suites.yaml`
- tracked known-good, injected-bug, and observability-fault cases
- bug fixture trees under `firmware/<board>/bugs/<id>__<slug>/`
- canonical runner at `tests/harness/r11_benchmark.py`

### Benchmark Runner Commands

Runner prerequisite:

```bash
codex mcp add pyocd-debug -- uv run pyocd-debug-mcp
codex mcp get pyocd-debug
```

Runner guardrails:

- before launching Codex for a case, the runner now enforces a per-board
  Stage 1 smoke preflight
- if that preflight fails, the case aborts immediately with a host-bench error
  instead of spending minutes inside a non-converging Codex run
- Codex execution is now time-bounded so a stuck case cannot hang indefinitely
- the runner now gives embedded `codex exec` bug-repair cases a longer default
  budget so diagnose -> patch/build -> flash/verify runs can finish cleanly
  instead of being cut off by a blanket sub-60-second cap
- benchmark prompts are intentionally self-contained and tell the nested agent
  not to spend time re-reading workflow docs or skills
- that self-contained prompt rule is benchmark-specific only; real deployment
  runs should still read the repo workflow docs and skills before acting

Single-case entrypoint:

```bash
uv run python -m tests.harness.r11_benchmark --case-id nucleo_l476rg__k001_reference_green
```

Pilot suite entrypoint:

```bash
uv run python -m tests.harness.r11_benchmark --suite pilot_v1
```

Frozen pilot order:

1. `nucleo_l476rg__k001_reference_green`
2. `nrf52833dk__k001_reference_green`
3. `nucleo_l476rg__b001_wrong_boot_text`
4. `nrf52833dk__b001_wrong_boot_text`
5. `nucleo_l476rg__b002_wrong_known_value`
6. `nrf52833dk__b002_wrong_known_value`
7. `nucleo_l476rg__f001_halted_target_silent_uart`
8. `nrf52833dk__f001_halted_target_silent_uart`

### Local Benchmark Validation Already Completed

These local checks already passed when the benchmark runner landed:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py tests/test_r11_benchmark.py
uv run pytest -q tests/test_r11_benchmark.py
uv run python -m tests.harness.r11_benchmark --help
```

Why those results are expected:

- the benchmark runner, schema validation, workspace isolation, and scoring
  logic already have local test coverage in the repo

### Live Benchmark Validation Already Completed

The following live benchmark commands were completed successfully on the current
Mac host after Codex MCP registration was added:

```bash
codex mcp add pyocd-debug -- uv run pyocd-debug-mcp
codex mcp get pyocd-debug

uv run python -m tests.harness.r11_benchmark --case-id nrf52833dk__k001_reference_green
uv run python -m tests.harness.r11_benchmark --case-id nrf52833dk__f001_halted_target_silent_uart
uv run python -m tests.harness.r11_benchmark --suite pilot_v1

uv run python -m tests.harness.r11_benchmark --case-id nucleo_l476rg__b003_silent_uart
uv run python -m tests.harness.r11_benchmark --case-id nrf52833dk__b003_silent_uart
uv run python -m tests.harness.r11_benchmark --case-id nucleo_l476rg__b004_dual_signal_regression
uv run python -m tests.harness.r11_benchmark --case-id nrf52833dk__b004_dual_signal_regression
```

Observed benchmark result:

- `nucleo_l476rg__k001_reference_green`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__k001_reference_green`: `FULL_SUCCESS`, score `100`
- `nucleo_l476rg__b001_wrong_boot_text`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__b001_wrong_boot_text`: `FULL_SUCCESS`, score `100`
- `nucleo_l476rg__b002_wrong_known_value`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__b002_wrong_known_value`: `FULL_SUCCESS`, score `100`
- `nucleo_l476rg__f001_halted_target_silent_uart`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__f001_halted_target_silent_uart`: `FULL_SUCCESS`, score `100`
- suite summary: `full_success=8`, `partial_success=0`, `fail=0`,
  `average_score=100.0`
- `nucleo_l476rg__b003_silent_uart`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__b003_silent_uart`: `FULL_SUCCESS`, score `100`
- `nucleo_l476rg__b004_dual_signal_regression`: `FULL_SUCCESS`, score `100`
- `nrf52833dk__b004_dual_signal_regression`: `FULL_SUCCESS`, score `100`
- alternate retained Nordic profile `nrf52840dk` is now also live-proven on
  this Windows host:
  - `uv run pyocd-zephyr-build --app-dir firmware/nrf52840dk/reference/src --build-dir firmware/nrf52840dk/reference/build --board nrf52840dk/nrf52840`
  - `uv run python host_bootstrap.py --board-id nrf52840dk`
  - `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --recover-test nrf52840dk --confirm-shared-usb nrf52840dk`
  - `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`
  - `uv run python -m tests.harness.r11_benchmark --case-id nrf52840dk__k001_reference_green`
  - `uv run python -m tests.harness.r11_benchmark --case-id nrf52840dk__b001_wrong_boot_text`
  - `uv run python -m tests.harness.r11_benchmark --case-id nrf52840dk__b002_wrong_known_value`
  - `uv run python -m tests.harness.r11_benchmark --case-id nrf52840dk__f001_halted_target_silent_uart`
  - `uv run python -m tests.harness.r11_benchmark --case-id nrf52840dk__b003_silent_uart`
  - `uv run python -m tests.harness.r11_benchmark --case-id nrf52840dk__b004_dual_signal_regression`
  - all six alternate `nrf52840dk` cases reached `FULL_SUCCESS`, score `100`

What that means:

- the frozen eight-case pilot passed end to end on the scoped pair
- the final minimal pre-wrap-up `R11` expansion landed without widening the
  runner contract, scoring rubric, result schema, or MCP surface
- the repo now distinguishes two superficially similar UART-miss diagnoses:
  - `f001_halted_target_silent_uart`: runtime/observability fault
  - `b003_silent_uart`: firmware code bug
- the repo now also exercises a combined two-symptom code repair path through
  `b004_dual_signal_regression`
- the current MCP surface was usable by a real external agent client
- the scoring rubric produced clean full-success outcomes on known-good,
  injected-bug, and observability-fault cases
- the benchmark runner captured complete run artifacts under
  `runs/<session_id>/...`
- board-aware `connect(board_id=...)` worked on the mixed-board host for both
  the STM32 and Nordic cases

## Turnkey Brain Status

The turnkey layer is now in the repo and has full live Codex-backed proof on
the scoped pair, but it is not fully closed yet because the required second
provider path is still blocked on this host.

### Latest Live Codex Turnkey Evidence

Live reruns on the current mixed-board macOS host now establish all of the
following through the turnkey path with `PYOCD_TURNKEY_PROVIDER=codex-cli`:

- healthy freeform verification passed on `nucleo_l476rg`
- healthy freeform verification passed on `nrf52833dk`
- the turnkey client started and stopped the MCP server itself
- the normal path connected by `board_id` only
- no explicit probe UID or serial-port override was needed
- turnkey artifacts were written under `runs/<session_id>/...`
- a clean six-case live pilot passed end to end:
  - `nucleo_l476rg__k001_reference_green`
  - `nrf52833dk__k001_reference_green`
  - `nucleo_l476rg__b001_wrong_boot_text`
  - `nrf52833dk__b001_wrong_boot_text`
  - `nucleo_l476rg__f001_halted_target_silent_uart`
  - `nrf52833dk__f001_halted_target_silent_uart`
- the full frozen 12-case suite also passed end to end:
  - command:
    `uv run pyocd-debug-brain benchmark --provider codex-cli --suite pilot_v1_plus_b003_b004`
  - outcome:
    `full_success=12`, `partial_success=0`, `fail=0`, `average_score=100.0`
  - no case required explicit UID or serial-port tuning
  - no case watcher-blocked from turnkey thrash
  - no forbidden recover usage occurred on non-recover cases

Recorded freeform sessions:

- `nucleo_l476rg`: `20260622T060957Z-41201f6d`
- `nrf52833dk`: `20260622T064455Z-3cb81b85`

Recorded six-case pilot sessions:

- `20260622T075340Z-2ea5e8d1`:
  `nucleo_l476rg__k001_reference_green` -> `FULL_SUCCESS`, score `100`
- `20260622T075647Z-e2a70406`:
  `nrf52833dk__k001_reference_green` -> `FULL_SUCCESS`, score `100`
- `20260622T080133Z-f1e887c7`:
  `nucleo_l476rg__b001_wrong_boot_text` -> `FULL_SUCCESS`, score `100`
- `20260622T080806Z-659b48bc`:
  `nrf52833dk__b001_wrong_boot_text` -> `FULL_SUCCESS`, score `100`
- `20260622T081211Z-a032305a`:
  `nucleo_l476rg__f001_halted_target_silent_uart` -> `FULL_SUCCESS`, score `100`
- `20260622T081440Z-9a0f4dc6`:
  `nrf52833dk__f001_halted_target_silent_uart` -> `FULL_SUCCESS`, score `100`

Recorded full-suite sessions:

- `20260622T211939Z-fb47c2f3`:
  `nucleo_l476rg__k001_reference_green` -> `FULL_SUCCESS`, score `100`
- `20260622T212201Z-fe90654f`:
  `nrf52833dk__k001_reference_green` -> `FULL_SUCCESS`, score `100`
- `20260622T212514Z-bce664a7`:
  `nucleo_l476rg__b001_wrong_boot_text` -> `FULL_SUCCESS`, score `100`
- `20260622T212948Z-82eff454`:
  `nrf52833dk__b001_wrong_boot_text` -> `FULL_SUCCESS`, score `100`
- `20260622T213434Z-176a3cbe`:
  `nucleo_l476rg__b002_wrong_known_value` -> `FULL_SUCCESS`, score `100`
- `20260622T214123Z-da9a888d`:
  `nrf52833dk__b002_wrong_known_value` -> `FULL_SUCCESS`, score `100`
- `20260622T214530Z-51579242`:
  `nucleo_l476rg__f001_halted_target_silent_uart` -> `FULL_SUCCESS`, score `100`
- `20260622T215011Z-eea0d767`:
  `nrf52833dk__f001_halted_target_silent_uart` -> `FULL_SUCCESS`, score `100`
- `20260622T215255Z-460a2987`:
  `nucleo_l476rg__b003_silent_uart` -> `FULL_SUCCESS`, score `100`
- `20260622T220304Z-0897b005`:
  `nrf52833dk__b003_silent_uart` -> `FULL_SUCCESS`, score `100`
- `20260622T221056Z-eae2cf78`:
  `nucleo_l476rg__b004_dual_signal_regression` -> `FULL_SUCCESS`, score `100`
- `20260622T221559Z-96a09a7c`:
  `nrf52833dk__b004_dual_signal_regression` -> `FULL_SUCCESS`, score `100`

Important live issues that were exposed and fixed during this pass:

- the turnkey loop previously counted intermediate flash/read states as failed
  repair cycles and could block a repaired code-bug case before
  `run_green_check` had a chance to verify the fix
- the turnkey loop previously treated `run_green_check` as an out-of-band
  verifier that disconnected the active MCP session; failed green checks could
  then force a second session and automatically violate the one-session
  benchmark rule
- `flash_firmware(path="build/firmware.hex")` from the turnkey benchmark could
  previously resolve against the repo root instead of the prepared case
  workspace; relative flash paths are now normalized against the prepared
  workspace root
- the injected-bug benchmark prompt was too loose for single-symptom bug cases,
  so the model could over-repair and damage a healthy tracked observable; the
  prompt now explicitly requires minimal repairs and case-family-specific
  preservation rules

### Latest Live Claude CLI Evidence

The second-provider path is no longer globally blocked. The latest live status
is:

- historical macOS `--model sonnet` attempts failed before board action
- current Windows STM32 Claude runs are now green on the attached
  `nucleo_l476rg`
- the remaining gap is full official-pair closure, not basic provider
  usability

Historical macOS attempted commands:

```bash
uv run pyocd-debug-brain run --provider claude-cli --model sonnet --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider claude-cli --model sonnet --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
```

Historical macOS observed result on both commands:

- no `session_id` was created
- no board session directory was created under `runs/<session_id>/...`
- the failure happened inside the Claude CLI provider before any live board
  action
- the exact provider error was:
  - `API Error: 404 {"type":"error","error":{"type":"not_found_error","message":"model: claude-sonnet-4-20250514"}}`

New Windows STM32 evidence:

```bash
uv run pyocd-debug-brain run --provider claude-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__k001_reference_green
```

Observed result on the Windows Nucleo pass:

- freeform run passed with `session_id=20260623T052725Z-a07db21b`
- benchmark known-good case passed with `session_id=20260623T052856Z-121bed12`
- the provider reached real board action, created normal run artifacts, and
  completed verification successfully

Why this matters:

- the old macOS 404 was a host/provider configuration failure, not a Stage 0 /
  Stage 1 / MCP substrate failure
- the newer Windows proof shows the Claude provider seam itself is viable in
  the merged product
- the Claude six-case pilot and full 12-case official-pair suite are still
  intentionally pending until the scoped Nordic board is attached for a real
  closure pass
- the turnkey layer therefore remains open until a real second-provider ladder
  completes successfully

### Turnkey Commands

Set turnkey provider config first.

For native OpenAI API runs:

```bash
export PYOCD_TURNKEY_PROVIDER=openai-api
export OPENAI_API_KEY=...
export PYOCD_TURNKEY_MODEL=...
```

For native Anthropic API runs:

```bash
export PYOCD_TURNKEY_PROVIDER=anthropic-api
export ANTHROPIC_API_KEY=...
export PYOCD_TURNKEY_MODEL=...
```

For subscription-backed local CLI runs:

```bash
export PYOCD_TURNKEY_PROVIDER=codex-cli
uv run pyocd-debug-brain run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."

export PYOCD_TURNKEY_PROVIDER=claude-cli
uv run pyocd-debug-brain run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
```

Or put the same values in the local gitignored `.env`.

Freeform verify/diagnose runs:

```bash
uv run pyocd-debug-brain run --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
```

Single-case turnkey benchmark runs:

```bash
uv run pyocd-debug-brain benchmark --case-id nucleo_l476rg__k001_reference_green --model <model>
uv run pyocd-debug-brain benchmark --case-id nrf52833dk__k001_reference_green --model <model>
uv run pyocd-debug-brain benchmark --case-id nucleo_l476rg__b003_silent_uart --model <model>
uv run pyocd-debug-brain benchmark --case-id nrf52833dk__f001_halted_target_silent_uart --model <model>
```

Full turnkey benchmark roll-up:

```bash
uv run pyocd-debug-brain benchmark --suite pilot_v1_plus_b003_b004 --model <model>
```

### What Has Already Been Verified Live

For both `nucleo_l476rg` and `nrf52833dk`, the current Codex-backed turnkey
path has now been shown to do all of the following:

- create a real `session_id`
- create:
  - `runs/<session_id>/run-metadata/turnkey_request.json`
  - `runs/<session_id>/run-metadata/turnkey_result.json`
  - `runs/<session_id>/run-metadata/turnkey_state.json`
  - `runs/<session_id>/logs/brain_trace.jsonl`
  - `runs/<session_id>/logs/model_turns.jsonl`
  - `runs/<session_id>/logs/prompt.txt`
  - `runs/<session_id>/applied-patches/turnkey.diff`
- connect with `connect(board_id=...)` rather than a hard-coded UID
- work without an explicit serial-port override on the normal path
- explain healthy reference firmware in board-grounded terms rather than vague
  generic prose

New mainline-hardening proof now also exists on this Windows host:

- the host-aware rebuild path works through the turnkey benchmark on attached
  `nrf52840dk` without relying on Windows `bash`
- the turnkey loop now records typed observations / hypotheses / experiments /
  strategy evaluations in `turnkey_state.json`
- the alternate-board `nrf52840dk` turnkey cases now accept against the same
  runner after the alternate-suite acceptance logic was generalized
- the live `read_file(...)` path now returns source contents instead of only a
  char-count placeholder, which fixed the previously failing
  `nrf52840dk__b003_silent_uart` repair loop
- Windows Codex CLI provider turns and local rebuild captures now tolerate
  non-ASCII subprocess output through UTF-8-with-replacement decoding

For the six-case pilot and full Codex suite above, the turnkey path has also
now been shown to:

- confirm known-good cases as healthy
- repair the `b001_wrong_boot_text` code bug on both boards
- classify the halted-target silent-UART cases as observability/runtime-state
  problems rather than firmware code bugs
- produce complete benchmark artifacts under the canonical
  `runs/<session_id>/...` roots

### What Still Needs To Be Verified Before Calling Turnkey Closed

The following proof work is still required before the turnkey product layer
should be treated as complete:

- extend the now-working Claude CLI path from the attached STM32 proof to the
  official scoped pair closure ladder:
  - healthy freeform verification on both scoped boards
  - six-case pilot-equivalent coverage for the attached board(s)
  - full `pilot_v1_plus_b003_b004` suite once the official pair is attached
- if Claude is not the intended second-provider path after all, explicitly
  freeze a replacement provider/model path and rerun the same ladder rather
  than changing the closure bar informally
- after a real official-pair second-provider pass exists, update the remaining
  repo-facing status text so `R12` can be treated as closed

### Why Those Checks Matter

These are the core product claims for the first turnkey layer:

- parity on the same benchmark corpus that already proved the BYO-agent path
- lower operator/setup burden than the Codex-driven path
- no reliance on prompt authoring, Codex installation, or MCP registration
- no reopening of the underlying server/substrate architecture

Latest scoped substrate reruns:

- both board-level truth paths were rerun successfully on the current macOS
  mixed-board host:
  - `uv run python host_bootstrap.py --board-id nucleo_l476rg`
  - `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg`
  - `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
  - `uv run python host_bootstrap.py --board-id nrf52833dk`
  - `uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk`
  - `uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk`
- this re-established that the remaining work is in the turnkey client rather
  than in Stage 0 / Stage 1 substrate drift

Important runner-accounting outcome:

- the benchmark runner no longer requires exactly one MCP session directory per
  case
- the final structured `session_id` returned by Codex is the canonical case
  root
- extra MCP sessions are treated as runner warnings rather than automatic
  benchmark failures
- this change was necessary because real Codex behavior can include a short
  scouting session before the final successful verification session

Important hardening outcome from the expansion:

- the added `b004` cases exposed a real benchmark trust bug:
  the runner previously allowed agent self-reported green verification to
  override a failing runner-owned final verification
- this is now fixed:
  runner-owned final verification is authoritative for scoring and outcome
  classification
- the mirrored `b004` bug fixtures were also tightened to preserve the stable
  Stage 1 symbol-access pattern, so the intended repair is “restore the wrong
  contract values” rather than “invent a new symbol-storage scheme”

Canonical roll-up command for the expanded corpus:

```bash
uv run python -m tests.harness.r11_benchmark --suite pilot_v1_plus_b003_b004
```

What to expect from that roll-up:

- `pilot_v1` remains frozen as the original eight-case milestone
- the four new expansion cases append after the original eight
- the most important new proof is already established by the four successful
  individual runs above; the aggregate suite simply replays the same corpus in
  one command

## What Still Needs To Be Fully Done

The scoped hardware-control substrate is not the blocker anymore. The remaining
work is all in the turnkey product layer.

### Immediate Next Tasks

1. Re-run the official scoped Nordic `R12` live chain in the latest merged
   benchmark state on `nrf52833dk`, not just historically.
2. Extend the second-provider ladder from the newly proven STM32 Claude runs to
   the full official scoped pair:
   - freeform healthy run on both boards
   - six-case pilot-equivalent coverage for the attached board(s)
   - full `pilot_v1_plus_b003_b004` suite when the pair is attached together
3. Compare the second provider against the already-proven Codex-backed path:
   - same case outcomes
   - same safety behavior
   - whether the normal path still works from `board_id` only
4. Only after the official-pair second-provider evidence exists, decide whether the turnkey
   layer is ready to be treated as closed.

### Remaining Proof Work Before Broader Deployment Claims

The repo is ready to move on to `R12` on the STM32 side, but a few proof tasks
still remain before the team should treat the latest portability/build-path
changes as fully bench-proven for customers:

1. Re-run the official scoped Nordic `R11` live chain in the current post-fix
   benchmark state, so the latest runner/build-path changes are re-proven on
   `nrf52833dk`, not only historically proven from earlier runs.
2. Run a true fresh-machine Windows validation without relying on a preexisting
   NCS install:
   host bootstrap, managed Zephyr bring-up, firmware rebuild, Stage 0, Stage 1,
   and at least one live benchmark case.
3. Run the equivalent macOS validation for the managed Zephyr/no-NCS path,
   because the latest benchmark/build-path changes have not yet been re-proven
   live on macOS in the current post-fix state.
4. Record the results of those validations back into this file and `README.md`
   before treating the broader cross-platform self-contained deployment claim as
   fully closed.

### What `R11` Already Proved

The first live benchmark pass has already proved all of the following:

- benchmark artifacts land in the correct `runs/<session_id>/...` tree
- both known-good cases score as healthy full-success cases
- both injected code-bug families reached full success on both boards
- the added `b003_silent_uart` family proves the agent can distinguish “missing
  application success UART because the target is halted” from “missing
  application success UART because the firmware is wrong”
- the added `b004_dual_signal_regression` family proves the agent can repair a
  combined UART-plus-symbol regression while still staying inside the one-file
  benchmark workspace contract
- both observability-fault cases were diagnosed as runtime/observability problems
  rather than code bugs
- the scoring rubric is understandable on real runs
- the runner’s capture/export path is sufficient for later analysis
- extra MCP sessions can occur in real Codex runs without invalidating the
  benchmark result, as long as the final structured `session_id` maps cleanly
  to a real run directory

### Optional Follow-Up Work After The Turnkey Pass

These are real tasks, but they are not the current blocker:

- post-fix Nordic live rerun for the official `nrf52833dk` bench path
- fresh-machine Windows managed-Zephyr / no-NCS validation
- fresh-machine macOS managed-Zephyr / no-NCS validation
- optional future parity rerun on `nrf52840dk` if that alternate profile is
  promoted from retained proof path to an official scoped support target
- further corpus expansion after the current twelve-case set is trustworthy

## nRF52840 Alternate Nordic Status

`nrf52840dk` is no longer waiting on first proof. It now has a real Windows
host proof stack on attached hardware. The numbered items below are historical
setup notes; the current proven results are:

- `uv run pyocd-zephyr-build --app-dir firmware/nrf52840dk/reference/src --build-dir firmware/nrf52840dk/reference/build --board nrf52840dk/nrf52840`
- `uv run python host_bootstrap.py --board-id nrf52840dk`
- `uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf --recover-test nrf52840dk --confirm-shared-usb nrf52840dk`
- `uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk`
- `uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52840dk --task "Verify this reference firmware is healthy and explain why."`
- all six implemented `nrf52840dk` `R11` cases reached `FULL_SUCCESS`:
  `k001`, `b001`, `b002`, `f001`, `b003`, `b004`
- on June 22, 2026, all six alternate-board Codex-backed `R12` turnkey cases
  also reached `FULL_SUCCESS` on this Windows host:
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__k001_reference_green`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__b001_wrong_boot_text`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__b002_wrong_known_value`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__f001_halted_target_silent_uart`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__b003_silent_uart`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52840dk__b004_dual_signal_regression`
- the run roots for those six live `R12` passes are:
  - `20260623T023010Z-9a4bfde3`
  - `20260623T025702Z-b71d3ee4`
  - `20260623T023621Z-8a0e1bb9`
  - `20260623T023941Z-b3bfc317`
  - `20260623T022530Z-9ffb99dc`
  - `20260623T024316Z-a5ce88bb`
- on June 23, 2026, the retained-board freeform Codex turnkey run also passed:
  - session root: `20260623T034813Z-4301eb52`
  - result: `[HEALTHY_CONFIRMED]`
- on June 23, 2026, the retained-board one-command Codex turnkey suite rerun
  also passed in the current merged state:
  - command:
    `uv run pyocd-debug-brain benchmark --provider codex-cli --suite nrf52840dk_v1_plus_b003_b004`
  - suite summary:
    `full_success=6`, `partial_success=0`, `fail=0`, `average_score=100.0`
  - case run roots:
    - `20260623T035021Z-e60b20c3`
    - `20260623T035301Z-18bc10da`
    - `20260623T035705Z-892b585d`
    - `20260623T040041Z-47861540`
    - `20260623T040253Z-7b5f1e56`
    - `20260623T040728Z-ff4cf87c`
  - observed runtime was about 20 minutes 43 seconds and continued to make
    forward case-by-case progress throughout, so this was treated as a valid
    long-running suite rather than a hang boundary

Important live failure boundaries that were exposed and fixed during that
alternate-board `R12` pass:

- the alternate-suite acceptance function was incorrectly hardcoded to the
  official scoped pair and could fail a real retained-board suite even when all
  retained-board cases were green
- the turnkey `read_file(...)` action previously returned only a char-count
  summary instead of the actual file contents, which prevented the model from
  seeing the source it repeatedly requested during `nrf52840dk__b003_silent_uart`
- Windows subprocess capture for local rebuilds and CLI-provider calls
  previously assumed the host code page, which caused `UnicodeDecodeError`
  noise during successful runs until the capture path was switched to
  UTF-8-with-replacement decoding

What is still not proven by this alternate-board run:

- the official scoped Nordic board `nrf52833dk` has not yet been re-run in the
  latest post-fix benchmark/build state
- a truly fresh Windows or macOS host without a preexisting `NCS` install has
  not yet been validated end to end with the managed no-`NCS` path

1. **Install NCS (nRF/Nordic only).** Install **nRF Connect SDK (NCS)** via the
   nRF Connect for VS Code extension (Toolchain Manager). The GUI/IDE is only the
   installer — builds run from `west` / the board build script afterward, so the
   IDE is not otherwise needed. What you actually need is the **NCS workspace**
   (the `zephyr/`, `nrf/`, `nrfxlib/` repos) plus a Zephyr SDK toolchain.
2. **NCS is Nordic-only.** This applies to `nrf52840dk` (and other nRF boards),
   **not** to the STM32 `nucleo_l476rg`, which stays on upstream Zephyr.
3. **Why NCS.** It is the common production path for nRF (and required for the
   SoftDevice Controller / Nordic BLE mesh later), and the agent rebuilds firmware
   with whatever toolchain the board's build script targets — so testing on NCS
   keeps your build and the agent's rebuild on the same toolchain. (A plain
   upstream-Zephyr build also works for the trivial reference app, but standardize
   on one toolchain per board.)
4. **Produce a real 52840 reference artifact (cannot be downloaded).** The
   `stage1_smoke` contract needs the firmware to print `boot ok` and expose
   `stage1_known_value = 0x1234ABCD`; no prebuilt hex satisfies that. Create
   `firmware/nrf52840dk/reference/` mirroring `firmware/nrf52833dk/reference/`
   (`src/` + a `build_reference.sh` with `BOARD=nrf52840dk/nrf52840`), then build
   it to `firmware/nrf52840dk/reference/build/firmware.{elf,hex}`.
5. **Point the build at the NCS workspace with env vars, not code edits.** The
   existing `build_*.sh` is already `west build` against `$WORKSPACE_DIR`:
   - `ZEPHYR_WORKSPACE_DIR=<NCS workspace root>` — the directory that **contains**
     `zephyr/`, `nrf/`, `nrfxlib/`, `.west/` (e.g. `~/ncs/<version>`), **not** the
     inner `zephyr/` folder (pointing at the inner one loses the Nordic modules).
   - `ZEPHYR_SDK_INSTALL_DIR=<NCS's bundled Zephyr SDK>` — set explicitly, because
     the script's auto-detect only finds a standalone `zephyr-sdk-*`.
   - If `west` complains about a version mismatch against the NCS manifest, use
     NCS's own `west` instead of the script's pip-installed one.
6. **Keep provenance consistent.** If you standardize nRF builds on NCS, rebuild
   and re-verify the existing `nrf52833dk` baseline under NCS too, so committed
   artifacts match what the agent rebuilds. Do not leave `nrf52833dk`
   upstream-Zephyr-built while `nrf52840dk` is NCS-built (functionally equivalent
   for these printk apps, but keep provenance consistent). Record the 52840
   artifact's toolchain provenance in the "Live Bench Facts" section once proven.
7. **Then run the standard validation** with `--board-id nrf52840dk`:
   `host_bootstrap.py` → `stage0_check.py` (with `--reference-firmware` and, since
   it is Nordic, `--recover-test`) → `tests.harness.stage1_smoke` → the MCP server
   runtime/manual matrix. Note the host it was proven on (if it is this Windows
   host, that also advances the open Windows-bench follow-up).

## Short Resume Note

If resuming later:

> The scoped pair is `nrf52833dk + nucleo_l476rg`. Everything through the
> full `R11` benchmark layer is already implemented and live-proven on that
> pair: Stage 0, the Stage 1 smoke harness, the current MCP surface,
> per-session logging, flash/recover guardrails, the mutation watcher, and the
> frozen 12-case Codex benchmark corpus. `R12` is now implemented in code as
> a native Python turnkey brain plus `pyocd-debug-brain`, and the Codex-backed
> turnkey path has now passed the full frozen 12-case suite on the scoped
> pair. `R12` is still open because the full official-pair second-provider
> closure ladder and the fresh-machine no-`NCS` portability proof are not done
> yet, even though the Claude CLI path is now live-proven on the attached
> Windows STM32 host.
Current Windows STM32 retest status on this host:

- the attached `nucleo_l476rg` is green again through Stage 0, Stage 1, and the
  full implemented STM32 `R11` case set
- `stage0_check.py` now passes again on Windows for the tracked STM32 reference
  artifact, including flash and UART `boot ok`
- `tests.harness.stage1_smoke` now passes again on Windows for
  `nucleo_l476rg`, including `stage1_known_value = 0x1234ABCD`
- the benchmark failure boundary was the runner's old blanket sub-60-second
  Codex budget, not a remaining STM32 board-control defect
- the benchmark runner now gives bug-repair cases a longer default Codex budget
  so diagnose -> patch/build -> flash/verify runs can finish cleanly
- the later Windows STM32 reproof also exposed and fixed a second real runner
  defect:
  - long Codex turnkey prompts could overflow the Windows command-line length
    limit during `nucleo_l476rg__b003_silent_uart`
  - the fix now sends Codex prompts over stdin with `codex exec -`, and the
    failing case plus the remaining STM32 ladder were rerun to green
- the Claude CLI provider is no longer blocked on this host:
  - `uv run pyocd-debug-brain run --provider claude-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."`
    passed with session root `20260623T052725Z-a07db21b`
  - `uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__k001_reference_green`
    passed with session root `20260623T052856Z-121bed12`
- the benchmark prompts remain intentionally self-contained so the nested
  benchmark agent stays on the board task instead of re-reading workflow docs
- that self-contained benchmark behavior is not the deployment rule; real
  workflow/deployment runs should still read repo workflow docs and skills
  before acting
- the currently live-proven Windows STM32 commands are:
  - `uv run python host_bootstrap.py --board-id nucleo_l476rg --install-packs`
  - `uv run pyocd-zephyr-build --app-dir firmware/nucleo_l476rg/reference/src --build-dir firmware/nucleo_l476rg/reference/build --board nucleo_l476rg`
  - `uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg`
  - `uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg`
  - `uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__k001_reference_green`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b001_wrong_boot_text`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b002_wrong_known_value`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__f001_halted_target_silent_uart`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b003_silent_uart`
  - `uv run pyocd-debug-brain benchmark --provider codex-cli --case-id nucleo_l476rg__b004_dual_signal_regression`
  - `uv run pyocd-debug-brain run --provider claude-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."`
  - `uv run pyocd-debug-brain benchmark --provider claude-cli --case-id nucleo_l476rg__k001_reference_green`
- during this Windows retest, the right boundary is no longer a flat 60-second
  wall
  - short runtime calls such as a single UART read should still fail fast if
    they stall
  - longer operations such as rebuilds, flashes, and full benchmark cases can
    legitimately run longer when they are still making progress
