# Audit + nRF52840 Validation + Mac Re-Proof — Execution Plan

This plan covers three workstreams requested as items 0, 1, and 2. They are
listed in dependency order, not necessarily execution order (Phase 0 can run in
parallel with hardware work — see "Sequencing" at the end).

- **Phase 0 — Repo inventory + documentation reconciliation.** Produce a
  file-by-file index of the repo, then bring every stale planning doc into
  agreement with the code as it actually exists today (R0–R10 done, R11 active).
- **Phase 1 — Full nRF52840 service-layer validation.** Prove the *entire*
  service layer — including firmware flashing — on `nrf52840dk`, not just the
  connect/read subset proven earlier.
- **Phase 2 — Full Mac hardware re-proof.** Re-run the complete hardware proof
  matrix on the Mac bench from a known-good baseline and capture the artifacts.

> Authoring note: this plan is the design/sequence. It deliberately does not do
> the work. Each phase has explicit deliverables and exit criteria so completion
> is unambiguous.

---

## Phase 0 — Repo inventory + documentation reconciliation

### 0a. Produce a repo file index

**Deliverable:** a new `markdowns/repo_file_index.md` with one line per file/dir
explaining what it is and what it does. Use the first-pass table below as the
starting point — **verify each row against the actual file** before trusting it;
rows for files not yet opened in detail are marked `(verify)`.

#### Root

| Path | What it is |
|---|---|
| `pyproject.toml` | Package metadata, deps, console-script entry `pyocd-debug-mcp = pyocd_debug_mcp.server:main` |
| `uv.lock`, `.python-version` | Pinned env (uv, Python 3.12) |
| `.env.example`, `.gitignore` | Local-override template; ignore rules |
| `README.md` | Repo overview, layout, commands |
| `init.md`, `stage0_setup.md` | Operator setup/bring-up guides `(verify scope)` |
| `setup_host.ps1`, `setup_host.sh` | Per-OS host bootstrap scripts `(verify)` |
| `host_bootstrap.py` | Host preflight (env/probe reachability) `(verify)` |
| `stage0_check.py` | Stage 0 board/toolchain validation CLI (now a thin wrapper over shared services) |

#### `src/pyocd_debug_mcp/`

| Path | What it is |
|---|---|
| `server.py` | FastMCP stdio server; all tools thin-wrap `services/` + `guardrails/` |
| `board_config.py` | Board YAML schema + loader (shared by all frontends) |
| `board_config_cli.py` | CLI surface for board-config inspection `(verify)` |
| `local_env.py` | `.env` auto-loader |
| `serial_resolver.py` | Serial/VCP discovery + override resolution |
| `probe_inventory.py` | Probe enumeration via `pyocd list --probes`; board-aware selection `(verify)` |
| `reference_artifacts.py` | Resolves per-board reference `.elf`/`.hex` from repo layout `(verify)` |
| `target_errors.py` | Typed error taxonomy (refusals, locked target, etc.) `(verify)` |
| `adapters/swd_interface.py` | Abstract SWD interface + `TargetSessionHandle` |
| `adapters/swd_pyocd.py` | pyOCD backend (incl. J-Link `non_interactive` routing) |
| `adapters/uart_interface.py` | Abstract UART interface `(verify)` |
| `adapters/uart_pyserial.py` | pyserial backend `(verify)` |
| `services/target_control.py` | Shared SWD operations (connect/flash/halt/read/recover/…) |
| `services/uart_capture.py` | Bounded UART capture/wait/reopen service |
| `services/symbols.py` | ELF symbol resolution |
| `services/session_runtime.py` | Per-session id, JSONL event log, run metadata |
| `services/convergence_watcher.py` | Deterministic mutation-thrash watcher |
| `guardrails/flash_gate.py` | Pre-flash validation (local `.elf`/`.hex` only) |
| `guardrails/recover_gate.py` | Gated/confirmed recover authorization |

#### `tests/`

| Path | What it is |
|---|---|
| `harness/stage1_smoke.py` | Stage 1 end-to-end smoke harness (both boards) |
| `harness/r11_benchmark.py` | R11 Codex benchmark runner |
| `test_*.py` | Unit/contract coverage (target_control, uart_capture, symbols, probe_inventory, reference_artifacts, r10_runtime, r11_benchmark, server_*) |
| `cases/<case_id>/` | R11 benchmark cases (`case.yaml` + `prompt.md`) |
| `cases/r11_result_schema.json`, `cases/suites.yaml` | Result schema; pilot suite ordering |

#### Other dirs

| Path | What it is |
|---|---|
| `boards/*.yaml` | Tracked board configs (`nrf52833dk`, `nrf52840dk`, `nucleo_l476rg`, examples) |
| `firmware/<board>/reference/` | Reference firmware source + built `.elf`/`.hex` |
| `firmware/<board>/{recovery,bugs}/` | Recovery images; injected-bug variants |
| `runs/<session_id>/` | Per-session runtime output (logs, metadata) |
| `superpowers/*.md` | Internal authoring playbooks (coding, doc-sync, portability, …) |
| `scratch/` | Throwaway local experiments (not shipped) |

