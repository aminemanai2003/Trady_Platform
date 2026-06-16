"""
Technical Agent V2 - DETERMINISTIC ONLY
NO LLM for trading logic
"""
from datetime import datetime, timedelta
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
        # Load one sufficiently long hourly series, then derive higher
        # timeframes from the exact same observations. This avoids comparing
        # mismatched timestamps from independently fetched datasets.
        hourly = self.data_loader.load_ohlcv(
            symbol,
            start_time=datetime.now() - timedelta(days=365),
            timeframe="1h",
        )

        if hourly.empty or len(hourly) < 200:
            return self._neutral_signal("Insufficient data")

        timeframes = self._build_timeframes(hourly)
        timeframe_weights = {"1h": 0.50, "4h": 0.30, "1d": 0.20}
        timeframe_signals = {}

        for timeframe, frame in timeframes.items():
            if len(frame) < 200:
                continue
            featured = self.feature_engine.calculate_all(frame)
            indicators = self.feature_engine.get_current_values(featured)
            result = self._apply_technical_rules(indicators)
            timeframe_signals[timeframe] = result

        if not timeframe_signals:
            return self._neutral_signal("Insufficient bars across technical timeframes")

        available_weight = sum(timeframe_weights[tf] for tf in timeframe_signals)
        normalized_weights = {
            tf: timeframe_weights[tf] / available_weight for tf in timeframe_signals
        }
        weighted_score = sum(
            result["signal"] * result["confidence"] * normalized_weights[tf]
            for tf, result in timeframe_signals.items()
        )

        if weighted_score > 0.25:
            final_signal = 1
        elif weighted_score < -0.25:
            final_signal = -1
        else:
            final_signal = 0

        directional = [
            result["signal"] for result in timeframe_signals.values()
            if result["signal"] != 0
        ]
        agreement = (
            max(directional.count(1), directional.count(-1)) / len(directional)
            if directional else 0.0
        )
        data_quality = min(available_weight, 1.0)
        confidence = min(
            1.0,
            abs(weighted_score) * 0.75 + agreement * 0.15 + data_quality * 0.10,
        )

        primary = timeframe_signals.get("1h") or next(iter(timeframe_signals.values()))
        summaries = {
            tf: {
                "signal": result["signal"],
                "confidence": round(result["confidence"], 4),
                "reason": result["deterministic_reason"],
                "bars": len(timeframes[tf]),
                "weight": round(normalized_weights[tf], 4),
            }
            for tf, result in timeframe_signals.items()
        }
        direction_name = {1: "bullish", 0: "mixed", -1: "bearish"}[final_signal]

        return {
            "signal": final_signal,
            "confidence": round(confidence, 4),
            "features_used": {
                **primary["features_used"],
                "timeframes": summaries,
                "timeframe_weighted_score": round(float(weighted_score), 4),
                "timeframe_agreement": round(agreement, 4),
            },
            "deterministic_reason": (
                f"Multi-timeframe evidence is {direction_name}: "
                + "; ".join(
                    f"{tf}={self._signal_name(result['signal'])}"
                    for tf, result in timeframe_signals.items()
                )
            ),
            "data_quality": round(data_quality, 4),
            "evidence_count": len(timeframe_signals),
            "agent": "TechnicalV2",
        }

    @staticmethod
    def _build_timeframes(hourly: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        frame = hourly.copy()
        if "timestamp" in frame.columns:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"])
            frame = frame.set_index("timestamp")
        elif not isinstance(frame.index, pd.DatetimeIndex):
            frame.index = pd.to_datetime(frame.index)

        frame = frame.sort_index()
        aggregation = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }

        return {
            "1h": frame.dropna(subset=["open", "high", "low", "close"]),
            "4h": frame.resample("4h").agg(aggregation).dropna(),
            "1d": frame.resample("1D").agg(aggregation).dropna(),
        }

    @staticmethod
    def _signal_name(signal: int) -> str:
        return {1: "BUY", 0: "NEUTRAL", -1: "SELL"}.get(signal, "NEUTRAL")
    
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
            'data_quality': 1.0,
            'evidence_count': 1,
            'agent': 'TechnicalV2'
        }
    
    def _neutral_signal(self, reason: str) -> Dict:
        """Return neutral signal"""
        return {
            'signal': 0,
            'confidence': 0.0,
            'features_used': {},
            'deterministic_reason': reason,
            'data_quality': 0.0,
            'evidence_count': 0,
            'agent': 'TechnicalV2'
        }
