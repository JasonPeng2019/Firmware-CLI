# Firmware CLI

`Firmware CLI` is a local embedded-debug and firmware-agent repo built around
`pyOCD`, Stage 0 validation tooling, and an MCP server surface in
`src/pyocd_debug_mcp/`.

This `README.md` is the canonical repo-level source for layout and naming
rules. Detailed bootstrap steps live in [init.md](./init.md). The bench/setup
scripts are operated through the single guide [stage0_setup.md](./stage0_setup.md)
(run a script with `--help` for its full flag list). The MCP server's runtime
tools are described in the tool docstrings the MCP client reads over the
protocol (`src/pyocd_debug_mcp/server.py`); there is no sidecar doc for them.
Today the Stage 0 flow is shell-first, but the intended product direction is
shared board-validation logic that is callable from `stage0_check.py`, future
MCP tools, and local programmer flows; only raw host bootstrap remains
pre-server.

The portability contract for this repo is post-bootstrap, not universal:
supported hosts plus supported boards, after a short documented developer
bootstrap equivalent to the setup needed for normal manual board debugging.
That bootstrap may still include vendor-driver or vendor-tool installation.

The scoped pair is green through the current `R11` benchmark layer:
`nrf52833dk + nucleo_l476rg` have passed the safety/runtime validation, the
shared Stage 1 smoke harness, the full MCP surface proof, and the frozen
12-case Codex benchmark corpus. `R12` is now implemented in the repo as a
turnkey product layer with one live-proven provider path, one still-open
provider proof gap, and a new additive Pass 1 operator shell over the same
brain/runtime:

- native Python brain package
- hybrid-session multi-provider decision backends
- stable headless turnkey CLI
- operator-facing `pyocd-debug` CLI
- board-aware skills tree
- sibling turnkey benchmark runner
- live MCP tool-schema prompting sourced from the local server metadata

The current live status is:

- `codex-cli` is now live-proven on the scoped pair through the full frozen
  12-case turnkey suite:
  `full_success=12`, `partial_success=0`, `fail=0`, `average_score=100.0`
- the normal turnkey path worked from `connect(board_id=...)` with no
  hard-coded probe UID or serial-port override
- for the current prototype boundary, this Codex-backed path is the required
  proven baseline
- the new `pyocd-debug` shell is now implemented on top of the same shared
  turnkey loop with:
  - structured brain events
  - live tool/progress rendering
  - evidence summaries
  - history/show/rerun flows
  - raw-provider-output visibility after completed turns
- `claude-cli` is no longer globally blocked on this host:
  - STM32 freeform and `k001` benchmark proof now exist through the local
    Claude CLI path
  - the official-pair second-provider closure bar is still open
  - the `--model sonnet` alias path that previously failed with
    `API Error: 404 ... model: claude-sonnet-4-20250514` should be treated as
    an alias-specific failure mode, not as proof that the provider path is
    unusable
- the turnkey/runtime surface is now product-owned rather than test-owned:
  - shared Stage 1 and benchmark helpers live under `src/pyocd_debug_mcp/`
  - packaged installs bundle the benchmark cases, skill manifests, and
    turnkey playbooks the runtime depends on
  - provider/runtime failures now persist inspectable turnkey run artifacts
    even when no board session is ever created
- turnkey provider continuity is now brain-owned and memory-first:
  - canonical compact local memory is persisted for every provider
  - OpenAI uses native continuation when healthy, with local fallback and
    periodic safety-sync injection
  - Anthropic, Codex CLI, and Claude CLI use the same canonical local memory
    model without pretending they have durable remote sessions
  - deterministic compaction is the default; `model-summary` compaction is
    available as an explicit option

For the current prototype branch plan, second-provider parity and true
fresh-machine Windows/macOS portability are explicit deferred risks, not the
current Wave 0 gate.

## What The Repo Currently Delivers

The repo still inherits the Phase A layout and naming decisions, but the
working baseline is now broader than Phase A alone. It includes the stable
board-control substrate, the runtime/safety layer, and the first live benchmark
proof on the scoped pair.

Today that means:

