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


def run_core_satellite_multi_backtest(
    obtain_context_func,
    get_core_satellite_codes_func,
    core_satellite_returns_func,
    calc_metrics_func,
    format_label_func,
    colorize_func,
    render_table_func,
    wait_for_ack_func,
    last_state: dict | None = None,
) -> None:
    """Run core-satellite multi-horizon backtest (core equal-weight + satellite TopN) via injected callbacks."""
    context = obtain_context_func(last_state, allow_reuse=bool(last_state))
    if not context:
        return
    result = context["result"]
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()})
    close_df = close_df.sort_index().dropna(how="all")
    if close_df.empty:
        print(colorize_func("无法回测：价格数据为空。", "warning"))
        return
    momentum_df = result.momentum_scores
    if momentum_df.empty:
        print(colorize_func("无法回测：动量得分为空。", "warning"))
        return

    core_codes, satellite_codes = get_core_satellite_codes_func()
    if not core_codes and not satellite_codes:
        print(colorize_func("缺少核心/卫星券池定义，请先在券池预设中配置 core 与 satellite。", "warning"))
        return
    available_columns = set(close_df.columns)
    core_available = [code for code in core_codes if code in available_columns]
    satellite_available = [code for code in satellite_codes if code in available_columns]

    if not core_available:
        print(colorize_func("核心券池在当前分析结果中无可用标的，将仅使用卫星仓。", "warning"))
    if not satellite_available:
        print(colorize_func("卫星券池在当前分析结果中无可用标的，将仅使用核心仓。", "warning"))
    if not core_available and not satellite_available:
        print(colorize_func("核心与卫星券池均无可用标的，无法执行回测。", "danger"))
        return

    horizons = [
        ("近10年", pd.DateOffset(years=10)),
        ("近5年", pd.DateOffset(years=5)),
        ("近2年", pd.DateOffset(years=2)),
        ("近1年", pd.DateOffset(years=1)),
        ("近6个月", pd.DateOffset(months=6)),
        ("近3个月", pd.DateOffset(months=3)),
    ]

    end_date = close_df.index.max()
    rows_for_table: list[dict] = []
    last_holdings: dict[str, float] = {}
    warnings: list[str] = []

    for label, offset in horizons:
        start_candidate = end_date - offset
        mask = close_df.index >= start_candidate
        close_slice = close_df.loc[mask]
        if close_slice.empty:
            continue
        actual_start = close_slice.index[0]
        momentum_slice = momentum_df.reindex(close_slice.index).ffill()
        portfolio_returns, detail = core_satellite_returns_func(
            close_slice,
            momentum_slice,
            core_available,
            satellite_available,
            core_allocation=0.6,
            satellite_allocation=0.4,
            top_n=2,
        )
        metrics = calc_metrics_func(portfolio_returns)
        if metrics["days"] == 0:
            continue
        note_text = ""
        if metrics["days"] < 40:
            warnings.append(f"{label} 数据量仅 {metrics['days']} 个交易日，结果仅供参考。")
            note_text = "样本偏少"
        def _fmt_pct(x: float, digits=2):
            import numpy as _np
            return "-" if _np.isnan(x) else f"{x:.{digits}%}"
        def _fmt_num(x):
            import numpy as _np
            return "-" if _np.isnan(x) else f"{x:.2f}"
        row = {
            "label": label,
            "start": str(actual_start.date()),
            "end": str(end_date.date()),
            "days": str(metrics["days"]),
            "total": _fmt_pct(metrics["total_return"]),
            "annual": _fmt_pct(metrics["annualized"]),
            "vol": _fmt_pct(metrics["volatility"]),
            "maxdd": _fmt_pct(metrics["max_drawdown"]),
            "sharpe": _fmt_num(metrics["sharpe"]),
            "note": note_text,
        }
        import numpy as _np
        if not _np.isnan(metrics["total_return"]):
            if metrics["total_return"] >= 0:
                row["style_total"] = "value_positive"
                row["style_annual"] = "value_positive"
            else:
                row["style_total"] = "value_negative"
                row["style_annual"] = "value_negative"
        if not _np.isnan(metrics["max_drawdown"]):
            row["style_maxdd"] = "value_negative" if metrics["max_drawdown"] < 0 else "value_positive"
        if not _np.isnan(metrics["sharpe"]):
            row["style_sharpe"] = "accent" if metrics["sharpe"] > 0 else "warning"
        rows_for_table.append(row)
        last_holdings = detail.get("last_weights", {})

    print(colorize_func("\n=== 核心-卫星多区间回测 ===", "heading"))
    print(colorize_func("策略假设：核心仓 60% 等权持有核心券池全部标的；卫星仓 40% 择优持有卫星券池中动量得分排名前二，每月调仓。", "menu_hint"))
    print(colorize_func(f"核心仓标的数: {len(core_available)} | 卫星仓候选: {len(satellite_available)}", "menu_text"))

    print(render_table_func(rows_for_table))

    if last_holdings:
        sorted_holdings = sorted(last_holdings.items(), key=lambda item: item[1], reverse=True)
        holding_lines = []
        for code, weight in sorted_holdings:
            label = format_label_func(code)
            holding_lines.append(f"{label}: {weight:.1%}")
        print(colorize_func("\n最新权重（所有区间共用）:", "heading"))
        print(colorize_func("; ".join(holding_lines), "menu_text"))

    if warnings:
        print("")
        for message in warnings:
            print(colorize_func(f"提示: {message}", "warning"))
    wait_for_ack_func()


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

