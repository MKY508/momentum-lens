#!/usr/bin/env bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SCRIPT_SOURCE" ]]; do
  TARGET="$(readlink "$SCRIPT_SOURCE")"
  if [[ "$TARGET" == /* ]]; then
    SCRIPT_SOURCE="$TARGET"
  else
    SCRIPT_SOURCE="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)/$TARGET"
  fi
done
readonly PROJECT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
readonly SCRIPT_NAME="$(basename "$SCRIPT_SOURCE")"
readonly CLI_ENTRY="momentum_cli"
readonly DEFAULT_VENV_PYTHON="$HOME/rqalpha_env/bin/python"

usage() {
  cat <<EOF
用法: ./$SCRIPT_NAME [command] [options]

命令:
  interactive            启动 momentum_cli 交互式菜单（默认行为）
  analyze [args...]      将参数原样转发给 momentum_cli 进行分析
  presets                列出可用的券池预设后退出
  analysis-presets       列出分析参数预设后退出
  bundle-update          通过 rqalpha update-bundle 更新数据
  update-bundle          同 bundle-update，向后兼容
  help                   显示本帮助

环境变量:
  MOMENTUM_PYTHON             指定用于运行 CLI 的 Python 解释器
  MOMENTUM_SKIP_IMPORT_CHECK  设为 1 可跳过对 momentum_cli 模块导入检测

示例:
  ./$SCRIPT_NAME analyze --preset core --run-backtest
  ./$SCRIPT_NAME analyze --preset core --export-strategy strategies/momentum_strategy.py
  ./$SCRIPT_NAME presets
EOF
}

die() {
  local message="$1"
  shift || true
  printf 'Error: %s\n' "$message" >&2
  for line in "$@"; do
    printf '%s\n' "$line" >&2
  done
  exit 1
}

resolve_python() {
  local candidate=""

  if [[ -n "${MOMENTUM_PYTHON:-}" ]]; then
    candidate="${MOMENTUM_PYTHON}"
  elif [[ -x "$DEFAULT_VENV_PYTHON" ]]; then
    candidate="$DEFAULT_VENV_PYTHON"
  else
    local bin
    for bin in python3 python; do
      if command -v "$bin" >/dev/null 2>&1; then
        candidate="$(command -v "$bin")"
        break
      fi
    done
  fi

  if [[ -z "$candidate" ]]; then
    die "未找到可用的 Python 解释器。" \
      "请安装 python3 或设置环境变量 MOMENTUM_PYTHON 指向可执行的解释器。"
  fi

  if [[ ! -x "$candidate" ]]; then
    die "指定的 Python 解释器不可执行: $candidate"
  fi

  printf '%s\n' "$candidate"
}

ensure_python_version() {
  if "$PYTHON_BIN" -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
    return 0
  fi

  die "Python 版本过低 (需要 >= 3.8)。" "当前解释器: $PYTHON_BIN"
}

verify_cli() {
  if [[ "${MOMENTUM_SKIP_IMPORT_CHECK:-0}" == "1" ]]; then
    return 0
  fi

  if ! "$PYTHON_BIN" -c "import momentum_cli" >/dev/null 2>&1; then
    die "无法导入 momentum_cli 模块。" \
      "请确认依赖已安装 (例如: pip install momentum-cli)，或激活正确的虚拟环境。" \
      "如需跳过检查，请在运行脚本前设置 MOMENTUM_SKIP_IMPORT_CHECK=1。"
  fi
}

run_cli() {
  exec "$PYTHON_BIN" -m "$CLI_ENTRY" "$@"
}

ensure_runtime_ready() {
  ensure_python_version
  verify_cli
}

dispatch_command() {
  local command="$1"
  shift || true

  case "$command" in
    interactive)
      run_cli --interactive "$@"
      ;;
    analyze)
      run_cli "$@"
      ;;
    presets|list-presets)
      run_cli --list-presets "$@"
      ;;
    analysis-presets|list-analysis-presets)
      run_cli --list-analysis-presets "$@"
      ;;
    bundle-update|update-bundle)
      run_cli --update-bundle "$@"
      ;;
    *)
      run_cli "$command" "$@"
      ;;
  esac
}

main() {
  cd "$PROJECT_DIR"

  if [[ $# -eq 0 ]]; then
    set -- interactive
  fi

  local command="$1"

  case "$command" in
    -h|--help|help)
      usage
      return 0
      ;;
  esac

  shift
  ensure_runtime_ready
  dispatch_command "$command" "$@"
}

PYTHON_BIN="$(resolve_python)"
readonly PYTHON_BIN

main "$@"
