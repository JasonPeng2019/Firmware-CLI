> STATUS: PROPOSAL - not authority. Implemented and verified in the current Branch B worktree for the attached `nucleo_l476rg + nrf52840dk` pair; exact `nrf52833dk` proof remains pending.

# R12 Branch B Full Deployment Completion Spec

## Goal in plain English

Finish `R12` prototype Wave 1 Branch B so it is not only internally testable,
but deployable through the normal customer-facing command path:

```powershell
uv run pyocd-debug-brain run --provider codex-cli ...
```

Roadmap anchor: `R12` prototype Wave 1 / Branch B.

The current Branch B runtime can execute ordered batches, `wait`,
`write_serial`, and `run_script` when a test harness seeds a
`ClientActionStore`. The remaining Branch B completion work is to expose that
session-scoped client-action store through the public brain CLI/app path, show
registered actions to the real provider in the prompt, and prove the full
feature chain through real Codex, real MCP, real hardware, and a real editable
workspace over multiple provider turns.

## Scope and non-scope

In scope:

- add an operator-facing way to register session-scoped client actions for
  `pyocd-debug-brain run`;
- load registered client-action files into the current run's
  `ClientActionStore`;
- validate action names, paths, content, and duplicate names deterministically;
- show registered action names, descriptions, source paths, and content hashes
  in the model prompt;
- pass the loaded store through `brain/app.py` into `run_turnkey`;
- persist enough client-action metadata in run artifacts for audit;
- test `run_script(name, inputs)` through the same public CLI/app path that a
  customer uses, not only through private harness injection;
- run at least one real Codex deployment smoke that uses multiple provider
  turns, real code/workspace actions, a registered client action, real MCP, and
  real hardware.

Out of scope:

- provider persistent sessions from Branch A;
- provider-native tool-call conversion;
- general MCP host shell/file execution;
- a hardened Python sandbox for arbitrary untrusted code;
- project-persistent custom actions that survive beyond the current run;
- UI/progress/inspector rendering from Wave 2;
- stream checkpoints/cancel support for long client actions;
- scoped green approval or model-made test approval from Branch F;
- broad benchmark-corpus scoring changes.

## Reconciliation summary

Build plan:

- `R12` prototype target says client actions are model-authored scripts saved in
  a session-scoped client-action store and run by name with inputs.
- Scripts that call server-native tools are governed and route every server
  call through the brain.
- Host-only work stays model-native, while board/server-native work remains
  governed.
- The turnkey product is exposed through `pyocd-debug-brain run` and benchmark
  commands.

Pre-implementation code state this spec was written to close:

- `ClientActionStore`, `ClientActionRecord`, snapshots, hashes, and
  `run_client_action(...)` exist in `brain/client_actions.py`.
- `run_turnkey(...)` accepts `client_actions: ClientActionStore | None`.
- `run_script` can execute a registered action through the brain gate when a
  store is supplied programmatically.
- At spec time, `pyocd-debug-brain run` did not accept any client-action
  registration flag.
- At spec time, `brain/app.py::run_freeform_task(...)` had no client-action
  parameter.
- At spec time, `TurnkeyInvocation` carried no client-action registration
  metadata.
- At spec time, `_build_turn_prompt(...)` listed `run_script(name, inputs)`,
  but did not list which script names were registered in this session.
- At spec time, real Codex provider proof existed for
  `action_batch(connect, wait, write_serial, read_serial)`, but not for
  public-CLI `run_script`, because no public CLI registration path existed.

Implementation outcome:

- The public Branch B completion pass added repeatable
  `--client-action NAME=PATH` registration.
- Registered actions are loaded into the session-scoped client-action store,
  shown to the provider, and persisted in `client_actions.json`.
- Public-CLI `run_script` was verified through real Codex, real MCP, real
  hardware, and repeated user-prompt / multi-loop deployment runs on the
  attached `nucleo_l476rg + nrf52840dk` pair.

