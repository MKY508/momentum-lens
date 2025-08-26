"""
半自动交易助手 - 条件单生成与管理
"""
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, time
import json
import logging

logger = logging.getLogger(__name__)

class TradingHelper:
    """交易助手"""
    
    def __init__(self):
        self.supported_brokers = {
            'ht': '华泰证券',
            'ht_client': '华泰客户端',
            'gj_client': '国金客户端',
            'yh_client': '银河客户端',
            'universal_client': '通用同花顺客户端'
        }
    
    def generate_conditional_orders(self, signals: List, capital: float, 
                                   trade_time: str = "10:30") -> pd.DataFrame:
        """生成条件单"""
        orders = []
        
        for signal in signals:
            if signal.action != "BUY":
                continue
            
            order = {
                '代码': signal.code,
                '名称': signal.name,
                '方向': '买入',
                '金额': capital * signal.weight,
                '价格类型': '限价',
                '限价': signal.iopv if signal.iopv else 0,
                '触发时间': trade_time,
                '有效期': '当日有效',
                '止损价': signal.stop_loss if signal.stop_loss else 0,
                '备注': signal.reason
            }
            orders.append(order)
        
        return pd.DataFrame(orders)
    
    def generate_iopv_band_orders(self, code: str, iopv: float, 
                                 amount: float, band_width: float = 0.002) -> List[Dict]:
        """生成IOPV限价带订单"""
        orders = []
        
        # 生成5档限价单
        for i in range(-2, 3):
            price = iopv * (1 + i * band_width)
            order = {
                'code': code,
                'price': round(price, 3),
                'amount': amount / 5,  # 分5档
                'type': 'limit',
                'side': 'buy'
            }
            orders.append(order)
        
        return orders
    
    def generate_grid_orders(self, code: str, base_price: float,
                           grid_size: float = 0.01, grid_count: int = 10,
                           amount_per_grid: float = 10000) -> List[Dict]:
        """生成网格交易订单"""
        orders = []
        
        for i in range(grid_count):
            # 买入网格
            buy_price = base_price * (1 - (i + 1) * grid_size)
            orders.append({
                'code': code,
                'price': round(buy_price, 3),
                'amount': amount_per_grid,
                'type': 'limit',
                'side': 'buy',
                'grid_level': i + 1
            })
            
            # 卖出网格
            sell_price = base_price * (1 + (i + 1) * grid_size)
            orders.append({
                'code': code,
                'price': round(sell_price, 3),
                'amount': amount_per_grid,
                'type': 'limit',
                'side': 'sell',
                'grid_level': i + 1
            })
        
        return orders
    
    def export_to_broker_format(self, orders: pd.DataFrame, 
                               broker: str = 'ht') -> str:
        """导出为券商格式"""
        if broker not in self.supported_brokers:
            raise ValueError(f"不支持的券商: {broker}")
        
        if broker == 'ht':
            # 华泰证券格式
            export_data = []
            for _, order in orders.iterrows():
                export_data.append({
                    'security': order['代码'],
                    'amount': int(order['金额']),
                    'price': order.get('限价', 0),
                    'entrust_prop': 'limit' if order.get('限价', 0) > 0 else 'market'
                })
            return json.dumps(export_data, ensure_ascii=False, indent=2)
        
        # 其他券商格式...
        return orders.to_csv(index=False)
    
    def generate_easytrader_script(self, orders: pd.DataFrame, 
                                  broker: str = 'ht') -> str:
        """生成easytrader脚本"""
        script = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 半自动交易脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M')}

import easytrader
import time
import json

# 配置券商
user = easytrader.use('{broker}')

# 准备配置文件（需要提前配置）
# config.json 示例：
# {{
#     "user": "你的账号",
#     "password": "你的密码",
#     "exe_path": "C:/path/to/client.exe"
# }}

user.prepare('config.json')

# 订单数据
orders = {orders.to_dict('records')}

# 执行订单
def execute_orders():
    success_count = 0
    fail_count = 0
    
    for order in orders:
        try:
            # 买入
            if order.get('限价', 0) > 0:
                # 限价单
                result = user.buy(
                    order['代码'],
                    price=order['限价'],
                    amount=int(order['金额'] / order['限价'] / 100) * 100
                )
            else:
                # 市价单
                result = user.market_buy(
                    order['代码'],
                    amount=order['金额']
                )
            
            print(f"✅ 成功: {{order['代码']}} {{order['名称']}}")
            success_count += 1
            
            # 避免频繁交易
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ 失败: {{order['代码']}} {{order['名称']}} - {{e}}")
            fail_count += 1
    
    print(f"\\n执行完成: 成功 {{success_count}} 笔, 失败 {{fail_count}} 笔")
    
    # 查询持仓
    print("\\n当前持仓:")
    print(user.position)
    
    # 查询余额
    print("\\n账户余额:")
    print(user.balance)

if __name__ == '__main__':
    print("开始执行半自动交易...")
    print(f"券商: {self.supported_brokers.get(broker, broker)}")
    print(f"订单数: {{len(orders)}}")
    
    confirm = input("\\n确认执行? (y/n): ")
    if confirm.lower() == 'y':
        execute_orders()
    else:
        print("已取消")
"""
        return script
    
    def generate_tuesday_schedule(self, morning_orders: pd.DataFrame,
                                 afternoon_orders: pd.DataFrame) -> Dict:
        """生成周二定投计划"""
        schedule = {
            'day': 'Tuesday',
            'morning': {
                'time': '10:30',
                'orders': morning_orders.to_dict('records')
            },
            'afternoon': {
                'time': '14:00',
                'orders': afternoon_orders.to_dict('records')
            },
            'total_amount': (
                morning_orders['金额'].sum() + 
                afternoon_orders['金额'].sum()
            )
        }
        
        return schedule
    
    def validate_orders(self, orders: pd.DataFrame) -> List[str]:
        """验证订单合法性"""
        warnings = []
        
        # 检查金额
        if orders['金额'].sum() == 0:
            warnings.append("订单总金额为0")
        
        # 检查代码格式
        for code in orders['代码']:
            if not (code.isdigit() and len(code) == 6):
                warnings.append(f"代码格式错误: {code}")
        
        # 检查重复
        duplicates = orders[orders.duplicated(['代码'], keep=False)]
        if not duplicates.empty:
            warnings.append(f"存在重复订单: {duplicates['代码'].unique()}")
        
        return warnings

if __name__ == "__main__":
    # 测试代码
    from decision_engine import DecisionEngine
    
    helper = TradingHelper()
    engine = DecisionEngine()
    
    # 生成信号
    signals = engine.generate_signals()
    
    # 生成条件单
    orders = helper.generate_conditional_orders(signals, capital=100000)
    print("条件单:")
    print(orders)
    
    # 生成脚本
    script = helper.generate_easytrader_script(orders)
    print("\n交易脚本已生成")
    
    # 保存脚本
    with open("auto_trade.py", 'w', encoding='utf-8') as f:
        f.write(script)
    print("脚本已保存到 auto_trade.py")