#!/bin/bash

# Momentum Lens Setup Script
# 系统环境初始化脚本

echo "🚀 Starting Momentum Lens Setup..."

# 创建必要的目录
echo "📁 Creating directories..."
mkdir -p data exports logs

# 检查Python版本
echo "🐍 Checking Python version..."
python3 --version

# 创建虚拟环境
echo "🔧 Creating virtual environment..."
python3 -m venv venv

# 激活虚拟环境
echo "📦 Activating virtual environment..."
source venv/bin/activate

# 升级pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# 安装依赖
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# 验证安装
echo "✅ Verifying installation..."
python3 -c "
import streamlit
import pandas
import numpy
import plotly
print('✅ Core packages installed successfully')
"

# 创建示例配置文件
if [ ! -f "backend/config/positions.yaml" ]; then
    echo "📝 Creating sample positions file..."
    cat > backend/config/positions.yaml << EOF
# 持仓记录
positions:
  - code: "510300"
    name: "沪深300ETF"
    weight: 0.3
    entry_price: 3.85
    entry_date: "2024-01-15"
  
  - code: "512760"
    name: "国防军工ETF"
    weight: 0.2
    entry_price: 0.95
    entry_date: "2024-01-20"

cash_ratio: 0.1
total_assets: 1000000
EOF
fi

echo ""
echo "✨ Setup completed successfully!"
echo ""
echo "To start the application, run:"
echo "  source venv/bin/activate"
echo "  streamlit run backend/app.py"
echo ""
echo "Or simply use:"
echo "  make app"