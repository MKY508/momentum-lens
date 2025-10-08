#!/usr/bin/env python
"""
批量回测脚本 - 参数优化实验

功能：
1. 对多个策略进行参数网格搜索
2. 两阶段优化：粗筛 → 精调
3. 生成完整的性能评估报告

使用方法：
    python scripts/experiments/batch_backtest.py --phase 1  # 粗筛
    python scripts/experiments/batch_backtest.py --phase 2  # 精调
    python scripts/experiments/batch_backtest.py --full     # 完整流程
"""

import sys
import os
import argparse
import json
import time
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Tuple, Any
import multiprocessing as mp
from functools import partial

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

from momentum_cli.analysis import analyze, AnalysisConfig
from momentum_cli.analysis_presets import ANALYSIS_PRESETS, refresh_analysis_presets
from momentum_cli.business.backtest import run_simple_backtest


# ============= 实验参数配置 =============

# 现有的4个策略
STRATEGIES = ["slow-core", "blend-dual", "twelve-minus-one", "fast-rotation"]

# 参数空间
FREQUENCIES = ["monthly", "weekly"]  # 调仓频率
TOP_N_LIST = [1, 2, 3]  # 持仓数量
OBSERVATION_PERIODS = [0, 1, 2]  # 观察期
CORRELATION_THRESHOLDS = [0.6, 0.7, 0.8]  # 相关性过滤阈值

# 时间段划分（避免过拟合）
TRAIN_PERIOD = ("2015-01-01", "2020-12-31")  # 训练期
VALIDATION_PERIOD = ("2021-01-01", "2022-12-31")  # 验证期
TEST_PERIOD = ("2023-01-01", "2024-12-31")  # 测试期

# ETF候选池（核心+卫星）
CORE_CODES = ["510300.XSHG", "510880.XSHG", "511360.XSHG", "518880.XSHG", "513500.XSHG"]
SATELLITE_CODES = [
    "512980.XSHG",  # 能源ETF
    "512170.XSHG",  # 医疗ETF
    "512690.XSHG",  # 白酒ETF
    "512480.XSHG",  # 半导体ETF
    "515790.XSHG",  # 光伏ETF
    "516160.XSHG",  # 新能源车ETF
    "159995.XSHE",  # 芯片ETF
    "513100.XSHG",  # 纳指100
    "513050.XSHG",  # 中概互联
    "159949.XSHE",  # 创业板50
    "588000.XSHG",  # 科创50
    "512260.XSHG",  # 中证1000
    "510500.XSHG",  # 中证500
]

ALL_CODES = list(set(CORE_CODES + SATELLITE_CODES))


# ============= 回测执行函数 =============

def run_single_backtest(
    strategy_key: str,
    start_date: str,
    end_date: str,
    frequency: str,
    top_n: int,
    observation_period: int,
    correlation_threshold: float,
) -> Dict[str, Any]:
    """
    执行单次回测

    Returns:
        包含性能指标的字典
    """
    try:
        # 1. 加载预设
        refresh_analysis_presets()
        preset = ANALYSIS_PRESETS.get(strategy_key)
        if not preset:
            return {"error": f"策略 {strategy_key} 不存在"}

        # 2. 运行分析
        config = AnalysisConfig(
            start_date=start_date,
            end_date=end_date,
            etfs=ALL_CODES,
            momentum=preset.momentum_config(),
            corr_window=preset.corr_window,
            chop_window=preset.chop_window,
            trend_window=preset.trend_window,
            rank_change_lookback=preset.rank_lookback,
            make_plots=False,  # 批量回测不生成图表
        )

        result = analyze(config)

        # 3. 提取回测指标（模拟run_simple_backtest的计算）
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

        # 模拟等权持仓回测
        weights = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
        current_codes = []
        observation_counter = {}

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

        # 换手率计算
        weight_changes = weights.diff().abs().sum(axis=1)
        turnover_per_period = weight_changes.mean()
        periods_per_year = 252 if frequency == "daily" else (52 if frequency == "weekly" else 12)
        annual_turnover = turnover_per_period * periods_per_year

        return {
            "strategy": strategy_key,
            "period": f"{start_date}_{end_date}",
            "frequency": frequency,
            "top_n": top_n,
            "observation_period": observation_period,
            "correlation_threshold": correlation_threshold,
            "trading_days": trading_days,
            "total_return": float(total_return),
            "annualized_return": float(ann_return) if np.isfinite(ann_return) else np.nan,
            "sharpe_ratio": float(sharpe) if np.isfinite(sharpe) else np.nan,
            "max_drawdown": float(max_drawdown),
            "annual_turnover": float(annual_turnover),
            "error": None,
        }

    except Exception as e:
        return {
            "error": str(e),
            "strategy": strategy_key,
            "period": f"{start_date}_{end_date}",
        }


