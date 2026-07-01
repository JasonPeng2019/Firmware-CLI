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

Run IDs in this file are historical evidence pointers. The `runs/` tree is
gitignored runtime output, so older run directories may be absent from a fresh
or cleaned checkout; absence of a referenced run folder means the artifact
cannot be reinspected locally, not that the status line has been re-proven in
the current session.

## Current Position

Current correction, 2026-06-30: do not treat the Wave 1 A/B/C prototype merge
as fully product-suite complete. Branch A is acceptable for the
provider-session/compact-tool-index bridge, Branch C is acceptable for the
event/timeout-policy slice, and Branch B's free host-work phase followed by one
final governed board/client/terminal decision is now implemented in code.
Codex CLI has live proof for that Branch B boundary on the attached
`nucleo_l476rg + nrf52840dk` pair. Claude CLI is also no longer blocked on the
current host for attached-board provider/hardware checks: after local auth was
restored, Branch C passed on both attached boards. Exact official `nrf52833dk`
proof remains pending.

Follow-up correction, 2026-06-30: the turnkey MCP tool prompt injection no
longer repeats full MCP JSON schema bodies. The brain now renders a compact
curated tool index from live MCP metadata: tool name, short description,
required/optional argument hints, and stable response/refusal semantics. The
actual MCP descriptors still retain their full input schemas for validation and
provenance.

Adversarial audit correction, 2026-06-30: the Branch B model-native skill loader
now preflights init scripts before subprocess execution. Init scripts that
directly import known probe/serial stacks or invoke known board/probe commands
are rejected before they can bypass governed server tools, and skill manifests
must declare the same `skill_id` as the requested skill folder. A later
scaffold-hardening pass then closed the broader context-boundary gaps: product
skill roots no longer default to `.codex/skills`, skill packages are copied to
runtime before init/context, skill-load failures are structured, compact indexes
are discovery-only, `load_tool_details` can load full schemas, and governed
tools, governed client actions/scripts, and `run_green_check` require
brain-owned loaded-detail flags before execution. A missing-detail call blocks,
auto-loads focused details, records the guardrail, and asks for a fresh provider
decision. Final validation for that pass: Python-change gate green with Pyright
`0` and full pytest green; suite preset green; real MCP smoke green; Codex
host-native/load-details/live multi-turn smokes green; attached-board checks
green on `nucleo_l476rg` and `nrf52840dk`. The remaining loader risk for a
future product launch is packaging/config drift, not the current design:
deployable packages must preserve the product/client-owned skill root, runtime
copy before init/context, read-only installed skill source, and init-script
preflight that blocks raw probe/serial imports or board/probe shell commands.

Wave 2 planning update, 2026-06-30: client-side codebase-map scaffolding is now
specified in `markdowns/curr/wave2-codebase-map_spec.md` and assigned to Module
G static-context work. It is not implemented. The spec requires first-boot
`codebase_map.md` creation, per-turn map rule/path/hash/summary, full map
injection once for workflow skill turns, and a bounded map-maintenance subturn
after provider-native file changes before the next governed action is trusted.

Scaffold-hardening implementation update, 2026-06-30: the current Branch B
model-native skill/tool prompt scaffold now implements the product-boundary work
required before Wave 2 builds on it. The active contract is
`markdowns/curr/r12-context-scaffold-hardening_spec.md`: product/client-owned
model-native skill root instead of `.codex/skills`, read-only installed skills,
runtime-copy-only provider repair, structured skill-load failures and recovery
prompts, `load_tool_details`, invalid-tool-call auto-details, strict
loaded-detail guardrails before governed tool/script or brain-owned
compound-action execution, canonical prompt ordering/dedupe for existing context
surfaces, provider/adapter failure classification, and prompt bundle alias
cleanup. Remaining scaffold proof gaps are external: API-provider credentials,
exact official `nrf52833dk` proof, and fresh-machine deployment. Claude CLI
attached-board proof is green again on this host after authentication was
restored.

