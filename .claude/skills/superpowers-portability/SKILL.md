---
name: superpowers-portability
description: "Build for the absent stranger on a fresh macOS/Windows machine. Use on any Firmware-CLI task touching setup, install, dependencies, config, paths, or first-run behavior. Script the high-friction parts (OS-detecting, idempotent), discover values instead of baking them in, and STOP-and-ask before any unautomatable install rather than emitting a vague 'go download X' step."
---

# Portability — build for the absent stranger

You are never writing for the developer at this desk. You are writing for an **absent stranger** on a
machine you've never seen (macOS or Windows, no Linux assumption), with a supported board plugged in, who
follows a short bootstrap and then expects the guided agent to take over.

**Mental test before any setup/install/config code:** "If I handed this to someone who follows a short
documented bootstrap and then expects the agent to take over, would it work on their machine, with their
board, on first run?" If no, it's not done.

## The rules

- **Everything that can live in a script, MUST.** Dependency install, board detection, port discovery,
  pack fetching, config scaffolding → automated and **idempotent** (check-then-act, safe to run twice).
  A short `init.md` pre-agent bootstrap is acceptable; repetitive/vendor setup moves into a script.
- **No manual config editing.** Config is generated/scaffolded with sane defaults and discovered values
  (ports via pyserial enumeration, board via detection). If the user must set something, prompt or accept
  a flag — never "open this file and edit it."
- **Self-hosted, portable by default.** No machine-specific path/port/env/toolchain assumption. Bundle
  what you legally can (Python deps via pyproject/lockfile); declare-and-auto-install the rest. The
  hardware-touching server runs locally (it must, to reach USB).
- **The install rule (the hard one):** you may NOT emit a vague "the user must install/download X"
  step. If something must be installed, prefer an OS-detecting idempotent SCRIPT. If an install genuinely
  CANNOT be scripted (proprietary tool, license click-through, OS permission), either document it as a
  bounded pre-agent step **or STOP BEFORE WRITING CODE and ask the author** which way to handle it.
  Never silently bake in a manual step.
- **Guided-agent experience:** the human does choices/confirmations, not setup labor. Destructive actions
  (flash, unlock/mass-erase) still gate. Failures self-diagnose and offer an automated retry — they don't
  dump a manual chore.

Trace every setup flow mentally on a clean macOS and clean Windows box with nothing pre-installed before
declaring it done.

Full playbook: `reference/agent_portability_playbook.md`.
