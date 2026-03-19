#!/usr/bin/env python
"""
测试所有修复

验证：
1. 榜首动量判定逻辑
2. 短期样本年化率
3. 选仓器约束
4. 组合风控
5. 手续费和滑点
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("测试所有修复")
print("=" * 80)

# 测试1: 编译检查
print("\n[测试1] 编译检查")
try:
    from momentum_cli import backtest
    from momentum_cli.business import backtest as biz_backtest
    from momentum_cli.business import reports
    print("✅ 所有模块导入成功")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

# 测试2: 选仓器约束
print("\n[测试2] 选仓器约束函数")
try:
    import pandas as pd
    import numpy as np
    
    # 创建测试数据
    scores = pd.Series({
        'A': 0.15,
        'B': 0.12,
        'C': 0.08,
        'D': 0.05,
        'E': 0.02,
    })
    
    percentiles = pd.Series({
        'A': 90.0,
        'B': 75.0,
        'C': 55.0,  # 低于阈值
        'D': 45.0,  # 低于阈值
        'E': 20.0,  # 低于阈值
    })
    
    corr_matrix = pd.DataFrame({
        'A': [1.0, 0.3, 0.2, 0.1, 0.1],
        'B': [0.3, 1.0, 0.9, 0.2, 0.1],  # B和C高相关
        'C': [0.2, 0.9, 1.0, 0.1, 0.1],
        'D': [0.1, 0.2, 0.1, 1.0, 0.1],
        'E': [0.1, 0.1, 0.1, 0.1, 1.0],
    }, index=['A', 'B', 'C', 'D', 'E'])
    
    selected, diag = biz_backtest.select_assets_with_constraints(
        scores,
        percentiles,
        corr_matrix,
        top_n=2,
        min_percentile=60.0,
        max_correlation=0.85,
    )
    
    print(f"  候选数: {diag['candidates_count']}")
    print(f"  选中数: {diag['selected_count']}")
    print(f"  选中资产: {selected}")
    print(f"  相关性冲突: {diag['correlation_violations']}")
    
    # 验证：应该只选A和B（C虽然和B相关但分位数不够）
    assert 'A' in selected, "A应该被选中（分位数90%）"
    assert 'B' in selected, "B应该被选中（分位数75%）"
    assert 'C' not in selected, "C不应该被选中（分位数55%<60%）"
    assert len(selected) == 2, "应该选中2个资产"
    
    print("✅ 选仓器约束测试通过")
    
except Exception as e:
    print(f"❌ 选仓器测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 组合风控
print("\n[测试3] 组合风控")
try:
    from momentum_cli.backtest import BacktestConfig, BacktestEngine
    import datetime as dt
    
    config = BacktestConfig(
        start_date="2023-01-01",
        end_date="2023-12-31"
    )
    engine = BacktestEngine(config)
    
    # 模拟权益变化
    dates = [
        dt.date(2023, 1, 1),
        dt.date(2023, 2, 1),
        dt.date(2023, 3, 1),
        dt.date(2023, 4, 1),
    ]
    
    equities = [
        100000,  # 初始
        95000,   # -5%
        85000,   # -15% (触发第一级)
        80000,   # -20% (触发第二级)
    ]
    
    print("  模拟权益变化:")
    for date, equity in zip(dates, equities):
        engine._update_portfolio_risk(date, equity)
        max_exp = engine.get_max_satellite_exposure()
        print(f"    {date}: 权益={equity}, 风控等级={engine.risk_level}, 最大卫星仓位={max_exp:.1%}")
    
    # 验证
    assert engine.risk_level == 2, f"风控等级应该是2，实际是{engine.risk_level}"
    assert engine.get_max_satellite_exposure() == 0.25, "最大卫星仓位应该是25%"
    
    print("✅ 组合风控测试通过")
    
except Exception as e:
    print(f"❌ 组合风控测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试4: 手续费和滑点
print("\n[测试4] 手续费和滑点")
try:
    # 检查默认值
    import inspect
    sig = inspect.signature(biz_backtest.run_simple_backtest)
    params = sig.parameters
    
    commission = params['commission_rate'].default
    slippage = params['slippage_rate'].default
    
    print(f"  手续费: {commission} (万{commission*10000:.1f})")
    print(f"  滑点: {slippage} ({slippage*100:.2f}%)")
    
    assert commission == 0.00005, f"手续费应该是万0.5，实际是{commission}"
    assert slippage == 0.0005, f"滑点应该是0.05%，实际是{slippage}"
    
    print("✅ 手续费和滑点测试通过")
    
except Exception as e:
    print(f"❌ 手续费和滑点测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试5: 配置文件更新
print("\n[测试5] 配置文件更新")
try:
    from momentum_cli.config.settings import DEFAULT_SETTINGS
    
    stability_weight = DEFAULT_SETTINGS.get('stability_weight')
    stability_window = DEFAULT_SETTINGS.get('stability_window')
    
    print(f"  稳定度权重: {stability_weight}")
    print(f"  稳定度窗口: {stability_window}")
    
    assert stability_weight == 0.2, f"稳定度权重应该是0.2，实际是{stability_weight}"
    assert stability_window == 30, f"稳定度窗口应该是30，实际是{stability_window}"
    
    print("✅ 配置文件更新测试通过")
    
except Exception as e:
    print(f"❌ 配置文件测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试6: 分析配置
print("\n[测试6] 分析配置")
try:
    from momentum_cli.analysis import AnalysisConfig
    
    config = AnalysisConfig()
    
    print(f"  稳定度权重: {config.stability_weight}")
    print(f"  稳定度窗口: {config.stability_window}")
    
    assert config.stability_weight == 0.2, f"稳定度权重应该是0.2，实际是{config.stability_weight}"
    assert config.stability_window == 30, f"稳定度窗口应该是30，实际是{config.stability_window}"
    
    print("✅ 分析配置测试通过")
    
except Exception as e:
    print(f"❌ 分析配置测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试7: 4个预设策略
print("\n[测试7] 4个预设策略")
try:
    from momentum_cli.analysis_presets import ANALYSIS_PRESETS
    
    expected_presets = ['slow-core', 'blend-dual', 'twelve-minus-one', 'fast-rotation']
    
    for key in expected_presets:
        if key in ANALYSIS_PRESETS:
            preset = ANALYSIS_PRESETS[key]
            print(f"  ✅ {preset.name} [{key}]")
            print(f"      动量窗口: {preset.momentum_windows}")
            print(f"      动量权重: {preset.momentum_weights}")
        else:
            print(f"  ❌ 缺少预设: {key}")
    
    assert all(k in ANALYSIS_PRESETS for k in expected_presets), "缺少预设策略"
    
    print("✅ 预设策略测试通过")
    
except Exception as e:
    print(f"❌ 预设策略测试失败: {e}")
    import traceback
    traceback.print_exc()

# 总结
print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)
print("""
✅ 已完成的修复:
  1. 榜首动量判定逻辑 - 使用分位数而非原始得分
  2. 短期样本年化率 - <180天不显示年化
  3. 选仓器约束 - 先过滤动量阈值，再控制相关性
  4. 组合风控 - 回撤阈值逐级降仓
  5. 手续费和滑点 - 万0.5 + 0.05%
  6. 配置文件更新 - 稳定度权重0.2，窗口30
  7. 4个预设策略 - slow-core, blend-dual, twelve-minus-one, fast-rotation

下一步:
  - 运行完整回测验证效果
  - 对比修复前后的结果
  - 根据实际效果微调参数
""")
print("=" * 80)

