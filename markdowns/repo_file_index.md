# Repo File Index

A file-by-file map of the repository: what each file is and what it does.
Produced as Phase 0a of `audit_and_validation_plan.md`. Generated/cache dirs
(`.venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`) are
omitted.

Status convention: descriptions below were verified against the file contents
unless marked `(by name)`, which means inferred from the filename/role and worth
a glance before relying on detail.

## Root

| Path | What it is / does |
|---|---|
| `pyproject.toml` | Package metadata + dependencies; declares the console scripts `pyocd-debug-mcp`, `pyocd-debug-brain`, `pyocd-debug`, and `pyocd-pack-repair`. |
| `uv.lock` | Locked dependency set for reproducible `uv sync`. |
| `.python-version` | Pins the team interpreter to Python 3.12. |
| `.env.example` | Template for the gitignored `.env` (probe UID, target, optional board id/config, turnkey BYOK settings). |
| `.gitignore` | Ignore rules (`.venv/`, `runs/` output, caches, local overrides). |
| `README.md` | Canonical repo-layout + naming reference, environment standard, main workflows, verification status, and the new Pass 1 operator-facing `pyocd-debug` shell. |
| `init.md` | Setup/bootstrap walkthrough referenced by the README. `(by name — verify scope)` |
| `stage0_setup.md` | Single operator guide for the bench bring-up scripts (`setup_host`, `host_bootstrap`, `stage0_check`). |
| `setup_host.ps1` | Windows unattended host-bootstrap entry point. `(by name)` |
| `setup_host.sh` | macOS host-bootstrap entry point. `(by name)` |
| `host_bootstrap.py` | Host-level readiness checks (pyOCD runs, probes/serial enumerate, board configs load, packs present/installable). In `--board-id` mode it now also requires a uniquely matched probe and board-specific serial result for each selected board before it reports Stage 0 readiness. Does not flash or install OS drivers. |
| `stage0_check.py` | Stage 0 board/toolchain validation CLI; data-driven from board configs; now a thin frontend over the shared services. |

## `skills/`

| Path | What it is / does |
|---|---|
| `skills/README.md` | Explains the R12 turnkey-skill tree and required manifest fields. |
| `skills/common/*.yaml` | Board-agnostic YAML skills for the current benchmark/task surface (baseline verification, UART/symbol triage, observability-vs-code distinction, dual-signal regression). |
| `skills/mcu_families/nrf52833/*.yaml` | Nordic-family YAML skills, currently focused on recover-policy reasoning. |
| `skills/mcu_families/stm32l476/*.yaml` | STM32-family YAML skills, currently focused on the no-recover expectation. |

## `src/pyocd_debug_mcp/` — product code

