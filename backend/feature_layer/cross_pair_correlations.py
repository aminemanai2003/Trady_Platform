"""
Cross-Pair Correlation Engine
Calculates real-time correlation matrix between major currency pairs.
Implements correlation-based signal adjustment (DSO presentation slides 16-18).

PURE MATH — NO LLM
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from data_layer.timeseries_loader import TimeSeriesLoader


# Known fundamental correlation relationships
FUNDAMENTAL_CORRELATIONS = {
    ('EURUSD', 'GBPUSD'): +0.76,   # Both risk-on vs USD
    ('USDJPY', 'USDCHF'): +0.68,   # Both safe-haven
    ('EURUSD', 'USDCHF'): -0.76,   # Inverse (USD denominator)
    ('EURUSD', 'USDJPY'): -0.59,   # Inverse
    ('GBPUSD', 'USDCHF'): -0.58,   # Inverse
    ('GBPUSD', 'USDJPY'): -0.42,   # Moderate inverse
}

MAJOR_PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']


class CrossPairCorrelationEngine:
    """
    Calculates rolling correlation matrix between FX pairs.
    Uses Pearson correlation on log-returns.
    """

    def __init__(self):
        self.loader = TimeSeriesLoader()
        self._cache = {}  # Simple cache for loaded data

    def calculate_correlation_matrix(
        self,
        pairs: List[str] = None,
        lookback_days: int = 90,
        return_period: int = 1
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix between pairs.

        Args:
            pairs: List of currency pairs (default: MAJOR_PAIRS)
            lookback_days: Number of days for correlation window
            return_period: Period for return calculation (1 = daily returns)

        Returns:
            DataFrame: Correlation matrix (n_pairs × n_pairs)
        """
        if pairs is None:
            pairs = MAJOR_PAIRS

        # Load close prices for all pairs
        close_prices = {}
        for pair in pairs:
            try:
                df = self.loader.load_ohlcv(pair)
                if not df.empty and len(df) > lookback_days:
                    close_prices[pair] = df['close'].tail(lookback_days * 24)  # hourly data
                elif not df.empty:
                    close_prices[pair] = df['close']
            except Exception:
                continue

        if len(close_prices) < 2:
            return pd.DataFrame()

        # Create combined DataFrame
        prices_df = pd.DataFrame(close_prices)

        # Calculate log returns
        log_returns = np.log(prices_df / prices_df.shift(return_period)).dropna()

        if log_returns.empty or len(log_returns) < 20:
            return pd.DataFrame()

        # Pearson correlation matrix
        corr_matrix = log_returns.corr()

        return corr_matrix

    def get_pair_correlation(
        self,
        pair1: str,
        pair2: str,
        lookback_days: int = 90
    ) -> float:
        """Get correlation between two specific pairs."""
        corr_matrix = self.calculate_correlation_matrix(
            pairs=[pair1, pair2],
            lookback_days=lookback_days
        )
        if corr_matrix.empty:
            # Fall back to fundamental correlations
            key = (pair1, pair2)
            rev_key = (pair2, pair1)
            return FUNDAMENTAL_CORRELATIONS.get(
                key, FUNDAMENTAL_CORRELATIONS.get(rev_key, 0.0)
            )
        return corr_matrix.loc[pair1, pair2]

    def get_correlation_signals(self, target_pair: str) -> Dict:
        """
        Analyze cross-pair correlations to validate or invalidate signals.

        Returns:
            {
                'correlation_matrix': dict,
                'signal_alignment': float,  # -1 to +1
                'conflicts': list,
                'supporting_pairs': list,
                'confidence_adjustment': float  # multiplier
            }
        """
        corr_matrix = self.calculate_correlation_matrix()

        if corr_matrix.empty:
            return {
                'correlation_matrix': {},
                'signal_alignment': 0.0,
                'conflicts': [],
                'supporting_pairs': [],
                'confidence_adjustment': 1.0
            }

        # Get recent price momentum for each pair
        momentum = {}
        for pair in MAJOR_PAIRS:
            try:
                df = self.loader.load_ohlcv(pair)
                if not df.empty and len(df) >= 24:
                    # 24-hour return
                    ret = (df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24]
                    momentum[pair] = ret
            except Exception:
                momentum[pair] = 0.0

        # Check alignment: if correlated pairs move in expected direction
        alignment_scores = []
        conflicts = []
        supporting = []

        target_mom = momentum.get(target_pair, 0.0)

        for other_pair in MAJOR_PAIRS:
            if other_pair == target_pair:
                continue

            corr = corr_matrix.loc[target_pair, other_pair] if (
                target_pair in corr_matrix.index and other_pair in corr_matrix.columns
            ) else 0.0

            other_mom = momentum.get(other_pair, 0.0)

            # Expected: if corr > 0, both should move same direction
            # Expected: if corr < 0, they should move opposite
            if abs(corr) > 0.3:
                expected_direction = np.sign(target_mom) * np.sign(corr)
                actual_direction = np.sign(other_mom)

                if expected_direction != 0 and actual_direction != 0:
                    if expected_direction == actual_direction:
                        alignment_scores.append(abs(corr))
                        supporting.append(f"{other_pair} (r={corr:.2f})")
                    else:
                        alignment_scores.append(-abs(corr))
                        conflicts.append(
                            f"{other_pair} moving {'same' if corr < 0 else 'opposite'} "
                            f"direction (r={corr:.2f})"
                        )

        # Calculate overall alignment
        signal_alignment = np.mean(alignment_scores) if alignment_scores else 0.0

        # Confidence adjustment based on alignment
        if signal_alignment > 0.3:
            confidence_adj = 1.15  # Boost confidence
        elif signal_alignment < -0.3:
            confidence_adj = 0.75  # Reduce confidence
        else:
            confidence_adj = 1.0

        return {
            'correlation_matrix': corr_matrix.to_dict(),
            'signal_alignment': float(signal_alignment),
            'conflicts': conflicts,
            'supporting_pairs': supporting,
            'confidence_adjustment': float(confidence_adj),
            'pair_momentum': {k: float(v) for k, v in momentum.items()}
        }

    def get_correlation_summary(self) -> Dict:
        """
        Get full correlation summary for display/reporting.
        Matches presentation slides 16-18.
        """
        corr_matrix = self.calculate_correlation_matrix()

        if corr_matrix.empty:
            # Return fundamental correlations as fallback
            return {
                'matrix': {p: {q: 0.0 for q in MAJOR_PAIRS} for p in MAJOR_PAIRS},
                'strong_positive': [
                    {'pair1': 'EURUSD', 'pair2': 'GBPUSD', 'correlation': 0.76,
                     'reason': 'Both risk-on currencies against USD'},
                    {'pair1': 'USDJPY', 'pair2': 'USDCHF', 'correlation': 0.68,
                     'reason': 'Both safe-haven currencies'},
                ],
                'strong_negative': [
                    {'pair1': 'EURUSD', 'pair2': 'USDCHF', 'correlation': -0.76,
                     'reason': 'USD common denominator inverse'},
                    {'pair1': 'EURUSD', 'pair2': 'USDJPY', 'correlation': -0.59,
                     'reason': 'EUR up means USD down'},
                    {'pair1': 'GBPUSD', 'pair2': 'USDCHF', 'correlation': -0.58,
                     'reason': 'GBP up means USD down'},
                ],
                'source': 'fundamental_defaults'
            }

        strong_pos = []
        strong_neg = []

        for i, p1 in enumerate(corr_matrix.index):
            for j, p2 in enumerate(corr_matrix.columns):
                if i >= j:
                    continue
                val = corr_matrix.loc[p1, p2]
                entry = {
                    'pair1': p1, 'pair2': p2,
                    'correlation': round(float(val), 3)
                }
                key = (p1, p2)
                rev_key = (p2, p1)
                fund_corr = FUNDAMENTAL_CORRELATIONS.get(
                    key, FUNDAMENTAL_CORRELATIONS.get(rev_key, None)
                )
                if fund_corr is not None:
                    entry['fundamental_expected'] = fund_corr
                    entry['deviation'] = round(float(val) - fund_corr, 3)

                if val > 0.5:
                    strong_pos.append(entry)
                elif val < -0.5:
                    strong_neg.append(entry)

        return {
            'matrix': {
                p: {q: round(float(corr_matrix.loc[p, q]), 3) for q in corr_matrix.columns}
                for p in corr_matrix.index
            },
            'strong_positive': sorted(strong_pos, key=lambda x: -x['correlation']),
            'strong_negative': sorted(strong_neg, key=lambda x: x['correlation']),
            'source': 'calculated',
            'pairs_count': len(corr_matrix.index)
        }
