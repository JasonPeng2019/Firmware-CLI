---
name: firmcli-firmware-debug
description: Use for FirmCLI firmware diagnosis, repair planning, and governed evidence requests.
---

# FirmCLI Firmware Debug

Use this workflow context for FirmCLI turnkey firmware repair and validation.

## Operating Rules

- Treat the FirmCLI brain as the board authority. Do not run pyOCD, serial tools, vendor flash utilities, probe commands, or board shell commands directly.
- Request governed actions through exactly one FirmCLI `TurnDecision`.
- Load action details before executing governed actions such as `connect`, `flash_firmware`, `read_serial`, `read_symbol_u32`, and `run_green_check`.
- Do not use `unlock_recover` unless the task and board policy explicitly allow recovery.
- Do not hardcode probe UIDs, serial ports, generic pyOCD targets, local absolute paths, or board-specific branches.
- Prefer surgical source edits in the prepared workspace over whole-file rewrites.
- Do not finalize `fixed` or `healthy_confirmed` until the relevant green-check evidence is present.

## Diagnosis Pattern

1. Inspect the task contract, expected UART text, expected symbol, board ID, and allowed edit roots.
2. Inspect source files in the workspace using provider-native host tools when available.
3. Make the smallest source change that explains the symptom.
4. Ask FirmCLI for build, flash, UART, symbol, and green-check evidence through governed actions.
5. If details are missing, request `load_tool_details` or `load_client_action_details` instead of guessing.
6. Finalize only after evidence supports the classification and status.
