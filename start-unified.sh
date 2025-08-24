#!/bin/bash

# Momentum Lens - 统一智能启动脚本
# 自动检测端口占用，智能切换，统一管理所有启动方式

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# 默认端口
DEFAULT_BACKEND_PORT=8000
DEFAULT_FRONTEND_PORT=3000
BACKEND_PORT=$DEFAULT_BACKEND_PORT
FRONTEND_PORT=$DEFAULT_FRONTEND_PORT

# PID文件
BACKEND_PID_FILE=".backend.pid"
FRONTEND_PID_FILE=".frontend.pid"

# 打印带颜色的消息
print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

# 打印Logo
print_logo() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║       🎯 Momentum Lens 统一启动器        ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════╝${NC}"
    echo ""
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -i:$port > /dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口可用
    fi
}

# 查找可用端口
find_available_port() {
    local base_port=$1
    local port=$base_port
    local max_attempts=10
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if ! check_port $port; then
            echo $port
            return 0
        fi
        port=$((port + 1))
        attempt=$((attempt + 1))
    done
    
    echo 0
    return 1
}

# 清理旧进程
cleanup_old_processes() {
    print_msg "$BLUE" "🧹 检查并清理旧进程..."
    
    # 清理后端进程
    if [ -f "$BACKEND_PID_FILE" ]; then
        OLD_BACKEND_PID=$(cat $BACKEND_PID_FILE)
        if kill -0 $OLD_BACKEND_PID 2>/dev/null; then
            print_msg "$YELLOW" "   发现旧的后端进程 (PID: $OLD_BACKEND_PID)，正在停止..."
            kill $OLD_BACKEND_PID 2>/dev/null || true
            sleep 2
        fi
        rm -f $BACKEND_PID_FILE
    fi
    
    # 清理前端进程
    if [ -f "$FRONTEND_PID_FILE" ]; then
        OLD_FRONTEND_PID=$(cat $FRONTEND_PID_FILE)
        if kill -0 $OLD_FRONTEND_PID 2>/dev/null; then
            print_msg "$YELLOW" "   发现旧的前端进程 (PID: $OLD_FRONTEND_PID)，正在停止..."
            kill $OLD_FRONTEND_PID 2>/dev/null || true
            sleep 2
        fi
        rm -f $FRONTEND_PID_FILE
    fi
    
    # 清理占用端口的其他进程（可选）
    for port in $DEFAULT_BACKEND_PORT $DEFAULT_FRONTEND_PORT; do
        if check_port $port; then
            PID=$(lsof -t -i:$port 2>/dev/null || true)
            if [ ! -z "$PID" ]; then
                print_msg "$YELLOW" "   端口 $port 被进程 $PID 占用"
                read -p "   是否终止该进程？(y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    kill $PID 2>/dev/null || true
                    sleep 1
                fi
            fi
        fi
    done
    
    print_msg "$GREEN" "✅ 清理完成"
}

# 检查依赖
check_dependencies() {
    print_msg "$BLUE" "📦 检查系统依赖..."
    
    local missing_deps=0
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_msg "$RED" "❌ Python3 未安装"
        missing_deps=1
    else
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d" " -f2)
        print_msg "$GREEN" "✅ Python $PYTHON_VERSION"
    fi
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        print_msg "$YELLOW" "⚠️  Node.js 未安装 (前端将不可用)"
        SKIP_FRONTEND=true
    else
        NODE_VERSION=$(node --version)
        print_msg "$GREEN" "✅ Node.js $NODE_VERSION"
        SKIP_FRONTEND=false
    fi
    
    # 检查npm
    if ! command -v npm &> /dev/null; then
        print_msg "$YELLOW" "⚠️  npm 未安装 (前端将不可用)"
        SKIP_FRONTEND=true
    else
        NPM_VERSION=$(npm --version)
        print_msg "$GREEN" "✅ npm $NPM_VERSION"
    fi
    
    if [ $missing_deps -eq 1 ]; then
        print_msg "$RED" "❌ 缺少必要依赖，请先安装"
        exit 1
    fi
}

