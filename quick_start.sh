#!/bin/bash

echo "🚀 ETF动量策略系统 - 快速启动"
echo ""

# 检查Python版本
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD=python3.11
    echo "✅ 使用 Python 3.11"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD=python3.12
    echo "✅ 使用 Python 3.12"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD=python3.10
    echo "✅ 使用 Python 3.10"
else
    PYTHON_CMD=python3
    echo "⚠️ 使用默认 Python 3"
fi

# 激活虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    $PYTHON_CMD -m venv venv
fi

source venv/bin/activate

# 检查依赖
if ! python -c "import streamlit" 2>/dev/null; then
    echo "安装依赖..."
    pip install -r requirements.txt
fi

# 设置环境变量
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 启动
echo ""
echo "启动系统..."
streamlit run app.py --server.port 8501 --server.address 127.0.0.1

echo ""
echo "✅ 访问: http://127.0.0.1:8501"