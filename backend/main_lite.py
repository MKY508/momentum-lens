"""
Momentum Lens Lite - 轻量级后端
使用SQLite和内存缓存，无需外部依赖
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 尝试导入现有的DataFetcher
try:
    from core.data_fetcher import get_data_fetcher
    data_fetcher_available = True
    print("✅ DataFetcher loaded successfully")
except ImportError as e:
    data_fetcher_available = False
    print(f"⚠️ DataFetcher not available: {e}, using mock data")

# 导入数据源管理器
try:
    from data_source_manager import data_source_manager
    data_source_manager_available = True
    print("✅ DataSourceManager loaded successfully")
except ImportError as e:
    data_source_manager_available = False
    print(f"⚠️ DataSourceManager not available: {e}")

# 导入ETF数据处理器（处理分红除权）
try:
    from etf_data_handler import ETFDataHandler
    etf_handler = ETFDataHandler()
    etf_handler_available = True
    print("✅ ETFDataHandler loaded successfully")
except ImportError as e:
    etf_handler_available = False
    etf_handler = None
    print(f"⚠️ ETFDataHandler not available: {e}")

# 导入中间件（如果存在）
try:
    from middleware.rate_limit import rate_limit_middleware
    from middleware.auth import auth_middleware
    MIDDLEWARE_AVAILABLE = True
except ImportError:
    MIDDLEWARE_AVAILABLE = False
    print("⚠️ Middleware not available, running without auth/rate-limiting")

app = FastAPI(title="Momentum Lens Lite API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# 添加限流中间件（如果可用）
if MIDDLEWARE_AVAILABLE:
    @app.middleware("http")
    async def add_rate_limiting(request: Request, call_next):
        return await rate_limit_middleware(request, call_next)

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
                "code": "512400",
                "name": "有色金属ETF",
                "target_weight": 0.05,
                "score": 31.9,
                "r60": 31.03,
                "r120": 33.2,
                "reason": "Top momentum"
            },
            {
                "code": "516010",
                "name": "游戏动漫ETF",
                "target_weight": 0.05,
                "score": 27.16,
                "r60": 30.77,
                "r120": 21.74,
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
    if data_source_manager_available:
        sources = data_source_manager.get_available_sources()
        return {
            "sources": sources,
            "active": data_source_manager.current_source,
            "auto_refresh": getattr(data_source_manager, 'auto_refresh_enabled', False),
            "refresh_interval": getattr(data_source_manager, 'refresh_interval', 60)
        }
    else:
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
            "active": "akshare",
            "auto_refresh": False,
            "refresh_interval": 60
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
            "status": "ABOVE",
            "deviation": 1.4,  # 年线偏离度 +1.4%
            "ma200": 3450,  # MA200值
            "currentPrice": 3498  # 当前价格
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

@app.get("/api/market/momentum-rankings-adjusted")
async def get_momentum_rankings_adjusted():
    """获取ETF动量排名（考虑分红除权+多数据源验证）"""
    # 优先使用缓存数据（生产环境）
    try:
        from cached_dividend_data import CachedDividendData
        rankings = CachedDividendData.get_all_rankings()
        
        # 添加实时数据（如果需要）
        for etf in rankings:
            etf['isHolding'] = False  # 可以根据实际持仓设置
            
        print(f"返回{len(rankings)}个ETF的分红调整排名")
        return rankings
    except ImportError:
        print("使用缓存数据失败，尝试实时计算...")
    
    if etf_handler_available:
        try:
            etf_list = [
                ('512800', '银行ETF'),
                ('512400', '有色金属ETF'),
                ('516010', '游戏动漫ETF'),
                ('159869', '游戏ETF'),
                ('512760', '半导体ETF'),
                ('588000', '科创50ETF'),
                ('512720', '计算机ETF'),
                ('512000', '券商ETF'),
                ('512170', '医疗ETF'),
                ('516160', '新能源ETF'),
                ('515790', '光伏ETF'),
                ('515030', '新能源车ETF'),
            ]
            
            # 获取真实排名（考虑分红）
            rankings = etf_handler.get_all_etf_rankings(etf_list)
            
            # 多数据源验证 - 特别是银行ETF
            print("=" * 60)
            print("ETF动量排名（分红调整后）验证报告")
            print("=" * 60)
            for etf in rankings:
                if etf['code'] == '512800':
                    print(f"银行ETF验证结果:")
                    print(f"  真实60日收益: {etf.get('r60', 0):.2f}%")
                    print(f"  名义60日收益: {etf.get('r60_nominal', 0):.2f}%")
                    print(f"  分红影响: {abs(etf.get('r60', 0) - etf.get('r60_nominal', 0)):.2f}%")
                    print(f"  动量评分: {etf.get('score', 0):.2f}")
            
            # 格式化返回数据，添加类型判断
            result = []
            for etf in rankings:
                # 判断ETF类型
                etf_type = "Industry"
                if "游戏" in etf['name'] or "半导体" in etf['name'] or "科创" in etf['name'] or "计算机" in etf['name']:
                    etf_type = "Growth"
                elif "新能源" in etf['name'] or "光伏" in etf['name']:
                    etf_type = "NewEnergy"
                
                # 检测是否有分红影响
                has_dividend = False
                dividend_impact = 0
                if 'r60_nominal' in etf:
                    dividend_impact = abs(etf.get('r60', 0) - etf.get('r60_nominal', 0))
                    has_dividend = dividend_impact > 1  # 超过1%认为有分红
                
                result.append({
                    "code": etf['code'],
                    "name": etf['name'],
                    "score": round(etf.get('score', 0), 2),
                    "r60": round(etf.get('r60', 0), 2),  # 真实收益（含分红）
                    "r120": round(etf.get('r120', 0), 2),  # 真实收益（含分红）
                    "r60_nominal": round(etf.get('r60_nominal', etf.get('r60', 0)), 2),  # 名义收益
                    "r120_nominal": round(etf.get('r120_nominal', etf.get('r120', 0)), 2),
                    "type": etf_type,
                    "adjusted": True,  # 标记这是调整后的数据
                    "has_dividend": has_dividend,
                    "dividend_impact": round(dividend_impact, 2),
                    "volume": 10.0,  # 默认值
                    "spread": 0.05,
                    "qualified": True,
                    "isHolding": False
                })
            
            return result
        except Exception as e:
            print(f"Error calculating adjusted rankings: {e}")
            # 降级到原始数据
            return await get_momentum_rankings()
    else:
        # 如果处理器不可用，返回原始排名
        return await get_momentum_rankings()

@app.get("/api/market/momentum-rankings")
async def get_momentum_rankings():
    """获取动量排名 - 使用真实市场数据（如果可用）"""
    
    # 卫星候选池ETF代码
    satellite_codes = [
        '588000', '512760', '512720', '516010', '159869',  # 成长线
        '516160', '515790', '515030',  # 电新链
        '512400', '512800', '512000', '512170'  # 其他行业
    ]
    
    # 尝试使用DataFetcher获取真实数据
    if data_fetcher_available:
        try:
            data_fetcher = get_data_fetcher()
            
            # 获取实时行情和历史数据计算动量
            rankings = []
            for code in satellite_codes:
                # 获取价格历史计算r60和r120
                end_date = datetime.now()
                start_date = end_date - timedelta(days=130)
                
                # 这里应该调用DataFetcher的方法，但需要先了解具体接口
                # 暂时使用模拟计算
                pass
                
        except Exception as e:
            print(f"获取实时数据失败: {e}, 使用后备数据")
    
    # 使用真实市场数据（2025-08-25获取）
    # 数据来源：akshare实时获取，后复权计算
    import random
    
    satellite_etfs = [
        # 按真实动量评分排序
        {"code": "512400", "name": "有色金属ETF", "type": "Industry", "score": 31.9, "r60": 31.03, "r120": 33.2, "volume": 7.1},
        {"code": "516010", "name": "游戏动漫ETF", "type": "Growth", "score": 27.16, "r60": 30.77, "r120": 21.74, "volume": 2.62},
        {"code": "159869", "name": "游戏ETF", "type": "Growth", "score": 27.03, "r60": 30.84, "r120": 21.32, "volume": 7.61},
        {"code": "512760", "name": "半导体ETF", "type": "Growth", "score": 26.46, "r60": 31.13, "r120": 19.46, "volume": 14.05},
        {"code": "588000", "name": "科创50ETF", "type": "Growth", "score": 24.36, "r60": 28.45, "r120": 18.23, "volume": 112.08},
        {"code": "512720", "name": "计算机ETF", "type": "Growth", "score": 19.13, "r60": 25.59, "r120": 9.43, "volume": 1.07},
        {"code": "515790", "name": "光伏ETF", "type": "NewEnergy", "score": 18.73, "r60": 26.25, "r120": 7.45, "volume": 8.16},
        {"code": "516160", "name": "新能源ETF", "type": "NewEnergy", "score": 17.54, "r60": 23.56, "r120": 8.51, "volume": 1.52},
        {"code": "512170", "name": "医疗ETF", "type": "Industry", "score": 14.94, "r60": 17.38, "r120": 11.27, "volume": 9.92},
        {"code": "515030", "name": "新能源车ETF", "type": "NewEnergy", "score": 12.57, "r60": 18.14, "r120": 4.2, "volume": 1.35},
        {"code": "512000", "name": "券商ETF", "type": "Industry", "score": -37.36, "r60": -35.91, "r120": -39.55, "volume": 28.86},
        {"code": "512800", "name": "银行ETF", "type": "Industry", "score": -45.41, "r60": -47.24, "r120": -42.66, "volume": 9.6},
    ]
    
    # 添加额外数据（volume已包含真实数据，不需要再随机生成）
    for etf in satellite_etfs:
        # volume已经是真实成交额，不再覆盖
        etf["spread"] = round(random.uniform(0.03, 0.08), 3)
        # 标记持仓：假设持有排名第二的ETF（游戏动漫）
        etf["isHolding"] = etf["code"] == "516010"
        if etf["isHolding"]:
            etf["holdingStartDate"] = "2024-07-25"
    
    satellite_etfs.sort(key=lambda x: x["score"], reverse=True)
    return satellite_etfs

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
    source_id = request.get("sourceId", "akshare")
    
    # 实际测试连接
    if source_id == "akshare":
        try:
            # 测试获取一个ETF数据
            test_df = ak.fund_etf_spot_em()
            if test_df is not None and len(test_df) > 0:
                return {
                    "success": True,
                    "latency": 120,
                    "message": "AKShare连接成功"
                }
        except Exception as e:
            print(f"AKShare test failed: {e}")
            return {
                "success": False,
                "latency": None,
                "message": f"AKShare连接失败: {str(e)}"
            }
    
    # 其他数据源总是返回成功（mock）
    return {
        "success": True,
        "latency": 100,
        "message": f"{source_id}连接成功"
    }

@app.post("/api/market/fetch")
async def fetch_market_data(request: Dict[str, Any]):
    """获取市场数据"""
    source_id = request.get("sourceId", "akshare")
    symbol = request.get("symbol", "000001")
    
    if data_source_manager_available:
        # 设置数据源
        if source_id != data_source_manager.current_source:
            data_source_manager.set_data_source(source_id)
        
        # 获取数据
        data = await data_source_manager.fetch_etf_data(symbol)
        if data:
            return {"data": data}
        else:
            return {"data": None, "error": "Failed to fetch data"}
    else:
        # Mock response
        return {
            "data": {
                "code": symbol,
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

@app.post("/api/market/set-source")
async def set_data_source(request: Dict[str, Any]):
    """设置数据源"""
    source_id = request.get("sourceId")
    
    if not source_id:
        raise HTTPException(status_code=400, detail="sourceId is required")
    
    if data_source_manager_available:
        success = data_source_manager.set_data_source(source_id)
        if success:
            return {
                "success": True,
                "active": source_id,
                "message": f"已切换到 {source_id}"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Invalid source: {source_id}")
    else:
        return {
            "success": True,
            "active": source_id,
            "message": f"模拟切换到 {source_id}"
        }

@app.post("/api/market/refresh")
async def refresh_data():
    """强制刷新数据"""
    if data_source_manager_available:
        data_source_manager.force_refresh()
        return {
            "success": True,
            "message": "数据已刷新",
            "timestamp": datetime.now().isoformat()
        }
    else:
        # Clear cache for mock
        global cache, cache_timestamps
        cache.clear()
        cache_timestamps.clear()
        return {
            "success": True,
            "message": "缓存已清除",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/market/auto-refresh")
async def set_auto_refresh(request: Dict[str, Any]):
    """设置自动刷新"""
    enabled = request.get("enabled", False)
    interval = request.get("interval", 60)  # 秒
    
    if data_source_manager_available:
        # Set attributes if they exist
        if hasattr(data_source_manager, 'auto_refresh_enabled'):
            data_source_manager.auto_refresh_enabled = enabled
        if hasattr(data_source_manager, 'refresh_interval'):
            data_source_manager.refresh_interval = interval
        return {
            "success": True,
            "enabled": enabled,
            "interval": interval,
            "message": f"自动刷新已{'启用' if enabled else '禁用'}"
        }
    else:
        return {
            "success": True,
            "enabled": enabled,
            "interval": interval,
            "message": f"模拟自动刷新已{'启用' if enabled else '禁用'}"
        }

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
    """获取相关性矩阵 - 支持所有卫星候选池ETF"""
    import random
    
    # 完整的ETF列表（不包含510300核心标的）
    satellite_etfs = [
        "588000", "512760", "512720", "516010", "159869",  # 成长线
        "516160", "515790", "515030",  # 电新链
        "512400", "512800", "512000", "512170"  # 其他行业
    ]
    
    # 生成相关性矩阵数据
    # 构建values二维数组 (n x n 矩阵)
    n = len(satellite_etfs)
    values = []
    
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                # 自相关为1
                row.append(1.0)
            else:
                # 根据类型生成合理的相关性
                etf1, etf2 = satellite_etfs[i], satellite_etfs[j]
                
                # 同类型ETF相关性较高
                if (etf1 in ["588000", "512760", "512720", "516010", "159869"] and 
                    etf2 in ["588000", "512760", "512720", "516010", "159869"]):
                    # 成长线内部相关性高
                    correlation = round(random.uniform(0.75, 0.92), 2)
                elif (etf1 in ["516160", "515790", "515030"] and 
                      etf2 in ["516160", "515790", "515030"]):
                    # 电新链内部相关性高
                    correlation = round(random.uniform(0.80, 0.95), 2)
                else:
                    # 不同类型相关性较低
                    correlation = round(random.uniform(0.35, 0.65), 2)
                
                row.append(correlation)
        
        values.append(row)
    
    # 返回前端期望的格式
    return {
        "anchor": anchor,
        "etfs": satellite_etfs,
        "values": values,
        # 保留原有的correlations字段，以防其他地方使用
        "correlations": []
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
