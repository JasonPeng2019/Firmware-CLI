You are validating a firmware benchmark case on `{board_id}`.

Use the `pyocd-debug` MCP server tools to determine whether the currently
tracked baseline firmware is healthy.

Rules:

- connect with `connect(board_id="{board_id}")`
- do not use a hard-coded probe UID
- treat the current workspace as read-only
- the runner already prepared the target state; do not rebuild or reflash unless
  the MCP evidence proves the prepared state is wrong
- do not edit source files
- do not run local shell discovery commands such as `rg`, `ls`, or
  `Get-ChildItem`; use the MCP tools directly for verification
- do not use `unlock_recover` unless the evidence clearly justifies it
- use MCP tools rather than guessing from static files alone

Target observables to confirm:

- UART contains `{uart_substring}`
- symbol `{symbol_name}` resolves and reads back `{symbol_value_u32_hex}`

Return your final answer in the structured schema exactly.
