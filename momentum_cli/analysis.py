from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import os

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .data_loader import BundleDataLoader
from .indicators import (
    MomentumConfig,
    average_true_range,
    choppiness_index,
    linear_trend,
    momentum_score,
    moving_average,
    rolling_rank,
    average_directional_index,
    exponential_moving_average,
)
from .metadata import get_label
from .presets import PRESETS


@dataclass
class AnalysisConfig:
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    etfs: Iterable[str] = field(default_factory=list)
    exclude: Iterable[str] = field(default_factory=list)
    momentum: MomentumConfig = field(default_factory=MomentumConfig)
    chop_window: int = 14
    trend_window: int = 90
    corr_window: int = 60
    rank_change_lookback: int = 5
    bundle_path: Optional[Path] = None
    output_dir: Path = Path("results")
    momentum_percentile_lookback: int = 756
    momentum_significance_threshold: float = 0.6
    trend_consistency_adx_threshold: float = 25.0
    trend_consistency_chop_threshold: float = 38.0
    trend_consistency_fast_span: int = 20
    trend_consistency_slow_span: int = 60
    stability_method: str = "presence_ratio"
    stability_window: int = 30  # 从15改为30天，更长的稳定度观察窗口
    stability_top_n: int = 10
    stability_weight: float = 0.2  # 从0.0改为0.2，启用稳定度权重降低追高风险
    make_plots: bool = True


@dataclass
class AnalysisResult:
    summary: pd.DataFrame
    momentum_scores: pd.DataFrame
    momentum_components: Dict[str, pd.DataFrame]
    rank_history: pd.DataFrame
    correlation: pd.DataFrame
    atr: Dict[str, pd.Series]
    chop: Dict[str, pd.Series]
    chop_quantiles: Dict[str, Tuple[Optional[float], Optional[float]]]
    trend: Dict[str, pd.Series]
    adx: Dict[str, pd.Series]
    ema_fast: Dict[str, pd.Series]
    ema_slow: Dict[str, pd.Series]
    stability_scores: pd.DataFrame
    raw_data: Dict[str, pd.DataFrame]
    runtime_seconds: float
    plot_paths: List[Path]
    market_snapshot: Optional[dict] = None


DEFAULT_ETFS = list(
    dict.fromkeys(
        [code for preset in PRESETS.values() for code in preset.tickers]
    )
)


def _classify_chop_state_static(current: float, previous: Optional[float]) -> Optional[str]:
    if not np.isfinite(current):
        return None
    if current <= 38.2:
        return "strong_trend"
    if np.isfinite(previous) and previous > 55 and current <= 55:
        return "trend_breakout"
    if current >= 61.8:
        return "range"
    if 55 <= current < 61.8:
        return "range_watch"
    return "neutral"


def _translate_static_state(state: Optional[str]) -> Optional[str]:
    mapping = {
        "strong_trend": "trend",
        "trend_breakout": "trend",
        "range": "range",
        "range_watch": "range",
        "neutral": "neutral",
    }
    return mapping.get(state, state)


def _kendall_tau_abs(series: pd.Series) -> float:
    values = series.dropna().to_numpy(dtype=float)
    n = len(values)
    if n < 2:
        return float("nan")
    concordant = 0
    discordant = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = values[j] - values[i]
            if diff > 0:
                concordant += 1
            elif diff < 0:
                discordant += 1
    total_pairs = concordant + discordant
    if total_pairs == 0:
        return 1.0
    tau = (concordant - discordant) / total_pairs
    return float(abs(tau))


def _compute_stability_matrix(
    rank_df: pd.DataFrame,
    *,
    method: str,
    window: int,
    top_n: int,
) -> pd.DataFrame:
    if rank_df.empty:
        return rank_df.copy()
    window = max(1, int(window))
    top_n = max(1, int(top_n))
    normalized_method = (method or "presence_ratio").strip().lower()
    if normalized_method not in {"presence_ratio", "kendall"}:
        normalized_method = "presence_ratio"

    if normalized_method == "kendall":
        stability = rank_df.rolling(window, min_periods=3).apply(_kendall_tau_abs, raw=False)
    else:
        membership = (rank_df <= top_n).astype(float)
        stability = membership.rolling(window, min_periods=1).mean()

    return stability.clip(lower=0.0, upper=1.0)


