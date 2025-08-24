"""
Mathematical and statistical calculation utilities.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_returns(prices: pd.Series, 
                     periods: List[int] = [5, 20, 60, 120]) -> Dict[int, float]:
    """
    Calculate returns over multiple periods
    
    Args:
        prices: Series of prices
        periods: List of periods in days
        
    Returns:
        Dictionary of {period: return}
    """
    returns = {}
    
    for period in periods:
        if len(prices) >= period + 1:
            current = prices.iloc[-1]
            past = prices.iloc[-period-1]
            returns[period] = (current - past) / past if past != 0 else 0
        else:
            returns[period] = 0
    
    return returns


def calculate_correlation_matrix(returns_dict: Dict[str, pd.Series],
                                method: str = 'pearson',
                                min_periods: int = 20) -> pd.DataFrame:
    """
    Calculate correlation matrix from returns
    
    Args:
        returns_dict: Dictionary of {symbol: returns_series}
        method: Correlation method ('pearson', 'spearman', 'kendall')
        min_periods: Minimum periods for correlation calculation
        
    Returns:
        Correlation matrix DataFrame
    """
    if not returns_dict:
        return pd.DataFrame()
    
    # Align all series to same index
    returns_df = pd.DataFrame(returns_dict)
    
    # Calculate correlation
    if method == 'pearson':
        corr_matrix = returns_df.corr(min_periods=min_periods)
    elif method == 'spearman':
        corr_matrix = returns_df.corr(method='spearman', min_periods=min_periods)
    elif method == 'kendall':
        corr_matrix = returns_df.corr(method='kendall', min_periods=min_periods)
    else:
        raise ValueError(f"Unknown correlation method: {method}")
    
    return corr_matrix


def calculate_sharpe_ratio(returns: pd.Series,
                          risk_free_rate: float = 0.02,
                          periods_per_year: int = 252) -> float:
    """
    Calculate Sharpe ratio
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods per year
        
    Returns:
        Sharpe ratio
    """
    if len(returns) < 2:
        return 0
    
    # Convert annual risk-free rate to period rate
    rf_period = risk_free_rate / periods_per_year
    
    # Calculate excess returns
    excess_returns = returns - rf_period
    
    # Calculate Sharpe ratio
    mean_excess = excess_returns.mean()
    std_returns = returns.std()
    
    if std_returns == 0:
        return 0
    
    sharpe = mean_excess / std_returns * np.sqrt(periods_per_year)
    
    return sharpe


def calculate_sortino_ratio(returns: pd.Series,
                           target_return: float = 0,
                           periods_per_year: int = 252) -> float:
    """
    Calculate Sortino ratio (uses downside deviation)
    
    Args:
        returns: Series of returns
        target_return: Target return (MAR)
        periods_per_year: Number of periods per year
        
    Returns:
        Sortino ratio
    """
    if len(returns) < 2:
        return 0
    
    # Calculate downside returns
    downside_returns = returns[returns < target_return]
    
    if len(downside_returns) == 0:
        return float('inf')  # No downside risk
    
    # Calculate downside deviation
    downside_std = np.sqrt(np.mean(downside_returns ** 2))
    
    if downside_std == 0:
        return 0
    
    # Calculate Sortino ratio
    mean_return = returns.mean()
    sortino = (mean_return - target_return) / downside_std * np.sqrt(periods_per_year)
    
    return sortino


def calculate_max_drawdown(prices: pd.Series) -> Tuple[float, int, date, date]:
    """
    Calculate maximum drawdown and duration
    
    Args:
        prices: Series of prices
        
    Returns:
        Tuple of (max_drawdown, duration_days, peak_date, trough_date)
    """
    if len(prices) < 2:
        return 0, 0, None, None
    
    # Calculate cumulative returns
    cumulative = (prices / prices.iloc[0])
    
    # Calculate running maximum
    running_max = cumulative.expanding().max()
    
    # Calculate drawdown
    drawdown = (cumulative - running_max) / running_max
    
    # Find maximum drawdown
    max_dd = drawdown.min()
    
    if max_dd == 0:
        return 0, 0, None, None
    
    # Find the peak and trough
    max_dd_idx = drawdown.idxmin()
    peak_idx = cumulative[:max_dd_idx].idxmax()
    
    # Calculate duration
    if isinstance(prices.index[0], (datetime, date)):
        duration = (max_dd_idx - peak_idx).days
    else:
        duration = max_dd_idx - peak_idx
    
    return max_dd, duration, peak_idx, max_dd_idx


def calculate_turnover_efficiency(trades: List[Dict],
                                 portfolio_value: float,
                                 period_days: int = 30) -> float:
    """
    Calculate portfolio turnover efficiency
    
    Args:
        trades: List of trade dictionaries
        portfolio_value: Total portfolio value
        period_days: Period in days
        
    Returns:
        Turnover efficiency ratio
    """
    if not trades or portfolio_value == 0:
        return 0
    
    # Calculate total traded value
    total_traded = sum(abs(trade.get('amount', 0)) for trade in trades)
    
    # Calculate turnover rate
    turnover_rate = total_traded / portfolio_value
    
    # Annualize if needed
    if period_days < 365:
        turnover_rate = turnover_rate * (365 / period_days)
    
    # Calculate efficiency (lower is better)
    # Efficiency = 1 / (1 + turnover_rate)
    efficiency = 1 / (1 + turnover_rate)
    
    return efficiency


def calculate_atr_series(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    
    Args:
        df: DataFrame with high, low, close columns
        period: ATR period
        
    Returns:
        ATR series
    """
    if len(df) < 2:
        return pd.Series()
    
    # Calculate true range
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR
    atr = true_range.rolling(window=period, min_periods=1).mean()
    
    return atr