- one canonical source tree under `src/pyocd_debug_mcp/`
- tracked board definitions in `boards/`
- repo-owned test-firmware scaffolding in `firmware/`
- untracked runtime-output space in `runs/`
- test and harness scaffolding in `tests/`
- a local MCP server entrypoint plus host and Stage 0 validation scripts
- a shared Stage 1 smoke harness
- a tracked Codex benchmark corpus and benchmark runner
- a Codex-proven turnkey brain and turnkey benchmark path over the same corpus
- an implemented Pass 1 operator-facing UX shell over the same brain
- an open second-provider validation gap for Claude CLI on this host
- deferred second-provider and fresh-machine portability proof work

The official scoped board pair for the real Phase A / Phase B bench path is
`nrf52833dk` plus `nucleo_l476rg`.
The repo also carries `nrf52840dk` as a retained alternate Nordic profile for
future support work, but it is no longer the board that blocks the current
Phase A / Phase B gates.

## Canonical Tree

```text
Firmware-CLI/
|-- .python-version
|-- pyproject.toml
|-- uv.lock
|-- README.md
|-- init.md
|-- setup_host.ps1
|-- setup_host.sh
|-- host_bootstrap.py
|-- stage0_check.py
|-- stage0_setup.md
|-- packs/
|   |-- manifest.yaml
|   |-- README.md
|   `-- live_index_repair.md
|-- boards/
|   |-- nrf52833dk.yaml
|   |-- nrf52840dk.yaml
|   `-- nucleo_l476rg.yaml
|-- firmware/
|   |-- README.md
|   |-- nrf52833dk/
|   |   |-- reference/src/
|   |   |-- reference/build/
|   |   |-- recovery/
|   |   `-- bugs/
|   |-- nrf52840dk/
|   |   |-- reference/src/
|   |   |-- reference/build/
|   |   |-- recovery/
|   |   `-- bugs/
|   `-- nucleo_l476rg/
|       |-- reference/src/
|       |-- reference/build/
|       |-- recovery/
|       `-- bugs/
|-- runs/
|   `-- README.md
|-- skills/
|   |-- README.md
|   |-- common/
|   `-- mcu_families/
|-- playbooks/
|   `-- turnkey/
|-- tests/
|   |-- README.md
|   |-- fixtures/
|   |-- cases/
|   |   |-- README.md
|   |   |-- suites.yaml
|   |   `-- r11_result_schema.json
|   `-- harness/
|       |-- stage1_smoke.py
|       |-- r11_benchmark.py
|       `-- r12_turnkey_benchmark.py
|-- src/
|   `-- pyocd_debug_mcp/
|       |-- adapters/
|       |   |-- swd_interface.py
|       |   |-- swd_pyocd.py
|       |   |-- uart_interface.py
|       |   `-- uart_pyserial.py
|       |-- guardrails/
|       |   |-- flash_gate.py
|       |   `-- recover_gate.py
|       |-- brain/
|       |   |-- actions.py
|       |   |-- app.py
|       |   |-- benchmark.py
|       |   |-- cli.py
|       |   |-- config.py
|       |   |-- evidence.py
|       |   |-- events.py
|       |   |-- loop.py
|       |   |-- mcp_client.py
|       |   |-- playbooks.py
|       |   |-- provider_anthropic.py
|       |   |-- provider_claude_cli.py
|       |   |-- provider_codex_cli.py
|       |   |-- provider_factory.py
|       |   |-- provider_openai.py
|       |   |-- provider_parsing.py
|       |   |-- provider_types.py
|       |   |-- skills.py
|       |   |-- state.py
|       |   |-- tool_schemas.py
|       |   `-- workspace.py
|       |-- ux/
|       |   |-- artifacts.py
|       |   |-- cli.py
|       |   |-- commands.py
|       |   |-- history.py
|       |   |-- renderer.py
|       |   `-- shell.py
|       |-- services/
|       |   |-- convergence_watcher.py
|       |   |-- session_runtime.py
|       |   |-- symbols.py
|       |   |-- target_control.py
|       |   `-- uart_capture.py
|       |-- __init__.py
|       |-- board_config.py
|       |-- board_config_cli.py
|       |-- benchmark_support.py
|       |-- local_env.py
|       |-- pack_index_repair.py
|       |-- probe_inventory.py
|       |-- reference_artifacts.py
|       |-- reference_smoke.py
|       |-- runtime_resources.py
|       |-- serial_resolver.py
|       |-- server.py
|       |-- timeouts.py
|       |-- zephyr_build.py
|       `-- target_errors.py
|-- scratch/
|   `-- README.md
`-- markdowns/
    |-- ROADMAP.md
    |-- firmware_agent_build_plan_concrete (10).md
    |-- firmware_agent_mcp_architecture.md
    |-- current-progress.md
    |-- repo_file_index.md
    |-- curr/                 # step-scoped docs for the current/active step (graduate to tmp/ when done)
    |   |-- p0-0-doc-sync-superpowers-audit_spec.md
    |   |-- p0-0-static-audit-fix_spec.md
    |   |-- p0_0_layered_validation_plan.md
    |   |-- p0_0_validation_report.md
    |   `-- r12_turnkey_spec.md
    `-- tmp/                  # step-scoped / throwaway docs no longer needed after their step
