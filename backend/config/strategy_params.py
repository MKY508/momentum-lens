"""
Strategy Parameters Configuration
策略参数统一配置 - 集中管理所有可调参数
"""

from typing import Dict, Any
from enum import Enum


class MarketMode(Enum):
    """市场模式枚举"""
    AGGRESSIVE = "aggressive"  # 进攻模式
    BALANCED = "balanced"      # 均衡模式（默认）
    CONSERVATIVE = "conservative"  # 保守模式
    CHOP = "chop"             # 震荡模式


# 基础参数配置
STRATEGY_PARAMS = {
    # 动量公式权重（固定，不可配置）
    'momentum_weights': {
        'r60_weight': 0.6,   # 60日收益权重
        'r120_weight': 0.4,  # 120日收益权重
        'description': 'Score = 0.6 × r60 + 0.4 × r120'
    },
    
    # 不同模式下的参数配置
    'mode_params': {
        MarketMode.AGGRESSIVE: {
            'stop_loss': -0.10,           # 止损线 -10%
            'buffer_zone': 0.02,          # 缓冲区 2%
            'min_holding_days': 14,       # 最短持有期 2周
            'price_band': 0.07,           # 价格带宽 ±7pp
            'max_legs': 2,                # 最大腿数
            'position_size_initial': 0.05, # 初始仓位 5%
            'position_size_full': 0.10,   # 完整仓位 10%
        },
        MarketMode.BALANCED: {  # 默认
            'stop_loss': -0.12,           # 止损线 -12%
            'buffer_zone': 0.03,          # 缓冲区 3%
            'min_holding_days': 14,       # 最短持有期 2周
            'price_band': 0.05,           # 价格带宽 ±5pp
            'max_legs': 2,                # 最大腿数
            'position_size_initial': 0.05, # 初始仓位 5%
            'position_size_full': 0.10,   # 完整仓位 10%
        },
        MarketMode.CONSERVATIVE: {
            'stop_loss': -0.15,           # 止损线 -15%
            'buffer_zone': 0.04,          # 缓冲区 4%
            'min_holding_days': 28,       # 最短持有期 4周
            'price_band': 0.03,           # 价格带宽 ±3pp
            'max_legs': 1,                # 最大腿数
            'position_size_initial': 0.03, # 初始仓位 3%
            'position_size_full': 0.06,   # 完整仓位 6%
        },
        MarketMode.CHOP: {  # 震荡市特殊参数
            'stop_loss': -0.15,           # 止损线 -15%
            'buffer_zone': 0.04,          # 缓冲区 4%
            'min_holding_days': 28,       # 最短持有期 4周
            'price_band': 0.03,           # 价格带宽 ±3pp
            'max_legs': 1,                # 最大腿数（强制单腿）
            'position_size_initial': 0.03, # 初始仓位 3%
            'position_size_full': 0.05,   # 完整仓位 5%
        }
    },
    
    # 市场环境判断阈值
    'market_thresholds': {
        'ma200_confirmation_days': 5,     # MA200确认天数
        'ma200_breakout_pct': 1.0,       # 突破MA200幅度要求
        'ma200_breakdown_pct': -1.0,     # 跌破MA200幅度
        'reversion_check_days': 3,       # 回落检查天数
        'chop_band_range': 0.03,         # CHOP判断的带宽 ±3%
        'chop_band_days': 10,            # CHOP带内天数阈值
        'chop_atr_ratio': 0.035,         # ATR/价格比率阈值 3.5%
        'chop_ma200_slope': 0.005,       # MA200斜率阈值 ±0.5%
        'momentum_gap_top3': 3.0,        # Top1-Top3动量差距
        'momentum_gap_top5': 8.0,        # Top1-Top5动量差距
    },
    
    # 相关性检查参数
    'correlation': {
        'max_correlation': 0.8,          # 最大相关系数
        'lookback_days': 90,             # 相关性计算天数
        'min_data_points': 60,           # 最少数据点数
    },
    
    # 交易执行参数
    'execution': {
        'windows': ['10:30', '14:00'],   # 执行窗口
        'iopv_band': 0.001,              # IOPV限价带 ±0.1%
        'qdii_premium_limit': 0.02,      # QDII溢价限制 2%
        'qdii_premium_stop': 0.03,       # QDII溢价暂停 3%
    },
    
    # 防频繁交易参数
    'anti_churning': {
        'min_score_improvement': 0.02,    # 最小分数改善要求 2%
        'max_weekly_rotations': 2,        # 每周最大轮换次数
        'cooldown_days': 7,              # 轮换冷却期
        'min_holding_before_rotation': 14, # 轮换前最短持有期
    },
    
    # Core池配置（固定持仓）
    'core_pool': {
        'target_weight': 0.60,  # Core目标权重 60%
        'holdings': {
            '510300': {'name': '沪深300', 'target': 0.20},
            '159919': {'name': '沪深300备选', 'target': 0.20},
            '510880': {'name': '上证红利', 'target': 0.15},
            '511990': {'name': '华宝添益', 'target': 0.10},
            '518880': {'name': '华安黄金', 'target': 0.10},
            '513500': {'name': '标普500', 'target': 0.05},
        }
    },
    
    # Satellite池配置（动量轮动）
    'satellite_pool': {
        'target_weight': 0.40,  # Satellite目标权重 40%
        'categories': {
            'growth': {  # 成长线（每期只选1支）
                'codes': ['588000', '512760', '512720', '516010', '159869'],
                'max_selection': 1
            },
            'new_energy': {  # 电新链（三选一）
                'codes': ['516160', '515790', '515030'],
                'max_selection': 1
            },
            'others': {  # 其他行业
                'codes': ['512400', '512800', '512000', '512170'],
                'max_selection': 2
            }
        }
    }
}


def get_mode_params(mode: MarketMode = MarketMode.BALANCED) -> Dict[str, Any]:
    """
    获取指定模式的参数配置
    
    Args:
        mode: 市场模式
    
    Returns:
        参数配置字典
    """
    return STRATEGY_PARAMS['mode_params'].get(mode, STRATEGY_PARAMS['mode_params'][MarketMode.BALANCED])


def get_current_params(market_regime: str = 'NEUTRAL') -> Dict[str, Any]:
    """
    根据市场状态获取当前应使用的参数
    
    Args:
        market_regime: 市场状态 ('TREND', 'CHOP', 'BEAR', 'NEUTRAL')
    
    Returns:
        当前参数配置
    """
    if market_regime == 'CHOP':
        return get_mode_params(MarketMode.CHOP)
    elif market_regime == 'TREND':
        return get_mode_params(MarketMode.AGGRESSIVE)
    elif market_regime == 'BEAR':
        return get_mode_params(MarketMode.CONSERVATIVE)
    else:
        return get_mode_params(MarketMode.BALANCED)