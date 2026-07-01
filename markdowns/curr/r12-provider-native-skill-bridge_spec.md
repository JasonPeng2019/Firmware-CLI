> STATUS: IMPLEMENTED IN CURRENT PASS - Wave 1 hard-bar feature, pending full
> product-suite hardware/API validation after code/doc sync.

# R12 Provider-Native Skill Bridge Spec

## Goal In Plain English

FirmCLI should use Claude Code and Codex native workflow features instead of
rebuilding every skill, loop, goal, and subagent primitive inside the turnkey
brain. The product contract still belongs to FirmCLI: board control, safety
gates, run artifacts, cleanup, verification, prompt memory, and fallback skill
loading remain governed by the brain. But when the selected provider is
`claude-cli` or `codex-cli`, FirmCLI should project its provider-specific
product skills into that provider's native runtime layout and prompt the agent
to invoke those skills using the provider's normal skill behavior.

The hard bar:

- FirmCLI product skill source stays client-owned and auditable.
- Claude and Codex get separate provider-native skill packages when their
  native behavior differs.
- The provider runtime gets a generated native skill view before the first
  provider decision.
- The compact skill index tells the agent which native skills exist and says to
  prefer native invocation.
- If native invocation is unavailable, fails, is not evidenced, or the provider
  is an API backend without native skill support, the agent must request
  FirmCLI `load_skills(skill_ids=[...])`, which uses the existing deterministic
  runtime-copy loader.
- Governed board/client actions remain FirmCLI decisions. Native skills may
  guide diagnosis, host work, subagents, loops, and planning, but they do not
  bypass loaded-detail guardrails, MCP schemas, recover gates, or cleanup.

Roadmap anchor: R12 Stage 5 turnkey brain, Wave 1 provider-native host work and
prompt/memory hardening, with Wave 2 Module G static-context efficiency and
workflow-skill map injection as the nearest continuation.

## Scope And Non-Scope

In scope:

- Add a provider-native skill bridge for `claude-cli` and `codex-cli`.
- Keep the canonical product skill packages under a FirmCLI-owned tree, not
  `.claude`, `.codex`, or provider global config.
- Add separate provider-native skill package variants for Claude and Codex when
  needed.
- Generate runtime native skill views into the provider working directory before
  the provider CLI is invoked.
- Prompt a compact native skill index on every relevant provider turn.
- Instruct CLI providers to invoke native skills first using their native
  mechanism.
- Preserve `load_skills` as the deterministic fallback and as the API-provider
  path.
- Add capability probing and feature flags for provider-native skill support in
  the exact noninteractive mode FirmCLI uses.
- Record projected skill source path, runtime path, provider layout, content
  hashes, feature-probe result, and prompt instructions in run artifacts.
- Treat native skill invocation as a provider-side workflow accelerator, not as
  proof that FirmCLI loaded or executed a skill.
- Add no-hardware tests for projection, prompting, feature fallback, hash
  accounting, and provider command behavior.
- Add live CLI smoke tests for Claude and Codex native skill projection when the
  local provider CLIs and auth are available.
- Add a required pre-implementation provider discovery phase using disposable
  burner skills in real provider CLI sessions. The implementation pass may not
  hardcode Codex or Claude native skill paths until this discovery pass records
  which paths and invocation forms work in `claude --print` and `codex exec`.

Out of scope:

- Replacing FirmCLI `load_skills`.
- Replacing the `TurnDecision` contract.
- Letting native skills call board tools directly.
- Trusting provider self-report as proof that a native skill loaded.
- Depending on provider-global `~/.claude`, `~/.codex`, or future user config
  for product behavior.
- Implementing a provider-native skill bridge for `openai-api` or
  `anthropic-api` in this pass.
- Implementing provider native `/loop` or `/goal` as a board-safety loop.
- Adding cross-invocation provider session persistence.
- Changing board configs, board IDs, probe routing, UART/SWD behavior, or
  hardware facts.

## Reconciliation Summary

Build plan:

