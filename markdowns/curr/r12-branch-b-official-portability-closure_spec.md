> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# R12 Branch B Official Portability Closure Spec

## Goal in plain English

Close the remaining proof gaps before anyone can honestly describe Branch B as
fully deployable on a supported customer's machine.

Branch B's scoped implementation is already built and live-proven on the
attached Windows bench pair `nucleo_l476rg + nrf52840dk`. This spec covers what
is still missing for the stricter project-wide claim:

- the official scoped board pair, `nrf52833dk + nucleo_l476rg`;
- fresh supported host proof on Windows and macOS after the documented
  bootstrap;
- customer-like repeated prompts through the public CLI, real Codex provider,
  real MCP subprocess, real boards, and session-scoped client actions.

Roadmap anchor: `R12` prototype Wave 1 / Branch B, under the build plan's Stage
5 turnkey brain + CLI exit criteria and the roadmap/current-progress
fresh-machine portability proof gap.

## Scope and non-scope

In scope:

- run the current Branch B deployment proof on the official scoped pair:
  `nrf52833dk + nucleo_l476rg`;
- run the same proof from a clean supported Windows host after the documented
  bootstrap;
- run the same proof from a clean supported macOS host after the documented
  bootstrap;
- verify the public command surface a customer actually uses:
  `pyocd-debug-brain run`, `--task-file` or `--task-stdin`,
  `--client-action NAME=PATH`, `--workspace-root`, and `--build-command`;
- verify real Codex provider execution, real MCP server-client subprocess
  execution, real board attach, UART write/read, ordered batches, `wait`, and
  `run_script`;
- verify repeated user prompts on each proven host/board combination, with each
  prompt running a full brain loop;
- verify no Branch B path relies on machine-local ports, probe UIDs, absolute
  repo paths, shell-only quoting, or a bench-only script path;
- fix any deployment, bootstrap, path, quoting, discovery, or documentation
  defect found during this proof pass;
- update only the authoritative docs that the proof or any fix actually moves.

Out of scope:

- provider-session continuity across user prompts. That remains Branch A scope;
- real tool-schema prompt forwarding. That remains Branch A scope;
- timeout clamp/default ownership. That remains Branch C scope;
- progress UI, developer inspector, stream checkpoints, and scoped green
  approval. Those remain Wave 2 / later-branch scope;
- provider-native tool-call conversion;
- broad shipped-product packaging/distribution format. The current portability
  contract is a repo-owned `uv` workflow after a short documented bootstrap,
  not a final commercial installer;
- a hardened sandbox for arbitrary untrusted client-action code. Branch B only
  injects a gated server API and restricted builtins for session-scoped scripts.

## Reconciliation summary

Build plan:

- The source-of-truth build plan names `nrf52833dk + nucleo_l476rg` as the
  co-primary board pair for the project.
- It requires macOS + Windows cross-platform hygiene from day one: ports from
  config/discovery, paths through portable APIs, no OS-specific command
  assumptions in product code.
- It defines the portability contract as supported hosts plus supported boards
  after a short documented developer bootstrap, with vendor-driver realities
  detected/guided rather than hidden.
- Stage 5 requires the turnkey brain + CLI to run the full loop on the scoped
  pair and show the more agentic prototype loop: free host work, governed board
  decisions, bounded waits, client actions, and related prototype behavior.

Current code:

- Branch B has implemented the scoped action surface:
  `action_batch`, bounded `wait`, `write_serial`, and `run_script`.
- `pyocd-debug-brain run` now accepts `--task-file`, `--task-stdin`, and
  repeatable `--client-action NAME=PATH`.
- Client-action files are loaded with `pathlib`, validated as Python modules
  defining `run(inputs, server)`, snapshotted by SHA-256, rendered in the prompt,
  executed with a gated server API, and persisted in `client_actions.json`.
- The Branch B code paths inspected for this spec do not hardcode a bench serial
  port or probe UID. Product code continues to route ports/probes through the
  existing board config and discovery layers.
- Branch B deployment proof exists on this Windows host for the physically
  attached `nucleo_l476rg + nrf52840dk` pair, including real Codex, real MCP,
  public `--client-action`, workspace edit/build, and repeated user prompts.
- The exact official `nrf52833dk` Branch B proof has not been produced in this
  Branch B completion pass because the attached Nordic board identified as
  `nrf52840dk` / `NRF52840_xxAA_REV2`.
