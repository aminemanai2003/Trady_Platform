"""
XAI (Explainable AI) Formatter Module
Structures trading decisions into human-readable explanations
Provides agent contributions, feature importance, risk analysis
"""
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class XAIFormatter:
    """
    Formats trading decisions into structured, explainable output.
    Combines agent signals, actuarial analysis, judge reasoning, and risk assessment.
    """
    
    def __init__(self ):
        """Initialize XAI Formatter"""
        pass
    
    def format(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict,
        judge_decision: Dict,
        risk_validation: Dict,
        market_context: Optional[Dict] = None
    ) -> Dict:
        """
        Format complete trading decision with explanations.
        
        Args:
            coordinator_output: Output from CoordinatorAgentV2
            actuarial_scores: Scores from ActuarialScorer
            judge_decision: Decision from LLMJudge
            risk_validation: Validation from RiskManager
            market_context: Optional additional context
        
        Returns:
            Structured XAI output dict
        """
        # Determine final decision
        if judge_decision['verdict'] == 'REJECT':
            final_decision = 'REJECTED'
            rejection_stage = 'LLM_JUDGE'
        elif not risk_validation['approved']:
            final_decision = 'REJECTED'
            rejection_stage = 'RISK_MANAGER'
        elif judge_decision['verdict'] == 'APPROVE':
            final_decision = 'APPROVED'
            rejection_stage = None
        else:  # MODIFY
            final_decision = 'APPROVED_MODIFIED'
            rejection_stage = None
        
        # Build agent breakdown
        agent_breakdown = self._build_agent_breakdown(coordinator_output)
        
        # Build coordinator analysis
        coordinator_analysis = self._build_coordinator_analysis(coordinator_output)
        
        # Build human explanation
        human_explanation = self._build_human_explanation(
            final_decision,
            coordinator_output,
            actuarial_scores,
            judge_decision,
            risk_validation,
            agent_breakdown
        )
        
        return {
            'decision': final_decision,
            'symbol': coordinator_output.get('symbol', 'UNKNOWN'),
            'timestamp': coordinator_output.get('timestamp', datetime.now().isoformat()),
            'rejection_stage': rejection_stage,
            'rejection_reason': self._get_rejection_reason(judge_decision, risk_validation),
            
            # Agent contributions
            'agent_breakdown': agent_breakdown,
            
            # Coordinator analysis
            'coordinator_analysis': coordinator_analysis,
            
            # Actuarial metrics
            'actuarial_metrics': {
                'expected_value_pips': actuarial_scores.get('expected_value_pips', 0),
                'expected_value_usd': actuarial_scores.get('expected_value_usd', 0),
                'probability_win': actuarial_scores.get('probability_win', 0),
                'probability_loss': actuarial_scores.get('probability_loss', 0),
                'risk_reward_ratio': actuarial_scores.get('risk_reward_ratio', 0),
                'kelly_fraction': actuarial_scores.get('kelly_fraction', 0),
                'verdict': actuarial_scores.get('verdict', 'UNKNOWN'),
                'recommendation': actuarial_scores.get('recommendation', '')
            },
            
            # Judge evaluation
            'judge_evaluation': {
                'verdict': judge_decision['verdict'],
                'reasoning': judge_decision['reasoning'],
                'latency_ms': judge_decision.get('latency_ms', 0),
                'rejection_criteria': judge_decision.get('rejection_criteria', []),
                'from_cache': judge_decision.get('from_cache', False),
                'confidence_adjusted': judge_decision.get('confidence_adjusted')
            },
            
            # Risk assessment
            'risk_assessment': {
                'approved': risk_validation['approved'],
                'reason': risk_validation['reason'],
                'violations': risk_validation.get('violations', []),
                'position_size': risk_validation.get('position_size', 0.0),
                'stop_loss': risk_validation.get('stop_loss'),
                'take_profit': risk_validation.get('take_profit'),
                'stop_loss_pips': risk_validation.get('stop_loss_pips', 0),
                'take_profit_pips': risk_validation.get('take_profit_pips', 0),
                'risk_reward_ratio': risk_validation.get('risk_reward_ratio', 0),
                'risk_pct': risk_validation.get('risk_pct', 0),
                'risk_amount': risk_validation.get('risk_amount', 0),
                'drawdown_pct': risk_validation.get('drawdown_pct', 0),
                'current_positions': risk_validation.get('current_positions', 0),
                'max_positions': risk_validation.get('max_positions', 4)
            },
            
            # Human-readable explanation
            'human_explanation': human_explanation,
            
            # Performance context (if available)
            'performance_context': self._build_performance_context(coordinator_output),
            
            # Market context (if available)
            'market_context': market_context or {}
        }
    
    def _build_agent_breakdown(self, coordinator_output: Dict) -> Dict:
        """
        Build detailed agent contribution breakdown.
        
        Args:
            coordinator_output: Coordinator output
        
        Returns:
            Dict with agent contributions
        """
        agent_signals = coordinator_output.get('agent_signals', {})
        weights = coordinator_output.get('weights_used', {})
        
        signal_map = {-1: "SELL", 0: "NEUTRAL", 1: "BUY"}
        
        breakdown = {}
        
        for agent_name, agent_data in agent_signals.items():
            signal = agent_data.get('signal', 0)
            confidence = agent_data.get('confidence', 0.5)
            weight = weights.get(agent_name, 0.33)
            contribution = signal * weight
            
            # Extract key features
            features_used = agent_data.get('features_used', {})
            key_features = self._extract_key_features(agent_name, features_used)
            
            breakdown[agent_name] = {
                'signal': signal_map.get(signal, 'UNKNOWN'),
                'signal_value': signal,
                'confidence': round(confidence, 2),
                'weight': round(weight, 2),
                'contribution': round(contribution, 2),
                'key_features': key_features,
                'reasoning': agent_data.get('deterministic_reason', ''),
                'influence_rank': None  # Will be set later
            }
        
        # Rank agents by absolute contribution
        sorted_agents = sorted(
            breakdown.items(),
            key=lambda x: abs(x[1]['contribution']),
            reverse=True
        )
        
        for rank, (agent_name, data) in enumerate(sorted_agents, 1):
            breakdown[agent_name]['influence_rank'] = rank
        
        return breakdown
    
    def _extract_key_features(self, agent_name: str, features: Dict) -> List[str]:
        """
        Extract key features that drove the agent's decision.
        
        Args:
            agent_name: Name of the agent
            features: Features dict from agent
        
        Returns:
            List of key feature descriptions
        """
        key_features = []
        
        if agent_name == 'TechnicalV2':
            # Technical features
            if 'RSI_14' in features:
                rsi = features['RSI_14']
                if rsi < 30:
                    key_features.append(f"RSI oversold ({rsi:.1f})")
                elif rsi > 70:
                    key_features.append(f"RSI overbought ({rsi:.1f})")
                else:
                    key_features.append(f"RSI neutral ({rsi:.1f})")
            
            if 'MACD_histogram' in features and features['MACD_histogram'] != 0:
                macd = features['MACD_histogram']
                direction = "bullish" if macd > 0 else "bearish"
                key_features.append(f"MACD {direction} ({macd:.4f})")
            
            if 'ADX' in features:
                adx = features['ADX']
                if adx > 25:
                    key_features.append(f"Strong trend (ADX {adx:.1f})")
                else:
                    key_features.append(f"Weak trend (ADX {adx:.1f})")
        
        elif agent_name == 'MacroV2':
            # Macro features
            if 'rate_differential' in features:
                rate_diff = features['rate_differential']
                key_features.append(f"Rate differential {rate_diff*100:.1f} bps")
            
            if 'inflation_differential' in features:
                infl_diff = features['inflation_differential']
                key_features.append(f"Inflation differential {infl_diff*100:.1f} bps")
            
            if 'risk_sentiment' in features:
                risk_sent = features['risk_sentiment']
                sentiment = "risk-on" if risk_sent > 0.2 else "risk-off" if risk_sent < -0.2 else "neutral"
                key_features.append(f"Market {sentiment}")
        
        elif agent_name == 'SentimentV2':
            # Sentiment features
            if 'avg_sentiment' in features:
                sent = features['avg_sentiment']
                sentiment = "bullish" if sent > 0.1 else "bearish" if sent < -0.1 else "neutral"
                key_features.append(f"News {sentiment} ({sent:.2f})")
            
            if 'article_count' in features:
                count = features['article_count']
                key_features.append(f"{count} articles analyzed")
        
        # If no features extracted, add generic
        if not key_features:
            key_features.append("No specific features highlighted")
        
        return key_features
    
    def _build_coordinator_analysis(self, coordinator_output: Dict) -> Dict:
        """
        Build coordinator-level analysis.
        
        Args:
            coordinator_output: Coordinator output
        
        Returns:
            Dict with coordinator analysis
        """
        signal_map = {-1: "SELL", 0: "NEUTRAL", 1: "BUY"}
        
        return {
            'initial_signal': signal_map.get(coordinator_output.get('final_signal', 0), 'UNKNOWN'),
            'weighted_score': round(coordinator_output.get('weighted_score', 0), 2),
            'initial_confidence': round(coordinator_output.get('confidence', 0.5), 2),
            'conflicts_detected': coordinator_output.get('conflicts_detected', False),
            'conflict_description': self._describe_conflicts(coordinator_output),
            'market_regime': coordinator_output.get('market_regime', 'unknown'),
            'cross_pair_validation': coordinator_output.get('cross_pair_correlations', {})
        }
    
    def _describe_conflicts(self, coordinator_output: Dict) -> str:
        """
        Describe agent conflicts in human terms.
        
        Args:
            coordinator_output: Coordinator output
        
        Returns:
            Conflict description string
        """
        if not coordinator_output.get('conflicts_detected', False):
            return "No conflicts - agents in general agreement"
        
        agent_signals = coordinator_output.get('agent_signals', {})
        signal_map = {-1: "SELL", 0: "NEUTRAL", 1: "BUY"}
        
        signals = [
            f"{name}: {signal_map.get(data.get('signal', 0), 'UNKNOWN')}"
            for name, data in agent_signals.items()
        ]
        
        return f"Conflicting signals detected: {', '.join(signals)}"
    
    def _get_rejection_reason(
        self,
        judge_decision: Dict,
        risk_validation: Dict
    ) -> Optional[str]:
        """
        Get consolidated rejection reason.
        
        Args:
            judge_decision: Judge decision
            risk_validation: Risk validation
        
        Returns:
            Rejection reason string or None
        """
        if judge_decision['verdict'] == 'REJECT':
            return f"LLM Judge: {judge_decision['reasoning']}"
        elif not risk_validation['approved']:
            return f"Risk Manager: {risk_validation['reason']}"
        return None
    
    def _build_human_explanation(
        self,
        decision: str,
        coordinator_output: Dict,
        actuarial_scores: Dict,
        judge_decision: Dict,
        risk_validation: Dict,
        agent_breakdown: Dict
    ) -> Dict:
        """
        Build human-readable explanation.
        
        Args:
            decision: Final decision
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
            judge_decision: Judge decision
            risk_validation: Risk validation
            agent_breakdown: Agent breakdown
        
        Returns:
            Dict with summary, details, recommendation
        """
        signal = coordinator_output.get('final_signal', 0)
        symbol = coordinator_output.get('symbol', 'UNKNOWN')
        confidence = coordinator_output.get('confidence', 0.5)
        
        signal_map = {-1: "SELL", 0: "NEUTRAL", 1: "BUY"}
        signal_text = signal_map.get(signal, 'UNKNOWN')
        
        # Build summary
        if decision == 'APPROVED':
            summary = f"Trade APPROVED: {signal_text} {symbol} with {confidence:.0%} confidence."
        elif decision == 'APPROVED_MODIFIED':
            summary = f"Trade APPROVED (with modifications): {signal_text} {symbol}."
        else:
            summary = f"Trade REJECTED: {symbol} {signal_text} signal declined."
        
        # Build details
        details_parts = []
        
        # Agent consensus
        top_agent = sorted(
            agent_breakdown.items(),
            key=lambda x: abs(x[1]['contribution']),
            reverse=True
        )[0]
        
        top_agent_name = top_agent[0].replace('V2', '')
        top_agent_data = top_agent[1]
        
        details_parts.append(
            f"Primary driver: {top_agent_name} Agent ({top_agent_data['signal']}, "
            f"{top_agent_data['confidence']:.0%} confidence, {top_agent_data['weight']:.0%} weight)."
        )
        
        # Key features
        if top_agent_data['key_features']:
            features_text = ', '.join(top_agent_data['key_features'][:2])
            details_parts.append(f"Key indicators: {features_text}.")
        
        # Actuarial
        ev = actuarial_scores.get('expected_value_pips', 0)
        p_win = actuarial_scores.get('probability_win', 0)
        details_parts.append(
            f"Expected value: {ev:+.1f} pips with {p_win:.0%} probability of success."
        )
        
        # Risk
        if decision == 'APPROVED' and risk_validation.get('position_size', 0) > 0:
            pos_size = risk_validation['position_size']
            sl_pips = risk_validation.get('stop_loss_pips', 0)
            tp_pips = risk_validation.get('take_profit_pips', 0)
            risk_pct = risk_validation.get('risk_pct', 0)
            
            details_parts.append(
                f"Position: {pos_size} lots, SL {sl_pips:.0f} pips, TP {tp_pips:.0f} pips "
                f"(Risk: {risk_pct:.1f}% of capital)."
            )
        
        # Judge reasoning (if rejected)
        if decision in ['REJECTED', 'APPROVED_MODIFIED']:
            details_parts.append(judge_decision['reasoning'])
        
        details = ' '.join(details_parts)
        
        # Recommendation
        if decision == 'APPROVED':
            recommendation = f"Execute {signal_text} trade as planned."
        elif decision == 'APPROVED_MODIFIED':
            recommendation = "Execute trade with Judge-recommended modifications."
        else:
            recommendation = f"Do not trade. {self._get_rejection_reason(judge_decision, risk_validation)}"
        
        return {
            'summary': summary,
            'details': details,
            'recommendation': recommendation
        }
    
    def _build_performance_context(self, coordinator_output: Dict) -> Dict:
        """
        Build performance context (if available).
        
        Args:
            coordinator_output: Coordinator output
        
        Returns:
            Dict with performance context
        """
        # TODO: Query database for similar historical setups
        # For now, return placeholder
        return {
            'similar_setups_last_30_days': 0,
            'win_rate_similar': 0.0,
            'avg_pnl_similar_pips': 0.0,
            'note': 'Performance context not yet implemented'
        }