- The R12 hard-bar amendment says host-local work is provider-native, not a
  governed brain action, and model-native workflow context is loaded through
  `load_skills`.
- The R12 scaffold-hardening amendment says model-native skills must load from a
  product/client-owned root, not `.codex/skills`; installed skills are read-only
  client assets; provider repair happens only in runtime copies; and
  context-expansion failures are provider-visible.
- The Stage 5 requirements say static context must stay cheap through compact
  skill/tool indexes, on-demand bodies, content hashes, and provider-native host
  work.
- The Stage 8 note says skills are the moat. The product should invest in skill
  depth and diagnosis orchestration, not only model choice.

Current code:

- `pyocd-debug-brain` is the product CLI entrypoint.
- `CodexCLIDecisionProvider` shells out to `codex exec` in a provider runtime
  working directory and resumes by Codex thread ID.
- `ClaudeCLIDecisionProvider` shells out to `claude --print --output-format
  json` in a provider runtime working directory and resumes by Claude session
  ID.
- `ProviderPromptBundle` already renders separate bootstrap, remote-delta,
  remote-sync, retry, and prompt-accounting views.
- `BrainState` tracks loaded tool details, loaded client-action details, loaded
  compound-action details, and model-native skill state.
- `load_skills` is a `TurnDecision` context-expansion action handled by
  `ModelNativeSkillRegistry`, with runtime copies, structured failures, and
  prompt injection on the next turn.
- The repo previously had data-only diagnostic YAML skills under
  `skills/common` and `skills/mcu_families`, with no shipped
  `skills/model_native` or provider-native skill package library for this
  feature. This implementation pass adds `firmcli-firmware-debug` as both a
  deterministic model-native fallback skill and a provider-native projected
  skill.

Other docs and current status:

- `r12-context-scaffold-hardening_spec.md` is implemented and validated. It
  establishes the product/client-owned skill root and runtime-copy fallback.
- `r12-prompt-memory-cost-hardening_spec.md` and its process ledger establish
  compact later-turn prompt behavior, bounded memory, and rendered-vs-available
  accounting.
- `current-progress.md` says remaining scaffold risk for future launch is
  packaging/config drift, not the current deterministic loader design.
- Official provider docs are moving targets and currently leave at least one
  Codex location ambiguity for this product design. As of this spec pass, Claude
  Code docs describe `.claude/skills`, direct `/skill-name` invocation, bundled
  skills including `/loop`, and custom commands merged into skills. OpenAI Codex
  docs say skills are available in Codex CLI, IDE extension, and app; the Codex
  skills page describes repository/user/admin skill locations under
  `.agents/skills`, `$HOME/.agents/skills`, and `/etc/codex/skills`; other
  Codex docs describe `CODEX_HOME` as containing skills and team configuration
  under a repository `.codex` directory with a `skills/` entry. Codex app docs
  say enabled skills appear in slash commands and may be invoked with `$`; Codex
  CLI docs document slash commands as interactive-session controls.

Disagreements and resolution:

- No settled build-plan decision is changed. This spec extends the already
  accepted provider-native host-work direction.
- A direct provider-native skill bridge adds provider-specific behavior, while
  the prior scaffold intentionally kept provider-independent `load_skills`.
  Resolution: native skill projection is CLI-provider acceleration; `load_skills`
  remains the FirmCLI contract, fallback, and API-provider path.
- The exact native invocation surface differs by provider and may differ between
  interactive and noninteractive modes. Resolution: feature-detect in the same
  CLI mode FirmCLI uses; when unsupported or ambiguous, fall back.
- Codex native skill storage may have changed or may differ by surface. The
  prior working assumption of `.agents/skills` is not accepted as a production
  fact until the installed `codex exec` binary proves it. Resolution: treat
  `.agents/skills`, runtime `.codex/skills` team-config style projection, and an
  isolated runtime `CODEX_HOME` skills location as probe candidates, then update
  this spec with the observed result before implementation.
- Claude `/loop` and Codex `/goal` style behavior should not become board-safety
  authority. Resolution: native loop/goal/subagent features may be used inside
  provider host reasoning, but every board/client/terminal action still returns
  through FirmCLI `TurnDecision`.

