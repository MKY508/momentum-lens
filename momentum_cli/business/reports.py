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
