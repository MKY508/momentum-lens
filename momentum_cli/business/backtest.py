"""回测业务逻辑模块"""
from __future__ import annotations

from typing import List
import numpy as np
import pandas as pd

from ..analysis_presets import AnalysisPreset
from ..utils.colors import colorize
from ..utils.helpers import format_code_label as _format_label
from ..metadata import get_label as _get_label


def select_assets_with_constraints(
    momentum_scores: pd.Series,
    momentum_percentiles: pd.Series,
    correlation_matrix: pd.DataFrame,
    top_n: int,
    *,
    min_percentile: float = 0.6,
    max_correlation: float = 0.85,
    allow_shrink: bool = True,
) -> tuple[list[str], dict]:
    """
    在约束条件下选择资产

    约束优先级:
    1. 动量分位数 >= min_percentile (硬约束)
    2. 两两相关性 <= max_correlation (软约束，尽力而为)
    3. 若无法满足，优先保证动量阈值，然后缩腿

    Returns:
        (selected_codes, diagnostics)
    """
    diagnostics = {
        "candidates_count": 0,
        "selected_count": 0,
        "correlation_violations": 0,
        "shrunk": False,
    }

    # 1. 过滤动量分位数（允许传入 0-1 或 0-100 两种尺度）
    if momentum_percentiles is None or momentum_percentiles.empty:
        return [], diagnostics

    threshold = float(min_percentile)
    if threshold > 1.0:
        threshold = threshold / 100.0

    candidates = momentum_percentiles[momentum_percentiles >= threshold]
    diagnostics["candidates_count"] = len(candidates)

    if len(candidates) == 0:
        # 无合格候选，返回空
        return [], diagnostics

    # 2. 按动量得分排序
    candidates_sorted = candidates.sort_values(ascending=False)

    # 3. 贪心选择：逐个添加，检查相关性
    selected = []
    for code in candidates_sorted.index:
        if len(selected) >= top_n:
            break

        # 检查与已选资产的相关性
        if len(selected) > 0 and correlation_matrix is not None:
            correlations = []
            for s in selected:
                if code in correlation_matrix.index and s in correlation_matrix.columns:
                    corr = correlation_matrix.loc[code, s]
                    if pd.notna(corr):
                        correlations.append(abs(corr))

            if correlations and max(correlations) > max_correlation:
                diagnostics["correlation_violations"] += 1
                continue  # 相关性过高，跳过

        selected.append(code)

    diagnostics["selected_count"] = len(selected)
    if len(selected) < top_n:
        diagnostics["shrunk"] = True

    return selected, diagnostics


