#!/usr/bin/env bash
set -euo pipefail

SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  TARGET="$(readlink "$SOURCE")"
  if [[ "$TARGET" == /* ]]; then
    SOURCE="$TARGET"
  else
    SOURCE="$(cd "$(dirname "$SOURCE")" && pwd)/$TARGET"
  fi
done
PROJECT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
PYTHON_BIN="$HOME/rqalpha_env/bin/python"

usage() {
  cat <<'EOF'
用法: ./momentum.sh [command] [options]

命令:
  interactive          进入交互式菜单（默认行为）
  analyze [args...]    直接传递参数给 momentum_cli 分析
  presets              列出预设券池后退出
  analysis-presets     列出分析预设后退出
  bundle-update        调用 rqalpha update-bundle 更新数据
  help                 显示本帮助

示例:
  ./momentum.sh analyze --preset core --run-backtest
  ./momentum.sh analyze --preset core --export-strategy strategies/momentum_strategy.py
  ./momentum.sh presets
EOF
}

if [[ ! -x "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "未找到可用的 python3 解释器，请检查环境。" >&2
    exit 1
  fi
fi

cd "$PROJECT_DIR"

if [[ $# -eq 0 ]]; then
  set -- interactive
fi

case "$1" in
  -h|--help|help)
    usage
    exit 0
    ;;
  interactive)
    shift
    exec "$PYTHON_BIN" -m momentum_cli --interactive "$@"
    ;;
  analyze)
    shift
    exec "$PYTHON_BIN" -m momentum_cli "$@"
    ;;
  presets)
    shift
    exec "$PYTHON_BIN" -m momentum_cli --list-presets "$@"
    ;;
  analysis-presets)
    shift
    exec "$PYTHON_BIN" -m momentum_cli --list-analysis-presets "$@"
    ;;
  bundle-update|update-bundle)
    shift
    exec "$PYTHON_BIN" -m momentum_cli --update-bundle "$@"
    ;;
  *)
    exec "$PYTHON_BIN" -m momentum_cli "$@"
    ;;
esac
