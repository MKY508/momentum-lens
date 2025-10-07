"""报告生成模块

提供文本和Markdown格式的报告生成功能。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def render_text_report(state: Dict[str, Any]) -> str:
    """渲染文本格式报告

    Args:
        state: 分析状态字典

    Returns:
        文本格式的报告
    """
    lines = []

    # 标题
    lines.append("=== 动量分析报告 ===")
    lines.append("")

    # 基本信息
    if "start_date" in state and "end_date" in state:
        lines.append(f"分析区间: {state['start_date']} → {state['end_date']}")

    if "tickers" in state:
        ticker_count = len(state["tickers"])
        lines.append(f"券池规模: {ticker_count}")

    if "momentum_windows" in state:
        windows = state["momentum_windows"]
        lines.append(f"动量窗口: {', '.join(map(str, windows))}")

    if "momentum_weights" in state:
        weights = state["momentum_weights"]
        weight_str = ", ".join(f"{w:.2f}" for w in weights)
        lines.append(f"动量权重: {weight_str}")

    lines.append("")

    # 排名信息
    if "rankings" in state:
        lines.append("=== 动量排名 ===")
        rankings = state["rankings"]

        for i, item in enumerate(rankings[:10], 1):  # 只显示前10
            ticker = item.get("ticker", "")
            momentum = item.get("momentum", 0)
            lines.append(f"{i:2d}. {ticker}: {momentum:.4f}")

        lines.append("")

    # 警告信息
    if "warnings" in state and state["warnings"]:
        lines.append("=== 警告 ===")
        for warning in state["warnings"]:
            lines.append(f"  • {warning}")
        lines.append("")

    return "\n".join(lines)


def render_markdown_report(state: Dict[str, Any]) -> str:
    """渲染Markdown格式报告

    Args:
        state: 分析状态字典

    Returns:
        Markdown格式的报告
    """
    lines = []

    # 标题
    lines.append("# 动量分析报告")
    lines.append("")

    # 基本信息
    lines.append("## 分析概览")
    lines.append("")

    if "start_date" in state and "end_date" in state:
        lines.append(f"- **分析区间**: {state['start_date']} → {state['end_date']}")

    if "tickers" in state:
        ticker_count = len(state["tickers"])
        lines.append(f"- **券池规模**: {ticker_count} 只")

    if "momentum_windows" in state:
        windows = state["momentum_windows"]
        lines.append(f"- **动量窗口**: {', '.join(map(str, windows))}")

    if "momentum_weights" in state:
        weights = state["momentum_weights"]
        weight_str = ", ".join(f"{w:.2f}" for w in weights)
        lines.append(f"- **动量权重**: {weight_str}")

    lines.append("")

    # 排名表格
    if "rankings" in state:
        lines.append("## 动量排名")
        lines.append("")
        lines.append("| 排名 | 代码 | 动量值 | 分位数 |")
        lines.append("|------|------|--------|--------|")

        rankings = state["rankings"]
        for i, item in enumerate(rankings[:20], 1):  # 显示前20
            ticker = item.get("ticker", "")
            momentum = item.get("momentum", 0)
            percentile = item.get("percentile", 0)
            lines.append(f"| {i} | {ticker} | {momentum:.4f} | {percentile:.1f}% |")

        lines.append("")

    # 相关性警告
    if "high_correlation_pairs" in state:
        pairs = state["high_correlation_pairs"]
        if pairs:
            lines.append("## 高相关性警告")
            lines.append("")
            for pair in pairs[:10]:  # 显示前10对
                ticker1 = pair.get("ticker1", "")
                ticker2 = pair.get("ticker2", "")
                corr = pair.get("correlation", 0)
                lines.append(f"- {ticker1} ↔ {ticker2}: {corr:.2f}")
            lines.append("")

    # 其他警告
    if "warnings" in state and state["warnings"]:
        lines.append("## 其他警告")
        lines.append("")
        for warning in state["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    # 生成时间
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"---")
    lines.append(f"*报告生成时间: {now}*")

    return "\n".join(lines)


def format_summary_table(data: List[Dict[str, Any]], columns: List[str]) -> str:
    """格式化摘要表格

    Args:
        data: 数据列表
        columns: 列名列表

    Returns:
        格式化的表格字符串
    """
    if not data or not columns:
        return ""

    lines = []

    # 计算列宽
    col_widths = {}
    for col in columns:
        col_widths[col] = len(col)

    for row in data:
        for col in columns:
            value = str(row.get(col, ""))
            col_widths[col] = max(col_widths[col], len(value))

    # 表头
    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
    lines.append(header)

    # 分隔线
    separator = "-+-".join("-" * col_widths[col] for col in columns)
    lines.append(separator)

    # 数据行
    for row in data:
        row_str = " | ".join(
            str(row.get(col, "")).ljust(col_widths[col])
            for col in columns
        )
        lines.append(row_str)

    return "\n".join(lines)


def generate_quick_summary(state: Dict[str, Any]) -> str:
    """生成快速摘要

    Args:
        state: 分析状态字典

    Returns:
        快速摘要字符串
    """
    parts = []

    if "tickers" in state:
        parts.append(f"{len(state['tickers'])}只ETF")

    if "start_date" in state and "end_date" in state:
        parts.append(f"{state['start_date']}至{state['end_date']}")

    if "rankings" in state and state["rankings"]:
        top = state["rankings"][0]
        ticker = top.get("ticker", "")
        parts.append(f"榜首: {ticker}")

    return " · ".join(parts) if parts else "无数据"




def display_analysis_summary(state: dict, format_summary_func, format_correlation_func, colorize_func) -> None:
    """显示分析摘要

    Args:
        state: 分析状态字典
        format_summary_func: 格式化摘要表的函数
        format_correlation_func: 格式化相关矩阵的函数
        colorize_func: 着色函数
    """
    report_text = state.get("report_text")
    if report_text:
        print(report_text)
        return

    result = state["result"]
    config = state["config"]

    print(colorize_func("\n=== 动量汇总 ===", "heading"))
    print(format_summary_func(result.summary, "zh"))

    print(
        colorize_func(
            f"\n=== 相关系数矩阵 (近 {config.corr_window} 个交易日) ===",
            "heading",
        )
    )
    print(format_correlation_func(result.correlation, "zh"))

    print(
        colorize_func(
            f"\n耗时: {result.runtime_seconds:.2f} 秒，覆盖 {len(result.summary)} 只 ETF",
            "info",
        )
    )

    if result.plot_paths:
        print(colorize_func("生成的图表：", "heading"))
        for path in result.plot_paths:
            print(colorize_func(f" - {path}", "menu_hint"))




def build_strategy_gate_entries(result, lang: str, format_label_func=None) -> list:
    """构建策略门控条目

    Args:
        result: 分析结果
        lang: 语言
        format_label_func: 格式化标签函数

    Returns:
        门控条目列表 [(text, style), ...]
    """
    import pandas as pd
    from typing import Optional

    entries: list = []
    market = getattr(result, "market_snapshot", None)
    is_zh = lang == "zh"

    summary_sorted = pd.DataFrame()
    if isinstance(getattr(result, "summary", None), pd.DataFrame) and not result.summary.empty:
        summary_sorted = result.summary.sort_values("momentum_score", ascending=False)

    top_label: Optional[str] = None
    top_score: Optional[float] = None
    top_adx: Optional[float] = None
    top_adx_state: Optional[str] = None

    if not summary_sorted.empty:
        top_row = summary_sorted.iloc[0]
        top_code = top_row.get("etf")
        if isinstance(top_code, str):
            if format_label_func:
                top_label = format_label_func(top_code)
            else:
                top_label = top_code
        try:
            top_score = float(top_row.get("momentum_score"))
        except (TypeError, ValueError):
            top_score = None
        try:
            top_adx = float(top_row.get("adx"))
        except (TypeError, ValueError):
            top_adx = None
        top_adx_state = top_row.get("adx_state")

    def _to_float(value) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    # 市场快照门控
    if market:
        hs300_chg = _to_float(market.get("hs300_change"))
        zz500_chg = _to_float(market.get("zz500_change"))
        zz1000_chg = _to_float(market.get("zz1000_change"))

        if hs300_chg is not None and zz500_chg is not None and zz1000_chg is not None:
            avg_chg = (hs300_chg + zz500_chg + zz1000_chg) / 3.0
            if avg_chg < -0.5:
                entries.append(("市场大跌" if is_zh else "Market Crash", "danger"))
            elif avg_chg < -0.2:
                entries.append(("市场下跌" if is_zh else "Market Down", "warning"))
            elif avg_chg > 1.0:
                entries.append(("市场大涨" if is_zh else "Market Rally", "success"))
            elif avg_chg > 0.3:
                entries.append(("市场上涨" if is_zh else "Market Up", "info"))

    # 榜首动量门控
    if top_score is not None:
        if top_score < 0.3:
            entries.append(("榜首动量弱" if is_zh else "Top Weak", "warning"))
        elif top_score > 0.7:
            entries.append(("榜首动量强" if is_zh else "Top Strong", "success"))

    # ADX 门控
    if top_adx is not None:
        if top_adx < 20:
            entries.append(("榜首趋势弱" if is_zh else "Top Trend Weak", "warning"))
        elif top_adx > 40:
            entries.append(("榜首趋势强" if is_zh else "Top Trend Strong", "success"))

    return entries




def build_result_payload(
    result,
    config,
    momentum_config,
    preset,
    lang: str,
    collect_alerts_func,
    build_gate_entries_func=None,
    max_series_export: int = 252,
) -> dict:
    """构建结果载荷

    Args:
        result: 分析结果
        config: 分析配置
        momentum_config: 动量配置
        preset: 分析预设
        lang: 语言
        collect_alerts_func: 收集预警的函数
        build_gate_entries_func: 构建门控条目的函数
        max_series_export: 最大导出序列长度

    Returns:
        结果载荷字典
    """
    import json
    import datetime as dt
    from dataclasses import asdict

    # 处理摘要数据
    summary_df = result.summary.copy()
    if "trade_date" in summary_df.columns:
        summary_df["trade_date"] = summary_df["trade_date"].apply(
            lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value)
        )
    summary_json = json.loads(
        summary_df.to_json(orient="records", force_ascii=False)
    )

    # 处理相关矩阵
    correlation_df = result.correlation.round(4)
    correlation_json = json.loads(correlation_df.to_json(force_ascii=False))

    # 处理动量序列
    momentum_series = result.momentum_scores.tail(max_series_export).reset_index()
    if not momentum_series.empty:
        momentum_series.rename(columns={momentum_series.columns[0]: "date"}, inplace=True)
        momentum_series["date"] = momentum_series["date"].astype(str)
    else:
        momentum_series["date"] = []
    momentum_json = json.loads(
        momentum_series.to_json(orient="records", force_ascii=False)
    )

    # 处理排名序列
    rank_series = result.rank_history.tail(max_series_export).reset_index()
    if not rank_series.empty:
        rank_series.rename(columns={rank_series.columns[0]: "date"}, inplace=True)
        rank_series["date"] = rank_series["date"].astype(str)
    else:
        rank_series["date"] = []
    rank_json = json.loads(
        rank_series.to_json(orient="records", force_ascii=False)
    )

    # 处理稳定度序列
    stability_series = result.stability_scores.tail(max_series_export).reset_index()
    if not stability_series.empty:
        stability_series.rename(columns={stability_series.columns[0]: "date"}, inplace=True)
        stability_series["date"] = stability_series["date"].astype(str)
    else:
        stability_series["date"] = []
    stability_json = json.loads(
        stability_series.to_json(orient="records", force_ascii=False)
    )

    # 构建元数据
    meta: dict = {
        "start": config.start_date,
        "end": config.end_date,
        "etfs": list(config.etfs),
        "exclude": list(config.exclude),
        "etf_count": len(result.summary),
        "momentum_windows": list(momentum_config.windows),
        "momentum_weights": list(momentum_config.weights)
        if momentum_config.weights is not None
        else None,
        "corr_window": config.corr_window,
        "chop_window": config.chop_window,
        "trend_window": config.trend_window,
        "rank_lookback": config.rank_change_lookback,
        "bundle_path": str(config.bundle_path) if config.bundle_path else None,
        "output_dir": str(config.output_dir),
        "make_plots": config.make_plots,
        "runtime_seconds": result.runtime_seconds,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "lang": lang,
        "plot_paths": [str(path) for path in result.plot_paths],
        "momentum_percentile_lookback": config.momentum_percentile_lookback,
        "momentum_significance_threshold": config.momentum_significance_threshold,
        "trend_consistency_adx_threshold": config.trend_consistency_adx_threshold,
        "trend_consistency_chop_threshold": config.trend_consistency_chop_threshold,
        "trend_consistency_fast_span": config.trend_consistency_fast_span,
        "trend_consistency_slow_span": config.trend_consistency_slow_span,
        "stability_method": config.stability_method,
        "stability_window": config.stability_window,
        "stability_top_n": config.stability_top_n,
        "stability_weight": config.stability_weight,
    }

    if preset:
        meta["analysis_preset"] = asdict(preset)

    # 市场快照
    market_snapshot = getattr(result, "market_snapshot", None)
    if market_snapshot:
        snapshot = dict(market_snapshot)
        trade_date = snapshot.get("trade_date")
        if hasattr(trade_date, "isoformat"):
            snapshot["trade_date"] = trade_date.isoformat()
        meta["market_snapshot"] = snapshot

    # 策略门控
    if build_gate_entries_func:
        gate_entries = build_gate_entries_func(result, lang)
        if gate_entries:
            meta["strategy_gates"] = [
                {"text": text, "style": style} for text, style in gate_entries
            ]

    # 动量配置
    momentum_payload = asdict(momentum_config)
    momentum_payload["windows"] = list(momentum_payload["windows"])
    if momentum_payload.get("weights") is not None:
        momentum_payload["weights"] = list(momentum_payload["weights"])
    meta["momentum_config"] = momentum_payload

    # 收集预警
    alerts = collect_alerts_func(result)

    return {
        "meta": meta,
        "summary": summary_json,
        "correlation": correlation_json,
        "series": {
            "momentum_scores": momentum_json,
            "rank_history": rank_json,
            "stability_scores": stability_json,
        },
        "alerts": alerts,
    }