```

## Naming Rules

- Board IDs are lowercase stable identifiers and key all per-board paths.
- Product code lives only under `src/pyocd_debug_mcp/`.
- Repo-owned reference firmware lives under `firmware/<board>/reference/`.
- The canonical symbol-bearing baseline artifact name is
  `firmware/<board>/reference/build/firmware.elf`.
- Additional flash artifacts may sit beside `firmware.elf`, but
  `firmware.elf` is the stable symbol-resolution artifact name.
- Recovery assets live under `firmware/<board>/recovery/`.
- Bug variants live under `firmware/<board>/bugs/<id>__<slug>/`.
- Runtime outputs live under `runs/<session_id>/...`.
- User firmware never lives in this repo and is always supplied later as
  runtime input.

## Environment Standard

- `.python-version` is committed and pins the team interpreter to `3.12`.
- Use `uv` as the canonical environment and command surface.
- Install `uv` first on a raw machine; this repo does not assume it already
  exists.
  Windows: `pip install uv`
  macOS: `brew install uv`
- Use `uv sync` to create `.venv/` and install the locked dependency set.
- Use `uv run ...` for repo commands so they always run inside the pinned env.
- `.env` is optional, gitignored, and auto-loaded by the MCP server and the
  Phase A host scripts when present.
- `.env` currently carries:
  - `PYOCD_PROBE_UID`
  - `PYOCD_TARGET`
  - optional `PYOCD_BOARD_ID` / `PYOCD_BOARD_CONFIG`
  - `PYOCD_TURNKEY_PROVIDER` for the turnkey brain backend:
    `openai-api`, `anthropic-api`, `codex-cli`, or `claude-cli`
  - `PYOCD_TURNKEY_MODEL` for an optional explicit model override
  - `PYOCD_TURNKEY_MEMORY_MODE` for turnkey provider-memory compaction:
    `deterministic` or `model-summary`
  - `PYOCD_TURNKEY_NATIVE_SYNC_EVERY` for native-session safety-sync cadence
  - `OPENAI_API_KEY` for the native OpenAI API provider
  - `ANTHROPIC_API_KEY` for the native Anthropic API provider
- With a board id set, the MCP server resolves that board's facts (target,
  recover policy, silicon id, baud) from `boards/<board>.yaml` through the
  shared loader, so `connect` needs no raw target and the `get_board_info`
  tool reports the loaded facts.
- `pyocd.local.yaml` is an optional per-developer pyOCD override file and is
  gitignored.
- `pyocd.yaml` is optional and only belongs in the repo once the team has a
  real shared pyOCD option to commit.
- Host and Stage 0 validation default to all non-example tracked boards.
- For first-time bring-up on one physical bench, use `--board-id <board>` to
  scope the run to the board you actually have attached.

## Board YAML Policy

Tracked board YAML is hardware-focused.

Allowed examples:

- board identity and display name
- MCU family
- probe family
- `pyocd_target`
- baudrate
- probe and serial hint terms
- recover policy such as `requires_recover_validation` and `recover_mode`
- UART expectation metadata

Forbidden examples:

- `reference_firmware_path`
- `recovery_image_path`
- project paths
- build commands
- artifact output paths
- any user- or session-scoped path

Canonical artifact locations are part of the repo tree and naming standard, not
tracked board-config fields in this Phase A layout.

## Main Workflows

Bootstrap the environment:

```bash
uv sync
```

On Windows, the preferred unattended host bootstrap entry point is:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nrf52833dk
```

On macOS, the preferred host bootstrap entry point is:

```bash
bash ./setup_host.sh --board-id nrf52833dk
```

