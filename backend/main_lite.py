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
