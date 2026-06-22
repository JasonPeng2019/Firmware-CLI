> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# stm32 build r11 turnkey

## Goal in plain English

Task: Make the STM32 rebuild path Windows/macOS-safe, self-contained, and agent-runnable without assuming preinstalled NCS, sync Zephyr build docs, then fully retest STM32 R11 on the attached bench
Roadmap anchor: `R11` closure for the scoped STM32 benchmark path, with the build substrate shaped for the `R12` turnkey brain direction

## Scope and non-scope

In scope:

- replace bash/WSL-only repo-owned Zephyr rebuild assumptions with one repo-owned cross-platform CLI entrypoint
- let that entrypoint reuse `NCS` when present but bootstrap upstream Zephyr + SDK when `NCS` is absent
- wire the entrypoint into the tracked STM32 / Nordic repo-owned reference and bug build flows
- update setup/docs so an agent can infer exactly how to provision build prerequisites and invoke builds
- rerun the non-hardware ladder, then the live STM32 `R11` suite on the attached bench and fix regressions found during that run

Out of scope:

- arbitrary non-Zephyr user firmware projects outside the repo
- adding STM32CubeIDE project generation/export
- claiming managed Zephyr SDK install support on macOS `x86_64` beyond what current Zephyr officially supports

## Reconciliation summary

- Build plan:
- the product direction explicitly requires the agent to edit code, rebuild it, flash it, and verify it; rebuild is not optional
- Current code:
- `R11` benchmark bug cases on Windows still shell through `bash -lc`, which fails on hosts without WSL
- copied STM32 bug workspaces currently drop `firmware/<board>/common`, so their relative overlay/include paths break
- build docs still imply a preexisting Zephyr workspace / SDK rather than a repo-owned bootstrap path
- Other docs or notes:
- live probe detection on this host reports the attached board as `NUCLEO-L476RG` / target `stm32l476rgtx`
- current host also has `NCS v3.3.1`, which can be reused for validation but must not be a product requirement
- Disagreements:
- repo history includes Intel-mac bench notes for older Zephyr SDKs, while current official Zephyr docs no longer support managed macOS `x86_64` SDK installs; document the limitation honestly instead of papering over it

## Design

- add `pyocd-zephyr-build`, a repo-owned Python CLI that:
  - runs under `uv`
  - reuses existing Zephyr workspaces (`ZEPHYR_WORKSPACE_DIR`, `ZEPHYR_BASE`, current `west` workspace, `~/zephyrproject`, detected `NCS`) when available
  - otherwise bootstraps a managed upstream Zephyr workspace pinned to `v4.3.0`
  - reuses `ZEPHYR_SDK_INSTALL_DIR` / standard SDK locations / adjacent `NCS` SDKs when available
  - otherwise installs the needed SDK component with `west sdk install`
  - builds any repo-owned Zephyr app into the canonical `firmware.elf` / `firmware.hex` outputs
- change the tracked shell wrappers to delegate to that helper, keeping bash compatibility while making the real contract cross-platform
- change `R11` injected-bug case manifests to use `uv run pyocd-zephyr-build ...` directly so benchmark rebuilds are Windows-safe
- make copied benchmark workspaces carry board-level `common/` assets when present
- keep Stage 0 setup separate from build bootstrap, but add an explicit setup-script flag that provisions the local build env when needed

## Board-facts-as-data and origin tags

## Documentation plan

- root docs: explain that `NCS` is optional and record the canonical `pyocd-zephyr-build` commands
- setup docs: add the opt-in build bootstrap flags and the direct `--ensure-only` flow
- board runbooks: replace bash-only recipes with cross-platform `uv run pyocd-zephyr-build ...` commands

## Portability

- primary supported managed-bootstrap hosts: Windows and macOS Apple Silicon
- existing `NCS` installs are reused but not required
- Intel macOS remains a documented limitation for managed SDK install under current Zephyr; allow reuse of a preinstalled older supported SDK via `ZEPHYR_SDK_INSTALL_DIR`

## Verification plan

- unit tests for the new Zephyr helper and updated `R11` workspace/build-command behavior
- repo checks for the touched Python/tests/docs
- real local firmware rebuild on the attached Windows host
- Stage 0 + Stage 1 preflight
- full live STM32 `R11` run, fixing failures until the suite is green or a true blocker remains

## Acceptance criteria

- a fresh agent can discover one documented command path that provisions Zephyr build prerequisites without assuming preinstalled `NCS`
- the tracked STM32 `R11` bug cases can rebuild on Windows without WSL/bash requirements
- the repo-owned STM32 reference and bug builds are invokable through the same cross-platform helper
- the attached `nucleo_l476rg` bench passes the implemented STM32 `R11` suite after fixes

## Verified

- actual attached board on this host resolves to `NUCLEO-L476RG` / `stm32l476rgtx`
- current Windows `R11` rebuild path is broken before this step because `_run_build_command()` shells via `bash -lc`
- copied STM32 benchmark workspaces omit `common/` and therefore break the new shared STM32 overlay/include wiring

## Pending verification

- unit/lint pass for the new helper and harness changes
- real Windows build through `pyocd-zephyr-build`
- live Stage 0 / Stage 1 / STM32 `R11`
