#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VENV_PATH="${PROJECT_ROOT}/.venv"
PYTHON_BIN="${PYTHON:-python3}"

if [ ! -d "${VENV_PATH}" ]; then
  echo "[+] Creating virtual environment at ${VENV_PATH}"
  "${PYTHON_BIN}" -m venv "${VENV_PATH}"
else
  echo "[i] Virtual environment already exists at ${VENV_PATH}"
fi

# shellcheck disable=SC1090
source "${VENV_PATH}/bin/activate"

pip install --upgrade pip
pip install -r "${PROJECT_ROOT}/requirements.txt"

echo "[+] Environment ready. Activate with: source ${VENV_PATH}/bin/activate"
