> STATUS: CURRENT HANDOFF - read this first when resuming the next Codex
> session. This is a navigation and status document, not authority. The build
> plan and `things-to-change.md` still win.

# Next Codex Handoff - 2026-06-30

## Current branch and worktree

Branch: `P-Wave-0`

Important: the worktree is not clean. Current uncommitted work is intentional
and splits into two groups:

1. R12 context-scaffold hardening spec/docs:
   - `markdowns/curr/r12-context-scaffold-hardening_spec.md` was created.
   - The governing markdowns were updated to make that spec visible and to
     distinguish immediate scaffold fixes from future Wave 2 work.
2. `.codex` skill self-containment cleanup:
   - FirmCLI Codex skills no longer instruct Codex to read `.claude/commands`.
   - Helper scripts now locate the repo by `.codex/skills` + `superpowers`,
     not `.claude/commands`.

No product code implementation has been done for the new scaffold-hardening
spec yet. Do not claim the spec is implemented.

## What happened in the last session

### R12 scaffold-hardening spec/docs

Created:

- `markdowns/curr/r12-context-scaffold-hardening_spec.md`

Updated:

- `markdowns/firmware_agent_build_plan_concrete (10).md`
- `markdowns/things-to-change.md`
- `markdowns/R12_P_SPLIT.md`
- `markdowns/ROADMAP.md`
- `markdowns/current-progress.md`
- `markdowns/curr/README.md`
- `markdowns/curr/wave2-codebase-map_spec.md`
- `markdowns/repo_file_index.md`

Main decisions captured:

- Model-native skills must load from a product/client-owned root, not
  `.codex/skills`.
- Installed/client skill packages are read-only product assets.
- Provider repair can only touch the runtime/session copy under provider
  runtime.
- Skill context and init should run from the runtime copy, not source.
- Skill-load failures should be structured provider-visible context-expansion
  failures with recovery choices.
- `load_tool_details(tool_names=[...])` should be added as a
  context-expansion decision.
- Invalid governed-tool argument calls should auto-return focused full tool
  details in the retry context.
- Prompt ordering/dedupe should be implemented now for current surfaces:
  skill index, compact tool index, loaded tool details, loaded skill context,
  configured provider memory, turn context, and decision schema.
- Future slots are reserved for codebase-map context and richer memory cadence.
- Global client-owned bug reporting/telemetry is future remote/backend work,
  not a current prototype implementation requirement.

Validation already run for this docs pass:

- markdown inventory helper
- markdown reference checker
- markdown overlap helper
- `git diff --check`

Reference checker still exits nonzero for known historical run IDs, shorthand
package paths like `brain/loop.py`, and old relative-link parser limitations.
New active spec references resolve.

### Codex skill self-containment cleanup

Updated:

- `.codex/skills/firmcli-build/SKILL.md`
- `.codex/skills/firmcli-fix-bug/SKILL.md`
- `.codex/skills/firmcli-review/SKILL.md`
- `.codex/skills/firmcli-spec-loop/SKILL.md`
- `.codex/skills/firmcli-specs/SKILL.md`
- `.codex/skills/firmcli-test-suite/SKILL.md`
- `.codex/skills/firmcli-write-process/SKILL.md`
- `.codex/skills/firmcli-workflow-core/SKILL.md`
- `.codex/skills/firmcli-workflow-core/references/source-map.md`
- `.codex/skills/firmcli-workflow-core/scripts/self_test_skills.py`
- `.codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py`
- `.codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py`

Main change:

- Codex skills are now self-contained workflow instructions. They no longer
  say to mirror or read `.claude/commands`.
- If a legacy slash-command file contains a rule Codex needs, copy it into the
  relevant Codex `SKILL.md`; do not make Codex load the legacy command file.
- `self_test_skills.py` no longer requires `.claude/commands` to exist.

Validation already run:

```powershell
rg -n "Claude workflow|Claude `/|\.claude/commands|Use this skill to mirror|Read `?\.claude|Claude-command" .codex/skills
python .codex\skills\firmcli-workflow-core\scripts\self_test_skills.py --skip-quick-validate
git diff --check
```

Results:

- dependency scan found no remaining `.claude/commands` / mirror-Claude
  workflow dependency in `.codex/skills`;
- skill self-test passed;
- `git diff --check` passed.

