#!/usr/bin/env bash
set -euo pipefail

# paths in repo
INFO_PLIST="mac_config/serve_mac_container.info.plist"
SHIM_SRC="mac_config/serve_mac_container.c"
SHIM_OUT="mac_config/serve_mac_container"
PYI_DIR="pyinstaller_builds/serve_mac"
PYI_EXE="${PYI_DIR}/serve_mac"
MIN_MACOS="12.0"

# sanity
if [[ ! -f "${INFO_PLIST}" ]]; then
  echo "Missing ${INFO_PLIST}" >&2; exit 1
fi
if [[ ! -x "${PYI_EXE}" ]]; then
  echo "Missing or non-executable ${PYI_EXE}" >&2; exit 1
fi

if [[ ! -f "${SHIM_SRC}" ]]; then
  echo "Missing or non-executable ${SHIM_SRC}" >&2; exit 1
fi

# compile the shim and EMBED Info.plist into the Mach-O
clang -Os -mmacosx-version-min="${MIN_MACOS}" \
  -Wl,-sectcreate,__TEXT,__info_plist,"${INFO_PLIST}" \
  -o "${SHIM_OUT}" "${SHIM_SRC}"

# drop the shim next to PyInstaller exe so electron-builder picks it up
install -m 0755 "${SHIM_OUT}" "${PYI_DIR}/serve_mac_container"

echo "Built shim -> ${PYI_DIR}/serve_mac_container"
echo "Next: make Electron spawn 'serve_mac_container' (not 'serve_mac')."
echo "Also add this to electron-builder.yml 'binaries':"
echo "  - Contents/backend/serve_mac/serve_mac_container"

# quick local checks
echo
echo "Verifying embedded Info.plist and load commands..."
otool -P "${PYI_DIR}/serve_mac_container" | head || true
otool -l "${PYI_DIR}/serve_mac_container" | grep -A3 -E 'LC_VERSION_MIN|LC_BUILD_VERSION' || true