- True fresh-machine Windows/macOS portability proof for Branch B has not been
  produced in this completion pass.

Other docs or notes:

- `README.md`, `ROADMAP.md`, and `current-progress.md` all explicitly say true
  fresh-machine Windows/macOS portability proof remains deferred/unverified.
- `R12_P_SPLIT.md` now records Branch B as implemented and reviewed while
  keeping exact `nrf52833dk` Branch B deployment proof pending.
- `markdowns/curr/r12-branch-b-status.md` records the attached-board proof as
  clean and identifies the same `nrf52833dk` and fresh-machine portability
  pending items.
- `things-to-change.md` includes broader prototype items that Branch B does not
  own, including persistent sessions, progress/inspector, stream checkpoints,
  and scoped green approval.

Disagreements:

- No source-of-truth conflict was found. The docs consistently distinguish the
  narrower current Branch B proof from the broader official-pair and
  fresh-machine portability claims.
- AMBIGUITY: the project can either merge Branch B with these proof gaps
  recorded, or promote this closure spec to a hard pre-merge gate. This spec is
  written so either choice is explicit. It does not silently change the build
  plan's current deferred-risk status.

## Design

This is primarily a validation and deployment-closure spec. It should not add a
new Branch B feature unless a real fresh-host or official-board run exposes a
defect.

The proof should use the same public path a customer uses:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id <board> --task-file <prompt-file> --client-action uart_write=<path>
```

For customer-like coding prompts, include:

```powershell
--workspace-root <temp-workspace> --build-command "python app.py"
```

The validation should have two prompt shapes per board/host:

1. A short board-action prompt that requires a single ordered batch:
   `connect`, `wait`, `run_script:uart_write`, `read_serial`, then finalize.
2. A coding prompt that requires inspect/replace/build in a temporary workspace,
   then the same ordered board batch, then finalize.

Each prompt is a separate public CLI invocation. This intentionally proves
repeated customer prompts through the current Branch B surface without claiming
Branch A provider-session persistence.

If a failure occurs, classify it before changing code:

- setup/bootstrap failure: fix setup docs or scripts, not Branch B logic;
- board discovery/port/probe failure: fix the shared discovery/config layer,
  not a Branch B special case;
- shell quoting/task ingestion failure: prefer `--task-file` / `--task-stdin`
  and fix CLI docs/tests if needed;
- Branch B action failure: fix the narrow layer that owns it:
  action parsing, batch execution, client-action loading/execution, UART service,
  or MCP tool wrapper.

No general host shell/file executor should be added to the MCP server. Host work
remains model-native/provider-side; board/server-native work remains gated by
the brain and server.

## Board-facts-as-data and origin tags

- `nrf52833dk` and `nucleo_l476rg` are `PROJECT-DEFINED` canonical board ids
  from the build plan and board YAML.
- `nrf52840dk` is a `PROJECT-DEFINED` retained alternate profile, not the
  official scoped Nordic proof target for this closure.
- MCU identities, silicon identity registers, and expected silicon values are
  `HW-FIXED` and must continue to live in board config / board validation code,
  not in Branch B conditionals.
- pyOCD target names, SEGGER/ST-Link tool behavior, and serial/vendor helper
  outputs are `VENDOR-FIXED`; any fresh-host drift must be verified against the
  installed tool versions.
- serial ports, probe UIDs, temp workspace roots, and run roots are
  machine-local discovered facts. They must not be written into tracked board
  config or Branch B product code.
- `--client-action NAME=PATH` action names are `PROJECT-DEFINED` prompt-stable
  ids for the current run. The path is machine-local input and must be resolved
  with portable path APIs.

## Documentation plan

- If the proof passes without code changes, update:
  - `markdowns/current-progress.md` with the exact host/board/run-root matrix;
  - `markdowns/R12_P_SPLIT.md` only if the pending verification bullets change;
  - `markdowns/curr/r12-branch-b-status.md` with the new proof roots.
- If a CLI usage or deployment instruction changes, update `README.md` in the
  operator command section.
- If host bootstrap or setup sequence changes, update `stage0_setup.md` and the
  relevant setup script help/docstrings.
- If an MCP tool behavior changes, update the tool docstring in
  `src/pyocd_debug_mcp/server.py`; do not create a sidecar MCP tool doc.
- If the project decides this closure is now a hard pre-merge gate rather than
  deferred proof, update the build plan or roadmap only with explicit user
  sign-off. This spec alone is not authority.

## Portability

The target portability claim is:

Supported macOS and Windows hosts, after a short documented bootstrap
equivalent to normal manual board debugging, can run the Branch B public CLI
against the supported boards without bench-specific configuration.

The proof must therefore start from clean or fresh-enough host states:

- clean checkout or clean worktree for the validation copy;
- `uv sync` or documented setup script path;
- no reliance on this developer's `.env` unless the same path is documented as
  the user-facing configuration path;
- no hardcoded `COM*`, `/dev/cu.*`, probe UID, or absolute repo path in the
  commands or code;
- prompt text supplied through `--task-file` or `--task-stdin` for long or
  JSON-like prompts;
- client-action paths passed as relative repo paths or portable absolute paths;
- host build commands chosen to work on both OSes for the proof prompt
  (`python app.py` is acceptable for the temporary workspace smoke).

Unautomatable vendor prerequisites, such as SEGGER/ST-Link driver/tool
installation, may remain bounded bootstrap prerequisites. The runtime must
detect or fail clearly after bootstrap; it must not require repeated manual
environment debugging.

## Verification plan

Non-hardware checks, cheapest first:

```powershell
uv run pytest -q
uv run ruff check .
uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py
uv run pytest -q tests/test_r11_benchmark.py
uv run python -m tests.harness.r11_benchmark --help
git diff --check
```

Fresh-host bootstrap proof, per supported OS:

```powershell
uv sync
uv run pyocd-debug-brain run --help
uv run python host_bootstrap.py --board-id nucleo_l476rg --install-packs
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