Other docs or notes:

- `markdowns/R12_P_SPLIT.md` assigns Branch B ownership for client actions.
- `markdowns/curr/r12-branch-b-action-boundary_process.md` recorded the
  original public CLI gap that this spec closed.
- `markdowns/curr/r12-branch-b-action-boundary_review.md` now records that
  public CLI client-action registration was added after the action-boundary
  review and verified in the later completion pass.
- `markdowns/curr/things-to-change.md` says CLI providers run in temp dirs and
  are one-shot today, so provider persistence is separate from this gap.

Disagreements and ambiguities:

- No source-of-truth conflict was found. At spec time, the implementation was
  behind the Branch B deployability bar, but that was implementation
  incompleteness, not a plan conflict. The later completion pass closed this
  gap for the attached-board proof boundary.
- AMBIGUITY: "model-authored" client actions can mean either scripts authored
  before the run and registered into the session, or scripts created dynamically
  by the provider during the run. For this Branch B completion pass, use the
  minimal deployable interpretation: the operator or test fixture registers
  session-scoped scripts at run start, and the model calls them by name with
  inputs. Dynamic provider-authored registration during a running one-shot CLI
  provider session remains future work unless Branch A changes the provider
  execution model.

## Design

### Public client-action registration

Add a repeatable `pyocd-debug-brain run` flag for session-scoped action
registration. The proposed minimal contract is:

```powershell
--client-action NAME=PATH
```

The CLI may also accept a separate optional description field if that can be
kept simple, but a description must not be required for the minimal path. If no
description is provided, use the first non-empty module docstring line or the
file stem as the prompt description.

Validation rules:

- `NAME` is a project-defined run-local identifier, not a filesystem path;
- names must be non-empty and stable enough for JSON decisions, for example
  letters, digits, underscore, dash, and dot;
- duplicate names are refused before provider startup;
- `PATH` is resolved with `pathlib`, may be absolute or relative to the current
  working directory, and must point to a readable file;
- content is read as UTF-8 with replacement or a documented deterministic
  UTF-8 policy consistent with the repo's subprocess-capture behavior;
- empty files or files without `run(inputs, server)` are refused before
  provider startup where practical, or deterministically refused at first
  execution with a clear error;
- no shell execution, executable-bit assumption, or OS-specific path handling is
  introduced.

### Data flow

Add a small structured load path rather than passing raw strings through the
system:

1. `brain/cli.py` parses repeated `--client-action NAME=PATH` flags.
2. `brain/app.py::run_freeform_task(...)` receives those registrations.
3. A client-action loader builds an `InMemoryClientActionStore`.
4. The store is passed into `run_turnkey_with_provider(...)` and then
   `run_turnkey(...)`.
5. `_build_turn_prompt(...)` receives the store or a rendered summary and shows
   registered action metadata to the provider.

The benchmark command does not need client-action registration in this pass
unless a benchmark case explicitly needs it. The customer deployment target for
this spec is `pyocd-debug-brain run`.

### Prompt visibility

The provider prompt must include a "Registered client actions" section when the
store is non-empty. It should list:

- name;
- description;
- relative/source path as seen by the operator;
- SHA-256 content hash;
- input convention if available from a simple module-level docstring or
  metadata convention.

The prompt must not inline the full script body by default. The purpose is to
make `run_script(name, inputs)` usable and auditable without dumping arbitrary
script text into every provider turn.

### Run artifacts

Persist registered client-action metadata under the run root, for example in
`run-metadata/client_actions.json`. Include:

- name;
- source path;
- description;
- content SHA-256;
- whether it was executed;
- execution result summaries already captured in brain trace.

Do not persist executable temp copies unless a later implementation needs them.
If script content is persisted, make that an explicit decision in the artifact
contract and document why.

### Real deployment acceptance scenario

The acceptance scenario must look like a customer workflow, not a unit harness.

