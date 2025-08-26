"""
Market environment analysis
市场环境分析
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger

from .technical import TechnicalIndicators


class MarketEnvironment:
    """
    市场环境分析类
    判断市场的解锁/回落状态、趋势强度等
    """
    
    def __init__(self):
        self.tech = TechnicalIndicators()
        
    def analyze_market_state(self, df: pd.DataFrame, 
                            ma_window: int = 200) -> Dict[str, any]:
        """
        分析市场状态
        
        Args:
            df: 价格数据DataFrame (需要包含date, close, high, low等列)
            ma_window: MA窗口期，默认200
            
        Returns:
            包含市场状态信息的字典
        """
        try:
            if df.empty:
                return self._empty_state()
                
            # 确保数据按日期排序
            df = df.sort_values('date').copy()
            
            # 计算MA200
            df['ma200'] = self.tech.calculate_ma(df['close'], ma_window)
            
            # 计算ATR20
            df['atr20'] = self.tech.calculate_atr(df, window=20)
            
            # 计算CHOP
            df['chop'] = self.tech.calculate_chop(df, window=14)
            
            # 获取最新值
            latest = df.iloc[-1]
            current_price = latest['close']
            ma200 = latest['ma200']
            atr20 = latest['atr20']
            chop = latest['chop']
            
            # 判断价格相对MA200的位置
            above_ma200 = current_price > ma200
            ma200_distance = (current_price - ma200) / ma200 * 100  # 百分比距离
            
            # 判断解锁/回落状态
            unlock_state, unlock_days = self._check_unlock_state(df, ma_window)
            fallback_state, fallback_days = self._check_fallback_state(df, ma_window)
            
            # 判断趋势强度
            trend_strength = self._calculate_trend_strength(df)
            
            # 判断市场环境
            market_env = self._determine_market_environment(
                above_ma200, unlock_state, fallback_state, chop, trend_strength
            )
            
            result = {
                'timestamp': datetime.now(),
                'current_price': current_price,
                'ma200': ma200,
                'above_ma200': above_ma200,
                'ma200_distance': ma200_distance,
                'atr20': atr20,
                'atr_ratio': atr20 / current_price * 100,  # ATR占价格比例
                'chop': chop,
                'unlock_state': unlock_state,
                'unlock_days': unlock_days,
                'fallback_state': fallback_state,
                'fallback_days': fallback_days,
                'trend_strength': trend_strength,
                'market_environment': market_env,
                'data_points': len(df)
            }
            
            logger.info(f"Market environment analysis completed: {market_env}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing market state: {str(e)}")
            return self._empty_state()
            
    def _check_unlock_state(self, df: pd.DataFrame, ma_window: int) -> Tuple[bool, int]:
        """
        检查解锁状态
        解锁：价格从MA下方突破到上方
        
        Returns:
            (是否处于解锁状态, 解锁天数)
        """
        try:
            if len(df) < ma_window:
                return False, 0
                
            # 计算价格与MA的关系
            df['above_ma'] = df['close'] > df['ma200']
            
            # 找到最近的突破点
            # 从后往前找第一个从下到上的突破
            for i in range(len(df) - 1, 0, -1):
                if df.iloc[i]['above_ma'] and not df.iloc[i-1]['above_ma']:
                    # 找到突破点
                    unlock_date = df.iloc[i]['date']
                    days_since_unlock = (df.iloc[-1]['date'] - unlock_date).days
                    
                    # 如果突破后一直在MA上方，则处于解锁状态
                    if all(df.iloc[i:]['above_ma']):
                        return True, days_since_unlock
                    else:
                        return False, 0
                        
            # 如果一直在MA上方
            if all(df['above_ma']):
                return True, len(df)
                
            return False, 0
            
        except Exception as e:
            logger.error(f"Error checking unlock state: {str(e)}")
            return False, 0
            
    def _check_fallback_state(self, df: pd.DataFrame, ma_window: int) -> Tuple[bool, int]:
        """
        检查回落状态
        回落：价格从MA上方跌破到下方
        
        Returns:
            (是否处于回落状态, 回落天数)
        """
        try:
            if len(df) < ma_window:
                return False, 0
                
            # 计算价格与MA的关系
            df['below_ma'] = df['close'] < df['ma200']
            
            # 找到最近的跌破点
            # 从后往前找第一个从上到下的跌破
            for i in range(len(df) - 1, 0, -1):
                if df.iloc[i]['below_ma'] and not df.iloc[i-1]['below_ma']:
                    # 找到跌破点
                    fallback_date = df.iloc[i]['date']
                    days_since_fallback = (df.iloc[-1]['date'] - fallback_date).days
                    
                    # 如果跌破后一直在MA下方，则处于回落状态
                    if all(df.iloc[i:]['below_ma']):
                        return True, days_since_fallback
                    else:
                        return False, 0
                        
            # 如果一直在MA下方
            if all(df['below_ma']):
                return True, len(df)
                
            return False, 0
            
        except Exception as e:
            logger.error(f"Error checking fallback state: {str(e)}")
            return False, 0
            
    def _calculate_trend_strength(self, df: pd.DataFrame, window: int = 20) -> str:
        """
        计算趋势强度
        
        Returns:
            趋势强度: 'strong_up', 'up', 'neutral', 'down', 'strong_down'
        """
        try:
            if len(df) < window:
                return 'neutral'
                
            # 计算最近N日的收益率
            recent_return = (df.iloc[-1]['close'] - df.iloc[-window]['close']) / df.iloc[-window]['close'] * 100
            
            # 计算RSI
            rsi = self.tech.calculate_rsi(df['close'], window=14).iloc[-1]
            
            # 根据收益率和RSI判断趋势强度
            if recent_return > 10 and rsi > 70:
                return 'strong_up'
            elif recent_return > 5 and rsi > 60:
                return 'up'
            elif recent_return < -10 and rsi < 30:
                return 'strong_down'
            elif recent_return < -5 and rsi < 40:
                return 'down'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.error(f"Error calculating trend strength: {str(e)}")
            return 'neutral'
            
    def _determine_market_environment(self, above_ma200: bool, unlock_state: bool,
                                     fallback_state: bool, chop: float,
                                     trend_strength: str) -> str:
        """
        判断市场环境
        
        Returns:
            市场环境: 'OFFENSE', 'DEFENSE', 'NEUTRAL'
        """
        # 进攻模式条件
        if above_ma200 and unlock_state and chop < 50 and trend_strength in ['up', 'strong_up']:
            return 'OFFENSE'
            
        # 防守模式条件
        if not above_ma200 and fallback_state and chop > 70:
            return 'DEFENSE'
            
        # 其他情况为中性
        return 'NEUTRAL'
        
    def _empty_state(self) -> Dict[str, any]:
        """返回空状态"""
        return {
            'timestamp': datetime.now(),
            'current_price': 0,
            'ma200': 0,
            'above_ma200': False,
            'ma200_distance': 0,
            'atr20': 0,
            'atr_ratio': 0,
            'chop': 50,
            'unlock_state': False,
            'unlock_days': 0,
            'fallback_state': False,
            'fallback_days': 0,
            'trend_strength': 'neutral',
            'market_environment': 'NEUTRAL',
            'data_points': 0
        }
        
    def get_market_signal(self, environment: str) -> Dict[str, any]:
        """
        根据市场环境获取交易信号
        
        Args:
            environment: 市场环境 ('OFFENSE', 'DEFENSE', 'NEUTRAL')
            
        Returns:
            交易信号字典
        """
        signals = {
            'OFFENSE': {
                'core_ratio': 0.3,
                'satellite_ratio': 0.7,
                'recommended_positions': 4,
                'risk_level': 'high',
                'strategy': '积极进攻，增加成长型ETF配置',
                'actions': [
                    '增加科技成长类ETF权重',
                    '减少防守型资产',
                    '考虑使用杠杆'
                ]
            },
            'DEFENSE': {
                'core_ratio': 0.7,
                'satellite_ratio': 0.3,
                'recommended_positions': 2,
                'risk_level': 'low',
                'strategy': '防守为主，增加稳健资产配置',
                'actions': [
                    '增加红利、银行等防守型ETF',
                    '减少成长型ETF',
                    '增加现金或债券比例'
                ]
            },
            'NEUTRAL': {
                'core_ratio': 0.5,
                'satellite_ratio': 0.5,
                'recommended_positions': 3,
                'risk_level': 'medium',
                'strategy': '均衡配置，灵活调整',
                'actions': [
                    '保持均衡配置',
                    '关注市场变化信号',
                    '适度调整仓位'
                ]
            }
        }
        
        return signals.get(environment, signals['NEUTRAL'])