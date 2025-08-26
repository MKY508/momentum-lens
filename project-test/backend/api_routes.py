"""API路由 - 提供真实数据接口"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/market/realtime")
async def get_realtime_market():
    """获取实时市场数据"""
    try:
        # 获取ETF实时行情
        etf_spot = ak.fund_etf_spot_em()
        
        # 获取Top10 ETF
        top_etfs = etf_spot.nlargest(10, '涨跌幅')[['代码', '名称', '最新价', '涨跌幅', '成交额']]
        
        # 获取主要ETF
        major_codes = ['510300', '510050', '159915', '518880', '510880']
        major_etfs = []
        
        for code in major_codes:
            etf = etf_spot[etf_spot['代码'].str.contains(code[-6:], na=False)]
            if not etf.empty:
                row = etf.iloc[0]
                major_etfs.append({
                    'code': code,
                    'name': row['名称'],
                    'price': float(row['最新价']),
                    'change': float(row['涨跌幅']),
                    'volume': float(row['成交额'])
                })
        
        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'top_gainers': top_etfs.to_dict('records'),
                'major_etfs': major_etfs,
                'total_count': len(etf_spot)
            }
        }
    except Exception as e:
        logger.error(f"获取实时市场数据失败: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'data': {
                'top_gainers': [],
                'major_etfs': [],
                'total_count': 0
            }
        }

@router.get("/api/etf/{code}/history")
async def get_etf_history(code: str, days: int = 30):
    """获取ETF历史数据"""
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        # 获取历史数据
        hist = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        # 转换为前端需要的格式
        data = []
        for _, row in hist.iterrows():
            data.append({
                'date': row['日期'],
                'open': float(row['开盘']),
                'high': float(row['最高']),
                'low': float(row['最低']),
                'close': float(row['收盘']),
                'volume': float(row['成交量']),
                'change': float(row['涨跌幅'])
            })
        
        # 计算动量指标
        hist['MA20'] = hist['收盘'].rolling(window=20).mean()
        hist['MA60'] = hist['收盘'].rolling(window=60).mean()
        
        current_price = float(hist['收盘'].iloc[-1])
        ma20 = float(hist['MA20'].iloc[-1]) if not pd.isna(hist['MA20'].iloc[-1]) else 0
        ma60 = float(hist['MA60'].iloc[-1]) if not pd.isna(hist['MA60'].iloc[-1]) else 0
        
        # 计算动量
        if len(hist) >= 20:
            momentum_1m = (current_price / float(hist['收盘'].iloc[-20]) - 1) * 100
        else:
            momentum_1m = 0
            
        return {
            'status': 'success',
            'code': code,
            'data': data,
            'indicators': {
                'current_price': current_price,
                'ma20': ma20,
                'ma60': ma60,
                'momentum_1m': momentum_1m
            }
        }
    except Exception as e:
        logger.error(f"获取ETF历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/momentum/ranking")
async def get_momentum_ranking():
    """获取动量排名"""
    try:
        # 热门ETF列表
        etf_codes = [
            ('510300', '沪深300ETF'),
            ('510050', '上证50ETF'),
            ('159915', '创业板ETF'),
            ('512660', '军工ETF'),
            ('512690', '酒ETF'),
            ('512010', '医药ETF'),
            ('515030', '新能源车ETF'),
            ('516160', '新能源ETF'),
            ('512880', '证券ETF'),
            ('159992', '创新药ETF')
        ]
        
        momentum_scores = []
        
        for code, name in etf_codes:
            try:
                # 获取60天历史数据
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=130)).strftime('%Y%m%d')
                
                hist = ak.fund_etf_hist_em(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                
                if len(hist) >= 60:
                    # 计算动量
                    current = float(hist['收盘'].iloc[-1])
                    price_20d = float(hist['收盘'].iloc[-20])
                    price_60d = float(hist['收盘'].iloc[-60])
                    
                    r1m = (current / price_20d - 1) * 100
                    r3m = (current / price_60d - 1) * 100
                    
                    # 综合得分
                    score = 0.6 * r3m + 0.4 * r1m
                    
                    momentum_scores.append({
                        'code': code,
                        'name': name,
                        'price': current,
                        'momentum_1m': round(r1m, 2),
                        'momentum_3m': round(r3m, 2),
                        'score': round(score, 2)
                    })
            except Exception as e:
                logger.warning(f"获取{code}动量失败: {e}")
                continue
        
        # 按得分排序
        momentum_scores.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'data': momentum_scores
        }
    except Exception as e:
        logger.error(f"获取动量排名失败: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'data': []
        }

@router.get("/api/index/hs300")
async def get_hs300_index():
    """获取沪深300指数数据"""
    try:
        # 获取沪深300指数
        index_data = ak.stock_zh_index_daily(symbol="sh000300")
        
        # 获取最近的数据
        recent = index_data.tail(30)
        
        # 计算MA200
        index_data['MA200'] = index_data['close'].rolling(window=200).mean()
        
        current_price = float(index_data['close'].iloc[-1])
        ma200 = float(index_data['MA200'].iloc[-1]) if not pd.isna(index_data['MA200'].iloc[-1]) else 0
        
        # 判断市场状态
        if ma200 > 0:
            ratio = current_price / ma200
            if ratio > 1.01:
                market_state = "BULLISH"
                state_text = "强势（站上年线）"
            elif ratio < 0.99:
                market_state = "BEARISH"
                state_text = "弱势（跌破年线）"
            else:
                market_state = "NEUTRAL"
                state_text = "震荡（年线附近）"
        else:
            market_state = "UNKNOWN"
            state_text = "数据不足"
            ratio = 0
        
        # 转换数据格式
        data = []
        for _, row in recent.iterrows():
            data.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })
        
        return {
            'status': 'success',
            'data': {
                'current': current_price,
                'ma200': ma200,
                'ratio': ratio,
                'market_state': market_state,
                'state_text': state_text,
                'history': data
            }
        }
    except Exception as e:
        logger.error(f"获取沪深300指数失败: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'data': None
        }

@router.get("/api/portfolio/suggestions")
async def get_portfolio_suggestions():
    """获取组合建议"""
    try:
        # 获取市场状态
        index_response = await get_hs300_index()
        market_state = index_response['data']['market_state'] if index_response['status'] == 'success' else 'UNKNOWN'
        
        # 获取动量排名
        momentum_response = await get_momentum_ranking()
        top_momentum = momentum_response['data'][:2] if momentum_response['status'] == 'success' else []
        
        # Core配置建议
        if market_state == "BULLISH":
            core_allocation = {
                '510300': {'name': '沪深300ETF', 'weight': 0.20, 'action': 'HOLD'},
                '510880': {'name': '红利ETF', 'weight': 0.10, 'action': 'BUY'},
                '511990': {'name': '华宝添益', 'weight': 0.15, 'action': 'HOLD'},
                '518880': {'name': '黄金ETF', 'weight': 0.10, 'action': 'REDUCE'},
                '513500': {'name': '标普500', 'weight': 0.05, 'action': 'HOLD'}
            }
            satellite_weight = 0.30
        else:
            core_allocation = {
                '510300': {'name': '沪深300ETF', 'weight': 0.15, 'action': 'REDUCE'},
                '510880': {'name': '红利ETF', 'weight': 0.15, 'action': 'BUY'},
                '511990': {'name': '华宝添益', 'weight': 0.20, 'action': 'BUY'},
                '518880': {'name': '黄金ETF', 'weight': 0.15, 'action': 'BUY'},
                '513500': {'name': '标普500', 'weight': 0.05, 'action': 'HOLD'}
            }
            satellite_weight = 0.20
        
        # 卫星建议
        satellite_suggestions = []
        for etf in top_momentum[:2]:
            satellite_suggestions.append({
                'code': etf['code'],
                'name': etf['name'],
                'score': etf['score'],
                'weight': satellite_weight / 2,
                'action': 'BUY' if etf['score'] > 5 else 'HOLD'
            })
        
        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'market_state': market_state,
            'suggestions': {
                'core': core_allocation,
                'satellite': satellite_suggestions,
                'cash': 0.10
            }
        }
    except Exception as e:
        logger.error(f"获取组合建议失败: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'suggestions': None
        }