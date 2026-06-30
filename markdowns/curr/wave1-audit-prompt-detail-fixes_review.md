# Review for wave1-audit-prompt-detail-fixes

Task: Review Wave 1 adversarial audit prompt ordering and invalid MCP argument retry fixes

## Verdict

CLEAN FOR AGENT-VERIFIABLE WAVE 1

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |
| high | Wave 1 prompt scaffold | `src/pyocd_debug_mcp/brain/provider_types.py` | Fixed: provider prompt ordering placed provider memory before loaded context and did not provide a stable compact skill-context slot. | Added `skill_context_text` and updated render order. |
| high | invalid governed action retry | `src/pyocd_debug_mcp/brain/loop.py` | Fixed: schema/argument failures raised as `MCPClientError` bypassed focused detail auto-load and were treated as unexpected failures. | Classify only argument/schema-like MCP errors as retryable invalid calls, auto-load focused details, and keep other MCP errors as failures. |
| medium | live provider behavior | `src/pyocd_debug_mcp/brain/actions.py` | Fixed: the schema left batch `action_type` as any string, and live Codex once tried `finalize` inside `action_batch` before correcting after refusal. | Enumerated valid batch action types, excluded `finalize`, and clarified the prompt. |

## Hardware hand-off status

- Complete for the two attached boards that were visible in this session:
  `nucleo_l476rg` and `nrf52840dk`.
- Claude CLI provider proof is blocked by local auth:
  `Not logged in - Please run /login`.

## What's genuinely good

- The fixes preserve the Wave 1 architecture: providers keep free host-side
  autonomy, while the brain only accepts governed decisions.
- The invalid-argument path is narrow enough that transport/runtime MCP failures
  are not masked as harmless retry prompts.
- Focused regression tests now cover both prompt ordering and MCP-client
  invalid-argument detail recovery.

## Verification

- Focused pytest command passed:
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle or invalid_mcp_arguments or blocks_server_tool or load_tool_details" tests/test_r12_turnkey_merge.py -k "prompt or memory or schema"`
  -> `15 passed, 79 deselected`.
- Final focused pytest command passed:
  `uv run pytest -q tests/test_r12_turnkey.py -k "provider_prompt_bundle or invalid_mcp_arguments or load_tool_details or action_batch or turn_decision_schema_excludes_finalize" tests/test_r12_turnkey_merge.py -k "prompt or memory or schema"`
  -> `16 passed, 79 deselected`.
- Python-change gate passed: Ruff, format, Pyright, and `359 passed`.
- FirmCLI suite ladder passed; report path:
  `runs/wave1-adversarial-audit-suite-report.txt`.
- Codex CLI provider + hardware live smokes passed on both boards on the final
  code: `runs/20260630T191305Z-97e20d79` for `nucleo_l476rg` and
  `runs/20260630T191450Z-8fedbe20` for `nrf52840dk`.
- A parallel Nordic rerun failed Stage 0 while the Nucleo hardware run was
  active, then passed when rerun alone; classified as a parallel probe/hardware
  precondition artifact.
