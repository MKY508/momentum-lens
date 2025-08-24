#!/bin/bash

# Momentum Lens 完整版启动脚本

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     🎯 Momentum Lens 完整版启动           ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════╝${NC}"
echo ""

# 清理旧进程
echo -e "${BLUE}🔍 清理旧进程...${NC}"
if [ -f ".backend.pid" ]; then
    PID=$(cat .backend.pid 2>/dev/null)
    if [ ! -z "$PID" ]; then
        kill $PID 2>/dev/null && echo -e "   ${YELLOW}停止后端进程 $PID${NC}"
    fi
    rm .backend.pid
fi
if [ -f ".frontend.pid" ]; then
    PID=$(cat .frontend.pid 2>/dev/null)
    if [ ! -z "$PID" ]; then
        kill $PID 2>/dev/null && echo -e "   ${YELLOW}停止前端进程 $PID${NC}"
    fi
    rm .frontend.pid
fi

# 检查端口占用
check_port() {
    lsof -i:$1 > /dev/null 2>&1
    return $?
}

# 清理占用的端口
for port in 8000 3000; do
    if check_port $port; then
        echo -e "${YELLOW}端口 $port 被占用，尝试清理...${NC}"
        PID=$(lsof -t -i:$port 2>/dev/null)
        if [ ! -z "$PID" ]; then
            kill $PID 2>/dev/null && echo -e "   ${GREEN}已清理进程 $PID${NC}"
        fi
        sleep 1
    fi
done

# 启动后端
echo ""
echo -e "${BLUE}🚀 启动后端服务...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo -e "   ${YELLOW}创建Python虚拟环境...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "   ${YELLOW}安装依赖...${NC}"
    pip install fastapi uvicorn pandas numpy aiohttp pydantic python-dotenv --quiet
else
    source venv/bin/activate
fi

echo -e "   ${GREEN}启动FastAPI服务...${NC}"
python main_lite.py > ../backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../.backend.pid
cd ..

# 等待后端启动
echo -e "   ${YELLOW}等待后端就绪...${NC}"
for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ 后端已启动${NC}"
        break
    fi
    sleep 1
done

# 启动前端
echo ""
echo -e "${BLUE}🚀 启动前端服务...${NC}"
cd frontend

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo -e "${RED}❌ 前端依赖未安装！${NC}"
    echo -e "${YELLOW}正在安装依赖...${NC}"
    npm install --legacy-peer-deps
fi

# 设置环境变量并启动
export REACT_APP_API_URL=http://127.0.0.1:8000
echo -e "   ${GREEN}启动React应用...${NC}"
PORT=3000 npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.frontend.pid
cd ..

# 等待前端启动
echo -e "   ${YELLOW}等待前端就绪（首次可能需要30-60秒）...${NC}"
for i in {1..60}; do
    if curl -s http://127.0.0.1:3000 > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ 前端已启动${NC}"
        break
    fi
    sleep 2
    echo -n "."
done
echo ""

# 显示状态
echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}✨ Momentum Lens 完整版启动成功！${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}访问地址：${NC}"
echo -e "  📊 前端界面: ${GREEN}http://127.0.0.1:3000${NC}"
echo -e "  🔧 后端API: ${GREEN}http://127.0.0.1:8000${NC}"
echo -e "  📚 API文档: ${GREEN}http://127.0.0.1:8000/docs${NC}"
echo ""
echo -e "${CYAN}功能模块：${NC}"
echo -e "  • 决策台 Dashboard - 市场环境指标、ETF选择、交易建议"
echo -e "  • Core模块 - 核心持仓管理、沪深300图表、再平衡仪表"
echo -e "  • Satellite模块 - 动量排行、相关性热图、轮动控制"
echo -e "  • 日志/KPI - 交易记录、绩效指标、风险监控"
echo ""
echo -e "${YELLOW}提示：${NC}"
echo -e "  • 查看后端日志: tail -f backend.log"
echo -e "  • 查看前端日志: tail -f frontend.log"
echo -e "  • 停止服务: ./stop-all.sh"
echo ""

# 保持运行
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '服务已停止'; exit" INT TERM
wait