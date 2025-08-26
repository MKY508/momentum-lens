"""可转债量化评分系统"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConvertibleBondScore:
    """可转债评分结果"""
    code: str
    name: str
    price: float
    premium_rate: float
    credit_rating: str
    size: float
    remaining_years: float
    turnover: float
    atr_ratio: float
    
    # 各项得分
    price_score: float
    premium_score: float
    credit_score: float
    size_score: float
    term_score: float
    liquidity_score: float
    volatility_score: float
    
    # 综合评分
    total_score: float
    grid_step: float
    warnings: List[str]
    
    # 排名
    rank: Optional[int] = None


class ConvertibleBondAnalyzer:
    """可转债分析器"""
    
    def __init__(self):
        self.rating_map = {
            'AAA': 1.0,
            'AA+': 0.9,
            'AA': 0.8,
            'AA-': 0.75,
            'A+': 0.7,
            'A': 0.6,
            'A-': 0.5,
            'BBB+': 0.4,
            'BBB': 0.3,
            'BBB-': 0.2
        }
        
        # 评分权重
        self.weights = {
            'price': 0.20,
            'premium': 0.25,
            'credit': 0.15,
            'size': 0.10,
            'term': 0.10,
            'liquidity': 0.10,
            'volatility': 0.10
        }
    
    def calculate_scores(self, cb_data: pd.DataFrame) -> List[ConvertibleBondScore]:
        """计算可转债评分"""
        scores = []
        
        for _, row in cb_data.iterrows():
            try:
                score = self._score_single_bond(row)
                scores.append(score)
            except Exception as e:
                logger.error(f"评分失败 {row.get('code', 'unknown')}: {e}")
                continue
        
        # 排序并设置排名
        scores.sort(key=lambda x: x.total_score, reverse=True)
        for i, score in enumerate(scores):
            score.rank = i + 1
        
        return scores
    
    def _score_single_bond(self, bond: pd.Series) -> ConvertibleBondScore:
        """单只债券评分"""
        warnings = []
        
        # 基础数据
        price = bond['price']
        premium_rate = bond['premium_rate']
        credit_rating = bond.get('credit_rating', 'A')
        size = bond.get('size', 1e9)
        remaining_years = bond.get('remaining_years', 3)
        turnover = bond.get('turnover', 0)
        atr20 = bond.get('atr20', price * 0.03)
        
        # 1. 低价性得分: min(1, 140/price)
        price_score = min(1.0, 140 / price) if price > 0 else 0
        
        # 2. 转股溢价得分: 1 - clip(premium, 0, 40)/40
        premium_score = 1 - np.clip(premium_rate, 0, 40) / 40
        
        # 3. 信用评级得分
        credit_score = self.rating_map.get(credit_rating, 0.5)
        if credit_rating not in self.rating_map:
            warnings.append(f"未知评级: {credit_rating}")
        
        # 4. 规模得分: log10(size)/log10(max_size)
        max_size = 1e11  # 1000亿
        size_score = np.log10(max(size, 1e6)) / np.log10(max_size)
        size_score = np.clip(size_score, 0, 1)
        
        # 5. 期限得分: 钟形分布，2.5-3.5年最优
        if 2.5 <= remaining_years <= 3.5:
            term_score = 1.0
        elif 1 <= remaining_years <= 5:
            term_score = 0.8 - abs(remaining_years - 3) * 0.2
        else:
            term_score = 0.3
            warnings.append(f"期限不理想: {remaining_years:.1f}年")
        
        # 6. 流动性得分: 基于成交额排名
        liquidity_score = min(1.0, turnover / 1e8) if turnover > 0 else 0
        
        # 7. 波动适配得分: 1 - |ATR20/price - 3%| / 3%
        atr_ratio = atr20 / price if price > 0 else 0.03
        volatility_score = max(0, 1 - abs(atr_ratio - 0.03) / 0.03)
        
        # 惩罚项检查
        if bond.get('forced_redeem', False):
            warnings.append("强赎在途")
            price_score *= 0.5
            premium_score *= 0.5
        
        if bond.get('negative_news', False):
            warnings.append("负面公告")
            credit_score *= 0.7
        
        if size < 5e8:
            warnings.append(f"规模过小: {size/1e8:.1f}亿")
            size_score *= 0.5
        
        if turnover < 1e7:
            warnings.append("流动性不足")
            liquidity_score *= 0.3
        
        # 计算综合得分
        total_score = (
            self.weights['price'] * price_score +
            self.weights['premium'] * premium_score +
            self.weights['credit'] * credit_score +
            self.weights['size'] * size_score +
            self.weights['term'] * term_score +
            self.weights['liquidity'] * liquidity_score +
            self.weights['volatility'] * volatility_score
        )
        
        # 计算网格步长: g% = clamp(2% + (ATR20/close - 2%)*1.5, 2%, 5%)
        grid_step = np.clip(0.02 + (atr_ratio - 0.02) * 1.5, 0.02, 0.05)
        
        return ConvertibleBondScore(
            code=bond['code'],
            name=bond.get('name', ''),
            price=price,
            premium_rate=premium_rate,
            credit_rating=credit_rating,
            size=size,
            remaining_years=remaining_years,
            turnover=turnover,
            atr_ratio=atr_ratio,
            price_score=price_score,
            premium_score=premium_score,
            credit_score=credit_score,
            size_score=size_score,
            term_score=term_score,
            liquidity_score=liquidity_score,
            volatility_score=volatility_score,
            total_score=total_score,
            grid_step=grid_step,
            warnings=warnings
        )
    
    def select_portfolio(self, scores: List[ConvertibleBondScore], 
                        max_bonds: int = 10,
                        min_score: float = 0.5) -> List[ConvertibleBondScore]:
        """选择可转债组合"""
        # 过滤低分债券
        candidates = [s for s in scores if s.total_score >= min_score and not s.warnings]
        
        # 如果优质标的不足，适当放宽标准
        if len(candidates) < max_bonds // 2:
            candidates = [s for s in scores if s.total_score >= min_score * 0.8]
        
        # 行业/发行人去重（简化版：按名称前缀）
        selected = []
        issuers = set()
        
        for score in candidates[:20]:  # 从Top20中选
            issuer_prefix = score.name[:2] if score.name else score.code[:4]
            if issuer_prefix not in issuers:
                selected.append(score)
                issuers.add(issuer_prefix)
                if len(selected) >= max_bonds:
                    break
        
        return selected
    
    def generate_grid_orders(self, bond: ConvertibleBondScore, 
                           base_price: Optional[float] = None,
                           shares_per_order: int = 10) -> Dict:
        """生成网格订单"""
        if base_price is None:
            base_price = bond.price
        
        grid_step = bond.grid_step
        
        # 生成买卖价格队列
        buy_prices = []
        sell_prices = []
        
        # 向下5档买入
        for i in range(1, 6):
            buy_price = base_price * (1 - grid_step * i)
            buy_prices.append(round(buy_price, 2))
        
        # 向上5档卖出
        for i in range(1, 6):
            sell_price = base_price * (1 + grid_step * i)
            sell_prices.append(round(sell_price, 2))
        
        return {
            'code': bond.code,
            'name': bond.name,
            'base_price': base_price,
            'grid_step_pct': grid_step * 100,
            'buy_orders': [
                {
                    'price': price,
                    'shares': shares_per_order,
                    'type': 'grid_buy',
                    'trigger': f'价格≤{price}'
                }
                for price in buy_prices
            ],
            'sell_orders': [
                {
                    'price': price,
                    'shares': shares_per_order,
                    'type': 'grid_sell',
                    'trigger': f'价格≥{price}'
                }
                for price in sell_prices
            ],
            'warnings': bond.warnings
        }