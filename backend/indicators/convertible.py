"""
Convertible bond scoring system
可转债评分系统
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger


class ConvertibleScorer:
    """
    可转债评分器
    基于溢价率、波动率、YTM、流动性、信用评级等因素进行评分
    """
    
    def __init__(self, 
                 premium_weight: float = 0.3,
                 volatility_weight: float = 0.2,
                 ytm_weight: float = 0.2,
                 liquidity_weight: float = 0.15,
                 credit_weight: float = 0.15):
        """
        初始化可转债评分器
        
        Args:
            premium_weight: 溢价率权重
            volatility_weight: 波动率权重
            ytm_weight: 到期收益率权重
            liquidity_weight: 流动性权重
            credit_weight: 信用评级权重
        """
        self.premium_weight = premium_weight
        self.volatility_weight = volatility_weight
        self.ytm_weight = ytm_weight
        self.liquidity_weight = liquidity_weight
        self.credit_weight = credit_weight
        
        # 验证权重和为1
        total_weight = (premium_weight + volatility_weight + ytm_weight + 
                       liquidity_weight + credit_weight)
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, normalizing...")
            self.premium_weight /= total_weight
            self.volatility_weight /= total_weight
            self.ytm_weight /= total_weight
            self.liquidity_weight /= total_weight
            self.credit_weight /= total_weight
            
    def score_convertible_bond(self, bond_data: Dict[str, any]) -> Dict[str, any]:
        """
        对单个可转债进行评分
        
        Args:
            bond_data: 可转债数据字典
            
        Returns:
            评分结果字典
        """
        try:
            # 提取数据
            premium_rate = bond_data.get('premium_rate', 0)
            volatility = bond_data.get('volatility', 0)
            ytm = bond_data.get('ytm', 0)
            daily_volume = bond_data.get('daily_volume', 0)
            credit_rating = bond_data.get('credit_rating', 'BBB')
            
            # 计算各项得分
            premium_score = self._score_premium_rate(premium_rate)
            volatility_score = self._score_volatility(volatility)
            ytm_score = self._score_ytm(ytm)
            liquidity_score = self._score_liquidity(daily_volume)
            credit_score = self._score_credit_rating(credit_rating)
            
            # 计算综合得分
            total_score = (
                self.premium_weight * premium_score +
                self.volatility_weight * volatility_score +
                self.ytm_weight * ytm_score +
                self.liquidity_weight * liquidity_score +
                self.credit_weight * credit_score
            )
            
            # 判断评级
            rating = self._get_rating(total_score)
            
            result = {
                'code': bond_data.get('code', ''),
                'name': bond_data.get('name', ''),
                'total_score': round(total_score, 2),
                'rating': rating,
                'premium_score': round(premium_score, 2),
                'volatility_score': round(volatility_score, 2),
                'ytm_score': round(ytm_score, 2),
                'liquidity_score': round(liquidity_score, 2),
                'credit_score': round(credit_score, 2),
                'recommendation': self._get_recommendation(total_score, premium_rate, volatility)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error scoring convertible bond: {str(e)}")
            return {
                'code': bond_data.get('code', ''),
                'name': bond_data.get('name', ''),
                'total_score': 0,
                'rating': 'N/A',
                'recommendation': '数据不足，无法评分'
            }
            
    def rank_convertible_bonds(self, bonds_data: List[Dict[str, any]]) -> pd.DataFrame:
        """
        对多个可转债进行评分和排名
        
        Args:
            bonds_data: 可转债数据列表
            
        Returns:
            排名后的DataFrame
        """
        try:
            scores = []
            
            for bond_data in bonds_data:
                score_result = self.score_convertible_bond(bond_data)
                scores.append(score_result)
                
            # 创建DataFrame
            df_scores = pd.DataFrame(scores)
            
            if df_scores.empty:
                return df_scores
                
            # 按总分排序
            df_scores = df_scores.sort_values('total_score', ascending=False)
            
            # 添加排名
            df_scores['rank'] = range(1, len(df_scores) + 1)
            
            logger.info(f"Ranked {len(df_scores)} convertible bonds")
            return df_scores
            
        except Exception as e:
            logger.error(f"Error ranking convertible bonds: {str(e)}")
            return pd.DataFrame()
            
    def calculate_grid_step(self, bond_data: Dict[str, any], 
                          base_step: float = 0.02,
                          atr_multiplier: float = 1.5,
                          min_step: float = 0.02,
                          max_step: float = 0.05) -> float:
        """
        计算网格交易步长
        公式: g = clamp(base_step + atr_multiplier*(ATR10/close - 2%), min_step, max_step)
        
        Args:
            bond_data: 可转债数据
            base_step: 基础步长
            atr_multiplier: ATR倍数
            min_step: 最小步长
            max_step: 最大步长
            
        Returns:
            网格步长
        """
        try:
            atr10 = bond_data.get('atr10', 0)
            close_price = bond_data.get('close', 100)
            
            if close_price == 0:
                return base_step
                
            # 计算ATR占价格的比例
            atr_ratio = atr10 / close_price
            
            # 计算动态步长
            dynamic_step = base_step + atr_multiplier * (atr_ratio - 0.02)
            
            # 限制在最小和最大步长之间
            grid_step = max(min_step, min(dynamic_step, max_step))
            
            return grid_step
            
        except Exception as e:
            logger.error(f"Error calculating grid step: {str(e)}")
            return base_step
            
    def _score_premium_rate(self, premium_rate: float) -> float:
        """
        溢价率评分
        溢价率越低越好
        """
        if premium_rate < 0:  # 折价
            return 100
        elif premium_rate < 5:
            return 90
        elif premium_rate < 10:
            return 80
        elif premium_rate < 15:
            return 70
        elif premium_rate < 20:
            return 60
        elif premium_rate < 30:
            return 40
        else:
            return 20
            
    def _score_volatility(self, volatility: float) -> float:
        """
        波动率评分
        适中的波动率最好（太低没机会，太高风险大）
        """
        if volatility < 10:  # 波动率太低
            return 40
        elif volatility < 20:
            return 60
        elif volatility < 30:  # 最佳区间
            return 90
        elif volatility < 40:
            return 70
        elif volatility < 50:
            return 50
        else:  # 波动率太高
            return 30
            
    def _score_ytm(self, ytm: float) -> float:
        """
        到期收益率评分
        YTM越高越好
        """
        if ytm < -5:
            return 20
        elif ytm < 0:
            return 40
        elif ytm < 2:
            return 60
        elif ytm < 4:
            return 80
        elif ytm < 6:
            return 90
        else:
            return 100
            
    def _score_liquidity(self, daily_volume: float) -> float:
        """
        流动性评分
        日成交额（万元）
        """
        if daily_volume < 100:  # 小于100万
            return 20
        elif daily_volume < 500:
            return 40
        elif daily_volume < 1000:
            return 60
        elif daily_volume < 5000:
            return 80
        elif daily_volume < 10000:
            return 90
        else:  # 大于1亿
            return 100
            
    def _score_credit_rating(self, rating: str) -> float:
        """
        信用评级评分
        """
        rating_scores = {
            'AAA': 100,
            'AA+': 90,
            'AA': 80,
            'AA-': 70,
            'A+': 60,
            'A': 50,
            'A-': 40,
            'BBB+': 30,
            'BBB': 20,
            'BBB-': 10
        }
        
        return rating_scores.get(rating.upper(), 50)
        
    def _get_rating(self, score: float) -> str:
        """
        根据得分获取评级
        """
        if score >= 85:
            return 'A+'
        elif score >= 75:
            return 'A'
        elif score >= 65:
            return 'B+'
        elif score >= 55:
            return 'B'
        elif score >= 45:
            return 'C+'
        elif score >= 35:
            return 'C'
        else:
            return 'D'
            
    def _get_recommendation(self, score: float, premium_rate: float, volatility: float) -> str:
        """
        生成投资建议
        """
        if score >= 75:
            if premium_rate < 10:
                return "强烈推荐：低溢价高评分，适合网格交易"
            else:
                return "推荐：高评分，但需注意溢价率"
        elif score >= 55:
            if volatility > 30:
                return "谨慎推荐：评分中等，波动较大，控制仓位"
            else:
                return "中性：可适度参与网格交易"
        else:
            return "不推荐：评分较低，建议观望"