Use a command shaped like:

```powershell
uv run pyocd-debug-brain run `
  --provider codex-cli `
  --board-id nucleo_l476rg `
  --workspace-root <editable-fixture-workspace> `
  --build-command "<portable build command>" `
  --client-action uart_write=<path-to-client-action-script> `
  --max-iters 4 `
  --serial-read-seconds 3 `
  --task "<multi-turn task>"
```

The task should require multiple provider turns and should prove:

- Codex sees the registered client action;
- Codex uses normal turnkey workspace actions for real coding work, such as
  reading a file, replacing a file, and running the configured build command;
- Codex then emits a governed `action_batch` containing at least:
  `connect`, `wait`, `run_script(name, inputs)`, `read_serial`;
- the `run_script` action calls `write_serial` through the brain gate;
- the run uses one MCP session for the board-facing portion unless the task
  explicitly justifies otherwise;
- the final result is based on the brain-observed action results, not a
  self-reported provider claim.

If the reference firmware does not echo or react to UART writes, the hardware
claim remains "UART bytes were written without backend failure and UART boot
text was then verified." Do not claim device-level stimulus response unless the
firmware reports such a response.

## Board-facts-as-data and origin tags

No new board-specific facts are required.

New values and origins:

- `--client-action`: `PROJECT-DEFINED`, a Branch B CLI contract.
- client-action name syntax: `PROJECT-DEFINED`, chosen for JSON/path
  portability and prompt stability.
- content hash algorithm, expected to be SHA-256: `PROJECT-DEFINED`, standard
  library implementation.
- action file paths: operator/session inputs, not tracked board facts.
- UART baud, port, target, and board identity still come from board config,
  serial discovery, or explicit operator overrides. No hardcoded port, baud,
  probe UID, or board-specific branch may be introduced.

## Documentation plan

- This spec is the proposal for completing Branch B deployability.
- Update `markdowns/curr/r12-branch-b-action-boundary_process.md` when the
  implementation lands, because it currently records this as a pending gap.
- Update `markdowns/curr/r12-branch-b-action-boundary_review.md` with the new
  review result after the build/review pass.
- If `pyocd-debug-brain run --help` changes, update the operator-facing R12 CLI
  docs or README section that lists brain CLI usage.
- Do not add a sidecar MCP tool doc. `run_script` is a brain action, not an MCP
  server tool; `write_serial` remains documented in its MCP tool docstring.
- If run artifacts gain `client_actions.json`, update the R12 run artifact
  contract where existing turnkey artifacts are documented.

## Portability

The registration path must work on Windows and macOS:

- use `pathlib` and argparse, not shell parsing tricks;
- support paths with spaces;
- avoid executable-bit or shebang requirements;
- avoid OS-specific temp paths in tracked artifacts;
- validate relative paths from the current process working directory or an
  explicitly documented base;
- ensure help text and errors do not mention this developer's local machine;
- keep provider commands bounded by the existing provider timeout path.

No new dependency is expected. If a build pass decides a dependency is needed
for script metadata parsing or sandboxing, it must go through the package/lock
workflow and be justified as part of the same change.

## Verification plan

Non-hardware checks:

```powershell
uv run pytest -q
uv run ruff check .
uv run mypy src
```

Focused tests required:

- CLI parser accepts repeated `--client-action NAME=PATH`;
- parser rejects malformed entries, duplicate names, missing files, and empty
  names before provider startup;
- loader builds deterministic `ClientActionRecord` entries with stable hashes;
- prompt rendering includes registered action names, descriptions, paths, and
  hashes;
- `run_freeform_task(...)` passes the loaded store into `run_turnkey`;
- a fake provider using the public app/CLI-shaped path can call
  `run_script(name, inputs)` and the script-owned `write_serial` appears in
  `mcp_tools_used`;
- existing runs without `--client-action` remain unchanged;
- real single-action and real batch compatibility tests remain green.