The only remaining `.claude` mention found by a broader scan was in
`.codex/skills/firmcli-markdown-audit/scripts/check_markdown_references.py` as
an ignored path prefix. That is not a workflow dependency.

## What to do next

Likely next implementation task:

Use `firmcli-write-process` on
`markdowns/curr/r12-context-scaffold-hardening_spec.md`.

Implementation should happen before Wave 2 Module G codebase-map work builds on
the current skill/tool prompt substrate.

Hard order:

1. Read authority docs and this handoff.
2. Read `r12-context-scaffold-hardening_spec.md` in full.
3. Implement only the immediate scaffold fixes from that spec.
4. Do not implement codebase-map first boot, map maintenance, real product
   skills, global bug reporting, backend upload, or provider-native tool calls
   unless the user explicitly changes scope.
5. Validate with focused tests and Codex smoke where possible.
6. Leave Claude/provider-quota and exact official-board proof as handoff if not
   available.

## Immediate implementation scope from the spec

Implement now:

- product/client-owned model-native skill root, not `.codex/skills`;
- installed skills read-only to provider recovery;
- full runtime/session skill package copy before init/context;
- init scripts and context files loaded from runtime copy;
- structured `load_skills` failure results and recovery prompt text;
- failure detail preserved in existing run events/artifacts;
- `load_tool_details(tool_names=[...])` action model and dispatch path;
- full tool-detail rendering/injection on the next provider turn;
- invalid governed-tool argument failure auto-injects focused tool details;
- canonical prompt ordering/dedupe for current prompt surfaces;
- provider/adapter failure classification;
- prompt bundle alias cleanup:
  `render_native_delta_text` / `render_native_sync_text` should be removed after
  callers/tests use canonical names.

Document-only/future work:

- `codebase_map.md` first-boot generation;
- codebase map maintenance turns;
- real product workflow skill library;
- global client-owned all-bugs registry;
- backend telemetry upload;
- maintainer dashboard/review flow;
- provider-native tool-call output format.

## Most important authority docs to read

Read in this order:

1. `superpowers/agent_index_START_HERE.md`
2. `superpowers/agent_consistency_playbook.md`
3. `markdowns/firmware_agent_build_plan_concrete (10).md`
4. `superpowers/agent_coding_playbook.md`
5. `superpowers/agent_doc_sync_playbook.md`
6. `superpowers/agent_portability_playbook.md`
7. `superpowers/agent_script_doc_playbook.md`
8. `superpowers/spec_build_review_loop_playbook.md`
9. `markdowns/ROADMAP.md`
10. `markdowns/current-progress.md`
11. `markdowns/things-to-change.md`
12. `markdowns/R12_P_SPLIT.md`
13. `markdowns/curr/README.md`
14. `markdowns/curr/r12_turnkey_spec.md`
15. `markdowns/curr/r12-context-scaffold-hardening_spec.md`
16. `markdowns/curr/wave2-codebase-map_spec.md`

Why these matter:

- Build plan is the source of truth.
- `things-to-change.md` is the prototype hard bar.
- `R12_P_SPLIT.md` schedules the work and says what belongs in Branch B
  hardening versus Wave 2 Module G.
- Current progress says what is actually proven versus pending.
- The two current specs define the immediate scaffold fixes and future
  codebase-map work.

## Product and customer/deployment rules to keep in mind

These are not optional style preferences:

- Host-local work is provider-native/free. Do not reintroduce governed
  `read_file`, `replace_file`, `run_build`, or generic host shell actions.
- The brain governs board/server actions, waits, client actions that touch the
  gated server API, context expansion, green checks, and finalization.
- The board/server boundary must remain structurally governed by the brain.
- Do not add generic host execution to the brain or MCP server.
- Direct raw hardware bypass by the provider is an accepted soft residual, but
  the normal cooperative path must strongly prefer governed MCP/server tools.
- Cross-platform is a development requirement. Use `pathlib`; no hardcoded
  Windows drive paths, serial ports, probe serials, pyOCD targets, baud rates,
  shell separators, or OS-specific command assumptions.
- Build for an absent stranger: setup/config/dependency changes should be
  self-installing or clearly STOP-and-ask if vendor/proprietary setup cannot be
  automated.
- Never claim real hardware proof unless a real board produced it in the
  current session.
- Exact official target pair remains `nrf52833dk + nucleo_l476rg`; attached
  `nrf52840dk` proof is useful but not a substitute unless the user promotes it.