## Design

### 1. Skill Package Model

Add a FirmCLI-owned provider-native skill tree. Recommended prototype layout:

```text
skills/
  provider_native/
    common/
      <skill_id>/
        skill.yaml
        SKILL.md
        references/
        scripts/
    claude/
      <skill_id>/
        skill.yaml
        SKILL.md
        references/
        scripts/
    codex/
      <skill_id>/
        skill.yaml
        SKILL.md
        references/
        scripts/
```

`common` holds provider-neutral source when possible. `claude` and `codex`
hold provider-specific variants when native invocation, bundled skill names,
slash command expectations, subagent instructions, or CLI behavior require
different text.

Each package must declare a manifest with at least:

- `skill_id`: `PROJECT-DEFINED`.
- `title`: `PROJECT-DEFINED`.
- `description`: `PROJECT-DEFINED`, optimized for provider skill discovery.
- `providers`: `["claude-cli"]`, `["codex-cli"]`, or both.
- `native_invocation`: provider-specific hint, such as `/uart-triage` for
  Claude or `$uart-triage` / explicit skill mention for Codex if supported.
- `fallback_skill_ids`: FirmCLI `load_skills` IDs to request when native
  invocation fails.
- `context_files`: files to project.
- `usable_paths`: scripts/templates/resources to copy.
- `requires_governed_actions`: action names whose details must still be loaded
  before execution.
- `source_status`: `proposal`, `active`, or `disabled`.
- optional `depends_on`.

The manifest is product-owned. Provider-native files are not operator-owned
`.claude` or `.codex` configuration. They are FirmCLI runtime assets.

### 2. Phase 0 Provider Discovery Gate

Before implementing the bridge, run a no-hardware discovery pass against the
actual local provider CLIs and edit this spec with the observed results. This
is a hard gate because provider-native paths and invocation forms are vendor
surface details, not FirmCLI design choices.

Discovery rules:

- Use disposable temp working directories, not the real repo and not global
  provider folders.
- Use only burner skills with unique names such as
  `firmcli-native-probe-<timestamp>` and a unique response token.
- The burner skill must instruct the provider to return a simple structured
  FirmCLI-compatible no-board decision, such as `finalize`, and to include the
  unique token in a harmless message field.
- The probe must be run through the exact noninteractive command shape FirmCLI
  uses: `claude --print --output-format json ...` and
  `codex exec --json -o <output> -`.
- The probe must not use pyOCD, serial, vendor tools, board files, or hardware.
- The probe must record provider binary path, version when available, command
  mode, working directory, environment overrides, candidate projection path,
  invocation string, exit code, structured-output result, and cleanup result.
- A provider self-report that it "used" a skill is not enough. Passing evidence
  requires the returned output to include the unique burner-skill token or a
  provider trace/artifact that clearly depends on the projected burner skill.

Claude candidate matrix:

```text
working-dir/.claude/skills/<burner>/SKILL.md
invocation forms:
  /<burner>
  explicit natural-language request naming the skill
  implicit request matching the skill description
optional bundled workflow smoke:
  /loop with a no-hardware, structured-output-only prompt
```

Codex candidate matrix:

```text
working-dir/.agents/skills/<burner>/SKILL.md
working-dir/.codex/skills/<burner>/SKILL.md
runtime-CODEX_HOME/skills/<burner>/SKILL.md, with CODEX_HOME set only for the probe
invocation forms:
  $<burner>
  /skills then selected skill only if noninteractive exec supports it
  explicit natural-language request naming the skill
  implicit request matching the skill description
```

The discovery pass must produce a small notes artifact, recommended path:

Write the discovery results into a future probe-notes markdown under
`markdowns/curr/` before implementing the bridge.

After discovery, update this spec before writing bridge code:

- mark each provider path candidate `works`, `does_not_work`, `unsupported`, or
  `not_tested`;
- mark each invocation form the same way;
- replace speculative runtime layout examples with the proven default where one
  exists;
