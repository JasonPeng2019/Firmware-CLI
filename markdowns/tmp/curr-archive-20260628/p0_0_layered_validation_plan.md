# P0.0 Layered Validation Plan

## Purpose

`P0.0` is the clean-slate validation gate before the R12 prototype foundation
work starts.

The goal is to prove that the current repo is healthy enough to build on:

- current dirty or error-prone behavior is found, fixed, or explicitly recorded;
- non-hardware checks are green or have known, bounded failures;
- the current `R12` Codex-backed baseline is re-proved on the currently
  validated host boundary;
- the scoped real boards still work through the current code path;
- blocking calls return bounded errors instead of leaving the brain, server, or
  provider waiting forever;
- evidence is captured before `P0` and the parallel prototype waves begin.

This is not a prototype-feature implementation plan. It is the validation ladder
that Wave 0 must clear first.

## Scope

Run this plan on the current Wave 0 branch before branching `P0`.

Scoped boards:

- `nucleo_l476rg`
- `nrf52833dk`

Primary evidence output:

- `markdowns/curr/p0_0_validation_report.md` for the pass/fail matrix and human
  summary;
- `runs/<session_id>/...` for machine-generated run artifacts when the repo
  produces them.

Deferred, accepted prototype risk outside this plan:

- full official-pair second-provider reproof;
- true fresh-machine Windows portability proof;
- true fresh-machine macOS portability proof.

These are not treated as Wave 0 blockers for the prototype start. They remain
unverified follow-on work and must be recorded as such.

## Non-Goals

- Do not implement persistent provider sessions, model-authored actions, stream
  checkpoints, or green approval here.
- Do not add BLE/NCS/Zephyr demonstration apps here.
- Do not expand the server tool surface except to fix defects found by this
  validation.
- Do not claim hardware proof from old runs; re-run or mark pending.

## Entry Conditions

Before starting:

1. Confirm the branch is Wave 0:

   ```powershell
   git status --short --branch
   ```

2. Record the starting commit:

   ```powershell
   git rev-parse HEAD
   ```

3. Record local host context:

   ```powershell
   python --version
   uv --version
   pyocd --version
   ```

4. Confirm `markdowns/curr/` contains only active current-step docs and this
   plan. Historical current-step docs should live under `markdowns/tmp/`.
5. Record the active proof boundary for Wave 0:
   current validated host + Codex provider on the scoped pair.
6. Record the deferred proof boundary for Wave 0:
   second-provider parity and fresh-machine portability are accepted prototype
   risk, not part of `P0.0` closure.

## Layer 0 - Worktree And Branch Hygiene

Purpose:
make sure the validation starts from an understandable repo state.

Checks:

```powershell
git status --short --branch
git diff --stat
git diff --check
```

Pass criteria:

- any dirty files are intentional and listed in the validation report;
- no whitespace errors from `git diff --check`;
- no half-landed or contradictory docs remain in `markdowns/curr/`.

If the worktree is dirty because of validation fixes, record the exact files and
why they changed before moving to hardware proof.

## Layer 1 - Static And Unit Checks

Purpose:
catch ordinary Python, typing, formatting, and non-hardware regressions before
touching boards.

Commands:

```powershell
uv run pytest -q
uv run ruff check .
uv run mypy src
```

Pass criteria:

- all three commands pass; or
- any failure is reproduced, triaged to a concrete root cause, and fixed before
  prototype feature work starts.

Allowed pending state:

- a failure may remain only if it requires unavailable hardware and is marked as
  pending hardware in the validation report.

## Layer 1.5 - R12 Baseline Reproof Boundary

Purpose:
prove the existing turnkey baseline still works well enough to build the
prototype on top of it, without pretending the deferred portability/provider
claims have already been validated.

Required interpretation:

- Wave 0 must re-prove the current Codex-backed turnkey path on the currently
  validated host boundary.
