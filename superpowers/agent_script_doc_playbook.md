# Script-Doc Playbook — Every Runnable Script Has a Doc That Fully Replaces Reading It

> **Why this exists.** In operation, the agent driving this product **cannot see the source code.** It
> can only *run* a script and *read what the script emits* (logs, output, exit codes). Therefore each
> script's `.md` is not documentation-for-humans — it is the **operating agent's ONLY model of what the
> script does.** If the doc is wrong or incomplete, the agent operates blind: it has no source to fall
> back on.
>
> **The bar this sets:** an agent that has never seen the code must, from the doc + the script's runtime
> output alone, be able to (a) decide WHEN to run it, (b) choose the RIGHT inputs, (c) interpret EVERY
> log/output it can produce, (d) diagnose ANY failure from output alone, and (e) know EXACTLY what to do
> next for each outcome. The doc must *fully substitute for reading the code.*
>
> **Read this whenever you create or change any runnable script (`.py` or otherwise) the agent will
> later invoke.** Every such script MUST have a doc meeting this template before it is considered done.

---

## 0. THE PRINCIPLE: the doc is the interface; the code is invisible

- The operating agent reasons about a script **only** through (1) this doc and (2) the script's runtime
  output. It will never read the source. Write the doc accordingly — completeness is not optional polish,
  it is the difference between the agent operating correctly and operating blind.
- **No behavior may be "discoverable only by reading the code."** If the script does it, the doc says it.
  Hidden behavior = behavior the agent cannot account for = wrong agent decisions.
- **Every observable the script emits must be explained.** If a log line, output field, or exit code can
  appear, the doc must tell the agent what it means and what to do about it. An unexplained output is a
  blind spot.
- This makes script-docs the HIGHEST-drift-risk docs in the project: a doc that lags the code doesn't
  just mislead a human, it directs the operating agent to wrong actions. The Doc-Sync Playbook applies to
  these with maximum force — see §3.

---

## 1. MANDATORY template — every script-doc has ALL of these sections

No section may be omitted. "Not applicable" must be stated explicitly, not left blank.

