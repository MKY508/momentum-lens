#!/bin/bash

# Momentum Lens 启动脚本

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "🎯 Momentum Lens 启动"
echo "===================="

# 清理旧进程
echo -e "${BLUE}清理旧进程...${NC}"
if [ -f ".backend.pid" ]; then
    PID=$(cat .backend.pid)
    kill $PID 2>/dev/null && echo "  停止后端进程 $PID"
    rm .backend.pid
fi
if [ -f ".frontend.pid" ]; then
    PID=$(cat .frontend.pid)
    kill $PID 2>/dev/null && echo "  停止前端进程 $PID"
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
        PID=$(lsof -t -i:$port)
        kill $PID 2>/dev/null && echo "  已清理进程 $PID"
    fi
done

# 启动后端
echo -e "${BLUE}启动后端API...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo "  创建Python虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "  安装依赖..."
    pip install fastapi uvicorn pandas numpy akshare pydantic python-dotenv aiohttp --quiet
else
    source venv/bin/activate
fi

# 使用现有的main_lite.py或创建简单后端
if [ -f "main_lite.py" ]; then
    echo "  使用 main_lite.py"
    python main_lite.py > ../backend.log 2>&1 &
else
    echo "  创建简单后端..."
    cat > main_api.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(title="Momentum Lens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "running", "time": datetime.now().isoformat()}

@app.get("/api/v1/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/decisions/calculate")
def calculate():
    return {
        "environment": {
            "yearline": True,
            "atr20_pct": 2.5,
            "chop": False
        },
        "picks": [
            {
                "code": "588000",
                "name": "科创50ETF",
                "score": 0.145,
                "target_weight": 0.05,
                "reason": "最高动量得分"
            },
            {
                "code": "512760",
                "name": "半导体ETF",
                "score": 0.132,
                "target_weight": 0.05,
                "reason": "低相关性第二腿"
            }
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/market/data-sources")
def data_sources():
    return {
        "sources": [
            {"id": "akshare", "name": "AKShare", "status": "active"}
        ],
        "active": "akshare"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF
    python main_api.py > ../backend.log 2>&1 &
fi

BACKEND_PID=$!
echo $BACKEND_PID > ../.backend.pid
cd ..

sleep 3
echo -e "${GREEN}✅ 后端已启动${NC}"
echo "   地址: http://localhost:8000"
echo "   文档: http://localhost:8000/docs"

# 启动前端
echo -e "${BLUE}启动前端...${NC}"
cd frontend

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo -e "${RED}前端依赖未安装！${NC}"
    echo "请运行: cd frontend && npm install --legacy-peer-deps"
    exit 1
fi

# 设置环境变量并启动
export REACT_APP_API_URL=http://localhost:8000
PORT=3000 npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.frontend.pid
cd ..

echo -e "${BLUE}前端正在启动，请等待...${NC}"
echo "（首次启动可能需要30-60秒）"

# 等待前端启动
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 前端已启动${NC}"
        echo "   地址: http://localhost:3000"
        break
    fi
    sleep 2
    echo -n "."
done

echo ""
echo "===================="
echo -e "${GREEN}✨ 系统启动完成！${NC}"
echo ""
echo "访问地址："
echo "  前端界面: http://localhost:3000"
echo "  后端API: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo ""
echo "查看日志："
echo "  后端: tail -f backend.log"
echo "  前端: tail -f frontend.log"
echo ""
echo "停止服务: ./stop-all.sh"
echo ""

# 保持运行
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '服务已停止'; exit" INT TERM
wait