"""预警检测业务逻辑"""
from __future__ import annotations

from typing import List
import numpy as np
import pandas as pd


def detect_high_correlation_pairs(
    corr: pd.DataFrame,
    threshold: float = 0.85,
    max_pairs: int = 10,
    format_label_func=None,
) -> List[dict]:
    """检测高相关性配对
    
    Args:
        corr: 相关矩阵
        threshold: 相关性阈值
        max_pairs: 最大返回对数
        format_label_func: 格式化标签的函数
        
    Returns:
        高相关性配对列表，每项包含 code_a, label_a, code_b, label_b, value
    """
    if corr.empty:
        return []
    
    matrix = corr.to_numpy(dtype=float)
    n = matrix.shape[0]
    if n < 2:
        return []
    
    # 获取上三角矩阵的索引（排除对角线）
    rows, cols = np.triu_indices(n, k=1)
    values = matrix[rows, cols]
    
    # 筛选高于阈值的相关性
    mask = np.isfinite(values) & (values >= threshold)
    if not mask.any():
        return []
    
    rows = rows[mask]
    cols = cols[mask]
    values = values[mask]
    
    # 按相关性降序排序
    order = np.argsort(values)[::-1]
    columns = list(corr.columns)
    
    alerts: List[dict] = []
    for idx in order[:max_pairs]:
        i = rows[idx]
        j = cols[idx]
        value = float(values[idx])
        code_a = columns[i]
        code_b = columns[j]
        
        alert = {
            "code_a": code_a,
            "code_b": code_b,
            "value": round(value, 4),
        }
        
        # 如果提供了格式化函数，添加标签
        if format_label_func:
            alert["label_a"] = format_label_func(code_a)
            alert["label_b"] = format_label_func(code_b)
        
        alerts.append(alert)
    
    return alerts


def detect_rank_drop_alerts(result, lookback: int = 5, drop_threshold: int = 3) -> List[dict]:
    """检测排名下降预警
    
    Args:
        result: 分析结果对象
        lookback: 回溯天数
        drop_threshold: 下降阈值
        
    Returns:
        排名下降预警列表
    """
    alerts: List[dict] = []
    
    if not hasattr(result, 'summary') or result.summary.empty:
        return alerts
    
    summary = result.summary
    
    for _, row in summary.iterrows():
        rank_change = row.get('rank_change', 0)
        if pd.notna(rank_change) and rank_change >= drop_threshold:
            alerts.append({
                "code": row.get('etf', ''),
                "name": row.get('name', ''),
                "rank_change": int(rank_change),
                "current_rank": int(row.get('momentum_rank', 0)),
            })
    
    return alerts


def collect_alerts(result, correlation_threshold: float = 0.85, max_correlation_pairs: int = 10, format_label_func=None) -> dict:
    """收集所有预警
    
    Args:
        result: 分析结果对象
        correlation_threshold: 相关性阈值
        max_correlation_pairs: 最大相关性配对数
        format_label_func: 格式化标签的函数
        
    Returns:
        包含各类预警的字典
    """
    return {
        "momentum_rank_drops": detect_rank_drop_alerts(result),
        "high_correlation_pairs": detect_high_correlation_pairs(
            result.correlation,
            threshold=correlation_threshold,
            max_pairs=max_correlation_pairs,
            format_label_func=format_label_func,
        ),
    }