def calculate_volatility(returns: pd.Series,
                        window: int = 20,
                        annualize: bool = True) -> pd.Series:
    """
    Calculate rolling volatility
    
    Args:
        returns: Series of returns
        window: Rolling window size
        annualize: Whether to annualize volatility
        
    Returns:
        Volatility series
    """
    volatility = returns.rolling(window=window, min_periods=1).std()
    
    if annualize:
        volatility = volatility * np.sqrt(252)
    
    return volatility


def calculate_beta(asset_returns: pd.Series,
                  market_returns: pd.Series) -> float:
    """
    Calculate beta relative to market
    
    Args:
        asset_returns: Asset returns series
        market_returns: Market returns series
        
    Returns:
        Beta value
    """
    if len(asset_returns) < 2 or len(market_returns) < 2:
        return 1.0
    
    # Align series
    aligned = pd.DataFrame({
        'asset': asset_returns,
        'market': market_returns
    }).dropna()
    
    if len(aligned) < 2:
        return 1.0
    
    # Calculate covariance and variance
    covariance = aligned['asset'].cov(aligned['market'])
    market_variance = aligned['market'].var()
    
    if market_variance == 0:
        return 1.0
    
    beta = covariance / market_variance
    
    return beta


def calculate_alpha(asset_returns: pd.Series,
                   market_returns: pd.Series,
                   risk_free_rate: float = 0.02) -> float:
    """
    Calculate alpha (Jensen's alpha)
    
    Args:
        asset_returns: Asset returns series
        market_returns: Market returns series
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Alpha value
    """
    # Calculate beta
    beta = calculate_beta(asset_returns, market_returns)
    
    # Convert to period returns
    rf_period = risk_free_rate / 252
    
    # Calculate expected return (CAPM)
    market_premium = market_returns.mean() - rf_period
    expected_return = rf_period + beta * market_premium
    
    # Calculate alpha
    actual_return = asset_returns.mean()
    alpha = actual_return - expected_return
    
    # Annualize
    alpha_annual = alpha * 252
    
    return alpha_annual


def calculate_information_ratio(asset_returns: pd.Series,
                              benchmark_returns: pd.Series) -> float:
    """
    Calculate information ratio
    
    Args:
        asset_returns: Asset returns series
        benchmark_returns: Benchmark returns series
        
    Returns:
        Information ratio
    """
    if len(asset_returns) < 2 or len(benchmark_returns) < 2:
        return 0
    
    # Calculate active returns
    active_returns = asset_returns - benchmark_returns
    
    # Calculate tracking error
    tracking_error = active_returns.std()
    
    if tracking_error == 0:
        return 0
    
    # Calculate information ratio
    ir = active_returns.mean() / tracking_error * np.sqrt(252)
    
    return ir


def calculate_calmar_ratio(returns: pd.Series,
                         prices: pd.Series,
                         periods_per_year: int = 252) -> float:
    """
    Calculate Calmar ratio (return / max drawdown)
    
    Args:
        returns: Returns series
        prices: Prices series
        periods_per_year: Periods per year
        
    Returns:
        Calmar ratio
    """
    # Calculate annualized return
    annual_return = returns.mean() * periods_per_year
    
    # Calculate max drawdown
    max_dd, _, _, _ = calculate_max_drawdown(prices)
    
    if max_dd == 0:
        return float('inf')
    
    calmar = annual_return / abs(max_dd)
    
    return calmar


def calculate_rolling_correlation(series1: pd.Series,
                                 series2: pd.Series,
                                 window: int = 90) -> pd.Series:
    """
    Calculate rolling correlation between two series
    
    Args:
        series1: First series
        series2: Second series
        window: Rolling window size
        
    Returns:
        Rolling correlation series
    """
    # Align series
    aligned = pd.DataFrame({
        's1': series1,
        's2': series2
    })
    
    # Calculate rolling correlation
    rolling_corr = aligned['s1'].rolling(window=window).corr(aligned['s2'])
    
    return rolling_corr


def calculate_momentum_score(returns_60d: float,
                            returns_120d: float,
                            weight_60d: float = 0.6,
                            weight_120d: float = 0.4) -> float:
    """
    Calculate momentum score
    
    Args:
        returns_60d: 60-day returns
        returns_120d: 120-day returns
        weight_60d: Weight for 60-day returns
        weight_120d: Weight for 120-day returns
        
    Returns:
        Momentum score
    """
    score = weight_60d * returns_60d + weight_120d * returns_120d
    return score


def calculate_portfolio_metrics(positions: List[Dict],
                               prices: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate portfolio-level metrics
    
    Args:
        positions: List of position dictionaries
        prices: Dictionary of current prices
        
    Returns:
        Dictionary of portfolio metrics
    """
    if not positions:
        return {
            'total_value': 0,
            'total_cost': 0,
            'total_pnl': 0,
            'total_pnl_pct': 0,
            'num_positions': 0,
            'avg_position_size': 0
        }
    
    total_value = 0
    total_cost = 0
    
    for position in positions:
        code = position['code']
        shares = position['shares']
        avg_price = position['avg_price']
        
        current_price = prices.get(code, avg_price)
        
        position_value = shares * current_price
        position_cost = shares * avg_price
        
        total_value += position_value
        total_cost += position_cost
    
    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost if total_cost > 0 else 0
    
    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'num_positions': len(positions),
        'avg_position_size': total_value / len(positions) if positions else 0
    }