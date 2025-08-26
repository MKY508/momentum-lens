"""FastAPI主应用"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import logging
import json
import io
import csv
from pathlib import Path

from engine.decision import DecisionEngine, ModuleType, SignalType
from portfolio.manager import PortfolioManager
from data.datasource import DataSourceFactory
from indicators.momentum import MomentumCalculator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="A股ETF动量核心卫星策略系统",
    description="半自动化ETF投资决策系统",
    version="1.0.0"
)

# 导入新的API路由
try:
    from api_routes import router as api_router
    app.include_router(api_router)
    logger.info("成功加载实时数据API路由")
except ImportError as e:
    logger.warning(f"无法导入api_routes: {e}")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
decision_engine = None
portfolio_manager = None
datasource = None


# Pydantic模型
class MarketEnvironmentResponse(BaseModel):
    """市场环境响应模型"""
    state: str
    ma200_ratio: float
    atr20: float
    chop: float
    vix_level: str
    timestamp: str
    metadata: Dict[str, Any]


class DecisionResponse(BaseModel):
    """决策响应模型"""
    module: str
    signal: str
    code: str
    name: str
    target_weight: float
    current_weight: float
    reason: str
    priority: int
    metadata: Dict[str, Any]


class PortfolioSummaryResponse(BaseModel):
    """组合汇总响应模型"""
    overview: Dict[str, float]
    allocation: Dict[str, Any]
    top_positions: List[Dict[str, Any]]
    last_update: str


class ETFListRequest(BaseModel):
    """ETF列表请求模型"""
    min_turnover: Optional[float] = Field(default=50_000_000, description="最小成交额")
    sector_only: Optional[bool] = Field(default=False, description="仅行业ETF")


class RebalanceRequest(BaseModel):
    """再平衡请求模型"""
    threshold: Optional[float] = Field(default=0.02, description="触发阈值")
    dry_run: Optional[bool] = Field(default=True, description="模拟运行")


class DCAExecuteRequest(BaseModel):
    """定投执行请求模型"""
    week: int = Field(ge=1, le=6, description="周数(1-6)")


class PriceUpdateRequest(BaseModel):
    """价格更新请求模型"""
    prices: Dict[str, float] = Field(description="代码:价格字典")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global decision_engine, portfolio_manager, datasource
    
    try:
        # 初始化组件
        decision_engine = DecisionEngine()
        portfolio_manager = PortfolioManager()
        datasource = DataSourceFactory.get_datasource("akshare")
        
        logger.info("应用启动成功")
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise


@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "message": "A股ETF动量核心卫星策略系统",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health", tags=["System"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "decision_engine": decision_engine is not None,
            "portfolio_manager": portfolio_manager is not None,
            "datasource": datasource is not None
        }
    }


@app.get("/api/market/environment", response_model=MarketEnvironmentResponse, tags=["Market"])
async def get_market_environment():
    """获取市场环境分析"""
    try:
        market_env = await decision_engine.analyze_market_environment()
        
        # 处理NaN值
        import math
        def clean_nan(value):
            if isinstance(value, float) and math.isnan(value):
                return 0.0
            return value
        
        return MarketEnvironmentResponse(
            state=market_env.state.value,
            ma200_ratio=clean_nan(market_env.ma200_ratio),
            atr20=clean_nan(market_env.atr20),
            chop=clean_nan(market_env.chop),
            vix_level=market_env.vix_level,
            timestamp=market_env.timestamp.isoformat(),
            metadata={k: clean_nan(v) if isinstance(v, (int, float)) else v 
                     for k, v in market_env.metadata.items()}
        )
    except Exception as e:
        logger.error(f"获取市场环境失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/decisions/generate", tags=["Decisions"])
async def generate_decisions():
    """生成投资决策"""
    try:
        result = await decision_engine.execute_decision_cycle()
        return result
    except Exception as e:
        logger.error(f"生成决策失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/decisions/satellite", tags=["Decisions"])
async def get_satellite_selections(top_n: int = 2):
    """获取卫星ETF选择"""
    try:
        decisions = await decision_engine.select_satellite_etfs(top_n=top_n)
        
        return {
            "count": len(decisions),
            "decisions": [
                {
                    "code": d.code,
                    "name": d.name,
                    "target_weight": d.target_weight,
                    "reason": d.reason,
                    "metadata": d.metadata
                }
                for d in decisions
            ]
        }
    except Exception as e:
        logger.error(f"获取卫星ETF选择失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/summary", response_model=PortfolioSummaryResponse, tags=["Portfolio"])
async def get_portfolio_summary():
    """获取组合汇总"""
    try:
        summary = portfolio_manager.get_position_summary()
        
        return PortfolioSummaryResponse(
            overview=summary['overview'],
            allocation=summary['allocation'],
            top_positions=summary['top_positions'],
            last_update=summary['last_update']
        )
    except Exception as e:
        logger.error(f"获取组合汇总失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/positions", tags=["Portfolio"])
async def get_positions():
    """获取当前持仓"""
    try:
        positions = []
        for code, pos in portfolio_manager.positions.items():
            positions.append({
                "code": pos.code,
                "name": pos.name,
                "shares": pos.shares,
                "avg_cost": pos.avg_cost,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "weight": pos.weight,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "module": pos.module,
                "entry_date": pos.entry_date.isoformat(),
                "metadata": pos.metadata
            })
        
        return {
            "count": len(positions),
            "positions": positions,
            "last_update": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取持仓失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/update-prices", tags=["Portfolio"])
async def update_prices(request: PriceUpdateRequest):
    """更新持仓价格"""
    try:
        portfolio_manager.update_prices(request.prices)
        portfolio_manager.save_positions()
        
        return {
            "status": "success",
            "updated_count": len(request.prices),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"更新价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/rebalance", tags=["Portfolio"])
async def generate_rebalance_orders(request: RebalanceRequest):
    """生成再平衡订单"""
    try:
        orders = portfolio_manager.generate_rebalance_orders(threshold=request.threshold)
        
        result = {
            "count": len(orders),
            "orders": [
                {
                    "code": order.code,
                    "name": order.name,
                    "action": order.action,
                    "shares": order.shares,
                    "price": order.price,
                    "amount": order.amount,
                    "reason": order.reason,
                    "module": order.module,
                    "priority": order.priority
                }
                for order in orders
            ],
            "dry_run": request.dry_run,
            "timestamp": datetime.now().isoformat()
        }
        
        if not request.dry_run:
            # 实际执行再平衡（这里需要实现）
            pass
        
        return result
    except Exception as e:
        logger.error(f"生成再平衡订单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/dca", tags=["Portfolio"])
async def execute_dca(request: DCAExecuteRequest):
    """执行定投计划"""
    try:
        result = portfolio_manager.apply_dca_plan(request.week)
        return result
    except Exception as e:
        logger.error(f"执行定投失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/risks", tags=["Portfolio"])
async def check_risks():
    """检查风险警告"""
    try:
        warnings = portfolio_manager.check_risk_limits()
        
        return {
            "count": len(warnings),
            "warnings": warnings,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"检查风险失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/etfs", tags=["Data"])
async def get_etf_list(min_turnover: float = 50_000_000):
    """获取ETF列表"""
    try:
        etf_list = await datasource.get_etf_list()
        
        # 过滤
        filtered = etf_list[etf_list['turnover'] >= min_turnover]
        
        return {
            "count": len(filtered),
            "etfs": filtered.head(50).to_dict('records')
        }
    except Exception as e:
        logger.error(f"获取ETF列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/etf/{code}/price", tags=["Data"])
async def get_etf_price(code: str, days: int = 30):
    """获取ETF价格数据"""
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        price_data = await datasource.get_etf_price(code, start_date, end_date)
        
        return {
            "code": code,
            "days": days,
            "data": price_data.reset_index().to_dict('records')
        }
    except Exception as e:
        logger.error(f"获取ETF价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/etf/{code}/iopv", tags=["Data"])
async def get_etf_iopv(code: str):
    """获取ETF的IOPV数据"""
    try:
        iopv_data = await datasource.get_etf_iopv(code)
        return iopv_data
    except Exception as e:
        logger.error(f"获取IOPV数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/convertibles", tags=["Data"])
async def get_convertible_bonds():
    """获取可转债列表"""
    try:
        cb_list = await datasource.get_convertible_bonds()
        
        # 根据配置过滤
        config = portfolio_manager.config['cb_rules']
        filtered = cb_list[
            (cb_list['balance'] >= config['size_min']) &
            (cb_list['premium_rate'] <= config['premium_max'])
        ]
        
        return {
            "count": len(filtered),
            "bonds": filtered.head(50).to_dict('records')
        }
    except Exception as e:
        logger.error(f"获取可转债列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/orders/csv", tags=["Export"])
async def export_orders_csv():
    """导出订单为CSV"""
    try:
        orders = portfolio_manager.generate_rebalance_orders()
        
        # 创建CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['代码', '名称', '操作', '数量', '价格', '金额', '原因', '模块', '优先级'])
        
        # 写入数据
        for order in orders:
            writer.writerow([
                order.code,
                order.name,
                order.action,
                order.shares,
                order.price,
                order.amount,
                order.reason,
                order.module,
                order.priority
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    except Exception as e:
        logger.error(f"导出订单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/momentum/ranking", tags=["Momentum"])
async def get_momentum_ranking(top_n: int = 20):
    """获取动量排名"""
    try:
        # 获取ETF列表
        etf_list = await datasource.get_etf_list()
        
        # 计算动量
        momentum_calc = MomentumCalculator()
        scores = []
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        for _, etf in etf_list.head(30).iterrows():
            try:
                price_data = await datasource.get_etf_price(
                    etf['code'], start_date, end_date
                )
                
                if len(price_data) >= 200:
                    score = momentum_calc.score_etf_momentum(
                        etf['code'], etf['name'], price_data
                    )
                    if score:
                        scores.append(score)
            except:
                continue
        
        # 排名
        ranked = momentum_calc.rank_momentum_scores(scores)
        
        return {
            "count": len(ranked),
            "ranking": [
                {
                    "rank": s.rank,
                    "code": s.code,
                    "name": s.name,
                    "r3m": s.r3m,
                    "r6m": s.r6m,
                    "total_score": s.total_score,
                    "ma200_state": s.ma200_state,
                    "volume_ratio": s.volume_ratio
                }
                for s in ranked[:top_n]
            ]
        }
    except Exception as e:
        logger.error(f"获取动量排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )