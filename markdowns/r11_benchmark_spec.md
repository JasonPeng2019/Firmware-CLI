# `R11` BYO-Agent Benchmark Spec

## Summary

`R11` proves the first real product claim for the scoped pair
`nrf52833dk + nucleo_l476rg`: a stock external agent can use the current MCP
server to diagnose, repair when appropriate, and re-verify a small, repeatable
benchmark corpus on real hardware.

This document is the implementation source of truth for the first `R11` slice.
It freezes:

- the benchmark case format
- the first corpus
- the Codex result schema
- the scoring rubric
- the run-capture contract
- the first external-agent path

The first `R11` agent is **Codex CLI**, not Claude Code and not manual
Inspector use.

## External-Agent Path

- agent: `Codex CLI`
- invocation: scripted `codex exec`
- MCP prerequisite:

```bash
codex mcp add pyocd-debug -- uv run pyocd-debug-mcp
```

- runner preflight must verify registration with:

```bash
codex mcp get pyocd-debug
```

- the runner must not mutate Codex MCP registration automatically

## Benchmark Case Contract

Each benchmark case lives under `tests/cases/<case_id>/` and contains:

- `case.yaml`: machine-readable case contract
- `prompt.md`: the exact Codex prompt template for the case
- optional `notes.md`: human-only notes, never used by scoring

Each `case.yaml` must define:

- `case_id`
- `title`
- `board_id`
- `kind`
  - `known_good`
  - `injected_bug`
  - `observability_fault`
- `workspace_mode`
  - `reference_read_only`
  - `copied_bug_workspace`
- `initial_prep`
  - `flash_mode`
    - `reference`
    - `case_artifact`
  - `post_flash_state`
    - `running`
    - `halted`
- `artifacts`
  - `flash_artifact`
  - `symbol_artifact`
  - for bug cases only:
    - `source_root`
    - `build_script`
- `expected_observables`
  - `uart_substring`
  - `symbol_name`
  - `symbol_value_u32`
  - optional `test_read_address`
- `allowed_actions`
  - `mcp_tools`
  - `code_edits_allowed`
  - `allowed_edit_roots`
  - `build_command`
  - `recover_allowed`
- `success_criteria`
  - `expected_classification`
    - `healthy`
    - `code_bug`
    - `observability_fault`
    - `physical_fault`
  - `requires_code_fix`
  - `requires_green_verification`
  - `expected_changed_files`
  - `forbidden_actions`
- `scoring_profile`

## First Corpus

The first pilot corpus contains 8 cases.

Known-good:

- `nucleo_l476rg__k001_reference_green`
- `nrf52833dk__k001_reference_green`

Injected code-bug cases:

- `nucleo_l476rg__b001_wrong_boot_text`
- `nrf52833dk__b001_wrong_boot_text`
- `nucleo_l476rg__b002_wrong_known_value`
- `nrf52833dk__b002_wrong_known_value`

Observability-fault cases:

- `nucleo_l476rg__f001_halted_target_silent_uart`
- `nrf52833dk__f001_halted_target_silent_uart`

The first fault corpus is intentionally **host-induced only**. Manual cable or
physical wiring faults are deferred until after the pilot is trustworthy.

## Result Schema And Scoring

The runner must require Codex final output through `codex exec --output-schema`.

The structured result requires:

- `case_id`
- `board_id`
- `session_id`
- `final_status`
  - `fixed`
  - `healthy_confirmed`
  - `diagnosed_only`
  - `unresolved`
  - `blocked`
- `classification`
- `root_cause`
- `actions_taken`
- `mcp_tools_used`
- `files_changed`
- `recover_used`
- `verification`
  - `flash_ok`
  - `uart_ok`
  - `symbol_ok`
  - `green_check_ok`
- `summary`

Score every case out of 100:

- `40`: diagnosis/classification correctness
- `25`: intervention correctness
- `25`: final verification outcome
- `10`: safety/convergence discipline

Full success:

- score `>= 85`
- correct classification
- correct intervention path
- required green verification succeeded

Partial success:

- score `50-84`
- usually correct diagnosis but incomplete repair or incomplete proof
- or correct repair without trustworthy final explanation

Fail:

- score `< 50`
- or wrong classification
- or unresolved state
- or watcher block caused by thrashing
- or destructive misuse that violates case policy

Penalty rules:

- unnecessary `unlock_recover` on a code-bug or halted-target case: `-25`
- watcher block from repeated bad mutation attempts: final score capped at `40`
- code edits during an observability-fault case: final score capped at `50`
- correct final state but wrong diagnosis: final score capped at `60`

## Run-Capture Contract

Use the server-generated `runs/<session_id>/...` tree as the durable benchmark
artifact root.

For each case, the runner must save:

- existing `logs/events.jsonl`
- existing `run-metadata/session.json`
- new `run-metadata/benchmark_case.json`
- new `run-metadata/benchmark_result.json`
- new `run-metadata/score.json`
- new `run-metadata/firmware_identity.json`
- new `logs/codex_exec.jsonl`
- new `logs/prompt.txt`
- new `captured-serial/final_excerpt.txt`
- new `applied-patches/agent.diff`

The first pilot freezes **one MCP session per case**.

If a Codex run produces zero new session directories or more than one new
session directory under `runs/`, the case fails.

`firmware_identity.json` must record:

- case id
- board id
- flashed artifact path
- symbol artifact path
- SHA-256 of both artifacts
- artifact kind: `reference` or `bug_variant`
- workspace source path for bug cases

## Runner Behavior

The canonical entrypoint is:

```bash
uv run python -m tests.harness.r11_benchmark --suite pilot_v1
```

Required capabilities:

- load and validate `case.yaml`
- render case prompt from `prompt.md`
- prepare a benchmark workspace under the gitignored `runs/` tree
- prepare initial target state before Codex starts
- invoke `codex exec`
- require exactly one new `session_id`
- verify that `runs/<session_id>/...` exists
- rerun `stage1_smoke` as the final green-state verifier
- compute score
- write benchmark artifacts into the session directory
- print a stable per-case and per-suite summary

The runner must sit on top of the existing board configs, artifact resolver,
Stage 1 smoke harness, and current MCP server. It must not reopen SWD/UART
architecture or redesign `R10`.

## Pilot Order

Run the first pilot in this order:

1. `nucleo_l476rg__k001_reference_green`
2. `nrf52833dk__k001_reference_green`
3. `nucleo_l476rg__b001_wrong_boot_text`
4. `nrf52833dk__b001_wrong_boot_text`
5. `nucleo_l476rg__b002_wrong_known_value`
6. `nrf52833dk__b002_wrong_known_value`
7. `nucleo_l476rg__f001_halted_target_silent_uart`
8. `nrf52833dk__f001_halted_target_silent_uart`

Pilot acceptance:

- both known-good cases score full success
- at least one code-bug case per board reaches full success
- both observability-fault cases are diagnosed as non-code faults
- runner artifacts are complete under `runs/<session_id>/...`
- the pilot exposes any missing observability or scoring gaps before the corpus
  expands
