"""Experimental scientific momentum backtest (pluggable, safe, and light).

This module implements an experimental cross-sectional momentum score that:
- Combines multiple return horizons (12-1m, 6-1m, 1m)
- Penalizes high volatility (126d std of daily returns)
- Confirms trend direction using linear regression slope of log-price
- Applies hard momentum percentile threshold and soft correlation filter

It is designed to be:
- Pluggable: can be added/removed without affecting existing flows
- Light-weight: leverages data already loaded by analyze(); no heavy optimizers
- Safe-by-default: respects existing backtest scaffolding and output formatters
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ..utils.colors import colorize
from ..metadata import get_label as _get_label
from ..utils.helpers import format_code_label as _format_label
from ..indicators import linear_trend
from .backtest import calculate_performance_metrics


@dataclass
class ExperimentalConfig:
    # selection & filters
    top_n: int = 2
    min_percentile: float = 0.6  # 0-1 scale
    max_correlation: float = 0.85
    corr_window: int = 120
    trend_window: int = 180
    rebalance: str = "ME"  # monthly end
    # scoring weights
    w_m12_1: float = 0.5
    w_m6_1: float = 0.3
    w_m1: float = 0.1
    w_vol126: float = -0.2  # penalty -> negative weight
    w_slope: float = 0.1
    # portfolio construction
    risk_parity: bool = False  # TopN 内 1/vol 分配
    hysteresis_adv: float = 0.0  # 分数优势阈值，替换现持需达到该差值
    # metadata
    title: str = "[实验] 科学动量多区间回测"
    hint: str = "评分：0.5*m12_1 + 0.3*m6_1 + 0.1*m1 - 0.2*vol126 + 0.1*slope；阈值与相关性过滤启用。"


# Experimental presets collection
EXPERIMENTAL_PRESETS = {
    "科学动量v1": ExperimentalConfig(
        title="[实验] 科学动量v1（经典）",
        hint="评分：0.5*m12_1 + 0.3*m6_1 + 0.1*m1 - 0.2*vol126 + 0.1*slope；经典长波主导，适度波动惩罚。",
        w_m12_1=0.5, w_m6_1=0.3, w_m1=0.1, w_vol126=-0.2, w_slope=0.1,
        max_correlation=0.85, min_percentile=0.6, top_n=2,
    ),
    "稳健动量": ExperimentalConfig(
        title="[实验] 稳健动量（低波优先）",
        hint="评分：0.4*m12_1 + 0.3*m6_1 + 0.1*m1 - 0.4*vol126 + 0.2*slope；强化波动惩罚，偏好稳健标的。",
        w_m12_1=0.4, w_m6_1=0.3, w_m1=0.1, w_vol126=-0.4, w_slope=0.2,
        max_correlation=0.80, min_percentile=0.65, top_n=2, risk_parity=True,
    ),
    "激进动量": ExperimentalConfig(
        title="[实验] 激进动量（纯择强）",
        hint="评分：0.6*m12_1 + 0.3*m6_1 + 0.1*m1 - 0.0*vol126 + 0.0*slope；纯动量择强，忽略波动与趋势确认。",
        w_m12_1=0.6, w_m6_1=0.3, w_m1=0.1, w_vol126=0.0, w_slope=0.0,
        max_correlation=0.90, min_percentile=0.55, top_n=2,
    ),
    "短波敏感": ExperimentalConfig(
        title="[实验] 短波敏感（快速响应）",
        hint="评分：0.3*m12_1 + 0.4*m6_1 + 0.3*m1 - 0.2*vol126 + 0.2*slope；提升短期动量权重，快速捕捉转向。",
        w_m12_1=0.3, w_m6_1=0.4, w_m1=0.3, w_vol126=-0.2, w_slope=0.2,
        max_correlation=0.85, min_percentile=0.6, top_n=2, trend_window=120,
    ),
    "趋势确认": ExperimentalConfig(
        title="[实验] 趋势确认（斜率主导）",
        hint="评分：0.4*m12_1 + 0.2*m6_1 + 0.1*m1 - 0.1*vol126 + 0.4*slope；强化趋势斜率，确认方向性。",
        w_m12_1=0.4, w_m6_1=0.2, w_m1=0.1, w_vol126=-0.1, w_slope=0.4,
        max_correlation=0.85, min_percentile=0.6, top_n=2, trend_window=240,
    ),
    "多腿分散": ExperimentalConfig(
        title="[实验] 多腿分散（Top3等权）",
        hint="评分：0.5*m12_1 + 0.3*m6_1 + 0.1*m1 - 0.2*vol126 + 0.1*slope；Top3分散持仓，降低集中度风险。",
        w_m12_1=0.5, w_m6_1=0.3, w_m1=0.1, w_vol126=-0.2, w_slope=0.1,
        max_correlation=0.80, min_percentile=0.6, top_n=3,
    ),
    "风险平价": ExperimentalConfig(
        title="[实验] 风险平价（逆波动配权）",
        hint="评分：0.5*m12_1 + 0.3*m6_1 + 0.1*m1 - 0.3*vol126 + 0.1*slope；TopN内按1/vol配权，均衡风险贡献。",
        w_m12_1=0.5, w_m6_1=0.3, w_m1=0.1, w_vol126=-0.3, w_slope=0.1,
        max_correlation=0.85, min_percentile=0.6, top_n=2, risk_parity=True,
    ),
    "低换手": ExperimentalConfig(
        title="[实验] 低换手（阻尼切换）",
        hint="评分：0.5*m12_1 + 0.3*m6_1 + 0.1*m1 - 0.2*vol126 + 0.1*slope；新候选需领先现持0.3分才切换，降低换手。",
        w_m12_1=0.5, w_m6_1=0.3, w_m1=0.1, w_vol126=-0.2, w_slope=0.1,
        max_correlation=0.85, min_percentile=0.6, top_n=2, hysteresis_adv=0.3,
    ),
}

def _last_valid(series: pd.Series, date) -> float:
    if series is None or series.empty:
        return np.nan
    if date in series.index:
        return float(series.loc[date])
    # fallback to last before date
    s = series.loc[:date]
    if len(s) == 0:
        return np.nan
    return float(s.iloc[-1])


def _zscore(values: pd.Series) -> pd.Series:
    v = values.astype(float)
    mu = v.mean()
    sd = v.std()
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(0.0, index=v.index)
    return (v - mu) / sd


def _pct_change_from(series: pd.Series, lag: int) -> pd.Series:
    if series is None or series.empty:
        return pd.Series(dtype=float)
    return series / series.shift(lag) - 1.0


def _twelve_minus_one(close: pd.Series, date) -> float:
    # Approx: return from t-252 to t-21 => close[t-21] / close[t-252] - 1
    if close is None or close.empty:
        return np.nan
    s = close
    # align to date
    if date not in s.index:
        s = s.loc[:date]
        if s.empty:
            return np.nan
        date = s.index[-1]
    idx = s.index.get_loc(date)
    if idx < 252:
        return np.nan
    c = s.iloc
    # need values at date-21 and date-252
    try:
        val_21 = c[idx - 21]
        val_252 = c[idx - 252]
    except Exception:
        return np.nan
    if not np.isfinite(val_21) or not np.isfinite(val_252) or val_252 == 0:
        return np.nan
    return float(val_21 / val_252 - 1.0)


def _k_month(close: pd.Series, date, k_days: int) -> float:
    # simple k-day momentum: close/close.shift(k) - 1
    if close is None or close.empty:
        return np.nan
    s = close
    if date not in s.index:
        s = s.loc[:date]
        if s.empty:
            return np.nan
        date = s.index[-1]
    idx = s.index.get_loc(date)
    if idx < k_days:
        return np.nan
    c = s.iloc
    val_now = c[idx]
    val_k = c[idx - k_days]
    if not np.isfinite(val_now) or not np.isfinite(val_k) or val_k == 0:
        return np.nan
    return float(val_now / val_k - 1.0)


def _volatility126(ret: pd.Series, date) -> float:
    s = ret
    if s is None or s.empty:
        return np.nan
    if date not in s.index:
        s = s.loc[:date]
        if s.empty:
            return np.nan
        date = s.index[-1]
    idx = s.index.get_loc(date)
    if idx < 126:
        return np.nan
    window = s.iloc[idx - 126 + 1 : idx + 1]
    return float(window.std())


def _trend_slope(close: pd.Series, date, window: int) -> float:
    s = close
    if s is None or s.empty:
        return np.nan
    if date not in s.index:
        s = s.loc[:date]
        if s.empty:
            return np.nan
        date = s.index[-1]
    idx = s.index.get_loc(date)
    if idx + 1 < window:
        return np.nan
    series = s.iloc[idx - window + 1 : idx + 1]
    slope_series = linear_trend(series, window=len(series))
    if slope_series is None or len(slope_series) == 0:
        return np.nan
    val = slope_series.iloc[-1]
    return float(val)


def _select_with_constraints(
    date,
    close_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    cfg: ExperimentalConfig,
    current_holdings: Dict[str, float],
) -> Tuple[List[str], Dict[str, object]]:
    # Compute feature values for available codes at this date
    feats: Dict[str, Dict[str, float]] = {}
    for code in close_df.columns:
        close = close_df[code].dropna()
        ret = returns_df[code].dropna() if code in returns_df else pd.Series(dtype=float)
        m12_1 = _twelve_minus_one(close, date)
        m6_1 = _k_month(close, date, 126 - 21)  # approx 6-1m ~ 105 days
        m1 = _k_month(close, date, 21)
        vol126 = _volatility126(ret, date)
        slope = _trend_slope(close, date, window=cfg.trend_window)
        feats[code] = {"m12_1": m12_1, "m6_1": m6_1, "m1": m1, "vol126": vol126, "slope": slope}

    df = pd.DataFrame.from_dict(feats, orient="index")
    df = df.replace([np.inf, -np.inf], np.nan)
    # Hard screen by momentum percentile (use m12_1 as canonical)
    m = df["m12_1"].dropna()
    if m.empty:
        return [], {"reason": "no_momentum_data"}
    thresh = cfg.min_percentile
    if thresh > 1.0:
        thresh = thresh / 100.0
    cutoff = m.quantile(thresh)
    eligible = df.loc[df["m12_1"] >= cutoff]
    if eligible.empty:
        return [], {"reason": "no_eligible_by_percentile", "cutoff": float(cutoff)}

    # Cross-sectional z-scores
    z = pd.DataFrame(index=eligible.index)
    z["z_m12_1"] = _zscore(eligible["m12_1"]) if "m12_1" in eligible else 0.0
    z["z_m6_1"] = _zscore(eligible["m6_1"]) if "m6_1" in eligible else 0.0
    z["z_m1"] = _zscore(eligible["m1"]) if "m1" in eligible else 0.0
    z["z_vol126"] = _zscore(eligible["vol126"]) if "vol126" in eligible else 0.0
    z["z_slope"] = _zscore(eligible["slope"]) if "slope" in eligible else 0.0

    score = (
        cfg.w_m12_1 * z["z_m12_1"]
        + cfg.w_m6_1 * z["z_m6_1"]
        + cfg.w_m1 * z["z_m1"]
        + cfg.w_vol126 * z["z_vol126"]  # already negative in config
        + cfg.w_slope * z["z_slope"]
    )
    rank = score.sort_values(ascending=False)

    # Soft correlation filter (greedy) + hysteresis
    sel: List[str] = []
    rejected_by_corr: List[Tuple[str, str, float]] = []  # (code, with_code, corr)
    rejected_by_hysteresis: List[Tuple[str, float, float]] = []  # (code, new_score, current_score)
    # Rolling window corr up to date
    corr_slice = returns_df.loc[:date].tail(cfg.corr_window)
    corr = corr_slice.corr() if not corr_slice.empty else pd.DataFrame()

    # Apply hysteresis: if current holdings exist, new candidates must beat them by threshold
    current_codes = set(current_holdings.keys()) if current_holdings else set()
    current_scores = {c: float(score.get(c, -999)) for c in current_codes if c in score.index}

    for code in rank.index:
        if len(sel) >= cfg.top_n:
            break

        # Hysteresis check: if replacing existing holding, need advantage
        if cfg.hysteresis_adv > 0 and current_codes:
            new_score = float(score.get(code, -999))
            # Find weakest current holding that would be displaced
            remaining_current = [c for c in current_codes if c not in sel]
            if remaining_current and len(sel) + len(remaining_current) >= cfg.top_n:
                weakest_current = min(remaining_current, key=lambda x: current_scores.get(x, -999))
                weakest_score = current_scores.get(weakest_current, -999)
                if new_score - weakest_score < cfg.hysteresis_adv:
                    rejected_by_hysteresis.append((code, new_score, weakest_score))
                    continue

        # Correlation filter
        if code not in corr.index or len(sel) == 0:
            sel.append(code)
            continue
        ok = True
        for s in sel:
            if s in corr.columns:
                val = corr.loc[code, s]
                if pd.notna(val) and abs(float(val)) > cfg.max_correlation:
                    rejected_by_corr.append((code, s, float(val)))
                    ok = False
                    break
        if ok:
            sel.append(code)
    diag = {
        "eligible_count": int(len(eligible)),
        "rank": rank,
        "z_table": z.assign(score=score).sort_values("score", ascending=False),
        "rejected_by_corr": rejected_by_corr,
        "rejected_by_hysteresis": rejected_by_hysteresis,
        "cutoff": float(cutoff),
        "current_scores": current_scores,
    }
    return sel, diag


def run_experimental_momentum_backtest(
    obtain_context_func,
    format_label_func,
    colorize_func,
    render_table_func,
    wait_for_ack_func,
    last_state: Optional[dict] = None,
    *,
    config: Optional[ExperimentalConfig] = None,
) -> None:
    cfg = config or ExperimentalConfig()
    context = obtain_context_func(last_state, allow_reuse=False)
    if not context:
        return
    result = context["result"]
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()}).sort_index().dropna(how="all")
    if close_df.empty:
        print(colorize_func("[实验] 无法回测：价格数据为空。", "warning"))
        return
    returns_df = close_df.pct_change().fillna(0.0)

    # Monthly rebalancing dates
    rebalance_dates = close_df.resample(cfg.rebalance).last().index
    if rebalance_dates.empty:
        rebalance_dates = close_df.index

    weights = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
    current_w: Dict[str, float] = {}
    # Hint for cross-market validation (after data available)
    try:
        suffixes = {str(c).split(".")[-1] for c in close_df.columns if isinstance(c, str) and "." in c}
        if suffixes.issubset({"XSHG", "XSHE"}):
            print(colorize_func("[实验] 提示：要验证美股/港股，请切换到包含相应ETF的预设；如数据缺失，可在回测工具菜单选择‘刷新数据’获取最新数据包。", "menu_hint"))
    except Exception:
        pass


    last_diag: Dict[str, object] = {}
    for date in close_df.index:
        if date in rebalance_dates:
            selected, diag = _select_with_constraints(
                date,
                close_df,
                returns_df,
                cfg,
                current_w,
            )
            last_diag = diag
            target: Dict[str, float] = {}
            if selected:
                # Risk parity from config or env override
                import os as _os
                use_rp = cfg.risk_parity or _os.getenv("EXP_RISK_PARITY", "").lower() in {"1","true","yes","on"}
                if use_rp:
                    vol_map: Dict[str, float] = {}
                    for code in selected:
                        series = returns_df[code].dropna()
                        vol = float(series.tail(126).std()) if len(series) > 5 else np.nan
                        vol_map[code] = vol if np.isfinite(vol) and vol > 0 else 1.0
                    inv = {c: 1.0/vol_map.get(c,1.0) for c in selected}
                    total = sum(inv.values())
                    for code in selected:
                        target[code] = inv[code]/total if total>0 else 1.0/len(selected)
                else:
                    per = 1.0 / len(selected)
                    for code in selected:
                        target[code] = per
            current_w = target
        if current_w:
            for code, w in current_w.items():
                weights.loc[date, code] = w

    shifted = weights.shift().ffill().fillna(0.0)
    portfolio_returns = (shifted * returns_df).sum(axis=1)

    # Output horizons + last month (previous complete natural month)
    horizons = [
        ("近10年", pd.DateOffset(years=10)),
        ("近5年", pd.DateOffset(years=5)),
        ("近2年", pd.DateOffset(years=2)),
        ("近1年", pd.DateOffset(years=1)),
        ("近6个月", pd.DateOffset(months=6)),
        ("近3个月", pd.DateOffset(months=3)),
    ]

    end_date = close_df.index.max()
    rows: List[Dict] = []

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
            "label": f"[实验] {label}",
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

    # Extra: last month (previous complete natural month)
    try:
        prev_month_end = (end_date - pd.offsets.MonthBegin(1)) - pd.Timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
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
                "label": "[实验] 近1个月",
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

    # Diagnostics: show latest selection and top candidates breakdown (compact)
    try:
        if last_diag and isinstance(last_diag.get("z_table"), pd.DataFrame):
            ztab: pd.DataFrame = last_diag["z_table"]
            head = ztab.head(6)
            lines = []
            for code, row in head.iterrows():
                parts = [
                    f"score={row['score']:.2f}",
                    f"m12_1={row.get('z_m12_1',0):+.2f}",
                    f"m6_1={row.get('z_m6_1',0):+.2f}",
                    f"m1={row.get('z_m1',0):+.2f}",
                    f"-vol={-row.get('z_vol126',0):+.2f}",
                    f"slope={row.get('z_slope',0):+.2f}",
                ]
                lines.append(f"{format_label_func(code)}: " + ", ".join(parts))
            print(colorize_func("\n[实验] 当期候选（前6）评分拆分:", "heading"))
            for ln in lines:
                print(colorize_func(ln, "menu_text"))
        rej = last_diag.get("rejected_by_corr") if last_diag else []
        if rej:
            samples = "; ".join([f"{a}~{b}={c:.2f}" for a,b,c in rej[:6]])
            print(colorize_func(f"[实验] 相关性剔除样例: {samples}", "warning"))

        hyst = last_diag.get("rejected_by_hysteresis") if last_diag else []
        if hyst:
            samples = "; ".join([f"{a}({new:.2f}<{cur:.2f}+{cfg.hysteresis_adv})" for a,new,cur in hyst[:4]])
            print(colorize_func(f"[实验] 阻尼剔除样例: {samples}", "warning"))
    except Exception:
        pass

    print(colorize_func(f"\n=== {cfg.title} ===", "heading"))
    print(colorize_func(cfg.hint, "menu_hint"))
    print(render_table_func(rows))

    # Show latest holdings
    if len(weights) > 0:
        last_w = weights.iloc[-1]
        non_zero = last_w[last_w > 0].sort_values(ascending=False)
        if len(non_zero) > 0:
            lines = [f"{format_label_func(c)}: {w:.1%}" for c, w in non_zero.items()]
            print(colorize_func("\n[实验] 最新权重:", "heading"))
            print(colorize_func("; ".join(lines), "menu_text"))

    wait_for_ack_func()

