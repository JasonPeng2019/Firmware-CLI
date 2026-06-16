# scratch/ — throwaway Step 1.0d harnesses

This folder is **not shipped**. It holds temporary harnesses that prove the pyOCD
**Python-API** path on real hardware before that logic is written into the shared
`src/pyocd_debug_mcp/services/` layer. Delete a harness once its operations are
proven and migrated.

## `api_target_control_harness.py`

Proves the three target-control operations `server.py` does not yet cover and that
`stage0_check.py` only exercises via subprocess: **silicon-ID read, flash, recover**.
Each is run through the pyOCD Python API and should match stage0's subprocess result.

### Oracle workflow (run stage0 first, then the harness, compare)

```powershell
# 1) subprocess truth (the proven path)
uv run python stage0_check.py --board-id nucleo_l476rg

# 2) API truth (the path being de-risked) — read-only by default
uv run python scratch/api_target_control_harness.py --board-id nucleo_l476rg --silicon-id
```

### Flash (needs an artifact)

```powershell
uv run python scratch/api_target_control_harness.py `
  --board-id nucleo_l476rg --flash `
  --firmware firmware/nucleo_l476rg/reference/build/firmware.elf
```

Artifacts present in the repo today: `nucleo_l476rg` and `nrf52833dk`
(`reference/build/firmware.{elf,hex}`). **`nrf52840dk` has none yet** — build one
before flashing that board.

### Recover / unlock (DESTRUCTIVE — mass erase)

Only meaningful on a board whose `recover_mode` is `nrf_pyocd_unlock`. Irreversibly
wipes the chip, so it is double-gated:

```powershell
uv run python scratch/api_target_control_harness.py `
  --board-id nrf52833dk --recover --confirm-recover
```

## Suggested validation order

1. **`nucleo_l476rg`** first — has a flash artifact, ST-Link has no destructive
   recover, and it closes the "Continue From Here" STM32/ST-Link gap.
2. **A Nordic board** (`nrf52833dk`, which has an artifact) for flash + recover.

A probe is selected by `--probe-uid` or the `PYOCD_PROBE_UID` in `.env`.
