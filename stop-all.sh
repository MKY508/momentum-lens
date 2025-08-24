#!/bin/bash

# Momentum Lens - 统一停止脚本
# 停止所有运行的服务和清理资源

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       🛑 Momentum Lens 停止服务          ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════╝${NC}"
echo ""

# 停止后端
echo -e "${BLUE}🔍 查找后端进程...${NC}"
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${YELLOW}   停止后端进程 (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}   ✅ 后端已停止${NC}"
    else
        echo -e "${YELLOW}   后端进程不存在${NC}"
    fi
    rm -f .backend.pid
else
    # 尝试通过端口查找
    for port in 8000 8001 8002 8003; do
        PID=$(lsof -t -i:$port 2>/dev/null || true)
        if [ ! -z "$PID" ]; then
            echo -e "${YELLOW}   发现后端进程在端口 $port (PID: $PID)${NC}"
            kill $PID 2>/dev/null || true
            echo -e "${GREEN}   ✅ 已停止${NC}"
        fi
    done
fi

# 停止前端
echo -e "${BLUE}🔍 查找前端进程...${NC}"
if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${YELLOW}   停止前端进程 (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}   ✅ 前端已停止${NC}"
    else
        echo -e "${YELLOW}   前端进程不存在${NC}"
    fi
    rm -f .frontend.pid
else
    # 尝试通过端口查找
    for port in 3000 3001 3002 3003; do
        PID=$(lsof -t -i:$port 2>/dev/null || true)
        if [ ! -z "$PID" ]; then
            echo -e "${YELLOW}   发现前端进程在端口 $port (PID: $PID)${NC}"
            echo -e "${YELLOW}   注意: 这可能是其他应用${NC}"
            read -p "   是否停止？(y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kill $PID 2>/dev/null || true
                echo -e "${GREEN}   ✅ 已停止${NC}"
            fi
        fi
    done
fi

# 停止Python相关进程
echo -e "${BLUE}🔍 查找Python进程...${NC}"
PYTHON_PIDS=$(ps aux | grep -E "python.*main.*py|uvicorn" | grep -v grep | awk '{print $2}' || true)
if [ ! -z "$PYTHON_PIDS" ]; then
    for PID in $PYTHON_PIDS; do
        echo -e "${YELLOW}   停止Python进程 (PID: $PID)...${NC}"
        kill $PID 2>/dev/null || true
    done
    echo -e "${GREEN}   ✅ Python进程已清理${NC}"
else
    echo -e "${GREEN}   无Python进程运行${NC}"
fi

# 停止Node进程
echo -e "${BLUE}🔍 查找Node进程...${NC}"
NODE_PIDS=$(ps aux | grep -E "node.*momentum|npm.*start|npm.*dev" | grep -v grep | awk '{print $2}' || true)
if [ ! -z "$NODE_PIDS" ]; then
    for PID in $NODE_PIDS; do
        echo -e "${YELLOW}   停止Node进程 (PID: $PID)...${NC}"
        kill $PID 2>/dev/null || true
    done
    echo -e "${GREEN}   ✅ Node进程已清理${NC}"
else
    echo -e "${GREEN}   无Node进程运行${NC}"
fi

# 停止Docker容器（如果有）
if command -v docker &> /dev/null; then
    echo -e "${BLUE}🔍 检查Docker容器...${NC}"
    CONTAINERS=$(docker ps -q --filter "name=momentum" 2>/dev/null || true)
    if [ ! -z "$CONTAINERS" ]; then
        echo -e "${YELLOW}   停止Docker容器...${NC}"
        docker-compose down 2>/dev/null || docker stop $CONTAINERS 2>/dev/null || true
        echo -e "${GREEN}   ✅ Docker容器已停止${NC}"
    else
        echo -e "${GREEN}   无Docker容器运行${NC}"
    fi
fi

# 清理临时文件
echo -e "${BLUE}🧹 清理临时文件...${NC}"
rm -f .backend.pid .frontend.pid
rm -f backend.log frontend.log
rm -f .env.current
echo -e "${GREEN}✅ 临时文件已清理${NC}"

echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}✨ 所有服务已停止并清理完成！${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}下次启动请运行: ./start-unified.sh${NC}"
echo ""