- keep unsupported candidates documented as rejected alternatives, not deleted;
- if no native path passes for a provider in noninteractive mode, require that
  provider to use `load_skills` fallback until the provider surface changes.

### 3. Runtime Native Views

Before the first CLI provider turn, FirmCLI creates a runtime projection under
the provider runtime working directory.

Phase 0 discovery result:

- Claude Code CLI `2.1.76`: `working-dir/.claude/skills/<skill>/SKILL.md`
  works in `claude --print --output-format json` when the FirmCLI command also
  passes `--allowedTools Skill(<skill-id>)`. Direct `/skill-id` invocation and
  natural-language skill requests both returned the burner-skill token in JSON
  output. `--json-schema` mode hung in the probe and is rejected for this pass.
- Codex CLI `0.142.2`: `working-dir/.codex/skills/<skill>/SKILL.md` works in
  `codex exec` noninteractive mode. `.agents/skills` also worked locally, but
  `.codex/skills` is the selected projection layout because it matches the
  user's requested native `.codex` behavior and avoids relying on older
  ambiguous `.agents` wording.
- API providers are fallback-only: they receive the compact native-skill index
  and can request FirmCLI `load_skills`, but no `.codex` or `.claude` runtime
  projection is attempted.

Implemented runtime layout:

```text
<provider_runtime>/
  .claude/
    skills/
      <skill_id>/
        SKILL.md
        references/
        scripts/
  .codex/
    skills/
      <skill_id>/
        SKILL.md
        references/
        scripts/
  firmcli-native-skills.json
```

The implementation must not project to every candidate path by default after
Phase 0. It should select the proven provider path for the installed CLI mode.
If multiple paths work, prefer the path that is project-local to the provider
runtime and does not require overriding global provider state. If no Codex path
works in `codex exec`, Codex native skills remain disabled in `auto` mode and
the provider uses `load_skills` fallback.

`firmcli-native-skills.json` records:

- provider;
- source root;
- runtime projection root;
- projected skill IDs;
- source file hashes;
- projected file hashes;
- feature-probe result;
- projection timestamp;
- fallback `load_skills` IDs;
- whether projection was used in the current prompt.

Projection must happen inside the provider runtime, not in the user's global
provider config. If a provider changes its expected skill folder, the adapter
changes the projection target while the FirmCLI source tree stays stable.

The installed source package is read-only to provider recovery. Runtime
projection files may be regenerated for a run. If a provider wants to repair a
skill, it may only edit a FirmCLI runtime copy that the brain explicitly exposes
for repair; source packages remain unchanged.

### 4. Provider Capability Probing And Current Implementation

The initial implementation records the Phase 0 probe result in provider
capabilities and run projection metadata. It does not rerun a live burner probe
before every hardware run; it uses the proven local CLI layouts and conservative
mode behavior:

- `off`: no projection and no native skill prompt.
- `auto`: CLI providers project active packages when available; unsupported
  providers fall back to `load_skills`; missing packages are non-fatal.
- `require`: unsupported providers or missing active packages fail before the
  provider turn with a visible provider-native-skills failure.

Future live probe caching can replace the static Phase 0 evidence fields, but
must preserve the same fail-closed semantics.

Add provider-native skill capability fields to `ProviderCapabilities`, for
example:

```text
supports_native_skills
native_skill_layout
native_skill_invocation_style
native_skill_probe_status
native_skill_probe_details
supports_native_loop_skill
supports_native_subagents
```

Probe exact installed behavior, not marketing claims. The probe should answer:

- Does this installed CLI version expose native skills in noninteractive mode?
- Does it discover skills from the projected runtime working directory?
- Which candidate path does it discover from?
- Does it accept direct skill invocation over stdin in the mode FirmCLI uses?
- Which invocation style works for the provider in noninteractive mode?
- Does it preserve structured JSON output when a prompt contains a native skill
  invocation?
- Does it expose enough command output or artifact evidence to know projection
  was considered?
