"""
Rotation manager for portfolio rebalancing
轮动管理器，用于投资组合再平衡
"""
from typing import Dict, List, Tuple
from datetime import datetime
from loguru import logger


class RotationManager:
    """轮动管理器"""
    
    def __init__(self):
        self.last_rotation_date = None
        self.rotation_history = []
        
    def calculate_rotation(self, current_holdings: Dict[str, float],
                          target_holdings: Dict[str, float]) -> Dict[str, float]:
        """计算轮动交易"""
        trades = {}
        
        # 计算需要买入和卖出的数量
        all_codes = set(current_holdings.keys()) | set(target_holdings.keys())
        
        for code in all_codes:
            current = current_holdings.get(code, 0)
            target = target_holdings.get(code, 0)
            diff = target - current
            
            if abs(diff) > 0.01:  # 忽略小于1%的差异
                trades[code] = diff
                
        return trades