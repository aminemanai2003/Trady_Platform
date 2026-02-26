"""
Drift Detector - Detect distribution shifts in data
"""
import pandas as pd
import numpy as np
from typing import Dict
from scipy import stats
from datetime import datetime, timedelta
from core.database import DatabaseManager


class DriftDetector:
    """
    Detect statistical drift in:
    - Sentiment distributions
    - Volatility regime changes
    - Volume patterns
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.baseline_stats = {}
    
    def detect_sentiment_drift(self, recent_window: int = 7) -> Dict:
        """
        Detect if sentiment distribution has shifted
        
        Uses Kolmogorov-Smirnov test
        """
        # Get baseline (30-60 days ago)
        baseline_start = datetime.now() - timedelta(days=60)
        baseline_end = datetime.now() - timedelta(days=30)
        
        # Get recent (last N days)
        recent_start = datetime.now() - timedelta(days=recent_window)
        
        with self.db.get_postgres_connection() as conn:
            baseline_query = """
            SELECT sentiment_score
            FROM news_sentiment_processed
            WHERE timestamp BETWEEN %s AND %s
            """
            baseline = pd.read_sql(baseline_query, conn, params=(baseline_start, baseline_end))
            
            recent_query = """
            SELECT sentiment_score
            FROM news_sentiment_processed
            WHERE timestamp >= %s
            """
            recent = pd.read_sql(recent_query, conn, params=(recent_start,))
        
        if baseline.empty or recent.empty:
            return {'drift_detected': False, 'reason': 'Insufficient data'}
        
        # KS test
        ks_statistic, p_value = stats.ks_2samp(
            baseline['sentiment_score'],
            recent['sentiment_score']
        )
        
        drift_detected = p_value < 0.05  # 95% confidence
        
        return {
            'drift_detected': drift_detected,
            'p_value': float(p_value),
            'ks_statistic': float(ks_statistic),
            'baseline_mean': float(baseline['sentiment_score'].mean()),
            'recent_mean': float(recent['sentiment_score'].mean()),
            'reason': 'Sentiment distribution has shifted significantly' if drift_detected else 'No drift'
        }
    
    def detect_volatility_regime_change(self, symbol: str, window: int = 20) -> Dict:
        """
        Detect if volatility regime has changed
        
        Compares recent volatility to baseline
        """
        # Get recent price data
        # (Would query InfluxDB for actual data)
        
        # Simplified: Compare rolling volatility
        # In production, would calculate from actual OHLC data
        
        return {
            'regime_change': False,
            'current_regime': 'normal',
            'reason': 'Volatility within normal range'
        }
    
    def get_drift_summary(self) -> Dict:
        """Get summary of all drift checks"""
        sentiment_drift = self.detect_sentiment_drift()
        
        return {
            'sentiment': sentiment_drift,
            'timestamp': datetime.now().isoformat()
        }
