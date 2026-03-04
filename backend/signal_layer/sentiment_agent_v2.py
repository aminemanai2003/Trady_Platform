"""
Sentiment Agent V2 - MINIMAL LLM USE
LLM only for classification, NOT for trading decisions
"""
from typing import Dict, List
from datetime import datetime, timedelta
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
        
        if news_df.empty:
            return self._neutral_signal("No recent news articles")
        
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
    
    def _neutral_signal(self, reason: str) -> Dict:
        """Return neutral signal"""
        return {
            'signal': 0,
            'confidence': 0.0,
            'features_used': {},
            'deterministic_reason': reason,
            'agent': 'SentimentV2'
        }
