"""决策引擎模块 - 核心决策逻辑"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import yaml
from pathlib import Path

from indicators.momentum import (
    MomentumCalculator, MomentumScore, MomentumFilter, MarketState
)
from data.datasource import DataSourceFactory

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REBALANCE = "rebalance"
    SWITCH = "switch"  # 换腿


class ModuleType(Enum):
    """模块类型"""
    CORE = "core"
    SATELLITE = "satellite"
    CONVERTIBLE = "convertible"


@dataclass
class Decision:
    """决策数据类"""
    timestamp: datetime
    module: ModuleType
    signal: SignalType
    code: str
    name: str
    target_weight: float
    current_weight: float
    action_amount: float
    reason: str
    priority: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketEnvironment:
    """市场环境数据类"""
    state: MarketState
    ma200_ratio: float
    atr20: float
    chop: float
    vix_level: str  # low, medium, high
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class DecisionEngine:
    """决策引擎"""
    
    def __init__(self, config_path: str = "../config/config.yaml"):
        """
        初始化决策引擎
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.datasource = DataSourceFactory.get_datasource(
            self.config['data_source']['provider']
        )
        self.momentum_calc = MomentumCalculator()
        self.positions = {}
        self.market_env = None
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    async def analyze_market_environment(self) -> MarketEnvironment:
        """
        分析市场环境
        
        Returns:
            市场环境对象
        """
        try:
            # 获取沪深300指数数据
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
            index_data = await self.datasource.get_index_data(
                "sh000300", start_date, end_date
            )
            
            # 识别市场状态
            market_state = self.momentum_calc.identify_market_state(index_data)
            
            # 计算MA200比率
            ma200, ma200_state = self.momentum_calc.calculate_ma200(index_data['close'])
            current_price = index_data['close'].iloc[-1]
            current_ma200 = ma200.iloc[-1] if not ma200.empty else current_price
            ma200_ratio = current_price / current_ma200 if current_ma200 != 0 else 1
            
            # 计算ATR和CHOP
            atr20 = self.momentum_calc.calculate_atr20(
                index_data['high'], index_data['low'], index_data['close']
            )
            chop = self.momentum_calc.calculate_chop(
                index_data['high'], index_data['low'], index_data['close']
            )
            
            current_atr = atr20.iloc[-1] if not atr20.empty else 0
            current_chop = chop.iloc[-1] if not chop.empty else 50
            
            # 判断VIX级别（这里用ATR模拟）
            if current_atr < 0.01:
                vix_level = "low"
            elif current_atr < 0.02:
                vix_level = "medium"
            else:
                vix_level = "high"
            
            self.market_env = MarketEnvironment(
                state=market_state,
                ma200_ratio=ma200_ratio,
                atr20=current_atr,
                chop=current_chop,
                vix_level=vix_level,
                timestamp=datetime.now(),
                metadata={
                    'ma200_state': ma200_state,
                    'index_close': current_price
                }
            )
            
            logger.info(f"市场环境分析完成: {market_state.value}, MA200比率: {ma200_ratio:.2f}")
            return self.market_env
            
        except Exception as e:
            logger.error(f"市场环境分析失败: {e}")
            raise
    
    async def select_satellite_etfs(self, top_n: int = 2) -> List[Decision]:
        """
        选择卫星ETF
        
        Args:
            top_n: 选择前N个ETF
            
        Returns:
            决策列表
        """
        try:
            # 获取ETF列表
            etf_list = await self.datasource.get_etf_list()
            
            # 过滤行业和主题ETF（这里需要根据实际情况调整过滤条件）
            sector_etfs = etf_list[
                (etf_list['turnover'] > self.config['satellite_rules']['min_turnover']) &
                (etf_list['name'].str.contains('ETF'))
            ]
            
            # 计算动量评分
            scores = []
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
            for _, etf in sector_etfs.head(20).iterrows():  # 限制数量避免请求过多
                try:
                    # 获取历史数据
                    price_data = await self.datasource.get_etf_price(
                        etf['code'], start_date, end_date
                    )
                    
                    if len(price_data) >= 200:
                        # 计算动量评分
                        score = self.momentum_calc.score_etf_momentum(
                            etf['code'], 
                            etf['name'], 
                            price_data,
                            self.config['satellite_rules']['momentum_weights']['r3m'],
                            self.config['satellite_rules']['momentum_weights']['r6m']
                        )
                        
                        if score is not None:
                            scores.append(score)
                    
                except Exception as e:
                    logger.warning(f"处理ETF {etf['code']} 失败: {e}")
                    continue
            
            # 排名
            ranked_scores = self.momentum_calc.rank_momentum_scores(scores)
            
            # 过滤
            filtered_scores = MomentumFilter.filter_by_turnover(
                ranked_scores, etf_list, self.config['satellite_rules']['min_turnover']
            )
            
            # 生成决策
            decisions = []
            satellite_weight = self.config['satellite_target'] / min(top_n, len(filtered_scores))
            
            for score in filtered_scores[:top_n]:
                decision = Decision(
                    timestamp=datetime.now(),
                    module=ModuleType.SATELLITE,
                    signal=SignalType.BUY,
                    code=score.code,
                    name=score.name,
                    target_weight=satellite_weight,
                    current_weight=0,  # 需要从持仓中获取
                    action_amount=0,   # 需要计算
                    reason=f"动量得分: {score.total_score:.2f}, 排名: {score.rank}",
                    priority=score.rank,
                    metadata={
                        'momentum_score': score.total_score,
                        'r3m': score.r3m,
                        'r6m': score.r6m,
                        'ma200_state': score.ma200_state
                    }
                )
                decisions.append(decision)
            
            logger.info(f"选择了{len(decisions)}个卫星ETF")
            return decisions
            
        except Exception as e:
            logger.error(f"选择卫星ETF失败: {e}")
            raise
    
    async def generate_core_decisions(self) -> List[Decision]:
        """
        生成Core模块决策
        
        Returns:
            Core模块决策列表
        """
        try:
            decisions = []
            
            # Core配置
            core_config = self.config['core_target']
            
            # 根据市场环境调整权重
            if self.market_env is None:
                await self.analyze_market_environment()
            
            # 市场环境调整逻辑
            adjusted_weights = self._adjust_core_weights(core_config, self.market_env)
            
            # 生成每个Core资产的决策
            core_etfs = {
                'broad': {'codes': ['510300', '159919'], 'name': '宽基'},
                'dividend': {'codes': ['510880'], 'name': '红利'},
                'bond_cash': {'codes': ['511990'], 'name': '短债'},
                'gold': {'codes': ['518880'], 'name': '黄金'},
                'sp500': {'codes': ['513500'], 'name': '标普500'}
            }
            
            for module, info in core_etfs.items():
                weight = adjusted_weights.get(module, 0)
                if weight > 0:
                    # 选择具体的ETF（这里简化为选择第一个）
                    code = info['codes'][0]
                    
                    decision = Decision(
                        timestamp=datetime.now(),
                        module=ModuleType.CORE,
                        signal=SignalType.BUY,
                        code=code,
                        name=info['name'],
                        target_weight=weight,
                        current_weight=0,  # 需要从持仓中获取
                        action_amount=0,   # 需要计算
                        reason=f"Core配置: {module}",
                        priority=1,
                        metadata={
                            'module': module,
                            'market_state': self.market_env.state.value
                        }
                    )
                    decisions.append(decision)
            
            logger.info(f"生成了{len(decisions)}个Core决策")
            return decisions
            
        except Exception as e:
            logger.error(f"生成Core决策失败: {e}")
            raise
    
    def _adjust_core_weights(self, base_weights: Dict[str, float], 
                            market_env: MarketEnvironment) -> Dict[str, float]:
        """
        根据市场环境调整Core权重
        
        Args:
            base_weights: 基础权重配置
            market_env: 市场环境
            
        Returns:
            调整后的权重
        """
        adjusted = base_weights.copy()
        
        # 根据市场状态调整
        if market_env.state == MarketState.BEAR:
            # 熊市增加债券和黄金
            adjusted['bond_cash'] *= 1.2
            adjusted['gold'] *= 1.1
            adjusted['broad'] *= 0.8
            adjusted['sp500'] *= 0.9
            
        elif market_env.state == MarketState.BULL:
            # 牛市增加股票权重
            adjusted['broad'] *= 1.1
            adjusted['dividend'] *= 1.1
            adjusted['bond_cash'] *= 0.8
            
        elif market_env.state == MarketState.SIDEWAYS:
            # 震荡市保持平衡
            pass
        
        # 归一化权重
        total = sum(adjusted.values())
        if total > 0:
            for key in adjusted:
                adjusted[key] = adjusted[key] / total * sum(base_weights.values())
        
        return adjusted
    
    async def check_switch_signals(self, current_positions: Dict) -> List[Decision]:
        """
        检查换腿信号
        
        Args:
            current_positions: 当前持仓
            
        Returns:
            换腿决策列表
        """
        decisions = []
        
        try:
            # 获取当前卫星持仓
            satellite_positions = {
                k: v for k, v in current_positions.items() 
                if v.get('module') == 'satellite'
            }
            
            if not satellite_positions:
                return decisions
            
            # 重新计算所有卫星ETF的动量
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
            for code, position in satellite_positions.items():
                # 检查持有时间
                hold_days = (datetime.now() - position['entry_date']).days
                min_hold_days = self.config['satellite_rules']['min_hold_weeks'] * 7
                
                if hold_days < min_hold_days:
                    continue
                
                # 获取最新价格数据
                price_data = await self.datasource.get_etf_price(
                    code, start_date, end_date
                )
                
                # 计算当前动量
                current_momentum = self.momentum_calc.calculate_dual_momentum(
                    price_data['close']
                )
                
                # 检查止损
                current_return = (price_data['close'].iloc[-1] - position['avg_cost']) / position['avg_cost']
                if current_return < self.config['satellite_rules']['stop_loss']:
                    decision = Decision(
                        timestamp=datetime.now(),
                        module=ModuleType.SATELLITE,
                        signal=SignalType.SELL,
                        code=code,
                        name=position['name'],
                        target_weight=0,
                        current_weight=position['weight'],
                        action_amount=-position['shares'],
                        reason=f"触发止损: {current_return:.2%}",
                        priority=1,
                        metadata={'stop_loss': True}
                    )
                    decisions.append(decision)
                
                # 检查动量衰减
                elif current_momentum['dual_score'] < position['momentum_score'] * (1 - self.config['satellite_rules']['buffer_pct']):
                    decision = Decision(
                        timestamp=datetime.now(),
                        module=ModuleType.SATELLITE,
                        signal=SignalType.SWITCH,
                        code=code,
                        name=position['name'],
                        target_weight=0,
                        current_weight=position['weight'],
                        action_amount=-position['shares'],
                        reason=f"动量衰减: {current_momentum['dual_score']:.2f} < {position['momentum_score']:.2f}",
                        priority=2,
                        metadata={'momentum_decay': True}
                    )
                    decisions.append(decision)
            
            return decisions
            
        except Exception as e:
            logger.error(f"检查换腿信号失败: {e}")
            return decisions
    
    async def generate_rebalance_decisions(self, current_positions: Dict, 
                                          target_allocation: Dict) -> List[Decision]:
        """
        生成再平衡决策
        
        Args:
            current_positions: 当前持仓
            target_allocation: 目标配置
            
        Returns:
            再平衡决策列表
        """
        decisions = []
        
        try:
            # 计算当前总市值
            total_value = sum(p.get('market_value', 0) for p in current_positions.values())
            
            # 对每个目标配置生成决策
            for code, target_weight in target_allocation.items():
                current_weight = 0
                if code in current_positions:
                    current_weight = current_positions[code]['market_value'] / total_value if total_value > 0 else 0
                
                # 计算权重差异
                weight_diff = target_weight - current_weight
                
                # 如果差异超过阈值，生成再平衡决策
                if abs(weight_diff) > 0.02:  # 2%的阈值
                    signal = SignalType.BUY if weight_diff > 0 else SignalType.SELL
                    
                    decision = Decision(
                        timestamp=datetime.now(),
                        module=ModuleType.CORE,  # 或根据实际情况判断
                        signal=signal,
                        code=code,
                        name=current_positions.get(code, {}).get('name', code),
                        target_weight=target_weight,
                        current_weight=current_weight,
                        action_amount=weight_diff * total_value,
                        reason=f"再平衡: {current_weight:.2%} -> {target_weight:.2%}",
                        priority=3,
                        metadata={'rebalance': True}
                    )
                    decisions.append(decision)
            
            return decisions
            
        except Exception as e:
            logger.error(f"生成再平衡决策失败: {e}")
            return decisions
    
    async def execute_decision_cycle(self) -> Dict[str, Any]:
        """
        执行完整的决策周期
        
        Returns:
            决策结果字典
        """
        try:
            # 1. 分析市场环境
            market_env = await self.analyze_market_environment()
            
            # 2. 生成Core决策
            core_decisions = await self.generate_core_decisions()
            
            # 3. 选择卫星ETF
            satellite_decisions = await self.select_satellite_etfs()
            
            # 4. 检查换腿信号（需要当前持仓）
            # switch_decisions = await self.check_switch_signals(self.positions)
            
            # 5. 合并所有决策
            all_decisions = core_decisions + satellite_decisions
            
            # 6. 按优先级排序
            all_decisions.sort(key=lambda x: x.priority)
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'market_environment': {
                    'state': market_env.state.value,
                    'ma200_ratio': market_env.ma200_ratio,
                    'atr20': market_env.atr20,
                    'chop': market_env.chop,
                    'vix_level': market_env.vix_level
                },
                'decisions': [
                    {
                        'module': d.module.value,
                        'signal': d.signal.value,
                        'code': d.code,
                        'name': d.name,
                        'target_weight': d.target_weight,
                        'reason': d.reason,
                        'priority': d.priority,
                        'metadata': d.metadata
                    }
                    for d in all_decisions
                ],
                'summary': {
                    'total_decisions': len(all_decisions),
                    'core_decisions': len(core_decisions),
                    'satellite_decisions': len(satellite_decisions),
                    'buy_signals': len([d for d in all_decisions if d.signal == SignalType.BUY]),
                    'sell_signals': len([d for d in all_decisions if d.signal == SignalType.SELL])
                }
            }
            
            logger.info(f"决策周期执行完成: {result['summary']}")
            return result
            
        except Exception as e:
            logger.error(f"执行决策周期失败: {e}")
            raise