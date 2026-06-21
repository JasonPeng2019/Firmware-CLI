#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${SCRIPT_DIR}/src"
CANONICAL_BUILD_DIR="${SCRIPT_DIR}/build"
WORKSPACE_DIR="${ZEPHYR_WORKSPACE_DIR:-$HOME/zephyrproject}"
BOARD="${BOARD:-nucleo_l476rg}"
WEST_VENV_DIR="${FIRMWARE_CLI_ZEPHYR_WEST_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/firmware-cli-zephyr-west}"

ensure_west_runner() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "error: 'python3' not found in PATH" >&2
    exit 1
  fi

  if [[ ! -x "${WEST_VENV_DIR}/bin/west" ]]; then
    python3 -m venv "${WEST_VENV_DIR}" >&2
    "${WEST_VENV_DIR}/bin/pip" install --upgrade pip >&2
    "${WEST_VENV_DIR}/bin/pip" install west pyelftools >&2
  fi

  printf '%s\n' "${WEST_VENV_DIR}/bin/west"
}

find_sdk_dir() {
  if [[ -n "${ZEPHYR_SDK_INSTALL_DIR:-}" && -d "${ZEPHYR_SDK_INSTALL_DIR}" ]]; then
    printf '%s\n' "${ZEPHYR_SDK_INSTALL_DIR}"
    return 0
  fi

  local candidates=(
    "$HOME/zephyr-sdk-1.0.1"
    "$HOME/zephyr-sdk-1.0.0"
    "$HOME/zephyr-sdk-0.17.4"
    "$HOME/.local/opt/zephyr-sdk-1.0.1"
    "$HOME/.local/opt/zephyr-sdk-1.0.0"
    "$HOME/.local/opt/zephyr-sdk-0.17.4"
    "/usr/local/zephyr-sdk-1.0.1"
    "/usr/local/zephyr-sdk-1.0.0"
    "/usr/local/zephyr-sdk-0.17.4"
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

WEST_BIN="$(ensure_west_runner)"

if [[ ! -d "${WORKSPACE_DIR}/zephyr" ]]; then
  echo "error: Zephyr workspace not found at ${WORKSPACE_DIR}" >&2
  echo "set ZEPHYR_WORKSPACE_DIR to a workspace containing zephyr/" >&2
  exit 1
fi

SDK_DIR="$(find_sdk_dir || true)"
if [[ -z "${SDK_DIR}" ]]; then
  echo "error: no Zephyr SDK installation found" >&2
  echo "set ZEPHYR_SDK_INSTALL_DIR or install a Zephyr SDK under a standard path" >&2
  exit 1
fi

export ZEPHYR_BASE="${WORKSPACE_DIR}/zephyr"
export ZEPHYR_TOOLCHAIN_VARIANT=zephyr
export ZEPHYR_SDK_INSTALL_DIR="${SDK_DIR}"

WORK_APP_DIR="${APP_DIR}"
WORK_BUILD_DIR="${CANONICAL_BUILD_DIR}"
SCRATCH_DIR=""

case "${APP_DIR} ${CANONICAL_BUILD_DIR}" in
  *" "*)
    SCRATCH_DIR="$(mktemp -d "${TMPDIR:-/tmp}/nucleo_l476rg-b003-build.XXXXXX")"
    trap '[[ -n "${SCRATCH_DIR}" ]] && rm -rf "${SCRATCH_DIR}"' EXIT
    ln -s "${APP_DIR}" "${SCRATCH_DIR}/app"
    WORK_APP_DIR="${SCRATCH_DIR}/app"
    WORK_BUILD_DIR="${SCRATCH_DIR}/build"
    ;;
esac

mkdir -p "${CANONICAL_BUILD_DIR}"
find "${CANONICAL_BUILD_DIR}" -mindepth 1 \
  ! -name '.gitkeep' \
  ! -name '.gitignore' \
  -exec rm -rf {} +

(
  cd "${WORKSPACE_DIR}"
  "${WEST_BIN}" build -p always -b "${BOARD}" "${WORK_APP_DIR}" -d "${WORK_BUILD_DIR}"
)

cp "${WORK_BUILD_DIR}/zephyr/zephyr.elf" "${CANONICAL_BUILD_DIR}/firmware.elf"
if [[ -f "${WORK_BUILD_DIR}/zephyr/zephyr.hex" ]]; then
  cp "${WORK_BUILD_DIR}/zephyr/zephyr.hex" "${CANONICAL_BUILD_DIR}/firmware.hex"
fi

echo "Built ${CANONICAL_BUILD_DIR}/firmware.elf"
if [[ -f "${CANONICAL_BUILD_DIR}/firmware.hex" ]]; then
  echo "Built ${CANONICAL_BUILD_DIR}/firmware.hex"
fi