- MCP tool behavior belongs in tool docstrings, not sidecar docs.
- Code and docs move together.

## Product architecture files to read for implementation

Turnkey brain and action boundary:

- `src/pyocd_debug_mcp/brain/actions.py`
- `src/pyocd_debug_mcp/brain/action_policy.py`
- `src/pyocd_debug_mcp/brain/loop.py`
- `src/pyocd_debug_mcp/brain/state.py`
- `src/pyocd_debug_mcp/brain/provider_types.py`
- `src/pyocd_debug_mcp/brain/provider_factory.py`

Model-native skills:

- `src/pyocd_debug_mcp/brain/model_native_skills.py`
- `src/pyocd_debug_mcp/brain/skills.py`
- Current known code gap: `loop.py` still defines
  `MODEL_NATIVE_SKILL_ROOT = REPO_ROOT / ".codex" / "skills"`.

Tool metadata and MCP client:

- `src/pyocd_debug_mcp/brain/tool_schemas.py`
- `src/pyocd_debug_mcp/brain/mcp_client.py`
- `src/pyocd_debug_mcp/server.py`

Provider adapters and prompt behavior:

- `src/pyocd_debug_mcp/brain/provider_codex_cli.py`
- `src/pyocd_debug_mcp/brain/provider_claude_cli.py`
- `src/pyocd_debug_mcp/brain/provider_openai.py`
- `src/pyocd_debug_mcp/brain/provider_anthropic.py`
- `src/pyocd_debug_mcp/brain/provider_parsing.py`

Client actions / workspace:

- `src/pyocd_debug_mcp/brain/client_actions.py`
- `src/pyocd_debug_mcp/brain/workspace.py`

Events, timeout, evidence:

- `src/pyocd_debug_mcp/brain/events.py`
- `src/pyocd_debug_mcp/brain/timeout_policy.py`
- `src/pyocd_debug_mcp/timeouts.py`
- `src/pyocd_debug_mcp/brain/evidence.py`

Hardware/server substrate:

- `src/pyocd_debug_mcp/adapters/swd_interface.py`
- `src/pyocd_debug_mcp/adapters/swd_pyocd.py`
- `src/pyocd_debug_mcp/adapters/uart_interface.py`
- `src/pyocd_debug_mcp/adapters/uart_pyserial.py`
- `src/pyocd_debug_mcp/services/target_control.py`
- `src/pyocd_debug_mcp/services/uart_capture.py`
- `src/pyocd_debug_mcp/services/symbols.py`
- `src/pyocd_debug_mcp/guardrails/`

CLI / UX:

- `src/pyocd_debug_mcp/brain/cli.py`
- `src/pyocd_debug_mcp/ux/`

Board/config/deployment:

- `boards/nrf52833dk.yaml`
- `boards/nucleo_l476rg.yaml`
- `boards/nrf52840dk.yaml`
- `src/pyocd_debug_mcp/board_config.py`
- `src/pyocd_debug_mcp/local_env.py`
- `host_bootstrap.py`
- `stage0_check.py`
- `stage0_setup.md`
- `setup_host.ps1`
- `setup_host.sh`

Firmware/test fixtures:

- `firmware/nrf52833dk/reference/`
- `firmware/nucleo_l476rg/reference/`
- `firmware/nrf52840dk/reference/`
- `cases/`
- `tests/harness/stage1_smoke.py`
- `tests/harness/r11_benchmark.py`
- `tests/harness/r12_turnkey_benchmark.py`

## Test files to read and update

Likely impacted:

- `tests/test_model_native_skills.py`
- `tests/test_r12_turnkey.py`
- `tests/test_p0_foundation.py`
- `tests/test_r12_turnkey_merge.py`
- `tests/test_branch_c_harness.py`
- `tests/harness/branch_c_tests.py`

Specific existing test/code facts:

- `tests/test_r12_turnkey.py` currently asserts prompt bundle compatibility
  aliases:
  `render_native_delta_text()` and `render_native_sync_text(...)`.
- `tests/test_r12_turnkey.py` monkeypatches `loop_mod.MODEL_NATIVE_SKILL_ROOT`
  in the current `load_skills` smoke test.
- `src/pyocd_debug_mcp/brain/action_policy.py` currently has
  `CONTEXT_EXPANSION_ACTIONS = frozenset({"load_skills"})`.