- Are bundled skills such as Claude `/loop` usable in `--print` mode without
  breaking structured output?

Probe output must be cached per provider binary/version during one top-level
FirmCLI invocation, with a conservative failure default. If probing is too
expensive or unsafe for a live hardware run, allow `--native-skills=off`,
`auto`, or `require` behavior:

- `off`: do not project or prompt native skill usage.
- `auto`: project and prompt native skills only if probe passes.
- `require`: fail early if projection or provider support is unavailable.

Default should be `auto`.

### 5. Prompt Contract

The prompt should include a compact native skill index separate from the
existing compact diagnostic YAML skill text.

Example:

```text
Provider-native FirmCLI skills available:
- uart-triage: Use for silent UART, wrong boot text, or serial mismatch.
  Preferred native invocation for this provider: /uart-triage
  Evidence expectation: after invoking it, continue with one FirmCLI
  TurnDecision. If native invocation fails or you are not sure the skill loaded,
  request load_skills(skill_ids=["uart-triage"]).

Rules:
- Prefer provider-native skill invocation for these skills when available.
- Do not invent skill names not listed here.
- Do not use provider-native skills to execute board actions directly.
- If native skill handling fails, request FirmCLI load_skills as fallback.
- Every provider turn must still end with exactly one TurnDecision.
```

The index should be compact and hash-accounted like other prompt sections.
Full skill bodies should not be duplicated every turn unless the provider lacks
native skill support or fallback `load_skills` has injected them.

Prompt mode behavior:

- `bootstrap/full`: include native skill index, projection metadata summary, and
  fallback instructions.
- `remote-delta`: include compact native skill index or stable hash plus any
  changed native skill status.
- `remote-sync`: include native skill status alongside provider memory.
- `retry`: include only the compact native skill index plus correction note
  unless the failure was about native skill fallback.

### 6. Native Invocation And Fallback Semantics

The brain does not execute `/skill-name` itself. It prompts the provider to use
its own native invocation behavior during provider-side reasoning. The provider
must still return one FirmCLI `TurnDecision`.

Success path:

1. Brain projects native skills into runtime.
2. Prompt tells provider native skills are available.
3. Provider invokes or uses a native skill inside its own CLI session.
4. Provider returns a valid `TurnDecision`.
5. FirmCLI executes only the governed or context-expansion decision.
6. Artifacts record that native projection was available. If provider output
   includes a native skill trace, artifacts record it as untrusted provider
   metadata.

Fallback path:

1. Provider says native invocation failed, or the probe says native skills are
   unavailable, or the provider is an API provider.
2. Provider requests `load_skills(skill_ids=[...])`.
3. FirmCLI loads the deterministic runtime-copy skill context with the existing
   `ModelNativeSkillRegistry`.
4. Provider sees the injected skill context next turn.
5. Normal loaded-detail and governed-action rules still apply.

If the provider reports "I used the native skill" but then makes a bad action,
the result is handled by existing parse, schema, details-required, and
convergence guardrails. Provider self-report does not mark a native skill
"verified".

### 7. Native Loop, Goal, And Subagent Features

FirmCLI should not clone Claude `/loop`, Codex `/goal`, or future native
workflow features. It should expose a provider-native bridge that can use them
when they are safe in the current mode.

Rules:

- Native loop/goal/subagent features may organize provider-side host reasoning,
  code inspection, parallel exploration, or skill use.
- They may not hold an open board session outside FirmCLI's loop.
- They may not directly call pyOCD, serial, vendor tools, or board/probe shell
  commands except through governed FirmCLI tools/actions.
- They may not replace FirmCLI max-iteration, timeout, cleanup, run-artifact,
  or finalization rules.
- The outer FirmCLI loop still owns termination. A provider-native workflow must
  eventually return a FirmCLI `TurnDecision` or fail as a provider error.

For Claude `/loop`, the first supported product use should be a no-hardware
host-work smoke. Board-attached runs should remain fallback-only until no-hardware
structured-output behavior is proven.

