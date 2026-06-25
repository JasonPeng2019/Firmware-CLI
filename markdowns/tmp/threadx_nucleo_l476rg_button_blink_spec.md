# ThreadX Nucleo-L476RG Button Blink Spec

This document is the retained STM32-only scaffold spec for the first real
ThreadX path in the repo.

It does **not** change the current scoped `R11` / `R12` acceptance surface.
It does **not** replace the current canonical Zephyr reference/benchmark path.
It does **not** add ThreadX to the current benchmark corpus.

The goal is narrower:

- define one real ThreadX workspace for `nucleo_l476rg`
- make it buildable and flashable through a repo-owned path
- make its behavior observable enough for manual validation now and turnkey
  freeform use later

## Scope And Reconciliation

Frozen scope:

- board: `nucleo_l476rg`
- RTOS: `ThreadX`
- app behavior:
  - LED blinks slowly by default
  - button press toggles to fast blink
  - next button press toggles back to slow blink
- validation mode:
  - manual bench runbook first
  - no `R11` / `R12` benchmark integration in this pass
  - no Nordic ThreadX mirror in this pass

Current repo truth that must remain stable:

- canonical reference firmware and benchmark fixtures are currently Zephyr-based
- the 12-case `R11` / `R12` acceptance corpus remains unchanged
- the scoped pair remains unchanged
- the turnkey benchmark schema and score contract remain unchanged

Important reconciliation:

- keep ThreadX outside `reference/`
- keep ThreadX outside `tests/cases/`
- keep ThreadX outside current acceptance gates
- treat this as a retained manual path that is future-turnkey-compatible by
  design

## Upstream Source Strategy

The ThreadX scaffold must be based on the official STM32 Azure RTOS path for
the STM32L4 family.

Frozen upstream/reference source:

- ST `x-cube-azrtos-l4`
- official repo:
  - `https://github.com/STMicroelectronics/x-cube-azrtos-l4`

Important nuance from the official package:

- the package is an official Azure RTOS integration path for STM32L4
- the published ready-to-run application boards in the upstream package are not
  `NUCLEO-L476RG`
- therefore the first `nucleo_l476rg` ThreadX path should be framed as an
  **ST-package-derived retained port**, not as a copied official L476RG sample

Frozen rules:

- do **not** invent a home-grown ThreadX port from scratch
- do **not** make STM32CubeIDE GUI generation part of the normal validation
  path after the scaffold is committed
- do **not** oversell the path as fresh-machine-portable in the same way the
  managed Zephyr flow is

## Repo Layout

Freeze the retained ThreadX path at:

```text
firmware/nucleo_l476rg/threadx/button_blink/
├── README.md
├── build_threadx.sh
├── project/
└── build/
```

Use `project/`, not `src/`, so the layout truthfully reflects a checked-in
STM32 ThreadX project with middleware/startup/linker/build-system files rather
than pretending it matches the current Zephyr app layout.

Rules:

- `README.md` is the canonical human/operator runbook for this retained path
- `build_threadx.sh` is the single repo-owned build entrypoint
- `project/` holds the checked-in STM32 ThreadX project
- `build/` holds generated artifacts and should be kept consistent with the
  repo’s existing artifact expectations

## Build Contract

Frozen build strategy:

- normal use builds from the checked-in project through `build_threadx.sh`
- normal use does not require opening STM32CubeIDE interactively
- this path may depend on explicit STM32/Azure RTOS toolchain prerequisites
- this path is intentionally outside the current “managed Zephyr on a fresh
  machine” promise

The later implementation must make `build_threadx.sh` responsible for:

- validating the required STM32 ThreadX toolchain/runtime prerequisites
- invoking the checked-in project build non-interactively
- placing final artifacts under `build/`
- exposing one canonical symbol-bearing ELF
- exposing one flashable HEX when the toolchain can emit it

Frozen artifact expectations:

- symbol-bearing artifact:
  - `firmware/nucleo_l476rg/threadx/button_blink/build/firmware.elf`
- flash artifact:
  - `firmware/nucleo_l476rg/threadx/button_blink/build/firmware.hex`
  - if a HEX cannot be emitted cleanly, the README must state that ELF is the
    flash artifact for this retained path

## Application Behavior Contract

The retained ThreadX app must implement exactly this behavior:

- on boot, the LED enters slow blink mode
- on each confirmed button press, the app toggles between:
  - slow blink
  - fast blink
