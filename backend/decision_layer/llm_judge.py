"""
LLM Judge Module
Local Ollama-based validation gate for trading decisions
Approves, rejects, or modifies trades based on comprehensive analysis
"""
from typing import Dict, Optional
import logging
import time
import hashlib
import json

from rag_tutor.services.ollama_service import generate_answer, _check_ollama_available

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    LLM-based decision validator using local Ollama.
    Acts as final gate before risk management.
    Can APPROVE, REJECT, or MODIFY trades.
    """
    
    # Rejection criteria thresholds
    MIN_CONFIDENCE = 0.50
    MIN_EV_PIPS = 0.0
    TIMEOUT_MS = 500
    
    def __init__(self, model: str = "llama3.2:3b", timeout_ms: int = 500):
        """
        Initialize LLM Judge.
        
        Args:
            model: Ollama model name (default: llama3.2:3b)
            timeout_ms: Maximum latency in milliseconds (default: 500)
        """
        self.model = model
        self.timeout_ms = timeout_ms
        self._cache = {}  # Simple in-memory cache
        
        # Check if Ollama is available
        if not _check_ollama_available():
            logger.warning("Ollama not available - Judge will default to REJECT")
            self.ollama_available = False
        else:
            logger.info(f"LLM Judge initialized with model: {model}")
            self.ollama_available = True
    
    def evaluate(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict,
        market_context: Optional[Dict] = None
    ) -> Dict:
        """
        Evaluate trade using LLM reasoning.
        
        Args:
            coordinator_output: Output from CoordinatorAgentV2
            actuarial_scores: Scores from ActuarialScorer
            market_context: Optional additional market context
        
        Returns:
            Dict with 'verdict', 'reasoning', 'latency_ms', 'confidence_adjusted'
        """
        start_time = time.perf_counter()
        
        # Check if Ollama is available
        if not self.ollama_available:
            return self._fallback_decision(coordinator_output, actuarial_scores)
        
        # Check cache
        cache_key = self._generate_cache_key(coordinator_output, actuarial_scores)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.info(f"Cache hit for Judge decision: {cached['verdict']}")
            cached['from_cache'] = True
            return cached
        
        # Quick rejection checks (before LLM call)
        quick_reject = self._quick_rejection_check(coordinator_output, actuarial_scores)
        if quick_reject:
            result = {
                'verdict': 'REJECT',
                'reasoning': quick_reject,
                'latency_ms': int((time.perf_counter() - start_time) * 1000),
                'confidence_adjusted': coordinator_output.get('confidence', 0.5),
                'rejection_criteria': ['pre_llm_check'],
                'from_cache': False
            }
            self._cache[cache_key] = result
            return result
        
        # Build prompt
        prompt = self._build_prompt(coordinator_output, actuarial_scores, market_context)
        
        # Call LLM
        try:
            llm_response = generate_answer(
                query=prompt,
                top_k=1,
                temperature=0.2  # Low temperature for deterministic output
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Check timeout
            if latency_ms > self.timeout_ms:
                logger.warning(f"LLM Judge timeout: {latency_ms}ms > {self.timeout_ms}ms")
            
            # Parse LLM response
            parsed = self._parse_llm_response(llm_response)
            
            result = {
                'verdict': parsed['verdict'],
                'reasoning': parsed['reasoning'],
                'latency_ms': latency_ms,
                'confidence_adjusted': parsed.get('confidence_adjusted', coordinator_output.get('confidence', 0.5)),
                'rejection_criteria': parsed.get('rejection_criteria', []),
                'raw_response': llm_response,
                'from_cache': False
            }
            
            # Cache result
            self._cache[cache_key] = result
            
            logger.info(f"LLM Judge verdict: {result['verdict']} ({latency_ms}ms)")
            
            return result
        
        except Exception as e:
            logger.error(f"LLM Judge error: {e}")
            # Fallback to REJECT on error
            return {
                'verdict': 'REJECT',
                'reasoning': f"LLM Judge error: {str(e)}",
                'latency_ms': int((time.perf_counter() - start_time) * 1000),
                'confidence_adjusted': coordinator_output.get('confidence', 0.5),
                'rejection_criteria': ['llm_error'],
                'from_cache': False
            }
    
    def _quick_rejection_check(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict
    ) -> Optional[str]:
        """
        Quick rejection checks before calling LLM.
        
        Args:
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
        
        Returns:
            Rejection reason string if should reject, None otherwise
        """
        confidence = coordinator_output.get('confidence', 0.5)
        conflicts = coordinator_output.get('conflicts_detected', False)
        ev_pips = actuarial_scores.get('expected_value_pips', 0.0)
        final_signal = coordinator_output.get('final_signal', 0)
        
        # NEUTRAL signal
        if final_signal == 0:
            return "NEUTRAL signal - no directional bias"
        
        # Low confidence
        if confidence < self.MIN_CONFIDENCE:
            return f"Confidence {confidence:.2f} below threshold {self.MIN_CONFIDENCE}"
        
        # Negative expected value
        if ev_pips < self.MIN_EV_PIPS:
            return f"Negative expected value: {ev_pips:.2f} pips"
        
        # Conflicting signals with very low confidence
        if conflicts and confidence < 0.55:
            return f"Conflicting agent signals with low confidence ({confidence:.2f})"
        
        return None
    
    def _build_prompt(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict,
        market_context: Optional[Dict] = None
    ) -> str:
        """
        Build structured prompt for LLM Judge.
        
        Args:
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
            market_context: Optional market context
        
        Returns:
            Prompt string
        """
        agent_signals = coordinator_output.get('agent_signals', {})
        
        # Extract agent details
        tech_signal = agent_signals.get('TechnicalV2', {}).get('signal', 0)
        tech_conf = agent_signals.get('TechnicalV2', {}).get('confidence', 0.5)
        macro_signal = agent_signals.get('MacroV2', {}).get('signal', 0)
        macro_conf = agent_signals.get('MacroV2', {}).get('confidence', 0.5)
        sent_signal = agent_signals.get('SentimentV2', {}).get('signal', 0)
        sent_conf = agent_signals.get('SentimentV2', {}).get('confidence', 0.5)
        
        signal_map = {-1: "SELL", 0: "NEUTRAL", 1: "BUY"}
        
        prompt = f"""You are a risk-averse trading validator reviewing a proposed FX trade.