### 1. Purpose & when to run vs. when NOT to run (a real decision aid)
- One-paragraph plain statement of what the script does.
- **WHEN to run it:** the specific situation(s) where THIS script is the correct choice. State the
  triggering conditions an agent can check from observable state ("run this when a board is connected and
  detected but not yet flashed", not "run this to flash").
- **WHEN NOT to run it:** the situations where it's the WRONG choice — and **which script to run
  instead.** A blind agent choosing among several scripts needs the doc to disambiguate: "if you need X
  instead, run `<other_script>`; if the board isn't detected yet, run `<detect_script>` first." Without
  this, the agent picks wrong when multiple scripts look superficially applicable.
- **Conflicting states:** conditions under which running it is unsafe or meaningless (e.g. a flash script
  while a live-monitor session holds the SWD connection).

### 2. Exact behavior (step by step)
- What the script actually does, in order, in enough detail that the agent can predict its effect
  without seeing the code. Side effects (files written, hardware touched, state changed) called out
  explicitly. Note anything destructive/irreversible (e.g. flash, mass-erase) prominently.

### 3. Inputs — every option, what it does, what it means
- EVERY input the script accepts: flags, arguments, env vars, config keys. For each: name, type,
  required/optional, default, allowed values/range, and **what it actually changes in behavior.** No
  input may be undocumented. Include examples of valid invocations.

### 4. Outputs & logs — what every emission MEANS
- Every log line / output field / status the script can emit, and what each one tells the agent.
- Group by meaning: normal-progress logs vs. warnings vs. errors. For each meaningful log, state what it
  implies about the script's state and whether action is needed.
- Exit codes / return status: enumerate each and its meaning.

### 5. Failure modes — exactly why it fails and how to fix
- A table/list of every known failure: **symptom (what the agent will see in the output) → cause → fix /
  next action.** This is the most important section — the agent diagnoses failures ONLY from output, so
  every failure must be traceable from its visible symptom to its remedy.
- Include hardware-specific failures (board not found, port busy, locked chip / APPROTECT, wrong target,
  wiring/power) with their distinguishing symptoms, since "is it code or hardware" is core to the product.
- For each fix, state **what to rerun** and with what inputs.

### 6. Rerun guidance — for each outcome, what to do next
- Given a particular log/result, what the agent should run next (this script again with different inputs,
  a different script, a recovery step, or stop-and-surface). Map outcomes → next actions explicitly.

### 7. Prerequisite SEQUENCE — the exact commands to reach the state this script needs
- **Not just "what must be true" — the ordered, runnable steps to GET there.** A blind agent cannot infer
  setup order from source; it needs the doc to lay out the path.
- List, IN ORDER, the commands/scripts to run before this one to bring the system to the required state,
  e.g.:
  1. `setup.py` (installs deps / drivers) — if not already done
  2. `<detect_board>` — confirms a supported board is connected and gets its id/port
  3. `<connect>` — establishes the SWD/serial session
  4. → THEN this script is valid to run
- **State the preconditions this script ASSUMES** (board detected, session open, firmware built, etc.)
  and, for each, **which earlier step/script satisfies it** — so the agent can trace back if a
  precondition is unmet.
- **Distinguish auto-handled vs. agent-must-run:** which preconditions the setup scripts handle
  automatically (per the Portability Playbook) vs. which the agent must explicitly run in sequence.
- If running out of order is a common failure, cross-reference it in §5 (symptom → "you skipped step N").

### 8. Verified / Pending verification
- Per the Coding Guidelines: which described behaviors are verified (run on real hardware / tested) vs.
  assumed. An UNVERIFIED behavior in a script-doc is especially dangerous — the agent will trust it.

---

## 2. QUALITY bar — write it for an agent operating blind

- **The failure-modes and logs sections are where docs usually fail — make them the most rigorous.**
  Every symptom the agent could see must map to a cause and a fix. If the agent sees output you didn't
  document, that's a gap to close, not the agent's problem.
- **Symptom-first, not cause-first.** The agent starts from what it *observes* (a log line, an exit
  code), not from the internal cause. Index failures by their visible symptom so the agent can go
  observation → diagnosis → fix.
- **No magic values.** If the script's output contains a number, code, or string the agent must
  interpret, the doc defines it. Apply origin tags where relevant.
- **Destructive operations get a prominent warning** in §2 and §5, with the gate/confirmation behavior
  described — consistent with the safety gates in `build_plan_concrete`.
- **Examples, not just descriptions.** Show real invocations and real (representative) output snippets so
  the agent can pattern-match what it sees against the doc.

---

## 3. SYNC: the script-doc moves with the script (zero tolerance for drift here)

- **A script change is not done until its doc is updated** — same unit of work, per the Doc-Sync
  Playbook. For script-docs this is absolute: a drifted script-doc actively misdirects the operating
  agent.
- **Any new input, log, output, failure mode, or behavior change → update the doc's matching section in
  the same commit.** Adding a log line the doc doesn't explain creates a blind spot the moment it ships.
- **If you change what a log means or what an exit code signals, the doc's §4/§5 MUST change with it** —
  the agent diagnoses from these; stale meanings cause wrong fixes.
- **A script with no doc, or a doc missing a mandatory §1–§8 section, is INCOMPLETE** and must not be
  considered shippable or agent-runnable.

---

## 4. Pre-commit script-doc check (run before committing any runnable script)
- [ ] The script has a doc with ALL mandatory sections §1–§8 present (none blank; N/A stated) (§1)
- [ ] §1 states WHEN to run AND when NOT to (with which script to run instead) — a real decision aid (§1)
- [ ] §7 gives the ordered, runnable PREREQUISITE COMMANDS to reach the state this script needs (§7)
- [ ] Every input/flag/env var/config key is documented with meaning, type, default, allowed values (§3)
- [ ] Every log line, output field, and exit code the script can emit is explained (§4)
- [ ] Every known failure maps symptom (visible in output) → cause → fix → what to rerun (§5, §6)
- [ ] Out-of-order / unmet-precondition failures cross-referenced between §5 and §7 (§7)
- [ ] Destructive behavior is prominently flagged; gate behavior described (§2)
- [ ] Hardware failure modes (board/port/lock/target/wiring) have distinguishing symptoms (§5)
- [ ] No behavior is discoverable only by reading the code — the doc fully substitutes for the source (§0)
- [ ] Doc updated in the SAME commit as the script; no new undocumented log/input/behavior (§3 sync)
- [ ] Verified vs. Pending-verification stated; UNVERIFIED behaviors marked (§8)

---

## The one-sentence version
**The operating agent never sees the code — only the doc and the script's output — so every runnable
script carries a doc that fully replaces reading it: when to run it vs. when to run something else, the
exact ordered commands to reach the state it needs, every input, every log/output/exit-code's meaning,
and every failure mapped from visible symptom to cause to fix to what-to-rerun — kept in lockstep with
the script, because a stale script-doc actively misdirects an agent operating blind.**
