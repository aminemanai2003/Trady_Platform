"""
PHASE 3: Technical Agent
Analyzes technical indicators to generate trading signals
"""
from typing import Dict, Optional
from datetime import datetime, timedelta

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from agents.base_agent import BaseAgent, AgentOutput
from features.models import TechnicalFeatures


class TechnicalAgent(BaseAgent):
    """Agent that analyzes technical indicators"""
    
    AGENT_TYPE = 'technical'
    
    DECISION_PROMPT = PromptTemplate(
        input_variables=["symbol", "rsi", "macd", "bb_position", "trend", "volatility"],
        template="""You are a technical analysis expert. Analyze these indicators and make a trading decision.

Symbol: {symbol}

Technical Indicators:
- RSI (14): {rsi} (oversold <30, overbought >70)
- MACD: {macd} (positive=bullish, negative=bearish)
- Bollinger Band Position: {bb_position} (0=lower band, 0.5=middle, 1=upper band)
- Trend Slope (20): {trend} (positive=uptrend, negative=downtrend)
- Volatility (20d): {volatility}

Based on these technical indicators, provide:
1. Trading signal: BUY, SELL, or NEUTRAL
2. Confidence level: 0.0 to 1.0
3. Brief reasoning

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
        """Fetch technical features"""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Get latest technical features
        features = TechnicalFeatures.objects.filter(
            symbol=symbol,
            timestamp__lte=timestamp
        ).order_by('-timestamp').first()
        
        if not features:
            raise ValueError(f"No technical features found for {symbol}")
        
        return {
            'rsi_14': features.rsi_14,
            'rsi_28': features.rsi_28,
            'macd': features.macd,
            'macd_signal': features.macd_signal,
            'macd_diff': features.macd_diff,
            'bb_position': features.bb_position,
            'bb_width': features.bb_width,
            'trend_slope_20': features.trend_slope_20,
            'trend_slope_60': features.trend_slope_60,
            'rolling_vol_20': features.rolling_vol_20,
            'atr_14': features.atr_14,
            'distance_to_support': features.distance_to_support,
            'distance_to_resistance': features.distance_to_resistance
        }
    
    def _make_decision(self, features: Dict) -> AgentOutput:
        """Make trading decision using technical features"""
        
        # Prepare prompt inputs
        rsi = features.get('rsi_14', 50)
        macd_diff = features.get('macd_diff', 0)
        bb_position = features.get('bb_position', 0.5)
        trend = features.get('trend_slope_20', 0)
        volatility = features.get('rolling_vol_20', 0)
        
        # Get LLM decision
        llm_response = self.decision_chain.run(
            symbol="EURUSD",  # Could be parameterized
            rsi=f"{rsi:.2f}",
            macd=f"{macd_diff:.6f}",
            bb_position=f"{bb_position:.2f}",
            trend=f"{trend:.6f}",
            volatility=f"{volatility:.4f}"
        )
        
        # Parse LLM output
        signal, confidence = self._parse_llm_decision(llm_response)
        
        # Apply rule-based adjustments for confidence
        confidence = self._adjust_confidence_technical(features, signal, confidence)
        
        return AgentOutput(
            signal=signal,
            confidence=confidence,
            reasoning=llm_response,
            features_used=features
        )
    
    def _adjust_confidence_technical(self, features: Dict, 
                                    signal: str, confidence: float) -> float:
        """Adjust confidence based on technical rules"""
        
        adjustments = []
        
        # RSI extreme zones increase confidence
        rsi = features.get('rsi_14', 50)
        if signal == "BUY" and rsi < 30:
            adjustments.append(0.1)  # Oversold supports BUY
        elif signal == "SELL" and rsi > 70:
            adjustments.append(0.1)  # Overbought supports SELL
        elif signal == "BUY" and rsi > 70:
            adjustments.append(-0.2)  # Overbought contradicts BUY
        elif signal == "SELL" and rsi < 30:
            adjustments.append(-0.2)  # Oversold contradicts SELL
        
        # MACD confirmation
        macd_diff = features.get('macd_diff', 0)
        if signal == "BUY" and macd_diff > 0:
            adjustments.append(0.1)
        elif signal == "SELL" and macd_diff < 0:
            adjustments.append(0.1)
        elif signal == "BUY" and macd_diff < 0:
            adjustments.append(-0.1)
        elif signal == "SELL" and macd_diff > 0:
            adjustments.append(-0.1)
        
        # Trend confirmation
        trend = features.get('trend_slope_20', 0)
        if signal == "BUY" and trend > 0:
            adjustments.append(0.1)
        elif signal == "SELL" and trend < 0:
            adjustments.append(0.1)
        elif signal == "BUY" and trend < 0:
            adjustments.append(-0.15)
        elif signal == "SELL" and trend > 0:
            adjustments.append(-0.15)
        
        # Apply adjustments
        adjusted_confidence = confidence + sum(adjustments)
        
        # Clip to [0, 1]
        return max(0.0, min(1.0, adjusted_confidence))
