"""
Sentiment Feature Engine
Uses LLM ONLY for:
- Sentiment classification (-1 to 1)
- Currency relevance detection

Does NOT use LLM for:
- Trading decisions
- Signal thresholds
- Weighted scoring
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import json
from core.llm_factory import LLMFactory
from langchain_core.prompts import PromptTemplate


class SentimentFeatureEngine:
    """Calculate sentiment features with minimal LLM usage"""
    
    def __init__(self):
        self._embeddings = None
        self._llm = None
        
        # Strict JSON-only prompt
        self.sentiment_prompt = PromptTemplate(
            input_variables=["text", "currencies"],
            template="""Analyze this forex news for sentiment.

News: {text}

Currencies: {currencies}

Return ONLY valid JSON with this exact format:
{{"sentiment": <number between -1 and 1>, "relevance": <number between 0 and 1>, "explained": "<one sentence>"}}

Examples:
- Hawkish central bank: {{"sentiment": 0.8, "relevance": 0.9, "explained": "Central bank signals rate hikes"}}
- Dovish policy: {{"sentiment": -0.7, "relevance": 0.8, "explained": "Policy easing expected"}}
- Neutral news: {{"sentiment": 0.0, "relevance": 0.3, "explained": "Low market impact"}}

JSON:"""
        )
    
    @property
    def llm(self):
        """Lazy-load LLM only when needed (not for pre-scored articles)"""
        if self._llm is None:
            self._llm = LLMFactory.get_llm()
        return self._llm
    
    @property
    def embeddings(self):
        """Lazy-load embeddings only when needed"""
        if self._embeddings is None:
            self._embeddings = LLMFactory.get_embeddings()
        return self._embeddings
    
    def calculate_sentiment_batch(
        self,
        news_df: pd.DataFrame,
        currencies: List[str]
    ) -> pd.DataFrame:
        """
        Calculate sentiment for batch of news
        
        Uses pre-computed sentiment_score from DB when available (fast path).
        Falls back to LLM classification only for articles without scores.
        All aggregation is deterministic Python.
        """
        results = []
        
        for idx, row in news_df.iterrows():
            # Fast path: use pre-computed sentiment score from database
            db_score = row.get('sentiment_score', None)
            if db_score is not None and not pd.isna(db_score):
                results.append({
                    'news_id': row['id'],
                    'timestamp': row['timestamp'],
                    'sentiment_score': float(db_score),
                    'relevance': 0.8,  # DB articles are pre-vetted
                    'explained': row.get('title', 'Pre-analyzed article')
                })
            else:
                # Slow path: LLM classification (only for unscored articles)
                sentiment_data = self._classify_single_article(
                    row['title'],
                    row.get('content', ''),
                    currencies
                )
                results.append({
                    'news_id': row['id'],
                    'timestamp': row['timestamp'],
                    'sentiment_score': sentiment_data['sentiment'],
                    'relevance': sentiment_data['relevance'],
                    'explained': sentiment_data['explained']
                })
        
        return pd.DataFrame(results)
    
    def _classify_single_article(
        self,
        title: str,
        content: str,
        currencies: List[str],
        max_retries: int = 3
    ) -> Dict:
        """
        Use LLM to classify sentiment
        
        WITH RETRY LOGIC for invalid JSON
        """
        text = f"{title}. {content[:500]}"  # Limit tokens
        currencies_str = ", ".join(currencies)
        
        for attempt in range(max_retries):
            try:
                prompt = self.sentiment_prompt.format(
                    text=text,
                    currencies=currencies_str
                )
                
                response = self.llm.invoke(prompt)
                
                # Parse JSON
                parsed = self._parse_llm_response(response)
                
                # Validate
                if self._validate_sentiment_output(parsed):
                    return parsed
                
            except Exception as e:
                if attempt == max_retries - 1:
                    # Fallback to neutral
                    return {
                        'sentiment': 0.0,
                        'relevance': 0.1,
                        'explained': 'LLM parsing failed - neutral default'
                    }
        
        return {
            'sentiment': 0.0,
            'relevance': 0.1,
            'explained': 'Invalid LLM output - neutral default'
        }
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response with strict JSON extraction"""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith('```'):
            response = response.split('```')[1]
            if response.startswith('json'):
                response = response[4:]
        
        # Find JSON object
        start = response.find('{')
        end = response.rfind('}') + 1
        
        if start == -1 or end == 0:
            raise ValueError("No JSON object found")
        
        json_str = response[start:end]
        parsed = json.loads(json_str)
        
        return parsed
    
    def _validate_sentiment_output(self, data: Dict) -> bool:
        """Validate LLM output matches schema"""
        required_keys = {'sentiment', 'relevance', 'explained'}
        
        if not all(k in data for k in required_keys):
            return False
        
        # Validate ranges
        if not (-1 <= data['sentiment'] <= 1):
            return False
        
        if not (0 <= data['relevance'] <= 1):
            return False
        
        if not isinstance(data['explained'], str):
            return False
        
        return True
    
    @staticmethod
    def aggregate_sentiment(
        sentiment_df: pd.DataFrame,
        time_decay_hours: float = 24.0
    ) -> Dict:
        """
        Aggregate sentiment DETERMINISTICALLY
        
        NO LLM - Pure Python math
        
        - Time-weighted average
        - Relevance-weighted
        - Exponential decay
        """
        if sentiment_df.empty:
            return {
                'signal': 0,
                'confidence': 0.0,
                'avg_sentiment': 0.0,
                'article_count': 0
            }
        
        # Calculate time decay weights
        now = pd.Timestamp.now(tz='UTC')
        # Ensure timestamps are tz-aware
        if sentiment_df['timestamp'].dt.tz is None:
            sentiment_df['timestamp'] = pd.to_datetime(sentiment_df['timestamp']).dt.tz_localize('UTC')
        sentiment_df['hours_ago'] = (now - sentiment_df['timestamp']).dt.total_seconds() / 3600
        sentiment_df['time_weight'] = np.exp(-sentiment_df['hours_ago'] / time_decay_hours)
        
        # Combined weight: relevance * time_decay
        sentiment_df['combined_weight'] = sentiment_df['relevance'] * sentiment_df['time_weight']
        
        # Weighted average sentiment
        if sentiment_df['combined_weight'].sum() > 0:
            avg_sentiment = (
                (sentiment_df['sentiment_score'] * sentiment_df['combined_weight']).sum() /
                sentiment_df['combined_weight'].sum()
            )
        else:
            avg_sentiment = 0.0
        
        # DETERMINISTIC signal thresholds
        if avg_sentiment > 0.3:
            signal = 1
        elif avg_sentiment < -0.3:
            signal = -1
        else:
            signal = 0
        
        # Confidence based on article count and agreement
        article_count = len(sentiment_df)
        sentiment_std = sentiment_df['sentiment_score'].std()
        
        confidence = min(
            (article_count / 20) * 0.5 +  # More articles = more confidence
            (1 - sentiment_std) * 0.5,     # Less variance = more confidence
            1.0
        )
        
        return {
            'signal': signal,
            'confidence': float(confidence),
            'avg_sentiment': float(avg_sentiment),
            'article_count': int(article_count),
            'features_used': {
                'sentiment_mean': float(avg_sentiment),
                'sentiment_std': float(sentiment_std) if not np.isnan(sentiment_std) else 0.0,
                'recent_articles': int(article_count)
            },
            'deterministic_reason': SentimentFeatureEngine._generate_reason(
                signal, avg_sentiment, article_count
            )
        }
    
    @staticmethod
    def _generate_reason(signal: int, avg_sent: float, count: int) -> str:
        """Generate deterministic explanation"""
        if signal == 1:
            return f"Bullish sentiment: {avg_sent:.2f} from {count} articles"
        elif signal == -1:
            return f"Bearish sentiment: {avg_sent:.2f} from {count} articles"
        else:
            return f"Neutral sentiment: {avg_sent:.2f} from {count} articles"
