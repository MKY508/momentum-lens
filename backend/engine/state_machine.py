"""
Market state machine implementation
市场状态机实现
"""
from enum import Enum
from typing import Dict, Optional, Tuple
from datetime import datetime
from loguru import logger


class MarketState(Enum):
    """市场状态枚举"""
    OFFENSE = "OFFENSE"    # 进攻模式
    NEUTRAL = "NEUTRAL"    # 中性模式
    DEFENSE = "DEFENSE"    # 防守模式


class StateMachine:
    """
    市场状态机
    根据市场环境动态切换策略状态
    """
    
    def __init__(self, initial_state: MarketState = MarketState.NEUTRAL):
        """
        初始化状态机
        
        Args:
            initial_state: 初始状态
        """
        self.current_state = initial_state
        self.previous_state = initial_state
        self.state_history = [(datetime.now(), initial_state)]
        self.transition_rules = self._init_transition_rules()
        
        logger.info(f"Initialized state machine with state: {initial_state.value}")
        
    def _init_transition_rules(self) -> Dict[MarketState, Dict[str, any]]:
        """
        初始化状态转换规则
        
        Returns:
            状态转换规则字典
        """
        return {
            MarketState.OFFENSE: {
                'to_neutral': {
                    'conditions': [
                        ('ma200_below', True),  # 价格跌破MA200
                        ('chop_high', True),     # CHOP > 60
                        ('momentum_weak', True)  # 动量转弱
                    ],
                    'required': 2  # 需要满足2个条件
                },
                'to_defense': {
                    'conditions': [
                        ('ma200_below', True),   # 价格跌破MA200
                        ('fallback_days', 5),    # 回落超过5天
                        ('chop_high', True),     # CHOP > 70
                        ('market_panic', True)   # 市场恐慌
                    ],
                    'required': 3  # 需要满足3个条件
                }
            },
            MarketState.NEUTRAL: {
                'to_offense': {
                    'conditions': [
                        ('ma200_above', True),   # 价格在MA200上方
                        ('unlock_days', 5),      # 解锁超过5天
                        ('chop_low', True),      # CHOP < 50
                        ('momentum_strong', True) # 动量强劲
                    ],
                    'required': 3
                },
                'to_defense': {
                    'conditions': [
                        ('ma200_below', True),   # 价格跌破MA200
                        ('fallback_days', 5),    # 回落超过5天
                        ('chop_high', True),     # CHOP > 70
                    ],
                    'required': 2
                }
            },
            MarketState.DEFENSE: {
                'to_neutral': {
                    'conditions': [
                        ('ma200_above', True),   # 价格回到MA200上方
                        ('chop_normal', True),   # CHOP正常化
                        ('momentum_recovery', True) # 动量恢复
                    ],
                    'required': 2
                },
                'to_offense': {
                    'conditions': [
                        ('ma200_above', True),   # 价格在MA200上方
                        ('unlock_days', 10),     # 解锁超过10天（更严格）
                        ('chop_low', True),      # CHOP < 40
                        ('momentum_strong', True), # 动量强劲
                        ('volume_surge', True)    # 成交量放大
                    ],
                    'required': 4  # 需要满足4个条件（从防守转进攻需要更多确认）
                }
            }
        }
        
    def update_state(self, market_conditions: Dict[str, any]) -> Tuple[MarketState, bool]:
        """
        根据市场条件更新状态
        
        Args:
            market_conditions: 市场条件字典
            
        Returns:
            (新状态, 是否发生转换)
        """
        try:
            # 评估当前市场条件
            evaluated_conditions = self._evaluate_conditions(market_conditions)
            
            # 检查是否需要状态转换
            new_state = self._check_transitions(evaluated_conditions)
            
            if new_state != self.current_state:
                # 状态发生转换
                self._transition_to(new_state)
                logger.info(f"State transition: {self.previous_state.value} -> {new_state.value}")
                return new_state, True
            else:
                return self.current_state, False
                
        except Exception as e:
            logger.error(f"Error updating state: {str(e)}")
            return self.current_state, False
            
    def _evaluate_conditions(self, market_conditions: Dict[str, any]) -> Dict[str, bool]:
        """
        评估市场条件
        
        Args:
            market_conditions: 市场条件字典
            
        Returns:
            评估结果字典
        """
        evaluated = {}
        
        # MA200相关
        evaluated['ma200_above'] = market_conditions.get('above_ma200', False)
        evaluated['ma200_below'] = not evaluated['ma200_above']
        
        # 解锁/回落状态
        evaluated['unlock_days'] = market_conditions.get('unlock_days', 0)
        evaluated['fallback_days'] = market_conditions.get('fallback_days', 0)
        
        # CHOP指标
        chop = market_conditions.get('chop', 50)
        evaluated['chop_low'] = chop < 50
        evaluated['chop_normal'] = 50 <= chop <= 70
        evaluated['chop_high'] = chop > 70
        
        # 动量强度
        trend_strength = market_conditions.get('trend_strength', 'neutral')
        evaluated['momentum_strong'] = trend_strength in ['up', 'strong_up']
        evaluated['momentum_weak'] = trend_strength in ['down', 'strong_down']
        evaluated['momentum_recovery'] = trend_strength in ['neutral', 'up']
        
        # 其他条件
        evaluated['volume_surge'] = market_conditions.get('volume_surge', False)
        evaluated['market_panic'] = market_conditions.get('vix_high', False)
        
        return evaluated
        
    def _check_transitions(self, evaluated_conditions: Dict[str, bool]) -> MarketState:
        """
        检查是否满足状态转换条件
        
        Args:
            evaluated_conditions: 评估后的条件字典
            
        Returns:
            新状态
        """
        current_rules = self.transition_rules.get(self.current_state, {})
        
        for target_state_name, rules in current_rules.items():
            conditions = rules['conditions']
            required = rules['required']
            
            # 计算满足的条件数
            satisfied = 0
            for condition_name, expected_value in conditions:
                actual_value = evaluated_conditions.get(condition_name)
                
                # 处理不同类型的条件
                if isinstance(expected_value, bool):
                    if actual_value == expected_value:
                        satisfied += 1
                elif isinstance(expected_value, (int, float)):
                    # 对于数值型条件，检查是否达到阈值
                    if condition_name in evaluated_conditions:
                        if evaluated_conditions[condition_name] >= expected_value:
                            satisfied += 1
                            
            # 检查是否满足转换条件
            if satisfied >= required:
                # 找到目标状态
                if 'offense' in target_state_name:
                    return MarketState.OFFENSE
                elif 'defense' in target_state_name:
                    return MarketState.DEFENSE
                elif 'neutral' in target_state_name:
                    return MarketState.NEUTRAL
                    
        return self.current_state
        
    def _transition_to(self, new_state: MarketState):
        """
        执行状态转换
        
        Args:
            new_state: 新状态
        """
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_history.append((datetime.now(), new_state))
        
        # 限制历史记录长度
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-100:]
            
    def get_state_config(self) -> Dict[str, any]:
        """
        获取当前状态的配置
        
        Returns:
            状态配置字典
        """
        configs = {
            MarketState.OFFENSE: {
                'core_ratio': 0.3,
                'satellite_ratio': 0.7,
                'max_positions': 4,
                'rebalance_frequency': 'monthly',
                'stop_loss': -0.08,
                'take_profit': 0.15,
                'position_sizing': 'equal_weight',
                'risk_level': 'high'
            },
            MarketState.NEUTRAL: {
                'core_ratio': 0.5,
                'satellite_ratio': 0.5,
                'max_positions': 3,
                'rebalance_frequency': 'quarterly',
                'stop_loss': -0.06,
                'take_profit': 0.12,
                'position_sizing': 'risk_parity',
                'risk_level': 'medium'
            },
            MarketState.DEFENSE: {
                'core_ratio': 0.7,
                'satellite_ratio': 0.3,
                'max_positions': 2,
                'rebalance_frequency': 'semi_annual',
                'stop_loss': -0.04,
                'take_profit': 0.08,
                'position_sizing': 'defensive',
                'risk_level': 'low'
            }
        }
        
        return configs.get(self.current_state, configs[MarketState.NEUTRAL])
        
    def get_state_history(self, days: Optional[int] = None) -> list:
        """
        获取状态历史
        
        Args:
            days: 获取最近N天的历史
            
        Returns:
            状态历史列表
        """
        if days is None:
            return self.state_history
            
        cutoff_date = datetime.now() - timedelta(days=days)
        return [(dt, state) for dt, state in self.state_history if dt >= cutoff_date]
        
    def reset(self, state: Optional[MarketState] = None):
        """
        重置状态机
        
        Args:
            state: 重置到的状态，默认为NEUTRAL
        """
        reset_state = state or MarketState.NEUTRAL
        self.current_state = reset_state
        self.previous_state = reset_state
        self.state_history = [(datetime.now(), reset_state)]
        logger.info(f"State machine reset to: {reset_state.value}")