- Wave 0 does not need to prove a second provider or fresh-machine setup before
  `P0` starts.
- those deferred items must be written down as unverified accepted risk in the
  validation report, not assumed working.

## Layer 2 - Timeout And Hang Regression Checks

Purpose:
verify that known hang-prone paths fail in bounded time and do not leave child
processes, server sessions, serial handles, or provider calls running after the
brain stops waiting.

Required checks:

- provider call timeout path using a stubbed or intentionally slow provider;
- MCP startup timeout path using a server command that never initializes;
- external command timeout path for build/workspace commands;
- external programmer/list command timeout paths where available;
- UART read with no expected data and a short read budget;
- bad serial port or unavailable probe path;
- pyOCD connect failure against a missing/wrong board;
- recover/flash refusal or timeout path where safe to simulate.

Pass criteria for every case:

- the caller returns a typed or structured error within the configured bound;
- the user-facing CLI returns control;
- no orphan provider, server, programmer, or build process remains;
- no board lock/session state persists after the failure unless explicitly
  documented as expected and recoverable.

Suggested orphan-process checks on Windows:

```powershell
Get-Process | Where-Object { $_.ProcessName -match 'python|pyocd|codex|claude|nrfjprog|STM32_Programmer_CLI' } | Select-Object Id,ProcessName,StartTime
```

Record elapsed wall-clock time for each negative case.

## Layer 3 - Host And Board Discovery Gate

Purpose:
prove the host can see the scoped boards before higher-level validation.

Commands:

```powershell
uv run python host_bootstrap.py --board-id nucleo_l476rg
uv run python host_bootstrap.py --board-id nrf52833dk
```

Pass criteria:

- board config loads;
- probe inventory is usable;
- serial discovery is usable or the required local override is documented;
- required packs/tooling are present or the bootstrap reports a bounded,
  actionable failure.

## Layer 4 - Stage 0 And Stage 1 Real-Board Proof

Purpose:
prove the current direct board-control substrate still works on both boards.

STM32:

```powershell
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
```

Nordic:

```powershell
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

Pass criteria:

- flash path works;
- reset/halt/read path works;
- UART reference output is captured;
- symbol/memory readback works in the Stage 1 harness;
- Nordic recover path is either proven or marked blocked with exact reason.

## Layer 5 - Direct MCP Tool Smoke

Purpose:
prove the server-facing tool contract works independently of the turnkey brain.

Run a small script or manual MCP client sequence against each board:

1. `connect`
2. `get_board_info`
3. `get_state`
4. `halt`
5. `read_core_register` for `pc`
6. `read_memory` from a safe known address or known symbol address
7. `resume`
8. `reset`
9. `read_serial`
10. `disconnect`

Pass criteria:

- every tool returns the expected structured shape;
- failures are typed and bounded;
- disconnect clears the server session;
- repeating the sequence does not leak state from the prior run.

If there is no committed harness for this exact sequence, add one as part of
P0.0 cleanup rather than relying on ad hoc manual calls.

## Layer 6 - Flash/UART/Symbol Repeatability

Purpose:
catch flaky behavior that passes once but fails under ordinary repetition.

For each board, repeat the core path at least three times:

1. connect;
2. flash reference firmware;
3. reset;
4. read UART until the known reference signal;
5. halt;
6. read `pc`;
7. resolve and read one known symbol when available;
8. disconnect.

Pass criteria:

- no unexplained intermittent failure;
- total elapsed time stays within expected bounds;
- watcher/guardrail state does not block legitimate repeated clean runs;
- no orphan process or hardware session remains after each cycle.

## Layer 7 - Turnkey Brain Smoke

Purpose:
prove the current brain can still drive a simple board-facing task before the
prototype changes the orchestration model.

Run at least one provider available on the host. Prefer `codex-cli` first if it
is the current local path.

STM32:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why."
```

