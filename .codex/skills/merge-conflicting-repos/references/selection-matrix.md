# Selection Matrix

Use this matrix after the initial diff inventory and scratch merge probe.

## 1. Same file, same problem

Signals:

- both sides changed the same module or contract
- both changes address the same bug, feature, or workflow
- the merge conflict is semantic, not just textual

Resolution:

- choose one implementation as the owner
- prefer:
  - better layering
  - stronger tests
  - cleaner public contract
  - fewer special cases
  - better doc-sync
- port additive improvements from the losing side if they strengthen the owner
  implementation without reopening the design

Do not:

- keep both implementations in parallel
- mix two incompatible contracts just because each side had one good idea

## 2. Same file, different problem

Signals:

- both sides touched the same file, but the changes solve different things
- one side is bug-fix hardening while the other is a feature addition

Resolution:

- keep both if they compose cleanly and help the goal
- if they do not compose, preserve the goal-critical change first and then
  reintroduce the other in the cleanest layer

## 3. Different files, goal-relevant addition

Signals:

- one side adds tests, docs, harnesses, or adjacent code that the other side
  never touched

Resolution:

- bring it in if it helps the merge goal or materially improves trust
- validate it in the same pass as the rest of the merge

## 4. Different files, goal-irrelevant churn

Signals:

- old notes
- stale temp files
- abandoned experiments
- docs that no longer describe the chosen implementation

Resolution:

- archive if historically useful
- otherwise delete

## 5. Validation ladder after selection

Run validation in this order:

1. static checks
2. targeted tests for overlapping features
3. broader smoke or integration harnesses
4. hardware validation when relevant
5. full application or benchmark runs when the goal requires them

If any step fails:

- route the defect through the repo's bug-fix workflow
- re-run the failing targeted check
- then re-run the broader ladder
