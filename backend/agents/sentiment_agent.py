"""
PHASE 3: Sentiment Agent
Analyzes news sentiment to generate trading signals
"""
from typing import Dict, Optional
from datetime import datetime, timedelta

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from agents.base_agent import BaseAgent, AgentOutput
from features.models import SentimentFeatures


class SentimentAgent(BaseAgent):
    """Agent that analyzes news sentiment"""
    
    AGENT_TYPE = 'sentiment'
    
    DECISION_PROMPT = PromptTemplate(
        input_variables=["currency", "sentiment", "confidence_avg", "news_volume", "relevance"],
        template="""You are a sentiment analysis expert for forex markets. Analyze news sentiment and make a trading decision.

Currency: {currency}

Sentiment Indicators:
- Average Sentiment Score: {sentiment} (-1=very negative, +1=very positive)
- Sentiment Confidence: {confidence_avg} (0=low, 1=high)
- News Volume (1h): {news_volume} articles
- Average Relevance: {relevance} (0=low, 1=high)

Based on news sentiment, provide:
1. Trading signal: BUY, SELL, or NEUTRAL
2. Confidence level: 0.0 to 1.0
3. Brief reasoning

Note: Consider sentiment STRENGTH and VOLUME together. High volume amplifies signal strength.

Response format:
Signal: [BUY/SELL/NEUTRAL]
Confidence: [0.0-1.0]
Reasoning: [Your analysis]
"""
    )
    
    def _create_decision_chain(self) -> LLMChain:
        """Create LangChain decision chain"""
        return LLMChain(llm=self.llm, prompt=self.DECISION_PROMPT)
    
    def _fetch_features(self, symbol: str, timestamp: Optional[datetime] = None) -> Dict:
        """Fetch sentiment features"""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Extract base and quote currencies
        base_currency = symbol[:3]
        quote_currency = symbol[3:6]
        
        # Get sentiment for last hour
        one_hour_ago = timestamp - timedelta(hours=1)
        
        # Fetch sentiments for both currencies
        base_sentiments = SentimentFeatures.objects.filter(
            currency_mentioned=base_currency,
            timestamp__gte=one_hour_ago,
            timestamp__lte=timestamp
        )
        
        quote_sentiments = SentimentFeatures.objects.filter(
            currency_mentioned=quote_currency,
            timestamp__gte=one_hour_ago,
            timestamp__lte=timestamp
        )
        
        # Aggregate sentiments
        base_sentiment_data = self._aggregate_sentiments(base_sentiments)
        quote_sentiment_data = self._aggregate_sentiments(quote_sentiments)
        
        # Calculate relative sentiment (base - quote)
        relative_sentiment = base_sentiment_data['avg_sentiment'] - quote_sentiment_data['avg_sentiment']
        
        return {
            'base_sentiment': base_sentiment_data['avg_sentiment'],
            'quote_sentiment': quote_sentiment_data['avg_sentiment'],
            'relative_sentiment': relative_sentiment,
            'base_confidence': base_sentiment_data['avg_confidence'],
            'quote_confidence': quote_sentiment_data['avg_confidence'],
            'base_news_volume': base_sentiment_data['count'],
            'quote_news_volume': quote_sentiment_data['count'],
            'base_relevance': base_sentiment_data['avg_relevance'],
            'quote_relevance': quote_sentiment_data['avg_relevance']
        }
    
    def _aggregate_sentiments(self, sentiments) -> Dict:
        """Aggregate sentiment features"""
        
        if not sentiments.exists():
            return {
                'avg_sentiment': 0.0,
                'avg_confidence': 0.0,
                'avg_relevance': 0.0,
                'count': 0
            }
        
        count = sentiments.count()
        
        # Weighted average by confidence
        total_weighted_sentiment = 0
        total_confidence = 0
        total_relevance = 0
        
        for s in sentiments:
            weight = s.confidence * s.relevance_score
            total_weighted_sentiment += s.sentiment_score * weight
            total_confidence += s.confidence
            total_relevance += s.relevance_score
        
        avg_sentiment = total_weighted_sentiment / max(sum([s.confidence * s.relevance_score for s in sentiments]), 0.01)
        avg_confidence = total_confidence / count
        avg_relevance = total_relevance / count
        
        return {
            'avg_sentiment': avg_sentiment,
            'avg_confidence': avg_confidence,
            'avg_relevance': avg_relevance,
            'count': count
        }
    
    def _make_decision(self, features: Dict) -> AgentOutput:
        """Make trading decision using sentiment features"""
        
        # Use relative sentiment (base - quote)
        relative_sentiment = features.get('relative_sentiment', 0)
        
        # Average confidence from both currencies
        avg_confidence = (features.get('base_confidence', 0) + features.get('quote_confidence', 0)) / 2
        
        # Total news volume
        news_volume = features.get('base_news_volume', 0) + features.get('quote_news_volume', 0)
        
        # Average relevance
        avg_relevance = (features.get('base_relevance', 0) + features.get('quote_relevance', 0)) / 2
        
        # Get LLM decision
        llm_response = self.decision_chain.run(
            currency="EUR (in EURUSD)",
            sentiment=f"{relative_sentiment:.2f}",
            confidence_avg=f"{avg_confidence:.2f}",
            news_volume=str(news_volume),
            relevance=f"{avg_relevance:.2f}"
        )
        
        # Parse LLM output
        signal, confidence = self._parse_llm_decision(llm_response)
        
        # Apply rule-based adjustments
        confidence = self._adjust_confidence_sentiment(features, signal, confidence)
        
        return AgentOutput(
            signal=signal,
            confidence=confidence,
            reasoning=llm_response,
            features_used=features
        )
    
    def _adjust_confidence_sentiment(self, features: Dict, 
                                    signal: str, confidence: float) -> float:
        """Adjust confidence based on sentiment rules"""
        
        adjustments = []
        
        relative_sentiment = features.get('relative_sentiment', 0)
        news_volume = features.get('base_news_volume', 0) + features.get('quote_news_volume', 0)
        avg_relevance = (features.get('base_relevance', 0) + features.get('quote_relevance', 0)) / 2
        
        # Strong sentiment with high volume increases confidence
        if signal == "BUY" and relative_sentiment > 0.3 and news_volume >= 3:
            adjustments.append(0.15)
        elif signal == "SELL" and relative_sentiment < -0.3 and news_volume >= 3:
            adjustments.append(0.15)
        
        # Low relevance decreases confidence
        if avg_relevance < 0.3:
            adjustments.append(-0.20)
        elif avg_relevance > 0.7:
            adjustments.append(0.10)
        
        # Very low news volume means low confidence
        if news_volume < 2:
            adjustments.append(-0.25)
        
        # Contradictory sentiment
        if signal == "BUY" and relative_sentiment < -0.2:
            adjustments.append(-0.20)
        elif signal == "SELL" and relative_sentiment > 0.2:
            adjustments.append(-0.20)
        
        # Apply adjustments
        adjusted_confidence = confidence + sum(adjustments)
        
        # Clip to [0, 1]
        return max(0.0, min(1.0, adjusted_confidence))
