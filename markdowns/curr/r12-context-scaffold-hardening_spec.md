> STATUS: IMPLEMENTED AND VALIDATED - active scaffold contract for Wave 2.

# R12 Context Scaffold Hardening

## Goal in plain English

Harden the already-landed R12 Branch B context scaffold before Wave 2 builds on
it. The current model-native skill and compact-tool-index work is directionally
right, but the scaffold still has product-boundary and prompt-usability gaps:
product skills must not load from `.codex/skills`, installed skills must be
client-owned read-only assets, provider recovery must happen only in runtime
copies, skill-load failures must be provider-visible and actionable, compact
tool indexes need an on-demand full-detail path, invalid tool calls should
auto-return focused tool details, and the prompt bundle should have one
canonical ordering/dedupe pipeline for the context surfaces that already exist.
The compact indexes are discovery surfaces only: if a governed tool, client
script, or brain-owned compound action has not had its details loaded in the
current session, the brain must block execution, auto-load the relevant details,
and ask the provider for a fresh decision.

This spec also records future documentation requirements for codebase map,
memory cadence, real product skills, and client-owned bug reporting, without
making the global bug-report registry a prototype implementation requirement.

Task: R12 context scaffold hardening: client-owned model-native skills,
runtime-copy recovery, tool detail loading, prompt ordering, and future bug
reporting.
Roadmap anchor: R12 Stage 5 prototype, Branch B hardening plus Module G
preconditions.

## Scope and non-scope

In scope:

- Replace the default model-native skill source root with a product/client-owned
  root, not `.codex/skills`.
- Keep installed model-native skill packages read-only from the provider's
  perspective.
- Copy each loaded skill package into the provider runtime before reading
  context files or running init scripts.
- Run init scripts and read context files from the runtime/session copy, not the
  installed source package.
- Preserve dependency closure, dependency-first post-order init, de-duping, and
  cycle detection from the existing `load_skills` design.
- Return structured provider-visible `load_skills` failures for bad manifests,
  missing files, dependency cycles, blocked init scripts, init timeouts, and
  non-zero init exits.
- Prompt recovery choices after a failed skill load: choose another skill,
  continue without it, edit the runtime copy and retry, or reset the runtime
  copy from source and retry. Source skill mutation is not an allowed recovery.
- Preserve detailed failure information in existing run events/artifacts where
  that mechanism already exists.
- Add a `load_tool_details(tool_names=[...])` context-expansion decision that
  lets the model pull one or more full governed-tool descriptions and input
  schemas after seeing the compact tool index.
- Add a detail-required execution guardrail: governed tools, governed
  tool-scripts/client actions, and brain-owned compound actions such as
  `run_green_check` cannot execute until the brain-owned loaded-detail flag for
  that object is true in the current session.
- Add a soft prompt reminder that the provider should load details before using
  any governed tool, governed script, or brain-owned compound action.
- When the provider violates that soft guardrail, the brain should fail closed:
  do not execute the requested action, auto-load the focused details, record the
  guardrail event, and ask for the next provider decision with those details in
  context.
- Automatically include focused full tool details in the retry context when a
  governed tool call fails argument/schema validation.
- Implement prompt ordering and de-dupe now for surfaces that already exist:
  skill index, governed-tool index, loaded tool details, loaded model-native
  skill context, provider memory when configured, and turn context.
- Classify failures at the provider/adapter boundary accurately enough to
  distinguish provider transport/runtime failure, invalid provider output,
  FirmCLI parser/schema bug, FirmCLI adapter/state bug, governed tool failure,
  and context-expansion failure.
- Remove prompt bundle compatibility aliases after callers/tests use canonical
  names.
- Update docs so Wave 2 codebase-map work plugs into this scaffold rather than
  re-deciding it.
- Add a future-facing client-owned bug-reporting/telemetry spec entry, marked
  non-prototype and dependent on later remote/backend infrastructure.

Out of scope:

