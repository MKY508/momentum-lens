#!/usr/bin/env python3
"""
系统测试脚本
"""
import sys
import os

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    try:
        from data_adapter import DataAdapter
        print("✅ data_adapter")
        
        from indicators import IndicatorCalculator
        print("✅ indicators")
        
        from decision_engine import DecisionEngine
        print("✅ decision_engine")
        
        from trading_helper import TradingHelper
        print("✅ trading_helper")
        
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_data_adapter():
    """测试数据适配器"""
    print("\n测试数据适配器...")
    try:
        from data_adapter import DataAdapter
        adapter = DataAdapter()
        
        # 测试市场状态
        state = adapter.get_market_state()
        print(f"市场状态: {state}")
        
        # 测试ETF列表
        etf_list = adapter.get_etf_list()
        if not etf_list.empty:
            print(f"获取到 {len(etf_list)} 只ETF")
            print(f"示例: {etf_list.iloc[0]['name']} ({etf_list.iloc[0]['code']})")
        else:
            print("⚠️ 未获取到ETF数据（可能是网络问题）")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_decision_engine():
    """测试决策引擎"""
    print("\n测试决策引擎...")
    try:
        from decision_engine import DecisionEngine
        engine = DecisionEngine()
        
        # 测试市场分析
        market_state = engine.analyze_market_state()
        print(f"市场状态: {market_state}")
        
        # 测试信号生成
        signals = engine.generate_signals()
        print(f"生成 {len(signals)} 个信号")
        
        if signals:
            signal = signals[0]
            print(f"示例信号: {signal.action} {signal.name} ({signal.code}) - {signal.module}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    print("=" * 50)
    print("ETF动量策略系统 - 功能测试")
    print("=" * 50)
    
    # 切换到项目目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 运行测试
    results = []
    
    results.append(("模块导入", test_imports()))
    results.append(("数据适配器", test_data_adapter()))
    results.append(("决策引擎", test_decision_engine()))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    # 总体状态
    if all(r[1] for r in results):
        print("\n🎉 所有测试通过！系统可以正常运行。")
        print("\n运行以下命令启动系统:")
        print("  streamlit run app.py")
    else:
        print("\n⚠️ 部分测试失败，请检查:")
        print("  1. 是否安装了所有依赖: pip install -r requirements.txt")
        print("  2. 网络连接是否正常")
        print("  3. Python版本是否>=3.8")

if __name__ == "__main__":
    main()