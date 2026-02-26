"""
PHASE 3: Macro Agent
Analyzes macro-economic features to generate trading signals
"""
from typing import Dict, Optional
from datetime import datetime, timedelta

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from agents.base_agent import BaseAgent, AgentOutput
from features.models import MacroFeatures


class MacroAgent(BaseAgent):
    """Agent that analyzes macro-economic indicators"""
    
    AGENT_TYPE = 'macro'
    
    DECISION_PROMPT = PromptTemplate(
        input_variables=["pair", "rate_diff", "inflation_diff", "surprise", "yield_spread", "risk_sentiment"],
        template="""You are a macro-economic analyst specializing in forex. Analyze these indicators and make a trading decision.

Currency Pair: {pair}

Macro Indicators:
- Interest Rate Differential (base-quote): {rate_diff}% (positive favors base currency)
- Inflation Differential: {inflation_diff}% (positive weakens base currency)
- Economic Surprise Metric: {surprise} (positive=better than expected)
- Yield Spread: {yield_spread} (positive favors base currency)
- Risk Sentiment: {risk_sentiment} (-1=risk-off, +1=risk-on)

Based on these macro indicators, provide:
1. Trading signal: BUY, SELL, or NEUTRAL
2. Confidence level: 0.0 to 1.0
3. Brief reasoning focusing on macro fundamentals

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
        """Fetch macro features"""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Get latest macro features
        features = MacroFeatures.objects.filter(
            currency_pair=symbol,
            date__lte=timestamp.date()
        ).order_by('-date').first()
        
        if not features:
            raise ValueError(f"No macro features found for {symbol}")
        
        return {
            'interest_rate_diff': features.interest_rate_diff or 0,
            'policy_rate_diff': features.policy_rate_diff or 0,
            'inflation_diff': features.inflation_diff or 0,
            'surprise_metric': features.surprise_metric or 0,
            'yield_spread': features.yield_spread or 0,
            'risk_sentiment': features.risk_sentiment or 0,
            'gdp_growth_diff': features.gdp_growth_diff or 0
        }
    
    def _make_decision(self, features: Dict) -> AgentOutput:
        """Make trading decision using macro features"""
        
        # Prepare prompt inputs
        rate_diff = features.get('interest_rate_diff', 0)
        inflation_diff = features.get('inflation_diff', 0)
        surprise = features.get('surprise_metric', 0)
        yield_spread = features.get('yield_spread', 0)
        risk_sentiment = features.get('risk_sentiment', 0)
        
        # Get LLM decision
        llm_response = self.decision_chain.run(
            pair="EURUSD",  # Could be parameterized
            rate_diff=f"{rate_diff:.2f}",
            inflation_diff=f"{inflation_diff:.2f}",
            surprise=f"{surprise:.4f}",
            yield_spread=f"{yield_spread:.2f}",
            risk_sentiment=f"{risk_sentiment:.2f}"
        )
        
        # Parse LLM output
        signal, confidence = self._parse_llm_decision(llm_response)
        
        # Apply rule-based adjustments
        confidence = self._adjust_confidence_macro(features, signal, confidence)
        
        return AgentOutput(
            signal=signal,
            confidence=confidence,
            reasoning=llm_response,
            features_used=features
        )
    
    def _adjust_confidence_macro(self, features: Dict, 
                                 signal: str, confidence: float) -> float:
        """Adjust confidence based on macro rules"""
        
        adjustments = []
        
        # Interest rate differential is strong signal
        rate_diff = features.get('interest_rate_diff', 0)
        if signal == "BUY" and rate_diff > 1.0:  # Base currency has higher rates
            adjustments.append(0.15)
        elif signal == "SELL" and rate_diff < -1.0:  # Quote currency has higher rates
            adjustments.append(0.15)
        elif signal == "BUY" and rate_diff < -0.5:
            adjustments.append(-0.10)
        elif signal == "SELL" and rate_diff > 0.5:
            adjustments.append(-0.10)
        
        # Economic surprise supports momentum
        surprise = features.get('surprise_metric', 0)
        if signal == "BUY" and surprise > 0.1:
            adjustments.append(0.10)
        elif signal == "SELL" and surprise < -0.1:
            adjustments.append(0.10)
        
        # Risk sentiment affects carry trades
        risk_sentiment = features.get('risk_sentiment', 0)
        # In risk-on environment, favor higher-yielding currencies
        if risk_sentiment > 0.3 and rate_diff > 0 and signal == "BUY":
            adjustments.append(0.10)
        elif risk_sentiment < -0.3 and signal == "SELL":
            # Risk-off: flight to safety
            adjustments.append(0.10)
        
        # Apply adjustments
        adjusted_confidence = confidence + sum(adjustments)
        
        # Clip to [0, 1]
        return max(0.0, min(1.0, adjusted_confidence))