def _compute_chop_quantiles(
    series: pd.Series,
    *,
    window: int = 250,
    lower_pct: float = 30.0,
    upper_pct: float = 70.0,
) -> tuple[Optional[float], Optional[float]]:
    if series is None or series.empty:
        return None, None
    tail = series.dropna()
    if tail.empty:
        return None, None
    tail = tail.tail(window)
    if len(tail) < max(30, window // 5):
        return None, None
    lower = float(np.nanpercentile(tail, lower_pct))
    upper = float(np.nanpercentile(tail, upper_pct))
    if not np.isfinite(lower):
        lower = None
    if not np.isfinite(upper):
        upper = None
    return lower, upper


def _determine_chop_state(
    series: pd.Series,
    *,
    window: int = 250,
) -> tuple[Optional[str], Optional[float], Optional[float]]:
    if series is None or series.empty:
        return None, None, None
    current = float(series.iloc[-1]) if len(series) else np.nan
    previous = float(series.iloc[-2]) if len(series) > 1 else np.nan
    lower, upper = _compute_chop_quantiles(series, window=window)
    state: Optional[str]
    if lower is not None and upper is not None and np.isfinite(current):
        if current <= lower:
            state = "trend"
        elif current >= upper:
            state = "range"
        else:
            state = "neutral"
    else:
        state = _translate_static_state(_classify_chop_state_static(current, previous))
    return state, lower, upper


def _compute_percentile_rank(series: pd.Series, lookback: int) -> float:
    if series is None or series.empty:
        return float("nan")
    cleaned = series.dropna()
    if cleaned.empty:
        return float("nan")
    if lookback is not None and lookback > 0:
        cleaned = cleaned.tail(max(lookback, 1))
    latest = float(cleaned.iloc[-1]) if len(cleaned) else float("nan")
    if not np.isfinite(latest):
        return float("nan")
    values = cleaned.to_numpy(dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan")
    less = float(np.sum(values < latest))
    equal = float(np.sum(values == latest))
    percentile = (less + 0.5 * equal) / values.size
    return float(np.clip(percentile, 0.0, 1.0))


def _classify_adx_state(value: float) -> Optional[str]:
    if not np.isfinite(value):
        return None
    if value >= 25:
        return "strong"
    if value >= 20:
        return "setup"
    if value < 20:
        return "weak"
    return None


def _apply_filters(codes: Iterable[str], exclude: Iterable[str]) -> List[str]:
    exclude_set = {code.upper() for code in exclude}
    deduped = []
    for code in codes:
        upper = code.upper()
        if upper in exclude_set:
            continue
        if upper not in deduped:
            deduped.append(upper)
    return deduped


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def analyze(config: AnalysisConfig) -> AnalysisResult:
    start = time.perf_counter()
    etf_list = config.etfs or DEFAULT_ETFS
    etf_list = _apply_filters(etf_list, config.exclude)

    raw_data: Dict[str, pd.DataFrame] = {}
    momentum_scores: Dict[str, pd.Series] = {}
    momentum_components: Dict[str, pd.DataFrame] = {}
    ma200_values: Dict[str, pd.Series] = {}
    atr_values: Dict[str, pd.Series] = {}
    chop_values: Dict[str, pd.Series] = {}
    chop_quantiles: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
    trend_values: Dict[str, pd.Series] = {}
    adx_values: Dict[str, pd.Series] = {}
    ema_fast_values: Dict[str, pd.Series] = {}
    ema_slow_values: Dict[str, pd.Series] = {}
    market_snapshot: Optional[dict] = None

    fast_span = max(1, int(config.trend_consistency_fast_span or 1))
    slow_span = max(1, int(config.trend_consistency_slow_span or 1))

    with BundleDataLoader(config.bundle_path) as loader:
        for code in etf_list:
            frame = loader.load_bars(code, start_date=config.start_date, end_date=config.end_date)
            if frame.empty:
                continue
            frame = frame.astype({col: float for col in frame.columns if col not in {"limit_up", "limit_down"}})
            # Derived columns
            frame["return"] = frame["close"].pct_change()
            turnover_series = frame["total_turnover"] if "total_turnover" in frame.columns else pd.Series(np.nan, index=frame.index)
            frame["vwap"] = np.where(frame["volume"] > 0, turnover_series / frame["volume"], np.nan)
            raw_data[code] = frame

            score, components = momentum_score(frame["close"], config.momentum)
            momentum_scores[code] = score
            components.columns = [f"{code}_{col}" for col in components.columns]
            momentum_components[code] = components

            ma200_values[code] = moving_average(frame["close"], 200)
            atr_values[code] = average_true_range(frame)
            chop_values[code] = choppiness_index(frame, config.chop_window)
            trend_values[code] = linear_trend(frame["close"], config.trend_window)
            adx_values[code] = average_directional_index(frame)
            ema_fast_values[code] = exponential_moving_average(frame["close"], fast_span)
            ema_slow_values[code] = exponential_moving_average(frame["close"], slow_span)

        try:
            benchmark_frame = loader.load_bars(
                "000300.XSHG",
                start_date=config.start_date,
                end_date=config.end_date,
            )
        except ValueError:
            benchmark_frame = pd.DataFrame()
        if not benchmark_frame.empty:
            benchmark_frame = benchmark_frame.astype(
                {col: float for col in benchmark_frame.columns if col not in {"limit_up", "limit_down"}}
            )
            benchmark_ma200 = moving_average(benchmark_frame["close"], 200)
            benchmark_atr20 = average_true_range(benchmark_frame, window=20)
            benchmark_chop14 = choppiness_index(benchmark_frame, window=14)
            latest_idx = benchmark_frame.index[-1]
            latest_row = benchmark_frame.iloc[-1]
            close_value = float(latest_row["close"])
            ma200_value = float(benchmark_ma200.iloc[-1]) if len(benchmark_ma200) else np.nan
            atr20_value = float(benchmark_atr20.iloc[-1]) if len(benchmark_atr20) else np.nan
            chop14_value = float(benchmark_chop14.iloc[-1]) if len(benchmark_chop14) else np.nan
            chop14_prev = float(benchmark_chop14.iloc[-2]) if len(benchmark_chop14) > 1 else np.nan
            ma200_finite = np.isfinite(ma200_value)
            atr20_finite = np.isfinite(atr20_value)
            chop14_finite = np.isfinite(chop14_value)
            atr_pct = (atr20_value / close_value * 100.0) if atr20_finite and close_value else np.nan
            chop_state, chop_p30, chop_p70 = _determine_chop_state(benchmark_chop14)
            market_snapshot = {
                "symbol": "000300.XSHG",
                "label": "沪深300",
                "trade_date": latest_idx.date(),
                "close": close_value,
                "ma200": ma200_value if ma200_finite else None,
                "above_ma200": bool(close_value > ma200_value) if ma200_finite else False,
                "atr20": atr20_value if atr20_finite else None,
                "atr20_pct": atr_pct if np.isfinite(atr_pct) else None,
                "chop14": chop14_value if chop14_finite else None,
                "chop14_prev": chop14_prev if np.isfinite(chop14_prev) else None,
                "chop14_state": chop_state,
                "chop_p30": chop_p30,
                "chop_p70": chop_p70,
            }

    if not raw_data:
        raise RuntimeError("No data loaded for requested ETFs. Check bundle path and symbols.")

    momentum_df = pd.DataFrame(momentum_scores).dropna(how="all")
    if momentum_df.empty:
        raise RuntimeError("动量得分为空，请检查窗口长度与数据覆盖。")
    rank_df_raw = rolling_rank(momentum_df, ascending=False)
    stability_matrix = _compute_stability_matrix(
        rank_df_raw,
        method=getattr(config, "stability_method", "presence_ratio"),
        window=getattr(config, "stability_window", 15),
        top_n=getattr(config, "stability_top_n", 10),
    )

    try:
        stability_weight = float(getattr(config, "stability_weight", 0.0))
    except (TypeError, ValueError):
        stability_weight = 0.0
    if not np.isfinite(stability_weight):
        stability_weight = 0.0
    stability_weight = float(np.clip(stability_weight, 0.0, 1.0))

    if stability_weight > 0:
        factor = (1.0 - stability_weight) + stability_weight * stability_matrix
        momentum_df = momentum_df * factor.fillna(1.0)
        rank_df = rolling_rank(momentum_df, ascending=False)
    else:
        rank_df = rank_df_raw
    combined_components = pd.concat(momentum_components.values(), axis=1)

    latest_rows = []
    for code, frame in raw_data.items():
        latest = frame.iloc[-1]

        ma200_series = ma200_values.get(code)
        ma200 = float(ma200_series.iloc[-1]) if ma200_series is not None and len(ma200_series) else np.nan
        chop_series = chop_values.get(code)
        chop = float(chop_series.iloc[-1]) if chop_series is not None and len(chop_series) else np.nan
        trend_series = trend_values.get(code)
        trend = float(trend_series.iloc[-1]) if trend_series is not None and len(trend_series) else np.nan
        adx_series = adx_values.get(code)
        adx_val = float(adx_series.iloc[-1]) if adx_series is not None and len(adx_series) else np.nan
        adx_state = _classify_adx_state(adx_val)
        if chop_series is not None:
            chop_state, chop_p30, chop_p70 = _determine_chop_state(chop_series)
        else:
            chop_state, chop_p30, chop_p70 = (None, None, None)
        chop_quantiles[code] = (chop_p30, chop_p70)

        ema_fast_series = ema_fast_values.get(code)
        ema_slow_series = ema_slow_values.get(code)
        ema_fast_val = float(ema_fast_series.iloc[-1]) if ema_fast_series is not None and len(ema_fast_series) else np.nan
        ema_slow_val = float(ema_slow_series.iloc[-1]) if ema_slow_series is not None and len(ema_slow_series) else np.nan

        price_val = float(latest["close"]) if np.isfinite(latest["close"]) else np.nan
        adx_threshold = float(config.trend_consistency_adx_threshold)
        chop_threshold = float(config.trend_consistency_chop_threshold)

        adx_condition: Optional[bool]
        if np.isfinite(adx_val):
            adx_condition = adx_val > adx_threshold
        else:
            adx_condition = None

        chop_condition: Optional[bool]
        if np.isfinite(chop):
            chop_condition = chop < chop_threshold
        else:
            chop_condition = None

        price_condition: Optional[bool]
        if np.isfinite(price_val) and np.isfinite(ema_slow_val):
            price_condition = price_val > ema_slow_val
        else:
            price_condition = None

        ema_condition: Optional[bool]
        if np.isfinite(ema_fast_val) and np.isfinite(ema_slow_val):
            ema_condition = ema_fast_val > ema_slow_val
        else:
            ema_condition = None

        if None not in {adx_condition, chop_condition, price_condition, ema_condition}:
            trend_ok = bool(adx_condition and chop_condition and price_condition and ema_condition)  # type: ignore[arg-type]
        else:
            trend_ok = None

        price_above_ema_slow = price_condition
        ema_alignment = ema_condition

        momentum_series = momentum_df[code] if code in momentum_df else pd.Series(dtype=float)
        mom_percentile = _compute_percentile_rank(momentum_series, config.momentum_percentile_lookback)
        if np.isfinite(mom_percentile):
            mom_significant: Optional[bool] = mom_percentile >= float(config.momentum_significance_threshold)
        else:
            mom_significant = None

        atr_series = atr_values.get(code)
        atr_val = float(atr_series.iloc[-1]) if atr_series is not None and len(atr_series) else np.nan

        stability_series = stability_matrix[code] if code in stability_matrix else None
        stability_val = (
            float(stability_series.iloc[-1])
            if stability_series is not None and len(stability_series)
            else float("nan")
        )

        rank_change = np.nan
        if len(rank_df) > config.rank_change_lookback:
            recent = rank_df[code].iloc[-1]
            previous = rank_df[code].iloc[-config.rank_change_lookback - 1]
            rank_change = recent - previous

        latest_rows.append(
            {
                "name": get_label(code),
                "etf": code,
                "trade_date": latest.name.date(),
                "close": latest["close"],
                "vwap": latest["vwap"],
                "momentum_score": momentum_df[code].iloc[-1],
                "momentum_rank": rank_df[code].iloc[-1],
                "rank_change": rank_change,
                "ma200": ma200,
                "above_ma200": bool(price_val > ma200) if np.isfinite(ma200) and np.isfinite(price_val) else False,
                "chop": chop,
                "trend_slope": trend,
                "atr": atr_val,
                "adx": adx_val,
                "adx_state": adx_state,
                "chop_state": chop_state,
                "chop_p30": chop_p30,
                "chop_p70": chop_p70,
                "ema_fast": ema_fast_val,
                "ema_slow": ema_slow_val,
                "above_ema_slow": price_above_ema_slow,
                "ema_fast_over_slow": ema_alignment,
                "trend_ok": trend_ok,
                "momentum_percentile": mom_percentile,
                "momentum_significant": mom_significant,
                "stability": stability_val,
            }
        )

    summary_df = pd.DataFrame(latest_rows).sort_values("momentum_score", ascending=False)

    returns_df = pd.DataFrame({code: data["return"] for code, data in raw_data.items()})
    corr_window = min(config.corr_window, len(returns_df))
    correlation_df = returns_df.tail(corr_window).corr().round(3)

    plot_paths: List[Path] = []
    make_plots = bool(config.make_plots) and os.getenv("MOMENTUM_FAST", "").lower() not in {"1", "true", "yes", "on"}
    if make_plots:
        output_dir = _ensure_output_dir(config.output_dir)
        plot_paths.extend(_make_plots(output_dir, momentum_df, rank_df, trend_values))

    runtime = time.perf_counter() - start
    return AnalysisResult(
        summary=summary_df,
        momentum_scores=momentum_df,
        momentum_components={k: v for k, v in momentum_components.items()},
        rank_history=rank_df,
        correlation=correlation_df,
        atr=atr_values,
        chop=chop_values,
        chop_quantiles=chop_quantiles,
        trend=trend_values,
        adx=adx_values,
        ema_fast=ema_fast_values,
        ema_slow=ema_slow_values,
        stability_scores=stability_matrix,
        raw_data=raw_data,
        runtime_seconds=runtime,
        plot_paths=plot_paths,
        market_snapshot=market_snapshot,
    )


def _make_plots(output_dir: Path, momentum_df: pd.DataFrame, rank_df: pd.DataFrame, trend_values: Dict[str, pd.Series]) -> List[Path]:
    paths: List[Path] = []
    plt.style.use("seaborn-v0_8")

    momentum_path = output_dir / "momentum_scores.png"
    figure, ax = plt.subplots(figsize=(10, 6))
    for column in momentum_df.columns:
        ax.plot(momentum_df.index, momentum_df[column], label=column)
    ax.set_title("Momentum Scores")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score")
    ax.legend(loc="best")
    figure.tight_layout()
    figure.savefig(momentum_path)
    plt.close(figure)
    paths.append(momentum_path)

    rank_path = output_dir / "momentum_ranks.png"
    figure, ax = plt.subplots(figsize=(10, 6))
    for column in rank_df.columns:
        ax.plot(rank_df.index, rank_df[column], label=column)
    ax.set_title("Momentum Rank History (lower is better)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Rank")
    ax.invert_yaxis()
    ax.legend(loc="best")
    figure.tight_layout()
    figure.savefig(rank_path)
    plt.close(figure)
    paths.append(rank_path)

    trend_path = output_dir / "trend_slope.png"
    figure, ax = plt.subplots(figsize=(10, 6))
    for code, series in trend_values.items():
        ax.plot(series.index, series.values, label=code)
    ax.set_title("Trend Slope (log price regression)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Slope")
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.legend(loc="best")
    figure.tight_layout()
    figure.savefig(trend_path)
    plt.close(figure)
    paths.append(trend_path)

    return paths