Delta-index follow-up, 2026-06-30: ordinary remote-primary `remote-delta`
provider turns now include the compact skill context and compact governed-tool
index in addition to the current turn context. This does not change compact
memory cadence: provider memory still syncs only according to
`--native-sync-every` / `PYOCD_TURNKEY_NATIVE_SYNC_EVERY` and defaults to every
10 provider turns. Full MCP input schemas and the full `TurnDecision` schema
remain out of ordinary `remote-delta` turns; they are still used for bootstrap,
sync, retry, or explicit/focused detail-loading paths. Verification for this
follow-up is recorded in
`markdowns/curr/r12-delta-compact-indexes_spec.md` and
`markdowns/tmp/curr-archive-20260630-delta-index-final/wave1-delta-index-adversarial-audit_process.md`.

Prompt/memory cost hardening update, 2026-07-01: the turnkey prompt path now
separates bootstrap/full task context from the compact canonical later-turn
state. Normal provider turns render a Tier 0 brain-owned digest with task
contract, loaded-detail status, latest evidence, changed files, blockers, and
available action kinds, while bootstrap/retry/sync modes keep the larger context
where it is useful. Provider memory defaults to the last two detailed committed
turns plus a hard-limited rolling summary, summary-mode prompts are explicitly
non-actionable, and overlong model summaries are rejected instead of silently
trimmed. The run artifacts now record rendered-vs-available prompt accounting
with per-section hashes and explicit `memory_injected`,
`decision_schema_injected`, and `static_tool_schema_injected` booleans, so
debugging can distinguish "state exists" from "state was actually sent to the
provider." Common safe details for `connect` and `run_green_check` preload by
default to avoid avoidable `details_required` turns; the behavior is
configurable with `--recent-turn-detail-limit`,
`--memory-summary-max-chars`, `--no-preload-common-details`, and matching
`PYOCD_TURNKEY_*` env vars. Follow-up audit during live benchmark repair found
two additional valid prompt-cost gaps and closed them: loaded detail bodies now
render only on the preload/detail-load turn or the immediate following
context-expansion turn, and selected turnkey skill facts render in full only at
bootstrap/sync while ordinary remote-delta turns carry a compact skill digest.
Post-fix live b001 repair proof is green on `nucleo_l476rg` and `nrf52840dk`
with both `codex-cli` and `claude-cli`; ordinary post-detail decision/finalize
turns in those runs were about 7.3k-7.8k rendered chars with no provider-memory
or decision-schema injection. Follow-up credentials-free API simulation now
also exercises the real `openai-api` and `anthropic-api` provider factory plus
`run_turnkey_with_provider` paths: OpenAI Responses-style
`previous_response_id` chaining, Anthropic local-memory-only continuation,
request/response handling, prompt render modes, retry/error surfaces, and
prompt accounting are covered without live API credentials. This feature still
does not add cross-invocation provider-session persistence.

The first capability prototype is complete only when every Prototype Priority
item in `markdowns/things-to-change.md` is implemented, mapped to code/tests,
and validated. Agents must not use passing subset tests or narrower branch
definitions to call the product done.

In roadmap terms, all scoped work through `R11` is implemented for the
official board pair:

- `nrf52833dk`
- `nucleo_l476rg`

Historical live proof already exists for the scoped pair through `R11`, and
the latest mixed-board macOS rerun has now re-proved both scoped boards
through Stage 0 and Stage 1. That means the remaining work is no longer in the
shared hardware substrate; it is in the turnkey product layer and the broader
cross-host portability claims.

Unless a later status entry explicitly widens it, the portability claim should
be read as post-bootstrap portability: supported hosts plus supported boards
after a short documented developer bootstrap equivalent to normal manual-debug
setup, not "every board on every machine with zero manual setup."

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
- multiple decision-provider backends:
  - native OpenAI API
  - native Anthropic API
  - Codex CLI
  - Claude Code CLI
- the sibling turnkey benchmark path over the same 12-case corpus
- the frozen `R12` contract in `markdowns/curr/r12_turnkey_spec.md`
- the imported Pass 1 event/UX shell scaffold from `main`, which is now on
  this branch but should still be cleaned up before further P0 prototype work

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