- Implementing first-boot `codebase_map.md` creation in this pass.
- Implementing map maintenance turns in this pass.
- Implementing memory every 10 turns beyond preserving the already-existing
  configured provider-memory injection behavior.
- Implementing the full product skill library. This pass fixes the loader and
  prompt substrate; later branches can add real product skills.
- Implementing a global all-bugs report folder, upload pipeline, backend sync,
  maintainer dashboard, or remote telemetry flow.
- Letting provider code mutate installed/client skill source packages.
- Reintroducing governed host file, edit, build, or generic shell actions.
- Switching the governed decision format to provider-native tool calls.
- Adding generic host execution to the brain or MCP server.

## Immediate-vs-future split

Implement now:

- product/client-owned skill root and no `.codex/skills` default;
- read-only installed skills;
- runtime skill package copies before init/context;
- structured skill-load failures and recovery prompt text;
- existing event/artifact capture of skill-load failures;
- `load_tool_details` context expansion;
- brain-owned loaded-detail flags and details-required guardrails for governed
  tools, governed scripts/client actions, and brain-owned compound actions;
- invalid governed-tool argument failures auto-inject focused tool details;
- canonical prompt ordering/dedupe for current context surfaces;
- provider/adapter failure classification;
- prompt bundle alias cleanup.

Document now, implement later:

- codebase map first-boot generation and bounded maintenance turns;
- codebase map full-body loading only when explicitly loaded or when workflow
  skills require it;
- memory cadence and summarization beyond the current provider-memory sync hook;
- actual shipped product workflow skills;
- global client-owned bug-report registry, local all-bugs index, offline
  retention, and backend upload/review workflow.

Prompt ordering/dedupe is partly immediate and partly future. The current
implementation already has skill index, compact tool index, loaded skill
context, and provider memory surfaces, so the ordering/dedupe policy for those
surfaces should be implemented now. The future codebase-map and memory cadence
slots should be reserved in the same ordering contract but remain no-op until
their branches land.

## Reconciliation summary

- Build plan: Stage 5 already says host-local work is provider-native, large
  static prompt bodies should not be reprinted every turn, the prompt should use
  compact tool/skill indexes and on-demand bodies, `load_skills` is a
  context-expansion decision, and Wave 2 Module G owns static-context efficiency
  plus codebase-map scaffolding.
- Current code: `src/pyocd_debug_mcp/brain/loop.py` still sets
  `MODEL_NATIVE_SKILL_ROOT = REPO_ROOT / ".codex" / "skills"`, which points at
  operator Codex skills instead of product/client skills. `model_native_skills.py`
  resolves manifests from the source folder, copies only declared
  `usable_paths`, runs init scripts from source, and reads context files from
  source. It raises `ModelNativeSkillError` for blocked or broken loads and the
  loop stores only the string failure. `tool_schemas.py` renders a compact
  governed-tool index while retaining full input schemas internally, but there
  is no `load_tool_details` decision or automatic schema return after invalid
  tool arguments. `ProviderPromptBundle` still exposes compatibility aliases
  `render_native_delta_text` and `render_native_sync_text`.
- Current code does not enforce detail-required execution. A provider can call a
  governed tool or `run_green_check` after seeing only the compact index and a
  few instruction lines. Client actions can be run by name after the client
  action prompt section is exposed, without a separate brain-owned loaded-detail
  flag.
- Other docs or notes: `things-to-change.md` entry #3 and Prototype Priority
  #14 require skill index/on-demand bodies; Prototype Priority #15 and
  `wave2-codebase-map_spec.md` require the codebase map in Wave 2 Module G; the
  user's clarified product boundary says `.codex/skills` are the agent
  operator's skills, not the FirmCLI client's model-native product skills.
- Disagreements: no settled build-plan decision conflicts with this spec. This
  spec tightens the current implementation to match the build plan and the
  user's clarified product boundary. The only scheduling distinction is that
  global bug reporting is documented for later remote/backend work, not
  implemented in the prototype scaffold.

