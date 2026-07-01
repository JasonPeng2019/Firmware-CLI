---
name: firmcli-firmware-debug
description: Use for FirmCLI firmware diagnosis, host-side code repair planning, and deciding which governed board evidence to request.
---

# FirmCLI Firmware Debug

Use this native provider skill for host-side reasoning and code inspection in a FirmCLI turnkey run. The native skill may guide planning, source inspection, source edits in the prepared workspace, and evidence selection. It does not grant board authority.

## Hard Boundaries

- End each provider turn with exactly one FirmCLI `TurnDecision`.
- Do not call pyOCD, serial tools, vendor flash utilities, probe tools, shell board commands, or hardware helpers directly.
- Board actions must return through FirmCLI governed decisions such as `load_tool_details`, `connect`, `flash_firmware`, `read_serial`, `read_symbol_u32`, and `run_green_check`.
- Do not use `unlock_recover` unless the task and board policy explicitly allow it.
- Do not hardcode probe UIDs, serial ports, generic pyOCD targets, local absolute paths, or board-specific control flow.
- Do not claim a fix is complete until FirmCLI evidence shows the build, flash, UART, symbol, and green-check requirements for the task are satisfied.

## Preferred Workflow

1. Read the compact run state, task contract, expected UART text, expected symbol, workspace path, allowed edit roots, and loaded details.
2. Inspect only relevant workspace source and build metadata with host-side provider tools.
3. Identify the smallest code or configuration change that explains the symptom.
4. If a governed action's details are missing, request detail loading first.
5. After code changes, request FirmCLI verification through governed actions.
6. If native skill handling is unavailable or uncertain, request `load_skills(skill_ids=["firmcli-firmware-debug"])` as fallback.