PROPOSED TRADE:
- Final Signal: {signal_map.get(coordinator_output.get('final_signal', 0), 'UNKNOWN')}
- Confidence: {coordinator_output.get('confidence', 0.5):.2f}
- Symbol: {coordinator_output.get('symbol', 'UNKNOWN')}

AGENT CONSENSUS:
- Technical Agent: {signal_map.get(tech_signal, 'UNKNOWN')} (confidence: {tech_conf:.2f})
- Macro Agent: {signal_map.get(macro_signal, 'UNKNOWN')} (confidence: {macro_conf:.2f})
- Sentiment Agent: {signal_map.get(sent_signal, 'UNKNOWN')} (confidence: {sent_conf:.2f})

CONFLICTS DETECTED: {'YES' if coordinator_output.get('conflicts_detected', False) else 'NO'}

ACTUARIAL ANALYSIS:
- Expected Value: {actuarial_scores.get('expected_value_pips', 0):.2f} pips
- Probability of Win: {actuarial_scores.get('probability_win', 0.5):.2%}
- Risk/Reward Ratio: {actuarial_scores.get('risk_reward_ratio', 1.0):.2f}

MARKET REGIME: {coordinator_output.get('market_regime', 'unknown')}

DECISION RULES:
- REJECT if: confidence < 0.50, conflicting signals, negative EV, incoherent setup
- APPROVE if: confidence > 0.70, agent consensus, positive EV, clear directional bias
- MODIFY if: marginal setup that can be improved (adjust confidence/position size)

Based on this analysis, should this trade be APPROVED, REJECTED, or MODIFIED?