For Codex `/goal` or skill/subagent workflows, the same rule applies: prove
noninteractive structured-output behavior before treating it as usable in
turnkey hardware runs.

### 8. Security And Safety

Provider-native skills are prompt/workflow assets, not new execution authority.

Hard boundaries:

- Native skill scripts/resources are copied from FirmCLI-owned source to
  provider runtime views only after manifest validation.
- Init or helper scripts shipped inside provider-native skill packages must go
  through the same hardware/probe import and command preflight policy as
  model-native skills before any FirmCLI-run init script executes.
- The provider may read projected skill files through its native system, but
  cannot use them to bypass FirmCLI governed actions.
- Board tools, client actions, and `run_green_check` still require loaded
  details and fresh provider decisions.
- Recover/unlock remains gated by existing board config and invocation policy.
- Native skills must not contain hardcoded ports, probe UIDs, board-specific
  branches, or OS-specific paths.

### 9. Files Expected To Change

Primary code files changed:

- `src/pyocd_debug_mcp/brain/provider_types.py`
  - Added provider-native skill capability fields, prompt accounting sections,
    and prompt bundle rendering for native skill indexes.

- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
  - Records Codex native skill capability metadata and run projection metadata.

- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
  - Records Claude native skill capability metadata, run projection metadata,
    and passes `--allowedTools Skill(...)` for projected skills.

- `src/pyocd_debug_mcp/brain/loop.py`
  - Builds native skill indexes, initializes projection before first provider
    turn, preserves fallback instructions, and records projection metadata in
    request payloads and prompt accounting.

- `src/pyocd_debug_mcp/brain/config.py`
  - Added env/config support for `off`, `auto`, `require`, and the optional
    provider-native skill root override.

- new provider-native-skill bridge module under the brain package, recommended
  name `provider_native_skills.py`
  - Owns manifests, validation, projection, hashing, capability probe records,
    and prompt-index rendering.

Likely docs:

- `skills/README.md`
- `markdowns/curr/README.md`
- `markdowns/current-progress.md` after implementation
- `markdowns/R12_P_SPLIT.md` or `markdowns/things-to-change.md` if this is
  accepted as a new hard-bar item.

Tests added or updated:

- `tests/test_provider_native_skills.py`
- `tests/test_r12_turnkey.py`

## Board-Facts-As-Data And Origin Tags

This spec introduces no new board facts.

- Native skill root names, projection folder names, manifest field names, and
  feature-flag names are `PROJECT-DEFINED`.
- Provider CLI skill folder names are `VENDOR-FIXED, UNVERIFIED` until proven
  against the installed provider CLI in noninteractive mode.
- Provider native invocation strings such as `/skill-name` or `$skill-name` are
  `VENDOR-FIXED, UNVERIFIED` until the focused probe proves they work in the
  exact mode FirmCLI uses.
- Board IDs, pyOCD targets, baud rates, probe families, expected UART text, and
  expected symbols continue to come from board config, benchmark cases, or run
  invocation data.

Do not add board-specific branches to the provider-native skill bridge. Skills
may describe board-specific reasoning, but selection must be data-driven through
manifest applicability, board config, or task/case data.

## Documentation Plan

Current status:

- Keep this file as the implemented hard-bar spec for the Wave 1
  provider-native skill bridge.
- Keep `markdowns/curr/README.md`, `markdowns/current-progress.md`,
  `markdowns/things-to-change.md`, `markdowns/R12_P_SPLIT.md`,
  `markdowns/ROADMAP.md`, and the concrete build plan synchronized with the
  implementation and validation state.
- Keep `skills/README.md` documenting the distinction between diagnostic YAML
  skills, model-native fallback skills, and provider-native projected skills.
- If provider-native bridge options appear in CLI help, update the CLI help
  strings and any operator-facing docs in the same build pass.

Provider docs used for this spec:

- Claude Code skills docs:
  `https://code.claude.com/docs/en/skills`
- OpenAI Codex skills docs:
  `https://developers.openai.com/codex/skills`
- OpenAI Codex slash command docs:
  `https://developers.openai.com/codex/cli/slash-commands`
