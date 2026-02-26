"""
PHASE 4: Coordinator Agent (Meta-Agent)
Aggregates signals from specialized agents using weighted voting
Dynamically adjusts weights based on market regime and performance
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from core.llm_factory import LLMFactory
from agents.models import AgentSignal, CoordinatorDecision, AgentPerformance
from agents.technical_agent import TechnicalAgent
from agents.macro_agent import MacroAgent
from agents.sentiment_agent import SentimentAgent
from features.models import TechnicalFeatures


class CoordinatorAgent:
    """
    Meta-agent that coordinates decisions from specialized agents
    Uses dynamic weighting based on:
    - Market volatility regime
    - Recent agent performance
    """
    
    # Default weights
    DEFAULT_WEIGHTS = {
        'technical': 0.40,
        'macro': 0.35,
        'sentiment': 0.25
    }
    
    COORDINATION_PROMPT = PromptTemplate(
        input_variables=["technical_signal", "macro_signal", "sentiment_signal", 
                        "technical_confidence", "macro_confidence", "sentiment_confidence",
                        "volatility_regime"],
        template="""You are a meta-analyst coordinating trading decisions from specialized agents.

Agent Signals:
1. Technical Agent: {technical_signal} (confidence: {technical_confidence})
2. Macro Agent: {macro_signal} (confidence: {macro_confidence})
3. Sentiment Agent: {sentiment_signal} (confidence: {sentiment_confidence})

Market Regime: {volatility_regime} volatility

Provide:
1. Final decision: BUY, SELL, or NEUTRAL
2. Overall confidence: 0.0 to 1.0
3. Risk level: LOW, MEDIUM, or HIGH
4. Reasoning that explains how you weighed the different signals

