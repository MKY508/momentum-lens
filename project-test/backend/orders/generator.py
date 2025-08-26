"""订单生成器模块"""
import pandas as pd
import json
import csv
from datetime import datetime, time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ConditionalOrder:
    """条件单"""
    code: str
    name: str
    order_type: str  # 'etf' or 'cb'
    direction: str  # 'buy' or 'sell'
    shares: int
    trigger_type: str  # 'time' or 'price'
    trigger_condition: str
    price_type: str  # 'limit' or 'market'
    limit_price: Optional[float] = None
    iopv_range: Optional[tuple] = None
    notes: str = ""
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class OrderGenerator:
    """订单生成器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.execution_windows = config.get('execution_windows', ['10:30', '14:00'])
        self.execution_day = config.get('execution_day', 'Tue')
        
    def generate_etf_orders(self, decision: Dict) -> List[ConditionalOrder]:
        """生成ETF条件单"""
        orders = []
        
        # Core资产订单
        core_orders = decision.get('core_orders', [])
        for order in core_orders:
            if abs(order['amount']) > 100:  # 忽略小额订单
                conditional_order = self._create_etf_order(
                    code=order['code'],
                    name=order['name'],
                    shares=int(order['amount'] / order.get('price', 1)),
                    direction='buy' if order['amount'] > 0 else 'sell',
                    execution_time=self.execution_windows[0],
                    iopv_info=order.get('iopv_info')
                )
                orders.append(conditional_order)
        
        # 卫星订单
        satellite_orders = decision.get('satellite_orders', [])
        for i, order in enumerate(satellite_orders):
            if abs(order['amount']) > 100:
                # 第一条腿10:30执行，第二条腿14:00执行
                exec_time = self.execution_windows[min(i, 1)]
                conditional_order = self._create_etf_order(
                    code=order['code'],
                    name=order['name'],
                    shares=int(order['amount'] / order.get('price', 1)),
                    direction='buy' if order['amount'] > 0 else 'sell',
                    execution_time=exec_time,
                    iopv_info=order.get('iopv_info'),
                    notes=f"卫星第{i+1}条腿，动量分数: {order.get('momentum_score', 0):.2f}"
                )
                orders.append(conditional_order)
        
        return orders
    
    def _create_etf_order(self, code: str, name: str, shares: int,
                         direction: str, execution_time: str,
                         iopv_info: Optional[Dict] = None,
                         notes: str = "") -> ConditionalOrder:
        """创建单个ETF订单"""
        warnings = []
        iopv_range = None
        
        # IOPV限价处理
        if iopv_info and iopv_info.get('available'):
            iopv = iopv_info['value']
            premium = iopv_info.get('premium_rate', 0)
            
            if code.startswith('5'):  # 国内ETF
                if abs(premium) > 0.005:
                    warnings.append(f"溢价率{premium*100:.2f}%超过0.5%")
                iopv_range = (iopv * 0.999, iopv * 1.001)
            else:  # QDII
                if premium > 0.02:
                    warnings.append(f"QDII溢价率{premium*100:.2f}%超过2%")
                    if direction == 'buy':
                        warnings.append("建议暂缓买入")
                iopv_range = (iopv * 0.98, iopv * 1.02)
        else:
            warnings.append("IOPV数据不可用，使用昨收±0.5%限价")
        
        return ConditionalOrder(
            code=code,
            name=name,
            order_type='etf',
            direction=direction,
            shares=shares,
            trigger_type='time',
            trigger_condition=f"{self.execution_day} {execution_time}",
            price_type='limit',
            iopv_range=iopv_range,
            notes=notes,
            warnings=warnings
        )
    
    def generate_cb_orders(self, cb_grids: List[Dict]) -> List[ConditionalOrder]:
        """生成可转债网格订单"""
        orders = []
        
        for grid in cb_grids:
            # 买入订单
            for buy_order in grid.get('buy_orders', []):
                order = ConditionalOrder(
                    code=grid['code'],
                    name=grid['name'],
                    order_type='cb',
                    direction='buy',
                    shares=buy_order['shares'],
                    trigger_type='price',
                    trigger_condition=buy_order['trigger'],
                    price_type='limit',
                    limit_price=buy_order['price'],
                    notes=f"网格步长{grid['grid_step_pct']:.1f}%",
                    warnings=grid.get('warnings', [])
                )
                orders.append(order)
            
            # 卖出订单
            for sell_order in grid.get('sell_orders', []):
                order = ConditionalOrder(
                    code=grid['code'],
                    name=grid['name'],
                    order_type='cb',
                    direction='sell',
                    shares=sell_order['shares'],
                    trigger_type='price',
                    trigger_condition=sell_order['trigger'],
                    price_type='limit',
                    limit_price=sell_order['price'],
                    notes=f"网格步长{grid['grid_step_pct']:.1f}%",
                    warnings=grid.get('warnings', [])
                )
                orders.append(order)
        
        return orders
    
    def export_to_csv(self, orders: List[ConditionalOrder], 
                      filepath: str = None) -> str:
        """导出到CSV文件"""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"orders_{timestamp}.csv"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = [
                '代码', '名称', '类型', '方向', '数量', 
                '触发类型', '触发条件', '价格类型', '限价',
                'IOPV范围', '备注', '警告'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for order in orders:
                iopv_str = ''
                if order.iopv_range:
                    iopv_str = f"{order.iopv_range[0]:.3f}-{order.iopv_range[1]:.3f}"
                
                writer.writerow({
                    '代码': order.code,
                    '名称': order.name,
                    '类型': 'ETF' if order.order_type == 'etf' else '可转债',
                    '方向': '买入' if order.direction == 'buy' else '卖出',
                    '数量': order.shares,
                    '触发类型': '时间' if order.trigger_type == 'time' else '价格',
                    '触发条件': order.trigger_condition,
                    '价格类型': '限价' if order.price_type == 'limit' else '市价',
                    '限价': order.limit_price if order.limit_price else '',
                    'IOPV范围': iopv_str,
                    '备注': order.notes,
                    '警告': '; '.join(order.warnings) if order.warnings else ''
                })
        
        logger.info(f"订单已导出到: {filepath}")
        return str(filepath)
    
    def export_to_json(self, orders: List[ConditionalOrder],
                      filepath: str = None) -> str:
        """导出到JSON文件"""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"orders_{timestamp}.json"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        orders_dict = [asdict(order) for order in orders]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'execution_day': self.execution_day,
                'execution_windows': self.execution_windows,
                'total_orders': len(orders),
                'orders': orders_dict
            }, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"订单已导出到: {filepath}")
        return str(filepath)
    
    def generate_broker_template(self, orders: List[ConditionalOrder]) -> Dict:
        """生成券商条件单模板"""
        # 按券商格式分组
        broker_orders = {
            'time_orders': [],  # 时间条件单
            'price_orders': [],  # 价格条件单
            'grid_orders': {}    # 网格单（按标的分组）
        }
        
        for order in orders:
            if order.trigger_type == 'time':
                broker_orders['time_orders'].append({
                    'code': order.code,
                    'name': order.name,
                    'direction': order.direction,
                    'shares': order.shares,
                    'time': order.trigger_condition,
                    'price_range': order.iopv_range,
                    'notes': order.notes
                })
            elif order.order_type == 'cb':
                if order.code not in broker_orders['grid_orders']:
                    broker_orders['grid_orders'][order.code] = {
                        'name': order.name,
                        'buy_orders': [],
                        'sell_orders': []
                    }
                
                grid_order = {
                    'price': order.limit_price,
                    'shares': order.shares
                }
                
                if order.direction == 'buy':
                    broker_orders['grid_orders'][order.code]['buy_orders'].append(grid_order)
                else:
                    broker_orders['grid_orders'][order.code]['sell_orders'].append(grid_order)
            else:
                broker_orders['price_orders'].append({
                    'code': order.code,
                    'name': order.name,
                    'direction': order.direction,
                    'shares': order.shares,
                    'trigger': order.trigger_condition,
                    'limit_price': order.limit_price,
                    'notes': order.notes
                })
        
        return broker_orders
    
    def validate_orders(self, orders: List[ConditionalOrder],
                       available_capital: float) -> Dict:
        """验证订单可行性"""
        validation_result = {
            'valid': True,
            'total_buy_amount': 0,
            'total_sell_amount': 0,
            'warnings': [],
            'errors': []
        }
        
        for order in orders:
            # 估算金额
            if order.limit_price:
                amount = order.shares * order.limit_price
            elif order.iopv_range:
                amount = order.shares * sum(order.iopv_range) / 2
            else:
                amount = 0  # 无法估算
                validation_result['warnings'].append(
                    f"{order.code} {order.name} 无法估算金额"
                )
            
            if order.direction == 'buy':
                validation_result['total_buy_amount'] += amount
            else:
                validation_result['total_sell_amount'] += amount
            
            # 检查警告
            if order.warnings:
                for warning in order.warnings:
                    validation_result['warnings'].append(
                        f"{order.code} {order.name}: {warning}"
                    )
        
        # 检查资金是否充足
        if validation_result['total_buy_amount'] > available_capital:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"买入金额{validation_result['total_buy_amount']:.0f}超过可用资金{available_capital:.0f}"
            )
        
        return validation_result