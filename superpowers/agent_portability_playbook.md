# Portability & Bootstrap Playbook - Portable After Short Developer Bootstrap

> **Why this exists.** The agent keeps drifting toward one of two bad extremes:
> building only for this developer's bench, or overclaiming a fantasy "fresh
> stranger machine with zero manual setup" product. The current product
> contract is narrower and more useful: Firmware-CLI should work across the
> supported host + supported board matrix after a short documented bootstrap
> equivalent to the setup an engineer would already need for normal manual
> board debugging. After that bootstrap, the repo-owned scripts, MCP server,
> and agent runtime should self-pilot as much as possible.
>
> **Read this at the start of any task that touches setup, installation,
> dependencies, config, paths, or first-run behavior.** It governs how code
> must be written to be portable within that post-bootstrap contract.

---

## 0. THE AUDIENCE

You are writing for a developer on a supported Windows or macOS machine, with
one of the supported boards, who is willing to do a short documented bootstrap
first and then expects the repo and agent to carry the rest.

That means:
- do not build only for the current bench
- do not assume arbitrary unsupported boards or arbitrary host states
- do allow a bounded bootstrap for OS drivers, proprietary probe software,
  permissions, and comparable manual-debug prerequisites
- do expect the guided runtime to stop pushing setup labor back onto the human
  once that bootstrap is complete

If a workflow still requires repeated manual setup or repeated environment
debugging after bootstrap, it is not done.

**Mental test before writing setup/install/config code:** "After the documented
bootstrap is complete, would this run cleanly on another supported machine with
the same supported board?" If no, it is not done.

---

## 1. SCRIPT WHAT IS REPEATABLE; DOCUMENT WHAT IS A TRUE BOOTSTRAP STEP

- **Dependency installation should prefer a setup script**, not scattered README
  instructions. A short `init.md` bootstrap is acceptable before the agent
  starts, but repetitive setup should move into a script whenever that can be
  done safely.
- **First-run setup -> automated bootstrap where practical.** Board detection,
  port discovery, target-pack fetching, and config scaffolding should be
  automatic on first run rather than manual configuration work.
- **Per-OS differences -> handled in code where practical.** macOS and Windows
  setup helpers are better than prose-only guidance. A concise `init.md`
  fallback is acceptable before the agent starts.
- **No manual config editing.** Config is generated or scaffolded by the tool
  with sane defaults and discovered values. If the user must set something, the
  tool prompts for it interactively or accepts a flag; never "open this file
  and edit it."
- **Idempotent + re-runnable.** Setup scripts must be safe to run twice
  (check-then-act), so a partial or repeated setup self-heals rather than
  breaking.

Vendor and OS realities:

- proprietary probe drivers and vendor tools may remain part of the documented
  bootstrap when redistribution or silent install is not realistic
- best-effort helper scripts are good; fake "fully automatic" claims are not
- if a vendor prerequisite remains manual, say so explicitly and keep the
  runtime behavior clean once it is present

**The bar:** short bootstrap, then repo-owned operation.

---

## 2. PORTABLE BY DEFAULT INSIDE THE SUPPORTED MATRIX

- **No dependency on anything specific to the author's machine** - not a
  hardcoded path, port, env var, toolchain location, or "it's already
  installed here" assumption.
- **Discover, don't assume:** serial ports via pyserial enumeration;
  board/target via detection or the board-config the user selected; never a
  baked-in `COM3` or `/dev/tty...`.
- **Bundle what you can legally bundle; script what you can safely script;
  document the rest as bootstrap.** Python deps travel with the package.
  Permissively licensed binaries may be bundled. Proprietary drivers or probe
  packages usually stay outside the repo and may remain a one-time documented
  bootstrap prerequisite.
- **The hardware-touching server runs locally on the user's machine** because
  it must reach the USB board. Do not design anything that assumes a centrally
  hosted hardware path.
- **Test mentally on a supported machine, not yours.** Before declaring setup
  code done, trace it on a clean supported macOS and clean supported Windows
  box with only the documented bootstrap completed.

---

## 3. THE INSTALL RULE: AUTOMATE LOW-FRICTION PATHS, EXPLICITLY BOUND THE REST

The rule that fixes the "agent keeps telling me to download stuff" problem:

- **You may not emit a vague manual "the user must install/download X somehow"
  step as the solution.** If a manual bootstrap step remains, it must be
  explicit, bounded, and part of the documented first-run path.
- **If something must be installed, prefer a script that installs it**
  (OS-detecting, idempotent), so the user does as little as possible by hand
  before the agent takes over.
- **If an install genuinely cannot or should not be scripted** - for example:
  proprietary tool with a brittle or interactive installer, license
  click-through, OS-level approval, or a prerequisite the engineer would
  already need for manual debugging - either:
  1. document it as a bounded bootstrap step and make the post-bootstrap
     runtime behave cleanly, or
  2. **STOP BEFORE WRITING CODE** and tell the human author if the remaining
     manual step would conflict with the product claim or create repeated
     operator burden:

     > WARNING: BOOTSTRAP CONTRACT CONFLICT: `<thing>` is required but cannot
     > be cleanly repo-owned because `<reason>`.
     > Options: (a) keep it as an explicit bootstrap prerequisite,
     > (b) choose a different tool or packaging path,
     > (c) narrow the support claim.
     > Which contract do you want before I build around it?

- **Never silently bake in a manual step and move on.** The choice between
  "automate it," "bundle it," or "accept a bounded pre-agent bootstrap step" is
  the human author's to make - surface it, do not hide it in vague
  instructions.

**Why this matters:** the defect is not that a bounded bootstrap exists. The
defect is hiding an unstable or repeated manual dependency inside what should
already be repo-owned runtime behavior.

---

## 4. THE GUIDED-AGENT EXPERIENCE AFTER BOOTSTRAP

- The product is driven by a **guided agent** that walks the user through use -
  the user's actions are choices and confirmations, not repeated setup labor.
- **Destructive or irreversible actions still gate** (flash, unlock,
  mass-erase). Automate setup where appropriate; still gate destruction.
- **Failures must self-diagnose, not dump a manual chore on the user.** If the
  board is not found, the tool should say what it detected and offer an
  automated retry or a bounded prerequisite reminder. It should not collapse
  into aimless setup guessing.

---

## 5. Pre-commit portability check

- [ ] Wrote for another supported machine after the documented bootstrap, not
      this bench alone
- [ ] Every repeatable install/setup/config step lives in an OS-detecting,
      idempotent script where practical
- [ ] No machine-specific paths, ports, or assumptions; values discovered, not
      baked in
- [ ] Did not emit a vague manual "user must download/install X" instruction as
      a solution
- [ ] Any remaining manual step is explicitly documented as bootstrap, not
      leaked into runtime
- [ ] For any contract conflict: STOPPED and asked the author before building
      around it
- [ ] Destructive actions still gated; failures self-diagnose rather than
      dumping chores
- [ ] Traced the flow mentally on a clean supported machine with the documented
      bootstrap completed

---

## The one-sentence version

**Write for a supported machine after a short explicit bootstrap: script the
repeatable parts, bound the true prerequisites, and make the agent self-pilot
after bootstrap instead of leaving the user to keep debugging the environment
by hand.**