Response format:
Decision: [BUY/SELL/NEUTRAL]
Confidence: [0.0-1.0]
Risk: [LOW/MEDIUM/HIGH]
Reasoning: [Your synthesis]
"""
    )
    
    def __init__(self):
        self.llm = LLMFactory.get_llm()
        self.coordination_chain = LLMChain(llm=self.llm, prompt=self.COORDINATION_PROMPT)
        
        # Initialize specialized agents
        self.technical_agent = TechnicalAgent()
        self.macro_agent = MacroAgent()
        self.sentiment_agent = SentimentAgent()
    
    def make_decision(self, symbol: str, timestamp: Optional[datetime] = None) -> Dict:
        """
        Coordinate decision from all agents
        Returns final trading decision
        """
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # 1. Get signals from all agents
        signals = self._get_all_signals(symbol, timestamp)
        
        # 2. Determine market regime
        volatility_regime = self._determine_market_regime(symbol, timestamp)
        
        # 3. Calculate dynamic weights
        weights = self._calculate_dynamic_weights(symbol, volatility_regime)
        
        # 4. Aggregate signals using weighted voting
        aggregated_decision = self._aggregate_signals(signals, weights)
        
        # 5. Use LLM for final reasoning
        final_decision = self._get_llm_coordination(signals, volatility_regime)
        
        # 6. Combine quantitative and qualitative decisions
        combined_decision = self._combine_decisions(aggregated_decision, final_decision)
        
        # 7. Determine risk level
        risk_level = self._assess_risk(signals, combined_decision, volatility_regime)
        
        # 8. Save decision to database
        decision_record = self._save_decision(
            symbol, 
            combined_decision, 
            signals, 
            weights, 
            risk_level, 
            volatility_regime
        )
        
        return {
            'decision': combined_decision['decision'],
            'confidence': combined_decision['confidence'],
            'risk_level': risk_level,
            'reasoning': combined_decision['reasoning'],
            'weights': weights,
            'agent_signals': {
                'technical': signals['technical'],
                'macro': signals['macro'],
                'sentiment': signals['sentiment']
            }
        }
    
    def _get_all_signals(self, symbol: str, timestamp: datetime) -> Dict:
        """Get signals from all agents"""
        
        try:
            technical_output = self.technical_agent.analyze(symbol, timestamp)
        except Exception as e:
            print(f"Technical agent error: {e}")
            technical_output = None
        
        try:
            macro_output = self.macro_agent.analyze(symbol, timestamp)
        except Exception as e:
            print(f"Macro agent error: {e}")
            macro_output = None
        
        try:
            sentiment_output = self.sentiment_agent.analyze(symbol, timestamp)
        except Exception as e:
            print(f"Sentiment agent error: {e}")
            sentiment_output = None
        
        return {
            'technical': technical_output,
            'macro': macro_output,
            'sentiment': sentiment_output
        }
    
    def _determine_market_regime(self, symbol: str, timestamp: datetime) -> str:
        """
        Determine current market regime based on volatility
        Returns: 'low', 'normal', 'high'
        """
        
        # Get recent volatility
        features = TechnicalFeatures.objects.filter(
            symbol=symbol,
            timestamp__lte=timestamp
        ).order_by('-timestamp').first()
        
        if not features or not features.rolling_vol_20:
            return 'normal'
        
        current_vol = features.rolling_vol_20
        
        # Get historical volatility for comparison
        lookback = timestamp - timedelta(days=90)
        historical_vols = TechnicalFeatures.objects.filter(
            symbol=symbol,
            timestamp__gte=lookback,
            timestamp__lte=timestamp
        ).values_list('rolling_vol_20', flat=True)
        
        if len(historical_vols) < 10:
            return 'normal'
        
        vol_array = [v for v in historical_vols if v is not None]
        if not vol_array:
            return 'normal'
        
        median_vol = np.median(vol_array)
        
        # Classify regime
        if current_vol < median_vol * 0.7:
            return 'low'
        elif current_vol > median_vol * 1.5:
            return 'high'
        else:
            return 'normal'
    
    def _calculate_dynamic_weights(self, symbol: str, regime: str) -> Dict:
        """
        Calculate dynamic weights based on:
        1. Recent agent performance
        2. Market regime
        """
        
        # Start with default weights
        weights = self.DEFAULT_WEIGHTS.copy()
        
        # Adjust based on regime
        if regime == 'low':
            # Low volatility: favor macro and trend
            weights['macro'] += 0.10
            weights['technical'] -= 0.05
            weights['sentiment'] -= 0.05
        
        elif regime == 'high':
            # High volatility: favor technical and sentiment
            weights['technical'] += 0.10
            weights['sentiment'] += 0.05
            weights['macro'] -= 0.15
        
        # Adjust based on recent performance
        lookback_days = 30
        lookback_date = datetime.now().date() - timedelta(days=lookback_days)
        
        for agent_type in ['technical', 'macro', 'sentiment']:
            performance = AgentPerformance.objects.filter(
                agent_type=agent_type,
                symbol=symbol,
                date__gte=lookback_date
            ).order_by('-date').first()
            
            if performance and performance.accuracy > 0:
                # Adjust weight based on accuracy
                # High accuracy -> increase weight
                # Low accuracy -> decrease weight
                accuracy_adjustment = (performance.accuracy - 0.5) * 0.2  # Scale to ±0.1
                weights[agent_type] += accuracy_adjustment
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Ensure minimum weight of 0.1 for each agent
        for agent_type in weights:
            weights[agent_type] = max(0.1, weights[agent_type])
        
        # Re-normalize after minimum enforcement
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def _aggregate_signals(self, signals: Dict, weights: Dict) -> Dict:
        """
        Aggregate signals using weighted voting
        Returns preliminary decision
        """
        
        # Convert signals to numerical values
        signal_values = {}
        confidences = {}
        
        for agent_type, output in signals.items():
            if output is None:
                signal_values[agent_type] = 0
                confidences[agent_type] = 0
            else:
                # BUY = +1, SELL = -1, NEUTRAL = 0
                if output.signal == 'BUY':
                    signal_values[agent_type] = 1
                elif output.signal == 'SELL':
                    signal_values[agent_type] = -1
                else:
                    signal_values[agent_type] = 0
                
                confidences[agent_type] = output.confidence
        
        # Weighted vote
        weighted_sum = 0
        total_confidence = 0
        
        for agent_type in ['technical', 'macro', 'sentiment']:
            weighted_vote = signal_values[agent_type] * confidences[agent_type] * weights[agent_type]
            weighted_sum += weighted_vote
            total_confidence += confidences[agent_type] * weights[agent_type]
        
        # Determine final signal
        if weighted_sum > 0.2:
            decision = 'BUY'
        elif weighted_sum < -0.2:
            decision = 'SELL'
        else:
            decision = 'NEUTRAL'
        
        # Calculate overall confidence
        confidence = abs(weighted_sum)
        
        return {
            'decision': decision,
            'confidence': min(confidence, 1.0),
            'weighted_sum': weighted_sum
        }
    
    def _get_llm_coordination(self, signals: Dict, regime: str) -> Dict:
        """Get LLM's coordination decision"""
        
        # Prepare signal summaries
        tech_signal = signals['technical'].signal if signals['technical'] else 'NEUTRAL'
        tech_conf = signals['technical'].confidence if signals['technical'] else 0.5
        
        macro_signal = signals['macro'].signal if signals['macro'] else 'NEUTRAL'
        macro_conf = signals['macro'].confidence if signals['macro'] else 0.5
        
        sent_signal = signals['sentiment'].signal if signals['sentiment'] else 'NEUTRAL'
        sent_conf = signals['sentiment'].confidence if signals['sentiment'] else 0.5
        
        # Get LLM response
        llm_response = self.coordination_chain.run(
            technical_signal=tech_signal,
            macro_signal=macro_signal,
            sentiment_signal=sent_signal,
            technical_confidence=f"{tech_conf:.2f}",
            macro_confidence=f"{macro_conf:.2f}",
            sentiment_confidence=f"{sent_conf:.2f}",
            volatility_regime=regime
        )
        
        # Parse response
        import re
        
        decision = 'NEUTRAL'
        if 'Decision: BUY' in llm_response or 'Decision: buy' in llm_response.lower():
            decision = 'BUY'
        elif 'Decision: SELL' in llm_response or 'Decision: sell' in llm_response.lower():
            decision = 'SELL'
        
        confidence = 0.5
        conf_match = re.search(r'Confidence:\s*([0-9.]+)', llm_response)
        if conf_match:
            confidence = float(conf_match.group(1))
        
        return {
            'decision': decision,
            'confidence': confidence,
            'reasoning': llm_response
        }
    
    def _combine_decisions(self, quant_decision: Dict, qual_decision: Dict) -> Dict:
        """Combine quantitative and qualitative decisions"""
        
        # If both agree, high confidence
        if quant_decision['decision'] == qual_decision['decision']:
            return {
                'decision': quant_decision['decision'],
                'confidence': min((quant_decision['confidence'] + qual_decision['confidence']) / 2 * 1.1, 1.0),
                'reasoning': qual_decision['reasoning']
            }
        
        # If they disagree, use confidence to decide
        if quant_decision['confidence'] > qual_decision['confidence']:
            return {
                'decision': quant_decision['decision'],
                'confidence': quant_decision['confidence'] * 0.8,  # Reduce confidence due to disagreement
                'reasoning': f"Quantitative analysis suggests {quant_decision['decision']}, though qualitative differs. {qual_decision['reasoning']}"
            }
        else:
            return {
                'decision': qual_decision['decision'],
                'confidence': qual_decision['confidence'] * 0.8,
                'reasoning': qual_decision['reasoning']
            }
    
    def _assess_risk(self, signals: Dict, decision: Dict, regime: str) -> str:
        """Assess risk level of the decision"""
        
        # Count disagreements
        signal_list = []
        for output in signals.values():
            if output:
                signal_list.append(output.signal)
        
        # Check consensus
        if len(set(signal_list)) == 1:
            # Full consensus - lower risk
            base_risk = 'LOW'
        elif len(set(signal_list)) == 2:
            # Partial consensus
            base_risk = 'MEDIUM'
        else:
            # No consensus
            base_risk = 'HIGH'
        
        # Adjust based on confidence
        if decision['confidence'] < 0.4:
            base_risk = 'HIGH'
        elif decision['confidence'] > 0.75:
            # Keep or reduce risk
            if base_risk == 'MEDIUM':
                base_risk = 'LOW'
        
        # Adjust based on regime
        if regime == 'high':
            if base_risk == 'LOW':
                base_risk = 'MEDIUM'
            elif base_risk == 'MEDIUM':
                base_risk = 'HIGH'
        
        return base_risk
    
    def _save_decision(self, symbol: str, decision: Dict, signals: Dict, 
                      weights: Dict, risk_level: str, regime: str) -> CoordinatorDecision:
        """Save coordinator decision to database"""
        
        # Get most recent signal records
        tech_signal = AgentSignal.objects.filter(
            agent_type='technical', symbol=symbol
        ).order_by('-timestamp').first()
        
        macro_signal = AgentSignal.objects.filter(
            agent_type='macro', symbol=symbol
        ).order_by('-timestamp').first()
        
        sent_signal = AgentSignal.objects.filter(
            agent_type='sentiment', symbol=symbol
        ).order_by('-timestamp').first()
        
        return CoordinatorDecision.objects.create(
            symbol=symbol,
            decision=decision['decision'],
            confidence=decision['confidence'],
            risk_level=risk_level,
            technical_signal=tech_signal,
            macro_signal=macro_signal,
            sentiment_signal=sent_signal,
            weights=weights,
            reasoning=decision['reasoning'],
            volatility_regime=regime
        )