## Design

### Product skill root

The model-native skill registry must default to a FirmCLI product/client skill
root, not `.codex/skills`. The prototype may choose a stable repo-local root
such as `skills/model_native/` while leaving a later config override hook. The
important boundary is semantic: installed model-native skills are client-owned
application assets. `.codex/skills` and `.claude/skills` are operator/developer
workflow assets and must not be the runtime source of product skills.

The selected source root should be recorded in state/events and testable. If the
root is missing or a requested skill is absent, `load_skills` should fail as a
context-expansion failure with a clear provider-visible message.

### Installed source vs runtime copy

Loading a skill has two paths:

- installed source package: durable, client-owned, read-only to provider;
- runtime/session copy:
  `<provider_runtime>/skills/<skill_id>/`, client-created and provider-editable
  for that run/session only.

For every newly loaded skill, the loader should copy the controlled package
contents needed for manifest, context, init, usable scripts/assets, and
references into the runtime copy before init or context injection. The manifest
stored in session state should preserve source provenance and runtime path.
Init scripts must run with a deterministic working directory inside the runtime
copy. Context files injected into prompts must be read from the runtime copy.
Usable scripts/assets exposed to the provider must be namespaced under that same
runtime copy.

If a runtime copy already exists for a failed load retry, the provider may edit
that runtime copy and retry. The source package is never changed by provider
recovery. A reset-from-source action may be supported as a brain/client operation
that replaces the runtime copy with the installed source package before retry.

### Graceful skill-load failures and recovery

`load_skills` must return structured results for both success and failure. A
failure should include:

- requested skill IDs;
- resolved dependency chain so far;
- failed skill ID;
- failure category, such as `missing_skill`, `bad_manifest`,
  `dependency_cycle`, `missing_context_file`, `missing_usable_path`,
  `policy_blocked_init`, `init_timeout`, or `init_failed`;
- source path and runtime path when known;
- failed manifest/file/script path when relevant;
- init stdout/stderr and exit code when a script ran;
- concise message safe for provider prompt context;
- allowed recovery choices.

After a failed load, the next provider turn should clearly say:

- installed skills are client-owned and read-only;
- the provider may inspect or edit only the runtime/session copy;
- it may retry `load_skills` after editing the runtime copy;
- it may choose another skill;
- it may continue without the failed skill;
- it may request reset-from-source if that operation exists.

The prototype should preserve failure detail in existing run events/artifacts.
It should not build a new global bug registry yet.

### Tool details as context expansion

The compact governed-tool index remains the default prompt surface. It should
continue to include tool names, short descriptions, required/optional argument
hints, and stable response/refusal semantics. It is a discovery/index layer, not
the full reference.

Add a context-expansion action:

```json
{
  "kind": "load_tool_details",
  "tool_names": ["flash_firmware", "read_memory"]
}
```

This action is not a board/server action and does not execute the tool. It asks
the brain to inject full governed-tool details into the next provider turn.
Details should be sourced from live MCP metadata and the retained internal
schema records, and should include:

- full tool name and description;
- full input schema;
- required and optional fields;
- enum/default/const constraints where present;
- response/refusal/block semantics;
- side-effect/risk notes where known;
- schema hash/provenance.

State should track loaded tool details and de-dupe repeats. Multiple tool names
in one action should load as one context-expansion result.

### Detail-required execution guardrail

Indexes are not execution authorization. The brain should maintain
session-scoped, brain-owned loaded-detail flags for every object whose execution
can touch hardware, execute governed client code, or run a brain-owned compound
operation. The provider may request details, but it cannot set or spoof the
flags.

At minimum, track:

- governed MCP tool details by tool name and MCP schema hash;
- governed client-action/tool-script details by action name and content hash;
- brain-owned compound-action details by action name and contract hash, starting
  with `run_green_check`;
- loaded model-native skill context by skill ID and content hash.

