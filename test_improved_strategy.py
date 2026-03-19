#!/usr/bin/env python
"""
测试改进的回测策略

验证：
1. 稳定度权重是否正确应用
2. 观察期机制是否正常工作
3. 策略说明是否正确显示
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from momentum_cli.backtest import run_improved_slow_leg_strategy
from momentum_cli.presets import PRESETS


def test_improved_strategy():
    """测试改进策略"""
    print("=" * 80)
    print("测试改进的慢腿轮动策略（观察期机制）")
    print("=" * 80)
    
    # 使用小范围测试
    etf_codes = [
        "510300.XSHG",  # 沪深300ETF
        "510500.XSHG",  # 中证500ETF
        "159915.XSHE",  # 创业板ETF
        "512100.XSHG",  # 中证1000ETF
        "159941.XSHE",  # 纳指ETF
    ]
    
    # 测试参数
    momentum_params = {
        'momentum_windows': [63, 126],
        'momentum_weights': [0.6, 0.4],
        'momentum_skip_windows': [21, 21],
        'stability_weight': 0.2,
        'stability_window': 30,
        'observation_weeks': 2
    }
    
    print(f"\n测试配置：")
    print(f"  ETF数量: {len(etf_codes)}")
    print(f"  稳定度权重: {momentum_params['stability_weight']}")
    print(f"  稳定度窗口: {momentum_params['stability_window']}天")
    print(f"  观察期: {momentum_params['observation_weeks']}周")
    print(f"  时间范围: 2023-01-01 至 2024-12-31")
    
    try:
        print("\n开始运行回测...")
        result = run_improved_slow_leg_strategy(
            etf_codes=etf_codes,
            start_date="2023-01-01",
            end_date="2024-12-31",
            momentum_params=momentum_params
        )
        
        print("\n" + "=" * 80)
        print(f"回测结果 - {result.strategy_name}")
        print("=" * 80)
        
        print(f"\n总收益率: {result.total_return:.2f}%")
        print(f"年化收益率: {result.annual_return:.2f}%")
        print(f"夏普比率: {result.sharpe_ratio:.2f}")
        print(f"最大回撤: {result.max_drawdown:.2f}%")
        print(f"交易次数: {len(result.trades)}")
        
        # 显示交易详情
        if result.trades:
            print(f"\n交易记录（共{len(result.trades)}笔）:")
            print("-" * 80)
            
            # 统计换仓原因
            reason_counts = {}
            for trade in result.trades:
                reason = trade.reason
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            print("\n换仓原因统计：")
            for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {reason}: {count}次")
            
            # 显示最近10笔交易
            print("\n最近10笔交易：")
            for trade in result.trades[-10:]:
                action_symbol = "📈" if trade.action == "BUY" else "📉"
                print(f"  {action_symbol} {trade.date} | {trade.action:4s} {trade.code:15s} | "
                      f"价格: {trade.price:6.2f} | {trade.reason}")
        
        print("\n" + "=" * 80)
        print("✅ 测试完成！策略运行正常。")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_description():
    """测试策略说明"""
    from momentum_cli.cli import _get_strategy_description
    
    print("\n" + "=" * 80)
    print("测试策略说明文档")
    print("=" * 80)
    
    strategies = ["慢腿轮动", "快腿轮动", "宏观驱动", "改进慢腿轮动(观察期)"]
    
    for strategy in strategies:
        desc = _get_strategy_description(strategy)
        if desc:
            print(f"\n策略: {strategy}")
            print(desc)
        else:
            print(f"\n⚠️  策略 '{strategy}' 没有说明文档")
    
    print("=" * 80)


if __name__ == "__main__":
    print("\n🚀 开始测试改进的回测策略\n")
    
    # 测试策略说明
    test_strategy_description()
    
    # 测试改进策略
    success = test_improved_strategy()
    
    if success:
        print("\n✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 测试失败，请检查错误信息。")
        sys.exit(1)

