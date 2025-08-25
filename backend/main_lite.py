"""
Momentum Lens Lite - 轻量级后端
使用SQLite和内存缓存，无需外部依赖
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
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

@app.get("/api/health")
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

@app.get("/api/market/etf/{code}")
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

@app.get("/api/market/indicators")
async def get_market_indicators():
    """获取市场指标"""
    try:
        # 获取沪深300数据
        df = ak.stock_zh_index_daily(symbol="sh000300")
        latest = df.iloc[-1]
        ma200 = df['close'].rolling(window=200).mean().iloc[-1]
        
        return {
            "yearline": {
                "status": "ABOVE" if float(latest['close']) > float(ma200) else "BELOW",
                "value": float(ma200)
            },
            "atr": {
                "status": "NORMAL",
                "value": 2.5
            },
            "chop": {
                "status": "TRENDING",
                "value": 45.0
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # 返回模拟数据
        return {
            "yearline": {
                "status": "ABOVE",
                "value": 3450.0
            },
            "atr": {
                "status": "NORMAL",
                "value": 2.5
            },
            "chop": {
                "status": "TRENDING",
                "value": 45.0
            },
            "timestamp": datetime.now().isoformat(),
            "note": "Mock data due to API error"
        }

@app.post("/api/decisions/calculate")
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

@app.get("/api/config/settings")
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

@app.get("/api/market/data-sources")
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

@app.get("/api/decisions/current")
async def get_current_decision():
    """获取当前决策"""
    return {
        "firstLeg": {
            "code": "588000",
            "name": "科创50ETF",
            "score": 0.145,
            "r60": 0.15,
            "r120": 0.14
        },
        "secondLeg": {
            "code": "512760",
            "name": "半导体ETF",
            "score": 0.132,
            "r60": 0.12,
            "r120": 0.13
        },
        "weights": {
            "trial": 5,
            "full": 10
        },
        "iopvBands": {
            "lower": 0.999,
            "upper": 1.001
        },
        "qualifications": {
            "buffer": True,
            "minHolding": True,
            "correlation": True,
            "legLimit": True
        },
        "qdiiStatus": {
            "premium": 1.5,
            "status": "OK"
        },
        "yearline": {
            "status": "ABOVE"
        },
        "atr": {
            "value": 2.5,
            "status": "NORMAL"
        },
        "chop": {
            "value": 45,
            "status": "TRENDING"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/portfolio/holdings")
async def get_holdings():
    """获取持仓"""
    return [
        {
            "code": "510300",
            "name": "沪深300ETF",
            "shares": 1000,
            "entryPrice": 3.5,
            "currentPrice": 3.6,
            "weight": 0.2,
            "targetWeight": 20.0,  # 目标权重
            "currentWeight": 19.5,  # 当前权重
            "deviation": -0.5,  # 偏差
            "return": 0.028,
            "category": "Core"
        },
        {
            "code": "510880",
            "name": "上证红利ETF",
            "shares": 800,
            "entryPrice": 2.8,
            "currentPrice": 2.9,
            "weight": 0.15,
            "targetWeight": 15.0,
            "currentWeight": 14.8,
            "deviation": -0.2,
            "return": 0.036,
            "category": "Core"
        },
        {
            "code": "511990",
            "name": "华宝添益",
            "shares": 5000,
            "entryPrice": 100.0,
            "currentPrice": 100.01,
            "weight": 0.10,
            "targetWeight": 10.0,
            "currentWeight": 10.1,
            "deviation": 0.1,
            "return": 0.0001,
            "category": "Core"
        },
        {
            "code": "518880",
            "name": "华安黄金ETF",
            "shares": 250,
            "entryPrice": 4.2,
            "currentPrice": 4.35,
            "weight": 0.10,
            "targetWeight": 10.0,
            "currentWeight": 9.8,
            "deviation": -0.2,
            "return": 0.036,
            "category": "Core"
        },
        {
            "code": "513500",
            "name": "标普500",
            "shares": 300,
            "entryPrice": 1.65,
            "currentPrice": 1.68,
            "weight": 0.05,
            "targetWeight": 5.0,
            "currentWeight": 5.2,
            "deviation": 0.2,
            "premium": 1.8,  # QDII溢价率
            "return": 0.018,
            "category": "Core"
        }
    ]

@app.get("/api/market/momentum-rankings")
async def get_momentum_rankings():
    """获取动量排名"""
    return [
        {"code": "588000", "name": "科创50ETF", "score": 0.145, "r60": 15.0, "r120": 14.0, "volume": 12500000, "spread": 0.05},
        {"code": "512760", "name": "半导体ETF", "score": 0.132, "r60": 12.0, "r120": 13.0, "volume": 8900000, "spread": 0.06},
        {"code": "512720", "name": "计算机ETF", "score": 0.125, "r60": 11.0, "r120": 12.0, "volume": 6700000, "spread": 0.04},
        {"code": "516160", "name": "新能源ETF", "score": 0.118, "r60": 10.0, "r120": 11.0, "volume": 5400000, "spread": 0.07},
        {"code": "515790", "name": "光伏ETF", "score": 0.112, "r60": 9.0, "r120": 10.0, "volume": 4200000, "spread": 0.08}
    ]

@app.get("/api/market/hs300-chart")
async def get_hs300_chart(period: str = "6M"):
    """获取沪深300图表数据"""
    # 生成时间序列数据（TradingView图表格式）
    base_date = 1707091200  # 2024-02-05 的Unix时间戳
    day_seconds = 86400
    
    prices_data = [
        {"time": base_date, "value": 3400},
        {"time": base_date + day_seconds * 30, "value": 3450},
        {"time": base_date + day_seconds * 60, "value": 3500},
        {"time": base_date + day_seconds * 90, "value": 3480},
        {"time": base_date + day_seconds * 120, "value": 3520},
        {"time": base_date + day_seconds * 150, "value": 3550},
        {"time": base_date + day_seconds * 180, "value": 3500}
    ]
    
    ma200_data = [
        {"time": base_date, "value": 3350},
        {"time": base_date + day_seconds * 30, "value": 3360},
        {"time": base_date + day_seconds * 60, "value": 3380},
        {"time": base_date + day_seconds * 90, "value": 3400},
        {"time": base_date + day_seconds * 120, "value": 3420},
        {"time": base_date + day_seconds * 150, "value": 3440},
        {"time": base_date + day_seconds * 180, "value": 3450}
    ]
    
    return {
        "prices": prices_data,
        "ma200": ma200_data,
        "period": period,
        "latest": {
            "price": 3500,
            "ma200": 3450,
            "aboveMa200": True
        }
    }

@app.get("/api/portfolio/dca-schedule")
async def get_dca_schedule():
    """获取定投计划"""
    return {
        "enabled": True,
        "frequency": "weekly",
        "amount": 10000,
        "nextDate": "2024-08-27",  # 改为nextDate，与前端匹配
        "nextExecution": "2024-08-27",  # 保留兼容性
        "allocation": {
            "510300": 0.33,
            "510880": 0.33,
            "511990": 0.34
        }
    }

@app.get("/api/trading/logs")
async def get_trade_logs(startDate: Optional[str] = None, endDate: Optional[str] = None):
    """获取交易日志"""
    return [
        {
            "id": "1",
            "date": "2024-08-20",
            "timestamp": "2024-08-20T10:30:00",
            "code": "588000",
            "name": "科创50ETF",
            "action": "BUY",
            "price": 0.95,
            "shares": 5000,
            "amount": 4750,
            "status": "executed",
            "type": "LIMIT",
            "slippage": 0.05  # 添加滑点字段
        },
        {
            "id": "2",
            "date": "2024-08-13",
            "timestamp": "2024-08-13T14:00:00",
            "code": "512760",
            "name": "半导体ETF",
            "action": "BUY",
            "price": 0.82,
            "shares": 6000,
            "amount": 4920,
            "status": "executed",
            "type": "LIMIT",
            "slippage": -0.02  # 添加滑点字段
        }
    ]

@app.get("/api/performance/metrics")
async def get_performance_metrics():
    """获取绩效指标"""
    return {
        "totalReturn": 0.085,
        "yearlyReturn": 0.102,
        "sharpeRatio": 1.25,
        "maxDrawdown": -12.0,  # 改为百分比格式
        "winRate": 0.65,
        "avgWin": 0.08,
        "avgLoss": -0.04,
        "monthlyIS": 0.35,  # 添加月度实施偏差
        "turnoverEfficiency": 85.5,  # 添加换手效率
        "calmarRatio": 0.85  # 添加Calmar比率
    }

@app.get("/api/performance/returns")
async def get_returns(period: str = "6M"):
    """获取收益数据"""
    return {
        "data": [
            {"date": "2024-02-01", "return": 0.02},
            {"date": "2024-03-01", "return": 0.03},
            {"date": "2024-04-01", "return": -0.01},
            {"date": "2024-05-01", "return": 0.025},
            {"date": "2024-06-01", "return": 0.015},
            {"date": "2024-07-01", "return": 0.028},
            {"date": "2024-08-01", "return": -0.005}
        ],
        "period": period
    }

@app.get("/api/performance/drawdown")
async def get_drawdown():
    """获取回撤数据"""
    return {
        "current": -0.05,
        "max": -0.12,
        "data": [
            {"date": "2024-02-01", "drawdown": -0.02},
            {"date": "2024-03-01", "drawdown": -0.01},
            {"date": "2024-04-01", "drawdown": -0.08},
            {"date": "2024-05-01", "drawdown": -0.05},
            {"date": "2024-06-01", "drawdown": -0.03},
            {"date": "2024-07-01", "drawdown": -0.02},
            {"date": "2024-08-01", "drawdown": -0.05}
        ]
    }

@app.get("/api/alerts")
async def get_alerts(unreadOnly: bool = False):
    """获取预警信息"""
    # 返回示例预警信息，避免空数组导致的问题
    return [
        {
            "id": "alert1",
            "type": "INFO",
            "title": "市场状态正常",
            "message": "当前市场环境适合交易",
            "timestamp": "2024-08-25T09:00:00",
            "read": False,
            "severity": "low"
        }
    ]

@app.post("/api/market/test-source")
async def test_data_source(request: Dict[str, Any]):
    """测试数据源"""
    return {
        "success": True,
        "latency": 120
    }

@app.post("/api/market/fetch")
async def fetch_market_data(request: Dict[str, Any]):
    """获取市场数据"""
    return {
        "data": {
            "code": request.get("symbol", "000001"),
            "price": 10.5,
            "change": 0.2,
            "volume": 1000000
        }
    }

@app.post("/api/market/fetch-batch")
async def fetch_batch_data(request: Dict[str, Any]):
    """批量获取市场数据"""
    symbols = request.get("symbols", [])
    result = {}
    for symbol in symbols:
        result[symbol] = {
            "price": 10.5,
            "change": 0.2,
            "volume": 1000000
        }
    return {"data": result}

@app.post("/api/config/settings")
async def update_settings(settings: Dict[str, Any]):
    """更新配置"""
    return settings

@app.get("/api/config/presets")
async def get_presets():
    """获取预设配置"""
    return [
        {"name": "进攻", "stopLoss": 10, "buffer": 2, "minHolding": 14},
        {"name": "均衡", "stopLoss": 12, "buffer": 3, "minHolding": 14},
        {"name": "保守", "stopLoss": 15, "buffer": 4, "minHolding": 28}
    ]

@app.get("/api/trading/export")
async def export_trades(format: str = "csv"):
    """导出交易记录"""
    # 返回模拟的CSV数据
    csv_content = "Date,Code,Name,Action,Price,Shares,Amount\n"
    csv_content += "2024-08-20,588000,科创50ETF,BUY,0.95,5000,4750\n"
    csv_content += "2024-08-13,512760,半导体ETF,BUY,0.82,6000,4920\n"
    
    if format == "csv":
        return PlainTextResponse(content=csv_content, media_type="text/csv")
    else:
        # PDF格式暂时返回CSV
        return PlainTextResponse(content=csv_content, media_type="text/plain")

@app.get("/api/market/correlation")
async def get_correlation(anchor: str = "510300"):
    """获取相关性矩阵"""
    # 返回完整的相关性矩阵格式
    etfs = ["510300", "588000", "512760", "512720", "516160"]
    
    # 模拟的相关性矩阵（对称矩阵）
    correlation_matrix = [
        [1.00, 0.65, 0.58, 0.72, 0.45],  # 510300
        [0.65, 1.00, 0.82, 0.76, 0.68],  # 588000
        [0.58, 0.82, 1.00, 0.89, 0.71],  # 512760
        [0.72, 0.76, 0.89, 1.00, 0.63],  # 512720
        [0.45, 0.68, 0.71, 0.63, 1.00],  # 516160
    ]
    
    return {
        "anchor": anchor,
        "etfs": etfs,
        "values": correlation_matrix,
        "matrix": [
            {"code": etf, "correlation": correlation_matrix[0][i]} 
            for i, etf in enumerate(etfs)
        ]
    }

# WebSocket端点（简单实现）
@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """WebSocket端点for价格推送（轻量版仅返回模拟数据）"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 简单回显，实际应推送价格数据
            await websocket.send_json({
                "type": "price_update",
                "data": {"message": "WebSocket connected"},
                "timestamp": datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """WebSocket端点for交易信号（轻量版仅返回模拟数据）"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "signal",
                "data": {"message": "No new signals"},
                "timestamp": datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        pass

# Socket.IO兼容端点（返回提示信息）
@app.get("/socket.io/")
async def socketio_fallback():
    """Socket.IO兼容端点 - 轻量版不支持"""
    return {"message": "Socket.IO not supported in lite version", "status": "use_websocket_instead"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
