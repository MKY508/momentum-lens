#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CLI_SCRIPT="${PROJECT_ROOT}/momentum_lens.sh"
TARGET_DIR="${HOME}/.local/bin"
TARGET_LINK="${TARGET_DIR}/momentum-lens"

mkdir -p "${TARGET_DIR}"

if [ -L "${TARGET_LINK}" ] || [ -f "${TARGET_LINK}" ]; then
  echo "[i] Removing existing ${TARGET_LINK}"
  rm -f "${TARGET_LINK}"
fi

ln -s "${CLI_SCRIPT}" "${TARGET_LINK}"
chmod +x "${CLI_SCRIPT}"

echo "[+] Linked momentum-lens CLI to ${TARGET_LINK}"
echo "[i] Ensure ${TARGET_DIR} is in your PATH (e.g. export PATH=\"${TARGET_DIR}:$PATH\")."