# ============= 阶段1：粗筛 =============

def phase1_coarse_screening() -> pd.DataFrame:
    """
    阶段1：粗粒度筛选
    - 4个策略 × 固定参数(月度/2只/观察期1/相关性0.7)
    - 只在训练期回测
    - 输出：4个结果，按夏普排序
    """
    print("\n" + "="*60)
    print("阶段1：粗筛 - 策略初选")
    print("="*60)
    print(f"测试策略数: {len(STRATEGIES)}")
    print(f"训练期: {TRAIN_PERIOD[0]} 至 {TRAIN_PERIOD[1]}")
    print()

    results = []

    for strategy in STRATEGIES:
        print(f"[{strategy}] 回测中...", end=" ", flush=True)
        result = run_single_backtest(
            strategy_key=strategy,
            start_date=TRAIN_PERIOD[0],
            end_date=TRAIN_PERIOD[1],
            frequency="monthly",  # 固定月度
            top_n=2,  # 固定2只
            observation_period=1,  # 固定观察期1
            correlation_threshold=0.7,  # 固定相关性0.7
        )
        results.append(result)

        if result.get("error"):
            print(f"❌ 失败: {result['error']}")
        else:
            print(f"✓ 夏普={result['sharpe_ratio']:.2f}")

    df = pd.DataFrame(results)
    df_sorted = df.sort_values("sharpe_ratio", ascending=False, na_position="last")

    print("\n" + "-"*60)
    print("粗筛结果（按夏普排序）：")
    print(df_sorted[["strategy", "sharpe_ratio", "annualized_return", "max_drawdown"]].to_string(index=False))

    return df_sorted


# ============= 阶段2：精调 =============

def phase2_fine_tuning(phase1_results: pd.DataFrame, top_k: int = 3) -> pd.DataFrame:
    """
    阶段2：精细化调优
    - 选取阶段1前K个策略
    - 变化参数：频率(2) × 持仓数(3) × 观察期(3) × 相关性(3) = 54种/策略
    - 在训练/验证/测试期全部回测
    """
    print("\n" + "="*60)
    print(f"阶段2：精调 - 参数优化（Top {top_k}策略）")
    print("="*60)

    # 选出Top K策略
    top_strategies = phase1_results.head(top_k)["strategy"].tolist()
    print(f"入选策略: {', '.join(top_strategies)}")
    print()

    # 生成参数组合
    param_combinations = []
    for strategy in top_strategies:
        for freq in FREQUENCIES:
            for top_n in TOP_N_LIST:
                for obs_period in OBSERVATION_PERIODS:
                    for corr_thresh in CORRELATION_THRESHOLDS:
                        param_combinations.append({
                            "strategy": strategy,
                            "frequency": freq,
                            "top_n": top_n,
                            "observation_period": obs_period,
                            "correlation_threshold": corr_thresh,
                        })

    print(f"总组合数: {len(param_combinations)}")
    print(f"预计耗时: ~{len(param_combinations) * 0.5:.0f}秒")
    print()

    # 在三个时期分别回测
    all_results = []

    for i, params in enumerate(param_combinations, 1):
        print(f"[{i}/{len(param_combinations)}] {params['strategy']} | "
              f"频率={params['frequency']} | "
              f"持仓={params['top_n']} | "
              f"观察期={params['observation_period']} | "
              f"相关性={params['correlation_threshold']}", flush=True)

        # 训练期
        result_train = run_single_backtest(
            strategy_key=params["strategy"],
            start_date=TRAIN_PERIOD[0],
            end_date=TRAIN_PERIOD[1],
            frequency=params["frequency"],
            top_n=params["top_n"],
            observation_period=params["observation_period"],
            correlation_threshold=params["correlation_threshold"],
        )

        # 验证期
        result_val = run_single_backtest(
            strategy_key=params["strategy"],
            start_date=VALIDATION_PERIOD[0],
            end_date=VALIDATION_PERIOD[1],
            frequency=params["frequency"],
            top_n=params["top_n"],
            observation_period=params["observation_period"],
            correlation_threshold=params["correlation_threshold"],
        )

        # 测试期
        result_test = run_single_backtest(
            strategy_key=params["strategy"],
            start_date=TEST_PERIOD[0],
            end_date=TEST_PERIOD[1],
            frequency=params["frequency"],
            top_n=params["top_n"],
            observation_period=params["observation_period"],
            correlation_threshold=params["correlation_threshold"],
        )

        # 合并结果
        combined = {
            **params,
            "sharpe_train": result_train.get("sharpe_ratio", np.nan),
            "sharpe_val": result_val.get("sharpe_ratio", np.nan),
            "sharpe_test": result_test.get("sharpe_ratio", np.nan),
            "return_train": result_train.get("annualized_return", np.nan),
            "return_val": result_val.get("annualized_return", np.nan),
            "return_test": result_test.get("annualized_return", np.nan),
            "maxdd_train": result_train.get("max_drawdown", np.nan),
            "maxdd_val": result_val.get("max_drawdown", np.nan),
            "maxdd_test": result_test.get("max_drawdown", np.nan),
            "turnover": result_test.get("annual_turnover", np.nan),
        }

        all_results.append(combined)

    df = pd.DataFrame(all_results)

    # 计算综合评分
    df["stability"] = 1 - (df[["sharpe_train", "sharpe_val", "sharpe_test"]].std(axis=1) /
                           df[["sharpe_train", "sharpe_val", "sharpe_test"]].mean(axis=1)).fillna(0)
    df["score"] = (
        0.4 * df["sharpe_test"].fillna(0) +
        0.3 * df["stability"].fillna(0) +
        0.2 * (1 - df["maxdd_test"].abs() / 0.30).fillna(0) +
        0.1 * (1 - df["turnover"] / 3.0).fillna(0)
    )

    df_sorted = df.sort_values("score", ascending=False)

    print("\n" + "-"*60)
    print("精调结果（Top 10）：")
    print(df_sorted.head(10)[[
        "strategy", "frequency", "top_n", "observation_period",
        "sharpe_test", "maxdd_test", "turnover", "score"
    ]].to_string(index=False))

    return df_sorted