# 选择启动模式
select_mode() {
    print_msg "$CYAN" "🎯 选择启动模式："
    echo ""
    echo "  1) 轻量级模式 (SQLite + AKShare，推荐)"
    echo "  2) 标准模式 (需要PostgreSQL + Redis)"
    echo "  3) Docker模式 (完整环境)"
    echo "  4) 仅后端API"
    echo "  5) 仅前端界面"
    echo "  6) Vite前端 + 轻量后端 (最新)"
    echo ""
    read -p "请选择 (1-6) [默认: 1]: " MODE
    MODE=${MODE:-1}
    
    case $MODE in
        1) START_MODE="lite" ;;
        2) START_MODE="standard" ;;
        3) START_MODE="docker" ;;
        4) START_MODE="backend-only" ;;
        5) START_MODE="frontend-only" ;;
        6) START_MODE="vite" ;;
        *) START_MODE="lite" ;;
    esac
    
    print_msg "$GREEN" "✅ 选择: $START_MODE 模式"
}

# 配置端口
configure_ports() {
    print_msg "$BLUE" "🔧 配置端口..."
    
    # 检查后端端口
    if check_port $BACKEND_PORT; then
        print_msg "$YELLOW" "⚠️  后端端口 $BACKEND_PORT 已被占用"
        BACKEND_PORT=$(find_available_port $BACKEND_PORT)
        if [ $BACKEND_PORT -eq 0 ]; then
            print_msg "$RED" "❌ 无法找到可用的后端端口"
            exit 1
        fi
        print_msg "$GREEN" "   使用备用端口: $BACKEND_PORT"
    else
        print_msg "$GREEN" "✅ 后端端口: $BACKEND_PORT"
    fi
    
    # 检查前端端口
    if [ "$SKIP_FRONTEND" != true ]; then
        if check_port $FRONTEND_PORT; then
            print_msg "$YELLOW" "⚠️  前端端口 $FRONTEND_PORT 已被占用"
            FRONTEND_PORT=$(find_available_port $FRONTEND_PORT)
            if [ $FRONTEND_PORT -eq 0 ]; then
                print_msg "$RED" "❌ 无法找到可用的前端端口"
                exit 1
            fi
            print_msg "$GREEN" "   使用备用端口: $FRONTEND_PORT"
        else
            print_msg "$GREEN" "✅ 前端端口: $FRONTEND_PORT"
        fi
    fi
}

# 创建环境配置
create_env_config() {
    print_msg "$BLUE" "🔧 创建环境配置..."
    
    cat > .env.current << EOF
# Momentum Lens 当前运行配置
# 模式: $START_MODE
# 生成时间: $(date)

# 端口配置
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT

# API配置
BACKEND_URL=http://localhost:$BACKEND_PORT
FRONTEND_URL=http://localhost:$FRONTEND_PORT

# 数据库配置 (轻量级模式)
DATABASE_URL=sqlite:///./momentum_lens.db
USE_SQLITE=true

# 缓存配置
CACHE_TYPE=memory
REDIS_URL=memory://

# 数据源配置
DEFAULT_DATA_SOURCE=akshare
ENABLE_FALLBACK=true
CACHE_DURATION=60000

# 应用配置
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || echo "dev-secret-key")
DEFAULT_PRESET=balanced
EXECUTION_WINDOWS=10:30,14:00
TIMEZONE=Asia/Shanghai
EOF
    
    print_msg "$GREEN" "✅ 环境配置已创建"
}

