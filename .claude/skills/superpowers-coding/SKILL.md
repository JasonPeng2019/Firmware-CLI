---
name: superpowers-coding
description: "How to write code and implementation docs in Firmware-CLI. Use when writing or editing ANY code or implementation doc here. Enforces: verify-don't-claim (never say hardware works unless run on a real board this session), no hardcoding of ports/paths/pyOCD targets/baud, origin tags (HW-FIXED/VENDOR-FIXED/PROJECT-DEFINED/UNVERIFIED), build-on-libraries-don't-reimplement, and lowest-level smoke checks."
---

# Coding — verify, don't claim; never hardcode; tag origins

Standing rules for writing code/docs on this hardware-tooling project. Re-read the relevant section
before each commit.

## 0. Prime directive: never claim what you didn't verify

You usually **cannot touch the hardware.** Never report "this works / flashing succeeds / the board
responds" unless a real run on a real board produced that result **this session**. Otherwise say "should
work pending hardware verification — not run on a board." Tag unverified code `# UNVERIFIED: needs
hardware check`. Always distinguish three states: (a) verified by running here, (b) verified by a
non-hardware check (test/type/lint/dry-run), (c) unverified assumption. If a step needs hardware you
can't reach, **STOP and hand off** a precise runnable instruction; don't guess the outcome.

## 1. No hardcoding

No hardcoded serial ports (discover via pyserial / board config), file paths (use `pathlib`), pyOCD
targets / baud / probe / board id (these live in `boards/<board>.yaml` via the one loader), secrets, or
OS assumptions. Rule of thumb: if a value differs on another machine/board/OS, it's config or discovery.

## 1b. Origin tags — every non-obvious value declares its authority

In code comments AND yaml:
- **`HW-FIXED`** — dictated by silicon/hardware spec (source: datasheet). Wrong, not a choice.
- **`VENDOR-FIXED`** — a contract with an external tool/lib/protocol (source: that tool's docs). Can drift with versions.
- **`PROJECT-DEFINED`** — a choice we made (source: our plan). Changeable by decision.
- **`UNVERIFIED`** (orthogonal) — best guess not yet confirmed against its source. Remove only after real confirmation.

Don't tag the obvious (loop counters, temporaries).

## 2–5. The rest

- **Read before writing.** Read the files you'll touch in full; confirm every pyOCD/pyserial/`mcp` call
  against the installed version's docs — never from memory.
- **Build on the libraries, don't reimplement them.** pyOCD does flashing/SWD/registers/unlock; pyserial
  does serial; the `mcp` SDK does protocol. Your code is the thin wrapper + shared services +
  guardrails/brain. Go through shared `target_control` / `swd_pyocd`; never call `ConnectHelper` directly.
- **Smoke-check at the lowest level** after any change: `uv run pytest -q` → `uv run ruff check .` →
  `uv run mypy src` → dry-run → (hand off) hardware. Validate MCP tools in the Inspector first.
- **Small, isolated, reversible changes.** One concern, one layer (adapter ↔ service ↔ server ↔
  guardrails ↔ brain). Destructive ops route through their safety gate and are tested with refusals/dry-runs.
- **When in doubt, stop and ask.** Don't guess forward on a prior decision, a hardware result, or a
  library API. Detect non-progress: same fix twice without change → escalate.

Full playbook (incl. the pre-commit checklist): `reference/agent_coding_playbook.md`.
