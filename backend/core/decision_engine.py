"""
Trading decision engine for Momentum Lens.
Implements momentum scoring, correlation checking, and signal generation.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

from backend.config.config import get_config_manager
from backend.models import TradingSignals, MarketIndicators, Holdings
from backend.models.base import get_db
from backend.utils.calculations import calculate_correlation_matrix

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classification"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    CHOPPY = "CHOPPY"


class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    REBALANCE = "REBALANCE"


class SignalStrength(Enum):
    """Signal strength classification"""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


@dataclass
class TradingSignal:
    """Trading signal data structure"""
    code: str
    signal_type: SignalType
    action: str
    portfolio_type: str
    momentum_score: float
    return_60d: float
    return_120d: float
    correlation_max: float
    correlation_avg: float
    passes_buffer: bool
    passes_holding_period: bool
    passes_correlation: bool
    passes_leg_limit: bool
    suggested_weight: float
    confidence: float
    signal_strength: SignalStrength
    notes: str = ""


class DecisionEngine:
    """Core decision engine for trading logic"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        self._cache = {}
    
    def assess_market_regime(self, indicators: MarketIndicators, 
                            etf_scores: Dict[str, float] = None,
                            price_history: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Assess market regime with yearline and CHOP (2 out of 3 conditions)
        
        Args:
            indicators: Market indicators for current date
            etf_scores: Current ETF momentum scores
            price_history: Recent price history for CHOP calculation
            
        Returns:
            Dictionary with regime details
        """
        regime = {
            'yearline': False,
            'chop': False,
            'chop_conditions_met': [],
            'regime': MarketRegime.NEUTRAL,
            'atr20_pct': 0
        }
        
        if not indicators:
            return regime
        
        # Check yearline (MA200)
        above_yearline = indicators.above_yearline
        regime['yearline'] = above_yearline
        
        # Calculate CHOP conditions (need 2 out of 3)
        chop_conditions = []
        
        # Condition a: Days in MA200±3% band ≥10 in last 30 days
        if price_history is not None and len(price_history) >= 30:
            ma200 = price_history['ma200'].iloc[-30:]
            close = price_history['close'].iloc[-30:]
            
            # Count days within ±3% of MA200
            within_band = abs((close - ma200) / ma200) <= 0.03
            days_in_band = within_band.sum()
            
            if days_in_band >= 10:
                chop_conditions.append('a_band')
                regime['chop_conditions_met'].append(f"Days in MA200±3% band: {days_in_band}/30")
        
        # Condition b: ATR20/price ≥3.5% AND MA200 5-day slope within ±0.5%
        if indicators.atr20 and indicators.hs300_close:
            atr20_pct = (indicators.atr20 / indicators.hs300_close) * 100
            regime['atr20_pct'] = atr20_pct
            
            if atr20_pct >= 3.5:
                # Check MA200 slope
                if price_history is not None and len(price_history) >= 5:
                    ma200_recent = price_history['ma200'].iloc[-5:]
                    if len(ma200_recent) == 5:
                        ma200_slope = ((ma200_recent.iloc[-1] - ma200_recent.iloc[0]) / 
                                      ma200_recent.iloc[0]) * 100 / 5  # Daily slope
                        
                        if abs(ma200_slope) <= 0.5:
                            chop_conditions.append('b_volatility')
                            regime['chop_conditions_met'].append(
                                f"ATR20/price: {atr20_pct:.2f}%, MA200 slope: {ma200_slope:.2f}%"
                            )
        
        # Condition c: Top1-Top3 spread <3% AND Top1-Top5 spread <8%
        if etf_scores:
            sorted_scores = sorted(etf_scores.values(), reverse=True)
            if len(sorted_scores) >= 5:
                top1 = sorted_scores[0]
                top3 = sorted_scores[2] if len(sorted_scores) > 2 else sorted_scores[-1]
                top5 = sorted_scores[4] if len(sorted_scores) > 4 else sorted_scores[-1]
                
                spread_1_3 = abs(top1 - top3) * 100
                spread_1_5 = abs(top1 - top5) * 100
                
                if spread_1_3 < 3 and spread_1_5 < 8:
                    chop_conditions.append('c_spread')
                    regime['chop_conditions_met'].append(
                        f"Top1-Top3 spread: {spread_1_3:.2f}%, Top1-Top5 spread: {spread_1_5:.2f}%"
                    )
        
        # CHOP is ON if 2 or more conditions are met
        regime['chop'] = len(chop_conditions) >= 2
        
        # Determine overall regime
        if above_yearline:
            if not regime['chop']:
                regime['regime'] = MarketRegime.BULLISH
            else:
                regime['regime'] = MarketRegime.CHOPPY
        else:
            regime['regime'] = MarketRegime.BEARISH
        
        return regime
    
    def calculate_momentum_score(self, 
                                return_60d: float,
                                return_120d: float) -> float:
        """
        Calculate momentum score using FIXED weighted returns
        Score = 0.6 × r60 + 0.4 × r120 (NOT configurable)
        
        Args:
            return_60d: 60-day return (percentage)
            return_120d: 120-day return (percentage)
            
        Returns:
            Momentum score
        """
        # FIXED weights per requirements - NOT configurable
        weight_60d = 0.6
        weight_120d = 0.4
        
        # Convert to decimal if needed
        if abs(return_60d) > 1:
            return_60d = return_60d / 100
        if abs(return_120d) > 1:
            return_120d = return_120d / 100
        
        score = (weight_60d * return_60d) + (weight_120d * return_120d)
        return score
    
    def check_correlation(self,
                         etf_code: str,
                         existing_holdings: List[str],
                         correlation_matrix: pd.DataFrame,
                         anchor_first: bool = True) -> Tuple[bool, float, float, str]:
        """
        Check correlation with existing holdings
        Anchor on Top1, find next best with ρ ≤ 0.8
        
        Args:
            etf_code: ETF to check
            existing_holdings: List of currently held ETF codes
            correlation_matrix: Correlation matrix DataFrame
            anchor_first: Whether to anchor on first holding (Top1)
            
        Returns:
            Tuple of (passes_check, max_correlation, avg_correlation, anchor_code)
        """
        if not existing_holdings or correlation_matrix.empty:
            return True, 0.0, 0.0, None
        
        correlations = {}
        correlation_limit = 0.8  # Fixed at 0.8 per requirements
        
        # If anchoring, only check against first holding (Top1)
        if anchor_first and len(existing_holdings) > 0:
            anchor = existing_holdings[0]
            if anchor in correlation_matrix.columns and etf_code in correlation_matrix.index:
                corr = abs(correlation_matrix.loc[etf_code, anchor])
                correlations[anchor] = corr
                
                passes = corr <= correlation_limit
                return passes, corr, corr, anchor
        else:
            # Check against all holdings
            for holding in existing_holdings:
                if holding in correlation_matrix.columns and etf_code in correlation_matrix.index:
                    corr = abs(correlation_matrix.loc[etf_code, holding])
                    correlations[holding] = corr
        
        if not correlations:
            return True, 0.0, 0.0, None
        
        max_corr = max(correlations.values())
        avg_corr = np.mean(list(correlations.values()))
        max_corr_code = max(correlations, key=correlations.get)
        
        passes = max_corr <= correlation_limit
        
        return passes, max_corr, avg_corr, max_corr_code
    
    def generate_signals(self,
                        date: date,
                        etf_prices: Dict[str, pd.DataFrame],
                        market_indicators: MarketIndicators,
                        current_holdings: List[Holdings]) -> List[TradingSignal]:
        """
        Generate trading signals for all ETFs
        
        Args:
            date: Current date
            etf_prices: Dictionary of ETF price DataFrames
            market_indicators: Current market indicators
            current_holdings: List of current holdings
            
        Returns:
            List of trading signals
        """
        signals = []
        
        # Assess market regime
        regime = self.assess_market_regime(market_indicators)
        
        # Skip signal generation in bearish regime
        if regime == MarketRegime.BEARISH:
            logger.info(f"Market regime is BEARISH, generating SELL signals only")
            return self._generate_exit_signals(current_holdings)
        
        # Get ETF pools
        etf_pools = self.config_manager.get_etf_pools()
        
        # Calculate returns and scores for all ETFs
        scores = {}
        for etf in etf_pools:
            if not etf.enabled or etf.code not in etf_prices:
                continue
            
            df = etf_prices[etf.code]
            if len(df) < 120:
                continue
            
            # Calculate returns
            current_price = df.iloc[-1]['close']
            price_60d_ago = df.iloc[-60]['close'] if len(df) >= 60 else df.iloc[0]['close']
            price_120d_ago = df.iloc[-120]['close'] if len(df) >= 120 else df.iloc[0]['close']
            
            return_60d = (current_price - price_60d_ago) / price_60d_ago
            return_120d = (current_price - price_120d_ago) / price_120d_ago
            
            # Calculate momentum score
            score = self.calculate_momentum_score(return_60d, return_120d)
            
            scores[etf.code] = {
                'score': score,
                'return_60d': return_60d,
                'return_120d': return_120d,
                'category': etf.category,
                'style': etf.style
            }
        
        # Sort by score
        sorted_etfs = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Calculate correlation matrix
        correlation_matrix = self._calculate_correlation_matrix(etf_prices)
        
        # Get current holding codes
        holding_codes = [h.code for h in current_holdings]
        
        # Generate signals
        for rank, (code, data) in enumerate(sorted_etfs, 1):
            # Check qualifications
            qualifications = self.check_qualifications(
                code, 
                data['score'],
                current_holdings,
                correlation_matrix,
                holding_codes
            )
            
            # Determine signal type and action
            signal_type, action = self._determine_signal_action(
                code,
                data['score'],
                qualifications,
                holding_codes,
                regime
            )
            
            # Calculate suggested weight
            suggested_weight = self._calculate_suggested_weight(
                data['category'],
                rank,
                len(holding_codes)
            )
            
            # Determine signal strength
            signal_strength = self._determine_signal_strength(
                data['score'],
                qualifications['confidence']
            )
            
            # Create signal
            signal = TradingSignal(
                code=code,
                signal_type=signal_type,
                action=action,
                portfolio_type=data['category'],
                momentum_score=data['score'],
                return_60d=data['return_60d'],
                return_120d=data['return_120d'],
                correlation_max=qualifications['correlation_max'],
                correlation_avg=qualifications['correlation_avg'],
                passes_buffer=qualifications['passes_buffer'],
                passes_holding_period=qualifications['passes_holding_period'],
                passes_correlation=qualifications['passes_correlation'],
                passes_leg_limit=qualifications['passes_leg_limit'],
                suggested_weight=suggested_weight,
                confidence=qualifications['confidence'],
                signal_strength=signal_strength
            )
            
            signals.append(signal)
        
        return signals
    
    def check_qualifications(self,
                            code: str,
                            score: float,
                            current_holdings: List[Holdings],
                            correlation_matrix: pd.DataFrame,
                            holding_codes: List[str],
                            is_month_end: bool = False) -> Dict[str, Any]:
        """
        Check if ETF qualifies for trading based on various criteria
        Allow replacement ONLY at month-end (except stop-loss/MA200 break)
        
        Args:
            code: ETF code
            score: Momentum score
            current_holdings: Current holdings
            correlation_matrix: Correlation matrix
            holding_codes: List of holding codes
            is_month_end: Whether current date is month-end
            
        Returns:
            Dictionary of qualification results
        """
        results = {
            'passes_buffer': True,
            'buffer_distance': 0.0,
            'passes_holding_period': True,
            'days_since_last_trade': 999,
            'passes_correlation': True,
            'correlation_max': 0.0,
            'correlation_avg': 0.0,
            'correlation_anchor': None,
            'passes_leg_limit': True,
            'passes_month_end': is_month_end,
            'confidence': 0.5,
            'allows_replacement': False
        }
        
        # Check buffer zone
        if code in holding_codes:
            holding = next((h for h in current_holdings if h.code == code), None)
            if holding and holding.position_score:
                buffer_distance = abs(score - holding.position_score)
                results['buffer_distance'] = buffer_distance
                results['passes_buffer'] = buffer_distance >= self.config.trading_params.buffer_zone_min
        
        # Check holding period
        for holding in current_holdings:
            if holding.code == code:
                days_held = holding.days_held or 0
                results['days_since_last_trade'] = days_held
                results['passes_holding_period'] = days_held >= self.config.trading_params.min_holding_days
                break
        
        # Check correlation
        passes_corr, max_corr, avg_corr = self.check_correlation(
            code,
            holding_codes,
            correlation_matrix
        )
        results['passes_correlation'] = passes_corr
        results['correlation_max'] = max_corr
        results['correlation_avg'] = avg_corr
        
        # Check leg limit (would need to check today's trades)
        # For now, assume it passes
        results['passes_leg_limit'] = True
        
        # Calculate confidence based on all checks
        confidence = 0.0
        if results['passes_buffer']:
            confidence += 0.25
        if results['passes_holding_period']:
            confidence += 0.25
        if results['passes_correlation']:
            confidence += 0.25
        if results['passes_leg_limit']:
            confidence += 0.25
        
        results['confidence'] = confidence
        
        return results
    
    def _calculate_correlation_matrix(self, etf_prices: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate 90-day correlation matrix using log returns
        Align trading days and remove NaN before calculation
        """
        # Prepare log returns data
        returns_data = {}
        
        for code, df in etf_prices.items():
            if len(df) >= 90:
                # Calculate log returns
                log_returns = np.log(df['close'] / df['close'].shift(1))
                
                # Use last 90 trading days
                returns_data[code] = log_returns.tail(90)
        
        if not returns_data:
            return pd.DataFrame()
        
        # Create DataFrame and align trading days
        returns_df = pd.DataFrame(returns_data)
        
        # Remove any rows with NaN (ensures alignment)
        returns_df = returns_df.dropna()
        
        # Calculate correlation matrix
        correlation_matrix = returns_df.corr()
        
        return correlation_matrix
    
    def _determine_signal_action(self,
                                code: str,
                                score: float,
                                qualifications: Dict,
                                holding_codes: List[str],
                                regime: MarketRegime) -> Tuple[SignalType, str]:
        """Determine signal type and action based on qualifications"""
        
        # Check if all qualifications pass
        all_pass = all([
            qualifications['passes_buffer'],
            qualifications['passes_holding_period'],
            qualifications['passes_correlation'],
            qualifications['passes_leg_limit']
        ])
        
        if code in holding_codes:
            # Existing position
            if score < 0:
                return SignalType.SELL, "EXIT"
            elif not qualifications['passes_buffer']:
                return SignalType.HOLD, "HOLD"
            elif all_pass and regime == MarketRegime.BULLISH:
                return SignalType.BUY, "ADD"
            else:
                return SignalType.HOLD, "HOLD"
        else:
            # New position
            if score > 0 and all_pass:
                return SignalType.BUY, "ENTER"
            else:
                return SignalType.HOLD, "WATCH"
    
    def _calculate_suggested_weight(self,
                                   category: str,
                                   rank: int,
                                   num_holdings: int) -> float:
        """Calculate suggested position weight"""
        if category == "Core":
            base_weight = self.config.portfolio_settings.core_target_weight / 4  # Assume 4 core positions
        else:
            base_weight = self.config.portfolio_settings.satellite_target_weight / 6  # Assume 6 satellite positions
        
        # Adjust based on rank
        if rank <= 3:
            weight_multiplier = 1.2
        elif rank <= 6:
            weight_multiplier = 1.0
        else:
            weight_multiplier = 0.8
        
        suggested_weight = base_weight * weight_multiplier
        
        # Apply limits
        suggested_weight = min(suggested_weight, self.config.portfolio_settings.max_single_position)
        suggested_weight = max(suggested_weight, self.config.portfolio_settings.min_single_position)
        
        return suggested_weight
    
    def _determine_signal_strength(self, score: float, confidence: float) -> SignalStrength:
        """Determine signal strength based on score and confidence"""
        if confidence >= 0.75 and abs(score) > 0.15:
            return SignalStrength.STRONG
        elif confidence >= 0.5 and abs(score) > 0.05:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _generate_exit_signals(self, holdings: List[Holdings]) -> List[TradingSignal]:
        """Generate exit signals for bearish market"""
        signals = []
        
        for holding in holdings:
            if holding.is_active:
                signal = TradingSignal(
                    code=holding.code,
                    signal_type=SignalType.SELL,
                    action="EXIT",
                    portfolio_type=holding.portfolio_type or "Unknown",
                    momentum_score=holding.position_score or 0,
                    return_60d=0,
                    return_120d=0,
                    correlation_max=0,
                    correlation_avg=0,
                    passes_buffer=True,
                    passes_holding_period=True,
                    passes_correlation=True,
                    passes_leg_limit=True,
                    suggested_weight=0,
                    confidence=1.0,
                    signal_strength=SignalStrength.STRONG,
                    notes="Market regime is BEARISH - exit all positions"
                )
                signals.append(signal)
        
        return signals
    
    def calculate_chop(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Choppiness Index (CHOP)
        Values > 61.8 indicate choppy market
        Values < 38.2 indicate trending market
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate ATR sum
        atr_sum = pd.Series(index=df.index, dtype=float)
        for i in range(period, len(df)):
            period_high = high.iloc[i-period:i].max()
            period_low = low.iloc[i-period:i].min()
            
            true_ranges = []
            for j in range(i-period, i):
                tr = max(
                    high.iloc[j] - low.iloc[j],
                    abs(high.iloc[j] - close.iloc[j-1]) if j > 0 else 0,
                    abs(low.iloc[j] - close.iloc[j-1]) if j > 0 else 0
                )
                true_ranges.append(tr)
            
            atr_sum.iloc[i] = sum(true_ranges)
        
        # Calculate CHOP
        highest = high.rolling(period).max()
        lowest = low.rolling(period).min()
        
        chop = 100 * np.log10(atr_sum / (highest - lowest)) / np.log10(period)
        
        return chop


# Singleton instance
_decision_engine: Optional[DecisionEngine] = None

def get_decision_engine() -> DecisionEngine:
    """Get singleton decision engine instance"""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine