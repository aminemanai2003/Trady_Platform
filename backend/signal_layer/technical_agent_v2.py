"""
Technical Agent V2 - DETERMINISTIC ONLY
NO LLM for trading logic
"""
from typing import Dict
import pandas as pd
from data_layer.timeseries_loader import TimeSeriesLoader
from feature_layer.technical_features import TechnicalFeatureEngine


class TechnicalAgentV2:
    """
    Technical Analysis Agent - Pure deterministic logic
    
    Uses:
    - RSI thresholds
    - MACD crossovers
    - Bollinger Band positions
    - Moving average trends
    
    NO LLM - Only math
    """
    
    def __init__(self):
        self.data_loader = TimeSeriesLoader()
        self.feature_engine = TechnicalFeatureEngine()
    
    def generate_signal(self, symbol: str) -> Dict:
        """
        Generate technical signal using PURE LOGIC
        
        Returns:
            {
                'signal': -1/0/1,
                'confidence': 0-1,
                'features_used': dict,
                'deterministic_reason': str
            }
        """
        # Load data
        df = self.data_loader.load_ohlcv(symbol)
        
        if df.empty or len(df) < 200:
            return self._neutral_signal("Insufficient data")
        
        # Calculate indicators
        df_with_features = self.feature_engine.calculate_all(df)
        indicators = self.feature_engine.get_current_values(df_with_features)
        
        # DETERMINISTIC RULES
        return self._apply_technical_rules(indicators)
    
    def _apply_technical_rules(self, ind: Dict) -> Dict:
        """
        Apply deterministic threshold rules
        
        NO RANDOMNESS - Same input = same output
        """
        signals = []
        confidence_weights = []
        reasons = []
        
        # Rule 1: RSI Oversold/Overbought (weight: 0.25)
        if ind.get('rsi_14') is not None:
            if ind['rsi_14'] < 30:
                signals.append(1)  # Oversold -> Buy
                confidence_weights.append(0.25)
                reasons.append(f"RSI oversold ({ind['rsi_14']:.1f})")
            elif ind['rsi_14'] > 70:
                signals.append(-1)  # Overbought -> Sell
                confidence_weights.append(0.25)
                reasons.append(f"RSI overbought ({ind['rsi_14']:.1f})")
            else:
                signals.append(0)
                confidence_weights.append(0.1)
        
        # Rule 2: MACD Crossover (weight: 0.30)
        if ind.get('macd_diff') is not None:
            macd_diff = float(ind['macd_diff'])
            macd_abs = abs(macd_diff)
            if ind['macd_diff'] > 0:
                signals.append(1)
                confidence_weights.append(0.30)
                if macd_abs < 1e-4:
                    reasons.append("MACD slightly bullish (near zero momentum)")
                else:
                    reasons.append(f"MACD bullish ({macd_diff:.4f})")
            elif ind['macd_diff'] < 0:
                signals.append(-1)
                confidence_weights.append(0.30)
                if macd_abs < 1e-4:
                    reasons.append("MACD slightly bearish (near zero momentum)")
                else:
                    reasons.append(f"MACD bearish ({macd_diff:.4f})")
            else:
                signals.append(0)
                confidence_weights.append(0.05)
                reasons.append("MACD neutral (momentum near zero)")
        
        # Rule 3: Bollinger Bands (weight: 0.20)
        if ind.get('bb_position') is not None:
            if ind['bb_position'] < -0.8:  # Near lower band
                signals.append(1)
                confidence_weights.append(0.20)
                reasons.append("Price at lower Bollinger Band")
            elif ind['bb_position'] > 0.8:  # Near upper band
                signals.append(-1)
                confidence_weights.append(0.20)
                reasons.append("Price at upper Bollinger Band")
        
        # Rule 4: Trend (SMA alignment) (weight: 0.25)
        if ind.get('sma_trend') is not None:
            if ind['sma_trend'] == 'strong_bullish':
                signals.append(1)
                confidence_weights.append(0.25)
                reasons.append("Strong bullish trend (SMA aligned)")
            elif ind['sma_trend'] == 'strong_bearish':
                signals.append(-1)
                confidence_weights.append(0.25)
                reasons.append("Strong bearish trend (SMA aligned)")
            elif ind['sma_trend'] in ['bullish', 'bearish']:
                signals.append(1 if ind['sma_trend'] == 'bullish' else -1)
                confidence_weights.append(0.15)
                reasons.append(f"Moderate {ind['sma_trend']} trend")
        
        # Aggregate signals
        if not signals:
            return self._neutral_signal("No clear technical pattern")
        
        # Weighted vote
        total_weight = sum(confidence_weights)
        weighted_signal = sum(s * w for s, w in zip(signals, confidence_weights)) / total_weight
        
        # Convert to discrete signal
        if weighted_signal > 0.3:
            final_signal = 1
        elif weighted_signal < -0.3:
            final_signal = -1
        else:
            final_signal = 0
        
        # Calculate confidence
        confidence = min(total_weight, 1.0)
        
        return {
            'signal': final_signal,
            'confidence': confidence,
            'features_used': ind,
            'deterministic_reason': '; '.join(reasons) if reasons else 'Mixed signals',
            'agent': 'TechnicalV2'
        }
    
    def _neutral_signal(self, reason: str) -> Dict:
        """Return neutral signal"""
        return {
            'signal': 0,
            'confidence': 0.0,
            'features_used': {},
            'deterministic_reason': reason,
            'agent': 'TechnicalV2'
        }
