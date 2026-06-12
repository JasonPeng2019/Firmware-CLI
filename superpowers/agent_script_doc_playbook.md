# Script-Doc Playbook - Every Runnable Script Has a Doc That Fully Replaces Reading It

> **Why this exists.** In operation, the agent driving this product **cannot see the source code.** It
> can only *run* a script and *read what the script emits* (logs, output, exit codes). Therefore each
> script's `.md` is not documentation-for-humans - it is the **operating agent's ONLY model of what the
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
> If a workflow spans multiple scripts, this playbook ALSO requires a separate operator guide; script
> docs and workflow docs are complementary, not interchangeable.

---

## 0. THE PRINCIPLE: the doc is the interface; the code is invisible

- The operating agent reasons about a script **only** through (1) this doc and (2) the script's runtime
  output. It will never read the source. Write the doc accordingly - completeness is not optional polish,
  it is the difference between the agent operating correctly and operating blind.
- **No behavior may be "discoverable only by reading the code."** If the script does it, the doc says it.
  Hidden behavior = behavior the agent cannot account for = wrong agent decisions.
- **Every observable the script emits must be explained.** If a log line, output field, or exit code can
  appear, the doc must tell the agent what it means and what to do about it. An unexplained output is a
  blind spot.
- This makes script-docs the HIGHEST-drift-risk docs in the project: a doc that lags the code doesn't
  just mislead a human, it directs the operating agent to wrong actions. The Doc-Sync Playbook applies to
  these with maximum force - see Section 3.

## 0b. Two doc types: script-docs vs. operator guides

- **Script-doc:** the doc for ONE runnable script, or tightly-coupled OS variants of the same script.
  Its job is to fully replace reading that script's source.
- **Operator guide / workflow doc:** the doc for ONE multi-step workflow or stage that spans MULTIPLE
  scripts. Its job is to tell the agent which script to run first, what information carries forward, and
  how to branch between scripts.
- **Do not merge these roles accidentally.** A workflow doc must not masquerade as the script doc for a
  specific executable, and a script doc must not try to become the entire workflow manual.
- **When an operator guide is required:** if success depends on sequencing multiple scripts, choosing
  between scripts, or carrying outputs from one script into another, you need BOTH:
  1. one script-doc per runnable script
  2. one operator guide for the cross-script workflow
- **How they reference each other:** the operator guide links to script-docs for exact CLI/output
  semantics; the script-doc's "when not to run" section can point back to the operator guide when the
  right choice depends on broader workflow state.

---

## 1. MANDATORY template - every script-doc has ALL of these sections

No section may be omitted. "Not applicable" must be stated explicitly, not left blank.