**Exit criteria 0a:** every row above confirmed or corrected; no file in
`src/`, `tests/`, or the repo root is undocumented.

### 0b. Reconcile the planning docs with reality

The code is now at R0–R10 done / R11 active, but several docs were written when
that work was *future*. Audit each against the code and update. Known staleness
risks, highest first:

| Doc | Likely state | Action |
|---|---|---|
| `ROADMAP.md` | **Stale.** Its R7 "Current-state reconciliation" and the Phase-B/C frontier text describe two-parallel-callers + no service layer — a state that no longer exists. | Mark R0–R10 done; rewrite the reconciliation/frontier notes as completed history or remove; point the frontier at R11. |
| `firmware_agent_build_plan_concrete (10).md` | **Stale.** Step 1.0d describes the de-risk/migration as upcoming; it's done. | Annotate Step 1.0d (and Stage 1/2/3) as completed; keep as historical design record but flag current status. |
| `build_plan_spec_gaps.md` | **Largely resolved.** A pre-implementation gap list. | Mark resolved gaps; keep only genuinely open ones. |
| `firmware_agent_mcp_architecture.md` | **Verify.** Architecture doc — confirm the adapters/services/guardrails split + tool/resource decisions match code. | Update any divergence (e.g. actual tool list, return-shape conventions). |
| `mcp_tools.md` | **Verify relevance.** Generic "per-user dynamic tools over HTTP/OAuth" reference; the actual server is single-user stdio. | Decide: keep as forward-looking reference (label it that) or retire; do not let it read as current architecture. |
| `r10_contract.md` | **Verify.** Should match implemented refusal/block codes, response shapes, watcher rules. | Diff against `server.py` + `convergence_watcher.py` + `guardrails/`; fix drift. |
| `r11_benchmark_spec.md` | **Verify.** Should match runner + case format + result schema. | Diff against `tests/harness/r11_benchmark.py`, `tests/cases/`. |
| `current-progress.md` | **Current.** Just updated. | Light pass only. |
| `README.md` | **Verify.** | Ensure layout/commands match; it is also where pilot results get recorded later. |
| `superpowers/*.md` | Process playbooks, likely stable. | Spot-check only. |

**Method:** for each doc, the staleness test is "does any claim contradict the
code/tree as it exists now?" Use the doc-sync playbook (`superpowers/agent_doc_sync_playbook.md`)
as the standard. Prefer annotating design docs as historical over deleting them,
so the decision record survives.

**Exit criteria 0b:** no planning doc asserts a current state that the code
contradicts; `ROADMAP.md` and the build plan clearly show R0–R10 complete and
R11 as the live item.

---

## Phase 1 — Full nRF52840 service-layer validation (incl. flashing)

**Goal:** prove the full service layer on `nrf52840dk` the same way it is proven
on the scoped pair — Stage 0, Stage 1 smoke, and the server runtime/safety
surface — not just the connect/read subset proven earlier.

### 1a. Produce a real nRF52840 reference firmware (the precondition)

