#!/bin/bash

# ETF动量系统启动脚本

echo "========================================="
echo "   ETF动量决策系统 - 启动程序"
echo "========================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    echo "访问: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 选择启动模式
echo ""
echo "请选择启动模式:"
echo "1) Docker容器模式 (推荐)"
echo "2) 本地开发模式"
echo -n "请输入选择 [1-2]: "
read mode

if [ "$mode" = "1" ]; then
    echo ""
    echo "🚀 启动Docker容器..."
    
    # 构建镜像
    echo "📦 构建Docker镜像..."
    docker-compose build
    
    # 启动服务
    echo "🔧 启动服务..."
    docker-compose up -d
    
    # 等待服务启动
    echo "⏳ 等待服务启动..."
    sleep 10
    
    # 检查服务状态
    echo ""
    echo "✅ 服务已启动!"
    echo ""
    echo "访问地址:"
    echo "  📊 前端界面: http://localhost:3000"
    echo "  🔌 API文档: http://localhost:8000/docs"
    echo "  📈 Grafana监控: http://localhost:3001 (admin/admin)"
    echo ""
    echo "查看日志: docker-compose logs -f"
    echo "停止服务: docker-compose down"
    
elif [ "$mode" = "2" ]; then
    echo ""
    echo "🖥️  启动本地开发模式..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3未安装"
        exit 1
    fi
    
    # 检查Node
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js未安装"
        exit 1
    fi
    
    # 启动后端
    echo "🐍 启动Python后端..."
    cd backend
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        echo "创建Python虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install -r requirements.txt
    
    # 启动后端服务
    uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    echo "后端PID: $BACKEND_PID"
    
    cd ..
    
    # 启动前端
    echo "⚛️  启动React前端..."
    cd frontend
    
    # 安装依赖
    if [ ! -d "node_modules" ]; then
        echo "安装前端依赖..."
        npm install
    fi
    
    # 启动前端服务
    npm run dev &
    FRONTEND_PID=$!
    echo "前端PID: $FRONTEND_PID"
    
    cd ..
    
    # 等待服务启动
    sleep 5
    
    echo ""
    echo "✅ 本地开发服务已启动!"
    echo ""
    echo "访问地址:"
    echo "  📊 前端界面: http://127.0.0.1:3000"
    echo "  🔌 API文档: http://127.0.0.1:8000/docs"
    echo ""
    echo "停止服务: 按 Ctrl+C"
    
    # 等待退出信号
    cleanup() {
        echo "正在清理进程..."
        if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID 2>/dev/null
        fi
        if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID 2>/dev/null
        fi
    }
    trap cleanup EXIT
    wait
    
else
    echo "❌ 无效的选择"
    exit 1
fi