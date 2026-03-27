"""
Sentiment Agent V2 - MINIMAL LLM USE
LLM only for classification, NOT for trading decisions
"""
from typing import Dict, List
from datetime import datetime, timedelta
import threading
from data_layer.news_loader import NewsLoader
from feature_layer.sentiment_features import SentimentFeatureEngine


class SentimentAgentV2:
    """
    Sentiment Analysis Agent
    
    LLM used ONLY for:
    - Classifying sentiment (-1 to 1)
    - Extracting currency relevance
    
    Trading logic is DETERMINISTIC Python
    """
    
    def __init__(self):
        self.data_loader = NewsLoader()
        self.feature_engine = SentimentFeatureEngine()
        self.max_news_staleness_hours = 4
        self._refresh_lock = threading.Lock()
        self._refresh_in_progress = False
    
    def generate_signal(
        self,
        currencies: List[str],
        lookback_hours: int = 168  # 7 days — ensures coverage even if pipeline was idle
    ) -> Dict:
        """
        Generate sentiment signal
        
        LLM: Only for article classification
        Aggregation: Pure deterministic Python
        
        Returns:
            {
                'signal': -1/0/1,
                'confidence': 0-1,
                'features_used': dict,
                'deterministic_reason': str
            }
        """
        # Load recent news
        start_time = datetime.now() - timedelta(hours=lookback_hours)
        news_df = self.data_loader.load_news(
            currencies=currencies,
            start_time=start_time,
            limit=100
        )

        # Auto-refresh when data is empty or stale
        latest_ts = self.data_loader.latest_timestamp()
        data_is_stale = (
            latest_ts is None or
            (datetime.now() - latest_ts.replace(tzinfo=None)).total_seconds() > self.max_news_staleness_hours * 3600
        )

        if news_df.empty or data_is_stale:
            self._refresh_news_data_async()
            news_df = self.data_loader.load_news(
                currencies=currencies,
                start_time=start_time,
                limit=100
            )

        # Historical fallback to prevent hard empty state when sources are temporarily down
        if news_df.empty:
            fallback_start = datetime.now() - timedelta(days=30)
            news_df = self.data_loader.load_news(
                currencies=currencies,
                start_time=fallback_start,
                limit=100
            )

        if news_df.empty:
            return self._neutral_signal("News feed temporarily unavailable")
        
        # LLM: Classify each article (ONLY classification)
        sentiment_df = self.feature_engine.calculate_sentiment_batch(
            news_df,
            currencies
        )
        
        # DETERMINISTIC: Aggregate sentiments
        signal_data = self.feature_engine.aggregate_sentiment(sentiment_df)
        
        # Add agent identifier
        signal_data['agent'] = 'SentimentV2'
        
        return signal_data

    def _refresh_news_data(self) -> None:
        """Best-effort refresh of news from acquisition sources."""
        try:
            from acquisition.news_collector import collect_news_data
            collect_news_data()
        except Exception:
            pass

    def _refresh_news_data_async(self) -> None:
        """Trigger refresh in background without blocking signal generation."""
        with self._refresh_lock:
            if self._refresh_in_progress:
                return
            self._refresh_in_progress = True

        def _run_refresh() -> None:
            try:
                self._refresh_news_data()
            finally:
                with self._refresh_lock:
                    self._refresh_in_progress = False

        thread = threading.Thread(target=_run_refresh, daemon=True)
        thread.start()
    
    def _neutral_signal(self, reason: str) -> Dict:
        """Return neutral signal"""
        return {
            'signal': 0,
            'confidence': 0.0,
            'features_used': {},
            'deterministic_reason': reason,
            'agent': 'SentimentV2'
        }