Real deployment checks:

1. Real Codex provider, real MCP, real hardware, no client action:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --max-iters 2 --serial-read-seconds 3 --task "<batch/wait/write/read smoke>"
```

2. Real Codex provider, public client-action registration, real MCP, real
   hardware:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --client-action uart_write=<path> --max-iters 3 --serial-read-seconds 3 --task "<run_script smoke>"
```

3. Real Codex provider, real coding/workspace flow, public client-action
   registration, real MCP, real hardware:

```powershell
uv run pyocd-debug-brain run --provider codex-cli --board-id nucleo_l476rg --workspace-root <fixture> --build-command "<portable command>" --client-action uart_write=<path> --max-iters 4 --serial-read-seconds 3 --task "<multi-turn coding + run_script smoke>"
```

4. Repeat the hardware portion on the attached Nordic board. If the attached
   board is still physically `nrf52840dk`, record that as retained-board proof
   and keep exact `nrf52833dk` proof pending.

Artifact checks:

- inspect `logs/model_turns.jsonl` to confirm real Codex emitted
  `run_script(name, inputs)`;
- inspect `logs/brain_trace.jsonl` to confirm ordering and results;
- inspect `run-metadata/turnkey_result.json` to confirm `actions_taken` and
  `mcp_tools_used`;
- inspect client-action metadata artifact if implemented.

## Acceptance criteria

Branch B is fully complete for deployment when:

- `pyocd-debug-brain run` exposes a documented way to register session-scoped
  client actions;
- the public app/CLI path loads those actions into the same store used by
  `run_script`;
- the provider prompt lists registered client actions clearly enough for real
  Codex to choose `run_script(name, inputs)` without hidden harness state;
- script-owned server calls route through `_execute_server_tool` and appear in
  `mcp_tools_used`;
- run artifacts include enough client-action metadata to audit what script ran;
- a real Codex CLI run completes a public `run_script` deployment smoke on real
  MCP and real hardware;
- a real Codex CLI run completes a multi-turn customer-like coding smoke with
  workspace read/edit/build plus a governed Branch B action batch;
- the full non-hardware ladder is green after the change;
- exact board proof is honestly separated between the official scoped pair and
  any retained alternate board that is physically attached.

## Verified

- `pyocd-debug-brain run` now accepts repeatable
  `--client-action NAME=PATH`.
- The app path loads registered files into the per-run `ClientActionStore` and
  passes that store into the turnkey loop.
- Provider prompts now include registered client-action name, path, description,
  and SHA-256 content hash.
- Run artifacts now persist `run-metadata/client_actions.json` with executed
  status.
- Non-hardware verification passed:
  `uv run pytest -q`, `uv run ruff check .`,
  `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`,
  `uv run pytest -q tests/test_r11_benchmark.py`, and
  `uv run python -m tests.harness.r11_benchmark --help`.
- Focused Branch B tests passed for loader validation, CLI/app threading,
  prompt visibility, `run_script`, and client-action audit metadata.
- Real Codex + real MCP + public `--client-action` smoke passed on:
  `nucleo_l476rg` (`20260628T210308Z-8b42e2ce`) and attached
  `nrf52840dk` (`20260628T210353Z-79827461`).
- Full customer-like Codex runs passed on both attached boards with multiple
  provider turns, workspace read/edit/build, governed action batch, `wait`,
  `run_script:uart_write`, and `read_serial`:
  `20260628T210541Z-8b5ecff9` (`nucleo_l476rg`) and
  `20260628T210710Z-b62737bb` (`nrf52840dk`).
- The current connected Nordic board reports as `nrf52840dk`, not the official
  scoped `nrf52833dk`.

## Pending verification

- Exact `nrf52833dk` proof remains pending until matching hardware is attached.
- Fresh-machine Windows/macOS portability proof remains outside this Branch B
  worktree verification.