- OpenAI Codex app command docs:
  `https://developers.openai.com/codex/app/commands`

Discovery docs:

- `r12-provider-native-skill-bridge_probe_notes.md` under `markdowns/curr/`
  - Burner skill definitions used for each provider.
  - Exact commands and environment overrides.
  - Candidate path and invocation matrix results.
  - Spec edits made from the observed results.

## Portability

- All source and projection paths must use `pathlib`.
- Projection roots must live inside the existing provider runtime root.
- No provider-native skill source should require a Windows drive letter, Unix
  shell syntax, user home config, global provider install paths, or hidden IDE
  state.
- The bridge must degrade cleanly when the selected CLI is missing,
  unauthenticated, too old, or lacks native skill support in noninteractive
  mode.
- API providers must continue to work through compact indexes and fallback
  `load_skills` without requiring Claude or Codex CLI.
- Feature probes must be bounded by explicit timeouts and must not touch
  hardware.
- Projection cleanup is covered by existing provider runtime cleanup and run
  artifact policy; do not broad-delete user `.claude`, `.codex`, or `.agents`
  folders.

## Verification Plan

Focused unit tests:

- Manifest validation accepts provider-native skill packages with common,
  Claude, and Codex variants.
- Manifest validation rejects missing IDs, provider mismatch, bad fallback IDs,
  path escapes, missing context files, and unsupported provider names.
- Projection creates Claude runtime view under the configured runtime root.
- Projection creates Codex runtime view under the Phase 0 proven configured
  runtime root.
- Projection never writes to global provider folders.
- Projection records source/runtime paths and content hashes.
- Projection de-dupes repeated skills and preserves dependency order if
  dependencies are added.
- Prompt index includes native invocation hints, fallback `load_skills` IDs, and
  safety rules.
- Prompt index is compact and hash-accounted.
- `native_skills=off` disables projection and native prompt instructions.
- `native_skills=auto` falls back cleanly when a provider probe fails.
- `native_skills=require` fails early and visibly when projection/probe fails.
- `openai-api` and `anthropic-api` ignore native projection and use fallback
  instructions only.
- Provider capability records include native skill probe status and projection
  metadata.
- Provider subprocess commands still use the expected working directory after
  projection.
- Existing `load_skills` fallback behavior is unchanged.
- Details-required guardrails still block governed actions even when native
  skills are projected.
- Provider self-report that a native skill was used does not set FirmCLI loaded
  model-native skill state.

No-hardware CLI smokes:

- Phase 0 Claude burner-skill discovery in `--print --output-format json` mode
  proves or rejects `.claude/skills` and each invocation form before bridge code
  is written.
- Phase 0 Codex burner-skill discovery in `codex exec --json -o ... -` mode
  proves or rejects `.agents/skills`, `.codex/skills`, isolated `CODEX_HOME`
  skills, and each invocation form before bridge code is written.
- Claude CLI projected-skill smoke in `--print --output-format json` mode:
  provider sees a tiny projected test skill and returns a valid no-board
  `finalize` or `load_skills` fallback decision.
- Codex CLI projected-skill smoke in `codex exec --json -o ... -` mode:
  provider sees a tiny projected test skill and returns a valid no-board
  `finalize` or `load_skills` fallback decision.
- For both CLI providers, a deliberately unavailable native skill path causes
  the provider to request FirmCLI `load_skills`.
- Output artifacts contain projection metadata and rendered prompt accounting.

Hardware checks after no-hardware proof:

- One attached-board healthy freeform run per available CLI provider with native
  skill projection enabled in `auto`.
- One simple bug-repair benchmark per available CLI provider with native skill
  projection enabled in `auto`.
- Compare against fallback-only `native_skills=off` for the same case to confirm
  board safety and final result semantics are unchanged.
- Cleanup audit shows no leftover spawned `codex`, `claude`, MCP, pyOCD, serial,
  or board sessions beyond known pre-existing processes.

## Acceptance Criteria

