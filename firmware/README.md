# Firmware Tree

This tree is for **repo-owned test firmware only**.

It is where the project will keep:

- known-good reference firmware source trees
- known-good built baseline artifacts
- recovery images used by later safety and unlock flows
- injected-bug variants used by the test harness

Phase A may commit the canonical directory scaffolding before `R4` baseline
artifacts are actually populated. The layout is stable early; the known-good
build outputs arrive when the reference baselines are validated.

This tree is **not** for a user’s own firmware project.

User firmware remains outside this repo and will be supplied later as runtime
input. Nothing in `boards/<board>.yaml` should hardcode user-project paths,
build commands, or artifact paths.

Canonical layout per board:

```text
firmware/<board>/
├── reference/src/
├── reference/build/
├── recovery/
└── bugs/
```

Canonical naming rules:

- symbol-bearing baseline artifact:
  `firmware/<board>/reference/build/firmware.elf`
- bug variants:
  `firmware/<board>/bugs/<id>__<slug>/`

Stage 0 still takes reference firmware as a runtime input. Until the canonical
baseline artifact for a board actually exists, pass the path explicitly with
`--reference-firmware BOARD_ID=PATH`.

See the root [README.md](../README.md) for the repo-wide naming standard.
