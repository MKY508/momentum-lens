#!/bin/bash

# Momentum Lens 快速启动脚本 - 优化版
# 跳过依赖检查，直接启动服务

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "🚀 Momentum Lens 快速启动"
echo "========================"

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}清理进程...${NC}"
    # 读取PID文件并终止进程
    if [ -f ".backend.pid" ]; then
        kill $(cat .backend.pid) 2>/dev/null
        rm .backend.pid
    fi
    if [ -f ".frontend.pid" ]; then
        kill $(cat .frontend.pid) 2>/dev/null
        rm .frontend.pid
    fi
    # 强制清理端口
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    lsof -ti:3000 | xargs kill -9 2>/dev/null
    echo -e "${GREEN}清理完成${NC}"
}

# 捕获退出信号
trap cleanup EXIT INT TERM

# 清理旧进程
echo -e "${BLUE}清理旧进程...${NC}"
cleanup 2>/dev/null

# 等待端口释放
sleep 1

# 启动后端 (轻量级模式)
echo -e "${BLUE}启动后端服务...${NC}"
cd backend

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${YELLOW}未找到虚拟环境，使用系统Python${NC}"
fi

# 使用轻量级后端
if [ -f "main_lite.py" ]; then
    echo "  使用轻量级后端 (main_lite.py)"
    python main_lite.py > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../.backend.pid
elif [ -f "app.py" ]; then
    echo "  使用标准后端 (app.py)"
    python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../.backend.pid
else
    echo -e "${RED}未找到后端文件！${NC}"
    echo "  创建最简后端..."
    cat > temp_api.py << 'EOF'
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
    return {"status": "running", "message": "Momentum Lens API", "time": datetime.now().isoformat()}

@app.get("/api/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF
    python temp_api.py > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../.backend.pid
fi

cd ..

# 等待后端启动
echo -n "  等待后端启动"
for i in {1..10}; do
    if curl -s http://localhost:8000 > /dev/null; then
        echo -e "\n${GREEN}✅ 后端已启动${NC}"
        echo "   地址: http://localhost:8000"
        echo "   API文档: http://localhost:8000/docs"
        break
    fi
    echo -n "."
    sleep 1
done

# 检查后端是否成功启动
if ! curl -s http://localhost:8000 > /dev/null; then
    echo -e "\n${RED}❌ 后端启动失败！${NC}"
    echo "查看日志: tail -f backend.log"
    exit 1
fi

# 启动前端（如果存在）
if [ -d "frontend" ]; then
    echo -e "\n${BLUE}启动前端服务...${NC}"
    cd frontend
    
    # 检查node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}⚠️  前端依赖未安装${NC}"
        echo "跳过前端启动。如需前端，请运行："
        echo "  cd frontend && npm install --legacy-peer-deps"
    else
        # 修复：使用正确的启动命令
        if [ -f "package.json" ]; then
            # 检查可用的脚本
            if npm run | grep -q "start"; then
                echo "  使用 npm start 启动前端..."
                PORT=3000 npm start > ../frontend.log 2>&1 &
                FRONTEND_PID=$!
                echo $FRONTEND_PID > ../.frontend.pid
            elif npm run | grep -q "dev"; then
                echo "  使用 npm run dev 启动前端..."
                npm run dev > ../frontend.log 2>&1 &
                FRONTEND_PID=$!
                echo $FRONTEND_PID > ../.frontend.pid
            else
                echo -e "${RED}未找到合适的启动脚本${NC}"
            fi
            
            # 等待前端启动
            if [ ! -z "$FRONTEND_PID" ]; then
                echo -n "  等待前端启动"
                for i in {1..15}; do
                    if curl -s http://localhost:3000 > /dev/null 2>&1; then
                        echo -e "\n${GREEN}✅ 前端已启动${NC}"
                        echo "   地址: http://localhost:3000"
                        break
                    fi
                    echo -n "."
                    sleep 1
                done
            fi
        fi
    fi
    cd ..
else
    echo -e "${YELLOW}未找到前端目录，跳过前端启动${NC}"
fi

echo ""
echo "========================================="
echo -e "${GREEN}🎉 Momentum Lens 启动完成！${NC}"
echo "========================================="
echo ""
echo "访问地址："
echo "  后端API: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
if [ ! -z "$FRONTEND_PID" ]; then
    echo "  前端界面: http://localhost:3000"
fi
echo ""
echo "查看日志："
echo "  后端: tail -f backend.log"
if [ ! -z "$FRONTEND_PID" ]; then
    echo "  前端: tail -f frontend.log"
fi
echo ""
echo "停止服务: 按 Ctrl+C 或运行 ./stop-all.sh"
echo ""

# 保持脚本运行
if [ ! -z "$FRONTEND_PID" ]; then
    echo "服务运行中... (按 Ctrl+C 停止)"
    wait $FRONTEND_PID
else
    echo "后端服务运行中... (按 Ctrl+C 停止)"
    wait $BACKEND_PID
fi