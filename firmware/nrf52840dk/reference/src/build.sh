#!/usr/bin/env bash
# Build script: nRF52840-DK reference LED-blink firmware
#
# Outputs firmware/nrf52840dk/reference/build/firmware.elf
# (the canonical artifact name per README.md §Naming Rules -- PROJECT-DEFINED)
#
# If arm-none-eabi-gcc is not on PATH this script installs the official Arm
# GNU Embedded Toolchain cask via Homebrew (macOS only).  On other platforms,
# install arm-none-eabi-gcc manually and re-run.
#
# Usage:
#   bash firmware/nrf52840dk/reference/src/build.sh
#
# To flash after a successful build:
#   uv run pyocd load --target nrf52840 firmware/nrf52840dk/reference/build/firmware.elf

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/../build"
mkdir -p "${BUILD_DIR}"
BUILD_DIR="$(cd "${BUILD_DIR}" && pwd)"

# ---------------------------------------------------------------------------
# 1. Locate arm-none-eabi-gcc
# ---------------------------------------------------------------------------
find_arm_gcc() {
    # Check PATH first
    if command -v arm-none-eabi-gcc &>/dev/null; then
        command -v arm-none-eabi-gcc
        return 0
    fi
    # Arm GNU Toolchain cask (gcc-arm-embedded) installs under /Applications
    local found
    found=$(ls /Applications/ArmGNUToolchain/*/arm-none-eabi/bin/arm-none-eabi-gcc 2>/dev/null \
            | sort -V | tail -1)
    if [[ -x "${found:-}" ]]; then
        echo "${found}"
        return 0
    fi
    # Common Homebrew formula install paths
    for candidate in /opt/homebrew/bin/arm-none-eabi-gcc /usr/local/bin/arm-none-eabi-gcc; do
        if [[ -x "${candidate}" ]]; then
            echo "${candidate}"
            return 0
        fi
    done
    return 1
}

ARM_GCC=$(find_arm_gcc 2>/dev/null || true)

if [[ -z "${ARM_GCC}" ]]; then
    echo "[INFO] arm-none-eabi-gcc not found; attempting install via Homebrew..."
    if ! command -v brew &>/dev/null; then
        echo "[FAIL] Homebrew not found."
        echo "       Install Homebrew from https://brew.sh, then re-run this script."
        exit 1
    fi
    # gcc-arm-embedded is the official Arm GNU Toolchain cask -- VENDOR-FIXED
    brew install --cask gcc-arm-embedded
    ARM_GCC=$(find_arm_gcc 2>/dev/null || true)
    if [[ -z "${ARM_GCC}" ]]; then
        echo "[FAIL] arm-none-eabi-gcc still not found after cask install."
        echo "       Open a new terminal (to refresh PATH) and re-run, or set ARM_GCC=/path/to/arm-none-eabi-gcc."
        exit 1
    fi
fi

ARM_GCC_DIR="$(dirname "${ARM_GCC}")"
ARM_OBJCOPY="${ARM_GCC_DIR}/arm-none-eabi-objcopy"

echo "[INFO] Toolchain : ${ARM_GCC}"
echo "[INFO] Build dir : ${BUILD_DIR}"

# ---------------------------------------------------------------------------
# 2. Compile and link
# ---------------------------------------------------------------------------
# Target: Cortex-M4 with FPU -- HW-FIXED (nRF52840 PS §CPU: ARM Cortex-M4F)
"${ARM_GCC}" \
    -mcpu=cortex-m4 \
    -mthumb \
    -mfloat-abi=hard \
    -mfpu=fpv4-sp-d16 \
    -O1 \
    -Wall \
    -ffreestanding \
    -nostdlib \
    -nostartfiles \
    -T "${SCRIPT_DIR}/nrf52840.ld" \
    -Wl,--gc-sections \
    -o "${BUILD_DIR}/firmware.elf" \
    "${SCRIPT_DIR}/startup.c" \
    "${SCRIPT_DIR}/main.c"

echo "[PASS] Built: ${BUILD_DIR}/firmware.elf"

# Also produce a raw binary for reference (useful for size checks)
if [[ -x "${ARM_OBJCOPY}" ]]; then
    "${ARM_OBJCOPY}" -O binary "${BUILD_DIR}/firmware.elf" "${BUILD_DIR}/firmware.bin"
    echo "[INFO] Also wrote: ${BUILD_DIR}/firmware.bin ($(wc -c < "${BUILD_DIR}/firmware.bin") bytes)"
fi

echo ""
echo "Flash to board with one of:"
echo "  uv run pyocd load --target nrf52840 '${BUILD_DIR}/firmware.elf'"
echo "  uv run python stage0_check.py --board-id nrf52840dk --reference-firmware nrf52840dk='${BUILD_DIR}/firmware.elf'"