Respond in this EXACT format:
VERDICT: [APPROVE/REJECT/MODIFY]
REASON: [One concise sentence explaining your decision]
CONFIDENCE: [Adjusted confidence 0.0-1.0 if MODIFY, otherwise same]
"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse structured LLM response.
        
        Args:
            response: Raw LLM response string
        
        Returns:
            Dict with verdict, reasoning, confidence_adjusted
        """
        lines = response.strip().split('\n')
        
        verdict = 'REJECT'  # Default to most conservative
        reasoning = 'Unable to parse LLM response'
        confidence_adjusted = None
        rejection_criteria = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('VERDICT:'):
                verdict_text = line.split(':', 1)[1].strip().upper()
                if 'APPROVE' in verdict_text:
                    verdict = 'APPROVE'
                elif 'REJECT' in verdict_text:
                    verdict = 'REJECT'
                elif 'MODIFY' in verdict_text:
                    verdict = 'MODIFY'
            
            elif line.startswith('REASON:'):
                reasoning = line.split(':', 1)[1].strip()
                
                # Extract rejection criteria from reasoning
                reasoning_lower = reasoning.lower()
                if 'conflict' in reasoning_lower:
                    rejection_criteria.append('conflicting_signals')
                if 'confidence' in reasoning_lower and 'low' in reasoning_lower:
                    rejection_criteria.append('low_confidence')
                if 'negative' in reasoning_lower or 'ev' in reasoning_lower:
                    rejection_criteria.append('negative_ev')
                if 'ranging' in reasoning_lower or 'volatile' in reasoning_lower:
                    rejection_criteria.append('unfavorable_regime')
            
            elif line.startswith('CONFIDENCE:'):
                try:
                    conf_text = line.split(':', 1)[1].strip()
                    confidence_adjusted = float(conf_text)
                except:
                    pass
        
        return {
            'verdict': verdict,
            'reasoning': reasoning,
            'confidence_adjusted': confidence_adjusted,
            'rejection_criteria': rejection_criteria
        }
    
    def _fallback_decision(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict
    ) -> Dict:
        """
        Fallback decision when Ollama is not available.
        Uses deterministic rules.
        
        Args:
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
        
        Returns:
            Dict with verdict and reasoning
        """
        confidence = coordinator_output.get('confidence', 0.5)
        conflicts = coordinator_output.get('conflicts_detected', False)
        ev_pips = actuarial_scores.get('expected_value_pips', 0.0)
        
        # Conservative fallback logic
        if confidence < 0.60 or conflicts or ev_pips < 5.0:
            verdict = 'REJECT'
            reasoning = "Ollama unavailable - using conservative fallback rules (low confidence or conflicts)"
        elif confidence > 0.75 and not conflicts and ev_pips > 10.0:
            verdict = 'APPROVE'
            reasoning = "Ollama unavailable - using fallback rules (high confidence, no conflicts, good EV)"
        else:
            verdict = 'REJECT'
            reasoning = "Ollama unavailable - defaulting to REJECT for safety"
        
        return {
            'verdict': verdict,
            'reasoning': reasoning,
            'latency_ms': 0,
            'confidence_adjusted': confidence,
            'rejection_criteria': ['ollama_unavailable'],
            'from_cache': False,
            'fallback': True
        }
    
    def _generate_cache_key(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict
    ) -> str:
        """
        Generate cache key for decision.
        
        Args:
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
        
        Returns:
            Cache key string
        """
        # Create hash of relevant decision inputs
        key_data = {
            'signal': coordinator_output.get('final_signal', 0),
            'confidence': round(coordinator_output.get('confidence', 0.5), 2),
            'conflicts': coordinator_output.get('conflicts_detected', False),
            'regime': coordinator_output.get('market_regime', 'unknown'),
            'ev': round(actuarial_scores.get('expected_value_pips', 0.0), 1),
            'p_win': round(actuarial_scores.get('probability_win', 0.5), 2)
        }
        
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_json.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear decision cache"""
        self._cache = {}
        logger.info("LLM Judge cache cleared")