> **Toolchain decision (see `current-progress.md` → "nRF52840 Bench-Check
> Prerequisites" for the authoritative checklist):** build nRF firmware with
> **nRF Connect SDK (NCS)**, targeted via the `build_*.sh` env pointers
> (`ZEPHYR_WORKSPACE_DIR=<NCS workspace root>`, `ZEPHYR_SDK_INSTALL_DIR=<NCS SDK>`),
> not hand-built with a different toolchain than the agent will rebuild with. The
> "upstream Zephyr" phrasing below predates that decision; the build *shape* is the
> same `west build`, only the workspace pointer changes.

The earlier blocker stands: `firmware/nrf52840dk/reference/build/` has no
artifact, and "full functionality" (UART `boot ok`, symbol readback) needs a
*correct* image, not just any flashable hex.

- Adapt `firmware/nrf52833dk/reference/` for the nRF52840 DK: same Zephyr sample
  shape (`src/main.c`, `CMakeLists.txt`, `prj.conf`, `build_reference.sh`),
  retargeted to the `nrf52840dk` board, and producing the same observable
  contract the harness expects:
  - UART prints `boot ok`
  - a global `stage1_known_value = 0x1234ABCD` resolvable from the ELF
- Build it → `firmware/nrf52840dk/reference/build/firmware.{elf,hex}`.
- Confirm `boards/nrf52840dk.yaml` carries the matching expectations
  (`expected_uart_substring` / silicon-id already present at `0x10000100` =
  `0x00052840`).

> Lighter fallback if a full build is impractical short-term: prove flash
> *mechanism* only with a precompiled `blinky_pca10056.hex` (nRF52840 DK) or even
> the existing `nrf52833dk` hex (wrong chip, programs but won't run). This
> validates `flash_firmware` programming + read-back but NOT Stage 1 smoke / UART
> `boot ok`. Use only as an interim; full validation needs a real artifact.

### 1b. Run the validation matrix on nRF52840

With board attached and probe UID known (in `.env` or `--probe-uid`):

```
uv run python host_bootstrap.py --board-id nrf52840dk
uv run python stage0_check.py --board-id nrf52840dk \
  --reference-firmware nrf52840dk=firmware/nrf52840dk/reference/build/firmware.elf \
  --recover-test nrf52840dk --confirm-shared-usb nrf52840dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52840dk
```

Then the server runtime/manual surface (mirror the `nrf52833dk` sequence in
`current-progress.md` §"Nordic Manual Runtime Validation"): `connect` →
`flash_firmware` (default + explicit .elf/.hex) → `read_serial` (`boot ok`) →
`unlock_recover(confirm=false/true)` → reflash → watcher checks.

### Opportunity: this likely also closes the Windows-bench gap

All current hardware proof is on Mac; the Windows bench run is an open follow-up.
If the `nrf52840dk` lives on the Windows host, running Phase 1 there proves the
service layer on Windows + J-Link at the same time. Note which host Phase 1 runs
on and record it.

**Exit criteria Phase 1:** on `nrf52840dk`, Stage 0 (incl. recover), Stage 1
smoke (incl. flash + UART `boot ok` + symbol readback), and the server
runtime/safety sequence all pass; results recorded in `current-progress.md`
(and the host noted).

---

## Phase 2 — Full Mac hardware re-proof

**Goal:** establish a captured, known-good baseline of *all* hardware proof on
the Mac bench, so R11 (and any later claim) rests on a freshly re-verified
foundation rather than prior runs.

### 2a. Static + contract gate

```
uv run pytest -q
uv run ruff check .
uv run mypy src
```

### 2b. Scoped-pair preflight (both boards)

Run the full preflight from `current-progress.md` §"Scoped Board Preflight" for
`nucleo_l476rg` and `nrf52833dk`: `host_bootstrap` → `stage0_check`
(flash/UART, + Nordic recover) → `stage1_smoke`.

### 2c. Server runtime + safety manual matrix

Execute the manual runtime sequences already documented in `current-progress.md`
(STM32 runtime, Nordic runtime, Nordic UART watcher) and confirm the expected
response shapes (§"Expected Response Shapes").

### 2d. Optional: fold in nRF52840

If Phase 1 produced a real `nrf52840dk` artifact and the board is available on
the Mac, add it to the matrix so the Mac proof covers all three boards.

### 2e. Capture

Preserve `runs/<session_id>/...` artifacts from the passing runs as the baseline
evidence, and record the run set + host facts (probe UIDs, ports, quirks like
STM32 `connect_mode=under-reset`) in `current-progress.md`.

**Exit criteria Phase 2:** the full matrix passes on the Mac from a clean
checkout; artifacts captured; `current-progress.md` updated with the dated
re-proof and host facts. This is the green baseline the R11 pilot should launch
from.

---

## Sequencing, dependencies, and risks

**Order:**
- **Phase 0 is independent of hardware** — it can run in parallel with, or
  before, Phases 1/2. Doing 0b first is valuable because accurate docs make the
  hardware phases less error-prone.
- **Phase 1 gates on 1a** (a real nRF52840 artifact). If that slips, use the
  interim flash-mechanism fallback to unblock partial validation, but do not
  call Phase 1 complete until a real artifact passes Stage 1 smoke.
- **Phase 2** is "then" per the request: run it after Phase 1 so the Mac re-proof
  can optionally include the now-validated nRF52840.

**Risks / open questions to resolve before/while executing:**
- *Which host runs Phase 1?* If the nRF52840 is on Windows, Phase 1 doubles as
  the Windows-bench proof; confirm and record.
- *Recover on nRF52840 is destructive* (mass-erase) — fine on a dev board, but
  it wipes the artifact; reflash after, exactly as the `nrf52833dk` flow does.
- *Doc churn vs. history* — when reconciling (0b), prefer annotating design docs
  as completed history over deleting the decision record.
- *pyOCD version sensitivity* — recover/unlock and flash entry points are
  version-specific (already flagged in the build plan); reconfirm on the host's
  installed pyOCD if anything errors.

## Definition of done (all phases)

- `markdowns/repo_file_index.md` exists and covers every non-generated file.
- No planning doc contradicts the current code; `ROADMAP.md` + build plan show
  R0–R10 done, R11 active.
- `nrf52840dk` passes the full Stage 0 / Stage 1 / server-runtime matrix with a
  real reference artifact, host recorded.
- The full hardware matrix passes on the Mac from a clean baseline, artifacts
  captured, `current-progress.md` updated.
