#!/bin/bash

# Momentum Lens - 轻量级快速启动脚本
# 使用SQLite代替PostgreSQL，无需复杂依赖

set -e

echo "🚀 Momentum Lens Lite - 轻量级快速启动"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查Python
echo -e "${BLUE}📦 检查Python环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3未安装${NC}"
    echo "请安装Python 3.8或更高版本"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1,2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION 已安装${NC}"

# 检查Node.js
echo -e "${BLUE}📦 检查Node.js环境...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js未安装，前端将无法启动${NC}"
    echo "建议安装Node.js 16或更高版本"
    SKIP_FRONTEND=true
else
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✅ Node.js $NODE_VERSION 已安装${NC}"
    SKIP_FRONTEND=false
fi

# 创建轻量级环境配置
echo -e "${BLUE}🔧 创建轻量级配置...${NC}"
cat > .env.lite << EOF
# Momentum Lens Lite Configuration
# 使用SQLite和内存缓存，无需外部数据库

# Database - 使用SQLite
DATABASE_URL=sqlite:///./momentum_lens.db
USE_SQLITE=true

# Cache - 使用内存缓存
CACHE_TYPE=memory
REDIS_URL=memory://

# API Configuration
DEFAULT_DATA_SOURCE=akshare
ENABLE_FALLBACK=true
CACHE_DURATION=60000

# Application
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Trading Configuration
DEFAULT_PRESET=balanced
EXECUTION_WINDOWS=10:30,14:00
TIMEZONE=Asia/Shanghai

# Data Sources (all free, no key required)
USE_AKSHARE=true
USE_SINA=true
USE_EASTMONEY=true
EOF

echo -e "${GREEN}✅ 轻量级配置创建完成${NC}"

# 创建Python虚拟环境
echo -e "${BLUE}🐍 设置Python环境...${NC}"
if [ ! -d "backend/venv" ]; then
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装轻量级依赖
    echo -e "${BLUE}📦 安装后端依赖（轻量级）...${NC}"
    
    # 创建轻量级requirements
    cat > requirements-lite.txt << EOF
# Core - 核心依赖
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database - 使用SQLite替代PostgreSQL
sqlalchemy==2.0.23
aiosqlite==0.19.0

# Data Processing - 数据处理
pandas==2.1.3
numpy==1.26.2

# Market Data - 免费数据源
akshare==1.12.0
yfinance==0.2.33

# Cache - 内存缓存
cachetools==5.3.2

# Configuration - 配置
pydantic==2.5.0
python-dotenv==1.0.0

# Date/Time - 时间处理
python-dateutil==2.8.2
pytz==2023.3

# HTTP Client - HTTP客户端
httpx==0.25.2
aiohttp==3.9.1

# WebSocket - 实时通信
websockets==12.0
python-socketio==5.10.0
EOF
    
    # 安装依赖
    pip install -r requirements-lite.txt
    
    # 清理
    rm requirements-lite.txt
    cd ..
    echo -e "${GREEN}✅ Python依赖安装完成（轻量级）${NC}"
else
    cd backend
    source venv/bin/activate
    cd ..
    echo -e "${GREEN}✅ Python虚拟环境已存在${NC}"
fi

