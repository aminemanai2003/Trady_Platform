"""
Macro Feature Engine - Pure economic calculations
100% deterministic - NO LLM
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class MacroFeatureEngine:
    """Calculate macro features using deterministic algorithms"""
    
    @staticmethod
    def calculate_rate_differentials(
        rates_df: pd.DataFrame,
        base_currency: str,
        quote_currency: str
    ) -> float:
        """
        Calculate interest rate differential
        
        Formula: rate_differential = base_rate - quote_rate
        PURE MATH - NO AI
        """
        latest = rates_df.groupby('currency')['rate'].last()
        
        base_rate = latest.get(base_currency, 0)
        quote_rate = latest.get(quote_currency, 0)
        
        return base_rate - quote_rate
    
    @staticmethod
    def calculate_inflation_differential(
        inflation_df: pd.DataFrame,
        base_currency: str,
        quote_currency: str
    ) -> float:
        """Calculate inflation differential"""
        latest = inflation_df.groupby('currency')['inflation_rate'].last()
        
        base_inflation = latest.get(base_currency, 0)
        quote_inflation = latest.get(quote_currency, 0)
        
        return base_inflation - quote_inflation
    
    @staticmethod
    def calculate_real_rate(
        nominal_rate: float,
        inflation_rate: float
    ) -> float:
        """Calculate real interest rate (Fisher equation)"""
        return nominal_rate - inflation_rate
    
    @staticmethod
    def calculate_macro_momentum(
        rates_df: pd.DataFrame,
        inflation_df: pd.DataFrame,
        currency: str,
        lookback_days: int = 90
    ) -> Dict[str, float]:
        """
        Calculate momentum of macro indicators
        Returns rate of change over lookback period
        """
        # Rate momentum
        currency_rates = rates_df[rates_df['currency'] == currency].sort_values('date')
        if len(currency_rates) >= 2:
            rate_change = (
                (currency_rates['rate'].iloc[-1] - currency_rates['rate'].iloc[0]) /
                currency_rates['rate'].iloc[0] * 100
            )
        else:
            rate_change = 0.0
        
        # Inflation momentum
        currency_inflation = inflation_df[inflation_df['currency'] == currency].sort_values('date')
        if len(currency_inflation) >= 2:
            inflation_change = (
                currency_inflation['inflation_rate'].iloc[-1] -
                currency_inflation['inflation_rate'].iloc[0]
            )
        else:
            inflation_change = 0.0
        
        return {
            'rate_momentum': rate_change,
            'inflation_momentum': inflation_change
        }
    
    @staticmethod
    def calculate_carry_score(
        rate_differential: float,
        volatility: float
    ) -> float:
        """
        Calculate carry trade attractiveness
        
        Score = rate_differential / volatility
        Higher is better for carry trades
        """
        if volatility == 0 or np.isnan(volatility):
            return 0.0
        return rate_differential / volatility
    
    @staticmethod
    def get_macro_signal(
        rate_differential: float,
        inflation_differential: float,
        rate_momentum: float,
        carry_score: float
    ) -> Dict[str, any]:
        """
        Generate DETERMINISTIC macro signal
        
        NO LLM - Pure threshold logic
        
        Returns:
            signal: -1 (bearish), 0 (neutral), 1 (bullish)
            confidence: 0-1
            features_used: dict
        """
        signal_score = 0
        confidence_factors = []
        
        # Rule 1: Rate differential (50% weight)
        if rate_differential > 0.5:
            signal_score += 1
            confidence_factors.append(0.5)
        elif rate_differential < -0.5:
            signal_score -= 1
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.2)
        
        # Rule 2: Rate momentum (30% weight)
        if rate_momentum > 0.1:
            signal_score += 0.6
            confidence_factors.append(0.3)
        elif rate_momentum < -0.1:
            signal_score -= 0.6
            confidence_factors.append(0.3)
        
        # Rule 3: Carry score (20% weight)
        if carry_score > 10:
            signal_score += 0.4
            confidence_factors.append(0.2)
        elif carry_score < -10:
            signal_score -= 0.4
            confidence_factors.append(0.2)
        
        # Normalize to -1, 0, 1
        if signal_score > 0.7:
            signal = 1
        elif signal_score < -0.7:
            signal = -1
        else:
            signal = 0
        
        # Calculate confidence
        confidence = min(sum(confidence_factors), 1.0)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'features_used': {
                'rate_differential': rate_differential,
                'inflation_differential': inflation_differential,
                'rate_momentum': rate_momentum,
                'carry_score': carry_score,
                'signal_score': signal_score
            },
            'deterministic_reason': MacroFeatureEngine._generate_reason(
                signal, rate_differential, rate_momentum, carry_score
            )
        }
    
    @staticmethod
    def _generate_reason(signal: int, rate_diff: float, momentum: float, carry: float) -> str:
        """Generate deterministic text explanation"""
        if signal == 1:
            return (
                f"Bullish: Rate differential +{rate_diff:.2f}%, "
                f"momentum {momentum:.2f}%, carry {carry:.1f}"
            )
        elif signal == -1:
            return (
                f"Bearish: Rate differential {rate_diff:.2f}%, "
                f"momentum {momentum:.2f}%, carry {carry:.1f}"
            )
        else:
            return "Neutral: Mixed macro signals, no clear direction"