The always-allowed decisions from the compact index are the context-expansion
actions (`load_tool_details`, `load_skills`), ordinary bounded `wait`, and
`finalize` subject to existing finalization rules. `load_skills` itself remains
callable from the skill index because it only loads model-native context; any
future skill-specific executable action must require that skill's context flag.

If the provider requests a guarded action whose loaded-detail flag is false, the
brain must not execute that action. It should instead:

1. record a details-required guardrail event and state update;
2. auto-load the focused details for the requested object where possible;
3. return a provider-visible block such as
   `Blocked [brain/details-required]: <name> was requested before its details
   were loaded. Details are now loaded; choose the next decision.`;
4. include those details in the next provider turn;
5. require the provider to emit a new decision.

The brain must not auto-load details and then execute the original call in the
same step. The missing-detail call failed the soft guardrail, so execution waits
for a fresh provider decision made with the full details visible.

For governed MCP tools, the auto-loaded detail is the same full schema/provenance
block loaded by `load_tool_details`. For client actions and tool scripts, the
loaded detail should include the name, description, content hash, input contract
or accepted input shape, whether it can call governed server tools, and any
side-effect/risk notes the client action store can derive. For `run_green_check`,
the loaded detail should explain that it is a brain-owned compound verification
action over build/flash/read-register/read-serial behavior, its required
preconditions, expected artifacts, and success/failure semantics.

When a governed tool call fails validation because of missing, extra, or invalid
arguments, the brain should automatically include focused full details for that
tool in the retry context. This preserves compact ordinary prompts while making
self-correction practical.

### Prompt ordering and de-dupe

Prompt assembly should have one canonical ordered pipeline for current and
future static/dynamic context. For the current scaffold, implement:

1. invariant safety and action-boundary rules;
2. compact skill index;
3. compact governed-tool index;
4. loaded tool details, de-duped by tool name and schema hash;
5. loaded client-action/tool-script details, de-duped by name and content hash;
6. loaded brain-owned compound-action details, de-duped by action and contract
   hash;
7. loaded model-native skill context, de-duped by skill ID and content hash;
8. provider memory when the configured provider/session policy injects it;
9. turn-specific context and prior brain result;
10. decision schema.

Reserve future slots for:

- codebase-map rule/path/hash/summary on normal turns;
- full codebase map body on explicit codebase-map loads or workflow skill turns;
- memory cadence/summarization beyond the current provider-memory surface.

No full MCP JSON schema body should be reprinted every ordinary turn. Full tool
details appear only after explicit `load_tool_details` or invalid-call
auto-detail injection. Full client-action/tool-script details and brain-owned
compound-action details appear only after explicit detail loading or a
details-required guardrail block. Multiple skill loads, tool-detail loads, or
auto-loaded detail blocks in one turn must not duplicate bodies.

### Failure classification and aliases

Broad `except Exception` boundaries may remain at the outermost artifact
preservation points, but events/results should classify failures accurately:

- provider transport/runtime failure;
- invalid provider output;
- FirmCLI parser/schema bug;
- FirmCLI adapter/state bug;
- governed tool execution failure;
- context-expansion failure.

Prompt bundle compatibility aliases should be removed after callers and tests
use canonical names. Keeping old names while adding more context surfaces makes
prompt assembly harder to reason about.

### Future client-owned bug reporting

This pass should not implement a new bug-report registry. The docs should define
the later product feature:

- client-owned local report root;
- all-bugs index/registry;
- report categories covering skill-load failures, bad manifests, blocked init,
  tool-schema mismatch, invalid provider output, adapter bugs, governed tool
  failures, board failures, and provider runtime failures;
- report payload schema;
- dedupe/grouping;
- privacy/redaction;
- offline retention;
- future backend upload after remote/account infrastructure exists;
- maintainer review workflow.

The provider may receive sanitized failure summaries in prompts, but canonical
bug reports are client-owned product/runtime artifacts, not provider-owned or
provider-editable files.

## Board-facts-as-data and origin tags

This change adds no board facts. Skill root paths, runtime paths, prompt-order
policy names, and context-expansion action names are `PROJECT-DEFINED`.

If tool details include board-affecting side-effect notes, those notes must be
derived from the existing MCP tool descriptions, guardrail semantics, or board
config and tagged in docs as provenance-bearing context, not new board truth.
The code must not add board-specific branches for skill loading, tool details,
or prompt ordering.

## Documentation plan

- Add this spec to `markdowns/curr/README.md`.
- Update `markdowns/things-to-change.md` Prototype Priority #14 and entry #3 to
  require the corrected product/client skill root, runtime-copy-only recovery,
  structured skill-load failures, `load_tool_details`, strict loaded-detail
  guardrails, invalid-call auto-details, and immediate prompt ordering/dedupe
  for current context surfaces.
- Update `markdowns/R12_P_SPLIT.md` so Branch B hardening owns the immediate
  scaffold fixes and Module G consumes them for Wave 2 codebase-map/static
  context work instead of reimplementing them.
- Update `markdowns/ROADMAP.md` and `markdowns/current-progress.md` with the
  scaffold-hardening implementation status and remaining external proof gaps.
- Update `markdowns/curr/wave2-codebase-map_spec.md` only to clarify that it
  depends on this scaffold and that full map body injection is not ordinary
  every-turn behavior.
- Add a future-facing client-owned bug-reporting spec or section in the
  backlog/docs, explicitly marked not prototype-required until remote/backend
  infrastructure exists.

## Portability

- Product skill roots and runtime copies must use `pathlib` and repo-relative or
  client-storage-relative paths where possible.
- Default product skill root is `PROJECT-DEFINED`; it must not depend on
  Windows drive letters, shell syntax, `.codex`, or `.claude`.
- Runtime copy paths live under the existing provider runtime/artifact root and
  must tolerate Windows and macOS path semantics.
- Init scripts already run with explicit timeouts; this pass must keep that
  bound and preserve UTF-8-with-replacement capture.
- Tool detail loading is prompt/context work and should not create new process,
  shell, or hardware portability surface.
- Details-required guardrail state is session-local metadata and must not be
  inferred from platform-specific paths or provider self-report.

## Verification plan

Focused unit tests:

- default model-native skill root is product/client-owned and not `.codex`;
- missing product skill root or unknown skill returns a structured
  context-expansion failure;
- skill package is copied to runtime before init/context loading;
- init scripts run from runtime copy with deterministic cwd;
- context files are read from runtime copy, so provider edits to runtime copy can
  repair a failed load without mutating source;
- installed source package remains unchanged after runtime repair;
- blocked hardware/probe init scripts produce structured provider-visible
  failure details and recovery choices;
- repeat load of already loaded skill does not rerun init;
- dependency closure, duplicate dependencies, and cycle detection still pass;
- `load_tool_details` parses one or more tool names;
- invalid tool names fail as structured context-expansion failures;
- loaded tool details include full schema and provenance and are injected next
  turn;
- repeated tool-detail loads de-dupe;
- governed MCP tool calls before their detail flag is loaded are blocked, do
  not execute, auto-load details, and require a fresh provider decision;
- `run_script` before its client-action/tool-script detail flag is loaded is
  blocked, auto-loads script details, and requires a fresh provider decision;
- `run_green_check` before its compound-action contract detail flag is loaded is
  blocked, auto-loads the contract details, and requires a fresh provider
  decision;
- auto-load-after-block does not execute the original blocked action in the same
  turn;
- invalid governed-tool arguments auto-inject focused tool details in retry
  context;
- compact tool index still omits raw `input_schema` and JSON schema bodies on
  ordinary turns;
- prompt ordering places current surfaces in the canonical order and avoids
  duplicate loaded skill/tool bodies;
- prompt bundle callers/tests use canonical methods with compatibility aliases
  removed;
- provider/adapter failure classification records the correct category.

