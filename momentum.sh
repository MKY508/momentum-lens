#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW_LAUNCHER="${SCRIPT_DIR}/momentum_lens.sh"

echo "[warning] momentum.sh 已更名为 momentum_lens.sh，请尽快更新命令。" >&2
exec "${NEW_LAUNCHER}" "$@"