When the machine must also rebuild the repo-owned Zephyr firmware locally, opt
into the managed Zephyr bootstrap during host setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1 -BoardId nucleo_l476rg -EnsureZephyrBuildEnv
```

```bash
bash ./setup_host.sh --board-id nucleo_l476rg --ensure-zephyr-build-env
```

Run host bootstrap for all tracked boards:

```bash
uv run python host_bootstrap.py
```

Run Stage 0 validation for all tracked boards:

```bash
uv run python stage0_check.py
```

Windows PowerShell:

```powershell
uv run python stage0_check.py
```

If Stage 0 cannot auto-resolve the UART endpoint, it prompts in an interactive
terminal. In non-interactive runs, rerun with `--port BOARD_ID=PORT`.

Run host bootstrap and Stage 0 for one board on your bench:

```bash
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk
```

Board-scoped `host_bootstrap.py --board-id ...` behavior:

- it now requires a unique matching probe for each selected board
- it now attempts board-specific serial resolution for each selected board
- on success it prints the matched probe UID/description and the matched serial
  port
- if serial matching is still ambiguous, it warns with rerun guidance using
  `--port BOARD_ID=PORT`

Run the turnkey CLI in freeform verify/diagnose mode:

```bash
uv run pyocd-debug-brain run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --provider claude-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug-brain run --board-id nrf52833dk --task "Diagnose this board interaction." --memory-mode model-summary --native-sync-every 0
```

Run the operator-facing CLI over the same turnkey brain:

```bash
uv run pyocd-debug
uv run pyocd-debug run --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
uv run pyocd-debug benchmark --case-id nrf52833dk__k001_reference_green
uv run pyocd-debug history
```

Operator-shell note:

- `pyocd-debug` uses the Rich + `prompt_toolkit` shell in a real TTY and
  falls back to plain non-live printing when stdout is not interactive
- the REPL now defaults to summary-first output; use `/raw on` to show full
  completed provider turns live
- generic freeform `run --task "fix ..."` is now diagnose-first and no
  longer pre-refuses based only on wording
- explicit `/repair` still requires `/workspace` and `/build-command`, and
  freeform repair context is constrained by workspace containment rather than a
  hardcoded `src/` root
- the REPL now supports persistent repair/artifact context and guided commands:
  - `/workspace`, `/build-command`, `/flash-artifact`, `/elf`
  - `/verify`, `/diagnose`, `/repair`
  - `/prompt`, `/diff`, `/serial`, `/score`, `/events`
  - `/memory-mode`, `/native-sync-every`

Run the turnkey benchmark against one case or the full frozen 12-case suite:

```bash
uv run pyocd-debug-brain benchmark --case-id nrf52833dk__k001_reference_green
uv run pyocd-debug-brain benchmark --suite pilot_v1_plus_b003_b004
uv run pyocd-debug-brain benchmark --provider anthropic-api --case-id nrf52833dk__k001_reference_green --model claude-sonnet-4-20250514
```

Turnkey provider rules:

- `openai-api` uses `OPENAI_API_KEY` and requires an explicit model from
  `--model` or `PYOCD_TURNKEY_MODEL`
- `anthropic-api` uses `ANTHROPIC_API_KEY` and requires an explicit model from
  `--model` or `PYOCD_TURNKEY_MODEL`
- `codex-cli` uses the locally installed `codex` CLI and inherits whatever
  Codex auth you already configured there, including a ChatGPT/Codex
  subscription or Codex's own API-key path
- `claude-cli` uses the locally installed `claude` CLI and inherits whatever
  Claude Code auth you already configured there, including a Claude
  subscription or `ANTHROPIC_API_KEY`
- provider continuity is unified across all backends:
  - the brain always persists compact local turn-fact memory
  - OpenAI uses native continuation first, then falls back to the local memory
    layer if the native handle is missing or reset
  - OpenAI can also inject local-memory safety sync on a cadence
    (`--native-sync-every`, default `4`, `0` disables)
  - Anthropic, Codex CLI, and Claude CLI always reason from the canonical
    local memory block rather than provider-owned remote sessions
- turnkey memory controls are optional:
  - `--memory-mode deterministic|model-summary`
  - `--native-sync-every N`
  - `.env`:
    `PYOCD_TURNKEY_MEMORY_MODE`, `PYOCD_TURNKEY_NATIVE_SYNC_EVERY`

Windows PowerShell:

```powershell
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nrf52833dk
```

Vendor-assisted serial auto-detect is used when the helper CLI is available:

- Nordic + J-Link boards: `nrfjprog --com`
- ST-LINK boards: `STM32_Programmer_CLI -l`

These CLIs improve auto-detect but are not required for every board. If they
are missing or a board remains ambiguous, Stage 0 falls back to prompting or
an explicit `--port` override.

Tracked board YAML now uses a typed `recover_mode` selector rather than a
free-form recover command string. Today `stage0_check.py` supports:

- `nrf_pyocd_unlock` for Nordic APPROTECT recovery through pyOCD's built-in
  unlock and mass-erase flow
- `manual_only` for boards that need recover validation but do not yet have an
  automated Stage 0 implementation

Start the MCP server:

```bash
uv run pyocd-debug-mcp
```

## Zephyr Rebuilds

Repo-owned firmware rebuilds now go through one cross-platform entrypoint:

```bash
uv run pyocd-zephyr-build --ensure-only
```

What it does:

- reuses an existing Zephyr workspace when `ZEPHYR_WORKSPACE_DIR`,
  `ZEPHYR_BASE`, `~/zephyrproject`, or a detected NCS workspace is already
  present
- otherwise bootstraps a managed upstream Zephyr workspace under the local
  cache and pins it to `zephyrproject-rtos/zephyr` tag `v4.3.0`
- reuses `ZEPHYR_SDK_INSTALL_DIR` or an existing SDK when one is already on the
  machine
- otherwise detects common global NCS toolchain installs and, if none are
  usable, downloads and installs the Zephyr SDK toolchain component it needs
  into the local cache with the repo helper's own managed archive/setup path
  rather than requiring a preinstalled `west sdk install` extractor workflow

Direct board builds are then:

```bash
uv run pyocd-zephyr-build --app-dir firmware/nucleo_l476rg/reference/src --build-dir firmware/nucleo_l476rg/reference/build --board nucleo_l476rg
uv run pyocd-zephyr-build --app-dir firmware/nrf52833dk/reference/src --build-dir firmware/nrf52833dk/reference/build --board nrf52833dk/nrf52833
uv run pyocd-zephyr-build --app-dir firmware/nrf52840dk/reference/src --build-dir firmware/nrf52840dk/reference/build --board nrf52840dk/nrf52840
```

The helper preserves the live Zephyr build tree and defaults to incremental
`west build -p auto` behavior so repeated agent rebuilds stay fast. Pass
`--pristine always` when a full clean reconfigure is actually required.

For `R11` benchmark cases, the nested Codex prompt is intentionally
self-contained so the benchmark agent spends its time on the board task rather
than re-reading repo workflow docs. That benchmark-only rule does not change
the real product path: non-benchmark deployment runs should still load the repo
workflow docs and skills before they edit, rebuild, flash, or diagnose.

The per-board `build_reference.sh` / `build_bug.sh` wrappers now delegate to
that same helper. `NCS` is optional: if it is already installed, the helper
reuses it; if not, the helper can provision a managed upstream-Zephyr build
path itself.

Current limitation:

- managed Zephyr SDK install is not supported on macOS `x86_64` by current
  Zephyr releases, so Intel Macs must point `ZEPHYR_SDK_INSTALL_DIR` at a
  preinstalled older supported SDK or use another supported host

## Docs

- Setup and bootstrap: [init.md](./init.md)
- Bench bring-up operator guide (setup_host, host_bootstrap, stage0_check): [stage0_setup.md](./stage0_setup.md)
- MCP server runtime tools: documented in the tool docstrings in `src/pyocd_debug_mcp/server.py` (read by the MCP client over the protocol)
- Official Nordic runbook: [firmware/nrf52833dk/README.md](./firmware/nrf52833dk/README.md)
- Official STM32 runbook: [firmware/nucleo_l476rg/README.md](./firmware/nucleo_l476rg/README.md)
- Roadmap: [markdowns/ROADMAP.md](./markdowns/ROADMAP.md)
- Current progress ledger: [markdowns/current-progress.md](./markdowns/current-progress.md)
- `R12` turnkey contract: [markdowns/curr/r12_turnkey_spec.md](./markdowns/curr/r12_turnkey_spec.md)
- `P0.0` layered validation plan: [markdowns/curr/p0_0_layered_validation_plan.md](./markdowns/curr/p0_0_layered_validation_plan.md)
- `P0.0` validation report: [markdowns/curr/p0_0_validation_report.md](./markdowns/curr/p0_0_validation_report.md)
- `P0.0` doc-sync and superpowers audit spec: [markdowns/curr/p0-0-doc-sync-superpowers-audit_spec.md](./markdowns/curr/p0-0-doc-sync-superpowers-audit_spec.md)
- `P0.0` static audit fix spec: [markdowns/curr/p0-0-static-audit-fix_spec.md](./markdowns/curr/p0-0-static-audit-fix_spec.md)
- Archived Wave 0 reconcile spec: [markdowns/tmp/p0-wave0-main-reconcile_spec.md](./markdowns/tmp/p0-wave0-main-reconcile_spec.md)
- Concrete build plan: [markdowns/firmware_agent_build_plan_concrete (10).md](./markdowns/firmware_agent_build_plan_concrete%20%2810%29.md)
- Architecture notes: [markdowns/firmware_agent_mcp_architecture.md](./markdowns/firmware_agent_mcp_architecture.md)

Until later roadmap items intentionally revise it, this `README.md` is the
canonical repo-layout and naming reference for Phase A.

## Verification Status

Verified:

- non-hardware verification: this document's tree, command surface, and doc
  links match the current root-level scripts and docs
- latest clean-slate rerun on the macOS mixed-board host re-proved:
  - both scoped-board probes visible together
  - strict `host_bootstrap.py --board-id ...` success for both scoped boards,
    including matched probe UID + matched serial-port reporting
  - STM32 Stage 0 + Stage 1 smoke
  - Nordic Stage 0 + recover + Stage 1 smoke
- hardware-backed STM32 proof on this Mac host: `nucleo_l476rg` now passes
  Stage 0 connect, flash, and UART through the shared target-control services
- the STM32 bench truth is fully closed in repo status, including the confirmed
  shared USB correlation between the visible ST-Link probe and
  `/dev/cu.usbmodem144403`
- the canonical Windows `R0` bootstrap path has been verified on a real Windows
  host
- the STM32 Windows Stage 0 path is now also bench-proven on a real Windows
  host: `host_bootstrap.py --board-id nucleo_l476rg --install-packs` and
  `stage0_check.py --board-id nucleo_l476rg --reference-firmware ...` both pass,
  with `COM9` + ST-Link visibility confirmed through the shared path
- the Windows MCP stdio `connect(board_id="nucleo_l476rg")` regression is also
  closed on real hardware: shared probe discovery now uses the pyOCD Python API
  first instead of paying the subprocess `pyocd list` penalty inside the live
  server process
- the scoped Nordic board is now `nrf52833dk`, and its Stage 0 path is bench
  proven on this Mac host for probe visibility, exact silicon identity, flash,
  UART `boot ok`, recover, and shared USB confirmation
- the repo now carries full baseline packages for the scoped board pair under
  `firmware/nrf52833dk/` and `firmware/nucleo_l476rg/`
- the tracked Stage 1 proof surface is now `tests/harness/stage1_smoke.py`; the
  old scratch API harness is retired
- the tracked Stage 1 smoke harness now passes on both scoped boards:
  `nucleo_l476rg` and `nrf52833dk`
- the full current MCP tool surface is now live-validated on both scoped
  boards through `server.py`: `connect`, `disconnect`, `get_board_info`,
  `get_state`, `halt`, `resume`, `step`, `reset`, `read_core_register`,
  `write_core_register`, `read_memory`, `read_memory_block`, `write_memory`,
  `set_breakpoint`, `remove_breakpoint`, `flash_firmware`, `read_serial`, and
  `unlock_recover`
- `connect(...)` now creates a visible `session_id`, and the runtime session
  writes `runs/<session_id>/logs/events.jsonl` plus
  `runs/<session_id>/run-metadata/session.json`
- flash guardrails are live-proven on the scoped pair:
  default tracked baseline flash, explicit valid `.elf`, and explicit valid
  `.hex` all succeed; missing-path and invalid-suffix inputs refuse
  deterministically
- recover guardrails are live-proven on the scoped pair:
  Nordic recover succeeds with `confirm=true`, while STM32 recover refuses
  deterministically because no supported recover mode is tracked
- mutation watchers are live-proven on the scoped pair:
  repeated flash failures block only `flash_firmware`, repeated UART misses
  block only `read_serial`, repeated recover failures block only
  `unlock_recover`, and disconnect/reconnect clears block state
- the current scoped milestones are now green through product #1:
  `G1` (`R2` + `R3`), `G3` (`R6` + `R7` + `R8`), `G4` (`R9`), `G5`
  (`R10`), and `G6` (`R11`)
- the tracked Codex benchmark pilot is now live-proven on the scoped pair:
  the frozen `pilot_v1` suite passed 8/8 cases with `full_success=8`,
  `partial_success=0`, `fail=0`, and `average_score=100.0`
- the final minimal `R11` hardening expansion is also live-proven:
  `b003_silent_uart` and `b004_dual_signal_regression` both reached
  `FULL_SUCCESS` on `nucleo_l476rg` and `nrf52833dk`
- benchmark session accounting is now hardened for real Codex behavior:
  the final structured `session_id` is the canonical case root, and extra
  MCP sessions are recorded as runner warnings rather than automatic failures
- benchmark scoring now treats the runner-owned final verification as
  authoritative, and the `b004` bug fixtures preserve the stable Stage 1
  symbol-access pattern so Nordic runs cannot “look green” while violating the
  symbol contract
- the first `R12` code path now exists in the repo:
  `src/pyocd_debug_mcp/brain/`, `skills/`, `pyocd-debug-brain`, and
  `tests/harness/r12_turnkey_benchmark.py`
- the current Branch A provider/prompt layer is also in place:
  - provider capabilities and loop-owned provider session state are explicit
  - all providers share one canonical compact local-memory model
  - OpenAI uses native continuation as an accelerator, with local fallback and
    optional periodic safety sync
  - Anthropic, Codex CLI, and Claude CLI use the same canonical compact
    memory model without fake durable remote sessions
  - model-facing server-tool docs now come from live MCP metadata through
    `brain/tool_schemas.py`
- the first Pass 1 UX-layer code path now also exists in the repo:
  `src/pyocd_debug_mcp/ux/`, `src/pyocd_debug_mcp/brain/events.py`, and
  `pyocd-debug`
- the turnkey layer no longer depends on Codex CLI or MCP registration:
  it launches the local MCP server as a subprocess and talks to it directly
- the turnkey benchmark path reuses the frozen `pilot_v1_plus_b003_b004`
  corpus and the existing case manifests instead of inventing a second
  benchmark taxonomy

Latest turnkey verification:

- benchmark bug-repair cases now allow a longer default `codex exec` budget so
  diagnose -> patch/build -> flash/verify runs are not cut off by a blanket
  sub-60-second cap while they are still making progress
- the retained alternate Nordic profile `nrf52840dk` is now live-proven on
  this Windows host for Zephyr rebuild, Stage 0, Stage 1, and a full six-case
  alternate `R11` suite (`k001`, `b001`, `b002`, `f001`, `b003`, `b004`)

- `R12` is now live-proven through the full frozen 12-case corpus with the
  `codex-cli` provider on `nrf52833dk + nucleo_l476rg`:
  - freeform healthy verification passed on both boards
  - the full `pilot_v1_plus_b003_b004` turnkey suite passed:
    `full_success=12`, `partial_success=0`, `fail=0`, `average_score=100.0`
  - the normal path used `connect(board_id=...)` without hard-coded UID or
    serial-port tuning
  - no forbidden recover usage occurred on non-recover cases
  - no case watcher-blocked due to turnkey thrash
- deferred prototype risk that is not yet re-proved:
  - full official-pair second-provider closure
  - true fresh-machine Windows/macOS portability proof
- current official-pair second-provider gap:
  - the STM32 Claude CLI path is proven on this host, but the official-pair
    freeform + suite closure bar is still open
  - the `--model sonnet` alias path that previously failed with
    `API Error: 404 ... model: claude-sonnet-4-20250514` remains a known
    alias-specific failure mode and should not be treated as the provider's
    current global status
- the Pass 1 `pyocd-debug` shell is implemented and green under the local
  non-hardware test/lint/typecheck ladder, but true provider-token streaming is
  still intentionally deferred to the next UX follow-up
- the broader self-contained no-`NCS` portability claim still needs true fresh
  Windows and macOS host validation
    that pass