What is still missing for broad turnkey closure is exact official-pair
second-provider proof on an actual `nrf52833dk + nucleo_l476rg` pair,
live API-provider proof, and fresh-machine portability proof. Credentials-free
API simulation is green through fake SDK clients and real provider-loop code
paths, but that is not the same as paid/live provider proof. Claude CLI is no
longer globally blocked: later Branch A/B ledger evidence records post-refresh
attached-board Claude proof on `nucleo_l476rg + nrf52840dk`.

What is still missing for true user-computer deployment is broader than the
current prototype gate:

- fresh Windows and macOS host proof;
- multiple top-level prompts in one operator CLI session, each with its own
  bounded provider/tool loop and isolated run artifacts; sequential
  `pyocd-debug-brain run` prompts have attached-board proof, but one-shell
  interactive `pyocd-debug` proof remains pending;
- strict provider-session handling, including fail-closed behavior when a
  promised remote handle cannot resume;
- real code-writing repair proof on the bug-repair cases, with build/flash/green
  evidence and no cross-prompt state leakage;
- live Anthropic/OpenAI API proof before claiming parity with Claude Code CLI or
  OpenAI Responses in production.
- memory continuity now relies on provider-native resume where available plus
  the compact brain-owned memory ledger; remote-primary providers receive a
  periodic safety sync every 10 provider turns by default, configurable with
  `--native-sync-every` / `PYOCD_TURNKEY_NATIVE_SYNC_EVERY`.

Latest Branch A/B live-provider refresh proof on 2026-06-29:

- the Claude quota-blocked handoff was resumed after the five-hour window
  refreshed
- the non-hardware suite ladder passed after the final provider-shape fix:
  `324` pytest tests, ruff, mypy, `34` R11 benchmark tests, and R11 benchmark
  help
- the attached boards were proven as `nucleo_l476rg + nrf52840dk`
- `nrf52833dk` was not attached for official closure: the Nordic probe/serial
  matched, but Stage 0 read FICR `0x52840` where the official `nrf52833dk`
  config expects `0x52833`
- `claude-cli` completed real code-writing repair prompts on both attached
  boards:
  - `nucleo_l476rg__b001_wrong_boot_text` -> `FULL_SUCCESS`
    (`20260629T181445Z-83140ead`)
  - `nucleo_l476rg__b002_wrong_known_value` -> `FULL_SUCCESS`
    (`20260629T181858Z-13304c13`)
  - `nrf52840dk__b001_wrong_boot_text` -> `FULL_SUCCESS`
    (`20260629T182216Z-476ebc86`)
  - `nrf52840dk__b002_wrong_known_value` -> `FULL_SUCCESS`
    (`20260629T182622Z-a0ef098b`)
- `codex-cli` completed the same attached-board comparison repair prompts:
  - `nucleo_l476rg__b001_wrong_boot_text` -> `FULL_SUCCESS`
    (`20260629T182803Z-f6063c6a`)
  - `nucleo_l476rg__b002_wrong_known_value` -> `FULL_SUCCESS`
    (`20260629T183109Z-d90d0f9b`)
  - `nrf52840dk__b001_wrong_boot_text` -> `FULL_SUCCESS`
    (`20260629T183358Z-85305768`)
  - `nrf52840dk__b002_wrong_known_value` -> `FULL_SUCCESS`
    (`20260629T183719Z-39a93fff`)
- the public client-action smoke passed on the final fixed branch state:
  `codex-cli + nucleo_l476rg`, session `20260629T181205Z-d502704c`,
  `HEALTHY_CONFIRMED`, with `uart_write` recorded as executed
- a live provider-shape gap found during that smoke was fixed: legacy
  `server_tool` batch calls with nested `arguments.arguments` are now unwrapped
  before MCP invocation, and conflicting duplicate arguments fail closed
- the process ledger records representative artifacts showing provider remote
  resume handles and no recovery-created replacement provider sessions
- current workspace audit note: the Branch A `20260629T03...`, `04...`,
  `17...`, and `18...` run directories named above are not present in local
  `runs/`; these run IDs are retained as historical ledger evidence, but the
  specific artifacts cannot be reinspected from this checkout until restored

Latest Wave 1 A/B/C merge-back validation on 2026-06-30:

- `P-Wave-C` event/timeout work has been selectively merged into the current
  `P-Wave-A` spine that already carried Branch A and a Branch B subset.
- The merge keeps Branch A provider/session/schema behavior, Branch B
  additive action-boundary/batch/wait/client-action behavior, and Branch C
  event-spine/timeout-policy/server-sync behavior in one loop. It does not close
  the Branch B hard bar because free host work is still governed as actions
  instead of being model-native until the final board/terminal decision.
- Non-hardware validation passed after the final harness fix:
  - focused A/B/C suite: `121 passed`
  - Branch C no-hardware harness: `4 passed, 0 failed, 0 skipped`
  - full pytest: `338 passed`
  - ruff check/fix and ruff format passed
  - mypy over `src`: passed
  - R11 benchmark tests: `34 passed`
  - `python -m tests.harness.r11_benchmark --help`: passed
- The historical A/B/C merge pass still predated the Pyright cleanup and used a
  changed-file Pyright filter. A later June 30, 2026 cleanup burned the
  repo-wide Pyright baseline down from `95` diagnostics to `0`; full
  `uv run pyright --outputjson` is now green across 105 analyzed files.
- Live hardware substrate proof passed on the attached boards:
  - `nucleo_l476rg`: `host_bootstrap.py`, `stage0_check.py`, and
    `tests.harness.stage1_smoke`
  - `nrf52840dk`: `host_bootstrap.py`, `stage0_check.py` with recover test,
    and `tests.harness.stage1_smoke`
- Branch C live provider/hardware harness passed with both local CLI providers
  on both attached boards:
  - `nucleo_l476rg`: `codex-cli` run root
    `20260630T035533Z-13eb8716`, `claude-cli` run root
    `20260630T035604Z-1cab4775`
  - `nrf52840dk`: `codex-cli` run root
    `20260630T035749Z-166e2f98`, `claude-cli` run root
    `20260630T035823Z-4733fa03`
- Explicit two-turn deployed CLI smokes passed on both attached boards and
  both providers. Each run used turn 1 `action_batch(connect, get_board_info)`
  and turn 2 standalone `finalize`:
  - `nucleo_l476rg` + `codex-cli`: `20260630T035908Z-792e4e13`
  - `nucleo_l476rg` + `claude-cli`: `20260630T035938Z-d595f811`
  - `nrf52840dk` + `codex-cli`: `20260630T040008Z-8a79ddbf`
  - `nrf52840dk` + `claude-cli`: `20260630T040034Z-b497ea08`
- A real acceptance-harness false negative was found and fixed: Codex reached
  hardware after recovering from an unsupported batched `finalize`, but the
  Branch C harness only accepted per-tool `tool_complete` event evidence. The
  harness now also accepts `TurnkeyRunResult.mcp_tools_used`, with a focused
  regression test.
- Process cleanup audits after the live provider and hardware smokes showed no
  leftover spawned `uv`, `python`, `codex`, `claude`, `pyocd`, MCP, or debug
  helper children. The only matching long-lived process was the pre-existing
  VS Code Codex app-server.
- A follow-up adversarial audit on June 30, 2026 fixed one additional harness
  false negative: Branch C provider dry-runs now accept schema-valid
  `action_batch` decisions as well as single actions. The rerun evidence on
  the current branch was:
  - focused regression: `15 passed`
  - full pytest: `339 passed`
  - Pyright changed-file filter for the harness/test fix: `0` diagnostics at
    that time; a later June 30 cleanup made full repo-wide Pyright green
  - live Branch C harness on both attached boards with both `codex-cli` and
    `claude-cli`: `11 passed, 0 failed, 0 skipped` for each board
  - public task-file two-turn CLI smokes on both attached boards and both
    providers: `runs/20260630T043529Z-6391fd28`,
    `runs/20260630T043559Z-83135d6d`,
    `runs/20260630T043636Z-e803899e`, and
    `runs/20260630T043707Z-34dd6769`
  - cleanup audit found no new leftover spawned provider/MCP/pyOCD/validation
    children; the only matching long-lived repo MCP process was the same
    pre-existing VS Code/Codex app-server-owned tree seen before the suite