Nordic:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why."
```

Optional API-provider checks when credentials and model selection are available:

```powershell
uv run pyocd-debug-brain run --provider openai-api --board-id nucleo_l476rg --task "Verify this reference firmware is healthy and explain why." --model <model>
uv run pyocd-debug-brain run --provider anthropic-api --board-id nrf52833dk --task "Verify this reference firmware is healthy and explain why." --model <model>
```

Pass criteria:

- the CLI prints progress or at least returns a final bounded result;
- the brain starts and stops the MCP server cleanly;
- the model does not thrash on repeated identical actions;
- run artifacts are written under `runs/<session_id>/...`.

Deferred in this layer:

- full official-pair second-provider reproof;
- fresh-machine portability proof.

Those may be attempted later, but their absence does not block `P0.0` closure
as long as they are clearly recorded as pending verification and accepted
prototype risk.

## Layer 8 - Benchmark Sanity Slice

Purpose:
prove the benchmark runner still works without requiring the full suite before
P0 starts.

Run:

- one known-good case;
- one injected-bug case that has historically passed;
- one fault/observability case if time allows.

If the repo has a stable suite command available, use it after the slice:

```powershell
uv run pyocd-debug-brain benchmark --provider codex-cli --suite pilot_v1_plus_b003_b004
```

Pass criteria:

- case manifests load;
- scoring artifacts are produced;
- known-good behavior is not misclassified as a code bug;
- injected-bug behavior reaches a bounded diagnosis or repair result;
- any failure is actionable and recorded.

## Layer 9 - Short Soak

Purpose:
catch leaks and delayed hangs before parallel prototype branches start.

Run a short soak per board:

- 10 cycles of connect, flash reference, reset, read UART, halt/read `pc`,
  disconnect; or
- the nearest existing committed smoke harness loop if it covers the same
  surfaces.

Pass criteria:

- no growing process count;
- no persistent serial/probe handle after disconnect;
- no increasing elapsed time trend that suggests a leak;
- no unexplained timeout.

## Validation Report Template

Create `markdowns/curr/p0_0_validation_report.md` with:

```markdown
# P0.0 Validation Report

## Environment

- branch:
- commit:
- host OS:
- Python:
- uv:
- pyOCD:
- boards attached:

## Pass/Fail Matrix

| Layer | Command/Case | Result | Elapsed | Artifact/Log | Notes |
|---|---|---|---|---|---|

## Fixes Made During P0.0

## Remaining Risks

## Pending Hardware

## Deferred Prototype Risk

- second-provider full official-pair reproof
- fresh-machine Windows portability proof
- fresh-machine macOS portability proof

## Exit Decision

- [ ] Wave 0 is clean enough to branch P0.
- [ ] Wave 0 is blocked; reason:
```

## Exit Criteria

`P0.0` is complete only when:

- non-hardware checks pass or have fixed/recorded root causes;
- timeout/hang negative cases return bounded errors;
- both scoped boards have fresh Stage 0/Stage 1 proof or missing proof is
  explicitly blocking;
- direct MCP tool smoke passes on both scoped boards or the failure is fixed;
- turnkey brain smoke returns control to the user on both scoped boards;
- no unexpected long-running provider/server/programmer/build processes remain;
- deferred second-provider and fresh-machine portability items are explicitly
  recorded as unverified accepted prototype risk rather than treated as
  blockers;
- `markdowns/curr/p0_0_validation_report.md` records the evidence.

## Verified

- This plan is a documentation-only validation ladder.
- The commands and board IDs are aligned with the current R12 manual validation
  sequence and scoped board pair.

## Pending Verification

- The plan has not been executed in this document change.
- Real `nucleo_l476rg` and `nrf52833dk` board proof is still required before
  claiming Wave 0 is clean.
- Second-provider parity and fresh-machine portability are intentionally
  deferred outside `P0.0`; they remain unverified and should not be claimed as
  working.
- The exact timeout negative-test harnesses may need small committed scripts if
  equivalent tests do not already exist.
