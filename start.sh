#!/bin/bash

echo "========================================="
echo "   ETF动量策略系统 - 快速启动"
echo "========================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3未安装"
    echo "请访问: https://www.python.org/downloads/"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📚 安装依赖包..."
pip install -r requirements.txt

# 启动Streamlit
echo ""
echo "🚀 启动系统..."
echo ""
streamlit run app.py --server.port 8501 --server.address 127.0.0.1

echo ""
echo "✅ 系统已启动!"
echo ""
echo "📊 访问地址: http://127.0.0.1:8501"
echo ""
echo "按 Ctrl+C 停止服务"