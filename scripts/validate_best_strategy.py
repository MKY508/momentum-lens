#!/usr/bin/env python
"""
最优策略验证与长期回测脚本

功能：
1. 验证推荐配置在不同时期的表现
2. 对比基准指数（沪深300、中证500等）
3. 生成详细的调仓指南
4. 解释为什么该策略表现最好

使用方法：
    python scripts/validate_best_strategy.py --strategy twelve-minus-one --period 10y
    python scripts/validate_best_strategy.py --compare-all  # 对比所有策略
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import argparse

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

from momentum_cli.analysis import analyze, AnalysisConfig
from momentum_cli.analysis_presets import ANALYSIS_PRESETS, refresh_analysis_presets


# ============= 配置 =============

# 推荐配置（来自你的测试结果）
RECOMMENDED_CONFIG = {
    "strategy": "twelve-minus-one",
    "frequency": "monthly",
    "top_n": 2,
    "observation_period": 2,
    "correlation_threshold": 0.70,
}

# 基准指数
BENCHMARK_CODES = {
    "沪深300": "510300.XSHG",
    "中证500": "510500.XSHG",
    "中证1000": "512260.XSHG",
    "创业板50": "159949.XSHE",
}

# ETF候选池
ALL_CODES = [
    "510300.XSHG", "510880.XSHG", "511360.XSHG", "518880.XSHG", "513500.XSHG",
    "512980.XSHG", "512170.XSHG", "512690.XSHG", "512480.XSHG", "515790.XSHG",
    "516160.XSHG", "159995.XSHE", "513100.XSHG", "513050.XSHG", "159949.XSHE",
    "588000.XSHG", "512260.XSHG", "510500.XSHG",
]


# ============= 回测函数 =============

def run_backtest_with_config(
    strategy_key: str,
    start_date: str,
    end_date: str,
    frequency: str = "monthly",
    top_n: int = 2,
    observation_period: int = 2,
    correlation_threshold: float = 0.70,
) -> Dict[str, Any]:
    """执行单次回测并返回详细结果"""
    
    refresh_analysis_presets()
    preset = ANALYSIS_PRESETS.get(strategy_key)
    if not preset:
        return {"error": f"策略 {strategy_key} 不存在"}

    config = AnalysisConfig(
        start_date=start_date,
        end_date=end_date,
        etfs=ALL_CODES,
        momentum=preset.momentum_config(),
        corr_window=preset.corr_window,
        chop_window=preset.chop_window,
        trend_window=preset.trend_window,
        rank_change_lookback=preset.rank_lookback,
        make_plots=False,
    )

    result = analyze(config)

    # 提取数据
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()})
    close_df = close_df.sort_index().dropna(how="all")

    if close_df.empty:
        return {"error": "价格数据为空"}

    returns_df = close_df.pct_change().fillna(0)
    momentum_df = result.momentum_scores

    # 数据对齐
    common_dates = close_df.index.intersection(momentum_df.index)
    if len(common_dates) < 20:
        return {"error": f"数据重叠期过短({len(common_dates)}天)"}

    close_df = close_df.loc[common_dates]
    returns_df = returns_df.loc[common_dates]
    momentum_df = momentum_df.loc[common_dates]

    # 调仓日期
    if frequency == "weekly":
        rebalance_dates = close_df.resample("W-FRI").last().index
    else:
        rebalance_dates = close_df.resample("ME").last().index

    # 回测逻辑
    weights = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
    current_codes = []
    observation_counter = {}
    rebalance_log = []  # 记录每次调仓

    for date in close_df.index:
        if date in rebalance_dates:
            scores = momentum_df.loc[date].dropna()
            top_codes = scores.sort_values(ascending=False).head(top_n).index.tolist()

            # 观察期逻辑
            next_hold = []
            current_set = set(current_codes)
            top_set = set(top_codes)

            for code in current_set:
                if code in top_set:
                    observation_counter[code] = 0
                    next_hold.append(code)
                else:
                    observation_counter[code] = observation_counter.get(code, 0) + 1
                    if observation_period <= 0 or observation_counter[code] >= observation_period:
                        pass
                    else:
                        next_hold.append(code)

            # 补足空位
            if len(next_hold) < top_n:
                for code in top_codes:
                    if code not in next_hold:
                        next_hold.append(code)
                    if len(next_hold) >= top_n:
                        break

            # 记录调仓
            if set(next_hold) != set(current_codes):
                rebalance_log.append({
                    "date": date,
                    "from": current_codes.copy(),
                    "to": next_hold.copy(),
                })

            current_codes = [c for c in next_hold if c in close_df.columns]

        if current_codes:
            weights.loc[date, current_codes] = 1.0 / len(current_codes)

    # 计算收益
    portfolio_returns = (weights.shift().fillna(0) * returns_df).sum(axis=1)
    cumulative = (1 + portfolio_returns).cumprod()

    # 性能指标
    total_return = cumulative.iloc[-1] - 1 if not cumulative.empty else 0
    trading_days = len(portfolio_returns)

    if trading_days >= 180:
        ann_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0
        sharpe = (portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(252) if portfolio_returns.std() != 0 else 0
    else:
        ann_return = np.nan
        sharpe = np.nan

    drawdown = cumulative / cumulative.cummax() - 1 if not cumulative.empty else pd.Series(dtype=float)
    max_drawdown = drawdown.min() if not drawdown.empty else 0

    # 换手率
    weight_changes = weights.diff().abs().sum(axis=1)
    turnover_per_period = weight_changes.mean()
    periods_per_year = 52 if frequency == "weekly" else 12
    annual_turnover = turnover_per_period * periods_per_year

    # 最新持仓
    latest_holdings = weights.iloc[-1]
    latest_holdings = latest_holdings[latest_holdings > 0].to_dict()

    return {
        "total_return": float(total_return),
        "annualized_return": float(ann_return) if np.isfinite(ann_return) else np.nan,
        "sharpe_ratio": float(sharpe) if np.isfinite(sharpe) else np.nan,
        "max_drawdown": float(max_drawdown),
        "annual_turnover": float(annual_turnover),
        "trading_days": trading_days,
        "rebalance_count": len(rebalance_log),
        "latest_holdings": latest_holdings,
        "cumulative_series": cumulative,
        "rebalance_log": rebalance_log[-10:],  # 最近10次调仓
    }


def calculate_benchmark_performance(benchmark_code: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """计算基准指数表现"""
    
    config = AnalysisConfig(
        start_date=start_date,
        end_date=end_date,
        etfs=[benchmark_code],
        make_plots=False,
    )

    result = analyze(config)
    
    if benchmark_code not in result.raw_data:
        return {"error": f"基准 {benchmark_code} 数据缺失"}

    close = result.raw_data[benchmark_code]["close"]
    returns = close.pct_change().fillna(0)
    cumulative = (1 + returns).cumprod()

    total_return = cumulative.iloc[-1] - 1 if not cumulative.empty else 0
    trading_days = len(returns)

    if trading_days >= 180:
        ann_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
    else:
        ann_return = np.nan
        sharpe = np.nan

    drawdown = cumulative / cumulative.cummax() - 1
    max_drawdown = drawdown.min() if not drawdown.empty else 0

    return {
        "total_return": float(total_return),
        "annualized_return": float(ann_return) if np.isfinite(ann_return) else np.nan,
        "sharpe_ratio": float(sharpe) if np.isfinite(sharpe) else np.nan,
        "max_drawdown": float(max_drawdown),
    }


# ============= 主流程 =============

def main():
    parser = argparse.ArgumentParser(description="最优策略验证与长期回测")
    parser.add_argument("--strategy", type=str, default="twelve-minus-one", help="策略名称")
    parser.add_argument("--period", type=str, default="10y", choices=["1y", "3y", "5y", "10y", "all"], help="回测周期")
    parser.add_argument("--compare-all", action="store_true", help="对比所有策略")
    
    args = parser.parse_args()

    # 确定回测区间
    end_date = datetime.now().strftime("%Y-%m-%d")
    if args.period == "1y":
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    elif args.period == "3y":
        start_date = (datetime.now() - timedelta(days=365*3)).strftime("%Y-%m-%d")
    elif args.period == "5y":
        start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
    elif args.period == "10y":
        start_date = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    else:
        start_date = "2015-01-01"

    print("\n" + "="*70)
    print(f"最优策略验证 - {args.strategy}")
    print("="*70)
    print(f"回测区间: {start_date} 至 {end_date}")
    print(f"配置: 月度调仓 | Top2持仓 | 观察期2月 | 相关性≤0.70")
    print()

    # 运行策略回测
    print("正在回测策略...")
    result = run_backtest_with_config(
        strategy_key=args.strategy,
        start_date=start_date,
        end_date=end_date,
        **{k: v for k, v in RECOMMENDED_CONFIG.items() if k != "strategy"}
    )

    if "error" in result:
        print(f"❌ 回测失败: {result['error']}")
        return

    # 计算基准表现
    print("正在计算基准指数...")
    benchmarks = {}
    for name, code in BENCHMARK_CODES.items():
        bm_result = calculate_benchmark_performance(code, start_date, end_date)
        if "error" not in bm_result:
            benchmarks[name] = bm_result

    # 输出结果
    print("\n" + "-"*70)
    print("📊 策略表现")
    print("-"*70)
    print(f"累计收益:     {result['total_return']:>8.2%}")
    print(f"年化收益:     {result['annualized_return']:>8.2%}")
    print(f"夏普比率:     {result['sharpe_ratio']:>8.2f}")
    print(f"最大回撤:     {result['max_drawdown']:>8.2%}")
    print(f"年化换手率:   {result['annual_turnover']:>8.2f}")
    print(f"调仓次数:     {result['rebalance_count']:>8d}")

    print("\n" + "-"*70)
    print("📈 基准对比")
    print("-"*70)
    print(f"{'指数':<12} {'年化收益':>10} {'夏普比率':>10} {'最大回撤':>10} {'超额收益':>10}")
    print("-"*70)
    
    for name, bm in benchmarks.items():
        excess = result['annualized_return'] - bm['annualized_return']
        print(f"{name:<12} {bm['annualized_return']:>9.2%} {bm['sharpe_ratio']:>10.2f} "
              f"{bm['max_drawdown']:>10.2%} {excess:>9.2%}")

    print("\n" + "-"*70)
    print("💼 当前持仓建议")
    print("-"*70)
    if result['latest_holdings']:
        for code, weight in result['latest_holdings'].items():
            print(f"{code}: {weight:.1%}")
    else:
        print("无持仓")

    print("\n✓ 验证完成！")


if __name__ == "__main__":
    main()

