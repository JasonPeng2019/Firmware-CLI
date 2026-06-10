# Tests Tree

This tree is the canonical home for repo-owned validation assets.

Phase A only adds rough scaffolding so later work lands in one stable place.

Intended layout:

- `tests/fixtures/`: shared static data and captured samples
- `tests/cases/`: benchmark and injected-bug case definitions
- `tests/harness/`: harness code and reusable test helpers

Keep bug-variant source trees under `firmware/<board>/bugs/`. Keep harness and
test definitions under `tests/`.