Branch B deployment proof, per supported OS and per official board:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id <board-id> --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 5 --serial-read-seconds 3 --task-file <prompt1.txt>
uv run pyocd-debug-brain run --provider codex-cli --board-id <board-id> --workspace-root <temp-workspace> --build-command "python app.py" --client-action uart_write=tests/fixtures/client_actions/uart_write.py --max-iters 8 --serial-read-seconds 3 --task-file <prompt2.txt>
```

Required artifact checks for every Branch B deployment run:

- `run-metadata/turnkey_result.json` records `final_status=diagnosed_only` or
  an explicitly successful status and `classification=healthy`;
- `actions_taken` includes the ordered Branch B board sequence;
- coding prompts include `read_file`, `replace_file`, and `run_build`;
- `mcp_tools_used` includes `connect`, `write_serial`, and `read_serial`;
- `run-metadata/client_actions.json` records `uart_write.executed=true` and a
  content SHA-256;
- `logs/model_turns.jsonl` contains multiple model turns for the coding prompt;
- no command used a hardcoded serial port or probe UID.

## Acceptance criteria

- Branch B official-pair proof exists on `nrf52833dk + nucleo_l476rg`.
- Branch B public CLI proof exists on a supported Windows host after documented
  bootstrap.
- Branch B public CLI proof exists on a supported macOS host after documented
  bootstrap.
- Each proven host/board combination has two separate user prompts: a focused
  board batch and a customer-like coding/build/batch prompt.
- All proof uses real Codex, real MCP subprocesses, real hardware, and
  `--client-action NAME=PATH`.
- Any setup/code/doc defect found during proof is fixed in the narrow owning
  layer and verified by rerunning the failing check plus the non-hardware
  ladder.
- `current-progress.md` and the Branch B review docs record exact run roots and
  distinguish official scoped proof from retained alternate proof.
- The final status does not claim fresh-machine or official-pair proof until the
  real run artifacts exist.

## Verified

- This spec was reconciled against the build plan, roadmap, current progress,
  `R12_P_SPLIT.md`, Branch B specs/reviews, `things-to-change.md`, README, and
  the relevant Branch B implementation files.
- Current Branch B implementation is already verified on the attached Windows
  bench pair `nucleo_l476rg + nrf52840dk`, including multi-loop public CLI
  proof.
- No Branch B-specific product-code hardcoded serial port, probe UID, or
  absolute bench path was found in this audit.
- Existing docs consistently mark exact `nrf52833dk` Branch B proof and
  fresh-machine Windows/macOS portability proof as pending, not silently done.

## Pending verification

- Execute this spec on real `nrf52833dk + nucleo_l476rg` hardware.
- Execute this spec on a fresh supported Windows host.
- Execute this spec on a fresh supported macOS host.
- Decide whether this closure is a hard pre-merge gate for Branch B or an
  explicit post-merge proof task.
