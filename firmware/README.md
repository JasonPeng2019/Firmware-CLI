# Firmware Tree

This tree is for **repo-owned test firmware only**.

It is where the project will keep:

- known-good reference firmware source trees
- known-good built baseline artifacts
- recovery images used by later safety and unlock flows
- injected-bug variants used by the test harness

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

See the root [README.md](../README.md) for the repo-wide naming standard.
