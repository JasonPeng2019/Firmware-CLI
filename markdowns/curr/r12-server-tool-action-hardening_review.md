# Review for r12-server-tool-action-hardening

Task: Review server tool action hardening and no-credit validation.

## Verdict

CLEAN FOR NO-CREDIT SCOPE

## Findings table

| severity | gate | file:line | issue | concrete fix |
| --- | --- | --- | --- | --- |
| none | no-credit implementation/test gate | n/a | No blocking issue found in the centralized server-tool action hardening pass. | n/a |

## Hardware hand-off status

No new hardware run was required for this parser/policy hardening pass. The
change is covered by unit/regression tests and real Codex adapter smokes. Full
Claude/hardware/provider matrix remains under the existing Branch A live
provider handoff and should be rerun only after Claude usage refresh.

## What's genuinely good

- The duplicated server-native tool list was removed from the action parser.
- The provider prompt list now renders from the canonical server-native set
  instead of maintaining another literal list.
- Namespaced `server_tool:<name>` calls now strip redundant embedded
  `tool_name` fields before MCP invocation.
- Conflicting provider-shape output fails closed before any MCP tool call.
- The no-credit ladder is green, and the real Codex adapter produced the exact
  redundant namespaced shape this change was meant to harden.