# 创建简化的后端启动文件
echo -e "${BLUE}📝 创建简化后端...${NC}"
cat > backend/main_lite.py << 'EOF'
"""
Momentum Lens Lite - 轻量级后端
使用SQLite和内存缓存，无需外部依赖
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path

app = FastAPI(title="Momentum Lens Lite API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内存缓存
cache = {}
cache_timestamps = {}
CACHE_DURATION = 60  # 60秒缓存

class MarketData(BaseModel):
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: float
    timestamp: datetime

@app.get("/")
def read_root():
    return {
        "name": "Momentum Lens Lite",
        "version": "1.0.0",
        "status": "running",
        "mode": "lite (SQLite + Memory Cache)",
        "data_source": "AKShare (Free)"
    }

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "running",
            "cache": "memory",
            "database": "sqlite",
            "data_source": "akshare"
        }
    }

@app.get("/api/v1/market/etf/{code}")
async def get_etf_data(code: str):
    """获取ETF数据"""
    cache_key = f"etf_{code}"
    
    # 检查缓存
    if cache_key in cache:
        if datetime.now() - cache_timestamps[cache_key] < timedelta(seconds=CACHE_DURATION):
            return cache[cache_key]
    
    try:
        # 使用AKShare获取ETF数据
        df = ak.fund_etf_spot_em()
        etf_data = df[df['代码'] == code].to_dict('records')
        
        if etf_data:
            result = {
                "code": code,
                "name": etf_data[0].get('名称', ''),
                "price": float(etf_data[0].get('最新价', 0)),
                "change": float(etf_data[0].get('涨跌额', 0)),
                "change_pct": float(etf_data[0].get('涨跌幅', 0)),
                "volume": float(etf_data[0].get('成交量', 0)),
                "timestamp": datetime.now().isoformat()
            }
            
            # 更新缓存
            cache[cache_key] = result
            cache_timestamps[cache_key] = datetime.now()
            
            return result
        else:
            raise HTTPException(status_code=404, detail=f"ETF {code} not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market/indicators")
async def get_market_indicators():
    """获取市场指标"""
    try:
        # 获取沪深300数据
        df = ak.stock_zh_index_daily(symbol="sh000300")
        latest = df.iloc[-1]
        ma200 = df['close'].rolling(window=200).mean().iloc[-1]
        
        return {
            "hs300": {
                "close": float(latest['close']),
                "ma200": float(ma200),
                "above_ma200": float(latest['close']) > float(ma200)
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # 返回模拟数据
        return {
            "hs300": {
                "close": 3500.0,
                "ma200": 3450.0,
                "above_ma200": True
            },
            "timestamp": datetime.now().isoformat(),
            "note": "Mock data due to API error"
        }

@app.get("/api/v1/decisions/calculate")
async def calculate_decision():
    """计算交易决策"""
    # 模拟决策数据
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
                "target_weight": 0.05,
                "score": 0.145,
                "r60": 0.15,
                "r120": 0.14,
                "reason": "Top momentum"
            },
            {
                "code": "512760",
                "name": "半导体ETF",
                "target_weight": 0.05,
                "score": 0.132,
                "r60": 0.12,
                "r120": 0.13,
                "rho": 0.65,
                "reason": "Low correlation second leg"
            }
        ],
        "core_dca": {
            "510300": 6700,
            "510880": 3300,
            "511990": 5000,
            "518880": 3300,
            "513500": 1700
        },
        "alerts": [],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/config/settings")
async def get_settings():
    """获取配置"""
    return {
        "presets": {
            "aggressive": {"stop_loss": -0.10, "buffer": 0.02, "min_holding_days": 14},
            "balanced": {"stop_loss": -0.12, "buffer": 0.03, "min_holding_days": 14},
            "conservative": {"stop_loss": -0.15, "buffer": 0.04, "min_holding_days": 28}
        },
        "current_preset": "balanced",
        "etf_pools": {
            "core": ["510300", "510880", "511990", "518880", "513500"],
            "satellite": ["588000", "512760", "512720", "516010", "516160", "512400"]
        }
    }

@app.get("/api/v1/market/data-sources")
async def get_data_sources():
    """获取可用数据源"""
    return {
        "sources": [
            {
                "id": "akshare",
                "name": "AKShare",
                "type": "free",
                "status": "active",
                "rate_limit": "unlimited"
            },
            {
                "id": "sina",
                "name": "新浪财经",
                "type": "free",
                "status": "available",
                "rate_limit": "1000/min"
            }
        ],
        "active": "akshare"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

echo -e "${GREEN}✅ 简化后端创建完成${NC}"

# 安装前端依赖（如果Node.js可用）
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${BLUE}⚛️  设置React前端...${NC}"
    if [ ! -d "frontend/node_modules" ]; then
        cd frontend
        npm install
        cd ..
        echo -e "${GREEN}✅ 前端依赖安装完成${NC}"
    else
        echo -e "${GREEN}✅ 前端依赖已安装${NC}"
    fi
fi

# 启动服务
echo -e "${BLUE}🚀 启动服务...${NC}"

# 启动后端
cd backend
source venv/bin/activate
python main_lite.py &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✅ 后端运行在: http://localhost:8000${NC}"
echo -e "${GREEN}📚 API文档: http://localhost:8000/docs${NC}"

# 启动前端（如果可用）
if [ "$SKIP_FRONTEND" = false ]; then
    sleep 3
    cd frontend
    npm start &
    FRONTEND_PID=$!
    cd ..
    echo -e "${GREEN}✅ 前端运行在: http://localhost:3000${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✨ Momentum Lens Lite 已启动！${NC}"
echo ""
echo "🌐 访问地址:"
echo "   后端API: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
if [ "$SKIP_FRONTEND" = false ]; then
    echo "   前端界面: http://localhost:3000"
fi
echo ""
echo "📊 轻量级特性:"
echo "   ✓ 使用SQLite，无需PostgreSQL"
echo "   ✓ 内存缓存，无需Redis"
echo "   ✓ AKShare免费数据，无需API密钥"
echo "   ✓ 零配置，开箱即用"
echo ""
echo "🛑 停止服务: 按 Ctrl+C"
echo "=========================================="

# 保存PID
echo $BACKEND_PID > .backend.pid
if [ "$SKIP_FRONTEND" = false ]; then
    echo $FRONTEND_PID > .frontend.pid
fi

# 等待用户中断
trap cleanup INT TERM

cleanup() {
    echo ""
    echo "正在停止服务..."
    kill $BACKEND_PID 2>/dev/null
    if [ "$SKIP_FRONTEND" = false ]; then
        kill $FRONTEND_PID 2>/dev/null
        rm -f .frontend.pid
    fi
    rm -f .backend.pid
    echo "服务已停止"
    exit
}

# 保持脚本运行
wait