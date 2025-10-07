"""回测业务逻辑模块"""
from __future__ import annotations

from typing import List
import numpy as np
import pandas as pd

from ..analysis_presets import AnalysisPreset
from ..utils.colors import colorize
from ..utils.helpers import format_code_label as _format_label


def run_simple_backtest(result, preset: AnalysisPreset, top_n: int = 2) -> None:
    """基于动量排名的简易月频回测（等权持仓）"""
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()})
    close_df = close_df.sort_index().dropna(how="all")
    if close_df.empty:
        print(colorize("无法回测：价格数据为空。", "warning"))
        return

    returns_df = close_df.pct_change().fillna(0)
    aligned_scores = result.momentum_scores.reindex(close_df.index).ffill()
    if aligned_scores.dropna(how="all").empty:
        print(colorize("无法回测：动量得分为空。", "warning"))
        return
    momentum_df = aligned_scores

    rebalance_dates = close_df.resample("ME").last().index
    if rebalance_dates.empty:
        rebalance_dates = close_df.index

    weights = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
    current_codes: List[str] = []
    for date in close_df.index:
        if date in rebalance_dates:
            scores = momentum_df.loc[date].dropna()
            top_codes = scores.sort_values(ascending=False).head(top_n).index.tolist()
            current_codes = [code for code in top_codes if code in close_df.columns]
        if current_codes:
            weights.loc[date, current_codes] = 1.0 / len(current_codes)

    portfolio_returns = (weights.shift().fillna(0) * returns_df).sum(axis=1)
    cumulative = (1 + portfolio_returns).cumprod()
    total_return = cumulative.iloc[-1] - 1 if not cumulative.empty else 0
    periods_per_year = 252
    ann_return = (
        (1 + total_return) ** (periods_per_year / len(portfolio_returns)) - 1
        if len(portfolio_returns) > 0
        else 0
    )
    drawdown = cumulative / cumulative.cummax() - 1 if not cumulative.empty else pd.Series()
    max_drawdown = drawdown.min() if not drawdown.empty else 0
    sharpe = (
        (portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(periods_per_year)
        if portfolio_returns.std() != 0
        else 0
    )

    print(colorize("\n=== 简易回测结果 ===", "heading"))
    preset_line = f"预设: {preset.name} [{preset.key}]，每月调仓，持仓上限 {top_n} 条腿"
    print(colorize(preset_line, "menu_text"))
    print(colorize(f"累计收益: {total_return:.2%}", "value_positive" if total_return >= 0 else "value_negative"))
    print(colorize(f"年化收益: {ann_return:.2%}", "value_positive" if ann_return >= 0 else "value_negative"))
    print(colorize(f"最大回撤: {max_drawdown:.2%}", "danger"))
    print(colorize(f"夏普比率: {sharpe:.2f}", "accent" if sharpe > 0 else "warning"))

    if current_codes:
        last_weights = weights.iloc[-1]
        holding_lines: List[str] = []
        for code in current_codes:
            weight = float(last_weights.get(code, 0.0))
            label = _format_label(code)
            holding_lines.append(f"{label}: {weight:.1%}")
        print(colorize("最新持仓结构:", "heading"))
        print(colorize("; ".join(holding_lines), "menu_text"))

"""
回测业务逻辑模块

包含：
- 核心-卫星组合的按月调仓收益序列计算
- 常用绩效指标计算
"""
from __future__ import annotations

from typing import Sequence, Tuple, Dict, List

import numpy as np
import pandas as pd


def core_satellite_portfolio_returns(
    close_df: pd.DataFrame,
    momentum_df: pd.DataFrame,
    core_codes: Sequence[str],
    satellite_codes: Sequence[str],
    core_allocation: float,
    satellite_allocation: float,
    top_n: int,
) -> Tuple[pd.Series, Dict[str, object]]:
    if close_df.empty:
        return pd.Series(dtype=float), {}

    close_df = close_df.sort_index()
    returns_df = close_df.pct_change().fillna(0.0)
    aligned_momentum = momentum_df.reindex(close_df.index).ffill()

    rebalance_dates = close_df.resample("ME").last().index
    if rebalance_dates.empty:
        rebalance_dates = close_df.index

    universe = list(close_df.columns)
    weights = pd.DataFrame(0.0, index=close_df.index, columns=universe)

    core_set = [code for code in core_codes if code in universe]
    sat_set = [code for code in satellite_codes if code in universe]
    used_sat_codes: set[str] = set()
    current_weights: Dict[str, float] = {}

    for date in close_df.index:
        if date in rebalance_dates:
            new_weights: Dict[str, float] = {}
            if core_set and core_allocation > 0:
                per_core = core_allocation / len(core_set)
                for code in core_set:
                    new_weights[code] = new_weights.get(code, 0.0) + per_core
            selected_sat: List[str] = []
            if sat_set and satellite_allocation > 0:
                score_series = aligned_momentum.loc[date, sat_set].dropna()
                if not score_series.empty:
                    selected_sat = (
                        score_series.sort_values(ascending=False)
                        .head(max(1, top_n))
                        .index.tolist()
                    )
                    used_sat_codes.update(selected_sat)
                    per_sat = satellite_allocation / len(selected_sat)
                    for code in selected_sat:
                        new_weights[code] = new_weights.get(code, 0.0) + per_sat
            total_alloc = sum(new_weights.values())
            if total_alloc > 0:
                new_weights = {
                    code: value / total_alloc for code, value in new_weights.items() if value > 0
                }
            else:
                new_weights = {}
            current_weights = new_weights
        if current_weights:
            for code, weight in current_weights.items():
                weights.loc[date, code] = weight

    shifted_weights = weights.shift().ffill().fillna(0.0)
    portfolio_returns = (shifted_weights * returns_df).sum(axis=1)

    detail: Dict[str, object] = {
        "core_set": core_set,
        "satellite_set": sat_set,
        "used_satellite": sorted(used_sat_codes),
        "last_weights": current_weights.copy(),
    }
    return portfolio_returns, detail


def calculate_performance_metrics(returns: pd.Series) -> Dict[str, float]:
    returns = returns.dropna()
    days = len(returns)
    if days == 0:
        return {
            "days": 0,
            "total_return": float("nan"),
            "annualized": float("nan"),
            "volatility": float("nan"),
            "max_drawdown": float("nan"),
            "sharpe": float("nan"),
        }
    cumulative = (1 + returns).cumprod()
    total_return = cumulative.iloc[-1] - 1
    periods_per_year = 252
    annualized = (1 + total_return) ** (periods_per_year / days) - 1 if days > 0 else np.nan
    volatility = returns.std() * np.sqrt(periods_per_year) if days > 1 else np.nan
    drawdown = cumulative / cumulative.cummax() - 1
    max_drawdown = drawdown.min() if not drawdown.empty else np.nan
    sharpe = (
        (returns.mean() / returns.std()) * np.sqrt(periods_per_year)
        if returns.std() and returns.std() > 0
        else np.nan
    )
    return {
        "days": int(days),
        "total_return": float(total_return),
        "annualized": float(annualized) if np.isfinite(annualized) else float("nan"),
        "volatility": float(volatility) if np.isfinite(volatility) else float("nan"),
        "max_drawdown": float(max_drawdown) if np.isfinite(max_drawdown) else float("nan"),
        "sharpe": float(sharpe) if np.isfinite(sharpe) else float("nan"),
    }