- A follow-up Pyright baseline cleanup on June 30, 2026 is now complete:
  - workflow skills and the coding playbook define full Pyright as the hard
    Python-change gate now that the baseline is green
  - `python .codex\skills\python-change\scripts\run_python_change_checks.py`
    passed: ruff check/fix, ruff format, full Pyright (`0` diagnostics), and
    full pytest (`339 passed`)
  - `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
    passed, including `339` pytest tests, ruff, mypy, `34` R11 benchmark
    tests, and R11 benchmark help
  - Branch C live provider/hardware harness reran green on both attached
    boards with both local CLI providers:
    `nucleo_l476rg` run roots `20260630T050810Z-8a1abf43` and
    `20260630T050841Z-1aaaf4a0`; `nrf52840dk` run roots
    `20260630T050814Z-ac5c22c2` and `20260630T050845Z-c42644ee`
  - public two-turn CLI smokes reran green by artifact semantics on both
    attached boards and both providers, with turn 1
    `action_batch(connect, get_board_info)` and turn 2 `finalize`:
    `20260630T050932Z-f84bc258`, `20260630T051005Z-56326461`,
    `20260630T051045Z-34e7d70e`, and `20260630T051113Z-f12e5c29`
  - cleanup audit again found no new leftover spawned provider/MCP/pyOCD or
    validation children beyond the pre-existing VS Code/Codex app-server-owned
    MCP process tree
- A deeper adversarial audit after the Pyright cleanup on June 30, 2026 found
  one valid Wave 1 product bug: final `run_turnkey` disconnect cleanup failures
  were swallowed, which could hide a failed board-session close after a model
  produced a final result. The fix now records an `unexpected_failure` event
  with phase `final_disconnect`, leaves the active `session_id` visible in
  state, and converts the run result to `blocked` / `tooling_failure`.
  Verification after that fix:
  - targeted cleanup regression:
    `uv run pytest -q tests/test_r12_turnkey.py -k "disconnect_cleanup_fails or invocation_default_timeout_for_disconnect"`
    -> `2 passed, 54 deselected`
  - `python .codex\skills\python-change\scripts\run_python_change_checks.py`
    -> ruff check/fix passed, ruff format passed, full Pyright passed with
    105 files analyzed and 0 diagnostics, full pytest -> `340 passed`
  - `python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite`
    -> full suite ladder passed, including `340` pytest tests, ruff, mypy,
    `34` R11 benchmark tests, and R11 benchmark help
  - Branch C live provider/hardware harness passed on both attached boards
    with both local CLI providers:
    `nucleo_l476rg` run roots `20260630T052616Z-4b553e39` and
    `20260630T052655Z-4e591717`; `nrf52840dk` run roots
    `20260630T052843Z-057bd52a` and `20260630T052926Z-bb4b66b1`
  - public two-turn CLI smokes passed by artifact semantics on both attached
    boards and both providers, with turn 1
    `action_batch(connect,get_board_info)`, turn 2 `finalize`, and
    `mcp_tools_used=connect,get_board_info`:
    `20260630T053014Z-2630df0f`, `20260630T053042Z-4a16f434`,
    `20260630T053111Z-eb3e6ce0`, and `20260630T053139Z-7449c301`
  - process audits before and after the gates, live harnesses, and public CLI
    smokes showed no new leftover spawned provider/MCP/pyOCD or validation
    children beyond the same pre-existing VS Code/Codex app-server-owned MCP
    process tree
- The Branch B hardbar correction pass on June 30, 2026 then removed
  model-native host work (`read_file`, `replace_file`, `run_build`) from the
  model-facing governed decision schema, refused stale host-action decisions,
  observed provider-native workspace changes at the next governed boundary, and
  rebuilt the workspace before governed `run_green_check`.
- Follow-up hard bar, also on June 30, 2026: the stale-action compatibility
  layer above has now been removed. `ReadFileAction`, `ReplaceFileAction`,
  `RunBuildAction`, their policy/refusal branches, governed executor branches,
  and prompt-visible decision language were deleted. `load_skills` is now the
  model-native context-expansion decision that loads workflow skills between
  provider turns. Verification for this pass:
  - focused model-native skill-loading tests: `9 passed`
  - Python-change gate: Ruff check/fix passed, Ruff format passed, full
    Pyright `0` diagnostics across `107` analyzed files, full pytest
    `347 passed`
  - Codex CLI no-hardware smoke passed with `load_skills:firmcli-fix-bug`,
    `mcp_tools_used=[]`, `session_id=(none)`, run root
    `runs/turnkey-20260630T084055Z-0a0377bc`
  - Claude CLI proof was pending provider quota reset at this point; later
    attached-board Claude rows are green after auth/quota was restored
  Verification after that correction:
  - suite ladder passed: full pytest `342 passed`, ruff clean, mypy clean,
    `34` R11 benchmark tests passed, and R11 benchmark help rendered
  - Python-change gate passed: ruff check/fix, ruff format, full Pyright `0`
    diagnostics across `105` analyzed files, and full pytest `342 passed`
  - attached `nucleo_l476rg` passed host bootstrap, Stage 0 flash/UART, and
    Stage 1 smoke
  - attached `nrf52840dk` passed host bootstrap, Stage 0 flash/UART/recover,
    and Stage 1 smoke
  - Branch C live harness passed with Codex CLI on both attached boards:
    `nucleo_l476rg` run root `20260630T080831Z-b996d530`; `nrf52840dk` run
    root `20260630T081021Z-31f3aaae`
  - Codex CLI code-writing `b001_wrong_boot_text` benchmark passed
    `FULL_SUCCESS` on both attached boards:
    `nucleo_l476rg` session `20260630T081152Z-0ed30757`; `nrf52840dk` session
    `20260630T081747Z-32904e64`
  - Claude CLI `nucleo_l476rg__b001_wrong_boot_text` remained blocked before
    any MCP session was created because the provider returned
    `You're out of extra usage - resets 7:30am (America/New_York)`; artifact:
    `runs/turnkey-20260630T082157Z-25e30a91`
  - post-run process audit found two new Codex-spawned `pyocd-debug-mcp`
    process trees; they were stopped by exact PID. The remaining matching MCP
    trees were the same pre-existing VS Code/Codex app-server-owned processes
    present in the baseline snapshot.

