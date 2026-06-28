# R12 Branch B Multi-Loop Real Deployment Test Report

Status: VERIFIED ON ATTACHED HARDWARE - documentation evidence report.

Date: 2026-06-28.

## Scope

This report records a real deployment-path test for Branch B repeated user
prompts:

- public `pyocd-debug-brain run` CLI
- real `codex-cli` provider
- real local MCP server subprocess started by the brain
- real board connections and UART through the server boundary
- session-scoped client action registration through `--client-action`
- prompt files through `--task-file`
- multiple sequential user prompts per board

This is not a provider-session persistence proof. Cross-prompt persistent
provider sessions remain Branch A scope. This test proves that Branch B's public
deployment surface can run repeated independent customer prompts, each with its
own full brain loop.

## Hardware Detected

Detected through Python APIs during the run:

- `nucleo_l476rg`
  - probe: STMicroelectronics ST-Link
  - UID: `066FFF514988525067233337`
  - UART: `COM12`
- `nrf52840dk`
  - probe: SEGGER J-Link OB
  - UID: `683377322`
  - UART: `COM11`

The attached Nordic board was `nrf52840dk`, not the official scoped
`nrf52833dk`. This is valid retained-board proof for the attached hardware, but
it does not replace a later `nrf52833dk` proof.

## Test Shape

For each attached board, two separate user prompts were submitted through the
public CLI.

Prompt 1:

- register `uart_write` with `--client-action`
- run an ordered board batch:
  - `connect`
  - `wait`
  - `run_script:uart_write`
  - `read_serial`
- finalize `diagnosed_only` / `healthy`

Prompt 2:

- register `uart_write` with `--client-action`
- use a temporary workspace containing a broken `app.py`
- model inspects `app.py`
- model replaces `app.py`
- configured build command `python app.py` succeeds
- run the ordered board batch:
  - `connect`
  - `wait`
  - `run_script:uart_write`
  - `read_serial`
- finalize `diagnosed_only` / `healthy`

## Results

| Board | Prompt | Run root | Model turns | Result | Evidence |
|---|---:|---|---:|---|---|
| `nucleo_l476rg` | 1 | `runs/20260628T212402Z-9b730979` | 2 | PASS | `actions_taken=connect -> wait -> write_serial -> run_script:uart_write -> read_serial`; `uart_ok=True`; client action executed |
| `nucleo_l476rg` | 2 | `runs/20260628T212523Z-fa129f2f` | 5 | PASS | host edit/build succeeded; same ordered board batch succeeded; `uart_ok=True`; client action executed |
| `nrf52840dk` | 1 | `runs/20260628T212604Z-e86cf36a` | 2 | PASS | `actions_taken=connect -> wait -> write_serial -> run_script:uart_write -> read_serial`; `uart_ok=True`; client action executed |
| `nrf52840dk` | 2 | `runs/20260628T212720Z-c8244c8c` | 5 | PASS | host edit/build succeeded; same ordered board batch succeeded; `uart_ok=True`; client action executed |

All four runs recorded:

- `final_status=diagnosed_only`
- `classification=healthy`
- `mcp_tools_used=connect,write_serial,read_serial`
- `client_actions.json` with `uart_write.executed=true`
- `uart_write` script hash
  `d1cdee58c07b47cadb3d91af03ab9c4b242c7adb18962f3c0b534e3a300fa661`

The two Prompt 2 runs also recorded `applied-patches/turnkey.diff` and
`files_changed=app.py`.

## Verified

- Multiple sequential user prompts work through the public Branch B brain CLI.
- Each user prompt ran a full provider-driven loop, not a mocked decision path.
- Prompt 2 on both boards required multiple provider turns and crossed the host
  action boundary before board actions.
- Ordered action batches executed in the expected order.
- `wait` executed inside the ordered batch.
- Session-scoped `run_script` registration was available through the public CLI.
- The client action ran and was snapshotted by hash in the run artifact.
- UART write and UART read were exercised against real serial ports.
- The MCP server boundary was exercised by real `connect`, `write_serial`, and
  `read_serial` tool calls.

## Pending Verification

- Repeat this exact multi-loop test on the official scoped Nordic
  `nrf52833dk` when that board is attached.
- Persistent provider-session reuse across user prompts remains Branch A scope
  and was not tested here.