### 1. Purpose & when to run vs. when NOT to run (a real decision aid)
- One-paragraph plain statement of what the script does.
- **WHEN to run it:** the specific situation(s) where THIS script is the correct choice. State the
  triggering conditions an agent can check from observable state ("run this when a board is connected and
  detected but not yet flashed", not "run this to flash").
- **WHEN NOT to run it:** the situations where it's the WRONG choice - and **which script to run
  instead.** A blind agent choosing among several scripts needs the doc to disambiguate: "if you need X
  instead, run `<other_script>`; if the board isn't detected yet, run `<detect_script>` first." Without
  this, the agent picks wrong when multiple scripts look superficially applicable.
- If the "run this other thing instead" answer depends on a larger multi-step flow, point to the
  operator guide explicitly rather than trying to compress the full workflow into this section.
- **Conflicting states:** conditions under which running it is unsafe or meaningless (e.g. a flash script
  while a live-monitor session holds the SWD connection).

### 2. Exact behavior (step by step)
- What the script actually does, in order, in enough detail that the agent can predict its effect
  without seeing the code. Side effects (files written, hardware touched, state changed) called out
  explicitly. Note anything destructive/irreversible (e.g. flash, mass-erase) prominently.

### 3. Inputs - every option, what it does, what it means
- EVERY input the script accepts: flags, arguments, env vars, config keys. For each: name, type,
  required/optional, default, allowed values/range, and **what it actually changes in behavior.** No
  input may be undocumented. Include examples of valid invocations.

### 4. Outputs & logs - what every emission MEANS
- Every log line / output field / status the script can emit, and what each one tells the agent.
- Group by meaning: normal-progress logs vs. warnings vs. errors. For each meaningful log, state what it
  implies about the script's state and whether action is needed.
- Exit codes / return status: enumerate each and its meaning.

### 5. Failure modes - exactly why it fails and how to fix
- A table/list of every known failure: **symptom (what the agent will see in the output) -> cause -> fix /
  next action.** This is the most important section - the agent diagnoses failures ONLY from output, so
  every failure must be traceable from its visible symptom to its remedy.
- Include hardware-specific failures (board not found, port busy, locked chip / APPROTECT, wrong target,
  wiring/power) with their distinguishing symptoms, since "is it code or hardware" is core to the product.
- For each fix, state **what to rerun** and with what inputs.

### 6. Rerun guidance - for each outcome, what to do next
- Given a particular log/result, what the agent should run next (this script again with different inputs,
  a different script, a recovery step, or stop-and-surface). Map outcomes -> next actions explicitly.

### 7. Prerequisite SEQUENCE - the exact commands to reach the state this script needs
- **Not just "what must be true" - the ordered, runnable steps to GET there.** A blind agent cannot infer
  setup order from source; it needs the doc to lay out the path.
- List, IN ORDER, the commands/scripts to run before this one to bring the system to the required state,
  e.g.:
  1. `setup.py` (installs deps / drivers) - if not already done
  2. `<detect_board>` - confirms a supported board is connected and gets its id/port
  3. `<connect>` - establishes the SWD/serial session
  4. -> THEN this script is valid to run
- **State the preconditions this script ASSUMES** (board detected, session open, firmware built, etc.)
  and, for each, **which earlier step/script satisfies it** - so the agent can trace back if a
  precondition is unmet.
- **Distinguish auto-handled vs. agent-must-run:** which preconditions the setup scripts handle
  automatically (per the Portability Playbook) vs. which the agent must explicitly run in sequence.
- If running out of order is a common failure, cross-reference it in Section 5 (symptom -> "you skipped step N").

### 8. Verified / Pending verification
- Per the Coding Guidelines: which described behaviors are verified (run on real hardware / tested) vs.
  assumed. An UNVERIFIED behavior in a script-doc is especially dangerous - the agent will trust it.

---

## 2. QUALITY bar - write it for an agent operating blind

- **The failure-modes and logs sections are where docs usually fail - make them the most rigorous.**
  Every symptom the agent could see must map to a cause and a fix. If the agent sees output you didn't
  document, that's a gap to close, not the agent's problem.
- **Symptom-first, not cause-first.** The agent starts from what it *observes* (a log line, an exit
  code), not from the internal cause. Index failures by their visible symptom so the agent can go
  observation -> diagnosis -> fix.
- **No magic values.** If the script's output contains a number, code, or string the agent must
  interpret, the doc defines it. Apply origin tags where relevant.
- **Destructive operations get a prominent warning** in Section 2 and Section 5, with the gate/confirmation
  behavior described - consistent with the safety gates in `build_plan_concrete`.
- **Examples, not just descriptions.** Show real invocations and real (representative) output snippets so
  the agent can pattern-match what it sees against the doc.

---

## 3. SYNC: the script-doc moves with the script (zero tolerance for drift here)

- **A script change is not done until its doc is updated** - same unit of work, per the Doc-Sync
  Playbook. For script-docs this is absolute: a drifted script-doc actively misdirects the operating
  agent.
- **Any new input, log, output, failure mode, or behavior change -> update the doc's matching section in
  the same commit.** Adding a log line the doc doesn't explain creates a blind spot the moment it ships.
- **If you change what a log means or what an exit code signals, the doc's Section 4/Section 5 MUST change with it** -
  the agent diagnoses from these; stale meanings cause wrong fixes.
- **A script with no doc, or a doc missing a mandatory Section 1-Section 8 section, is INCOMPLETE** and must not be
  considered shippable or agent-runnable.
- **If a workflow change alters script ordering, handoffs, or decision branches across multiple scripts,
  update the operator guide in the SAME unit of work.** Script-docs do not replace workflow docs.

---

## 3b. Operator guides - when they are required and what they contain

An operator guide is REQUIRED when:

- a stage or task spans multiple scripts
- the agent must choose between scripts based on runtime state
- outputs from one script become inputs or prerequisites for another
- troubleshooting requires branching across scripts rather than rerunning one script in isolation

An operator guide must contain, at minimum:

1. **Purpose of the workflow/stage**
2. **Entry conditions:** when this workflow is the right one
3. **Ordered sequence:** exact commands/scripts to run, in order
4. **Branch points:** if X happens, run script A; if Y happens, run script B
5. **Handoffs:** what information from each step must be carried forward
6. **Cross-script troubleshooting:** common failure branches that require switching scripts
7. **Links to the script-docs** for each runnable script in the workflow
8. **Verified / Pending verification**

Operator guides SHOULD NOT:

- duplicate every flag/log/output from each script-doc
- replace the script-doc for any runnable script
- silently become the only documentation for a script

---

## 4. Pre-commit script-doc check (run before committing any runnable script)
- [ ] The script has a doc with ALL mandatory sections Section 1-Section 8 present (none blank; N/A stated) (Section 1)
- [ ] Section 1 states WHEN to run AND when NOT to (with which script to run instead) - a real decision aid (Section 1)
- [ ] Section 7 gives the ordered, runnable PREREQUISITE COMMANDS to reach the state this script needs (Section 7)
- [ ] Every input/flag/env var/config key is documented with meaning, type, default, allowed values (Section 3)
- [ ] Every log line, output field, and exit code the script can emit is explained (Section 4)
- [ ] Every known failure maps symptom (visible in output) -> cause -> fix -> what to rerun (Section 5, Section 6)
- [ ] Out-of-order / unmet-precondition failures cross-referenced between Section 5 and Section 7 (Section 7)
- [ ] Destructive behavior is prominently flagged; gate behavior described (Section 2)
- [ ] Hardware failure modes (board/port/lock/target/wiring) have distinguishing symptoms (Section 5)
- [ ] No behavior is discoverable only by reading the code - the doc fully substitutes for the source (Section 0)
- [ ] Doc updated in the SAME commit as the script; no new undocumented log/input/behavior (Section 3 sync)
- [ ] Verified vs. Pending-verification stated; UNVERIFIED behaviors marked (Section 8)
- [ ] If the change affects a multi-script workflow, the operator guide was updated too (Section 3b)

---

## The one-sentence version
**The operating agent never sees the code - only docs and runtime output - so every runnable script gets
a script-doc that fully replaces reading its source, and every multi-script workflow gets an operator
guide that explains sequence and branching across those scripts; both must move in lockstep with the
code, because stale docs actively misdirect an agent operating blind.**
