"""
Coordinator Agent V2 - DETERMINISTIC AGGREGATION
NO LLM for trading decisions
LLM only for final explanation generation
"""
from typing import Dict, List
import numpy as np
from datetime import datetime, timedelta
from signal_layer.technical_agent_v2 import TechnicalAgentV2
from signal_layer.macro_agent_v2 import MacroAgentV2
from signal_layer.sentiment_agent_v2 import SentimentAgentV2
from monitoring.performance_tracker import PerformanceTracker


class CoordinatorAgentV2:
    """
    Meta-Agent that coordinates all agents
    
    DETERMINISTIC:
    - Weighted voting
    - Dynamic weight adjustment based on performance
    - Volatility regime detection
    - Conflict detection
    
    LLM: Only for final explanation text
    """
    
    def __init__(self):
        self.technical_agent = TechnicalAgentV2()
        self.macro_agent = MacroAgentV2()
        self.sentiment_agent = SentimentAgentV2()
        self.performance_tracker = PerformanceTracker()
        
        # Default weights (updated dynamically)
        self.agent_weights = {
            'TechnicalV2': 0.40,
            'MacroV2': 0.35,
            'SentimentV2': 0.25
        }
    
    def generate_final_signal(
        self,
        symbol: str,
        base_currency: str,
        quote_currency: str
    ) -> Dict:
        """
        Generate final aggregated signal
        
        Process:
        1. Collect signals from all agents (deterministic)
        2. Update weights based on recent performance (deterministic)
        3. Detect market regime (deterministic)
        4. Weighted vote (deterministic)
        5. Apply safety rules (deterministic)
        6. Generate explanation (LLM used here ONLY)
        
        Returns:
            {
                'final_signal': -1/0/1,
                'confidence': 0-1,
                'agent_signals': dict,
                'weights_used': dict,
                'conflicts_detected': bool,
                'explanation': str (from LLM)
            }
        """
        # Step 1: Collect all agent signals
        technical_signal = self.technical_agent.generate_signal(symbol)
        
        # Get volatility for macro agent
        # (Would normally calculate from recent data)
        price_volatility = self._estimate_volatility(symbol)
        
        macro_signal = self.macro_agent.generate_signal(
            base_currency,
            quote_currency,
            price_volatility
        )
        
        sentiment_signal = self.sentiment_agent.generate_signal(
            [base_currency, quote_currency]
        )
        
        agent_signals = {
            'TechnicalV2': technical_signal,
            'MacroV2': macro_signal,
            'SentimentV2': sentiment_signal
        }
        
        # Step 2: Update weights based on recent performance
        updated_weights = self._calculate_dynamic_weights(agent_signals)
        
        # Step 3: Detect market regime
        regime = self._detect_market_regime(technical_signal, price_volatility)
        
        # Step 4: Weighted aggregation (PURE MATH)
        final_signal, confidence = self._aggregate_signals(
            agent_signals,
            updated_weights,
            regime
        )
        
        # Step 5: Safety checks
        conflicts = self._detect_conflicts(agent_signals)
        final_signal, confidence = self._apply_safety_rules(
            final_signal,
            confidence,
            conflicts,
            regime
        )
        
        # Step 6: Generate explanation (LLM used ONLY here)
        explanation = self._generate_explanation_text(
            final_signal,
            agent_signals,
            updated_weights,
            conflicts
        )
        
        return {
            'final_signal': final_signal,
            'confidence': confidence,
            'agent_signals': agent_signals,
            'weights_used': updated_weights,
            'market_regime': regime,
            'conflicts_detected': conflicts,
            'deterministic_reason': self._generate_deterministic_reason(
                final_signal, agent_signals, updated_weights
            ),
            'explanation': explanation,  # Natural language from LLM
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_dynamic_weights(self, agent_signals: Dict) -> Dict[str, float]:
        """
        Adjust agent weights based on recent 30-day performance
        
        PURE DETERMINISTIC LOGIC
        """
        # Get recent performance for each agent
        performances = {}
        for agent_name in self.agent_weights.keys():
            perf = self.performance_tracker.get_agent_performance(agent_name, days=30)
            performances[agent_name] = perf.get('sharpe_ratio', 0.0)
        
        # If no performance data, use default weights
        if all(p == 0.0 for p in performances.values()):
            return self.agent_weights.copy()
        
        # Normalize Sharpe ratios to weights (softmax-like)
        # Add constant to avoid negative weights
        adjusted = {k: max(v + 2.0, 0.1) for k, v in performances.items()}
        total = sum(adjusted.values())
        
        new_weights = {k: v / total for k, v in adjusted.items()}
        
        # Smooth transition (80% old, 20% new)
        smoothed = {
            k: 0.8 * self.agent_weights[k] + 0.2 * new_weights[k]
            for k in self.agent_weights.keys()
        }
        
        # Normalize to sum to 1.0
        total_smoothed = sum(smoothed.values())
        final_weights = {k: v / total_smoothed for k, v in smoothed.items()}
        
        return final_weights
    
    def _detect_market_regime(self, technical_signal: Dict, volatility: float) -> str:
        """
        Detect market regime (trending, ranging, volatile)
        
        DETERMINISTIC THRESHOLDS
        """
        adx = technical_signal['features_used'].get('adx', 0)
        
        if volatility > 0.02:  # High volatility
            return 'volatile'
        elif adx > 25:  # Strong trend
            return 'trending'
        else:
            return 'ranging'
    
    def _aggregate_signals(
        self,
        agent_signals: Dict,
        weights: Dict,
        regime: str
    ) -> tuple:
        """
        Weighted vote aggregation
        
        PURE MATH - NO LLM
        """
        # Adjust weights based on regime
        regime_weights = weights.copy()
        
        if regime == 'trending':
            # Boost technical weight in trends
            regime_weights['TechnicalV2'] *= 1.3
        elif regime == 'ranging':
            # Boost macro weight in ranges
            regime_weights['MacroV2'] *= 1.2
        elif regime == 'volatile':
            # Lower all weights in volatile periods
            regime_weights = {k: v * 0.7 for k, v in regime_weights.items()}
        
        # Renormalize
        total_weight = sum(regime_weights.values())
        regime_weights = {k: v / total_weight for k, v in regime_weights.items()}
        
        # Weighted sum of signals
        weighted_signal_sum = sum(
            agent_signals[agent]['signal'] * 
            agent_signals[agent]['confidence'] *
            regime_weights[agent]
            for agent in regime_weights.keys()
        )
        
        # Weighted confidence
        avg_confidence = sum(
            agent_signals[agent]['confidence'] * regime_weights[agent]
            for agent in regime_weights.keys()
        )
        
        # Convert to discrete signal
        if weighted_signal_sum > 0.25:
            final_signal = 1
        elif weighted_signal_sum < -0.25:
            final_signal = -1
        else:
            final_signal = 0
        
        return final_signal, avg_confidence
    
    def _detect_conflicts(self, agent_signals: Dict) -> bool:
        """
        Detect if agents strongly disagree
        
        DETERMINISTIC
        """
        signals = [
            agent_signals[agent]['signal'] 
            for agent in agent_signals.keys()
        ]
        
        # If we have both strong buy (+1) and strong sell (-1)
        if 1 in signals and -1 in signals:
            return True
        
        return False
    
    def _apply_safety_rules(
        self,
        signal: int,
        confidence: float,
        conflicts: bool,
        regime: str
    ) -> tuple:
        """
        Apply production safety rules
        
        - Reduce confidence if conflicts detected
        - Reduce confidence in volatile regimes
        - Require min confidence threshold
        """
        adjusted_confidence = confidence
        
        # Rule 1: Conflicts reduce confidence
        if conflicts:
            adjusted_confidence *= 0.5
        
        # Rule 2: Volatile regime reduces confidence
        if regime == 'volatile':
            adjusted_confidence *= 0.7
        
        # Rule 3: Minimum confidence threshold
        if adjusted_confidence < 0.3:
            return 0, adjusted_confidence  # Force neutral
        
        return signal, adjusted_confidence
    
    def _estimate_volatility(self, symbol: str) -> float:
        """Estimate recent volatility (simplified)"""
        # Would normally calculate from recent returns
        # Placeholder for now
        return 0.01
    
    def _generate_deterministic_reason(
        self,
        final_signal: int,
        agent_signals: Dict,
        weights: Dict
    ) -> str:
        """Generate structured deterministic reason"""
        signal_names = {1: 'BUY', 0: 'NEUTRAL', -1: 'SELL'}
        
        parts = [f"Final: {signal_names[final_signal]}"]
        
        for agent, signal_data in agent_signals.items():
            agent_sig = signal_names[signal_data['signal']]
            conf = signal_data['confidence']
            weight = weights[agent]
            parts.append(f"{agent}: {agent_sig} ({conf:.2f}, w={weight:.2f})")
        
        return " | ".join(parts)
    
    def _generate_explanation_text(
        self,
        final_signal: int,
        agent_signals: Dict,
        weights: Dict,
        conflicts: bool
    ) -> str:
        """
        Generate natural language explanation
        
        THIS IS WHERE LLM IS USED (optional)
        For now, return structured text
        """
        signal_names = {1: 'BUY', 0: 'NEUTRAL', -1: 'SELL'}
        
        explanation = f"Final Decision: {signal_names[final_signal]}\n\n"
        
        explanation += "Agent Breakdown:\n"
        for agent, data in agent_signals.items():
            explanation += f"- {agent}: {signal_names[data['signal']]} "
            explanation += f"(confidence: {data['confidence']:.2%}, weight: {weights[agent]:.2%})\n"
            explanation += f"  Reason: {data['deterministic_reason']}\n"
        
        if conflicts:
            explanation += "\n⚠️ Warning: Agents disagree - confidence reduced for safety.\n"
        
        return explanation