# 安装后端依赖
setup_backend() {
    print_msg "$BLUE" "🐍 设置后端环境..."
    
    cd backend
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        print_msg "$BLUE" "   创建Python虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip --quiet
    
    # 安装依赖
    if [ "$START_MODE" = "lite" ] || [ "$START_MODE" = "backend-only" ] || [ "$START_MODE" = "vite" ]; then
        print_msg "$BLUE" "   安装轻量级依赖..."
        pip install fastapi uvicorn sqlalchemy aiosqlite pandas numpy akshare \
                   yfinance pydantic python-dotenv python-dateutil pytz \
                   httpx aiohttp websockets python-socketio --quiet
    else
        if [ -f "requirements.txt" ]; then
            print_msg "$BLUE" "   安装完整依赖..."
            pip install -r requirements.txt --quiet
        fi
    fi
    
    cd ..
    print_msg "$GREEN" "✅ 后端环境准备完成"
}

# 安装前端依赖
setup_frontend() {
    if [ "$SKIP_FRONTEND" = true ]; then
        return
    fi
    
    print_msg "$BLUE" "⚛️  设置前端环境..."
    
    if [ "$START_MODE" = "vite" ]; then
        # 检查是否需要创建Vite项目
        if [ ! -d "frontend/node_modules" ] || [ ! -f "frontend/vite.config.ts" ]; then
            print_msg "$YELLOW" "   需要先运行 ./use-vite.sh 创建Vite前端"
            ./use-vite.sh
        fi
    else
        # 标准前端设置
        if [ ! -d "frontend/node_modules" ]; then
            cd frontend
            print_msg "$BLUE" "   安装前端依赖..."
            npm install --legacy-peer-deps --quiet
            cd ..
        fi
    fi
    
    print_msg "$GREEN" "✅ 前端环境准备完成"
}

# 启动后端
start_backend() {
    print_msg "$BLUE" "🚀 启动后端服务..."
    
    cd backend
    source venv/bin/activate
    
    # 选择启动文件
    if [ "$START_MODE" = "lite" ] || [ "$START_MODE" = "backend-only" ] || [ "$START_MODE" = "vite" ]; then
        if [ -f "main_lite.py" ]; then
            MAIN_FILE="main_lite.py"
        else
            MAIN_FILE="main.py"
        fi
    else
        MAIN_FILE="main.py"
    fi
    
    # 启动后端
    PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../$BACKEND_PID_FILE
    
    cd ..
    
    # 等待后端启动
    sleep 3
    
    # 检查后端是否成功启动
    if kill -0 $BACKEND_PID 2>/dev/null; then
        print_msg "$GREEN" "✅ 后端已启动 (PID: $BACKEND_PID)"
        print_msg "$GREEN" "   API地址: http://localhost:$BACKEND_PORT"
        print_msg "$GREEN" "   API文档: http://localhost:$BACKEND_PORT/docs"
    else
        print_msg "$RED" "❌ 后端启动失败"
        print_msg "$YELLOW" "   查看日志: tail -f backend.log"
        exit 1
    fi
}

# 启动前端
start_frontend() {
    if [ "$SKIP_FRONTEND" = true ] || [ "$START_MODE" = "backend-only" ]; then
        return
    fi
    
    print_msg "$BLUE" "🚀 启动前端服务..."
    
    cd frontend
    
    # 更新前端配置以使用正确的后端端口
    if [ -f ".env" ]; then
        sed -i.bak "s|REACT_APP_API_URL=.*|REACT_APP_API_URL=http://localhost:$BACKEND_PORT|" .env
        sed -i.bak "s|VITE_API_URL=.*|VITE_API_URL=http://localhost:$BACKEND_PORT|" .env
    fi
    
    # 启动前端
    if [ "$START_MODE" = "vite" ]; then
        PORT=$FRONTEND_PORT npm run dev > ../frontend.log 2>&1 &
    else
        PORT=$FRONTEND_PORT npm start > ../frontend.log 2>&1 &
    fi
    
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../$FRONTEND_PID_FILE
    
    cd ..
    
    # 等待前端启动
    sleep 5
    
    # 检查前端是否成功启动
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        print_msg "$GREEN" "✅ 前端已启动 (PID: $FRONTEND_PID)"
        print_msg "$GREEN" "   访问地址: http://localhost:$FRONTEND_PORT"
    else
        print_msg "$YELLOW" "⚠️  前端启动可能需要更多时间"
        print_msg "$YELLOW" "   查看日志: tail -f frontend.log"
    fi
}

