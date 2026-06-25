# Review: P-Wave-A + benPhaseB Integration

## Verdict

**CHANGES REQUESTED**

The merge is non-hardware clean and the intended union landed: `P0` foundation
seams still exist, and the hybrid provider-session / tool-schema runtime is the
actual behavior. But there are still a few real implementation issues in the
session and toolkit layers that should be fixed before building more on top of
this branch.

## Findings

| Severity | Gate | File:line | Issue | Concrete fix |
|---|---|---|---|---|
| MAJOR | Spec conformance / layering | `src/pyocd_debug_mcp/brain/provider_types.py:323-335`, `src/pyocd_debug_mcp/brain/provider_openai.py:96-118` | The OpenAI native-session path still resends the full tool-schema and decision-schema block on every turn. `ProviderPromptBundle.user_prompt_text()` always includes `tool_schema_text`, and `OpenAIDecisionProvider` passes that whole block again even when `previous_response_id` is healthy. That means the native conversation accumulates repeated static prompt payloads, which wastes context and weakens the value of native continuation. | Split prompt rendering into stable-vs-delta layers for native providers. On native-primary turns, send only the current-turn delta by default; inject tool schemas and local memory only on bootstrap or explicit safety-sync turns. |
| MAJOR | Spec conformance / consistency | `src/pyocd_debug_mcp/brain/loop.py:1847-1852` | The merge restored timeout-config plumbing almost everywhere, but the final disconnect path still hardcodes `TURNKEY_DEFAULT_TOOL_TIMEOUT_SECONDS`. This is a real merge leftover: the run starts with `invocation.timeout_config`, but teardown partially bypasses it. | Route the disconnect timeout through `invocation.timeout_config`, either by using `default_tool_seconds` or by adding an explicit disconnect timeout field to `TurnkeyTimeoutConfig`. |
| MAJOR | Toolkit completeness | `src/pyocd_debug_mcp/brain/mcp_client.py:68-79`, `src/pyocd_debug_mcp/brain/tool_schemas.py:45-89` | The new tool-schema prompt is live and stable, but it only carries tool name, description, and input schema. It does not expose the public output/refusal semantics the brain actually depends on: `connect` returning `session_id=...`, refusal/block text shapes, or other stable result conventions. That leaves the model to infer output semantics from runtime experience instead of from the prompt contract. | Extend the toolkit layer with curated output-contract notes for the allowed tool set. Keep live MCP metadata as the source of truth for descriptions/inputs, but add a product-owned overlay for stable output semantics and refusal/block patterns. |
| MINOR | Spec conformance | `src/pyocd_debug_mcp/brain/benchmark.py:520-576`, `src/pyocd_debug_mcp/brain/cli.py:73-118` | The main headless CLI now carries the `P0` planning hooks, but the module-level benchmark CLI in `brain/benchmark.py` did not inherit the same timeout/planning flags. The merged runtime supports those fields; this CLI path does not expose them. | Add `--timeout-config-json`, `--timeout-proposal-json`, and `--iteration-estimate-json` to the benchmark module CLI and thread them through the same parsing helpers used by `brain/cli.py`. |
| MINOR | Layering / dead seam | `src/pyocd_debug_mcp/brain/provider_types.py:348-361` | `ProviderProgressUpdate` and `ProviderTurn.progress_updates` survived the merge as a harmless `P0` seam, but they are still dead. Runtime providers do not emit them, and the loop/UX stack does not consume them. Today they exist only to satisfy tests. | Either wire progress updates into provider implementations plus the UX/event layer, or remove the seam until a later wave actually needs it. |

## Hardware Hand-Off Status

What I re-ran here:

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run mypy src`
- `uv build --wheel`
- `uv run pyocd-debug --help`
- `uv run pyocd-debug-brain --help`

What I did **not** re-prove here:

- real STM32 + Nordic board flows
- real provider-backed turnkey runs
- real MCP/hardware session behavior after the merge

If you want the merged branch hardware-proven again, rerun the current ladder from
`current-progress.md`:

```bash
uv run pyocd list --probes
uv run python host_bootstrap.py --board-id nucleo_l476rg
uv run python host_bootstrap.py --board-id nrf52833dk
uv run python stage0_check.py --board-id nucleo_l476rg --reference-firmware nucleo_l476rg=firmware/nucleo_l476rg/reference/build/firmware.elf --confirm-shared-usb nucleo_l476rg
uv run python -m tests.harness.stage1_smoke --board-id nucleo_l476rg
uv run python stage0_check.py --board-id nrf52833dk --reference-firmware nrf52833dk=firmware/nrf52833dk/reference/build/firmware.elf --recover-test nrf52833dk --confirm-shared-usb nrf52833dk
uv run python -m tests.harness.stage1_smoke --board-id nrf52833dk
```

## What Is Genuinely Good

- The merge did preserve the intended shape: `P0` foundation seams are still
  present, and the hybrid provider-session runtime remains the real behavior.
- The non-hardware ladder is clean after the merge:
  - `pytest`
  - `ruff`
  - `mypy`
  - wheel build
- The headless CLI now carries both families of controls:
  - P0 timeout/planning hooks
  - hybrid memory/session controls
- `LocalMCPClient` retained both the startup-timeout seam and the live
  tool-descriptor path.
- The shell still has the benPhaseB behavior, and the non-Windows prompt-toolkit
  import fallback is now safe again.

Review requests changes. Run `/build <spec-path> markdowns/curr/p_wave_a_merge_benphaseb_review.md` to address them, then `/review` again.
