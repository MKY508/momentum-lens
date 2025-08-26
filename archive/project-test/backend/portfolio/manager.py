"""投资组合管理模块"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import yaml
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """持仓数据类"""
    code: str
    name: str
    shares: float
    avg_cost: float
    current_price: float
    market_value: float
    weight: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    module: str  # core, satellite, convertible
    entry_date: datetime
    last_update: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioStats:
    """组合统计数据类"""
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    core_weight: float
    satellite_weight: float
    convertible_weight: float
    cash_weight: float
    positions_count: int
    last_update: datetime


@dataclass
class RebalanceOrder:
    """再平衡订单"""
    code: str
    name: str
    action: str  # buy, sell
    shares: int
    price: float
    amount: float
    reason: str
    module: str
    priority: int


class PortfolioManager:
    """投资组合管理器"""
    
    def __init__(self, config_path: str = "../config/config.yaml", 
                 positions_path: str = "../config/positions.yaml"):
        """
        初始化组合管理器
        
        Args:
            config_path: 配置文件路径
            positions_path: 持仓文件路径
        """
        self.config = self._load_config(config_path)
        self.positions_path = positions_path
        self.positions = self._load_positions()
        self.capital = self.config['capital']
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_positions(self) -> Dict[str, Position]:
        """加载持仓数据"""
        positions = {}
        
        if Path(self.positions_path).exists():
            with open(self.positions_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 加载Core持仓
            for pos in data.get('core_positions', []):
                positions[pos['code']] = Position(
                    code=pos['code'],
                    name=pos['name'],
                    shares=pos['shares'],
                    avg_cost=pos['avg_cost'],
                    current_price=pos['avg_cost'],  # 需要更新
                    market_value=pos['shares'] * pos['avg_cost'],
                    weight=pos['weight'],
                    unrealized_pnl=0,
                    unrealized_pnl_pct=0,
                    module='core',
                    entry_date=datetime.now(),  # 需要从数据中获取
                    last_update=datetime.now(),
                    metadata={'sub_module': pos.get('module')}
                )
            
            # 加载卫星持仓
            for pos in data.get('satellite_positions', []):
                positions[pos['code']] = Position(
                    code=pos['code'],
                    name=pos['name'],
                    shares=pos['shares'],
                    avg_cost=pos['avg_cost'],
                    current_price=pos['avg_cost'],
                    market_value=pos['shares'] * pos['avg_cost'],
                    weight=pos['weight'],
                    unrealized_pnl=0,
                    unrealized_pnl_pct=0,
                    module='satellite',
                    entry_date=datetime.strptime(pos['entry_date'], "%Y-%m-%d"),
                    last_update=datetime.now(),
                    metadata={'momentum_score': pos.get('momentum_score')}
                )
            
            # 加载可转债持仓
            for pos in data.get('convertible_positions', []):
                positions[pos['code']] = Position(
                    code=pos['code'],
                    name=pos['name'],
                    shares=pos['shares'],
                    avg_cost=pos['avg_cost'],
                    current_price=pos['avg_cost'],
                    market_value=pos['shares'] * pos['avg_cost'],
                    weight=pos['weight'],
                    unrealized_pnl=0,
                    unrealized_pnl_pct=0,
                    module='convertible',
                    entry_date=datetime.now(),
                    last_update=datetime.now(),
                    metadata={
                        'conversion_price': pos.get('conversion_price'),
                        'premium_rate': pos.get('premium_rate')
                    }
                )
        
        return positions
    
    def save_positions(self):
        """保存持仓数据"""
        data = {
            'last_update': datetime.now().isoformat(),
            'core_positions': [],
            'satellite_positions': [],
            'convertible_positions': []
        }
        
        for code, pos in self.positions.items():
            pos_data = {
                'code': pos.code,
                'name': pos.name,
                'shares': pos.shares,
                'avg_cost': pos.avg_cost,
                'weight': pos.weight
            }
            
            if pos.module == 'core':
                pos_data['module'] = pos.metadata.get('sub_module', '')
                data['core_positions'].append(pos_data)
            elif pos.module == 'satellite':
                pos_data['entry_date'] = pos.entry_date.strftime("%Y-%m-%d")
                pos_data['momentum_score'] = pos.metadata.get('momentum_score', 0)
                data['satellite_positions'].append(pos_data)
            elif pos.module == 'convertible':
                pos_data['conversion_price'] = pos.metadata.get('conversion_price', 0)
                pos_data['premium_rate'] = pos.metadata.get('premium_rate', 0)
                data['convertible_positions'].append(pos_data)
        
        with open(self.positions_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    def update_prices(self, price_data: Dict[str, float]):
        """
        更新持仓价格
        
        Args:
            price_data: {代码: 价格}字典
        """
        total_value = 0
        
        for code, price in price_data.items():
            if code in self.positions:
                pos = self.positions[code]
                pos.current_price = price
                pos.market_value = pos.shares * price
                pos.unrealized_pnl = (price - pos.avg_cost) * pos.shares
                pos.unrealized_pnl_pct = (price - pos.avg_cost) / pos.avg_cost if pos.avg_cost > 0 else 0
                pos.last_update = datetime.now()
                total_value += pos.market_value
        
        # 更新权重
        if total_value > 0:
            for pos in self.positions.values():
                pos.weight = pos.market_value / total_value
    
    def get_portfolio_stats(self) -> PortfolioStats:
        """
        获取组合统计
        
        Returns:
            组合统计对象
        """
        total_value = sum(pos.market_value for pos in self.positions.values())
        total_cost = sum(pos.shares * pos.avg_cost for pos in self.positions.values())
        total_pnl = total_value - total_cost
        total_pnl_pct = total_pnl / total_cost if total_cost > 0 else 0
        
        # 计算各模块权重
        core_value = sum(pos.market_value for pos in self.positions.values() if pos.module == 'core')
        satellite_value = sum(pos.market_value for pos in self.positions.values() if pos.module == 'satellite')
        convertible_value = sum(pos.market_value for pos in self.positions.values() if pos.module == 'convertible')
        
        cash = self.capital - total_value
        total_assets = self.capital
        
        stats = PortfolioStats(
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            core_weight=core_value / total_assets if total_assets > 0 else 0,
            satellite_weight=satellite_value / total_assets if total_assets > 0 else 0,
            convertible_weight=convertible_value / total_assets if total_assets > 0 else 0,
            cash_weight=cash / total_assets if total_assets > 0 else 0,
            positions_count=len(self.positions),
            last_update=datetime.now()
        )
        
        return stats
    
    def calculate_target_allocation(self) -> Dict[str, float]:
        """
        计算目标配置
        
        Returns:
            {代码: 目标权重}字典
        """
        target = {}
        
        # Core目标
        core_config = self.config['core_target']
        core_etfs = {
            'broad': '510300',     # 沪深300
            'dividend': '510880',  # 红利ETF
            'bond_cash': '511990', # 短债ETF
            'gold': '518880',      # 黄金ETF
            'sp500': '513500'      # 标普500
        }
        
        for module, code in core_etfs.items():
            if module in core_config:
                target[code] = core_config[module]
        
        # Satellite目标（需要动态计算）
        # 这里简化处理，实际应该根据动量选股结果
        satellite_weight = self.config['satellite_target']
        satellite_positions = [pos for pos in self.positions.values() if pos.module == 'satellite']
        
        if satellite_positions:
            weight_per_position = satellite_weight / len(satellite_positions)
            for pos in satellite_positions:
                target[pos.code] = weight_per_position
        
        # Convertible目标
        convertible_weight = self.config['convertible_target']
        convertible_positions = [pos for pos in self.positions.values() if pos.module == 'convertible']
        
        if convertible_positions:
            weight_per_cb = convertible_weight / len(convertible_positions)
            for pos in convertible_positions:
                target[pos.code] = min(weight_per_cb, self.config['cb_rules']['per_bond_cap'])
        
        return target
    
    def generate_rebalance_orders(self, target_allocation: Optional[Dict[str, float]] = None,
                                  threshold: float = 0.02) -> List[RebalanceOrder]:
        """
        生成再平衡订单
        
        Args:
            target_allocation: 目标配置，如果为None则使用默认配置
            threshold: 触发再平衡的阈值
            
        Returns:
            再平衡订单列表
        """
        if target_allocation is None:
            target_allocation = self.calculate_target_allocation()
        
        orders = []
        total_value = self.capital
        
        # 计算当前权重
        current_weights = {}
        for code, pos in self.positions.items():
            current_weights[code] = pos.market_value / total_value if total_value > 0 else 0
        
        # 生成订单
        for code, target_weight in target_allocation.items():
            current_weight = current_weights.get(code, 0)
            weight_diff = target_weight - current_weight
            
            # 如果差异超过阈值
            if abs(weight_diff) > threshold:
                amount_diff = weight_diff * total_value
                
                if code in self.positions:
                    pos = self.positions[code]
                    shares_diff = int(amount_diff / pos.current_price) if pos.current_price > 0 else 0
                    
                    if shares_diff != 0:
                        order = RebalanceOrder(
                            code=code,
                            name=pos.name,
                            action='buy' if shares_diff > 0 else 'sell',
                            shares=abs(shares_diff),
                            price=pos.current_price,
                            amount=abs(amount_diff),
                            reason=f"再平衡: {current_weight:.2%} -> {target_weight:.2%}",
                            module=pos.module,
                            priority=2
                        )
                        orders.append(order)
                else:
                    # 新建仓位
                    # 需要获取价格信息（这里简化处理）
                    order = RebalanceOrder(
                        code=code,
                        name=code,  # 需要获取名称
                        action='buy',
                        shares=0,  # 需要计算
                        price=0,   # 需要获取
                        amount=amount_diff,
                        reason=f"新建仓位: 目标{target_weight:.2%}",
                        module='core',  # 需要判断
                        priority=1
                    )
                    orders.append(order)
        
        # 按优先级排序
        orders.sort(key=lambda x: x.priority)
        
        return orders
    
    def apply_dca_plan(self, week_number: int) -> Dict[str, Any]:
        """
        应用定投计划
        
        Args:
            week_number: 当前周数（1-6）
            
        Returns:
            定投执行结果
        """
        if week_number < 1 or week_number > self.config['dca_weeks']:
            raise ValueError(f"无效的周数: {week_number}")
        
        # 计算本周投资金额
        weekly_amount = self.capital / self.config['dca_weeks']
        
        # 分配到各模块
        allocations = {
            'core': weekly_amount * 0.4,
            'satellite': weekly_amount * 0.3,
            'convertible': weekly_amount * 0.1,
            'cash_reserve': weekly_amount * 0.2
        }
        
        # 生成具体的买入计划
        orders = []
        
        # Core模块分配
        core_amount = allocations['core']
        core_config = self.config['core_target']
        core_total = sum(core_config.values())
        
        core_etfs = {
            'broad': {'code': '510300', 'name': '沪深300ETF'},
            'dividend': {'code': '510880', 'name': '红利ETF'},
            'bond_cash': {'code': '511990', 'name': '短债ETF'},
            'gold': {'code': '518880', 'name': '黄金ETF'},
            'sp500': {'code': '513500', 'name': '标普500ETF'}
        }
        
        for module, weight in core_config.items():
            if module in core_etfs:
                amount = core_amount * (weight / core_total)
                orders.append({
                    'code': core_etfs[module]['code'],
                    'name': core_etfs[module]['name'],
                    'module': 'core',
                    'sub_module': module,
                    'amount': amount,
                    'weight': weight
                })
        
        result = {
            'week': week_number,
            'date': datetime.now().isoformat(),
            'total_amount': weekly_amount,
            'allocations': allocations,
            'orders': orders,
            'progress': {
                'completed_weeks': week_number,
                'total_weeks': self.config['dca_weeks'],
                'completion_rate': week_number / self.config['dca_weeks'],
                'invested_amount': weekly_amount * week_number,
                'remaining_amount': weekly_amount * (self.config['dca_weeks'] - week_number)
            }
        }
        
        logger.info(f"第{week_number}周定投计划: 投资{weekly_amount:.0f}元")
        return result
    
    def check_risk_limits(self) -> List[Dict[str, Any]]:
        """
        检查风险限制
        
        Returns:
            风险警告列表
        """
        warnings = []
        
        # 检查单一持仓集中度
        for code, pos in self.positions.items():
            if pos.module == 'satellite' and pos.weight > 0.15:
                warnings.append({
                    'type': 'concentration',
                    'code': code,
                    'name': pos.name,
                    'weight': pos.weight,
                    'message': f"{pos.name}权重{pos.weight:.2%}超过15%限制"
                })
            
            # 检查止损
            if pos.unrealized_pnl_pct < self.config['satellite_rules']['stop_loss']:
                warnings.append({
                    'type': 'stop_loss',
                    'code': code,
                    'name': pos.name,
                    'loss': pos.unrealized_pnl_pct,
                    'message': f"{pos.name}亏损{pos.unrealized_pnl_pct:.2%}触发止损"
                })
        
        # 检查模块权重偏离
        stats = self.get_portfolio_stats()
        
        core_target = sum(self.config['core_target'].values())
        if abs(stats.core_weight - core_target) > 0.1:
            warnings.append({
                'type': 'module_deviation',
                'module': 'core',
                'current': stats.core_weight,
                'target': core_target,
                'message': f"Core权重{stats.core_weight:.2%}偏离目标{core_target:.2%}"
            })
        
        return warnings
    
    def get_position_summary(self) -> Dict[str, Any]:
        """
        获取持仓汇总
        
        Returns:
            持仓汇总信息
        """
        stats = self.get_portfolio_stats()
        
        # 按模块分组
        core_positions = [p for p in self.positions.values() if p.module == 'core']
        satellite_positions = [p for p in self.positions.values() if p.module == 'satellite']
        convertible_positions = [p for p in self.positions.values() if p.module == 'convertible']
        
        summary = {
            'overview': {
                'total_value': stats.total_value,
                'total_cost': stats.total_cost,
                'total_pnl': stats.total_pnl,
                'total_pnl_pct': stats.total_pnl_pct,
                'cash': self.capital - stats.total_value,
                'positions_count': stats.positions_count
            },
            'allocation': {
                'core': {
                    'weight': stats.core_weight,
                    'value': sum(p.market_value for p in core_positions),
                    'count': len(core_positions)
                },
                'satellite': {
                    'weight': stats.satellite_weight,
                    'value': sum(p.market_value for p in satellite_positions),
                    'count': len(satellite_positions)
                },
                'convertible': {
                    'weight': stats.convertible_weight,
                    'value': sum(p.market_value for p in convertible_positions),
                    'count': len(convertible_positions)
                },
                'cash': {
                    'weight': stats.cash_weight,
                    'value': self.capital - stats.total_value
                }
            },
            'top_positions': sorted(
                [
                    {
                        'code': p.code,
                        'name': p.name,
                        'weight': p.weight,
                        'pnl_pct': p.unrealized_pnl_pct,
                        'module': p.module
                    }
                    for p in self.positions.values()
                ],
                key=lambda x: x['weight'],
                reverse=True
            )[:10],
            'last_update': stats.last_update.isoformat()
        }
        
        return summary