Non-hardware smoke checks:

- no-hardware Codex `load_skills` smoke still loads a valid skill from the new
  product skill root or fails with a structured missing-skill result if no
  product skills are installed in the prototype environment;
- no-hardware Codex `load_tool_details` smoke can request full details for one
  governed tool after seeing the compact index and then finalize without board
  actions;
- invalid-argument dry-run smoke shows focused tool details in the retry prompt.

Hardware checks:

- no new board behavior is required for context-expansion mechanics;
- after implementation, the standard Branch B / Wave 1 board boundary smoke
  should rerun on the attached pair because prompt/action schemas changed;
- exact official `nrf52833dk + nucleo_l476rg` and Claude proof remain pending if
  hardware/quota is unavailable.

## Acceptance criteria

- Model-native skills no longer default to `.codex/skills`.
- Installed/client skill packages are read-only to provider recovery.
- Newly loaded skills run entirely from runtime/session copies after source
  copy.
- The provider can repair only the runtime copy and retry; source mutation is
  not a valid recovery path.
- Skill-load failures are structured provider-visible context-expansion
  failures, not opaque brain crashes.
- Existing events/artifacts preserve failure details sufficient for debugging.
- `load_tool_details(tool_names=[...])` is a valid context-expansion decision.
- One `load_tool_details` decision can load multiple tool details.
- Full tool details include complete input schemas and provenance but appear
  only when loaded or auto-returned after invalid arguments.
- Governed tools, governed client scripts/tool scripts, and brain-owned compound
  actions cannot execute from index-only knowledge; they require brain-owned
  loaded-detail flags in the current session.
- A missing-detail call fails closed, auto-loads focused details, records a
  details-required guardrail event, and asks for a fresh provider decision.
- Invalid governed-tool arguments automatically include focused tool details for
  retry.
- Prompt ordering/dedupe is canonical for existing skill/tool/memory/turn
  surfaces, with future codebase-map/memory slots reserved.
- Prompt bundle compatibility aliases are removed after canonical names are in
  use.
- Provider/adapter failures are classified accurately enough for run artifacts
  and later bug reporting.
- Codebase-map and global bug-reporting requirements are documented for future
  branches without being claimed implemented.
- Removed host actions remain absent from valid `TurnDecision` variants.
- Board/server actions remain governed by the brain; no generic host execution
  is added to the brain or MCP server.

## Verified

- Spec reconciled on 2026-06-30 against the build plan, `things-to-change.md`,
  `R12_P_SPLIT.md`, `wave2-codebase-map_spec.md`, and the current code modules
  `loop.py`, `model_native_skills.py`, `tool_schemas.py`, and
  `provider_types.py`.
- Implemented in the R12 brain scaffold: product-owned default skill root,
  runtime skill copies, structured skill-load failures, `load_tool_details`,
  loaded-detail state, details-required guardrails for governed MCP tools,
  governed client actions/scripts, and `run_green_check`, invalid-call focused
  details, canonical prompt surfaces, provider/action failure classification,
  and prompt bundle alias cleanup.
- Focused tests were added/updated in `tests/test_r12_turnkey.py`,
  `tests/test_model_native_skills.py`, and `tests/test_p0_foundation.py`.
- Final validation in the 2026-06-30 scaffold/audit pass: Python-change gate
  green with Pyright `0` and full pytest green; suite ladder green; real MCP
  smoke green; Codex live multi-turn smokes green; attached-board checks green
  on `nucleo_l476rg` and `nrf52840dk`.

## Pending verification

- Claude CLI proof remains external-provider blocked in this environment until
  login/quota is available.
- API-provider parity proof remains pending until credentials are available.
- Exact official `nrf52833dk` proof remains pending until that board is
  attached; this pass used the attached `nrf52840dk` retained Nordic board.
- Fresh-machine deployment proof remains pending.
- Future client-owned bug reporting remains design-only until remote/backend
  infrastructure exists.
