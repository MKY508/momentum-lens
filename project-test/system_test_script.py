#!/usr/bin/env python3
"""系统测试脚本 - 验证各个模块功能"""

import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加backend到Python路径
sys.path.append(str(Path(__file__).parent / 'backend'))

def test_imports():
    """测试模块导入"""
    print("📦 测试模块导入...")
    try:
        from data.datasource import DataSourceInterface, AKShareAdapter
        from indicators.momentum import MomentumCalculator
        from indicators.convertible import ConvertibleBondAnalyzer
        from engine.decision import DecisionEngine
        from portfolio.manager import PortfolioManager
        from orders.generator import OrderGenerator
        from risk.monitor import RiskMonitor
        print("✅ 所有模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def test_config_loading():
    """测试配置文件加载"""
    print("\n📋 测试配置文件加载...")
    import yaml
    
    config_files = ['config.yaml', 'positions.yaml', 'build_plan.yaml']
    configs = {}
    
    for file in config_files:
        path = Path('config') / file
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                configs[file] = yaml.safe_load(f)
                print(f"✅ {file} 加载成功")
        else:
            print(f"⚠️  {file} 不存在")
    
    return configs

def test_momentum_calculation():
    """测试动量计算"""
    print("\n🎯 测试动量计算...")
    from indicators.momentum import MomentumCalculator
    
    # 模拟数据
    mock_data = pd.DataFrame({
        'date': pd.date_range(end=datetime.now(), periods=252),
        'close': 100 + pd.Series(range(252)) * 0.1  # 模拟上涨趋势
    })
    
    calc = MomentumCalculator()
    
    # 计算MA200
    ma200 = calc.calculate_ma(mock_data['close'], 200)
    print(f"  MA200最新值: {ma200.iloc[-1]:.2f}")
    
    # 计算动量
    r3m = calc.calculate_momentum(mock_data, 63)
    r6m = calc.calculate_momentum(mock_data, 126)
    score = calc.calculate_dual_momentum_score(r3m, r6m)
    print(f"  3月动量: {r3m:.2%}")
    print(f"  6月动量: {r6m:.2%}")
    print(f"  动量得分: {score:.2f}")
    
    return True

def test_convertible_bond_scoring():
    """测试可转债评分"""
    print("\n🎰 测试可转债评分...")
    from indicators.convertible import ConvertibleBondAnalyzer
    
    # 模拟可转债数据
    mock_cb_data = pd.DataFrame({
        'code': ['113001', '113002', '113003'],
        'name': ['转债A', '转债B', '转债C'],
        'price': [105, 98, 120],
        'premium_rate': [5, 15, 25],
        'credit_rating': ['AAA', 'AA+', 'AA'],
        'size': [10e8, 5e8, 20e8],
        'remaining_years': [3, 2, 4],
        'turnover': [1e8, 5e7, 2e8],
        'atr20': [3, 2, 5]
    })
    
    analyzer = ConvertibleBondAnalyzer()
    scores = analyzer.calculate_scores(mock_cb_data)
    
    print(f"  评分数量: {len(scores)}")
    for score in scores[:3]:
        print(f"  {score.name}: 总分={score.total_score:.2f}, 网格步长={score.grid_step*100:.1f}%")
    
    # 选择组合
    portfolio = analyzer.select_portfolio(scores, max_bonds=5)
    print(f"  选中债券: {len(portfolio)}只")
    
    return True

def test_risk_monitoring():
    """测试风险监控"""
    print("\n🚨 测试风险监控...")
    from risk.monitor import RiskMonitor
    
    config = {'satellite_rules': {'stop_loss': -0.12, 'corr_max': 0.8}}
    monitor = RiskMonitor(config)
    
    # 模拟市场和持仓数据
    market_data = {
        'hs300': {
            'ma200_ratio': 0.98,  # 跌破年线
            'chop': 65,  # 震荡市
            'atr_pct': 0.025
        }
    }
    
    portfolio = {
        'positions': [
            {
                'code': '510300',
                'name': '沪深300ETF',
                'weight': 0.20,
                'pnl_pct': -0.05,
                'category': 'core'
            },
            {
                'code': '512660',
                'name': '军工ETF',
                'weight': 0.15,
                'pnl_pct': -0.13,  # 触及止损
                'category': 'satellite',
                'avg_turnover': 3e7  # 流动性不足
            }
        ],
        'drawdown': -0.08,
        'satellite_correlation': 0.85  # 相关性过高
    }
    
    data_quality = {'overall': 0.98, 'issues': []}
    
    # 执行风险检查
    alerts = monitor.check_all_risks(market_data, portfolio, data_quality)
    summary = monitor.get_risk_summary()
    
    print(f"  风险警报数: {summary['total_alerts']}")
    print(f"  高风险: {summary['high']}, 中风险: {summary['medium']}, 低风险: {summary['low']}")
    print(f"  是否停止交易: {summary['should_stop']}")
    
    return True

def test_order_generation():
    """测试订单生成"""
    print("\n📝 测试订单生成...")
    from orders.generator import OrderGenerator
    
    config = {
        'execution_windows': ['10:30', '14:00'],
        'execution_day': 'Tue'
    }
    
    generator = OrderGenerator(config)
    
    # 模拟决策数据
    decision = {
        'core_orders': [
            {
                'code': '510300',
                'name': '沪深300ETF',
                'amount': 10000,
                'price': 4.5,
                'iopv_info': {'available': True, 'value': 4.495, 'premium_rate': 0.001}
            }
        ],
        'satellite_orders': [
            {
                'code': '512660',
                'name': '军工ETF',
                'amount': 5000,
                'price': 1.2,
                'momentum_score': 0.85
            }
        ]
    }
    
    # 生成ETF订单
    etf_orders = generator.generate_etf_orders(decision)
    print(f"  生成ETF订单: {len(etf_orders)}条")
    
    for order in etf_orders:
        print(f"    {order.name}: {order.direction} {order.shares}股 @ {order.trigger_condition}")
    
    # 导出CSV
    if etf_orders:
        csv_path = generator.export_to_csv(etf_orders, 'test_orders.csv')
        print(f"  订单已导出到: {csv_path}")
    
    return True

def test_api_endpoints():
    """测试API端点（需要后端服务运行）"""
    print("\n🔌 测试API端点...")
    base_url = "http://localhost:8000"
    
    try:
        # 测试健康检查
        response = requests.get(f"{base_url}/health", timeout=2)
        if response.status_code == 200:
            print("✅ API服务正常")
        
        # 测试市场环境
        response = requests.get(f"{base_url}/api/market/environment", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"  市场状态: {data.get('regime', 'N/A')}")
        
        return True
    except requests.exceptions.ConnectionError:
        print("⚠️  API服务未运行，跳过测试")
        return False
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("   ETF动量决策系统 - 功能测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("配置加载", test_config_loading),
        ("动量计算", test_momentum_calculation),
        ("可转债评分", test_convertible_bond_scoring),
        ("风险监控", test_risk_monitoring),
        ("订单生成", test_order_generation),
        ("API端点", test_api_endpoints)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name}测试异常: {e}")
            results.append((name, False))
    
    # 测试总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统准备就绪。")
        print("\n下一步:")
        print("1. 运行 ./start.sh 启动系统")
        print("2. 访问 http://localhost:3000 查看界面")
        print("3. 访问 http://localhost:8000/docs 查看API文档")
    else:
        print("\n⚠️  部分测试失败，请检查相关模块。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)