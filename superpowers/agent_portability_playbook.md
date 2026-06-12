# Portability & Self-Setup Playbook — Build for the Absent Stranger

> **Why this exists.** The agent keeps building for *this developer's bench* — assuming someone is
> present to install tools, add config, or run manual steps. That is the wrong audience. This product
> ships to **arbitrary users on arbitrary machines (macOS + Windows) with arbitrary supported boards**,
> who install a CLI and expect it to **just work, unattended.** Every manual "now go download X" step
> the agent emits is a defect, not a handoff.
>
> **Read this at the start of any task that touches setup, installation, dependencies, config, paths,
> or first-run behavior.** It governs how code must be written to be portable and self-installing.

---

## 0. THE AUDIENCE (the reframe that fixes everything)

You are **never** writing for the developer at this desk. You are writing for an **absent stranger**:
- on a machine you've never seen (macOS or Windows, no Linux assumption either way),
- with one of the supported boards plugged in,
- who will **not** read a README, **not** run manual commands, and **not** debug your setup,
- who installs the CLI and expects the guided agent to do the rest.

If a step requires that stranger to *do* something manually, it has failed — unless it's genuinely
impossible to automate (see §3), in which case you STOP and tell the human author first.

**Mental test before writing any setup/install/config code:** "If I handed this to someone who will
never type a command I didn't put in a script, would it work on their machine, with their board, on
first run?" If no, it's not done.

---

## 1. EVERYTHING that can live in a script, MUST live in a script

- **Dependency installation → a setup script**, not a README instruction. If the product needs pyOCD,
  a device pack, a udev/WinUSB association, a Python env — the script installs/sets it up, detecting the
  OS and doing the right thing per platform. The user runs ONE entry point; the script handles the rest.
- **First-run setup → automated bootstrap.** Board detection, port discovery, target-pack fetching,
  config scaffolding — all automatic on first run, not manual prerequisites.
- **Per-OS differences → handled IN the script**, branching on detected OS. macOS and Windows paths
  both covered. Never "on Mac do X, on Windows do Y" prose for the user — the script detects and does it.
- **No manual config editing.** Config is generated/scaffolded by the tool with sane defaults and
  discovered values (ports via enumeration, board via detection). If the user must set something, the
  tool prompts for it interactively or accepts a flag — never "open this file and edit it."
- **Idempotent + re-runnable.** Setup scripts must be safe to run twice (check-then-act), so a partial
  or repeated setup self-heals rather than breaking.

**The bar:** install the CLI → run it → the guided agent and scripts handle environment, dependencies,
board/port discovery, and config, with zero manual steps for the user.

---

## 2. SELF-HOSTED, SELF-CONTAINED, PORTABLE BY DEFAULT

- **No dependency on anything specific to the author's machine** — not a hardcoded path, port, env var,
  toolchain location, or "it's already installed here" assumption. (Ties to the no-hardcoding rule in
  the Coding Guidelines and the cross-platform Scope Assumptions.)
- **Discover, don't assume:** serial ports via pyserial enumeration; board/target via detection or the
  board-config the user selected; never a baked-in `COM3` / `/dev/tty…`.
- **Bundle what you can legally bundle; declare-and-auto-install the rest.** Python deps travel with the
  package (pyproject/lockfile). Permissively-licensed binaries *may* be bundled. Proprietary drivers
  (SEGGER/ST) cannot be redistributed → the script detects their absence and **automates the install
  invocation** (runs the vendor installer / driver-association step) rather than telling the user to do
  it by hand; only if even that is impossible does it fall to §3.
- **The hardware-touching server runs locally on the user's machine** (it must, to reach the USB board)
  — so "self-hosted" is the default and the architecture already requires it. Don't design anything that
  assumes a service you host centrally for the hardware path.
- **Test mentally on a fresh machine, not yours.** Before declaring setup code done, trace it on a
  hypothetical clean macOS and clean Windows box with nothing pre-installed.

---

## 3. THE INSTALL RULE: automate it, or STOP and tell the human FIRST

The one hard rule that fixes the "agent keeps telling me to download stuff" problem:

- **You may NOT emit a manual "the user must install/download X" step as the solution.** Manual installs
  are defects.
- **If something must be installed, the agent writes a SCRIPT that installs it** (OS-detecting,
  idempotent), so the user never installs anything by hand.
- **If an install genuinely CANNOT be scripted/automated** (e.g. a proprietary tool with no silent
  installer, a license click-through, an OS permission that requires user action), you **STOP BEFORE
  WRITING CODE** and tell the human author:
  > ⚠️ UNAUTOMATABLE SETUP: `<thing>` is required but cannot be installed by script because `<reason>`.
  > Options: (a) <bundle / alternative tool / scripted workaround>, (b) accept a one-time manual step.
  > How do you want to handle this before I build around it?
- **Never silently bake in a manual step and move on.** The choice between "automate it," "bundle it,"
  or "accept an unavoidable manual step" is the human author's to make — surface it, don't decide it by
  emitting a download instruction.

**Why STOP-first matters:** if the agent builds assuming a manual install, the whole setup flow is
designed around a defect. Catching "this can't be automated" *before* writing code lets the author pick
a portable alternative (a different tool, a bundleable binary) instead of discovering the wall later.

---

## 4. THE GUIDED-AGENT EXPERIENCE (the human does nothing manual)

- The product is driven by a **guided agent** that walks the user through use — the user's actions are
  *choices and confirmations*, not setup labor.
- **Destructive/irreversible actions still gate** (flash, unlock/mass-erase) — "no manual setup" does
  NOT mean "no confirmations for dangerous operations." Automate setup; still gate destruction.
  (Consistent with the safety gates in `build_plan_concrete`.)
- **Failures must self-diagnose, not dump a manual chore on the user.** If the board isn't found, the
  tool says what it detected and offers an automated retry/fix — it doesn't say "go install drivers and
  figure it out." (The fault-vs-wiring diagnosis is a product feature; apply it to setup too.)

---

## 5. Pre-commit portability check (run before any setup/install/config commit)
- [ ] Wrote for the absent stranger on a fresh macOS/Windows box, not this bench (§0)
- [ ] Every automatable install/setup/config step lives in an OS-detecting, idempotent script (§1)
- [ ] No machine-specific paths/ports/assumptions; values discovered, not baked in (§2)
- [ ] Did NOT emit a manual "user must download/install X" instruction as a solution (§3)
- [ ] For anything unautomatable: STOPPED and asked the author before building around it (§3)
- [ ] Destructive actions still gated; failures self-diagnose rather than dumping chores (§4)
- [ ] Traced the flow mentally on a clean machine with nothing pre-installed (§2)

---

## The one-sentence version
**Write for an absent stranger on a fresh machine: everything installable goes in an OS-detecting,
idempotent script so the user does nothing by hand — and if something truly can't be automated, STOP
and ask the author before building around it, never just tell the user to go download it.**
