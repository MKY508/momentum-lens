"""
Risk management module for stop loss, position limits, and drawdown monitoring.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

from backend.config.config import get_config_manager
from backend.models import Holdings, Transactions, PortfolioSnapshot
from backend.models.base import get_db
from backend.core.portfolio_manager import Position

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    """Alert type classification with precise enums"""
    STOP_LOSS = "STOP_LOSS"
    TRAILING_STOP = "TRAILING_STOP"
    DRAWDOWN = "DRAWDOWN"
    CORRELATION = "CORRELATION"
    VOLATILITY = "VOLATILITY"
    POSITION_SIZE = "POSITION_SIZE"
    HOLDING_PERIOD = "HOLDING_PERIOD"
    # New precise alert types
    YEARLINE_UP = "YEARLINE_UP"
    YEARLINE_DOWN = "YEARLINE_DOWN"
    CHOP_ON = "CHOP_ON"
    CHOP_OFF = "CHOP_OFF"
    STOP_HIT = "STOP_HIT"
    MA200_BREAK = "MA200_BREAK"
    QDII_OK = "QDII_OK"
    QDII_PAUSE = "QDII_PAUSE"
    TURNOVER_PNL_NEG = "TURNOVER_PNL_NEG"


@dataclass
class RiskAlert:
    """Risk alert data structure"""
    alert_type: AlertType
    risk_level: RiskLevel
    code: Optional[str]
    message: str
    value: float
    threshold: float
    action_required: str
    timestamp: datetime


class RiskManager:
    """Risk management and monitoring"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        self.alerts = []
    
    def check_stop_loss(self, positions: List[Position], 
                       market_regime: Dict[str, Any]) -> List[RiskAlert]:
        """
        Check stop loss with adaptive thresholds
        - Default: -12%
        - Strong trend (above MA200 & CHOP=OFF): -10%
        - Oscillation or high volatility: -15%
        
        Args:
            positions: List of current positions
            market_regime: Market regime information
            
        Returns:
            List of stop loss alerts
        """
        alerts = []
        
        for position in positions:
            # Calculate current loss percentage
            loss_pct = position.unrealized_pnl_pct
            
            # Determine stop loss threshold based on market conditions
            yearline = market_regime.get('yearline', False)
            chop = market_regime.get('chop', False)
            atr20_pct = market_regime.get('atr20_pct', 0)
            
            if yearline and not chop:
                # Strong trend - tighter stop
                stop_loss_threshold = -0.10  # -10%
                condition = "Strong trend"
            elif chop or atr20_pct > 4:
                # High volatility - wider stop
                stop_loss_threshold = -0.15  # -15%
                condition = "High volatility/oscillation"
            else:
                # Default
                stop_loss_threshold = -0.12  # -12%
                condition = "Default"
            
            if loss_pct <= stop_loss_threshold:
                # Stop loss hit
                alert = RiskAlert(
                    alert_type=AlertType.STOP_HIT,
                    risk_level=RiskLevel.CRITICAL,
                    code=position.code,
                    message=f"Position {position.code} hit stop loss ({condition})",
                    value=loss_pct,
                    threshold=stop_loss_threshold,
                    action_required="IMMEDIATE SELL",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
            
            elif loss_pct <= stop_loss_max:
                # Warning stop loss level
                alert = RiskAlert(
                    alert_type=AlertType.STOP_LOSS,
                    risk_level=RiskLevel.HIGH,
                    code=position.code,
                    message=f"Position {position.code} approaching stop loss",
                    value=loss_pct,
                    threshold=stop_loss_max,
                    action_required="CONSIDER SELLING",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        return alerts
    
    def check_trailing_stop(self, positions: List[Position]) -> List[RiskAlert]:
        """
        Check trailing stop conditions
        
        Args:
            positions: List of current positions
            
        Returns:
            List of trailing stop alerts
        """
        alerts = []
        
        with get_db() as db:
            for position in positions:
                holding = db.query(Holdings).filter(
                    Holdings.user_id == self.user_id,
                    Holdings.code == position.code,
                    Holdings.is_active == True
                ).first()
                
                if not holding or not holding.trailing_stop:
                    continue
                
                # Get highest price since entry
                highest_price = holding.highest_price or holding.avg_entry_price
                
                # Update highest price if current is higher
                if position.current_price > highest_price:
                    holding.highest_price = position.current_price
                    highest_price = position.current_price
                    db.commit()
                
                # Calculate drawdown from peak
                drawdown = (position.current_price - highest_price) / highest_price
                trailing_stop_pct = -0.08  # Default 8% trailing stop
                
                if drawdown <= trailing_stop_pct:
                    alert = RiskAlert(
                        alert_type=AlertType.TRAILING_STOP,
                        risk_level=RiskLevel.HIGH,
                        code=position.code,
                        message=f"Position {position.code} hit trailing stop",
                        value=drawdown,
                        threshold=trailing_stop_pct,
                        action_required="SELL",
                        timestamp=datetime.now()
                    )
                    alerts.append(alert)
        
        return alerts
    
    def check_min_holding(self, positions: List[Position]) -> List[RiskAlert]:
        """
        Check minimum holding period constraints
        
        Args:
            positions: List of current positions
            
        Returns:
            List of holding period alerts
        """
        alerts = []
        min_days = self.config.trading_params.min_holding_days
        
        for position in positions:
            if position.days_held < min_days and position.unrealized_pnl_pct < 0:
                alert = RiskAlert(
                    alert_type=AlertType.HOLDING_PERIOD,
                    risk_level=RiskLevel.MEDIUM,
                    code=position.code,
                    message=f"Position {position.code} in loss but minimum holding period not met",
                    value=position.days_held,
                    threshold=min_days,
                    action_required=f"HOLD for {min_days - position.days_held} more days",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        return alerts
    
    def check_buffer_zone(self, 
                         code: str,
                         current_score: float,
                         previous_score: float) -> bool:
        """
        Check if score change exceeds buffer zone
        
        Args:
            code: ETF code
            current_score: Current momentum score
            previous_score: Previous momentum score
            
        Returns:
            True if buffer zone exceeded
        """
        score_change = abs(current_score - previous_score)
        buffer_min = self.config.trading_params.buffer_zone_min
        buffer_max = self.config.trading_params.buffer_zone_max
        
        # Use adaptive buffer based on score magnitude
        if abs(current_score) > 0.2:
            buffer = buffer_max
        else:
            buffer = buffer_min
        
        return score_change >= buffer
    
    def check_ma200_break(self, positions: List[Position], 
                         etf_prices: Dict[str, pd.DataFrame]) -> List[RiskAlert]:
        """
        Check if ETF breaks its own 200-day MA
        If break detected -> halve position
        
        Args:
            positions: List of current positions
            etf_prices: Price data for ETFs
            
        Returns:
            List of MA200 break alerts
        """
        alerts = []
        
        for position in positions:
            if position.code not in etf_prices:
                continue
                
            df = etf_prices[position.code]
            if len(df) < 200:
                continue
            
            # Calculate MA200
            ma200 = df['close'].rolling(window=200, min_periods=200).mean().iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # Check if price broke below MA200
            if current_price < ma200:
                distance_pct = ((current_price - ma200) / ma200) * 100
                
                alert = RiskAlert(
                    alert_type=AlertType.MA200_BREAK,
                    risk_level=RiskLevel.HIGH,
                    code=position.code,
                    message=f"{position.code} broke below MA200 ({distance_pct:.2f}%)",
                    value=current_price,
                    threshold=ma200,
                    action_required="HALVE POSITION",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        return alerts
    
    def check_unlock_pullback(self, hs300_data: pd.DataFrame, 
                             recent_trades: List[Transactions]) -> List[RiskAlert]:
        """
        Check unlock and pullback protection conditions
        - Unlock: HS300 above MA200 for 5 consecutive days, last day ≥1%
        - Pullback: If close_vs_ma200 ≤-1% within 3 days after adding 2nd leg -> clear 2nd leg
        
        Args:
            hs300_data: HS300 price data with MA200
            recent_trades: Recent trading transactions
            
        Returns:
            List of unlock/pullback alerts
        """
        alerts = []
        
        if len(hs300_data) < 200:
            return alerts
        
        # Calculate MA200
        hs300_data['ma200'] = hs300_data['close'].rolling(window=200, min_periods=200).mean()
        
        # Check unlock condition
        last_5_days = hs300_data.tail(5)
        if len(last_5_days) == 5:
            all_above = all(last_5_days['close'] > last_5_days['ma200'])
            last_day_return = (last_5_days['close'].iloc[-1] / last_5_days['close'].iloc[-2] - 1) * 100
            
            if all_above and last_day_return >= 1:
                alert = RiskAlert(
                    alert_type=AlertType.YEARLINE_UP,
                    risk_level=RiskLevel.LOW,
                    code=None,
                    message="Market unlock condition met - HS300 above MA200 for 5 days",
                    value=last_day_return,
                    threshold=1.0,
                    action_required="CONSIDER ADDING POSITIONS",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        # Check pullback protection for recent 2nd leg additions
        three_days_ago = datetime.now() - timedelta(days=3)
        recent_2nd_legs = [t for t in recent_trades 
                          if t.transaction_date >= three_days_ago.date() 
                          and '2nd leg' in t.notes]
        
        if recent_2nd_legs:
            current_vs_ma200 = ((hs300_data['close'].iloc[-1] - hs300_data['ma200'].iloc[-1]) / 
                               hs300_data['ma200'].iloc[-1]) * 100
            
            if current_vs_ma200 <= -1:
                for trade in recent_2nd_legs:
                    alert = RiskAlert(
                        alert_type=AlertType.YEARLINE_DOWN,
                        risk_level=RiskLevel.HIGH,
                        code=trade.code,
                        message=f"Pullback protection triggered for 2nd leg {trade.code}",
                        value=current_vs_ma200,
                        threshold=-1.0,
                        action_required="CLEAR 2ND LEG",
                        timestamp=datetime.now()
                    )
                    alerts.append(alert)
        
        return alerts
    
    def check_qdii_premium(self, code: str, premium: float) -> Optional[RiskAlert]:
        """
        Check QDII (513500) premium validation
        
        Args:
            code: ETF code
            premium: Current premium/discount percentage
            
        Returns:
            Alert if QDII premium exceeds limits
        """
        if code != '513500':
            return None
        
        # QDII premium limit (example: 2%)
        PREMIUM_LIMIT = 2.0
        
        if abs(premium) > PREMIUM_LIMIT:
            alert = RiskAlert(
                alert_type=AlertType.QDII_PAUSE,
                risk_level=RiskLevel.MEDIUM,
                code=code,
                message=f"QDII premium {premium:.2f}% exceeds limit",
                value=premium,
                threshold=PREMIUM_LIMIT,
                action_required="PAUSE TRADING",
                timestamp=datetime.now()
            )
            return alert
        else:
            alert = RiskAlert(
                alert_type=AlertType.QDII_OK,
                risk_level=RiskLevel.LOW,
                code=code,
                message=f"QDII premium {premium:.2f}% within limits",
                value=premium,
                threshold=PREMIUM_LIMIT,
                action_required="OK TO TRADE",
                timestamp=datetime.now()
            )
            return alert
    
    def monitor_drawdown(self, lookback_days: int = 30) -> RiskAlert:
        """
        Monitor portfolio drawdown
        
        Args:
            lookback_days: Number of days to look back
            
        Returns:
            Drawdown alert if threshold exceeded
        """
        with get_db() as db:
            # Get portfolio snapshots
            end_date = date.today()
            start_date = end_date - timedelta(days=lookback_days)
            
            snapshots = db.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.user_id == self.user_id,
                PortfolioSnapshot.date >= start_date
            ).order_by(PortfolioSnapshot.date).all()
            
            if not snapshots:
                return None
            
            # Calculate drawdown
            values = [s.total_value for s in snapshots]
            peak = max(values)
            current = values[-1]
            drawdown = (current - peak) / peak if peak > 0 else 0
            
            # Check thresholds
            if drawdown <= -0.20:  # 20% drawdown
                return RiskAlert(
                    alert_type=AlertType.DRAWDOWN,
                    risk_level=RiskLevel.CRITICAL,
                    code=None,
                    message="Portfolio drawdown exceeds 20%",
                    value=drawdown,
                    threshold=-0.20,
                    action_required="REDUCE RISK EXPOSURE",
                    timestamp=datetime.now()
                )
            elif drawdown <= -0.15:  # 15% drawdown
                return RiskAlert(
                    alert_type=AlertType.DRAWDOWN,
                    risk_level=RiskLevel.HIGH,
                    code=None,
                    message="Portfolio drawdown exceeds 15%",
                    value=drawdown,
                    threshold=-0.15,
                    action_required="REVIEW POSITIONS",
                    timestamp=datetime.now()
                )
            elif drawdown <= -0.10:  # 10% drawdown
                return RiskAlert(
                    alert_type=AlertType.DRAWDOWN,
                    risk_level=RiskLevel.MEDIUM,
                    code=None,
                    message="Portfolio drawdown exceeds 10%",
                    value=drawdown,
                    threshold=-0.10,
                    action_required="MONITOR CLOSELY",
                    timestamp=datetime.now()
                )
        
        return None
    
    def check_position_concentration(self, positions: List[Position]) -> List[RiskAlert]:
        """
        Check for position concentration risk
        
        Args:
            positions: List of current positions
            
        Returns:
            List of concentration alerts
        """
        alerts = []
        
        if not positions:
            return alerts
        
        # Calculate total value
        total_value = sum(p.market_value for p in positions)
        max_position = self.config.portfolio_settings.max_single_position
        
        for position in positions:
            weight = position.market_value / total_value if total_value > 0 else 0
            
            if weight > max_position:
                alert = RiskAlert(
                    alert_type=AlertType.POSITION_SIZE,
                    risk_level=RiskLevel.HIGH,
                    code=position.code,
                    message=f"Position {position.code} exceeds maximum allocation",
                    value=weight,
                    threshold=max_position,
                    action_required="REDUCE POSITION",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        return alerts
    
    def check_correlation_risk(self, 
                              positions: List[Position],
                              correlation_matrix: pd.DataFrame) -> List[RiskAlert]:
        """
        Check for high correlation between positions
        
        Args:
            positions: List of current positions
            correlation_matrix: Correlation matrix DataFrame
            
        Returns:
            List of correlation alerts
        """
        alerts = []
        correlation_limit = self.config.market_thresholds.correlation_limit
        
        if len(positions) < 2 or correlation_matrix.empty:
            return alerts
        
        # Check pairwise correlations
        position_codes = [p.code for p in positions]
        
        for i, code1 in enumerate(position_codes):
            for code2 in position_codes[i+1:]:
                if code1 in correlation_matrix.index and code2 in correlation_matrix.columns:
                    corr = correlation_matrix.loc[code1, code2]
                    
                    if abs(corr) > correlation_limit:
                        alert = RiskAlert(
                            alert_type=AlertType.CORRELATION,
                            risk_level=RiskLevel.MEDIUM,
                            code=f"{code1}-{code2}",
                            message=f"High correlation between {code1} and {code2}",
                            value=corr,
                            threshold=correlation_limit,
                            action_required="CONSIDER DIVERSIFICATION",
                            timestamp=datetime.now()
                        )
                        alerts.append(alert)
        
        return alerts
    
    def calculate_var(self, 
                     positions: List[Position],
                     confidence_level: float = 0.95,
                     horizon_days: int = 1) -> float:
        """
        Calculate Value at Risk (VaR)
        
        Args:
            positions: List of current positions
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            horizon_days: Time horizon in days
            
        Returns:
            VaR value
        """
        if not positions:
            return 0
        
        # Get historical returns for positions
        with get_db() as db:
            returns_data = {}
            
            for position in positions:
                # Get price history
                from backend.models import PriceHistory
                
                prices = db.query(PriceHistory).filter(
                    PriceHistory.code == position.code
                ).order_by(PriceHistory.date.desc()).limit(252).all()
                
                if prices:
                    price_series = pd.Series([p.close for p in reversed(prices)])
                    returns = price_series.pct_change().dropna()
                    returns_data[position.code] = returns
            
            if not returns_data:
                return 0
            
            # Create portfolio returns
            returns_df = pd.DataFrame(returns_data)
            
            # Calculate portfolio weights
            total_value = sum(p.market_value for p in positions)
            weights = [p.market_value / total_value for p in positions]
            
            # Calculate portfolio returns
            portfolio_returns = returns_df.dot(weights)
            
            # Calculate VaR
            var_percentile = (1 - confidence_level) * 100
            var_daily = np.percentile(portfolio_returns, var_percentile)
            
            # Scale to horizon
            var_horizon = var_daily * np.sqrt(horizon_days) * total_value
            
            return abs(var_horizon)
    
    def calculate_turnover_efficiency(self, 
                                     portfolio_history: pd.DataFrame,
                                     months: int = 2) -> Optional[RiskAlert]:
        """
        Calculate turnover efficiency = (monthly satellite return) / (monthly satellite turnover)
        If <0 for 2 consecutive months -> reduce satellite by 10pp next month
        
        Args:
            portfolio_history: Portfolio performance history
            months: Number of months to check
            
        Returns:
            Alert if turnover efficiency is negative
        """
        if len(portfolio_history) < months * 30:
            return None
        
        # Calculate monthly metrics
        monthly_efficiency = []
        
        for i in range(months):
            month_start = -(i+1) * 30
            month_end = -i * 30 if i > 0 else None
            
            month_data = portfolio_history[month_start:month_end]
            
            # Calculate satellite return
            satellite_return = month_data['satellite_return'].sum()
            
            # Calculate satellite turnover
            satellite_turnover = month_data['satellite_turnover'].sum()
            
            if satellite_turnover > 0:
                efficiency = satellite_return / satellite_turnover
                monthly_efficiency.append(efficiency)
        
        # Check if negative for consecutive months
        if all(e < 0 for e in monthly_efficiency):
            alert = RiskAlert(
                alert_type=AlertType.TURNOVER_PNL_NEG,
                risk_level=RiskLevel.MEDIUM,
                code=None,
                message=f"Turnover efficiency negative for {months} consecutive months",
                value=monthly_efficiency[-1],
                threshold=0,
                action_required="REDUCE SATELLITE BY 10PP NEXT MONTH",
                timestamp=datetime.now()
            )
            return alert
        
        return None
    
    def generate_alerts(self, positions: List[Position], 
                       market_regime: Dict[str, Any] = None,
                       etf_prices: Dict[str, pd.DataFrame] = None) -> List[RiskAlert]:
        """
        Generate all risk alerts for current positions
        
        Args:
            positions: List of current positions
            
        Returns:
            List of all risk alerts
        """
        all_alerts = []
        
        # Stop loss checks
        all_alerts.extend(self.check_stop_loss(positions))
        
        # Trailing stop checks
        all_alerts.extend(self.check_trailing_stop(positions))
        
        # Holding period checks
        all_alerts.extend(self.check_min_holding(positions))
        
        # Position concentration checks
        all_alerts.extend(self.check_position_concentration(positions))
        
        # Drawdown check
        drawdown_alert = self.monitor_drawdown()
        if drawdown_alert:
            all_alerts.append(drawdown_alert)
        
        # Sort by risk level (CRITICAL first)
        risk_order = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 3
        }
        all_alerts.sort(key=lambda x: risk_order[x.risk_level])
        
        # Store alerts
        self.alerts = all_alerts
        
        return all_alerts
    
    def get_risk_metrics(self, positions: List[Position]) -> Dict[str, float]:
        """
        Calculate comprehensive risk metrics
        
        Args:
            positions: List of current positions
            
        Returns:
            Dictionary of risk metrics
        """
        metrics = {
            'total_positions': len(positions),
            'positions_in_loss': 0,
            'positions_in_profit': 0,
            'avg_loss': 0,
            'avg_profit': 0,
            'largest_loss': 0,
            'largest_profit': 0,
            'portfolio_var_95': 0,
            'portfolio_volatility': 0
        }
        
        if not positions:
            return metrics
        
        # Calculate P&L metrics
        losses = [p.unrealized_pnl_pct for p in positions if p.unrealized_pnl_pct < 0]
        profits = [p.unrealized_pnl_pct for p in positions if p.unrealized_pnl_pct > 0]
        
        metrics['positions_in_loss'] = len(losses)
        metrics['positions_in_profit'] = len(profits)
        
        if losses:
            metrics['avg_loss'] = np.mean(losses)
            metrics['largest_loss'] = min(losses)
        
        if profits:
            metrics['avg_profit'] = np.mean(profits)
            metrics['largest_profit'] = max(profits)
        
        # Calculate VaR
        metrics['portfolio_var_95'] = self.calculate_var(positions)
        
        return metrics


def get_risk_manager(user_id: int) -> RiskManager:
    """Get risk manager instance for user"""
    return RiskManager(user_id)