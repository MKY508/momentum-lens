#!/bin/bash

# Momentum Lens - 快速启动脚本
# 用于快速启动开发环境

set -e

echo "🚀 Momentum Lens - 快速启动"
echo "================================"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查Python
echo -e "${BLUE}📦 检查Python环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3已安装${NC}"

# 检查Node.js
echo -e "${BLUE}📦 检查Node.js环境...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js已安装${NC}"

# 设置环境变量
echo -e "${BLUE}🔧 配置环境变量...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  已创建.env文件，请根据需要修改配置${NC}"
fi

# 创建Python虚拟环境
echo -e "${BLUE}🐍 设置Python环境...${NC}"
if [ ! -d "backend/venv" ]; then
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ..
    echo -e "${GREEN}✅ Python依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ Python虚拟环境已存在${NC}"
fi

# 安装前端依赖
echo -e "${BLUE}⚛️  设置React前端...${NC}"
if [ ! -d "frontend/node_modules" ]; then
    cd frontend
    npm install --legacy-peer-deps
    cd ..
    echo -e "${GREEN}✅ 前端依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ 前端依赖已安装${NC}"
fi

# 启动后端
echo -e "${BLUE}🚀 启动后端服务...${NC}"
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✅ 后端运行在: http://localhost:8000${NC}"
echo -e "${GREEN}📚 API文档: http://localhost:8000/docs${NC}"

# 等待后端启动
sleep 3

# 启动前端
echo -e "${BLUE}🚀 启动前端服务...${NC}"
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "================================"
echo -e "${GREEN}✨ Momentum Lens 已启动！${NC}"
echo ""
echo "🌐 访问地址:"
echo "   前端界面: http://localhost:3000"
echo "   后端API: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "📊 默认配置:"
echo "   策略模式: 均衡"
echo "   动量公式: Score = 0.6×r60 + 0.4×r120"
echo "   止损线: -12%"
echo "   缓冲区: 3%"
echo ""
echo "🛑 停止服务: 运行 ./stop.sh 或按 Ctrl+C"
echo "================================"

# 保存PID
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

# 等待用户中断
trap "echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .backend.pid .frontend.pid; exit" INT TERM

# 保持脚本运行
wait