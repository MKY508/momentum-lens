"""
Market Regime Assessment Module
市场状态评估模块 - 统一判断市场环境（趋势/震荡）
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from loguru import logger


class MarketRegimeAnalyzer:
    """市场状态分析器"""
    
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher
        self.hs300_code = '000300'  # 沪深300指数代码
        
    def assess_market_regime(self) -> Dict:
        """
        综合评估市场状态
        Returns:
            Dict containing:
            - regime: 'TREND' | 'CHOP' | 'BEAR'
            - trend_confirmed: bool (是否满足双腿条件)
            - chop_conditions: dict (3个CHOP条件的满足情况)
            - recommendations: list (操作建议)
        """
        result = {
            'regime': 'UNKNOWN',
            'trend_confirmed': False,
            'chop_conditions': {},
            'ma200_status': {},
            'recommendations': []
        }
        
        try:
            # 获取沪深300数据
            hs300_data = self._get_hs300_data()
            
            # 1. 判断MA200状态
            ma200_status = self._check_ma200_status(hs300_data)
            result['ma200_status'] = ma200_status
            
            # 2. 判断趋势确认（双腿条件）
            result['trend_confirmed'] = self._check_trend_confirmation(
                hs300_data, ma200_status
            )
            
            # 3. 判断CHOP条件
            chop_conditions = self._check_chop_conditions(hs300_data, ma200_status)
            result['chop_conditions'] = chop_conditions
            
            # 4. 综合判断市场状态
            chop_count = sum(chop_conditions.values())
            
            if ma200_status['above_ma200'] and result['trend_confirmed']:
                result['regime'] = 'TREND'
                result['recommendations'].append('趋势模式：可启用双腿策略')
            elif chop_count >= 2:
                result['regime'] = 'CHOP'
                result['recommendations'].append('震荡模式：降低仓位，单腿操作')
                result['recommendations'].append('调整参数：止损-15%，缓冲4%，最短持有4周')
            elif not ma200_status['above_ma200']:
                result['regime'] = 'BEAR'
                result['recommendations'].append('熊市模式：谨慎操作或空仓观望')
            else:
                result['regime'] = 'NEUTRAL'
                result['recommendations'].append('中性模式：单腿操作，标准参数')
                
        except Exception as e:
            logger.error(f"Market regime assessment failed: {e}")
            result['error'] = str(e)
            
        return result
    
    def _get_hs300_data(self, days: int = 250) -> pd.DataFrame:
        """获取沪深300历史数据"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 这里调用data_fetcher获取数据
        # 实际实现需要连接数据源
        data = self.data_fetcher.get_index_history(
            self.hs300_code, 
            start_date, 
            end_date
        )
        
        # 计算技术指标
        data['MA200'] = data['close'].rolling(window=200).mean()
        data['ATR20'] = self._calculate_atr(data, period=20)
        
        return data
    
    def _check_ma200_status(self, data: pd.DataFrame) -> Dict:
        """检查MA200状态"""
        recent_data = data.tail(5)
        current_price = recent_data['close'].iloc[-1]
        ma200 = recent_data['MA200'].iloc[-1]
        
        # MA200斜率（5日）
        ma200_slope = (ma200 - data['MA200'].iloc[-6]) / data['MA200'].iloc[-6] * 100
        
        return {
            'current_price': current_price,
            'ma200': ma200,
            'above_ma200': current_price > ma200,
            'distance_pct': (current_price - ma200) / ma200 * 100,
            'ma200_slope': ma200_slope,
            'ma200_flat': abs(ma200_slope) <= 0.5  # ±0.5%视为走平
        }
    
    def _check_trend_confirmation(self, 
                                 data: pd.DataFrame, 
                                 ma200_status: Dict) -> bool:
        """
        检查趋势确认（双腿启用条件）
        - 沪深300连续5日收盘价高于MA200
        - 最后一日涨幅≥1%
        - 三日内回落检查
        """
        recent_5d = data.tail(5)
        
        # 条件1：连续5日在MA200上方
        all_above = all(recent_5d['close'] > recent_5d['MA200'])
        
        # 条件2：最后一日相对MA200涨幅≥1%
        last_day_gain = ma200_status['distance_pct'] >= 1.0
        
        # 条件3：检查是否有回落信号（用于退出双腿）
        # 如果之前是双腿模式，检查3日内是否跌破MA200超过1%
        recent_3d = data.tail(3)
        has_breakdown = any(
            (recent_3d['close'] < recent_3d['MA200'] * 0.99).values
        )
        
        trend_confirmed = all_above and last_day_gain and not has_breakdown
        
        return trend_confirmed
    
    def _check_chop_conditions(self, 
                              data: pd.DataFrame,
                              ma200_status: Dict) -> Dict:
        """
        检查CHOP震荡条件（3选2）
        a) 近30日在MA200±3%带内天数≥10
        b) ATR20/价≥3.5% 且 MA200走平
        c) 动量差距收窄：Top1-Top3<3% 且 Top1-Top5<8%
        """
        conditions = {
            'band_days': False,
            'high_atr_flat_ma': False,
            'momentum_convergence': False
        }
        
        recent_30d = data.tail(30)
        
        # 条件a：带内天数
        ma200_band_upper = recent_30d['MA200'] * 1.03
        ma200_band_lower = recent_30d['MA200'] * 0.97
        days_in_band = sum(
            (recent_30d['close'] <= ma200_band_upper) & 
            (recent_30d['close'] >= ma200_band_lower)
        )
        conditions['band_days'] = days_in_band >= 10
        
        # 条件b：高ATR且MA200走平
        current_atr = data['ATR20'].iloc[-1]
        current_price = data['close'].iloc[-1]
        atr_ratio = (current_atr / current_price) * 100
        
        conditions['high_atr_flat_ma'] = (
            atr_ratio >= 3.5 and ma200_status['ma200_flat']
        )
        
        # 条件c：动量差距收窄
        # 需要获取当前动量排名前5的ETF
        momentum_scores = self._get_top_momentum_scores(5)
        if len(momentum_scores) >= 5:
            top1 = momentum_scores[0]
            top3 = momentum_scores[2] if len(momentum_scores) > 2 else 0
            top5 = momentum_scores[4] if len(momentum_scores) > 4 else 0
            
            conditions['momentum_convergence'] = (
                (top1 - top3) < 3 and (top1 - top5) < 8
            )
        
        return conditions
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算ATR（Average True Range）"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # True Range计算
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR是TR的移动平均
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def _get_top_momentum_scores(self, n: int = 5) -> List[float]:
        """
        获取动量排名前N的分数
        这里需要调用decision_engine的功能
        """
        # 暂时返回模拟数据
        # 实际应该从decision_engine获取
        return [15.2, 14.8, 13.5, 12.1, 10.3]
    
    def check_reversion_signal(self, days_since_confirmation: int = 3) -> bool:
        """
        检查是否需要从双腿回到单腿
        - 确认双腿后3日内跌破MA200超过1%
        """
        data = self._get_hs300_data(days=days_since_confirmation + 5)
        recent_data = data.tail(days_since_confirmation)
        
        for _, row in recent_data.iterrows():
            if row['close'] < row['MA200'] * 0.99:
                return True
        
        return False