The latest Wave 0 merge-validation pass also produced a current merged-branch
proof artifact:

- `markdowns/tmp/curr-archive-20260628/p0_0_validation_report.md`

That report covers the reconciled `P-Wave-0` branch after the `main` merge,
including real stdio MCP client/server smoke, turnkey smoke, benchmark sanity,
and timeout-recovery checks on the attached `nrf52840dk + nucleo_l476rg` pair.
It does not replace the historical scoped-pair truth for `nrf52833dk`; it is
the current merged-branch proof for the hardware that was attached in that
session.

For the current prototype branch plan, the active execution boundary is
narrower:

- treated as current attached-board proof: Codex CLI and Claude CLI on
  `nucleo_l476rg + nrf52840dk`, with exact `nrf52833dk` still pending
- treated as deferred, unverified prototype risk: API-provider parity and true
  fresh-machine Windows/macOS portability proof

They should not be claimed as working, but they also are not immediate blockers
for Wave 0 / `P0.0` unless the team explicitly restores them as hard gates.

The active prototype direction has also moved beyond the original narrow R12
acceptance layer. The current docs now track a capability prototype that adds
persistent provider sessions, free host-side model work with a final governed
board-decision boundary, compact real tool metadata, batched actions with `wait` and
UART write, live progress/inspector output, timeout hardening with
model-refined budgets, session-scoped client actions, scoped green approval via
model-made flipped tests, stream checkpoints for UART/build/client-action
flows, static-context/cache efficiency including client-side codebase-map
scaffolding, and the existing compact memory ledger with configurable periodic
native memory sync. Those items are planned prototype work unless a later status
entry says they have been implemented and verified.

The remaining proof work before making the broader "fresh customer machine"
portability claim is now narrower and currently deferred for the prototype:

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
    `unique_id` / `PYOCD_PROBE_UID`, the server now resolves through the pyOCD
    Python API path only
  - if that API path yields a UID, the server uses it for the attach
  - if the API path yields nothing, the server passes `unique_id=None` through
    to the shared backend rather than falling back to the subprocess probe-list
    path on this host
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
- `src/pyocd_debug_mcp/brain/playbooks.py`
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
- now uses one unified hybrid provider-continuation model:
  - `openai-api` is `remote-primary` through Responses
    `previous_response_id`, with strict typed resume-failure handling and
    periodic safety sync
  - `claude-cli` is `remote-primary` through real `--resume <session_id>`
    reuse with `--fork-session` retries and strict resume-failure handling
  - `codex-cli` is `remote-primary` through real `codex exec resume
    <thread_id>` reuse with same-thread correction retry and strict
    resume-failure handling
  - `anthropic-api` remains `local-primary` because the current Anthropic
    Messages API surface is stateless and does not expose a resumable
    conversation handle

It also:

- selects board-aware YAML skills
- keeps local turnkey run state
- supports freeform `run` mode and benchmark mode
- captures turnkey artifacts into the same `runs/<session_id>/...` tree
- persists typed evidence inside `turnkey_state.json`
- reuses the existing 12-case benchmark corpus instead of inventing a second
  benchmark taxonomy
- keeps deterministic repair/health-check helper playbooks in a separate
  internal layer rather than overloading the prompt-skill YAMLs

Provider integration direction:

The current CLI resume adapters are the working subscription-backed bridge, not
the final high-reliability provider interface. The final provider direction is
to keep this repo's brain-owned adapter protocol and move each subscription
provider to its best programmable session surface:

- Codex: SDK/app-server style thread and turn APIs.
- Claude: Claude Agent SDK session APIs.

If a run mode promises one continuous provider session, failed resume should be
a hard failure or explicit operator decision. Silent fresh-session fallback is
only acceptable in a labeled recovery mode.

Expected policy for deployment hardening:

- headless `pyocd-debug-brain` fails closed on provider resume failure by
  default;
- interactive `pyocd-debug` asks the operator to retry resume, start a new
  provider session from saved local memory, or abort;
- any recovery-created provider session is labeled as new in events and run
  artifacts;
- `anthropic-api` is not treated as a real-session provider because its
  continuity is currently brain-owned memory rather than provider-owned resume.
- Future memory hardening for `anthropic-api` may revisit stronger recovery
  memory after the current prototype.

Claude provider policy:

- `claude-cli` remains the safest current subscription-backed Claude path. It is
  a BYO local Claude Code integration: the user installs and authenticates
  Anthropic's official CLI, and this app invokes that local executable.
- `anthropic-api` is the API-key-backed Claude path. It does not provide a
  Claude Code-style session; it relies on the brain's compact memory and
  compaction layer.
- Future Claude Agent SDK work should be treated as API-key/approved-partner
  work. Do not claim Claude subscription/rate-limit support through SDKs unless
  Anthropic approves that product shape.

## Live Bench Facts

These are the current real bench facts that were proven on the Mac and Windows
hosts used for the scoped validation.

### `nucleo_l476rg`

- probe UID: `0668FF514988525067213913`
- serial port: `/dev/cu.usbmodem144403`
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

- benchmark runner and score contract in `tests/harness/r11_benchmark.py`
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

The second-provider path is no longer globally blocked. Current status is:

- historical pre-upgrade macOS `--model sonnet` attempts failed before board
  action
- current local provider-upgrade sanity is green for:
  - direct Claude transport bootstrap/resume/fork probes
  - direct Codex transport bootstrap/resume probe
  - `pyocd-debug-brain run --provider claude-cli --model sonnet --board-id nucleo_l476rg`
  - `pyocd-debug-brain run --provider codex-cli --board-id nrf52833dk`
  - `pyocd-debug-brain benchmark --provider claude-cli --model sonnet --case-id nucleo_l476rg__k001_reference_green`
  - `pyocd-debug-brain benchmark --provider codex-cli --case-id nrf52833dk__k001_reference_green`
- current Branch A/B ledger evidence records Claude CLI attached-board proof on
  `nucleo_l476rg + nrf52840dk`, including code-writing repair prompts after
  the 2026-06-29 quota refresh
- the remaining gaps are exact official-pair closure, paid API-provider parity,
  and fresh-machine portability, not basic Claude CLI provider usability