# 启动Docker
start_docker() {
    print_msg "$BLUE" "🐳 启动Docker容器..."
    
    if ! command -v docker &> /dev/null; then
        print_msg "$RED" "❌ Docker 未安装"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_msg "$RED" "❌ Docker Compose 未安装"
        exit 1
    fi
    
    docker-compose up -d
    
    print_msg "$GREEN" "✅ Docker容器已启动"
    print_msg "$GREEN" "   查看状态: docker-compose ps"
    print_msg "$GREEN" "   查看日志: docker-compose logs -f"
}

# 显示状态
show_status() {
    echo ""
    print_msg "$CYAN" "╔════════════════════════════════════════════╗"
    print_msg "$CYAN" "║         🎉 Momentum Lens 已启动!          ║"
    print_msg "$CYAN" "╚════════════════════════════════════════════╝"
    echo ""
    
    print_msg "$GREEN" "📊 运行状态:"
    print_msg "$GREEN" "   模式: $START_MODE"
    
    if [ "$START_MODE" != "frontend-only" ]; then
        print_msg "$GREEN" "   后端: http://localhost:$BACKEND_PORT"
        print_msg "$GREEN" "   API文档: http://localhost:$BACKEND_PORT/docs"
    fi
    
    if [ "$SKIP_FRONTEND" != true ] && [ "$START_MODE" != "backend-only" ]; then
        print_msg "$GREEN" "   前端: http://localhost:$FRONTEND_PORT"
    fi
    
    echo ""
    print_msg "$YELLOW" "📝 管理命令:"
    print_msg "$YELLOW" "   查看后端日志: tail -f backend.log"
    print_msg "$YELLOW" "   查看前端日志: tail -f frontend.log"
    print_msg "$YELLOW" "   停止所有服务: ./stop.sh"
    print_msg "$YELLOW" "   查看进程: ps aux | grep 'momentum'"
    
    echo ""
    print_msg "$MAGENTA" "💡 提示:"
    print_msg "$MAGENTA" "   - 使用 Ctrl+C 停止所有服务"
    print_msg "$MAGENTA" "   - 配置文件: .env.current"
    print_msg "$MAGENTA" "   - 默认数据源: AKShare (免费)"
    
    echo ""
}

# 清理函数
cleanup() {
    echo ""
    print_msg "$YELLOW" "🛑 正在停止服务..."
    
    # 停止后端
    if [ -f "$BACKEND_PID_FILE" ]; then
        BACKEND_PID=$(cat $BACKEND_PID_FILE)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID 2>/dev/null || true
            print_msg "$GREEN" "   后端已停止"
        fi
        rm -f $BACKEND_PID_FILE
    fi
    
    # 停止前端
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat $FRONTEND_PID_FILE)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID 2>/dev/null || true
            print_msg "$GREEN" "   前端已停止"
        fi
        rm -f $FRONTEND_PID_FILE
    fi
    
    print_msg "$GREEN" "✅ 服务已停止"
    exit 0
}

# 主流程
main() {
    # 设置信号处理
    trap cleanup INT TERM
    
    # 打印Logo
    print_logo
    
    # 清理旧进程
    cleanup_old_processes
    
    # 检查依赖
    check_dependencies
    
    # 选择启动模式
    select_mode
    
    # 配置端口
    configure_ports
    
    # 创建环境配置
    create_env_config
    
    # 根据模式启动服务
    case $START_MODE in
        docker)
            start_docker
            ;;
        frontend-only)
            setup_frontend
            SKIP_BACKEND=true
            start_frontend
            ;;
        *)
            setup_backend
            start_backend
            
            if [ "$START_MODE" != "backend-only" ]; then
                setup_frontend
                start_frontend
            fi
            ;;
    esac
    
    # 显示状态
    show_status
    
    # 等待用户中断
    while true; do
        sleep 1
    done
}

# 运行主程序
main "$@"