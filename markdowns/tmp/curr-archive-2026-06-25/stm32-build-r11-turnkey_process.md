# Process ledger for stm32-build-r11-turnkey

## Goal and roadmap anchor

Task: Implement and validate the portable STM32 rebuild substrate and complete the live STM32 R11 retest
Roadmap anchor: `R11` STM32 benchmark closure, with implementation shaped for the `R12` turnkey-agent direction

## Done

- reconciled product intent against the repo docs: rebuild/flash/verify is a real product requirement, not an operator-only convenience
- confirmed the attached hardware resolves as `NUCLEO-L476RG` / `stm32l476rgtx` through the shared pyOCD probe path
- reproduced the Windows benchmark rebuild failure: current `R11` harness still runs `bash -lc ...`, which fails immediately on this host without WSL
- reproduced the STM32 copied-workspace defect: the benchmark workspace did not include `firmware/nucleo_l476rg/common/`, so relative overlay/include paths would fail even after the shell issue was fixed
- added `pyocd-zephyr-build`, the repo-owned cross-platform Zephyr bootstrap/build helper
- wired the tracked shell build wrappers to delegate to that helper
- switched tracked `R11` injected-bug case manifests to cross-platform `uv run pyocd-zephyr-build ...` commands
- updated the benchmark harness to use `cmd.exe` on Windows and to copy board-level `common/` assets into copied workspaces
- updated root/setup/board docs plus setup scripts so the build bootstrap path is explicit and agent-runnable
- fixed the helper's same-directory artifact copy bug, which had been deleting the live Zephyr build tree before copying canonical artifacts
- changed the helper to default to incremental `west build -p auto` rebuilds so repeated agent edit/build loops stay fast
- fixed helper artifact discovery for Nordic sysbuild outputs, so canonical `firmware.elf` / `firmware.hex` refresh correctly across STM32 and Nordic boards
- rebuilt the tracked STM32 reference artifact on Windows through the managed helper
- rebuilt the tracked Nordic reference artifacts on Windows through the same helper (`nrf52833dk`, `nrf52840dk`)
- confirmed the attached Windows STM32 bench still has a UART-observability blocker even after the firmware-side console-path cleanup
- proved that the blocker is not specific to repo firmware by rebuilding/flashing upstream Zephyr `samples/hello_world` for `nucleo_l476rg` and observing the same silent COM port

## In progress

- documenting the final live-bench status and remaining physical blocker clearly enough for the next agent/operator handoff

## TODO

- rerun the live STM32 `R11` green/reference case once the current bench UART path is restored
- if the same board is intended for final closure, verify the ST-LINK VCP solder-bridge/driver path on the Windows host before spending more time on repo firmware

## Limitations and known gaps

- managed Zephyr SDK install is intentionally documented as unsupported on macOS `x86_64` under current Zephyr releases; those hosts must reuse a preinstalled older supported SDK
- this step creates a reusable Zephyr build substrate for the repo's Zephyr-based boards, not a universal exporter for arbitrary non-Zephyr customer firmware projects
- the attached Windows `nucleo_l476rg` bench currently fails the UART half of Stage 0 even for upstream Zephyr `hello_world`; until that bench issue is cleared, the live STM32 `R11` green case cannot honestly be called complete

## Hardware hand-off

## Open decisions and surfaced issues

- the repo historically recorded Intel-mac Zephyr bench notes; keep those as historical facts, but do not present them as current managed-bootstrap support
- user stated `stm32l474rg`, but the actual attached hardware detected by pyOCD is `NUCLEO-L476RG`; continue against the detected board unless hardware changes mid-run
- treat "repo firmware silent + upstream hello_world silent" as the decision boundary for a bench UART blocker on this board family

## Verified

- attached probe UID `0670FF3031454D3043223536`, board `NUCLEO-L476RG`, target `stm32l476rgtx`
- `NCS v3.3.1` + bundled Zephyr SDK exist on this host and are reusable for validation, but the new path no longer requires them conceptually
- `uv run pytest tests/test_zephyr_build.py tests/test_r11_benchmark.py` passes after the helper/harness changes
- `uv run ruff check src/pyocd_debug_mcp/zephyr_build.py tests/test_zephyr_build.py tests/test_r11_benchmark.py` passes
- managed-helper STM32 rebuild on Windows now completes in about 26s from a cleanish build tree and about 4.6s on an immediate incremental rerun
- managed-helper Nordic rebuilds now refresh canonical artifacts on Windows too (`nrf52833dk` about 1.7s on rerun, `nrf52840dk` about 36s on first run here)
- `host_bootstrap.py --board-id nucleo_l476rg` passes on the attached Windows host
- `stage0_check.py --board-id nucleo_l476rg --reference-firmware ...` passes probe visibility, target attach, pack availability, COM-port visibility, and flash, but fails UART observation
- direct bench control sample: upstream Zephyr `hello_world` for `nucleo_l476rg` also flashes and runs but produces no UART bytes on `COM9`

## Pending verification

- full live STM32 `R11` benchmark result on a bench where UART observability is healthy