| Path | What it is / does |
|---|---|
| `__init__.py` | Package marker. |
| `server.py` | FastMCP stdio server. Every tool thin-wraps `services/` + `guardrails/`; owns session lifecycle, refusal/block formatting, and the tool surface (connect/disconnect, state/halt/resume/step/reset, register+memory r/w, breakpoints, `flash_firmware`, `read_serial`, `unlock_recover`, `get_board_info`). |
| `board_config.py` | Board YAML/JSON schema (`BoardConfig`), loader, validation, recover-mode vocabulary; the single board-facts source for all frontends. |
| `board_config_cli.py` | Small CLI to resolve/inspect tracked board configs through the shared loader. |
| `local_env.py` | Auto-loads `.env` when present. |
| `pack_index_repair.py` | Repairs a partial cmsis-pack-manager live descriptor index by controlled PDSC fetch + local `index.json` rebuild. |
| `serial_resolver.py` | Serial/VCP discovery, vendor-assisted detection, and `--port`/override resolution with interactive/non-interactive fallback. |
| `probe_inventory.py` | Parses `pyocd list --probes`, models `ProbeInfo`, and does board-aware probe selection (preserves real UIDs for J-Link and ST-Link). |
| `reference_artifacts.py` | Resolves the canonical per-board reference `.elf`/`.hex` pair from the repo `firmware/<board>/reference/build/` layout. |
| `reference_smoke.py` | Product-owned shared Stage 1 smoke verifier used by the harness wrapper and turnkey benchmark final verification. |
| `runtime_resources.py` | Resolves runtime data roots from a live repo checkout when present, else from packaged bundled data inside the installed wheel. |
| `benchmark_support.py` | Product-owned shared benchmark contracts/helpers: case loading, workspace prep, session reconciliation, scoring, and benchmark artifact writing. |
| `pack_provision.py` | Pinned, deterministic CMSIS-Pack provisioning: `ensure_all` (fetch+sha256-verify from `packs/manifest.yaml`) and `discover_local_packs` (network-free runtime lookup for pyOCD's `pack` option). Replaces dependence on the live `pyocd pack` index. |
| `target_errors.py` | Typed error taxonomy: `TargetControlError` base + `ProbeNotFound`, `TargetConnection`, `LockedTarget`, `UnsupportedArtifact`, `SymbolLookup`, `ReferenceArtifact`. |
| `timeouts.py` | Shared timeout constants plus turnkey timeout config/update models used by the runtime and the P0 prototype substrate. |

### `brain/` — R12 turnkey product layer

| Path | What it is / does |
|---|---|
| `brain/actions.py` | Structured brain action/result schema (curated server-tool actions, local workspace actions, finalize result). |
| `brain/decision_types.py` | Shared future-facing prototype decision/planning shapes: timeout proposals, iteration estimates, early-exit verdicts, future board-decision envelopes, and batch/action-call containers. |
| `brain/app.py` | Shared run/benchmark invocation helpers reused by both the headless brain CLI and the operator-facing UX CLI. |
| `brain/benchmark.py` | Core R12 benchmark runner over the native turnkey brain; reuses the frozen R11 case corpus and scoring contract. |
| `brain/cli.py` | `pyocd-debug-brain` entrypoint; exposes `run` and `benchmark` modes. |
| `brain/client_actions.py` | Minimal session-scoped client-action record/store contract landed in P0; execution is still future work. |
| `brain/config.py` | Turnkey provider config loading (`openai-api`, `anthropic-api`, `codex-cli`, `claude-cli`) plus the `TurnkeyInvocation` model. |
| `brain/evidence.py` | Typed observation/hypothesis/experiment/strategy-evaluation records persisted into turnkey state artifacts. |
| `brain/events.py` | Structured event model + sink contract for live UX rendering and persisted `brain_events.jsonl` artifacts. |
| `brain/loop.py` | Deterministic outer loop for the turnkey brain: prompt-bundle assembly, provider-session threading, action execution, convergence, and run-artifact capture. |
| `brain/mcp_client.py` | Local stdio MCP client wrapper that launches `uv run pyocd-debug-mcp` and exposes typed tool descriptors plus parsed tool-call helpers. |
| `brain/playbooks.py` | Loader for the internal deterministic turnkey helper playbooks stored under `playbooks/turnkey/`, resolved from repo roots in checkout mode or from bundled package data in wheel installs. |
| `brain/cli_parsing.py` | Shared turnkey CLI parsing helpers for JSON planning-hook flags such as timeout overrides, timeout proposals, and iteration estimates. |
| `brain/provider_anthropic.py` | Anthropic Messages API wrapper for per-turn structured next-action generation using the canonical local-memory session model plus optional summarizer calls for `model-summary` compaction. |
| `brain/provider_claude_cli.py` | Claude Code CLI wrapper for per-turn structured next-action generation through `claude --print`, using the same canonical local-memory session model as the other backends. |
| `brain/provider_codex_cli.py` | Codex CLI wrapper for per-turn structured next-action generation through `codex exec`, using the same canonical local-memory session model as the other backends while keeping transport invocation ephemeral. |
| `brain/provider_factory.py` | Factory that maps provider config to the correct decision backend. |
| `brain/provider_openai.py` | OpenAI Responses API wrapper for per-turn structured next-action generation with native continuation as the primary path, local-memory fallback, periodic safety sync, and optional summarizer calls for `model-summary` compaction. |
| `brain/provider_parsing.py` | Shared parsing helpers for extracting `TurnDecision` JSON from provider output text. |
| `brain/provider_types.py` | Shared hybrid provider/session contracts: provider capabilities, native-handle metadata, compact memory entries, compaction helpers, explicit prompt render modes, `ProviderTurn`, coarse provider progress updates, and `DecisionProvider`. |
| `brain/skills.py` | YAML skill-manifest loader, applicability matching, and deterministic prompt rendering; resolves skills from the live repo when present or from bundled package data when installed. |
| `brain/state.py` | In-memory brain run state (session ids, counters, verification state, blocked/refused families, observations). |
| `brain/tool_schemas.py` | Loads live MCP tool metadata, filters it to the curated allowed tool surface, and renders the stable tool-schema prompt bundle plus curated response/refusal semantics used by the brain. |
| `brain/workspace.py` | Safe local workspace read/replace/build helpers plus diff capture. |

## `playbooks/turnkey/`

| Path | What it is / does |
|---|---|
| `playbooks/turnkey/*.yaml` | Internal deterministic helper playbooks used by the turnkey brain for reference health, diagnosis, repair, and Nordic recover-cycle guidance. |

### `ux/` — operator-facing turnkey shell

| Path | What it is / does |
|---|---|
| `ux/cli.py` | `pyocd-debug` entrypoint; launches the REPL shell with no args and also exposes pretty `run`, `benchmark`, `history`, `show`, and `rerun` subcommands. |
| `ux/shell.py` | Interactive Rich + `prompt_toolkit` shell controller and slash-command dispatch. |
| `ux/renderer.py` | Rich renderer for live provider/tool activity, evidence summaries, raw-output display, and benchmark/history summaries. |
| `ux/history.py` | Saved-run discovery and `turnkey_request`/`turnkey_result` loading from `runs/<session_id>/...`, with best-effort listing that skips malformed runs and returns warnings. |
| `ux/artifacts.py` | Artifact discovery and safe text/JSON preview helpers for saved runs. |
| `ux/commands.py` | Slash-command parsing and help text for the interactive shell. |

### `adapters/` — backend-neutral transport contracts + backends

| Path | What it is / does |
|---|---|
| `swd_interface.py` | Abstract `SWDInterface` contract + `TargetSessionHandle` (session + board facts + route used). |
| `swd_pyocd.py` | pyOCD-backed SWD implementation: connect/flash (`FileProgrammer`)/erase (`FlashEraser`)/read/halt; maps backend errors to typed errors; J-Link `non_interactive` routing. |
| `uart_interface.py` | Abstract `UARTInterface` contract + `UARTPortHandle`. |
| `uart_pyserial.py` | pyserial-backed UART implementation. |
| `__init__.py` | Package marker. |

### `services/` — shared board-control operations (used by server + Stage 0 + harnesses)

| Path | What it is / does |
|---|---|
| `target_control.py` | The shared SWD operation surface over the pyOCD backend (open/close session, state, read/write memory+registers, flash, recover, halt/resume/step/reset). |
| `uart_capture.py` | Bounded UART capture/wait/reopen service returning a deterministic `UARTCaptureResult` (text, match, reopen count, duration). |
| `symbols.py` | ELF symbol resolution (`ResolvedSymbol`) via pyOCD's ELF reader; optional u32 value read. |
| `session_runtime.py` | Runtime session model: `session_id` generation, append-only JSONL event log, run metadata, `ToolOutcome`, `PolicyRefusal`, `WatcherBlocked`, `ActionContext`. |
| `convergence_watcher.py` | Deterministic mutation-thrash watcher: blocks repeated identical flash/UART/recover failures per session; cleared on disconnect. |
| `__init__.py` | Package marker. |

### `guardrails/` — deterministic safety policy

| Path | What it is / does |
|---|---|
| `flash_gate.py` | Pre-flash policy: resolves the artifact, computes identity (size/sha256/source), allows only local `.elf`/`.hex`, refuses missing/unsupported/URL-like inputs. |
| `recover_gate.py` | Recover authorization: requires active session + loaded board config + explicit `confirm`; refuses boards with no supported recover mode. |
| `__init__.py` | Package marker. |

## `tests/`

| Path | What it is / does |
|---|---|
| `harness/stage1_smoke.py` | Thin CLI wrapper over `src/pyocd_debug_mcp/reference_smoke.py`. |
| `harness/r11_benchmark.py` | Thin CLI wrapper over `src/pyocd_debug_mcp/benchmark_support.py`. |
| `harness/r12_turnkey_benchmark.py` | Thin CLI wrapper for the R12 turnkey benchmark path. |
| `test_board_configs.py` | Board-config loader/schema tests. `(by name)` |
| `test_serial_resolver.py` | Serial resolution tests. `(by name)` |
| `test_probe_inventory.py` | Probe parsing/selection tests. `(by name)` |
| `test_reference_artifacts.py` | Reference-artifact resolution tests. `(by name)` |
| `test_symbols.py` | Symbol-resolution tests. `(by name)` |
| `test_target_control.py` | Shared target-control service tests. `(by name)` |
| `test_uart_capture.py` | UART capture service tests. `(by name)` |
| `test_r10_runtime.py` | R10 runtime/safety (session, gates, watcher) tests. `(by name)` |
| `test_pack_index_repair.py` | Live-index repair tests (master-index parse, filtering, missing-plan logic; no network). |
| `test_pack_provision.py` | Pinned-pack provisioning tests (sha256 verify, discover, manifest parse; no network). |
| `test_r11_benchmark.py` | Benchmark runner/schema/scoring tests. `(by name)` |
| `test_stage0_shared_errors.py` | Stage 0 shared-error behavior tests. `(by name)` |
| `test_server_board_config.py` | Server board-config resolution tests. `(by name)` |
| `test_server_import.py` | Server import/smoke test. `(by name)` |
| `test_server_runtime_tools.py` | Server runtime tool-surface tests. `(by name)` |
| `cases/<case_id>/case.yaml` + `prompt.md` | R11/R12 benchmark cases: known-good `k001`, injected-bug `b001/b002/b003/b004`, and observability-fault `f001`, mirrored across the scoped pair. |
| `cases/r11_result_schema.json` | JSON schema for Codex benchmark results. |
| `cases/suites.yaml` | Benchmark suite ordering (`pilot_v1`, `pilot_v1_plus_b003_b004`, retained alternate-board suites). |
| `cases/README.md`, `tests/README.md` | Case-format and test-layout docs. |
| `fixtures/`, `cases/`, `harness/` `.gitkeep` | Tracked empty-dir placeholders. |

## `boards/`

| Path | What it is / does |
|---|---|
| `nrf52833dk.yaml` | Scoped Nordic board config (target, recover policy, silicon id, baud, hints). |
| `nucleo_l476rg.yaml` | Scoped STM32 board config. |
| `nrf52840dk.yaml` | Retained alternate Nordic profile (not the current scoped blocker). |
| `example_custom_board.yaml`, `example_custom_nrf52_board.yaml` | Templates for adding a custom board (ignored by default board selection). |

## `packs/`

| Path | What it is / does |
|---|---|
| `manifest.yaml` | Tracked pin list (id/version/url/sha256) for deterministic CMSIS-Pack provisioning. |
| `README.md` | Why pinned-fetch instead of the live index; how to add/update a pin or fetch manually. |
| `live_index_repair.md` | Diagnosis + verified repair flow for partial live pyOCD/CMSIS pack indexes. |
| `*.pack` | Downloaded DFP binaries (gitignored); provisioned by `host_bootstrap.py --install-packs`, loaded at runtime via `discover_local_packs`. |

## `firmware/<board>/`

| Path | What it is / does |
|---|---|
| `reference/src/` | Reference firmware source tree (Zephyr sample: `main.c`, `CMakeLists.txt`, `prj.conf`). |
| `reference/build_reference.sh` | Build script producing the canonical artifacts (present for `nrf52833dk`, `nucleo_l476rg`). |
| `reference/build/firmware.{elf,hex}` | Canonical baseline artifacts (present for the scoped pair; `nrf52840dk` has only `.gitkeep`). |
| `recovery/` | Known-good recovery images the safety gates expect (placeholder today). |
| `bugs/<id>__<slug>/` | Injected-bug variants for the benchmark corpus. |
| `firmware/README.md`, per-board `README.md` | Firmware policy + per-board runbook (Nordic runbook is the official one). |

## `markdowns/`

| Path | What it is / does |
|---|---|
| `README` order | Read order is `README.md` → `ROADMAP.md` → `current-progress.md`. |
| `ROADMAP.md` | Full project plan (R0-R15), dependency tree, gates, rolling-frontier staffing, and the current active R12 frontier. *Design/plan doc - see status banner.* |
| `R12_P_SPLIT.md` | Conflict-safe R12 prototype wave/branch split: Wave 0 clean slate, serial P0, parallel Branches A/B/C, parallel Branches D/E/F, merge-back rules, and serial final integration. |
| `curr/things-to-change.md` | Active product/design backlog for the R12 capability prototype; ordered from earliest prototype work to later MVP/nice-to-have items. |
| `UXLayer.md` | UX-layer design/implementation note for the additive `pyocd-debug` operator shell; Pass 1 is implemented, with richer streaming/checkpoint work still deferred. |
| `firmware_agent_build_plan_concrete (10).md` | Step-ordered concrete build plan with design decisions and the current R12 closure boundary. *Design/plan doc - see status banner.* |
| `firmware_agent_mcp_architecture.md` | MCP-centered architecture (one server, two clients; tools/resources; guardrails) plus the current turnkey prototype control model. *Design doc - see status banner.* |
| `current-progress.md` | Live repo status, current proof boundary, exact rerun ladder, expected outputs, and the remaining open work. |
| `repo_file_index.md` | This file. |

### `markdowns/curr/` - step-scoped docs for the current/active step (graduate to `tmp/` when done)

| Path | What it is / does |
|---|---|
| `p0_foundation_spec.md`, `p0_foundation_process.md` | The active serial P0 foundation contract and process ledger for the R12 prototype. |
| `r12_turnkey_spec.md` | The broader R12 prototype contract that P0 is preparing the codebase to support. |
| `things-to-change.md` | Active R12 prototype backlog and priority ordering. |

### `markdowns/tmp/` — step-scoped / throwaway docs (no longer needed after their step)

| Path | What it is / does |
|---|---|
| `audit_and_validation_plan.md` | The audit + nRF52840 validation + Mac re-proof execution plan (Phase 0 complete). |
| `build_plan_spec_gaps.md` | Pre-implementation gap analysis; mostly resolved. |
| `mcp_tools.md` | Forward-looking reference on per-user dynamic tool listing over HTTP/OAuth (future hosted tier; not current architecture). |
| `R12JasonBenMerge.md` | Historical merge rationale for the Ben/Jason R12 branch reconciliation; superseded by the current roadmap/spec where prototype scope differs. |
| `r10_contract.md`, `r11_benchmark_spec.md` | Older slice contracts retained for historical traceability, not current-step authority. |
| `r12-ben-mainline-merge_process.md`, `r12_ben_mainline_merge_spec.md` | Completed Ben mainline merge process/spec docs. |
| `r12-nucleo-reproof_spec.md`, `r12-windows-cmdline-bug_spec.md` | Completed focused R12 follow-up specs. |
| `runtime-timeout-audit_spec.md` | Historical timeout-hardening audit/spec. |
| `stm32-build-r11-turnkey_process.md`, `stm32-build-r11-turnkey_spec.md`, `stm32-r11-windows-retest_spec.md` | Older STM32-centric benchmark/process docs. |
| `threadx_nucleo_l476rg_button_blink_spec.md` | Retained exploratory STM32-only scaffold spec. |
| `uxlayer_gap_checklist.md` | Historical UX gap audit after the first shipped shell pass. |

## `superpowers/` — internal authoring playbooks

| Path | What it is / does |
|---|---|
| `agent_index_START_HERE.md` | Entry point / index for the playbooks. |
| `agent_coding_playbook.md` | Coding conventions (no-hardcoding, etc.). `(by name)` |
| `agent_consistency_playbook.md` | Cross-file consistency guidance. `(by name)` |
| `agent_doc_sync_playbook.md` | Doc-vs-code sync discipline (used as the Phase 0b standard). |
| `agent_portability_playbook.md` | Cross-platform / vendor-install portability rules. `(by name)` |
| `agent_script_doc_playbook.md` | Script/doc authoring rules. `(by name)` |

## `runs/` and `scratch/`

| Path | What it is / does |
|---|---|
| `runs/README.md` | Explains the per-session runtime-output tree (`runs/<session_id>/...`); contents are gitignored. |
| `scratch/README.md` | Throwaway-experiments policy; the old Step 1.0d API harness was retired here once `tests/harness/stage1_smoke.py` replaced it. |