- subsequent button presses continue toggling those two states

Frozen implementation-level expectations:

- use board/BSP definitions for the user LED and user button
- do **not** introduce ad hoc raw pin constants unless the vendor-generated
  project leaves no cleaner option
- debounce strategy may be simple, but it must be deterministic enough for a
  manual bench run

## Observability Contract

The app must be externally observable enough for both manual validation now and
turnkey freeform reasoning later.

Frozen UART contract:

- emit one ready line on boot
- emit one line on each mode change

Recommended messages:

- boot:
  - `threadx ready`
- mode changes:
  - `blink slow`
  - `blink fast`

Frozen symbol contract:

- export one symbol-bearing state variable named:
  - `threadx_blink_mode`

Frozen value convention:

- `0` = slow blink
- `1` = fast blink

Rules:

- the symbol must live in normal target memory so the existing debug substrate
  can read it
- the symbol and UART contracts should stay simple and explicit
- the future turnkey path should be able to reason from:
  - boot UART
  - mode-change UART
  - direct symbol readback

## Validation Runbook Shape

This retained path is manual-path first.

The README for the later scaffold must give one exact runbook in this order:

1. build the ThreadX app
2. flash the built artifact
3. observe the boot UART line
4. confirm the LED starts in slow blink mode
5. press the button once and confirm:
   - LED changes to fast blink
   - UART reports `blink fast`
6. press the button again and confirm:
   - LED changes back to slow blink
   - UART reports `blink slow`
7. optionally read back `threadx_blink_mode` through the existing debug surface
   and confirm the logical value matches the observed mode

This remains a bench runbook, not a benchmark-scored case.

## Future Turnkey Integration Seam

This scaffold should not be a dead end. Freeze the future hand-off now.

A later turnkey freeform run should be able to use:

- `--workspace-root firmware/nucleo_l476rg/threadx/button_blink/project`
- `--build-command ./build_threadx.sh`

That future path assumes:

- the checked-in project is self-contained enough to rebuild from the repo
- the UART and symbol contracts are stable
- the build script is deterministic enough for agent-driven reruns

This pass does **not** add:

- benchmark-case manifests
- benchmark scoring
- benchmark-runner changes
- scoped acceptance updates

## What Must Not Change In This Pass

Do not change:

- `tests/cases/suites.yaml`
- the current 12-case `R11` / `R12` acceptance corpus
- the canonical Zephyr `reference/build/firmware.elf` contract
- the scoped pair definition
- the current turnkey benchmark runner and score schema

Document the ThreadX path explicitly as:

- retained
- manual-path first
- outside current acceptance gates
- future-turnkey-compatible by design

## Implementation Acceptance For The Later Scaffold Pass

The later implementation is acceptable only if:

- the repo gains
  `firmware/nucleo_l476rg/threadx/button_blink/` with the frozen layout
- `build_threadx.sh` is the single repo-owned build entrypoint
- the committed project emits a flashable ELF and HEX or explicitly documents
  the final flash-artifact fallback
- the README gives one exact manual bench sequence
- the app exposes:
  - one boot UART line
  - one mode-change UART line on each toggle
  - one symbol for current blink mode
- no `R11` / `R12` benchmark or scoped acceptance files are changed

## Verified

- The current repo was re-checked and does not contain a real ThreadX workspace
  or tracked ThreadX build path.
- The current canonical firmware/build/benchmark path is Zephyr-only:
  - tracked `reference/` apps build through `pyocd-zephyr-build`
  - current benchmark fixtures are Zephyr-derived
- The STM32 board facts for this retained path were grounded from
  `boards/nucleo_l476rg.yaml`.
- The official STM32 Azure RTOS L4 package was confirmed at:
  - `https://github.com/STMicroelectronics/x-cube-azrtos-l4`
- The official package supports STM32L4 Azure RTOS integration, but its
  published ready-to-run application boards are not `NUCLEO-L476RG`.

## Pending Verification

- The exact non-interactive build mechanics for the retained `nucleo_l476rg`
  ThreadX project still need to be proven in a later scaffold/build pass.
- The exact UART route for the retained ThreadX app still needs bench proof on
  the physical board.
- The exact LED/button BSP mapping for the retained ThreadX project still needs
  to be fixed from the checked-in STM32 project used in the later scaffold
  pass.