- local audit caveat: the Branch A `20260629T03...` / `04...` / `17...` /
  `18...` run folders cited by the active Branch A/B process ledger are not
  present in this checkout's `runs/` directory

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
- the Claude attached-board repair matrix is recorded as complete for
  `nucleo_l476rg + nrf52840dk`
- the turnkey layer remains open for exact official-pair closure and paid
  API-provider parity

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

Branch B subset deployment proof exists on this Windows host for the attached
pair `nucleo_l476rg + nrf52840dk`. This evidence is retained because it proves
the additive batch/wait/UART/client-action surface, but it is not Branch B
completion proof under the current prototype bar:

- non-hardware ladder passed after adding the public client-action path:
  `uv run pytest -q`, `uv run ruff check .`,
  `uv run mypy src tests/harness/stage1_smoke.py tests/harness/r11_benchmark.py`,
  `uv run pytest -q tests/test_r11_benchmark.py`, and
  `uv run python -m tests.harness.r11_benchmark --help`
- focused Branch B tests now cover client-action loading, CLI/app threading,
  prompt visibility, `run_script` execution, and `client_actions.json` audit
  metadata
- real hardware preflight passed on the attached boards:
  - `nucleo_l476rg`: `host_bootstrap.py`, Stage 0 flash/UART, and Stage 1 smoke
  - `nrf52840dk`: `host_bootstrap.py`, Stage 0 silicon identity/flash/UART/recover,
    and Stage 1 smoke after one transient post-recover attach retry
- real Codex + real MCP + public `--client-action` smoke passed on both
  attached boards:
  - `20260628T210308Z-8b42e2ce` (`nucleo_l476rg`)
  - `20260628T210353Z-79827461` (`nrf52840dk`)
- full customer-like Codex runs also passed on both attached boards through
  `--task-file`, avoiding shell quoting problems for prompts with JSON-like
  examples. Each run used multiple provider turns, edited an isolated temporary
  workspace, ran `python app.py`, then executed a governed Branch B batch
  containing `connect`, `wait`, `run_script:uart_write`, and `read_serial`:
  - `20260628T211451Z-f2bc0136` (`nucleo_l476rg`)
  - `20260628T211628Z-3d17f3d8` (`nrf52840dk`)
- repeated user-prompt / multi-loop Codex deployment proof also passed on the
  same attached pair. Each board received two separate public
  `pyocd-debug-brain run` prompts, each prompt started a real MCP subprocess
  and ran a complete provider-driven brain loop:
  - prompt 1 on each board: ordered `connect`, `wait`,
    `run_script:uart_write`, `read_serial` board batch
  - prompt 2 on each board: inspect/replace/build in an isolated temporary
    workspace, then the same ordered board batch
  - evidence was summarized in the archived Branch B status docs; the
    detailed test report is archived at
    `markdowns/tmp/curr-archive-20260628/r12-branch-b-multi-loop-real-deployment_test_report.md`
  - run roots:
    - `20260628T212402Z-9b730979` (`nucleo_l476rg`, prompt 1)
    - `20260628T212523Z-fa129f2f` (`nucleo_l476rg`, prompt 2)
    - `20260628T212604Z-e86cf36a` (`nrf52840dk`, prompt 1)
    - `20260628T212720Z-c8244c8c` (`nrf52840dk`, prompt 2)

Remaining Branch B hard gap: host-only file/shell/script work must be
model-native/free, and each provider turn must close with exactly one governed
board or terminal decision. Until that exists and is tested, Wave 1 is not
complete.
- exact `nrf52833dk` Branch B deployment proof is still pending because the
  attached Nordic board in this session identified as `NRF52840_xxAA_REV2`

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

- extend the now-working Claude CLI path from the attached
  `nucleo_l476rg + nrf52840dk` proof to the exact official scoped pair closure
  ladder:
  - healthy freeform verification on `nrf52833dk + nucleo_l476rg`
  - repair/diagnosis coverage on the official pair
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
2. Extend the second-provider ladder from the newly recorded attached-board
   Claude runs to the full official scoped pair:
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
> pair. For the current prototype boundary, that Codex-backed path is the
> required proven baseline. Full official-pair second-provider closure and the
> fresh-machine no-`NCS` portability proof are explicit deferred prototype
> risks, not the current Wave 0 gate.
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
