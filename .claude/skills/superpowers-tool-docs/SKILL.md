---
name: superpowers-tool-docs
description: "Where documentation lives in the Firmware-CLI MCP product. Use when adding or changing an MCP tool, or any bench/setup script the operator runs. An MCP tool is documented in its DOCSTRING (the description + handle the client reads over the protocol) — never a sidecar .md; the human/terminal shell workflow shares ONE operator guide (stage0_setup.md), not a doc per script."
---

# Tool-Description & Operator-Guide — document each thing where its reader looks

There are two readers and two surfaces. Put each kind of documentation where its reader will see it, and
nowhere else.

| Surface | Who reads it | Where its docs MUST live |
|---|---|---|
| MCP tools (`@mcp.tool()` in `server.py`) | the MCP **client agent**, over the protocol | the function **docstring** + typed signature + typed return |
| Bench/setup scripts (`setup_host.*`, `host_bootstrap.py`, `stage0_check.py`) | a **human/terminal agent** at a shell | **one operator guide**: `stage0_setup.md` |

**The cardinal error: do not write a sidecar `.md` to document an MCP tool.** The client can't read it,
and it drifts from the docstring the client *does* read. If you find one, fold it into the docstring and delete it.

## 1. MCP tool docstrings — the docstring is the interface

Every tool docstring must let the model: decide WHEN to call it (one plain sentence + expected state,
e.g. "Call `connect` first"); choose the RIGHT inputs (document every arg: meaning, units, accepted forms,
default/fallback); interpret the RETURN (self-describing, stable strings — the agent pattern-matches on
them); recover from refusals/errors (guard/error text phrased as the next action). Return typed
text/strings, not raw dicts (dicts truncate silently in the client). Destructive tools say so in the
first docstring line and route through their gate. Validate every tool in the MCP Inspector
(`uv run mcp dev …`) before a real client — schema errors fail silently in the client.

## 2. One operator guide for bench/setup scripts

`stage0_setup.md` is the single consolidated guide: purpose & entry conditions; the ordered sequence
(`setup_host.{ps1,sh}` → `host_bootstrap.py` → `stage0_check.py` → `uv run pyocd-debug-mcp`); per-script
essentials (one-line purpose, the few flags an operator chooses, what "done/ready" looks like — `--help`
carries the exhaustive list); branch points & handoffs; a consolidated symptom→cause→fix→rerun table; and
Verified / Pending-verification. Bootstrap/env specifics live in `init.md`; layout/naming in `README.md`
— link, don't duplicate. When a NEW bench script appears, add its rows to `stage0_setup.md`; do not create
a new per-script doc.

Docs still move with the code (doc-sync): change a tool's behavior → update its docstring in the same
unit; change a script's sequence/flag/ready-signal → update `stage0_setup.md` in the same unit.

Full playbook: `reference/agent_script_doc_playbook.md`.