- `src/pyocd_debug_mcp/brain/actions.py` currently has `LoadSkillsAction` but
  no `LoadToolDetailsAction`.
- `src/pyocd_debug_mcp/brain/tool_schemas.py` currently renders compact tool
  index text and retains `input_schema` in internal records.

## Validation commands to use

For Python implementation work, use the Python-change skill and run:

```powershell
python .codex\skills\python-change\scripts\run_python_change_checks.py
```

For broader non-hardware suite:

```powershell
python .codex\skills\firmcli-workflow-core\scripts\run_check_ladder.py --preset suite
```

Likely focused tests after scaffold implementation:

```powershell
uv run pytest -q tests/test_model_native_skills.py
uv run pytest -q tests/test_r12_turnkey.py -k "skill or tool_schema or tool_details or prompt or invalid"
uv run pytest -q tests/test_p0_foundation.py
```

Expected additional smoke tests after implementation:

- no-hardware Codex `load_skills` smoke against the new product/client skill
  root or a structured missing-skill failure if no product skill exists;
- no-hardware Codex `load_tool_details` smoke;
- invalid governed-tool argument dry-run that auto-injects focused tool
  details;
- attached-board Branch B/Wave 1 boundary smoke if hardware is available.

Do not claim Claude proof if provider quota is unavailable.

## Known current gaps from the spec

The following are expected to be false in current code until implementation:

- Product skills do not yet default to a product/client-owned root.
- The loader does not yet copy the full skill package to runtime before
  init/context.
- Context files and init scripts are still source-root oriented.
- Skill-load failures are not yet rich structured provider-visible results.
- `load_tool_details` does not exist.
- Invalid governed-tool argument calls do not yet auto-inject full focused tool
  details.
- Prompt ordering/dedupe is not yet centralized for loaded tool details plus
  loaded skill context.
- Prompt bundle compatibility aliases still exist.
- Provider/adapter failure categories still need audit and implementation.

## Codex skill suite state

The local `.codex` FirmCLI workflow skills were cleaned up so they are
self-contained.

Relevant files:

- `.codex/skills/firmcli-workflow-core/SKILL.md`
- `.codex/skills/firmcli-workflow-core/references/source-map.md`
- `.codex/skills/firmcli-workflow-core/scripts/self_test_skills.py`
- `.codex/skills/firmcli-workflow-core/scripts/scaffold_workflow_doc.py`
- `.codex/skills/firmcli-workflow-core/scripts/run_check_ladder.py`
- `.codex/skills/firmcli-specs/SKILL.md`
- `.codex/skills/firmcli-build/SKILL.md`
- `.codex/skills/firmcli-review/SKILL.md`
- `.codex/skills/firmcli-spec-loop/SKILL.md`
- `.codex/skills/firmcli-fix-bug/SKILL.md`
- `.codex/skills/firmcli-test-suite/SKILL.md`
- `.codex/skills/firmcli-write-process/SKILL.md`

Validation run:

```powershell
python .codex\skills\firmcli-workflow-core\scripts\self_test_skills.py --skip-quick-validate
```

Result: passed.

## Handoff warnings

- Do not revert the uncommitted markdown/spec changes unless the user asks.
- Do not archive this handoff until the next session has consumed it or the
  current work is committed/pushed.
- The old `markdowns/curr/next-codex-handoff-20260630.md` had previously been
  archived during cleanup; this file is a fresh replacement.
- Some docs still reference historical run IDs whose `runs/` folders may be
  absent in a fresh/clean checkout. That is expected unless a doc claims a
  current-session proof.
- The attached Nordic board in recent proof was `nrf52840dk`, not the official
  `nrf52833dk`; keep that distinction in all summaries.

## Verified here

- This handoff was created on `P-Wave-0`.
- Current `markdowns/curr/` contains:
  - `README.md`
  - `r12_turnkey_spec.md`
  - `r12-context-scaffold-hardening_spec.md`
  - `wave2-codebase-map_spec.md`
- The previous session's skill self-test and `git diff --check` were green
  after the `.codex` skill cleanup.

## Pending verification

- This handoff itself has not been pushed.
- R12 context-scaffold hardening has not been implemented.
- Wave 2 codebase-map scaffolding has not been implemented.
- Claude CLI code-writing proof remains pending provider quota/availability.
- Exact official `nrf52833dk + nucleo_l476rg` proof remains pending.
