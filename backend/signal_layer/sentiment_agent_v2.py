"""
Sentiment Agent V2 - MINIMAL LLM USE
LLM only for classification, NOT for trading decisions
"""
from typing import Dict, List
from datetime import datetime, timedelta
import threading
from data_layer.news_loader import NewsLoader
from data_layer.news_loader import CURRENCY_TERMS
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
        
        if len(currencies) < 2:
            return self._neutral_signal("A base and quote currency are required")

        base, quote = currencies[0].upper(), currencies[1].upper()
        base_news = news_df[
            news_df.apply(lambda row: self._mentions_currency(row, base), axis=1)
        ]
        quote_news = news_df[
            news_df.apply(lambda row: self._mentions_currency(row, quote), axis=1)
        ]

        # Directional FX sentiment requires evidence for both sides of the pair.
        if base_news.empty or quote_news.empty:
            return self._neutral_signal(
                f"Incomplete pair-specific news coverage for {base}/{quote}"
            )

        base_scores = self.feature_engine.calculate_sentiment_batch(base_news, [base])
        quote_scores = self.feature_engine.calculate_sentiment_batch(quote_news, [quote])
        base_aggregate = self.feature_engine.aggregate_sentiment(base_scores)
        quote_aggregate = self.feature_engine.aggregate_sentiment(quote_scores)

        base_sentiment = float(base_aggregate.get("avg_sentiment", 0.0))
        quote_sentiment = float(quote_aggregate.get("avg_sentiment", 0.0))
        differential = base_sentiment - quote_sentiment
        if differential > 0.20:
            signal = 1
        elif differential < -0.20:
            signal = -1
        else:
            signal = 0

        base_count = int(base_aggregate.get("article_count", 0))
        quote_count = int(quote_aggregate.get("article_count", 0))
        balanced_count = min(base_count, quote_count)
        confidence = min(
            0.80,
            abs(differential) * 0.6 + min(balanced_count / 20.0, 1.0) * 0.4,
        )
        article_count = len(set(base_news.index) | set(quote_news.index))
        signal_name = {1: "bullish", 0: "neutral", -1: "bearish"}[signal]
        signal_data = {
            "signal": signal,
            "confidence": round(confidence, 4),
            "avg_sentiment": differential,
            "article_count": article_count,
            "features_used": {
                "sentiment_mean": differential,
                "base_sentiment": base_sentiment,
                "quote_sentiment": quote_sentiment,
                "base_articles": base_count,
                "quote_articles": quote_count,
                "recent_articles": article_count,
            },
            "deterministic_reason": (
                f"{signal_name.capitalize()} pair sentiment: {base} "
                f"{base_sentiment:+.2f} vs {quote} {quote_sentiment:+.2f} "
                f"from {base_count}/{quote_count} articles"
            ),
        }
        balance_quality = min(base_count, quote_count) / max(base_count, quote_count)
        signal_data["data_quality"] = round(
            min(article_count / 20.0, 1.0) * balance_quality,
            4,
        )
        signal_data["evidence_count"] = article_count
        
        # Add agent identifier
        signal_data['agent'] = 'SentimentV2'
        
        return signal_data

    @staticmethod
    def _mentions_currency(row, currency: str) -> bool:
        tagged = row.get("currencies")
        if isinstance(tagged, list) and currency in {
            str(value).upper() for value in tagged
        }:
            return True
        text = f"{row.get('title', '')} {row.get('content', '')}".lower()
        return any(
            term in text
            for term in CURRENCY_TERMS.get(currency, (currency.lower(),))
        )

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
            'data_quality': 0.0,
            'evidence_count': 0,
            'agent': 'SentimentV2'
        }