- FirmCLI has a provider-native skill bridge for CLI providers.
- Product source skills remain FirmCLI-owned, not provider-global state.
- Claude and Codex can have separate provider-native skill variants.
- Runtime projection is generated under the provider runtime root.
- The provider prompt includes a compact native skill index with fallback
  instructions.
- `claude-cli` and `codex-cli` capability probes determine whether native
  projection is usable in the exact noninteractive mode FirmCLI invokes.
- Before production bridge code is written, the Phase 0 discovery notes record
  real CLI results for burner skills and this spec is updated to use proven
  provider paths/invocation forms.
- Codex projection does not assume `.agents/skills`, `.codex/skills`, or
  `CODEX_HOME/skills` until the installed `codex exec` mode proves one of them.
- The default mode is conservative `auto`, with `off` and `require` available.
- Native skill projection failure does not break API providers or fallback
  FirmCLI runs.
- Existing `load_skills` remains the deterministic fallback and is unchanged for
  API providers.
- Native skills cannot bypass loaded-detail guardrails, MCP schemas, recover
  gates, or cleanup.
- Native `/loop`, `/goal`, subagent, or future workflow features may be used
  only as provider-side host-work accelerators, not as the board-safety loop.
- Run artifacts record source/projection hashes, provider-native feature status,
  and rendered prompt accounting.
- No provider self-report is treated as verified native skill loading.
- No global user `.claude`, `.codex`, or `.agents` folders are written.
- Non-hardware tests prove projection and fallback.
- Live CLI no-hardware smokes prove structured output survives native skill
  projection before any hardware proof is claimed.

## Verified

- Spec reconciled on 2026-07-01 against the build plan R12 hard-bar and
  scaffold-hardening amendments, `ROADMAP.md`, `current-progress.md`,
  `r12-context-scaffold-hardening_spec.md`, and
  `r12-prompt-memory-cost-hardening_spec.md`.
- Current code inspection found the relevant provider/runtime surfaces:
  `provider_codex_cli.py`, `provider_claude_cli.py`, `provider_types.py`,
  `loop.py`, `model_native_skills.py`, `tool_schemas.py`, `state.py`, and
  `config.py`.
- Official provider documentation was checked for current native skill surfaces:
  Claude Code skills, Codex skills, Codex CLI slash commands, and Codex app
  commands.
- Codex documentation conflict/ambiguity is captured explicitly: the skills
  page describes `.agents/skills` paths, while other Codex docs describe
  `CODEX_HOME` containing skills and team config under `.codex/skills`.
  Production code must follow Phase 0 local CLI evidence, not this proposal's
  older path assumption.
- Phase 0 burner probes proved native skill access in the current
  brain/provider architecture:
  - Codex CLI uses runtime `.codex/skills` in `codex exec`.
  - Claude CLI uses runtime `.claude/skills` in `claude --print` when FirmCLI
    passes `--allowedTools Skill(<skill-id>)`.
- Implementation added `provider_native_skills.py`, provider capability and
  prompt-accounting fields, Codex/Claude projection metadata, Claude
  `--allowedTools` skill allowlist wiring, `--provider-native-skills
  off|auto|require`, `--provider-native-skill-root`,
  `skills/provider_native/common/firmcli-firmware-debug`, and
  `skills/model_native/firmcli-firmware-debug`.
- Focused non-hardware tests are green:
  `uv run pytest tests/test_provider_native_skills.py tests/test_r12_turnkey.py -q`
  -> `78 passed`.

## Pending Verification

- Full Python-change validation and full FirmCLI suite validation are still
  pending after this implementation pass.
- Claude `/loop`, Codex `/goal`, subagent, and future workflow behavior are not
  proven safe for FirmCLI hardware runs.
- Native skill projection has no attached-board product run proof yet in this
  pass; focused no-hardware regression tests prove projection and
  prompt/artifact behavior.
- Live Claude/Codex native skill projection requires local CLI/auth availability
  and should be included in the next full Wave 1 validation run.
- Exact official `nrf52833dk` hardware proof remains pending until that board is
  attached.