def run_simple_backtest(
    result,
    preset: AnalysisPreset,
    top_n: int = 2,
    *,
    frequency: str = "monthly",  # monthly/weekly/daily
    observation_period: int = 0,  # 连续掉队N个调仓周期后才换仓
    commission_rate: float = 0.00005,  # 万0.5
    slippage_rate: float = 0.0005,  # 0.05%滑点
    min_momentum_percentile: float = 0.6,  # 最低动量分位数（0-1范围）
    max_correlation: float = 0.85,  # 最大相关性
    use_correlation_filter: bool = True,  # 是否使用相关性过滤
) -> None:
    """基于动量排名的可配置简易回测（等权持仓，含可选观察期与交易成本）"""
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()})
    close_df = close_df.sort_index().dropna(how="all")
    if close_df.empty:
        print(colorize("无法回测：价格数据为空。", "warning"))
        return

    returns_df = close_df.pct_change().fillna(0)

    # 对齐动量得分：只回测有有效动量得分的期间
    momentum_df = result.momentum_scores
    if momentum_df.empty:
        print(colorize("无法回测：动量得分为空。", "warning"))
        return

    # 找到动量数据和价格数据的重叠期间
    common_dates = close_df.index.intersection(momentum_df.index)
    if len(common_dates) < 20:
        print(colorize(f"⚠️  动量数据与价格数据重叠期间过短（{len(common_dates)}天），无法回测。", "warning"))
        print(colorize(f"   价格数据范围: {close_df.index[0].date()} - {close_df.index[-1].date()}", "menu_hint"))
        print(colorize(f"   动量数据范围: {momentum_df.index[0].date()} - {momentum_df.index[-1].date()}", "menu_hint"))
        return

    # 只对重叠期间进行回测
    close_df = close_df.loc[common_dates]
    returns_df = returns_df.loc[common_dates]
    momentum_df = momentum_df.loc[common_dates]

    # 获取动量分位数和相关性矩阵
    percentiles_df = None
    if hasattr(result, 'summary') and result.summary is not None and not result.summary.empty:
        if 'momentum_percentile' in result.summary.columns:
            percentiles_df = result.summary.set_index('etf')['momentum_percentile']

    # 相关性矩阵：兼容属性名 'correlation' 与 'correlation_matrix'
    correlation_matrix = getattr(result, 'correlation_matrix', None)
    if correlation_matrix is None:
        correlation_matrix = getattr(result, 'correlation', None)

    # 调仓频率
    if frequency == "weekly":
        rebalance_dates = close_df.resample("W-FRI").last().index
    elif frequency == "daily":
        rebalance_dates = close_df.index
    else:
        rebalance_dates = close_df.resample("ME").last().index
    if rebalance_dates.empty:
        rebalance_dates = close_df.index

    weights = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
    current_codes: List[str] = []
    # 观察期计数：code -> 连续未入选的周期数
    observation_counter: dict[str, int] = {}

    # 为计算换仓成本，记录上一期权重
    last_weights = pd.Series(0.0, index=close_df.columns)
    turnover_cost = pd.Series(0.0, index=close_df.index, dtype=float)

    for date in close_df.index:
        if date in rebalance_dates:
            # 使用新的选仓器
            scores = momentum_df.loc[date].dropna()

            # 获取当期分位数
            current_percentiles = None
            if percentiles_df is not None:
                # 简化：使用最新的分位数（实际应该按日期对齐）
                current_percentiles = percentiles_df.reindex(scores.index)

            if use_correlation_filter and current_percentiles is not None:
                # 使用约束选仓器
                top_codes, diag = select_assets_with_constraints(
                    scores,
                    current_percentiles,
                    correlation_matrix,
                    top_n,
                    min_percentile=min_momentum_percentile,
                    max_correlation=max_correlation,
                )
                # 兜底：若因阈值或相关性导致空仓，则回退为简单TopN选择，避免全程零权重
                if not top_codes:
                    top_codes = scores.sort_values(ascending=False).head(top_n).index.tolist()
            else:
                # 简单排序选择
                top_codes = scores.sort_values(ascending=False).head(top_n).index.tolist()

            # 观察期机制
            next_hold: list[str] = []
            current_set = set(current_codes)
            top_set = set(top_codes)

            # 维护/离开
            for code in list(current_set):
                if code in top_set:
                    observation_counter[code] = 0
                    next_hold.append(code)
                else:
                    observation_counter[code] = observation_counter.get(code, 0) + 1
                    if observation_period <= 0 or observation_counter[code] >= observation_period:
                        # 放弃该持仓
                        pass
                    else:
                        # 观察期内暂时保留
                        next_hold.append(code)

            # 补足空位
            if len(next_hold) < top_n:
                for code in top_codes:
                    if code not in next_hold:
                        next_hold.append(code)
                    if len(next_hold) >= top_n:
                        break

            # 修正只保留出现在数据列的代码
            current_codes = [c for c in next_hold if c in close_df.columns]

            # 根据新持仓设置等权目标
            if current_codes:
                target = pd.Series(0.0, index=close_df.columns)
                target.loc[current_codes] = 1.0 / len(current_codes)
            else:
                target = pd.Series(0.0, index=close_df.columns)

            # 计算换手成本（近似）：∑|Δw|*(佣金+滑点)
            delta = (target - last_weights).abs()
            cost_rate = commission_rate + slippage_rate
            turnover_cost.loc[date] = float(delta.sum() * cost_rate)
            last_weights = target

        # 非调仓日沿用上一目标
        if last_weights is not None:
            weights.loc[date, :] = last_weights

    # 组合收益，调仓日扣除换手成本
    portfolio_returns = (weights.shift().fillna(0) * returns_df).sum(axis=1)
    # 扣除成本（视为当天一次性扣减）
    portfolio_returns = portfolio_returns - turnover_cost

    cumulative = (1 + portfolio_returns).cumprod()
    total_return = cumulative.iloc[-1] - 1 if not cumulative.empty else 0
    periods_per_year = 252
    trading_days = len(portfolio_returns)

    # 只有足够长的样本才计算年化指标
    if trading_days >= 180:
        ann_return = (
            (1 + total_return) ** (periods_per_year / trading_days) - 1
            if trading_days > 0
            else 0
        )
        sharpe = (
            (portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(periods_per_year)
            if portfolio_returns.std() != 0
            else 0.0
        )
    else:
        ann_return = None
        sharpe = None

    drawdown = cumulative / cumulative.cummax() - 1 if not cumulative.empty else pd.Series(dtype=float)
    max_drawdown = drawdown.min() if not drawdown.empty else 0.0

    print(colorize("\n=== 简易回测结果 ===", "heading"))
    freq_cn = {"monthly": "每月", "weekly": "每周", "daily": "每日"}.get(frequency, "每月")
    preset_line = f"预设: {preset.name} [{preset.key}]，{freq_cn}调仓，持仓上限 {top_n} 条腿"
    print(colorize(preset_line, "menu_text"))
    print(colorize(f"回测样本: {trading_days} 个交易日", "menu_hint"))
    if observation_period > 0:
        print(colorize(f"观察期: 连续 {observation_period} 个调仓周期掉队才换仓", "menu_hint"))
    print(colorize(f"交易成本假设: 佣金 {commission_rate:.4%} + 滑点 {slippage_rate:.4%}", "menu_hint"))
    print(colorize(f"累计收益: {total_return:.2%}", "value_positive" if total_return >= 0 else "value_negative"))

    if ann_return is not None and sharpe is not None:
        print(colorize(f"年化收益: {ann_return:.2%}", "value_positive" if ann_return >= 0 else "value_negative"))
        print(colorize(f"夏普比率: {sharpe:.2f}", "accent" if sharpe > 0 else "warning"))
    else:
        print(colorize(f"⚠️  样本期过短({trading_days}天 < 180天)，年化指标不可靠，已隐藏", "warning"))

    print(colorize(f"最大回撤: {max_drawdown:.2%}", "danger"))

    if len(current_codes) > 0:
        last_w = weights.iloc[-1]
        holding_lines: List[str] = []
        for code in current_codes:
            weight = float(last_w.get(code, 0.0))
            label = _format_label(code, _get_label)
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

    # 额外增加：近1个月（上一个完整自然月，不含当前未完整月份）
    try:
        prev_month_end = (end_date - pd.offsets.MonthBegin(1)) - pd.Timedelta(days=1)
        prev_month_start = (prev_month_end.replace(day=1))
        mask_month = (close_df.index >= prev_month_start) & (close_df.index <= prev_month_end)
        close_slice = close_df.loc[mask_month]
        if not close_slice.empty:
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
            if metrics["days"] > 0:
                def _fmt_pct(x: float, digits=2):
                    import numpy as _np
                    return "-" if _np.isnan(x) else f"{x:.{digits}%}"
                def _fmt_num(x):
                    import numpy as _np
                    return "-" if _np.isnan(x) else f"{x:.2f}"
                row = {
                    "label": "近1个月",
                    "start": str(close_slice.index.min().date()),
                    "end": str(close_slice.index.max().date()),
                    "days": str(metrics["days"]),
                    "total": _fmt_pct(metrics["total_return"]),
                    "annual": _fmt_pct(metrics["annualized"]),
                    "vol": _fmt_pct(metrics["volatility"]),
                    "maxdd": _fmt_pct(metrics["max_drawdown"]),
                    "sharpe": _fmt_num(metrics["sharpe"]),
                    "note": "",
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
    except Exception:
        pass

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

    # 只对价格数据和动量数据的重叠期间进行回测
    common_dates = close_df.index.intersection(momentum_df.index)
    if len(common_dates) < 20:
        return pd.Series(dtype=float), {}

    close_df = close_df.loc[common_dates].sort_index()
    returns_df = close_df.pct_change().fillna(0.0)
    aligned_momentum = momentum_df.loc[common_dates]

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


def run_core_satellite_custom_backtest(
    obtain_context_func,
    get_core_satellite_codes_func,
    format_label_func,
    colorize_func,
    render_table_func,
    wait_for_ack_func,
    last_state: dict | None = None,
    *,
    mode: str = "core+sat",  # core+sat/core/sat
    chop_threshold: float = 38.0,
    ma_window: int = 200,
    # 固定核心底座构成（总计60%）：
    core_map: dict | None = None,  # 可传入覆盖 {code: weight}
    sat_allocation_trend: float = 0.40,
    sat_allocation_defense: float = 0.15,
    defense_to_cash: bool = True,
    top_n_trend: int = 2,
    top_n_defense: int = 1,
) -> None:
    """核心-卫星（自定义）回测：
    - 市场代理：优先 510300.XSHG；否则使用第一个可用的核心标的
    - 趋势判定：MA200 上方且 CHOP < 阈值
    - 趋势时卫星持仓：Top N = 2，合计 40%
    - 防守时卫星持仓：Top N = 1，合计 15%（默认未使用部分留作现金）
    - 核心仓：60% 等权持有核心券池全部标的
    """
    context = obtain_context_func(last_state, allow_reuse=False)
    if not context:
        return
    result = context["result"]
    momentum_df = result.momentum_scores
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()}).sort_index().dropna(how="all")
    if close_df.empty or momentum_df.empty:
        print(colorize_func("无法回测：数据为空。", "warning"))
        return

    # 对齐动量与价格
    common_dates = close_df.index.intersection(momentum_df.index)
    if len(common_dates) < 20:
        print(colorize_func("重叠区间过短，无法回测。", "warning"))
        return
    close_df = close_df.loc[common_dates]
    returns_df = close_df.pct_change().fillna(0.0)
    momentum_df = momentum_df.loc[common_dates]

    rebalance_dates = close_df.resample("ME").last().index
    if rebalance_dates.empty:
        rebalance_dates = close_df.index

    core_codes, satellite_codes = get_core_satellite_codes_func()
    available = set(close_df.columns)
    core_set = [c for c in core_codes if c in available]
    sat_set = [c for c in satellite_codes if c in available]

    if not core_set and not sat_set:
        print(colorize_func("核心与卫星券池均无可用标的，无法执行回测。", "danger"))
        return

    # 市场代理：510300 优先
    market_code = "510300.XSHG" if "510300.XSHG" in close_df.columns else (core_set[0] if core_set else None)
    market_close = close_df[market_code] if market_code else None
    ma200 = market_close.rolling(window=ma_window, min_periods=1).mean() if market_close is not None else None

    # CHOP 使用分析结果中已有的序列（若可用）
    chop_series = None
    try:
        chop_dict = getattr(result, "chop", None)
        if chop_dict and market_code in chop_dict:
            chop_series = chop_dict[market_code].reindex(close_df.index)
    except Exception:
        chop_series = None

    weights = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
    current_w: dict[str, float] = {}
    def _get_core_map_clean_default() -> dict:
        # 默认核心底座：总计 60%
        return {
            "510300.XSHG": 0.20,  # A股宽基 20%
            "510880.XSHG": 0.10,  # 红利因子 10%
            "511360.XSHG": 0.15,  # 短久期固收 15%
            "518880.XSHG": 0.10,  # 黄金 10%
            "513500.XSHG": 0.05,  # 美股基线 5%
        }


    #
    def _get_core_map_default() -> dict:
        # cleaned fallback (unused)
        return {}

    def _alloc_core_fixed(target: dict[str, float]) -> None:
        if mode in {"core+sat", "core", "core-only"}:
            cm = dict(_get_core_map_clean_default())
            if core_map:
                cm.update({k: float(v) for k, v in core_map.items()})
            for code, w in cm.items():
                if code in close_df.columns and w > 0:
                    target[code] = target.get(code, 0.0) + float(w)

    def _alloc_satellite(target: dict[str, float], date, allocation: float, top_n: int) -> None:
        if mode in {"core+sat", "sat", "satellite", "sat-only"}:
            if not sat_set or allocation <= 0:
                return
            scores = momentum_df.loc[date, sat_set].dropna()
            if scores.empty:
                return
            picks = scores.sort_values(ascending=False).head(max(1, top_n)).index.tolist()
            per = allocation / len(picks)
            for code in picks:
                target[code] = target.get(code, 0.0) + per
        else:
            return

    for date in close_df.index:
        if date in rebalance_dates:
            target: dict[str, float] = {}
            # 市场状态
            above_ma = False
            in_trend = False
            if market_close is not None and ma200 is not None:
                if not pd.isna(market_close.loc[date]) and not pd.isna(ma200.loc[date]):
                    above_ma = bool(market_close.loc[date] > ma200.loc[date])

            if chop_series is not None and not pd.isna(chop_series.loc[date]):
                in_trend = chop_series.loc[date] < float(chop_threshold)
            else:
                # 无 CHOP 时仅以年线判定趋势
                in_trend = above_ma

            # 配置卫星参数：纯卫星模式不启用动态防守/CHOP/MA200，始终使用趋势期设置
            if mode in {"sat", "sat-only"}:
                sat_alloc = sat_allocation_trend
                sat_top_n = top_n_trend
            elif above_ma and in_trend:
                sat_alloc = sat_allocation_trend
                sat_top_n = top_n_trend
            else:
                sat_alloc = sat_allocation_defense
                sat_top_n = top_n_defense

            # 分配核心与卫星
            _alloc_core_fixed(target)
            _alloc_satellite(target, date, sat_alloc, sat_top_n)

            # 是否把未使用的卫星差额回流核心：默认否（留现金）
            # target 权重和可能 < 1
            current_w = target

        if current_w:
            for code, w in current_w.items():
                weights.loc[date, code] = w

    shifted = weights.shift().ffill().fillna(0.0)
    portfolio_returns = (shifted * returns_df).sum(axis=1)

    # 按多区间输出
    horizons = [
        ("近10年", pd.DateOffset(years=10)),
        ("近5年", pd.DateOffset(years=5)),
        ("近2年", pd.DateOffset(years=2)),
        ("近1年", pd.DateOffset(years=1)),
        ("近6个月", pd.DateOffset(months=6)),
        ("近3个月", pd.DateOffset(months=3)),
    ]

    end_date = close_df.index.max()
    rows: list[dict] = []
    last_weights = current_w.copy()

    for label, offset in horizons:
        start_candidate = end_date - offset
        mask = close_df.index >= start_candidate
        if not mask.any():
            continue
        slice_returns = portfolio_returns.loc[mask]
        metrics = calculate_performance_metrics(slice_returns)
        if metrics["days"] == 0:
            continue
        def _fmt_pct(x: float, digits=2):
            import numpy as _np
            return "-" if _np.isnan(x) else f"{x:.{digits}%}"
        def _fmt_num(x):
            import numpy as _np
            return "-" if _np.isnan(x) else f"{x:.2f}"
        row = {
            "label": label,
            "start": str(slice_returns.index.min().date()),
            "end": str(slice_returns.index.max().date()),
            "days": str(metrics["days"]),
            "total": _fmt_pct(metrics["total_return"]),
            "annual": _fmt_pct(metrics["annualized"]),
            "vol": _fmt_pct(metrics["volatility"]),
            "maxdd": _fmt_pct(metrics["max_drawdown"]),
            "sharpe": _fmt_num(metrics["sharpe"]),
            "note": "",
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
        rows.append(row)

    print(colorize_func("\n=== 核心-卫星（自定义）多区间回测 ===", "heading"))
    # 额外增加：近1个月（上一个完整自然月，不含当前未完整月份）
    try:
        prev_month_end = (end_date - pd.offsets.MonthBegin(1)) - pd.Timedelta(days=1)
        prev_month_start = (prev_month_end.replace(day=1))
        mask_month = (close_df.index >= prev_month_start) & (close_df.index <= prev_month_end)
        slice_returns = portfolio_returns.loc[mask_month]
        metrics = calculate_performance_metrics(slice_returns)
        if metrics["days"] > 0:
            def _fmt_pct(x: float, digits=2):
                import numpy as _np
                return "-" if _np.isnan(x) else f"{x:.{digits}%}"
            def _fmt_num(x):
                import numpy as _np
                return "-" if _np.isnan(x) else f"{x:.2f}"
            row = {
                "label": "近1个月",
                "start": str(slice_returns.index.min().date()),
                "end": str(slice_returns.index.max().date()),
                "days": str(metrics["days"]),
                "total": _fmt_pct(metrics["total_return"]),
                "annual": _fmt_pct(metrics["annualized"]),
                "vol": _fmt_pct(metrics["volatility"]),
                "maxdd": _fmt_pct(metrics["max_drawdown"]),
                "sharpe": _fmt_num(metrics["sharpe"]),
                "note": "",
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
            rows.append(row)
    except Exception:
        pass

    print(colorize_func("策略：核心 60% 等权；趋势时卫星 40% 择优 2 条腿；防守时卫星 15% 择优 1 条腿；未用部分留现金。", "menu_hint"))
    print(colorize_func(f"核心仓标的数: {len(core_set)} | 卫星仓候选: {len(sat_set)}", "menu_text"))
    print(render_table_func(rows))

    if last_weights:
        sorted_holdings = sorted(last_weights.items(), key=lambda kv: kv[1], reverse=True)
        lines = [f"{format_label_func(code)}: {w:.1%}" for code, w in sorted_holdings]
        print(colorize_func("\n最新权重:", "heading"))
        print(colorize_func("; ".join(lines), "menu_text"))

    wait_for_ack_func()




def run_core_satellite_enhanced_backtest(
    obtain_context_func,
    get_core_satellite_codes_func,
    format_label_func,
    colorize_func,
    render_table_func,
    wait_for_ack_func,
    last_state: dict | None = None,
    *,
    # 核心配置
    core_allocation: float = 0.6,
    satellite_allocation: float = 0.4,
    top_n: int = 2,
    # 止损配置
    enable_stop_loss: bool = True,
    stop_loss_pct: float = 0.15,  # 从最高点回撤15%止损
    # 再平衡配置
    enable_rebalance: bool = True,
    rebalance_threshold: float = 0.05,  # 偏离5%时再平衡
    # 防御配置
    enable_defense: bool = True,
    defense_ma_window: int = 200,  # MA200作为趋势判断
    defense_satellite_allocation: float = 0.20,  # 防御时卫星仓降至20%
) -> None:
    """
    核心-卫星增强回测（含止损、再平衡、防御机制）

    策略逻辑：
    1. 核心仓：60%等权持有核心券池全部标的
    2. 卫星仓：40%择优持有卫星券池中动量得分排名前N
    3. 止损：单只ETF从最高点回撤>15%时止损
    4. 再平衡：每月检查，偏离>5%时再平衡
    5. 防御：大盘MA200以下时，降低卫星仓至20%
    """

    context = obtain_context_func(last_state, allow_reuse=False)
    if not context:
        return

    result = context["result"]
    momentum_df = result.momentum_scores
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()}).sort_index().dropna(how="all")

    if close_df.empty or momentum_df.empty:
        print(colorize_func("无法回测：数据为空。", "warning"))
        return

    # 对齐动量与价格
    common_dates = close_df.index.intersection(momentum_df.index)
    if len(common_dates) < 20:
        print(colorize_func("重叠区间过短，无法回测。", "warning"))
        return

    close_df = close_df.loc[common_dates].sort_index()
    returns_df = close_df.pct_change().fillna(0.0)
    momentum_df = momentum_df.loc[common_dates]

    # 获取核心和卫星券池
    core_codes, satellite_codes = get_core_satellite_codes_func()
    available = set(close_df.columns)
    core_set = [c for c in core_codes if c in available]
    sat_set = [c for c in satellite_codes if c in available]

    if not core_set and not sat_set:
        print(colorize_func("核心与卫星券池均无可用标的，无法执行回测。", "danger"))
        return

    # 调仓日期（月末）
    rebalance_dates = close_df.resample("ME").last().index
    if rebalance_dates.empty:
        rebalance_dates = close_df.index

    # 市场代理（用于防御判断）
    market_code = "510300.XSHG" if "510300.XSHG" in close_df.columns else (core_set[0] if core_set else None)
    market_close = close_df[market_code] if market_code else None
    ma200 = market_close.rolling(window=defense_ma_window, min_periods=1).mean() if market_close is not None else None

    # 初始化
    weights = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
    current_w: dict[str, float] = {}
    high_water_mark: dict[str, float] = {}  # 记录每只ETF的最高点
    stop_loss_triggered: set[str] = set()  # 已触发止损的ETF
    rebalance_log: list[dict] = []  # 调仓记录

    for date in close_df.index:
        # 更新最高点
        for code in close_df.columns:
            if code not in high_water_mark:
                high_water_mark[code] = close_df.loc[date, code]
            else:
                high_water_mark[code] = max(high_water_mark[code], close_df.loc[date, code])

        # 检查止损
        if enable_stop_loss:
            for code in list(current_w.keys()):
                if code in stop_loss_triggered:
                    continue
                current_price = close_df.loc[date, code]
                high = high_water_mark.get(code, current_price)
                drawdown = (current_price - high) / high if high > 0 else 0

                if drawdown < -stop_loss_pct:
                    # 触发止损
                    stop_loss_triggered.add(code)
                    if code in current_w:
                        del current_w[code]
                    rebalance_log.append({
                        "date": str(date.date()),
                        "action": "STOP_LOSS",
                        "code": code,
                        "price": float(current_price),
                        "drawdown": float(drawdown),
                    })

        # 调仓日
        if date in rebalance_dates:
            target: dict[str, float] = {}

            # 判断市场状态（防御）
            above_ma = False
            if enable_defense and market_close is not None and ma200 is not None:
                if not pd.isna(market_close.loc[date]) and not pd.isna(ma200.loc[date]):
                    above_ma = market_close.loc[date] > ma200.loc[date]

            # 确定卫星仓配置
            if enable_defense and not above_ma:
                sat_alloc = defense_satellite_allocation
            else:
                sat_alloc = satellite_allocation

            # 分配核心仓（等权）
            if core_set:
                core_weight = core_allocation / len(core_set)
                for code in core_set:
                    target[code] = core_weight

            # 分配卫星仓（择优TopN）
            if sat_set and sat_alloc > 0:
                # 排除已止损的ETF
                available_sat = [c for c in sat_set if c not in stop_loss_triggered]
                if available_sat:
                    scores = momentum_df.loc[date, available_sat].dropna()
                    if not scores.empty:
                        picks = scores.sort_values(ascending=False).head(top_n).index.tolist()
                        sat_weight = sat_alloc / len(picks)
                        for code in picks:
                            target[code] = target.get(code, 0.0) + sat_weight

            # 再平衡检查
            if enable_rebalance and current_w:
                need_rebalance = False
                for code, target_weight in target.items():
                    current_weight = current_w.get(code, 0.0)
                    if abs(target_weight - current_weight) > rebalance_threshold:
                        need_rebalance = True
                        break

                if need_rebalance:
                    rebalance_log.append({
                        "date": str(date.date()),
                        "action": "REBALANCE",
                        "from": dict(current_w),
                        "to": dict(target),
                    })
                    current_w = target
                # 否则保持当前权重
            else:
                current_w = target

        # 应用权重
        if current_w:
            for code, w in current_w.items():
                weights.loc[date, code] = w

    # 计算收益
    shifted = weights.shift().ffill().fillna(0.0)
    portfolio_returns = (shifted * returns_df).sum(axis=1)

    # 多区间回测
    horizons = [
        ("近10年", pd.DateOffset(years=10)),
        ("近5年", pd.DateOffset(years=5)),
        ("近2年", pd.DateOffset(years=2)),
        ("近1年", pd.DateOffset(years=1)),
        ("近6个月", pd.DateOffset(months=6)),
        ("近3个月", pd.DateOffset(months=3)),
    ]

    end_date = close_df.index.max()
    rows = []

    for label, offset in horizons:
        start_candidate = end_date - offset
        mask = close_df.index >= start_candidate
        slice_returns = portfolio_returns.loc[mask]

        if slice_returns.empty:
            continue

        metrics = calculate_performance_metrics(slice_returns)
        if metrics["days"] == 0:
            continue

        def _fmt_pct(x: float, digits=2):
            import numpy as _np
            return "-" if _np.isnan(x) else f"{x:.{digits}%}"

        def _fmt_num(x):
            import numpy as _np
            return "-" if _np.isnan(x) else f"{x:.2f}"

        row = {
            "label": label,
            "start": str(slice_returns.index.min().date()),
            "end": str(slice_returns.index.max().date()),
            "days": str(metrics["days"]),
            "total": _fmt_pct(metrics["total_return"]),
            "annual": _fmt_pct(metrics["annualized"]),
            "vol": _fmt_pct(metrics["volatility"]),
            "maxdd": _fmt_pct(metrics["max_drawdown"]),
            "sharpe": _fmt_num(metrics["sharpe"]),
            "note": "",
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

        rows.append(row)

    # 输出结果
    print(colorize_func("\n=== 核心-卫星增强回测（含止损/再平衡/防御） ===", "heading"))
    print(colorize_func(f"核心仓: {core_allocation:.0%} 等权 | 卫星仓: {satellite_allocation:.0%} 择优Top{top_n}", "menu_hint"))
    print(colorize_func(f"止损: {'启用' if enable_stop_loss else '禁用'} ({stop_loss_pct:.0%}) | "
                       f"再平衡: {'启用' if enable_rebalance else '禁用'} ({rebalance_threshold:.0%}) | "
                       f"防御: {'启用' if enable_defense else '禁用'} (MA{defense_ma_window})", "menu_text"))
    print(colorize_func(f"核心仓标的数: {len(core_set)} | 卫星仓候选: {len(sat_set)}", "menu_text"))
    print()

    print(render_table_func(rows))

    # 显示最新权重
    if current_w:
        sorted_holdings = sorted(current_w.items(), key=lambda kv: kv[1], reverse=True)
        lines = [f"{format_label_func(code)}: {w:.1%}" for code, w in sorted_holdings]
        print(colorize_func("\n最新权重:", "heading"))
        print(colorize_func("; ".join(lines), "menu_text"))

    # 显示止损记录
    if stop_loss_triggered:
        print(colorize_func(f"\n⚠️  已触发止损的ETF ({len(stop_loss_triggered)}只):", "warning"))
        for code in stop_loss_triggered:
            print(colorize_func(f"  • {format_label_func(code)}", "menu_text"))

    # 显示调仓统计
    rebalance_count = len([log for log in rebalance_log if log["action"] == "REBALANCE"])
    stop_loss_count = len([log for log in rebalance_log if log["action"] == "STOP_LOSS"])
    print(colorize_func(f"\n📊 调仓统计: 再平衡{rebalance_count}次 | 止损{stop_loss_count}次", "accent"))

    wait_for_ack_func()