# ============= 主流程 =============

def main():
    parser = argparse.ArgumentParser(description="批量回测 - 参数优化实验")
    parser.add_argument("--phase", type=int, choices=[1, 2], help="指定运行阶段（1=粗筛, 2=精调）")
    parser.add_argument("--full", action="store_true", help="完整流程（阶段1+2）")
    parser.add_argument("--output", type=str, default="results", help="结果输出目录")

    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.phase == 1 or args.full:
        # 阶段1：粗筛
        phase1_results = phase1_coarse_screening()
        phase1_path = output_dir / f"phase1_coarse_{timestamp}.csv"
        phase1_results.to_csv(phase1_path, index=False, encoding="utf-8-sig")
        print(f"\n✓ 阶段1结果已保存: {phase1_path}")

    if args.phase == 2 or args.full:
        # 阶段2：精调
        if not args.full:
            # 如果单独运行阶段2，需要加载阶段1结果
            phase1_files = sorted(output_dir.glob("phase1_coarse_*.csv"))
            if not phase1_files:
                print("❌ 错误：未找到阶段1结果文件，请先运行阶段1")
                return
            phase1_results = pd.read_csv(phase1_files[-1])
            print(f"加载阶段1结果: {phase1_files[-1]}")

        phase2_results = phase2_fine_tuning(phase1_results, top_k=3)
        phase2_path = output_dir / f"phase2_fine_{timestamp}.csv"
        phase2_results.to_csv(phase2_path, index=False, encoding="utf-8-sig")
        print(f"\n✓ 阶段2结果已保存: {phase2_path}")

        # 输出最优配置
        best = phase2_results.iloc[0]
        print("\n" + "="*60)
        print("🏆 最优配置")
        print("="*60)
        print(f"策略: {best['strategy']}")
        print(f"调仓频率: {best['frequency']}")
        print(f"持仓数量: {int(best['top_n'])}")
        print(f"观察期: {int(best['observation_period'])}个月")
        print(f"相关性阈值: {best['correlation_threshold']:.2f}")
        print(f"\n测试期夏普: {best['sharpe_test']:.2f}")
        print(f"测试期年化收益: {best['return_test']:.2%}")
        print(f"最大回撤: {best['maxdd_test']:.2%}")
        print(f"年化换手率: {best['turnover']:.2f}")
        print(f"综合得分: {best['score']:.4f}")

    print("\n✓ 实验完成！")


if __name__ == "__main__":
    main()
